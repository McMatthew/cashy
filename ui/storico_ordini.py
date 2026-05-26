from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QWidget, QFrame, QFileDialog, QMessageBox, QLineEdit
)
from PyQt6.QtCore import Qt
from ui.theme import C
from ui.scontrino_dialog import ScontrinoDialog
from datetime import datetime
from core.database import DatabaseManager
from core.receipt import genera_scontrino, genera_resoconto, stampa_termico


class StoricoOrdini(QDialog):
    def __init__(self, db: DatabaseManager, config: dict, parent=None):
        super().__init__(parent)
        self._db = db
        self._config = config
        self._ordini = []
        self._ordini_filtrati = []
        self.setWindowTitle("Storico Ordini")
        self.setMinimumSize(900, 580)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {C['surface_container']}; color: {C['on_surface']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Title + search row
        top_row = QHBoxLayout()
        title = QLabel("Storico Ordini")
        title.setStyleSheet(
            f"font-size: 14pt; font-weight: 700; color: {C['on_surface']}; background: transparent;"
        )
        top_row.addWidget(title)
        top_row.addStretch()

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Filtra per data (es. 2026-05)…")
        self._search_input.setFixedWidth(220)
        self._search_input.textChanged.connect(self._applica_filtro)
        top_row.addWidget(self._search_input)

        layout.addLayout(top_row)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setLineWidth(0)

        # Left: orders list
        left_widget = QWidget()
        left_widget.setStyleSheet("background: transparent;")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(8)

        orders_lbl = QLabel("Ordini")
        orders_lbl.setStyleSheet(
            f"color: {C['on_surface_variant']}; font-size: 9pt; font-weight: 700; background: transparent;"
        )
        left_layout.addWidget(orders_lbl)

        self._orders_table = QTableWidget()
        self._orders_table.setColumnCount(3)
        self._orders_table.setHorizontalHeaderLabels(["#", "Data/Ora", "Totale"])
        self._orders_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._orders_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._orders_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._orders_table.verticalHeader().setVisible(False)
        self._orders_table.selectionModel().selectionChanged.connect(self._on_selection)
        left_layout.addWidget(self._orders_table)

        splitter.addWidget(left_widget)

        # Right: detail panel
        right_widget = QWidget()
        right_widget.setStyleSheet("background: transparent;")
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        detail_lbl = QLabel("Dettaglio Ordine")
        detail_lbl.setStyleSheet(
            f"color: {C['on_surface_variant']}; font-size: 9pt; font-weight: 700; background: transparent;"
        )
        right_layout.addWidget(detail_lbl)

        self._detail_table = QTableWidget()
        self._detail_table.setColumnCount(3)
        self._detail_table.setHorizontalHeaderLabels(["Prodotto", "Qtà", "Prezzo"])
        self._detail_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._detail_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._detail_table.verticalHeader().setVisible(False)
        right_layout.addWidget(self._detail_table)

        # Summary
        summary_frame = QFrame()
        summary_frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        summary_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {C['surface_container_high']};
                border: 1px solid {C['border_secondary']};
                border-radius: 8px;
            }}
        """)
        summary_layout = QVBoxLayout(summary_frame)
        summary_layout.setContentsMargins(12, 10, 12, 10)
        summary_layout.setSpacing(4)

        self._tot_lbl = QLabel("Totale: —")
        self._tot_lbl.setStyleSheet(
            f"color: {C['primary']}; font-weight: 700; font-size: 11pt; background: transparent; border: none;"
        )
        self._ric_lbl = QLabel("Ricevuto: —")
        self._ric_lbl.setStyleSheet(f"color: {C['on_surface']}; font-size: 9pt; background: transparent; border: none;")
        self._res_lbl = QLabel("Resto: —")
        self._res_lbl.setStyleSheet(f"color: {C['on_surface']}; font-size: 9pt; background: transparent; border: none;")
        summary_layout.addWidget(self._tot_lbl)
        summary_layout.addWidget(self._ric_lbl)
        summary_layout.addWidget(self._res_lbl)

        right_layout.addWidget(summary_frame)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        layout.addWidget(splitter)

        # Bottom buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_ristampa = QPushButton("Ristampa")
        btn_ristampa.setObjectName("btn_secondary")
        btn_ristampa.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_ristampa.clicked.connect(self._ristampa)
        btn_row.addWidget(btn_ristampa)

        btn_resoconto = QPushButton("Stampa Resoconto")
        btn_resoconto.setObjectName("btn_secondary")
        btn_resoconto.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_resoconto.clicked.connect(self._stampa_resoconto)
        btn_row.addWidget(btn_resoconto)

        btn_export = QPushButton("Export CSV")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.clicked.connect(self._export_csv)
        btn_row.addWidget(btn_export)

        btn_row.addStretch()

        btn_chiudi = QPushButton("Chiudi")
        btn_chiudi.setObjectName("btn_primary")
        btn_chiudi.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_chiudi.clicked.connect(self.accept)
        btn_row.addWidget(btn_chiudi)

        layout.addLayout(btn_row)

        self._carica_ordini()

    def _fmt_price(self, value: float) -> str:
        return f"€{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def _carica_ordini(self):
        self._ordini = self._db.get_ordini()
        self._applica_filtro()

    def _applica_filtro(self):
        query = self._search_input.text().strip().lower()
        if query:
            self._ordini_filtrati = [
                o for o in self._ordini
                if query in o.get("data_ora", "").lower()
            ]
        else:
            self._ordini_filtrati = list(self._ordini)
        self._popola_tabella()

    def _popola_tabella(self):
        self._orders_table.setRowCount(len(self._ordini_filtrati))
        for i, o in enumerate(self._ordini_filtrati):
            self._orders_table.setItem(i, 0, QTableWidgetItem(str(o["id"])))
            self._orders_table.setItem(i, 1, QTableWidgetItem(o.get("data_ora", "")))
            self._orders_table.setItem(i, 2, QTableWidgetItem(self._fmt_price(o["totale"])))
        # Clear detail panel when filter changes
        self._detail_table.setRowCount(0)
        self._tot_lbl.setText("Totale: —")
        self._ric_lbl.setText("Ricevuto: —")
        self._res_lbl.setText("Resto: —")

    def _on_selection(self, selected, deselected):
        row = self._orders_table.currentRow()
        if row < 0 or row >= len(self._ordini_filtrati):
            return
        self._show_detail(self._ordini_filtrati[row])

    def _show_detail(self, ordine: dict):
        righe = self._db.get_righe_ordine(ordine["id"])
        self._detail_table.setRowCount(len(righe))
        for i, r in enumerate(righe):
            self._detail_table.setItem(i, 0, QTableWidgetItem(r["nome_snap"]))
            self._detail_table.setItem(i, 1, QTableWidgetItem(str(r["quantita"])))
            self._detail_table.setItem(
                i, 2, QTableWidgetItem(self._fmt_price(r["prezzo_snap"] * r["quantita"]))
            )
        self._tot_lbl.setText(f"Totale: {self._fmt_price(ordine['totale'])}")
        self._ric_lbl.setText(f"Ricevuto: {self._fmt_price(ordine['ricevuto'])}")
        self._res_lbl.setText(f"Resto: {self._fmt_price(ordine['resto'])}")

    def _ristampa(self):
        row = self._orders_table.currentRow()
        if row < 0 or row >= len(self._ordini_filtrati):
            QMessageBox.information(self, "Info", "Selezionare un ordine.")
            return
        ordine = self._ordini_filtrati[row]
        righe = self._db.get_righe_ordine(ordine["id"])
        righe_fmt = [
            {"nome": r["nome_snap"], "prezzo": r["prezzo_snap"], "quantita": r["quantita"]}
            for r in righe
        ]
        testo = genera_scontrino(
            self._config, righe_fmt,
            ordine["totale"], ordine["ricevuto"], ordine["resto"],
            numero=ordine["id"],
        )
        porta = self._config.get("porta_stampante", "")
        dlg = ScontrinoDialog(testo, self, porta=porta)
        dlg.exec()

    def _stampa_resoconto(self):
        if not self._ordini_filtrati:
            QMessageBox.information(self, "Info", "Nessun ordine da riepilogare.")
            return
        ordine_ids = [o["id"] for o in self._ordini_filtrati]
        righe_aggregate = self._db.get_resoconto_per_ordini(ordine_ids)
        n_ordini = len(self._ordini_filtrati)
        totale = sum(o["totale"] for o in self._ordini_filtrati)

        query = self._search_input.text().strip()
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        data_ora = f"{query} - {now_str}" if query else now_str

        testo = genera_resoconto(self._config, data_ora, righe_aggregate, n_ordini, totale)
        porta = self._config.get("porta_stampante", "")
        ok, _ = stampa_termico(testo, porta)
        if not ok:
            dlg = ScontrinoDialog(testo, self, porta=porta)
            dlg.exec()

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Esporta ordini CSV", "ordini.csv", "CSV Files (*.csv)"
        )
        if path:
            try:
                self._db.export_csv_ordini(path)
                QMessageBox.information(self, "Esportazione completata", "Ordini esportati con successo.")
            except Exception as e:
                QMessageBox.critical(self, "Errore", f"Errore durante l'esportazione:\n{e}")
