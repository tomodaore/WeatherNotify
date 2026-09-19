from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .weather_service import HourlyForecast


ROW_HEIGHTS = [26, 38, 26, 26, 26]
CONTENT_HEIGHT = sum(ROW_HEIGHTS) + 4
SCROLL_HEIGHT = CONTENT_HEIGHT + 14


def weather_symbol(code: int) -> str:
    if code == 0:
        return "☀︎"
    if code in {1, 2}:
        return "☀︎☁︎"
    if code == 3:
        return "☁︎"
    if code in {45, 48}:
        return "≋"
    if code in {51, 53, 55, 56, 57}:
        return "☂︎"
    if code in {61, 63, 65, 66, 67, 80, 81, 82}:
        return "☂︎"
    if code in {71, 73, 75, 77, 85, 86}:
        return "❄︎"
    if code in {95, 96, 99}:
        return "⚡"
    return "☁︎"


class ForecastColumn(QFrame):
    def __init__(self, item: HourlyForecast, show_date: bool, parent=None):
        super().__init__(parent)
        self.setObjectName("forecastColumn")
        self.setFixedWidth(60)
        self.setFixedHeight(CONTENT_HEIGHT)

        try:
            dt = datetime.fromisoformat(item.time)
            time_text = f"{dt.day}日\n{dt.hour}時" if show_date else f"{dt.hour}時"
        except ValueError:
            time_text = item.time[-5:]

        values = [
            time_text,
            weather_symbol(item.weather_code),
            f"{item.precipitation_probability}%",
            f"{item.temperature:.0f}℃",
            f"{item.wind_speed:.0f}m/s",
        ]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        for index, value in enumerate(values):
            label = QLabel(value)
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFixedHeight(ROW_HEIGHTS[index])
            if index == 1:
                label.setObjectName("forecastWeatherIcon")
                label.setToolTip(item.weather_text)
            elif index == 3:
                label.setObjectName("forecastTemperature")
            else:
                label.setObjectName("forecastCell")
            layout.addWidget(label)


class HourlyForecastStrip(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("hourlyForecastFrame")
        self.setFixedHeight(196)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(4)

        title = QLabel("時間別予報")
        title.setObjectName("hourlyForecastTitle")
        root.addWidget(title)

        content_row = QHBoxLayout()
        content_row.setContentsMargins(0, 0, 0, 0)
        content_row.setSpacing(0)
        root.addLayout(content_row, 1)

        labels = QFrame()
        labels.setObjectName("forecastRowLabels")
        labels.setFixedWidth(44)
        labels.setFixedHeight(CONTENT_HEIGHT)
        labels_layout = QVBoxLayout(labels)
        labels_layout.setContentsMargins(0, 2, 0, 2)
        labels_layout.setSpacing(0)
        for height, text in zip(ROW_HEIGHTS, ["時", "天気", "降水", "気温", "風"]):
            label = QLabel(text)
            label.setObjectName("forecastRowLabel")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setFixedHeight(height)
            labels_layout.addWidget(label)
        content_row.addWidget(labels)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("hourlyForecastScroll")
        self.scroll.setWidgetResizable(False)
        self.scroll.setFixedHeight(SCROLL_HEIGHT)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)

        self.host = QWidget()
        self.host.setFixedHeight(CONTENT_HEIGHT)
        self.host.setObjectName("hourlyForecastHost")
        self.columns = QHBoxLayout(self.host)
        self.columns.setContentsMargins(0, 0, 0, 0)
        self.columns.setSpacing(0)
        self.scroll.setWidget(self.host)
        content_row.addWidget(self.scroll, 1)

        self.set_forecast([])

    def set_forecast(self, hourly: list[HourlyForecast]):
        while self.columns.count():
            item = self.columns.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if not hourly:
            empty = QLabel("予報を取得すると表示されます")
            empty.setObjectName("forecastEmpty")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setFixedSize(230, CONTENT_HEIGHT)
            self.columns.addWidget(empty)
            self.host.setFixedWidth(230)
            return

        previous_date = None
        for index, forecast in enumerate(hourly):
            try:
                dt = datetime.fromisoformat(forecast.time)
                date = dt.date()
                show_date = index == 0 or date != previous_date
                previous_date = date
            except ValueError:
                show_date = index == 0
            self.columns.addWidget(ForecastColumn(forecast, show_date))

        width = max(1, len(hourly) * 60)
        self.host.setFixedSize(width, CONTENT_HEIGHT)
        self.scroll.horizontalScrollBar().setValue(0)
