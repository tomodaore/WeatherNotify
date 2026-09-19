from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from typing import List
import threading
import time
import requests

from .models import Location


FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"
NOMINATIM_USER_AGENT = "WeatherNotify/0.1.21 (personal Windows desktop weather notifier)"
_NOMINATIM_RATE_LOCK = threading.Lock()
_NOMINATIM_LAST_REQUEST = 0.0


def _wait_for_nominatim_slot() -> None:
    """Respect the public Nominatim maximum of one request per second."""
    global _NOMINATIM_LAST_REQUEST
    with _NOMINATIM_RATE_LOCK:
        elapsed = time.monotonic() - _NOMINATIM_LAST_REQUEST
        if elapsed < 1.05:
            time.sleep(1.05 - elapsed)
        _NOMINATIM_LAST_REQUEST = time.monotonic()


@dataclass
class HourlyForecast:
    time: str
    temperature: float
    humidity: int
    precipitation_probability: int
    weather_code: int
    weather_text: str
    wind_speed: float


@dataclass
class Weather:
    temperature: float
    humidity: int
    precipitation_probability: int
    weather_code: int
    weather_text: str
    wind_speed: float
    observed_at: str
    hourly: list[HourlyForecast]


WMO_WEATHER = {
    0: "快晴",
    1: "晴れ",
    2: "一部曇り",
    3: "曇り",
    45: "霧",
    48: "着氷性の霧",
    51: "弱い霧雨",
    53: "霧雨",
    55: "強い霧雨",
    56: "弱い着氷性霧雨",
    57: "強い着氷性霧雨",
    61: "弱い雨",
    63: "雨",
    65: "強い雨",
    66: "弱い着氷性の雨",
    67: "強い着氷性の雨",
    71: "弱い雪",
    73: "雪",
    75: "強い雪",
    77: "霧雪",
    80: "弱いにわか雨",
    81: "にわか雨",
    82: "激しいにわか雨",
    85: "弱いにわか雪",
    86: "強いにわか雪",
    95: "雷雨",
    96: "ひょうを伴う雷雨",
    99: "激しいひょうを伴う雷雨",
}


def weather_text(code: int) -> str:
    return WMO_WEATHER.get(code, f"天気コード {code}")


def _dedupe_locations(locations: List[Location], count: int) -> List[Location]:
    seen = set()
    output = []
    for loc in locations:
        # Same geocoded point may be returned by multiple providers.
        key = (round(loc.latitude, 5), round(loc.longitude, 5))
        if key in seen:
            continue
        seen.add(key)
        output.append(loc)
        if len(output) >= count:
            break
    return output


def _search_nominatim(query: str, count: int) -> List[Location]:
    # Searches are only made when the user explicitly presses the Search button.
    # The selected latitude/longitude is saved, so this is not called by the
    # periodic weather refresh.
    _wait_for_nominatim_slot()

    search_text = query
    if "日本" not in search_text and "Japan" not in search_text:
        search_text = f"{search_text}, 日本"

    response = requests.get(
        NOMINATIM_URL,
        params={
            "q": search_text,
            "format": "jsonv2",
            "addressdetails": 1,
            "limit": min(max(count, 1), 20),
            "countrycodes": "jp",
            "layer": "address",
            "accept-language": "ja",
        },
        headers={
            "User-Agent": NOMINATIM_USER_AGENT,
            "Accept-Language": "ja",
        },
        timeout=12,
    )
    response.raise_for_status()

    results = []
    for row in response.json():
        display = str(row.get("display_name") or "").strip()
        if not display:
            continue
        results.append(
            Location(
                name=display,
                latitude=float(row["lat"]),
                longitude=float(row["lon"]),
                source="search",
            )
        )
    return results


