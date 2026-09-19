from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from .resources import resource_path


class AboutDialog(QDialog):
    def __init__(self, version: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Weather Notify について")
        self.setWindowIcon(QIcon(str(resource_path("assets/weather_notify.ico"))))
        self.resize(680, 650)
        self.setStyleSheet("""
            QDialog {
                background: #f8fafc;
                color: #111827;
            }
            QLabel {
                color: #111827;
                background: transparent;
            }
            QTextBrowser {
                background: white;
                color: #111827;
                border: 1px solid #d1d5db;
                border-radius: 10px;
                padding: 12px;
                selection-background-color: #bfdbfe;
                selection-color: #111827;
            }
            QTextBrowser a {
                color: #2563eb;
            }
            QScrollBar:vertical {
                background: #f3f4f6;
                width: 12px;
                margin: 10px 2px 10px 2px;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #cbd5e1;
                min-height: 30px;
                border-radius: 6px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QPushButton {
                padding: 7px 12px;
                border: 1px solid #111111;
                border-radius: 7px;
                background: #111111;
                color: white;
            }
            QPushButton:hover {
                background: #2a2a2a;
            }
            QPushButton:pressed {
                background: #000000;
            }
        """)

        title = QLabel("Weather Notify")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 24px; font-weight: 800; color: #111111;")

        version_label = QLabel(f"Version {version} / Portfolio Project")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: #4b5563; font-size: 12px;")

        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(
            f"""
            <style>
                body {{
                    font-family: 'Yu Gothic UI', 'Segoe UI', sans-serif;
                    color: #111827;
                    background: #ffffff;
                    margin: 6px;
                }}
                h3 {{
                    margin-top: 16px;
                    margin-bottom: 6px;
                    color: #111827;
                }}
                p, li {{ line-height: 1.6; }}
                ul {{ margin-top: 6px; margin-bottom: 10px; }}
                a {{ color: #2563eb; }}
                .note {{ color: #4b5563; }}
            </style>
            <h3>このアプリについて</h3>
            <p>
            Weather Notify は、Windows PCで現在地・指定地点の天気を表示し、
            気温や湿度が設定条件に入ったときに通知するデスクトップアプリです。
            時間別予報、睡眠中の窓開け判定、複数地点監視、動的な天気背景などを備えています。
            </p>

            <h3>データ提供元</h3>
            <ul>
              <li>Weather data: <b>Open-Meteo</b> — CC BY 4.0<br>
                  <a href="https://open-meteo.com/">https://open-meteo.com/</a></li>
              <li>Address search / reverse geocoding: <b>Nominatim / OpenStreetMap</b><br>
                  © OpenStreetMap contributors / ODbL<br>
                  <a href="https://www.openstreetmap.org/copyright">https://www.openstreetmap.org/copyright</a></li>
            </ul>

            <h3>主な技術</h3>
            <p>
            Python / PySide6 (Qt) / Requests / PyInstaller / Inno Setup
            </p>

            <h3>プライバシー</h3>
            <p>
            Weather Notifyには独自アカウント、広告、アクセス解析、開発者が管理するバックエンドサーバーはありません。
            監視設定はPC内に保存します。
            </p>
            <p>
            天気取得時には設定地点の緯度・経度をOpen-Meteoへ送信します。
            地点検索時には検索文字列、現在地の住所表示時には緯度・経度をNominatimへ送信します。
            </p>

            <h3>注意事項</h3>
            <p>
            天気情報・予報・窓開け判定は参考情報です。
            災害・生命・財産に関わる判断には公的機関や信頼できる公式情報を確認してください。
            「睡眠中の窓開け判定」は防犯、騒音、花粉、大気汚染、虫などを考慮していません。
            </p>

            <h3>第三者ライセンス</h3>
            <ul>
              <li>Qt / PySide6: LGPLv3/GPLv3 or commercial licensing depending on use</li>
              <li>Requests: Apache License 2.0</li>
              <li>PyInstaller: GPL with bootloader exception</li>
            </ul>
            <p class="note">
            詳細は配布物に同梱される README.md / PRIVACY.md / THIRD_PARTY_NOTICES.md を参照してください。
            </p>

            <h3>非提携表記</h3>
            <p>
            Weather Notify は Weathernews / ウェザーニュース社、Open-Meteo、OpenStreetMap Foundation、
            The Qt Company の公式製品ではなく、これらの組織による承認・提携を示すものではありません。
            </p>
            """
        )

        source_buttons = QHBoxLayout()
        open_meteo = QPushButton("Open-Meteo")
        osm = QPushButton("OpenStreetMap")
        qt = QPushButton("Qt / PySide6")
        open_meteo.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://open-meteo.com/en/terms"))
        )
        osm.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://www.openstreetmap.org/copyright"))
        )
        qt.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl("https://doc.qt.io/qtforpython-6/"))
        )
        source_buttons.addWidget(open_meteo)
        source_buttons.addWidget(osm)
        source_buttons.addWidget(qt)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(version_label)
        layout.addWidget(browser, 1)
        layout.addLayout(source_buttons)
        layout.addWidget(buttons)
