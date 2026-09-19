from __future__ import annotations

import math
from typing import Optional

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Qt, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtPositioning import QGeoPositionInfo, QGeoPositionInfoSource
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from .models import Location, Monitor
from .weather_service import reverse_geocode, search_locations


DIALOG_STYLE = """
    QDialog, QMessageBox {
        background: #ffffff;
        color: #111111;
    }
    QLabel, QCheckBox {
        background: #ffffff;
        color: #111111;
    }
    QLineEdit, QComboBox, QDoubleSpinBox {
        background: #ffffff;
        color: #111111;
        border: 1px solid #c7cbd1;
        border-radius: 6px;
        padding: 6px 8px;
        min-height: 22px;
    }
    QComboBox QAbstractItemView {
        background: #ffffff;
        color: #111111;
        selection-background-color: #e5e7eb;
        selection-color: #000000;
        border: 1px solid #c7cbd1;
    }
    QPushButton, QDialogButtonBox QPushButton {
        background: #111111;
        color: #ffffff;
        border: 1px solid #111111;
        border-radius: 7px;
        padding: 7px 12px;
        min-width: 72px;
    }
    QPushButton:hover, QDialogButtonBox QPushButton:hover {
        background: #2a2a2a;
    }
    QPushButton:pressed, QDialogButtonBox QPushButton:pressed {
        background: #000000;
    }
    QPushButton:disabled {
        background: #777777;
        color: #eeeeee;
        border-color: #777777;
    }
"""


class ReverseSignals(QObject):
    finished = Signal(object)
    error = Signal(str)


class ReverseGeocodeWorker(QRunnable):
    def __init__(self, latitude: float, longitude: float, accuracy_m: Optional[float]):
        super().__init__()
        self.latitude = latitude
        self.longitude = longitude
        self.accuracy_m = accuracy_m
        self.signals = ReverseSignals()

    @Slot()
    def run(self) -> None:
        try:
            location = reverse_geocode(
                self.latitude,
                self.longitude,
                self.accuracy_m,
            )
            self.signals.finished.emit(location)
        except Exception as exc:
            self.signals.error.emit(str(exc))


