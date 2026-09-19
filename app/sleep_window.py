from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QVBoxLayout,
)

from .sleep_assessment import SleepWindowAssessment


class SleepHoursDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("睡眠中の窓開け判定")
        self.setModal(True)
        self.setMinimumWidth(360)

        title = QLabel("今から何時間くらい寝ますか？")
        title.setObjectName("sleepDialogTitle")
        help_text = QLabel(
            "指定した時間内の気温・湿度・降水確率・天気・風速から、\n"
            "窓を開けっぱなしにしやすいか判定します。"
        )
        help_text.setWordWrap(True)

        self.hours = QSpinBox()
        self.hours.setRange(1, 12)
        self.hours.setValue(7)
        self.hours.setSuffix(" 時間")

        row = QHBoxLayout()
        row.addWidget(QLabel("睡眠時間"))
        row.addStretch()
        row.addWidget(self.hours)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("判定する")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("キャンセル")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(title)
        layout.addWidget(help_text)
        layout.addSpacing(8)
        layout.addLayout(row)
        layout.addSpacing(8)
        layout.addWidget(buttons)

        self.setStyleSheet("""
            QDialog { background: #ffffff; }
            QLabel { color: #111111; font-size: 14px; }
            #sleepDialogTitle { font-size: 19px; font-weight: 800; }
            QSpinBox { background: #ffffff; color: #111111; border: 1px solid #9ca3af; border-radius: 6px; padding: 6px 8px; min-width: 100px; font-size: 15px; font-weight: 700; }
            QPushButton { padding: 7px 14px; border: 1px solid #111111; border-radius: 7px; background: #111111; color: #ffffff; }
        """)

    def selected_hours(self) -> int:
        return int(self.hours.value())


class SleepResultDialog(QDialog):
    def __init__(self, assessment: SleepWindowAssessment, hours: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("睡眠中の窓開け判定")
        self.setModal(True)
        self.setMinimumWidth(520)

        result = QLabel(assessment.title)
        result.setObjectName(f"sleepResult_{assessment.level}")
        result.setAlignment(Qt.AlignmentFlag.AlignCenter)
        period = QLabel(f"今から {hours}時間　　{assessment.start_text} → {assessment.end_text}")
        period.setAlignment(Qt.AlignmentFlag.AlignCenter)
        period.setObjectName("sleepPeriod")
        summary = QLabel(assessment.summary)
        summary.setWordWrap(True)
        summary.setAlignment(Qt.AlignmentFlag.AlignCenter)

        metrics = QFrame()
        metrics.setObjectName("sleepMetrics")
        metrics_layout = QVBoxLayout(metrics)
        metrics_layout.setContentsMargins(14, 10, 14, 10)
        metrics_layout.setSpacing(4)
        for text in [
            f"気温　　　{assessment.min_temp:.1f}℃ ～ {assessment.max_temp:.1f}℃",
            f"最大湿度　{assessment.max_humidity}%",
            f"最大降水確率　{assessment.max_precipitation_probability}%",
            f"最大風速　{assessment.max_wind_speed:.1f} m/s",
        ]:
            line = QLabel(text)
            line.setObjectName("sleepMetricLine")
            metrics_layout.addWidget(line)

        reason_title = QLabel("判定理由")
        reason_title.setObjectName("sleepSectionTitle")
        reasons = QLabel("\n".join(f"・{r}" for r in assessment.reasons))
        reasons.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.addWidget(result)
        layout.addWidget(period)
        layout.addWidget(summary)
        layout.addSpacing(8)
        layout.addWidget(metrics)
        layout.addSpacing(6)
        layout.addWidget(reason_title)
        layout.addWidget(reasons)

        if assessment.hourly_notes:
            notes_title = QLabel("注意する時間帯")
            notes_title.setObjectName("sleepSectionTitle")
            notes = QLabel("\n".join(f"・{x}" for x in assessment.hourly_notes))
            notes.setWordWrap(True)
            layout.addWidget(notes_title)
            layout.addWidget(notes)

        caveat = QLabel("※ 気象条件だけを使った目安です。防犯・騒音・花粉などは判定していません。")
        caveat.setWordWrap(True)
        caveat.setObjectName("sleepCaveat")
        layout.addSpacing(6)
        layout.addWidget(caveat)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("閉じる")
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self.setStyleSheet("""
            QDialog { background: #ffffff; }
            QLabel { color: #111111; font-size: 14px; }
            #sleepResult_good { background: #dcfce7; color: #166534; font-size: 23px; font-weight: 900; border-radius: 10px; padding: 12px; }
            #sleepResult_caution { background: #fef3c7; color: #92400e; font-size: 23px; font-weight: 900; border-radius: 10px; padding: 12px; }
            #sleepResult_bad { background: #fee2e2; color: #991b1b; font-size: 23px; font-weight: 900; border-radius: 10px; padding: 12px; }
            #sleepPeriod { font-weight: 700; color: #374151; }
            #sleepMetrics { background: #f8fafc; border: 1px solid #d1d5db; border-radius: 8px; }
            #sleepMetricLine { font-size: 15px; font-weight: 700; background: #f8fafc; }
            #sleepSectionTitle { font-size: 15px; font-weight: 800; margin-top: 4px; }
            #sleepCaveat { font-size: 11px; color: #6b7280; }
            QPushButton { padding: 7px 16px; border: 1px solid #111111; border-radius: 7px; background: #111111; color: #ffffff; }
        """)
