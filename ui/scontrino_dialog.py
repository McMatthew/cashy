from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from ui.theme import C


class ScontrinoDialog(QDialog):
    def __init__(self, testo: str, parent=None, porta: str | None = None):
        super().__init__(parent)
        self.setWindowTitle("Scontrino")
        self.setMinimumSize(420, 520)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {C['surface_container']}; color: {C['on_surface']};")
        self._testo = testo
        self._porta = porta

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("Scontrino")
        title.setStyleSheet(
            f"font-size: 13pt; font-weight: 700; color: {C['on_surface']}; background: transparent;"
        )
        layout.addWidget(title)

        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        font = QFont("Courier New", 10)
        font.setFixedPitch(True)
        text_edit.setFont(font)
        text_edit.setPlainText(testo)
        text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {C['surface_container_highest']};
                color: {C['on_surface']};
                border: 1px solid {C['border_secondary']};
                border-radius: 8px;
                padding: 12px;
                font-family: "Courier New", monospace;
            }}
        """)
        layout.addWidget(text_edit)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_stampa = QPushButton("Stampa")
        btn_stampa.setObjectName("btn_secondary")
        btn_stampa.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_stampa.clicked.connect(self._stampa)
        btn_row.addWidget(btn_stampa)

        btn_chiudi = QPushButton("Chiudi")
        btn_chiudi.setObjectName("btn_primary")
        btn_chiudi.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_chiudi.clicked.connect(self.accept)
        btn_row.addWidget(btn_chiudi)

        layout.addLayout(btn_row)

    def _stampa(self):
        if self._porta:
            from core.receipt import stampa_termico
            ok, _ = stampa_termico(self._testo, self._porta)
            if ok:
                return
        # Fallback: dialogo di stampa Windows (GDI)
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            from PyQt6.QtGui import QTextDocument
            doc = QTextDocument()
            doc.setPlainText(self._testo)
            doc.print(printer)
