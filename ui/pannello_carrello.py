from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QLineEdit, QSizePolicy, QMessageBox
)

from core.database import DatabaseManager
from core.receipt import (
    genera_scontrino, genera_scontrino_categoria,
    stampa_termico, stampa_multiplo,
)
from ui.theme import C


class _CartRow(QWidget):
    qty_dec = pyqtSignal(int)
    qty_inc = pyqtSignal(int)
    rimuovi = pyqtSignal(int)

    def __init__(self, prodotto_id: int, nome: str, prezzo: float, quantita: int, parent=None):
        super().__init__(parent)
        self._pid = prodotto_id
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {C['surface_container_high']};
                border-radius: 8px;
                max-height: 80px
            }}
        """)

        # Outer layout: no margins so the delete button can fill full height
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(1)

        # ── Content area (left) ──────────────────────────────────────
        content_w = QWidget()
        content_w.setStyleSheet("background: transparent")
        layout = QHBoxLayout(content_w)
        layout.setContentsMargins(10, 6, 6, 6)
        layout.setSpacing(2)

        # Name
        self._nome_lbl = QLabel(nome)
        self._nome_lbl.setStyleSheet(
            f"color: {C['on_surface']}; font-size: 9pt; font-weight: 600; background: transparent;")
        self._nome_lbl.setFixedWidth(110)
        self._nome_lbl.setWordWrap(False)
        self._nome_lbl.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        layout.addWidget(self._nome_lbl)

        # Dec button
        btn_dec = QPushButton("−")
        btn_dec.setFixedSize(28, 28)
        btn_dec.setStyleSheet(self._stepper_style())
        btn_dec.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_dec.clicked.connect(lambda: self.qty_dec.emit(self._pid))
        layout.addWidget(btn_dec)

        # Qty label
        self._qty_lbl = QLabel(str(quantita))
        self._qty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qty_lbl.setFixedWidth(28)
        self._qty_lbl.setStyleSheet(f"color: {C['on_surface']}; font-weight: 700; background: transparent;")
        layout.addWidget(self._qty_lbl)

        # Inc button
        btn_inc = QPushButton("+")
        btn_inc.setFixedSize(28, 28)
        btn_inc.setStyleSheet(self._stepper_style())
        btn_inc.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_inc.clicked.connect(lambda: self.qty_inc.emit(self._pid))
        layout.addWidget(btn_inc)

        layout.addStretch()

        # Price
        totale = prezzo * quantita
        prezzo_str = f"€{totale:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        self._price_lbl = QLabel(prezzo_str)
        self._price_lbl.setStyleSheet(
            f"color: {C['primary']}; font-weight: 700; font-size: 10pt; background: transparent;")
        self._price_lbl.setFixedWidth(70)
        self._price_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._price_lbl)

        outer.addWidget(content_w, stretch=1)

        # ── Remove button — full-height flush right ──────────────────
        btn_rm = QPushButton("×")
        btn_rm.setFixedWidth(38)
        btn_rm.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        btn_rm.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C['error']};
                border: none;
                border-left: 1px solid {C['border_secondary']};
                border-top-right-radius: 8px;
                border-bottom-right-radius: 8px;
                font-size: 15pt;
                font-weight: 700;
                min-height: 0px;
                max-height: 9999px;
            }}
            QPushButton:hover {{ background: rgba(248,113,113,0.20); }}
            QPushButton:pressed {{ background: rgba(248,113,113,0.35); }}
        """)
        btn_rm.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_rm.clicked.connect(lambda: self.rimuovi.emit(self._pid))
        outer.addWidget(btn_rm)

    def _stepper_style(self):
        return f"""
            QPushButton {{
                background-color: {C['surface_container_highest']};
                color: {C['on_surface']};
                border: 1px solid {C['border_secondary']};
                border-radius: 6px;
                font-size: 14pt;
                font-weight: 700;
                padding: 0;
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
            }}
            QPushButton:hover {{ background-color: {C['surface_bright']}; }}
        """

    def update_qty(self, quantita: int, prezzo: float):
        self._qty_lbl.setText(str(quantita))
        totale = prezzo * quantita
        prezzo_str = f"€{totale:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        self._price_lbl.setText(prezzo_str)


