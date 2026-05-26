from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QSizePolicy
)
from PyQt6.QtCore import Qt
from ui.theme import C
from core.database import DatabaseManager


class _Card(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {C['surface_container_high']};
                border-radius: 12px;
            }}
        """)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 14, 16, 14)
        self._layout.setSpacing(0)


class _SectionLabel(QLabel):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QLabel {{
                color: {C['on_surface_variant']};
                font-size: 8pt;
                font-weight: 700;
                letter-spacing: 1px;
                background: transparent;
                line-height: 1.4;
            }}
        """)


class _EventoCard(_Card):
    def __init__(self, config: dict, parent=None):
        super().__init__(parent)
        self._section = _SectionLabel("INFO EVENTO")
        self._layout.addWidget(self._section)


        self._nome_label = QLabel()
        self._nome_label.setStyleSheet(f"""
            QLabel {{
                color: {C['on_surface']};
                font-size: 14pt;
                font-weight: 700;
                background: transparent;
            }}
        """)
        self._nome_label.setWordWrap(True)
        self._layout.addWidget(self._nome_label)

        self._data_label = QLabel()
        self._data_label.setStyleSheet(f"color: {C['on_surface_variant']}; font-size: 10pt; background: transparent;")
        self._layout.addWidget(self._data_label)

        self._orario_label = QLabel()
        self._orario_label.setStyleSheet(
            f"color: {C['primary']}; font-size: 10pt; font-weight: 600; background: transparent;")
        self._layout.addWidget(self._orario_label)

        self._layout.addStretch()
        self.aggiorna(config)

    def aggiorna(self, config: dict):
        nome = config.get("nome_evento", "")
        self._nome_label.setText(f'<span style="line-height: 1.4;">{nome}</span>')
        self._data_label.setText(config.get("data_evento", ""))
        self._orario_label.setText(config.get("orario_evento", ""))


class _UltimoOrdineCard(_Card):
    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self._db = db

        self._section = _SectionLabel("ULTIMA TRANSAZIONE")
        self._layout.addWidget(self._section)

        self._ordine_label = QLabel("—")
        self._ordine_label.setStyleSheet(
            f"color: {C['on_surface']}; font-size: 11pt; font-weight: 600; background: transparent;")
        self._layout.addWidget(self._ordine_label)

        self._totale_label = QLabel()
        self._totale_label.setStyleSheet(
            f"color: {C['primary']}; font-size: 20pt; font-weight: 700; background: transparent;")
        self._layout.addWidget(self._totale_label)

        self._items_label = QLabel()
        self._items_label.setStyleSheet(f"color: {C['on_surface_variant']}; font-size: 9pt; background: transparent;")
        self._items_label.setWordWrap(True)
        self._layout.addWidget(self._items_label)

        self._layout.addStretch()
        self._load_last()

    def _load_last(self):
        ordine = self._db.get_last_order()
        if ordine:
            self._refresh(ordine["id"])
        else:
            self._ordine_label.setText("Nessun ordine")
            self._totale_label.setText("")
            self._items_label.setText("")

    def aggiorna(self, ordine_id: int):
        self._refresh(ordine_id)

    def _refresh(self, ordine_id: int):
        righe = self._db.get_righe_ordine(ordine_id)
        ordine = self._db.get_ordine_by_id(ordine_id)
        if ordine:
            self._ordine_label.setText(f"Ordine #{ordine_id}")
            totale = ordine.get("totale", 0)
            totale_str = f"€{totale:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            self._totale_label.setText(totale_str)
            items_str = ", ".join(
                f"{r['quantita']}x {r['nome_snap']}" for r in righe
            )
            self._items_label.setText(items_str if items_str else "—")


class PannelloInfo(QWidget):
    def __init__(self, db: DatabaseManager, config: dict, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._db = db
        self._config = config

        self.setStyleSheet(f"""
            QWidget {{
                background-color: {C['surface_container']};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        self._evento_card = _EventoCard(config, self)
        self._ordine_card = _UltimoOrdineCard(db, self)

        layout.addWidget(self._evento_card)
        layout.addWidget(self._ordine_card)
        layout.addStretch()

    def aggiorna_config(self, config: dict):
        self._config = config
        self._evento_card.aggiorna(config)

    def aggiorna_ultimo_ordine(self, ordine_id: int):
        self._ordine_card.aggiorna(ordine_id)