class LocationPicker(QDialog):
    def __init__(self, parent=None, title: str = "地点を設定"):
        super().__init__(parent)
        self.setStyleSheet(DIALOG_STYLE)
        self.setWindowTitle(title)
        self.resize(720, 390)
        self.selected_location: Optional[Location] = None
        self._results: list[Location] = []
        self._position_source: Optional[QGeoPositionInfoSource] = None
        self._reverse_worker: Optional[ReverseGeocodeWorker] = None
        self._pending_latitude: Optional[float] = None
        self._pending_longitude: Optional[float] = None
        self._pending_accuracy: Optional[float] = None

        current_guide = QLabel(
            "現在地はWindowsの位置情報サービスから取得します。"
            " PCにGPSがない場合はWi-Fiなどから推定されるため、精度は環境によって変わります。"
        )
        current_guide.setWordWrap(True)

        self.current_button = QPushButton("現在地を取得")
        self.location_settings_button = QPushButton("Windows位置情報設定")
        current_row = QHBoxLayout()
        current_row.addWidget(self.current_button)
        current_row.addWidget(self.location_settings_button)
        current_row.addStretch()

        separator = QLabel("または住所・地点名から検索")
        separator.setStyleSheet(
            "background: #ffffff; color: #111111; font-weight: 700; margin-top: 8px;"
        )

        guide = QLabel(
            "市区町村より細かい住所も検索できます。例: 「住吉 浜松市中央区」"
        )
        guide.setWordWrap(True)

        self.query = QLineEdit()
        self.query.setPlaceholderText("例: 住吉 浜松市中央区 / 中央区 浜松市 / 静岡駅")
        self.search_button = QPushButton("検索")
        self.results_combo = QComboBox()
        self.results_combo.setMinimumWidth(590)
        self.results_combo.setMaxVisibleItems(12)

        search_row = QHBoxLayout()
        search_row.addWidget(self.query, 1)
        search_row.addWidget(self.search_button)

        self.status = QLabel("現在地を取得するか、地点名・住所を入力して検索してください。")
        self.status.setWordWrap(True)
        self.status.setStyleSheet(
            "background: #ffffff; color: #111111; border: 1px solid #d1d5db; "
            "border-radius: 6px; padding: 8px;"
        )

        attribution = QLabel(
            '住所検索・逆ジオコーディング: '
            '<a href="https://www.openstreetmap.org/copyright">© OpenStreetMap contributors</a> / Open-Meteo'
        )
        attribution.setOpenExternalLinks(True)
        attribution.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        attribution.setStyleSheet("color: #4b5563; background: #ffffff;")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )

        layout = QVBoxLayout(self)
        layout.addWidget(current_guide)
        layout.addLayout(current_row)
        layout.addWidget(separator)
        layout.addWidget(guide)
        layout.addLayout(search_row)
        layout.addWidget(self.results_combo)
        layout.addWidget(self.status)
        layout.addStretch()
        layout.addWidget(attribution)
        layout.addWidget(buttons)

        self.current_button.clicked.connect(self.get_current_location)
        self.location_settings_button.clicked.connect(self.open_location_settings)
        self.search_button.clicked.connect(self.search)
        self.query.returnPressed.connect(self.search)
        self.query.textChanged.connect(self._invalidate_selection)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

    def _invalidate_selection(self):
        self.selected_location = None

    def _set_busy(self, busy: bool) -> None:
        self.current_button.setEnabled(not busy)
        self.search_button.setEnabled(not busy)

    def open_location_settings(self) -> None:
        QDesktopServices.openUrl(QUrl("ms-settings:privacy-location"))

    def get_current_location(self) -> None:
        self.selected_location = None
        self._results = []
        self.results_combo.clear()
        self._set_busy(True)
        self.status.setText(
            "Windowsから現在地を取得しています… 初回やPC環境によっては少し時間がかかります。"
        )

        try:
            self._position_source = QGeoPositionInfoSource.createDefaultSource(self)
        except Exception as exc:
            self._position_source = None
            self._location_unavailable(str(exc))
            return

        if self._position_source is None:
            self._location_unavailable(
                "Windowsの位置情報ソースを利用できませんでした。"
            )
            return

        self._position_source.positionUpdated.connect(self._on_position_updated)
        self._position_source.errorOccurred.connect(self._on_position_error)
        timeout = max(20000, int(self._position_source.minimumUpdateInterval()) + 1000)
        self._position_source.requestUpdate(timeout)

    def _location_unavailable(self, detail: str) -> None:
        self._set_busy(False)
        self.status.setText(
            "現在地を取得できませんでした。Windowsの「位置情報サービス」と、"
            "デスクトップ アプリの位置情報アクセスをONにしてください。"
        )
        QMessageBox.warning(
            self,
            "現在地を取得できません",
            "Windowsの位置情報を利用できません。\n\n"
            "設定 → プライバシーとセキュリティ → 位置情報 で、\n"
            "位置情報サービスとデスクトップアプリのアクセスを確認してください。\n\n"
            f"詳細: {detail}",
        )

    def _on_position_updated(self, position: QGeoPositionInfo) -> None:
        if not position.isValid() or not position.coordinate().isValid():
            self._location_unavailable("無効な位置情報が返されました。")
            return

        coordinate = position.coordinate()
        latitude = float(coordinate.latitude())
        longitude = float(coordinate.longitude())
        accuracy = None
        attr = QGeoPositionInfo.Attribute.HorizontalAccuracy
        if position.hasAttribute(attr):
            value = float(position.attribute(attr))
            if math.isfinite(value) and value >= 0:
                accuracy = value

        self._pending_latitude = latitude
        self._pending_longitude = longitude
        self._pending_accuracy = accuracy

        accuracy_text = (
            f" / 位置精度 約±{accuracy:.0f}m" if accuracy is not None else ""
        )
        self.status.setText(
            f"座標を取得しました ({latitude:.6f}, {longitude:.6f}){accuracy_text}。"
            " 詳細住所を確認しています…"
        )

        # Reverse geocoding is a network operation, so do not block the UI thread.
        worker = ReverseGeocodeWorker(latitude, longitude, accuracy)
        worker.signals.finished.connect(self._on_reverse_finished)
        worker.signals.error.connect(self._on_reverse_error)
        self._reverse_worker = worker
        QThreadPool.globalInstance().start(worker)

        if self._position_source is not None:
            self._position_source.deleteLater()
            self._position_source = None

    def _on_position_error(self, error) -> None:
        if self._position_source is not None:
            self._position_source.deleteLater()
            self._position_source = None

        if error == QGeoPositionInfoSource.Error.AccessError:
            detail = "位置情報へのアクセスが許可されていません。"
        elif error == QGeoPositionInfoSource.Error.ClosedError:
            detail = "Windowsの位置情報サービスがOFFになっています。"
        elif error == QGeoPositionInfoSource.Error.UpdateTimeoutError:
            detail = "時間内に現在地を取得できませんでした。"
        else:
            detail = f"位置情報エラー: {error}"
        self._location_unavailable(detail)

    def _on_reverse_finished(self, location: Location) -> None:
        self._reverse_worker = None
        self._results = [location]
        self.results_combo.clear()
        self.results_combo.addItem(
            f"{location.name}  ({location.latitude:.6f}, {location.longitude:.6f})"
        )
        self.results_combo.setCurrentIndex(0)
        self.selected_location = location
        self._set_busy(False)

        if location.accuracy_m is None:
            accuracy_text = "位置精度: 不明"
        else:
            accuracy_text = f"位置精度: 約±{location.accuracy_m:.0f}m"

        if location.accuracy_m is not None and location.accuracy_m > 100:
            accuracy_note = (
                " 精度が100mを超えているため、丁目・番地表示は参考程度にしてください。"
            )
        else:
            accuracy_note = (
                " 地図データに番地情報があれば、丁目・番地相当まで表示します。"
            )
        self.status.setText(
            f"現在地を取得しました。{accuracy_text}。{accuracy_note} 保存するとこの座標を使います。"
        )

    def _on_reverse_error(self, message: str) -> None:
        self._reverse_worker = None
        latitude = self._pending_latitude
        longitude = self._pending_longitude
        accuracy = self._pending_accuracy
        self._set_busy(False)
        if latitude is None or longitude is None:
            self.status.setText("住所への変換に失敗しました。")
            return

        # Weather can still use the exact acquired coordinate even if the address lookup fails.
        location = Location(
            name=f"現在地 ({latitude:.6f}, {longitude:.6f})",
            latitude=latitude,
            longitude=longitude,
            accuracy_m=accuracy,
            source="device",
        )
        self._results = [location]
        self.results_combo.clear()
        self.results_combo.addItem(location.name)
        self.results_combo.setCurrentIndex(0)
        self.selected_location = location
        self.status.setText(
            "現在地の座標は取得できましたが、詳細住所への変換に失敗しました。"
            " 座標そのものは天気取得に利用できます。"
        )
        QMessageBox.information(
            self,
            "住所の取得に失敗",
            f"現在地の座標は取得できました。\n\n"
            f"緯度: {latitude:.6f}\n経度: {longitude:.6f}\n\n"
            f"住所変換エラー: {message}",
        )

    def search(self):
        try:
            self._set_busy(True)
            self.status.setText("検索中...")
            self._results = search_locations(self.query.text())
            self.results_combo.clear()
            if not self._results:
                self.status.setText(
                    "地点が見つかりませんでした。市区町村も一緒に入力してみてください。"
                )
                return
            for loc in self._results:
                self.results_combo.addItem(
                    f"{loc.name}  ({loc.latitude:.5f}, {loc.longitude:.5f})"
                )
            self.status.setText(
                f"{len(self._results)}件見つかりました。候補を選んで保存してください。"
            )
        except Exception as exc:
            QMessageBox.warning(self, "地点検索エラー", str(exc))
            self.status.setText("検索に失敗しました。")
        finally:
            self._set_busy(False)

    def _accept(self):
        idx = self.results_combo.currentIndex()
        if idx < 0 or idx >= len(self._results):
            QMessageBox.information(
                self,
                "地点未選択",
                "現在地を取得するか、検索結果から地点を選んでください。",
            )
            return
        self.selected_location = self._results[idx]
        self.accept()


