from __future__ import annotations

import sys
from datetime import datetime

from PySide6.QtCore import QTimer, QThreadPool, Qt
from PySide6.QtGui import QAction, QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QStyle,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from .condition import evaluate_monitor_condition
from .about_dialog import AboutDialog
from .dialogs import LocationPicker, MonitorDialog
from .weather_background import WeatherBackgroundWidget
from .hourly_forecast import HourlyForecastStrip
from .models import Location, Monitor
from .resources import resource_path
from .sleep_assessment import assess_sleep_window
from .sleep_window import SleepHoursDialog, SleepResultDialog
from .storage import load_settings, save_settings
from .weather_service import Weather
from .workers import WeatherRefreshWorker


APP_VERSION = "0.1.21"
REFRESH_INTERVAL_MS = 5 * 60 * 1000


class MonitorCard(QFrame):
    def __init__(self, monitor: Monitor, edit_callback, delete_callback):
        super().__init__()
        self.monitor = monitor
        self.setObjectName("monitorCard")
        self.setMinimumWidth(245)
        self.setMaximumWidth(285)

        self.location = QLabel(monitor.location.name)
        self.location.setWordWrap(True)
        self.location.setObjectName("cardTitle")

        symbol = "以上" if monitor.condition == "above" else "以下"
        rule_text = f"{monitor.threshold:.1f}℃ {symbol}"
        if monitor.humidity_enabled:
            hsymbol = "以上" if monitor.humidity_condition == "above" else "以下"
            rule_text += f"\nAND 湿度 {monitor.humidity_threshold:.0f}% {hsymbol}"
        self.rule = QLabel(rule_text)
        self.rule.setObjectName("ruleLabel")

        self.current = QLabel("現在 --.-℃ / 湿度 --%")
        self.status = QLabel("未取得")
        self.details = QLabel("降水確率 --% / --\n風速 -- m/s")
        self.details.setWordWrap(True)

        edit_btn = QPushButton("編集")
        delete_btn = QPushButton("削除")
        edit_btn.clicked.connect(lambda: edit_callback(monitor))
        delete_btn.clicked.connect(lambda: delete_callback(monitor))

        btns = QHBoxLayout()
        btns.addWidget(edit_btn)
        btns.addWidget(delete_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self.location)
        layout.addWidget(self.rule)
        layout.addSpacing(6)
        layout.addWidget(self.current)
        layout.addWidget(self.status)
        layout.addWidget(self.details)
        layout.addStretch()
        layout.addLayout(btns)

        self._apply_enabled_state()

    def _apply_enabled_state(self):
        if not self.monitor.enabled:
            self.status.setText("監視OFF")
            self.status.setObjectName("statusOff")
            self.style().unpolish(self.status)
            self.style().polish(self.status)

    def update_weather(self, weather: Weather):
        self.current.setText(
            f"現在 {weather.temperature:.1f}℃ / 湿度 {weather.humidity}%"
        )
        self.details.setText(
            f"降水確率 {weather.precipitation_probability}% / {weather.weather_text}\n"
            f"風速 {weather.wind_speed:.1f} m/s"
        )
        if not self.monitor.enabled:
            self.status.setText("監視OFF")
            return
        if self.monitor.active is None:
            self.status.setText("状態初期化中")
        elif self.monitor.active:
            self.status.setText("● 条件内")
        else:
            self.status.setText("○ 条件外")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Weather Notify")
        self.app_icon = QIcon(str(resource_path("assets/weather_notify.ico")))
        self.setWindowIcon(self.app_icon)
        self.resize(1120, 760)

        self.current_location, self.monitors = load_settings()
        self.monitor_cards: dict[str, MonitorCard] = {}
        self.thread_pool = QThreadPool.globalInstance()
        self.refresh_running = False
        self.latest_current_weather: Weather | None = None

        self._build_ui()
        self._build_tray()
        self._rebuild_monitor_cards()

        self.timer = QTimer(self)
        self.timer.setInterval(REFRESH_INTERVAL_MS)
        self.timer.timeout.connect(self.refresh_all)
        self.timer.start()

        QTimer.singleShot(250, self.refresh_all)

    def _build_ui(self):
        central = QWidget()
        central.setObjectName("centralRoot")
        central.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setCentralWidget(central)
        self.background_widget = WeatherBackgroundWidget(central)
        self.background_widget.lower()
        outer = QVBoxLayout(central)

        top_row = QHBoxLayout()
        heading = QLabel("Weather Notify")
        heading.setObjectName("appTitle")
        self.refresh_button = QPushButton("今すぐ更新")
        self.refresh_button.clicked.connect(self.refresh_all)
        top_row.addWidget(heading)
        top_row.addStretch()
        top_row.addWidget(self.refresh_button)
        outer.addLayout(top_row)

        body = QHBoxLayout()
        body.setSpacing(18)
        outer.addLayout(body, 1)

        # Left: current location weather
        left = QFrame()
        left.setObjectName("currentPanel")
        left.setMinimumWidth(315)
        left.setMaximumWidth(360)
        left_layout = QVBoxLayout(left)

        label = QLabel("現在地の天気")
        label.setObjectName("sectionTitle")
        self.current_name = QLabel(
            self.current_location.name if self.current_location else "地点未設定"
        )
        self.current_name.setObjectName("locationTitle")
        self.current_name.setWordWrap(True)
        self.current_accuracy = QLabel(self._location_accuracy_text(self.current_location))
        self.current_accuracy.setObjectName("locationAccuracy")
        self.current_accuracy.setWordWrap(True)

        self.weather_main = QLabel("--.-℃")
        self.weather_main.setObjectName("bigTemp")
        self.weather_text = QLabel("--")
        self.weather_text.setObjectName("weatherText")
        self.humidity = QLabel("湿度　--%")
        self.humidity.setObjectName("weatherMetric")
        self.precip = QLabel("降水確率　--%")
        self.precip.setObjectName("weatherMetric")
        self.wind = QLabel("風速　-- m/s")
        self.wind.setObjectName("weatherMetric")
        self.hourly_forecast = HourlyForecastStrip()
        self.updated = QLabel("最終更新　--")
        self.updated.setObjectName("updatedLabel")

        set_current = QPushButton("現在地として使う地点を設定")
        set_current.clicked.connect(self.set_current_location)

        left_layout.addWidget(label)
        left_layout.addWidget(self.current_name)
        left_layout.addWidget(self.current_accuracy)
        left_layout.addSpacing(14)
        left_layout.addWidget(self.weather_main)
        left_layout.addWidget(self.weather_text)
        left_layout.addSpacing(22)
        left_layout.addWidget(self.humidity)
        left_layout.addSpacing(12)
        left_layout.addWidget(self.precip)
        left_layout.addSpacing(12)
        left_layout.addWidget(self.wind)
        left_layout.addSpacing(14)
        left_layout.addWidget(self.hourly_forecast)
        left_layout.addStretch()
        left_layout.addWidget(self.updated)
        left_layout.addWidget(set_current)

        body.addWidget(left)

        # Right: monitor cards
        right = QVBoxLayout()
        right_head = QHBoxLayout()
        right_title = QLabel("気温・湿度の監視設定")
        right_title.setObjectName("sectionTitle")
        sleep_btn = QPushButton("睡眠中の窓開け判定")
        sleep_btn.clicked.connect(self.check_sleep_window)
        add_btn = QPushButton("＋ 監視地点を追加")
        add_btn.clicked.connect(self.add_monitor)
        right_head.addWidget(right_title)
        right_head.addStretch()
        right_head.addWidget(sleep_btn)
        right_head.addWidget(add_btn)
        right.addLayout(right_head)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.cards_host = QWidget()
        self.cards_layout = QHBoxLayout(self.cards_host)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.cards_layout.setSpacing(12)
        self.scroll.setWidget(self.cards_host)
        right.addWidget(self.scroll, 1)

        note = QLabel(
            "通知は「条件外 → 条件内」に入った瞬間だけ送信します。"
            " 気温は1℃、湿度は5ポイントのヒステリシスを使います。"
            " 湿度条件を使う場合は、気温条件 AND 湿度条件の両方を満たしたとき通知します。"
        )
        note.setWordWrap(True)
        note.setObjectName("hint")
        right.addWidget(note)

        body.addLayout(right, 1)

        footer = QHBoxLayout()
        footer.addStretch()
        about_btn = QPushButton("このアプリについて")
        about_btn.setObjectName("aboutButton")
        about_btn.clicked.connect(self.show_about_dialog)
        footer.addWidget(about_btn)
        self.version_label = QLabel(f"v{APP_VERSION}")
        self.version_label.setObjectName("versionLabel")
        footer.addWidget(self.version_label)
        outer.addLayout(footer)

        self.statusBar().showMessage("5分ごとに自動更新します")

        self.setStyleSheet("""
            QMainWindow {
                background: #0f172a;
            }
            #centralRoot {
                background: transparent;
            }
            QWidget {
                font-size: 14px;
                color: #111111;
            }
            QLabel {
                color: #111111;
            }
            #appTitle {
                font-size: 24px;
                font-weight: 700;
                color: #ffffff;
                background: #2563eb;
                border-radius: 10px;
                padding: 8px 14px;
            }
            #sectionTitle {
                font-size: 18px;
                font-weight: 700;
                color: #000000;
                background: #ffffff;
                border-radius: 6px;
                padding: 4px 8px;
            }
            #currentPanel, #monitorCard {
                background: #ffffff;
                border: 1px solid #dadde3;
                border-radius: 12px;
            }
            #currentPanel QLabel, #monitorCard QLabel {
                background: #ffffff;
                color: #111111;
            }
            #locationTitle, #cardTitle {
                font-size: 16px;
                font-weight: 650;
                color: #111111;
                background: #ffffff;
            }
            #bigTemp {
                font-size: 42px;
                font-weight: 700;
                color: #111111;
                background: #ffffff;
            }
            #weatherText {
                font-size: 20px;
                color: #111111;
                background: #ffffff;
            }
            #ruleLabel {
                font-size: 24px;
                font-weight: 700;
                color: #111111;
                background: #ffffff;
            }
            #updatedLabel, #hint, #locationAccuracy {
                color: #4b5563;
                background: #ffffff;
            }
            #hourlyForecastFrame {
                background: #f8fafc;
                border: 1px solid #d1d5db;
                border-radius: 8px;
            }
            #hourlyForecastTitle {
                background: #f8fafc;
                color: #111111;
                font-size: 13px;
                font-weight: 700;
                padding-left: 5px;
            }
            #forecastRowLabels, #hourlyForecastHost, #hourlyForecastScroll {
                background: #f3f4f6;
            }
            #forecastRowLabel {
                background: #f3f4f6;
                color: #374151;
                font-size: 11px;
                font-weight: 600;
                border-right: 1px solid #d1d5db;
                border-bottom: 1px solid #e5e7eb;
            }
            #forecastColumn {
                background: #ffffff;
                border-right: 1px solid #d1d5db;
            }
            #forecastColumn QLabel {
                background: #ffffff;
                border-bottom: 1px solid #e5e7eb;
            }
            #forecastCell {
                font-size: 11px;
                color: #111111;
            }
            #forecastWeatherIcon {
                font-size: 21px;
                font-family: "Segoe UI Symbol", "Yu Gothic UI";
                color: #111111;
            }
            #forecastTemperature {
                font-size: 12px;
                font-weight: 800;
                color: #111111;
            }
            #forecastEmpty {
                background: #ffffff;
                color: #6b7280;
                font-size: 11px;
            }
            #hourlyForecastScroll QScrollBar:horizontal {
                height: 10px;
                background: #e5e7eb;
                margin: 0px;
            }
            #hourlyForecastScroll QScrollBar::handle:horizontal {
                background: #3b82f6;
                min-width: 34px;
                border-radius: 5px;
            }
            #hourlyForecastScroll QScrollBar::add-line:horizontal,
            #hourlyForecastScroll QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            #aboutButton {
                padding: 4px 8px;
                font-size: 11px;
                border-radius: 6px;
            }
            QPushButton {
                padding: 7px 12px;
                border: 1px solid #111111;
                border-radius: 7px;
                background: #111111;
                color: #ffffff;
            }
            QPushButton:hover {
                background: #2a2a2a;
                color: #ffffff;
            }
            QPushButton:pressed {
                background: #000000;
                color: #ffffff;
            }
            QPushButton:disabled {
                background: #777777;
                color: #eeeeee;
                border-color: #777777;
            }
        """)

    def show_about_dialog(self):
        dialog = AboutDialog(APP_VERSION, self)
        dialog.exec()

    def _build_tray(self):
        self.tray = QSystemTrayIcon(self)
        self.tray.setIcon(self.app_icon)
        self.tray.setToolTip("Weather Notify")

        menu = QMenu(self)
        open_action = QAction("開く", self)
        open_action.triggered.connect(self.show_and_raise)
        quit_action = QAction("終了", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(open_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self._tray_activated)
        self.tray.show()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_and_raise()

    def show_and_raise(self):
        self.show()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "background_widget") and self.centralWidget() is not None:
            self.background_widget.setGeometry(self.centralWidget().rect())
            self.background_widget.lower()

    def closeEvent(self, event: QCloseEvent):
        # Keep monitoring in the system tray instead of terminating accidentally.
        event.ignore()
        self.hide()
        self.tray.showMessage(
            "Weather Notify",
            "バックグラウンドで監視を続けます。終了はタスクトレイのメニューから行えます。",
            QSystemTrayIcon.MessageIcon.Information,
            3000,
        )

    def _location_accuracy_text(self, location: Location | None) -> str:
        if location is None:
            return ""
        if location.source == "device":
            if location.accuracy_m is not None:
                return f"Windows現在地 / 位置精度 約±{location.accuracy_m:.0f}m"
            return "Windows現在地 / 位置精度 不明"
        return "住所・地点検索で設定"

    def set_current_location(self):
        dialog = LocationPicker(self, "現在地として表示する地点")
        if dialog.exec() == dialog.DialogCode.Accepted and dialog.selected_location:
            self.current_location = dialog.selected_location
            self.current_name.setText(self.current_location.name)
            self.current_accuracy.setText(self._location_accuracy_text(self.current_location))
            save_settings(self.current_location, self.monitors)
            self.refresh_all()

    def check_sleep_window(self):
        if self.current_location is None:
            QMessageBox.information(
                self,
                "睡眠中の窓開け判定",
                "先に左側の「現在地として使う地点を設定」から地点を設定してください。",
            )
            return

        if self.latest_current_weather is None:
            QMessageBox.information(
                self,
                "睡眠中の窓開け判定",
                "まだ時間別予報を取得できていません。\n「今すぐ更新」を押してからもう一度試してください。",
            )
            return

        dialog = SleepHoursDialog(self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        hours = dialog.selected_hours()
        assessment = assess_sleep_window(self.latest_current_weather, hours)
        result = SleepResultDialog(assessment, hours, self)
        result.exec()

    def add_monitor(self):
        dialog = MonitorDialog(self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            self.monitors.append(dialog.to_monitor())
            save_settings(self.current_location, self.monitors)
            self._rebuild_monitor_cards()
            self.refresh_all()

    def edit_monitor(self, monitor: Monitor):
        dialog = MonitorDialog(self, monitor)
        if dialog.exec() == dialog.DialogCode.Accepted:
            new_monitor = dialog.to_monitor(monitor)
            idx = next(i for i, m in enumerate(self.monitors) if m.id == monitor.id)
            self.monitors[idx] = new_monitor
            save_settings(self.current_location, self.monitors)
            self._rebuild_monitor_cards()
            self.refresh_all()

    def delete_monitor(self, monitor: Monitor):
        answer = QMessageBox.question(
            self,
            "監視設定を削除",
            f"「{monitor.location.name}」の監視設定を削除しますか？",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.monitors = [m for m in self.monitors if m.id != monitor.id]
            save_settings(self.current_location, self.monitors)
            self._rebuild_monitor_cards()

    def _rebuild_monitor_cards(self):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        self.monitor_cards.clear()
        for monitor in self.monitors:
            card = MonitorCard(
                monitor,
                self.edit_monitor,
                self.delete_monitor,
            )
            self.monitor_cards[monitor.id] = card
            self.cards_layout.addWidget(card)

        if not self.monitors:
            empty = QLabel(
                "まだ監視地点がありません。\n"
                "「＋ 監視地点を追加」から地点と気温・湿度条件を設定してください。"
            )
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            empty.setObjectName("hint")
            self.cards_layout.addWidget(empty)

    def refresh_all(self):
        if self.refresh_running:
            return

        locations: dict[str, Location] = {}
        if self.current_location:
            locations["current"] = self.current_location

        for monitor in self.monitors:
            locations[f"monitor:{monitor.id}"] = monitor.location

        if not locations:
            self.statusBar().showMessage("地点を設定してください")
            return

        self.refresh_running = True
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("更新中...")
        self.statusBar().showMessage("天気を更新しています...")

        worker = WeatherRefreshWorker(locations)
        worker.signals.finished.connect(self._refresh_finished)
        worker.signals.error.connect(self._refresh_failed)
        self.thread_pool.start(worker)

    def _refresh_finished(self, payload):
        results, errors = payload
        changed = False

        current_weather = results.get("current")
        if current_weather:
            self._update_current_weather(current_weather)
        else:
            for key, weather in results.items():
                if weather:
                    self.background_widget.set_weather_code(weather.weather_code)
                    break

        for monitor in self.monitors:
            weather = results.get(f"monitor:{monitor.id}")
            if not weather:
                continue

            if monitor.enabled:
                new_active, should_notify = evaluate_monitor_condition(
                    current_temp=weather.temperature,
                    current_humidity=weather.humidity,
                    temp_threshold=monitor.threshold,
                    temp_condition=monitor.condition,
                    humidity_enabled=monitor.humidity_enabled,
                    humidity_threshold=monitor.humidity_threshold,
                    humidity_condition=monitor.humidity_condition,
                    active=monitor.active,
                )
                if new_active != monitor.active:
                    monitor.active = new_active
                    changed = True

                if should_notify:
                    self._notify_monitor(monitor, weather)

            card = self.monitor_cards.get(monitor.id)
            if card:
                card.update_weather(weather)

        if changed:
            save_settings(self.current_location, self.monitors)

        self.refresh_running = False
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("今すぐ更新")

        if errors:
            self.statusBar().showMessage(
                f"更新完了（一部失敗: {len(errors)}件）", 8000
            )
        else:
            self.statusBar().showMessage("更新完了", 5000)

    def _refresh_failed(self, message: str):
        self.refresh_running = False
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("今すぐ更新")
        self.statusBar().showMessage("更新に失敗しました", 8000)
        QMessageBox.warning(self, "更新エラー", message)

    def _update_current_weather(self, weather: Weather):
        self.latest_current_weather = weather
        self.background_widget.set_weather_code(weather.weather_code)
        self.weather_main.setText(f"{weather.temperature:.1f}℃")
        self.weather_text.setText(weather.weather_text)
        self.humidity.setText(f"湿度　{weather.humidity}%")
        self.precip.setText(f"降水確率　{weather.precipitation_probability}%")
        self.wind.setText(f"風速　{weather.wind_speed:.1f} m/s")
        self.hourly_forecast.set_forecast(weather.hourly)
        try:
            dt = datetime.fromisoformat(weather.observed_at)
            stamp = dt.strftime("%Y/%m/%d %H:%M")
        except ValueError:
            stamp = weather.observed_at
        self.updated.setText(f"最終更新　{stamp}")

    def _notify_monitor(self, monitor: Monitor, weather: Weather):
        symbol = "以上" if monitor.condition == "above" else "以下"
        if monitor.humidity_enabled:
            hsymbol = "以上" if monitor.humidity_condition == "above" else "以下"
            title = (
                f"気象条件に入りました：{monitor.threshold:.1f}℃{symbol} / "
                f"湿度{monitor.humidity_threshold:.0f}%{hsymbol}"
            )
        else:
            title = f"気温条件に入りました：{monitor.threshold:.1f}℃{symbol}"
        message = (
            f"地点：{monitor.location.name}\n"
            f"気温：{weather.temperature:.1f}℃\n"
            f"湿度：{weather.humidity}%\n"
            f"降水確率：{weather.precipitation_probability}%\n"
            f"天気：{weather.weather_text}\n"
            f"風速：{weather.wind_speed:.1f} m/s"
        )
        self.tray.showMessage(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Information,
            10000,
        )


def run_app():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "WeatherNotify.DesktopApp"
            )
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("Weather Notify")
    app.setWindowIcon(QIcon(str(resource_path("assets/weather_notify.ico"))))
    app.setQuitOnLastWindowClosed(False)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())
