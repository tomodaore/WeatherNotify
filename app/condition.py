from __future__ import annotations

from typing import Optional, Tuple

HYSTERESIS_C = 1.0
HUMIDITY_HYSTERESIS_PERCENT = 5.0


def _enter(value: float, threshold: float, condition: str) -> bool:
    if condition == "above":
        return value >= threshold
    if condition == "below":
        return value <= threshold
    raise ValueError(f"Unknown condition: {condition}")


def _leave(value: float, threshold: float, condition: str, hysteresis: float) -> bool:
    if condition == "above":
        return value <= threshold - hysteresis
    if condition == "below":
        return value >= threshold + hysteresis
    raise ValueError(f"Unknown condition: {condition}")


def evaluate_temperature_condition(
    current_temp: float,
    threshold: float,
    condition: str,
    active: Optional[bool],
) -> Tuple[bool, bool]:
    """Backward-compatible temperature-only evaluator."""
    return evaluate_monitor_condition(
        current_temp=current_temp,
        current_humidity=0.0,
        temp_threshold=threshold,
        temp_condition=condition,
        humidity_enabled=False,
        humidity_threshold=0.0,
        humidity_condition="below",
        active=active,
    )


def evaluate_monitor_condition(
    *,
    current_temp: float,
    current_humidity: float,
    temp_threshold: float,
    temp_condition: str,
    humidity_enabled: bool,
    humidity_threshold: float,
    humidity_condition: str,
    active: Optional[bool],
) -> Tuple[bool, bool]:
    """Evaluate temperature + optional humidity using AND semantics.

    Entry:
      - temperature rule must be satisfied
      - and, when enabled, humidity rule must also be satisfied

    Exit while active:
      - temperature crosses its 1 C release boundary, OR
      - enabled humidity crosses its 5 percentage-point release boundary

    active=None initializes state without sending a notification.
    """
    temp_enter = _enter(current_temp, temp_threshold, temp_condition)
    humidity_enter = (
        True
        if not humidity_enabled
        else _enter(current_humidity, humidity_threshold, humidity_condition)
    )
    all_enter = temp_enter and humidity_enter

    if active is None:
        return all_enter, False

    if not active:
        if all_enter:
            return True, True
        return False, False

    temp_leave = _leave(
        current_temp, temp_threshold, temp_condition, HYSTERESIS_C
    )
    humidity_leave = (
        False
        if not humidity_enabled
        else _leave(
            current_humidity,
            humidity_threshold,
            humidity_condition,
            HUMIDITY_HYSTERESIS_PERCENT,
        )
    )

    if temp_leave or humidity_leave:
        return False, False
    return True, False
