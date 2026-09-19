from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .weather_service import HourlyForecast, Weather

PRECIP_CODES = {
    51, 53, 55, 56, 57,
    61, 63, 65, 66, 67,
    71, 73, 75, 77,
    80, 81, 82,
    85, 86,
    95, 96, 99,
}
FOG_CODES = {45, 48}
THUNDER_CODES = {95, 96, 99}


@dataclass
class SleepWindowAssessment:
    level: str
    title: str
    summary: str
    start_text: str
    end_text: str
    min_temp: float
    max_temp: float
    max_humidity: int
    max_precipitation_probability: int
    max_wind_speed: float
    reasons: list[str]
    hourly_notes: list[str]


def _format_hour(time_text: str) -> str:
    try:
        dt = datetime.fromisoformat(time_text)
        return f"{dt.hour:02d}:00"
    except ValueError:
        return time_text[-5:]


def _forecast_window(weather: Weather, hours: int) -> tuple[list[HourlyForecast], datetime, datetime]:
    try:
        start = datetime.fromisoformat(weather.observed_at)
    except ValueError:
        start = datetime.now()
    end = start + timedelta(hours=hours)

    items: list[HourlyForecast] = []
    start_hour = start.replace(minute=0, second=0, microsecond=0)
    for item in weather.hourly:
        try:
            dt = datetime.fromisoformat(item.time)
        except ValueError:
            continue
        if dt < start_hour:
            continue
        if dt >= end:
            continue
        items.append(item)
    return items, start, end


def assess_sleep_window(weather: Weather, hours: int) -> SleepWindowAssessment:
    items, start, end = _forecast_window(weather, hours)

    if not items:
        items = [HourlyForecast(
            time=weather.observed_at,
            temperature=weather.temperature,
            humidity=weather.humidity,
            precipitation_probability=weather.precipitation_probability,
            weather_code=weather.weather_code,
            weather_text=weather.weather_text,
            wind_speed=weather.wind_speed,
        )]

    min_temp = min(x.temperature for x in items)
    max_temp = max(x.temperature for x in items)
    max_humidity = max(x.humidity for x in items)
    max_pop = max(x.precipitation_probability for x in items)
    max_wind = max(x.wind_speed for x in items)

    hard_reasons: list[str] = []
    caution_reasons: list[str] = []

    precip_items = [x for x in items if x.weather_code in PRECIP_CODES]
    thunder_items = [x for x in items if x.weather_code in THUNDER_CODES]
    fog_items = [x for x in items if x.weather_code in FOG_CODES]

    if thunder_items:
        first = thunder_items[0]
        hard_reasons.append(f"{_format_hour(first.time)}ごろに雷雨予報があります")
    elif precip_items:
        first = precip_items[0]
        hard_reasons.append(f"{_format_hour(first.time)}ごろに{first.weather_text}の予報があります")

    if max_pop >= 50:
        hard_reasons.append(f"最大降水確率が{max_pop}%です")
    elif max_pop >= 30:
        caution_reasons.append(f"最大降水確率が{max_pop}%です")

    if max_wind >= 8.0:
        hard_reasons.append(f"最大風速が{max_wind:.1f}m/sと強めです")
    elif max_wind >= 5.0:
        caution_reasons.append(f"最大風速が{max_wind:.1f}m/sです")

    if min_temp < 15.0:
        hard_reasons.append(f"最低気温が{min_temp:.1f}℃まで下がります")
    elif min_temp < 18.0:
        caution_reasons.append(f"最低気温が{min_temp:.1f}℃まで下がります")

    if max_temp > 27.0:
        hard_reasons.append(f"最高気温が{max_temp:.1f}℃です")
    elif max_temp > 24.0:
        caution_reasons.append(f"最高気温が{max_temp:.1f}℃です")

    if max_humidity >= 90:
        hard_reasons.append(f"最大湿度が{max_humidity}%です")
    elif max_humidity > 75:
        caution_reasons.append(f"最大湿度が{max_humidity}%です")

    if fog_items:
        first = fog_items[0]
        caution_reasons.append(f"{_format_hour(first.time)}ごろに{first.weather_text}の予報があります")

    risky = []
    for x in items:
        notes = []
        if x.precipitation_probability >= 30:
            notes.append(f"降水{x.precipitation_probability}%")
        if x.humidity > 75:
            notes.append(f"湿度{x.humidity}%")
        if x.wind_speed >= 5.0:
            notes.append(f"風{x.wind_speed:.1f}m/s")
        if x.temperature < 18.0 or x.temperature > 24.0:
            notes.append(f"{x.temperature:.1f}℃")
        if x.weather_code in PRECIP_CODES | FOG_CODES:
            notes.append(x.weather_text)
        if notes:
            risky.append(f"{_format_hour(x.time)}: " + " / ".join(dict.fromkeys(notes)))
    hourly_notes = risky[:5]

    if hard_reasons:
        level = "bad"
        title = "窓開けはおすすめしません"
        summary = "睡眠中に天候が悪化する可能性があります。"
        reasons = hard_reasons + caution_reasons
    elif caution_reasons:
        level = "caution"
        title = "窓開けは条件付きです"
        summary = "開けっぱなしにするなら、気温・湿度や雨の変化に注意してください。"
        reasons = caution_reasons
    else:
        level = "good"
        title = "窓開けはおすすめです"
        summary = "予報上は、睡眠中も窓を開けやすい気象条件です。"
        reasons = ["雨・雷雨の予報なし", "気温・湿度・風速が目安の範囲内です"]

    return SleepWindowAssessment(
        level=level,
        title=title,
        summary=summary,
        start_text=start.strftime("%m/%d %H:%M"),
        end_text=end.strftime("%m/%d %H:%M"),
        min_temp=min_temp,
        max_temp=max_temp,
        max_humidity=max_humidity,
        max_precipitation_probability=max_pop,
        max_wind_speed=max_wind,
        reasons=reasons,
        hourly_notes=hourly_notes,
    )
