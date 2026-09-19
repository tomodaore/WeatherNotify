from __future__ import annotations

from PySide6.QtCore import QObject, QRunnable, Signal, Slot

from .weather_service import fetch_weather


class WorkerSignals(QObject):
    finished = Signal(object)
    error = Signal(str)


class WeatherRefreshWorker(QRunnable):
    def __init__(self, locations: dict[str, object]):
        super().__init__()
        self.locations = locations
        self.signals = WorkerSignals()

    @Slot()
    def run(self) -> None:
        try:
            results = {}
            errors = {}
            for key, location in self.locations.items():
                try:
                    results[key] = fetch_weather(location)
                except Exception as exc:
                    errors[key] = str(exc)
            self.signals.finished.emit((results, errors))
        except Exception as exc:
            self.signals.error.emit(str(exc))