def _search_open_meteo(query: str, count: int) -> List[Location]:
    response = requests.get(
        OPEN_METEO_GEOCODING_URL,
        params={
            "name": query,
            "count": count,
            "language": "ja",
            "format": "json",
        },
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()

    results = []
    for row in payload.get("results", []):
        parts = [
            row.get("name"),
            row.get("admin2"),
            row.get("admin1"),
            row.get("country"),
        ]
        display = " / ".join(dict.fromkeys(p for p in parts if p))
        results.append(
            Location(
                name=display,
                latitude=float(row["latitude"]),
                longitude=float(row["longitude"]),
                source="search",
            )
        )
    return results


@lru_cache(maxsize=128)
def _cached_search(query: str, count: int) -> tuple[Location, ...]:
    results: List[Location] = []
    nominatim_error = None

    try:
        results.extend(_search_nominatim(query, count))
    except requests.RequestException as exc:
        nominatim_error = exc

    # Keep the old provider as a fallback and as a source of broader city-level
    # matches. It is especially useful if the OSM public service is temporarily
    # unavailable.
    if len(results) < count:
        try:
            results.extend(_search_open_meteo(query, count))
        except requests.RequestException:
            if not results and nominatim_error is not None:
                raise nominatim_error

    return tuple(_dedupe_locations(results, count))


def search_locations(query: str, count: int = 10) -> List[Location]:
    query = " ".join(query.strip().split())
    if len(query) < 2:
        raise ValueError("地点名を2文字以上入力してください。")
    return list(_cached_search(query, count))


def reverse_geocode(latitude: float, longitude: float, accuracy_m: float | None = None) -> Location:
    """Convert a coordinate to the most detailed available address.

    Nominatim returns the closest suitable OpenStreetMap address object, so the
    displayed address can only be as detailed as both the Windows position fix
    and the available map data.
    """
    _wait_for_nominatim_slot()
    response = requests.get(
        NOMINATIM_REVERSE_URL,
        params={
            "lat": latitude,
            "lon": longitude,
            "format": "jsonv2",
            "addressdetails": 1,
            "zoom": 18,
            "layer": "address",
            "accept-language": "ja",
        },
        headers={
            "User-Agent": NOMINATIM_USER_AGENT,
            "Accept-Language": "ja",
        },
        timeout=12,
    )
    response.raise_for_status()
    row = response.json()
    display = str(row.get("display_name") or "").strip()
    if not display:
        display = f"現在地 ({latitude:.6f}, {longitude:.6f})"
    return Location(
        name=display,
        latitude=float(latitude),
        longitude=float(longitude),
        accuracy_m=accuracy_m,
        source="device",
    )


def fetch_weather(location: Location) -> Weather:
    response = requests.get(
        FORECAST_URL,
        params={
            "latitude": location.latitude,
            "longitude": location.longitude,
            "current": ",".join(
                [
                    "temperature_2m",
                    "relative_humidity_2m",
                    "weather_code",
                    "wind_speed_10m",
                ]
            ),
            "hourly": ",".join([
                "temperature_2m",
                "relative_humidity_2m",
                "precipitation_probability",
                "weather_code",
                "wind_speed_10m",
            ]),
            "timezone": "auto",
            "forecast_days": 2,
            "wind_speed_unit": "ms",
        },
        timeout=12,
    )
    response.raise_for_status()
    payload = response.json()

    current = payload["current"]
    current_time = current["time"]
    hour_key = current_time[:13] + ":00"

    hourly_times = payload.get("hourly", {}).get("time", [])
    hourly_pop = payload.get("hourly", {}).get("precipitation_probability", [])
    pop = 0

    if hour_key in hourly_times:
        idx = hourly_times.index(hour_key)
        if idx < len(hourly_pop) and hourly_pop[idx] is not None:
            pop = int(round(hourly_pop[idx]))
    elif hourly_times and hourly_pop:
        target = datetime.fromisoformat(current_time)
        pairs = []
        for t, p in zip(hourly_times, hourly_pop):
            if p is None:
                continue
            pairs.append((abs((datetime.fromisoformat(t) - target).total_seconds()), p))
        if pairs:
            pop = int(round(min(pairs, key=lambda x: x[0])[1]))

    code = int(current["weather_code"])

    hourly_payload = payload.get("hourly", {})
    hourly_temperatures = hourly_payload.get("temperature_2m", [])
    hourly_humidities = hourly_payload.get("relative_humidity_2m", [])
    hourly_codes = hourly_payload.get("weather_code", [])
    hourly_winds = hourly_payload.get("wind_speed_10m", [])

    hourly_forecast: list[HourlyForecast] = []
    try:
        current_dt = datetime.fromisoformat(current_time)
        current_hour = current_dt.replace(minute=0, second=0, microsecond=0)
    except ValueError:
        current_hour = None

    for idx, t in enumerate(hourly_times):
        if len(hourly_forecast) >= 18:
            break
        if (
            idx >= len(hourly_temperatures)
            or idx >= len(hourly_humidities)
            or idx >= len(hourly_codes)
            or idx >= len(hourly_winds)
        ):
            break
        try:
            forecast_dt = datetime.fromisoformat(t)
        except ValueError:
            continue
        if current_hour is not None and forecast_dt < current_hour:
            continue

        temp_value = hourly_temperatures[idx]
        humidity_value = hourly_humidities[idx]
        code_value = hourly_codes[idx]
        wind_value = hourly_winds[idx]
        pop_value = hourly_pop[idx] if idx < len(hourly_pop) else 0
        if temp_value is None or humidity_value is None or code_value is None or wind_value is None:
            continue
        if pop_value is None:
            pop_value = 0

        forecast_code = int(code_value)
        hourly_forecast.append(
            HourlyForecast(
                time=t,
                temperature=float(temp_value),
                humidity=int(round(humidity_value)),
                precipitation_probability=int(round(pop_value)),
                weather_code=forecast_code,
                weather_text=weather_text(forecast_code),
                wind_speed=float(wind_value),
            )
        )

    return Weather(
        temperature=float(current["temperature_2m"]),
        humidity=int(round(current["relative_humidity_2m"])),
        precipitation_probability=pop,
        weather_code=code,
        weather_text=weather_text(code),
        wind_speed=float(current["wind_speed_10m"]),
        observed_at=current_time,
        hourly=hourly_forecast,
    )
