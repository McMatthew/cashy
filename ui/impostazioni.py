import json
import shutil
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QComboBox, QFileDialog, QMessageBox, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal
from ui.theme import C
from core.database import DatabaseManager
from core.paths import get_app_dir
from core.receipt import genera_scontrino, stampa_termico

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class _SectionTitle(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QLabel {{
                color: {C['primary']};
                font-size: 10pt;
                font-weight: 700;
                background: transparent;
                padding-top: 6px;
                padding-bottom: 2px;
            }}
        """)


class _FieldLabel(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(
            f"color: {C['on_surface_variant']}; font-size: 9pt; background: transparent;"
        )


class Impostazioni(QDialog):
    impostazioni_salvate = pyqtSignal(dict)

    def __init__(self, db: DatabaseManager, config: dict, parent=None):
        super().__init__(parent)
        self._db = db
        self._config = dict(config)
        self.setWindowTitle("Impostazioni")
        self.setMinimumSize(700, 420)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(
            f"background-color: {C['surface_container']}; color: {C['on_surface']};"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 20, 24, 20)
        root.setSpacing(10)

        # ── Title ────────────────────────────────────────────────────
        title = QLabel("Impostazioni")
        title.setStyleSheet(
            f"font-size: 14pt; font-weight: 700; color: {C['on_surface']}; background: transparent;"
        )
        root.addWidget(title)
        root.addWidget(self._make_sep())

        # ── Two-column content area ───────────────────────────────────
        cols = QHBoxLayout()
        cols.setSpacing(0)

        left = self._build_left_col()
        vsep = QFrame()
        vsep.setFrameShape(QFrame.Shape.VLine)
        vsep.setStyleSheet(
            f"background-color: {C['outline_variant']}; max-width: 1px; margin: 0 20px;"
        )
        right = self._build_right_col()

        cols.addLayout(left, 1)
        cols.addWidget(vsep)
        cols.addLayout(right, 1)

        root.addLayout(cols)
        root.addWidget(self._make_sep())

        # ── Buttons ───────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_annulla = QPushButton("Annulla")
        btn_annulla.setObjectName("btn_secondary")
        btn_annulla.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_annulla.clicked.connect(self.reject)
        btn_row.addWidget(btn_annulla)

        btn_salva = QPushButton("Salva")
        btn_salva.setObjectName("btn_primary")
        btn_salva.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_salva.clicked.connect(self._salva)
        btn_row.addWidget(btn_salva)

        root.addLayout(btn_row)

    # ── Column builders ───────────────────────────────────────────────

    def _build_left_col(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(6)
        col.setContentsMargins(0, 0, 20, 0)

        col.addWidget(_SectionTitle("Evento"))

        col.addWidget(_FieldLabel("Nome Evento"))
        self._nome_input = QLineEdit(self._config.get("nome_evento", ""))
        col.addWidget(self._nome_input)

        col.addWidget(_FieldLabel("Data (gg/mm/aaaa)"))
        self._data_input = QLineEdit(self._config.get("data_evento", ""))
        col.addWidget(self._data_input)

        col.addWidget(_FieldLabel("Orario"))
        self._orario_input = QLineEdit(self._config.get("orario_evento", ""))
        col.addWidget(self._orario_input)

        col.addWidget(_FieldLabel("Messaggio Scontrino"))
        self._messaggio_input = QLineEdit(self._config.get("messaggio_scontrino", ""))
        col.addWidget(self._messaggio_input)

        col.addStretch()
        return col

    def _build_right_col(self) -> QVBoxLayout:
        col = QVBoxLayout()
        col.setSpacing(6)
        col.setContentsMargins(20, 0, 0, 0)

        # ── Stampante ────────────────────────────────────────────────
        col.addWidget(_SectionTitle("Stampante"))

        col.addWidget(_FieldLabel("Stampante"))
        self._porta_combo = QComboBox()
        self._porta_combo.setMaxVisibleItems(12)
        self._reload_stampanti()
        col.addWidget(self._porta_combo)

        hint = QLabel(
            "Stampanti di sistema: ESC/POS raw via win32print (scontrino compatto). "
            "USB/COM/LPT: ESC/POS diretto (richiede python-escpos)."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(
            f"color: {C['on_surface_variant']}; font-size: 8pt; background: transparent;"
        )
        col.addWidget(hint)

        btn_row_stampa = QHBoxLayout()
        btn_row_stampa.setSpacing(8)

        btn_test = QPushButton("Test Stampa")
        btn_test.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_test.clicked.connect(self._test_stampa)
        btn_row_stampa.addWidget(btn_test)

        btn_reload = QPushButton("↻ Aggiorna")
        btn_reload.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_reload.clicked.connect(self._reload_stampanti)
        btn_row_stampa.addWidget(btn_reload)
        btn_row_stampa.addStretch()

        col.addLayout(btn_row_stampa)
        col.addWidget(self._make_sep())

        # ── Aspetto ──────────────────────────────────────────────────
        col.addWidget(_SectionTitle("Aspetto"))

        col.addWidget(_FieldLabel("Tema"))
        self._tema_combo = QComboBox()
        self._tema_combo.addItem("Scuro", "dark")
        self._tema_combo.addItem("Chiaro", "light")
        current_theme = self._config.get("theme", "dark")
        self._tema_combo.setCurrentIndex(0 if current_theme == "dark" else 1)
        col.addWidget(self._tema_combo)
        col.addWidget(self._make_sep())

        # ── Sistema ──────────────────────────────────────────────────
        col.addWidget(_SectionTitle("Sistema"))

        btn_backup = QPushButton("Backup Database")
        btn_backup.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_backup.clicked.connect(self._backup_db)
        col.addWidget(btn_backup)

        self._sys_lbl = QLabel()
        self._sys_lbl.setStyleSheet(
            f"color: {C['on_surface_variant']}; font-size: 9pt; background: transparent;"
        )
        self._sys_lbl.setWordWrap(True)
        col.addWidget(self._sys_lbl)
        self._update_sys_info()

        col.addStretch()
        return col

    # ── Helpers ───────────────────────────────────────────────────────

    def _make_sep(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(
            f"background-color: {C['outline_variant']}; max-height: 1px;"
        )
        return sep

    def _reload_stampanti(self):
        from core.printing import get_stampanti_windows
        porta_attuale = self._porta_combo.currentText() if self._porta_combo.count() > 0 else ""

        self._porta_combo.blockSignals(True)
        self._porta_combo.clear()

        stampanti_win = get_stampanti_windows()
        for p in stampanti_win:
            self._porta_combo.addItem(p)
        if stampanti_win:
            self._porta_combo.insertSeparator(len(stampanti_win))
        for p in ["USB", "COM1", "COM2", "COM3", "LPT1"]:
            self._porta_combo.addItem(p)

        self._porta_combo.blockSignals(False)

        target = porta_attuale or self._config.get("porta_stampante", "USB")
        idx = self._porta_combo.findText(target)
        if idx >= 0:
            self._porta_combo.setCurrentIndex(idx)

    def _update_sys_info(self):
        parts = []
        if HAS_PSUTIL:
            try:
                batt = psutil.sensors_battery()
                if batt:
                    pct = int(batt.percent)
                    charging = " (in carica)" if batt.power_plugged else ""
                    parts.append(f"Batteria: {pct}%{charging}")
                else:
                    parts.append("Batteria: N/A")
            except Exception:
                parts.append("Batteria: N/A")
            try:
                net = psutil.net_if_stats()
                connected = any(s.isup for s in net.values())
                parts.append(f"Rete: {'Connessa' if connected else 'Non connessa'}")
            except Exception:
                parts.append("Rete: N/A")
        else:
            parts.append("Batteria: N/A")
            parts.append("Rete: N/A")
        self._sys_lbl.setText("  |  ".join(parts))

    def _test_stampa(self):
        testo = genera_scontrino(
            self._config,
            [{"nome": "Articolo Test", "prezzo": 1.00, "quantita": 1}],
            1.00, 1.00, 0.00, numero=0,
        )
        porta = self._porta_combo.currentText()
        ok, err = stampa_termico(testo, porta)
        if not ok:
            from ui.scontrino_dialog import ScontrinoDialog
            dlg = ScontrinoDialog(testo, self, porta=porta)
            dlg.exec()

    def _backup_db(self):
        from core.database import DB_PATH
        dest, _ = QFileDialog.getSaveFileName(
            self, "Salva backup database", "cashy_backup.db", "SQLite DB (*.db)"
        )
        if dest:
            try:
                shutil.copy2(str(DB_PATH), dest)
                QMessageBox.information(
                    self, "Backup completato", f"Database copiato in:\n{dest}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Errore", f"Errore durante il backup:\n{e}")

    def _salva(self):
        self._config["nome_evento"] = self._nome_input.text().strip()
        self._config["data_evento"] = self._data_input.text().strip()
        self._config["orario_evento"] = self._orario_input.text().strip()
        self._config["messaggio_scontrino"] = self._messaggio_input.text().strip()
        self._config["porta_stampante"] = self._porta_combo.currentText()

        new_theme = self._tema_combo.currentData()
        theme_changed = new_theme != self._config.get("theme", "dark")
        self._config["theme"] = new_theme

        config_path = get_app_dir() / "config.json"
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            QMessageBox.critical(
                self, "Errore", f"Errore nel salvataggio delle impostazioni:\n{e}"
            )
            return

        self.impostazioni_salvate.emit(dict(self._config))
        self.accept()

        if theme_changed:
            QMessageBox.information(
                self.parent(), "Tema modificato",
                "Riavvia Cashy per applicare il nuovo tema."
            )
