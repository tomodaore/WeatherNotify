from __future__ import annotations

import random
from dataclasses import dataclass

from PySide6.QtCore import QPointF, QTimer, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QWidget

from .resources import resource_path


@dataclass
class RainStreak:
    x: float
    y: float
    length: float
    speed: float
    width: float
    alpha: int


@dataclass
class SnowFlake:
    x: float
    y: float
    radius: float
    speed_y: float
    drift: float
    alpha: int


@dataclass
class MistBand:
    x: float
    y: float
    width: float
    height: float
    speed: float
    alpha: int


class WeatherBackgroundWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAutoFillBackground(False)

        self.mode = 'clear'
        self.weather_code = 0
        self.precip_intensity = 0.0
        self.rng = random.Random(20260919)
        self.frame = 0
        self.flash_alpha = 0
        self.cloud_offset = 0.0

        self.pixmaps = {
            'clear': QPixmap(str(resource_path('assets/backgrounds/sky_clear.png'))),
            'partly_cloudy': QPixmap(str(resource_path('assets/backgrounds/sky_partly_cloudy.png'))),
            'cloudy': QPixmap(str(resource_path('assets/backgrounds/sky_cloudy.png'))),
            'fog': QPixmap(str(resource_path('assets/backgrounds/sky_fog.png'))),
            'rain': QPixmap(str(resource_path('assets/backgrounds/sky_rain.png'))),
            'snow': QPixmap(str(resource_path('assets/backgrounds/sky_snow.png'))),
            'thunderstorm': QPixmap(str(resource_path('assets/backgrounds/sky_thunderstorm.png'))),
        }

        self.rain_streaks = [self._new_rain_streak() for _ in range(90)]
        self.snowflakes = [self._new_snowflake() for _ in range(80)]
        self.mist_bands = [self._new_mist_band() for _ in range(7)]

        self.timer = QTimer(self)
        self.timer.setInterval(45)
        self.timer.timeout.connect(self._tick)
        self.timer.start()

    def set_weather_code(self, code: int):
        self.weather_code = int(code)
        self.precip_intensity = self._intensity_for_code(self.weather_code)
        new_mode = self._mode_for_code(self.weather_code)
        if new_mode != self.mode:
            self.mode = new_mode
        self.update()

    def _intensity_for_code(self, code: int) -> float:
        # WMO code-aware visual strength. The image category stays simple,
        # while animation density reflects weak / normal / strong weather.
        if code in {51, 56}:
            return 0.28
        if code in {53}:
            return 0.42
        if code in {55, 57}:
            return 0.58
        if code in {61, 66, 80}:
            return 0.52
        if code in {63, 81}:
            return 0.72
        if code in {65, 67, 82}:
            return 1.0
        if code in {71, 85}:
            return 0.45
        if code in {73}:
            return 0.68
        if code in {75, 77, 86}:
            return 1.0
        if code == 95:
            return 0.78
        if code in {96, 99}:
            return 1.0
        return 0.0

    def _mode_for_code(self, code: int) -> str:
        if code in {95, 96, 99}:
            return 'thunderstorm'
        if code in {71, 73, 75, 77, 85, 86}:
            return 'snow'
        if code in {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}:
            return 'rain'
        if code in {45, 48}:
            return 'fog'
        if code == 3:
            return 'cloudy'
        if code in {1, 2}:
            return 'partly_cloudy'
        return 'clear'

    def _new_rain_streak(self) -> RainStreak:
        w = max(self.width(), 1)
        h = max(self.height(), 1)
        return RainStreak(
            x=self.rng.uniform(0, w),
            y=self.rng.uniform(-h, h),
            length=self.rng.uniform(18, 54),
            speed=self.rng.uniform(16, 32),
            width=self.rng.uniform(1.0, 2.2),
            alpha=self.rng.randint(45, 110),
        )

    def _new_snowflake(self) -> SnowFlake:
        w = max(self.width(), 1)
        h = max(self.height(), 1)
        return SnowFlake(
            x=self.rng.uniform(0, w),
            y=self.rng.uniform(-h, h),
            radius=self.rng.uniform(1.5, 4.8),
            speed_y=self.rng.uniform(1.2, 4.2),
            drift=self.rng.uniform(-0.8, 0.8),
            alpha=self.rng.randint(90, 180),
        )

    def _new_mist_band(self) -> MistBand:
        w = max(self.width(), 1)
        h = max(self.height(), 1)
        return MistBand(
            x=self.rng.uniform(-0.2 * w, 0.8 * w),
            y=self.rng.uniform(0.08 * h, 0.75 * h),
            width=self.rng.uniform(0.25 * w, 0.6 * w),
            height=self.rng.uniform(36, 92),
            speed=self.rng.uniform(0.2, 0.8),
            alpha=self.rng.randint(20, 55),
        )

    def _tick(self):
        self.frame += 1
        self.cloud_offset = (self.cloud_offset + 0.35) % max(self.width(), 1)

        if self.mode in {'rain', 'thunderstorm'}:
            for r in self.rain_streaks:
                r.y += r.speed
                r.x -= r.speed * 0.18
                if r.y - r.length > self.height() or r.x < -40:
                    nr = self._new_rain_streak()
                    r.x = self.rng.uniform(0, max(self.width(), 1))
                    r.y = self.rng.uniform(-160, -20)
                    r.length = nr.length
                    r.speed = nr.speed
                    r.width = nr.width
                    r.alpha = nr.alpha
        if self.mode == 'snow':
            for s in self.snowflakes:
                s.y += s.speed_y
                s.x += s.drift
                if s.y - s.radius > self.height() or s.x < -10 or s.x > self.width() + 10:
                    ns = self._new_snowflake()
                    s.x = self.rng.uniform(0, max(self.width(), 1))
                    s.y = self.rng.uniform(-120, -10)
                    s.radius = ns.radius
                    s.speed_y = ns.speed_y
                    s.drift = ns.drift
                    s.alpha = ns.alpha
        if self.mode in {'fog', 'cloudy', 'partly_cloudy', 'clear'}:
            for m in self.mist_bands:
                m.x += m.speed
                if m.x > self.width() + 120:
                    nm = self._new_mist_band()
                    m.x = -nm.width
                    m.y = nm.y
                    m.width = nm.width
                    m.height = nm.height
                    m.speed = nm.speed
                    m.alpha = nm.alpha
        if self.mode == 'thunderstorm':
            if self.flash_alpha <= 0 and self.rng.random() < 0.03:
                self.flash_alpha = self.rng.randint(90, 170)
            else:
                self.flash_alpha = max(0, self.flash_alpha - 22)
        else:
            self.flash_alpha = 0

        self.update()

    def _draw_cover_pixmap(self, painter: QPainter, pixmap: QPixmap):
        if pixmap.isNull():
            painter.fillRect(self.rect(), QColor(18, 33, 57))
            return
        scaled = pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)
        x = int((self.width() - scaled.width()) / 2)
        y = int((self.height() - scaled.height()) / 2)
        painter.drawPixmap(x, y, scaled)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        pixmap = self.pixmaps.get(self.mode) or self.pixmaps['clear']
        self._draw_cover_pixmap(painter, pixmap)
        self._draw_ambient_overlay(painter)

        if self.mode in {'clear', 'partly_cloudy', 'cloudy'}:
            self._draw_cloud_drift(painter)
        if self.mode == 'fog':
            self._draw_fog(painter)
        if self.mode in {'rain', 'thunderstorm'}:
            self._draw_rain(painter)
        if self.mode == 'snow':
            self._draw_snow(painter)
        if self.mode == 'thunderstorm' and self.flash_alpha > 0:
            painter.fillRect(self.rect(), QColor(255, 255, 255, self.flash_alpha))

    def _draw_ambient_overlay(self, painter: QPainter):
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0.0, QColor(0, 0, 0, 20))
        gradient.setColorAt(0.5, QColor(255, 255, 255, 0))
        gradient.setColorAt(1.0, QColor(0, 0, 0, 28))
        painter.fillRect(self.rect(), gradient)

    def _draw_cloud_drift(self, painter: QPainter):
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        count = 3 if self.mode == 'clear' else 5
        base_alpha = 16 if self.mode == 'clear' else 26 if self.mode == 'partly_cloudy' else 34
        for i in range(count):
            x = -200 + ((self.cloud_offset * (0.45 + i * 0.13)) % (self.width() + 420))
            y = 40 + i * 55
            width = self.width() * (0.42 + i * 0.06)
            height = 80 + i * 18
            color = QColor(255, 255, 255, base_alpha)
            painter.setBrush(color)
            painter.drawEllipse(int(x), int(y), int(width), int(height))
        painter.restore()

    def _draw_fog(self, painter: QPainter):
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        for band in self.mist_bands:
            path = QPainterPath()
            path.addRoundedRect(band.x, band.y, band.width, band.height, band.height / 2, band.height / 2)
            painter.fillPath(path, QColor(255, 255, 255, band.alpha))
        painter.fillRect(self.rect(), QColor(235, 240, 245, 28))
        painter.restore()

    def _draw_rain(self, painter: QPainter):
        painter.save()
        pen = QPen(QColor(220, 235, 255, 90))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        active_count = max(10, int(len(self.rain_streaks) * max(self.precip_intensity, 0.35)))
        for r in self.rain_streaks[:active_count]:
            pen.setWidthF(r.width)
            pen.setColor(QColor(220, 235, 255, r.alpha))
            painter.setPen(pen)
            painter.drawLine(QPointF(r.x, r.y), QPointF(r.x - r.length * 0.22, r.y + r.length))
        painter.restore()

    def _draw_snow(self, painter: QPainter):
        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        active_count = max(12, int(len(self.snowflakes) * max(self.precip_intensity, 0.4)))
        for s in self.snowflakes[:active_count]:
            painter.setBrush(QColor(255, 255, 255, s.alpha))
            painter.drawEllipse(QPointF(s.x, s.y), s.radius, s.radius)
        painter.restore()