class MonitorDialog(QDialog):
    def __init__(self, parent=None, monitor: Optional[Monitor] = None):
        super().__init__(parent)
        self.setStyleSheet(DIALOG_STYLE)
        self.setWindowTitle("監視設定")
        self.resize(590, 430)
        self.location: Optional[Location] = monitor.location if monitor else None

        self.location_label = QLabel(
            self.location.name if self.location else "未設定"
        )
        self.location_label.setWordWrap(True)
        self.location_label.setStyleSheet(
            "background: #ffffff; color: #111111; border: 1px solid #d1d5db; "
            "border-radius: 6px; padding: 7px;"
        )
        self.location_button = QPushButton("地点を選ぶ")

        location_row = QHBoxLayout()
        location_row.addWidget(self.location_label, 1)
        location_row.addWidget(self.location_button)

        self.condition_combo = QComboBox()
        self.condition_combo.addItem("以上", "above")
        self.condition_combo.addItem("以下", "below")

        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(-60.0, 60.0)
        self.threshold.setDecimals(1)
        self.threshold.setSingleStep(0.5)
        self.threshold.setSuffix(" ℃")
        self.threshold.setValue(30.0)

        self.humidity_enabled = QCheckBox("湿度条件も使う（OFFなら気温のみ / ONなら気温とAND）")
        self.humidity_enabled.setChecked(False)

        self.humidity_condition_combo = QComboBox()
        self.humidity_condition_combo.addItem("以上", "above")
        self.humidity_condition_combo.addItem("以下", "below")
        self.humidity_condition_combo.setCurrentIndex(1)

        self.humidity_threshold = QDoubleSpinBox()
        self.humidity_threshold.setRange(0.0, 100.0)
        self.humidity_threshold.setDecimals(0)
        self.humidity_threshold.setSingleStep(1.0)
        self.humidity_threshold.setSuffix(" %")
        self.humidity_threshold.setValue(75.0)

        self.enabled = QCheckBox("監視を有効にする")
        self.enabled.setChecked(True)

        form = QFormLayout()
        form.addRow("地点", location_row)
        form.addRow("気温条件", self.condition_combo)
        form.addRow("設定気温", self.threshold)
        form.addRow("", self.humidity_enabled)
        form.addRow("湿度条件", self.humidity_condition_combo)
        form.addRow("設定湿度", self.humidity_threshold)
        form.addRow("", self.enabled)

        explanation = QLabel(
            "気温は1℃、湿度は5ポイントのヒステリシスを使用します。\n"
            "例: 30℃以上 → 29℃以下で解除。湿度75%以下 → 80%以上で解除。\n"
            "湿度条件を有効にした場合は、気温条件 AND 湿度条件の両方を満たしたとき通知します。"
        )
        explanation.setWordWrap(True)
        explanation.setStyleSheet("color: #4b5563; background: #ffffff;")

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(explanation)
        layout.addStretch()
        layout.addWidget(buttons)

        self.location_button.clicked.connect(self.pick_location)
        self.humidity_enabled.toggled.connect(self._update_humidity_controls)
        buttons.accepted.connect(self._accept)
        buttons.rejected.connect(self.reject)

        if monitor:
            idx = self.condition_combo.findData(monitor.condition)
            if idx >= 0:
                self.condition_combo.setCurrentIndex(idx)
            self.threshold.setValue(monitor.threshold)
            self.humidity_enabled.setChecked(monitor.humidity_enabled)
            hidx = self.humidity_condition_combo.findData(monitor.humidity_condition)
            if hidx >= 0:
                self.humidity_condition_combo.setCurrentIndex(hidx)
            self.humidity_threshold.setValue(monitor.humidity_threshold)
            self.enabled.setChecked(monitor.enabled)

        self._update_humidity_controls(self.humidity_enabled.isChecked())

    def _update_humidity_controls(self, enabled: bool) -> None:
        self.humidity_condition_combo.setEnabled(enabled)
        self.humidity_threshold.setEnabled(enabled)

    def pick_location(self):
        dialog = LocationPicker(self, "監視する地点を選択")
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_location:
            self.location = dialog.selected_location
            self.location_label.setText(self.location.name)

    def _accept(self):
        if not self.location:
            QMessageBox.information(self, "地点未設定", "監視する地点を選択してください。")
            return
        self.accept()

    def to_monitor(self, existing: Optional[Monitor] = None) -> Monitor:
        condition = self.condition_combo.currentData()
        humidity_condition = self.humidity_condition_combo.currentData()
        humidity_enabled = self.humidity_enabled.isChecked()
        changed_rule = (
            existing is None
            or existing.location != self.location
            or existing.condition != condition
            or abs(existing.threshold - self.threshold.value()) > 1e-9
            or existing.humidity_enabled != humidity_enabled
            or existing.humidity_condition != humidity_condition
            or abs(existing.humidity_threshold - self.humidity_threshold.value()) > 1e-9
        )
        return Monitor(
            id=existing.id if existing else "",
            location=self.location,
            condition=condition,
            threshold=self.threshold.value(),
            humidity_enabled=humidity_enabled,
            humidity_condition=humidity_condition,
            humidity_threshold=self.humidity_threshold.value(),
            enabled=self.enabled.isChecked(),
            active=None if changed_rule else existing.active,
        )
