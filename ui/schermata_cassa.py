import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QFrame, QLabel,
    QStatusBar, QSizePolicy
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from ui.theme import C
from ui.pannello_info import PannelloInfo
from ui.pannello_prodotti import PannelloProdotti
from ui.pannello_carrello import PannelloCarrello
from core.database import DatabaseManager

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _make_vsep() -> QFrame:
    """Create a 1px vertical separator."""
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.VLine)
    sep.setFixedWidth(1)
    sep.setStyleSheet(f"background-color: {C['border_secondary']}; border: none;")
    return sep


class SchermataCassa(QMainWindow):
    def __init__(self, config: dict):
        super().__init__()
        self.config = config
        self.db = DatabaseManager()

        self.setWindowTitle("Cashy — Cassa Non Fiscale")
        self.setMinimumSize(1200, 700)

        # ── Panels ───────────────────────────────────────────────────
        self.pannello_info = PannelloInfo(self.db, config, self)
        self.pannello_prodotti = PannelloProdotti(self.db, self)
        self.pannello_carrello = PannelloCarrello(self.db, config, self)

        # ── Central widget ────────────────────────────────────────────
        central = QWidget()
        central.setObjectName("central_widget")
        central.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        central.setStyleSheet(f"background-color: {C['background']};")
        h_layout = QHBoxLayout(central)
        h_layout.setContentsMargins(0, 0, 0, 0)
        h_layout.setSpacing(0)

        h_layout.addWidget(self.pannello_info, stretch=1)
        h_layout.addWidget(_make_vsep())
        h_layout.addWidget(self.pannello_prodotti, stretch=4)
        h_layout.addWidget(_make_vsep())
        h_layout.addWidget(self.pannello_carrello, stretch=2)

        self.setCentralWidget(central)

        # ── Menu bar ──────────────────────────────────────────────────
        self._build_menu()

        # ── Status bar ────────────────────────────────────────────────
        self._build_statusbar()

        # ── Signal connections ────────────────────────────────────────
        self.pannello_prodotti.prodotto_selezionato.connect(
            self.pannello_carrello.aggiungi_prodotto
        )
        self.pannello_carrello.ordine_completato.connect(
            self.pannello_info.aggiorna_ultimo_ordine
        )
        self.pannello_carrello.ordine_completato.connect(
            self._on_ordine_completato
        )
        self.pannello_carrello.ordine_completato.connect(
            lambda _: self.pannello_prodotti.ricarica_prodotti()
        )

        # ── Start maximized ───────────────────────────────────────────
        self.showMaximized()

    def _build_menu(self):
        menubar = self.menuBar()

        # App menu
        app_menu = menubar.addMenu("App")

        act_impostazioni = app_menu.addAction("Impostazioni...")
        act_impostazioni.triggered.connect(self._apri_impostazioni)

        app_menu.addSeparator()

        act_esci = app_menu.addAction("Esci")
        act_esci.triggered.connect(self.close)

        # Prodotti menu
        prodotti_menu = menubar.addMenu("Prodotti")

        act_gestione = prodotti_menu.addAction("Gestione Prodotti...")
        act_gestione.triggered.connect(self._apri_gestione_prodotti)

        act_storico = prodotti_menu.addAction("Storico Ordini...")
        act_storico.triggered.connect(self._apri_storico_ordini)

    def _build_statusbar(self):
        statusbar = self.statusBar()

        # App name (left)
        app_lbl = QLabel("Cashy POS")
        app_lbl.setStyleSheet(f"color: {C['primary']}; font-weight: 700; padding: 0 8px; background: transparent;")
        statusbar.addWidget(app_lbl)

        # Clock label (left, after app name)
        self._clock_lbl = QLabel()
        self._clock_lbl.setStyleSheet(f"color: {C['on_surface_variant']}; padding: 0 8px; background: transparent;")
        statusbar.addWidget(self._clock_lbl)

        # Permanent widget on right: battery
        self._battery_lbl = QLabel()
        self._battery_lbl.setStyleSheet(f"color: {C['on_surface_variant']}; padding: 0 8px; background: transparent;")
        statusbar.addPermanentWidget(self._battery_lbl)

        self._update_clock()
        self._update_battery()

        self._clock_timer = QTimer(self)
        self._clock_timer.setInterval(60000)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start()

        self._battery_timer = QTimer(self)
        self._battery_timer.setInterval(60000)
        self._battery_timer.timeout.connect(self._update_battery)
        self._battery_timer.start()

    def _update_clock(self):
        from datetime import datetime
        now = datetime.now()
        self._clock_lbl.setText(now.strftime("%d/%m/%Y  %H:%M"))

    def _update_battery(self):
        if HAS_PSUTIL:
            try:
                batt = psutil.sensors_battery()
                if batt:
                    pct = int(batt.percent)
                    icon = "🔌" if batt.power_plugged else "🔋"
                    self._battery_lbl.setText(f"{icon} {pct}%")
                    return
            except Exception:
                pass
        self._battery_lbl.setText("")

    def _on_ordine_completato(self, ordine_id: int):
        self.statusBar().showMessage(f"Ordine #{ordine_id} salvato con successo.", 5000)

    def _apri_impostazioni(self):
        from ui.impostazioni import Impostazioni
        dlg = Impostazioni(self.db, self.config, self)
        dlg.impostazioni_salvate.connect(self._on_impostazioni_salvate)
        dlg.exec()

    def _on_impostazioni_salvate(self, new_config: dict):
        self.config = new_config
        self.pannello_info.aggiorna_config(new_config)
        self.pannello_carrello.aggiorna_config(new_config)

    def _apri_gestione_prodotti(self):
        from ui.gestione_prodotti import GestioneProdotti
        dlg = GestioneProdotti(self.db, self)
        dlg.prodotti_modificati.connect(self.pannello_prodotti.ricarica_prodotti)
        dlg.exec()

    def _apri_storico_ordini(self):
        from ui.storico_ordini import StoricoOrdini
        dlg = StoricoOrdini(self.db, self.config, self)
        dlg.exec()
        # Un eventuale annullamento ordine ripristina le scorte: ricarico la griglia.
        self.pannello_prodotti.ricarica_prodotti()