class PannelloCarrello(QWidget):
    ordine_completato = pyqtSignal(int)

    def __init__(self, db: DatabaseManager, config: dict, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._db = db
        self._config = config
        self._cart: dict = {}  # prodotto_id -> {id, nome, prezzo, quantita}
        self._row_widgets: dict = {}  # prodotto_id -> _CartRow

        self.setStyleSheet(f"background-color: {C['surface_container']}; border-radius: 0px;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── Header ──────────────────────────────────────────────────
        header_frame = QFrame()
        header_frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        header_frame.setStyleSheet(
            f"background-color: {C['surface_container_high']}; border-bottom: 1px solid {C['border_secondary']};")
        header_frame.setFixedHeight(52)
        hdr_layout = QHBoxLayout(header_frame)
        hdr_layout.setContentsMargins(16, 0, 8, 0)

        title_lbl = QLabel("Ordine Corrente")
        title_lbl.setStyleSheet(
            f"font-size: 12pt; font-weight: 700; color: {C['on_surface']}; background: transparent; border: none")
        hdr_layout.addWidget(title_lbl)
        hdr_layout.addStretch()

        self._btn_svuota = QPushButton("Svuota")
        self._btn_svuota.setObjectName("btn_flat")
        self._btn_svuota.setStyleSheet(f"border: none")
        self._btn_svuota.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_svuota.clicked.connect(self._svuota)
        hdr_layout.addWidget(self._btn_svuota)

        main_layout.addWidget(header_frame)

        # ── Cart scroll area ─────────────────────────────────────────
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._cart_container = QWidget()
        self._cart_container.setStyleSheet("background: transparent;")
        self._cart_layout = QVBoxLayout(self._cart_container)
        self._cart_layout.setContentsMargins(12, 12, 12, 12)
        self._cart_layout.setSpacing(8)
        self._cart_layout.addStretch()

        self._empty_lbl = QLabel("Nessun articolo nel carrello")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setStyleSheet(f"color: {C['on_surface_variant']}; font-size: 10pt; background: transparent;")
        self._cart_layout.insertWidget(0, self._empty_lbl)

        self._scroll.setWidget(self._cart_container)
        main_layout.addWidget(self._scroll, stretch=1)

        # ── Bottom panel ─────────────────────────────────────────────
        bottom = QFrame()
        bottom.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        bottom.setStyleSheet(f"""
            QFrame {{
                background-color: {C['surface_container_high']};
                border-top: 1px solid {C['border_secondary']};
            }}
        """)
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(16, 12, 16, 12)
        bottom_layout.setSpacing(8)

        # Total
        tot_row = QHBoxLayout()
        tot_lbl = QLabel("TOTALE")
        tot_lbl.setStyleSheet(
            f"color: {C['on_surface']}; font-size: 13pt; font-weight: 700; background: transparent; border: none")
        self._tot_val = QLabel("€0,00")
        self._tot_val.setStyleSheet(
            f"color: {C['primary']}; font-size: 24pt; font-weight: 700; background: transparent; border: none")
        self._tot_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        tot_row.addWidget(tot_lbl)
        tot_row.addStretch()
        tot_row.addWidget(self._tot_val)
        bottom_layout.addLayout(tot_row)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {C['border_secondary']};")
        sep.setFixedHeight(1)
        bottom_layout.addWidget(sep)

        # Received input row
        ric_row = QHBoxLayout()
        ric_lbl = QLabel("Ricevuto")
        ric_lbl.setStyleSheet(
            f"color: {C['on_surface_variant']}; font-size: 9pt; background: transparent; border: none;")
        ric_row.addWidget(ric_lbl)
        ric_row.addStretch()
        self._ricevuto_input = QLineEdit()
        self._ricevuto_input.setPlaceholderText("0,00")
        self._ricevuto_input.setFixedWidth(90)
        self._ricevuto_input.setAlignment(Qt.AlignmentFlag.AlignRight)
        self._ricevuto_input.textChanged.connect(self._calc_resto)
        ric_row.addWidget(self._ricevuto_input)
        btn_clear = QPushButton("×")
        btn_clear.setFixedSize(26, 26)
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {C['on_surface_variant']};
                border: none;
                font-size: 14pt;
                font-weight: 700;
                padding: 0;
            }}
            QPushButton:hover {{ color: {C['error']}; }}
        """)
        btn_clear.clicked.connect(self._ricevuto_input.clear)
        ric_row.addWidget(btn_clear)
        bottom_layout.addLayout(ric_row)

        quick_btn_style = f"""
            QPushButton {{
                background-color: {C['surface_container_highest']};
                color: {C['on_surface']};
                border: 1px solid {C['border_secondary']};
                border-radius: 6px;
                font-size: 9pt;
                font-weight: 600;
                padding: 2px 4px;
            }}
            QPushButton:hover {{ background-color: {C['surface_bright']}; }}
        """

        # Quick amount buttons — large denominations
        quick_row = QHBoxLayout()
        for amount in [5, 10, 20, 50]:
            btn = QPushButton(f"€{amount}")
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(quick_btn_style)
            btn.clicked.connect(lambda checked, a=amount: self._set_ricevuto(a))
            quick_row.addWidget(btn)
        bottom_layout.addLayout(quick_row)

        # Quick amount buttons — small denominations
        quick_row2 = QHBoxLayout()
        for amount, label in [(0.10, "€0,10"), (0.20, "€0,20"), (0.50, "€0,50"), (1, "€1"), (2, "€2")]:
            btn = QPushButton(label)
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet(quick_btn_style)
            btn.clicked.connect(lambda checked, a=amount: self._set_ricevuto(a))
            quick_row2.addWidget(btn)
        bottom_layout.addLayout(quick_row2)

        # Resto row
        resto_row = QHBoxLayout()
        resto_lbl = QLabel("RESTO")
        resto_lbl.setStyleSheet(
            f"color: {C['on_surface']}; font-size: 11pt; font-weight: 600; background: transparent; border: none")
        self._resto_val = QLabel("—")
        self._resto_val.setStyleSheet(
            f"color: {C['on_surface_variant']}; font-size: 14pt; font-weight: 700; background: transparent; border: none")
        self._resto_val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        resto_row.addWidget(resto_lbl)
        resto_row.addStretch()
        resto_row.addWidget(self._resto_val)
        bottom_layout.addLayout(resto_row)

        # Action buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._btn_incassa = QPushButton("Stampa && Incassa")
        self._btn_incassa.setObjectName("btn_primary")
        self._btn_incassa.setStyleSheet(f"""background-color: {C['primary']}; border-radius: 8px""")
        self._btn_incassa.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_incassa.clicked.connect(self._incassa)
        btn_row.addWidget(self._btn_incassa)

        self._btn_no_stampa = QPushButton("Non stampare")
        self._btn_no_stampa.setObjectName("btn_secondary")
        self._btn_no_stampa.setStyleSheet(f"""border-radius: 8px""")
        self._btn_no_stampa.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_no_stampa.clicked.connect(self._incassa_no_stampa)
        btn_row.addWidget(self._btn_no_stampa)

        bottom_layout.addLayout(btn_row)
        main_layout.addWidget(bottom)

    # ── Public methods ───────────────────────────────────────────────

    def aggiungi_prodotto(self, prodotto: dict):
        pid = prodotto["id"]
        if pid in self._cart:
            self._cart[pid]["quantita"] += 1
            row_widget = self._row_widgets.get(pid)
            if row_widget:
                row_widget.update_qty(self._cart[pid]["quantita"], self._cart[pid]["prezzo"])
        else:
            self._cart[pid] = {
                "id": prodotto["id"],
                "nome": prodotto["nome"],
                "prezzo": prodotto["prezzo"],
                "quantita": 1,
                "categoria": prodotto.get("categoria", ""),
            }
            row_widget = _CartRow(pid, prodotto["nome"], prodotto["prezzo"], 1, self)
            row_widget.qty_dec.connect(self._dec_qty)
            row_widget.qty_inc.connect(self._inc_qty)
            row_widget.rimuovi.connect(self._rimuovi_riga)
            self._row_widgets[pid] = row_widget
            # Insert before the stretch at the end
            idx = self._cart_layout.count() - 1
            self._cart_layout.insertWidget(idx, row_widget)
            self._empty_lbl.setVisible(False)
        self._aggiorna_totali()

    def aggiorna_config(self, config: dict):
        self._config = config

    # ── Private helpers ──────────────────────────────────────────────

    def _dec_qty(self, pid: int):
        if pid not in self._cart:
            return
        self._cart[pid]["quantita"] -= 1
        if self._cart[pid]["quantita"] <= 0:
            self._rimuovi_riga(pid)
        else:
            self._row_widgets[pid].update_qty(self._cart[pid]["quantita"], self._cart[pid]["prezzo"])
            self._aggiorna_totali()

    def _inc_qty(self, pid: int):
        if pid not in self._cart:
            return
        self._cart[pid]["quantita"] += 1
        self._row_widgets[pid].update_qty(self._cart[pid]["quantita"], self._cart[pid]["prezzo"])
        self._aggiorna_totali()

    def _rimuovi_riga(self, pid: int):
        if pid not in self._cart:
            return
        del self._cart[pid]
        widget = self._row_widgets.pop(pid, None)
        if widget:
            self._cart_layout.removeWidget(widget)
            widget.deleteLater()
        if not self._cart:
            self._empty_lbl.setVisible(True)
        self._aggiorna_totali()

    def _aggiorna_totali(self):
        totale = sum(r["prezzo"] * r["quantita"] for r in self._cart.values())
        totale_str = f"€{totale:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        self._tot_val.setText(totale_str)
        self._calc_resto()

    def _fmt_price(self, value: float) -> str:
        return f"€{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    def _get_totale(self) -> float:
        return sum(r["prezzo"] * r["quantita"] for r in self._cart.values())

    def _get_ricevuto(self) -> float:
        text = self._ricevuto_input.text().replace(",", ".").strip()
        try:
            return float(text)
        except ValueError:
            return 0.0

    def _calc_resto(self):
        totale = self._get_totale()
        ricevuto = self._get_ricevuto()
        resto = ricevuto - totale
        if ricevuto == 0.0 and totale == 0.0:
            self._resto_val.setText("—")
            self._resto_val.setStyleSheet(
                f"color: {C['on_surface_variant']}; font-size: 14pt; font-weight: 700; background: transparent; border: none")
            return
        if ricevuto >= totale:
            self._resto_val.setText(self._fmt_price(resto))
            self._resto_val.setStyleSheet(
                f"color: {C['primary']}; font-size: 14pt; font-weight: 700; background: transparent; border: none")
        else:
            mancante = totale - ricevuto
            self._resto_val.setText(f"-{self._fmt_price(mancante)}")
            self._resto_val.setStyleSheet(
                f"color: {C['error']}; font-size: 14pt; font-weight: 700; background: transparent; border: none")

    def _set_ricevuto(self, amount: float):
        self._ricevuto_input.setText(
            f"{self._get_ricevuto() + amount:.2f}".replace(".", ",")
        )

    def _svuota(self):
        if not self._cart:
            return
        msg = QMessageBox(self)
        msg.setWindowTitle("Svuota carrello")
        msg.setText("Svuotare il carrello?")
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        if msg.exec() == QMessageBox.StandardButton.Yes:
            self._clear_cart()

    def _clear_cart(self):
        pids = list(self._cart.keys())
        for pid in pids:
            self._rimuovi_riga(pid)
        self._ricevuto_input.clear()
        self._resto_val.setText("—")
        self._resto_val.setStyleSheet(
            f"color: {C['on_surface_variant']}; font-size: 14pt; font-weight: 700; background: transparent;")
        self._aggiorna_totali()

    def _validate_order(self) -> bool:
        if not self._cart:
            QMessageBox.warning(self, "Carrello vuoto", "Aggiungere almeno un prodotto.")
            return False
        totale = self._get_totale()
        ricevuto = self._get_ricevuto()
        if ricevuto < totale:
            QMessageBox.warning(self, "Importo insufficiente", "L'importo ricevuto è inferiore al totale.")
            return False
        return True

    def _save_and_emit(self) -> int:
        righe = list(self._cart.values())
        totale = self._get_totale()
        ricevuto = self._get_ricevuto()
        resto = ricevuto - totale
        ordine_id = self._db.salva_ordine(righe, totale, ricevuto, resto)
        return ordine_id

    def _incassa(self):
        if not self._validate_order():
            return
        righe = list(self._cart.values())
        totale = self._get_totale()
        ricevuto = self._get_ricevuto()
        resto = ricevuto - totale
        numero = self._db.get_next_numero() if self._config.get("numero_progressivo", True) else None
        ordine_id = self._db.salva_ordine(righe, totale, ricevuto, resto)

        # Main receipt (always contains all items + payment)
        testo_principale = genera_scontrino(self._config, righe, totale, ricevuto, resto, numero)

        # Category slips for categories with scontrino_separato=True
        categorie_separate = self._db.get_nomi_categorie_separate()
        slips = []
        for cat in sorted(categorie_separate):
            righe_cat = [r for r in righe if r.get("categoria", "") == cat]
            if righe_cat:
                subtot = sum(r["prezzo"] * r["quantita"] for r in righe_cat)
                slips.append(genera_scontrino_categoria(self._config, cat, righe_cat, subtot))

        all_texts = [testo_principale] + slips
        if len(all_texts) == 1:
            ok, err = stampa_termico(testo_principale, self._config.get("porta_stampante", "USB"), self._config)
        else:
            ok, err = stampa_multiplo(slips, self._config.get("porta_stampante", "USB"), self._config)

        if not ok:
            sep = "\n" + "─" * 32 + "\n"
            combined = sep.join(all_texts)
            porta = self._config.get("porta_stampante", "")
            from ui.scontrino_dialog import ScontrinoDialog
            dlg = ScontrinoDialog(combined, self, porta=porta, config=self._config)
            dlg.exec()

        self._clear_cart()
        self.ordine_completato.emit(ordine_id)

    def _incassa_no_stampa(self):
        if not self._validate_order():
            return
        righe = list(self._cart.values())
        totale = self._get_totale()
        ricevuto = self._get_ricevuto()
        resto = ricevuto - totale
        ordine_id = self._db.salva_ordine(righe, totale, ricevuto, resto)
        self._clear_cart()
        self.ordine_completato.emit(ordine_id)
