from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox,
    QLineEdit, QDoubleSpinBox, QSpinBox, QComboBox, QColorDialog, QFileDialog,
    QWidget, QSizePolicy, QTabWidget, QCheckBox, QInputDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QColor, QPixmap, QIcon
from ui.theme import C
from core.database import DatabaseManager


class _FormProdotto(QDialog):
    def __init__(self, db: DatabaseManager, prodotto: dict = None, parent=None):
        super().__init__(parent)
        self._db = db
        self._prodotto = prodotto
        self._colore = prodotto["colore"] if prodotto else "#1a2a3a"
        self._foto_path: str = prodotto.get("foto", "") if prodotto else ""
        self.setWindowTitle("Modifica Prodotto" if prodotto else "Nuovo Prodotto")
        self.setMinimumWidth(420)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {C['surface_container']}; color: {C['on_surface']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Modifica Prodotto" if prodotto else "Nuovo Prodotto")
        title.setStyleSheet(f"font-size: 13pt; font-weight: 700; color: {C['on_surface']}; background: transparent;")
        layout.addWidget(title)

        layout.addWidget(self._field_label("Nome"))
        self._nome_input = QLineEdit()
        self._nome_input.setText(prodotto["nome"] if prodotto else "")
        layout.addWidget(self._nome_input)

        layout.addWidget(self._field_label("Prezzo (€)"))
        self._prezzo_input = QDoubleSpinBox()
        self._prezzo_input.setDecimals(2)
        self._prezzo_input.setSingleStep(0.50)
        self._prezzo_input.setMaximum(9999.99)
        self._prezzo_input.setValue(prodotto["prezzo"] if prodotto else 0.0)
        layout.addWidget(self._prezzo_input)

        layout.addWidget(self._field_label("Categoria"))
        self._cat_input = QComboBox()
        self._cat_input.setEditable(True)
        categorie = db.get_categorie()
        for cat in categorie:
            self._cat_input.addItem(cat)
        if prodotto:
            idx = self._cat_input.findText(prodotto["categoria"])
            if idx >= 0:
                self._cat_input.setCurrentIndex(idx)
            else:
                self._cat_input.setCurrentText(prodotto["categoria"])
        layout.addWidget(self._cat_input)

        layout.addWidget(self._field_label("Quantità in magazzino"))
        qm = prodotto.get("quantita_magazzino") if prodotto else None
        qty_row = QHBoxLayout()
        qty_row.setSpacing(10)
        self._traccia_chk = QCheckBox("Traccia quantità")
        self._traccia_chk.setChecked(qm is not None)
        self._traccia_chk.setCursor(Qt.CursorShape.PointingHandCursor)
        self._traccia_chk.toggled.connect(self._toggle_quantita)
        qty_row.addWidget(self._traccia_chk)
        self._qty_input = QSpinBox()
        self._qty_input.setMaximum(999999)
        self._qty_input.setValue(qm if qm is not None else 0)
        self._qty_input.setEnabled(qm is not None)
        qty_row.addWidget(self._qty_input)
        qty_row.addWidget(QLabel("Limite scorta"))
        ls = prodotto.get("limite_scorta") if prodotto else None
        self._limite_input = QSpinBox()
        self._limite_input.setMaximum(999999)
        self._limite_input.setValue(ls if ls is not None else 0)
        self._limite_input.setEnabled(qm is not None)
        qty_row.addWidget(self._limite_input)
        qty_row.addStretch()
        layout.addLayout(qty_row)
        hint_qm = QLabel(
            "Se disattivato, il prodotto è considerato sempre disponibile (scorta illimitata). "
            "Il limite scorta è la giacenza piena: sotto il 20% la quantità viene evidenziata in rosso."
        )
        hint_qm.setWordWrap(True)
        hint_qm.setStyleSheet(f"color: {C['on_surface_variant']}; font-size: 8pt; background: transparent;")
        layout.addWidget(hint_qm)

        layout.addWidget(self._field_label("Colore sfondo"))
        color_row = QHBoxLayout()
        self._btn_colore = QPushButton("Scegli colore")
        self._btn_colore.setFixedHeight(36)
        self._btn_colore.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_colore.clicked.connect(self._pick_color)
        color_row.addWidget(self._btn_colore)
        self._color_preview = QWidget()
        self._color_preview.setFixedSize(36, 36)
        self._color_preview.setStyleSheet(
            f"background-color: {self._colore}; border-radius: 6px; border: 1px solid {C['border_secondary']};"
        )
        color_row.addWidget(self._color_preview)
        color_row.addStretch()
        layout.addLayout(color_row)

        layout.addWidget(self._field_label("Foto prodotto"))
        foto_row = QHBoxLayout()
        foto_row.setSpacing(10)

        self._foto_preview = QLabel()
        self._foto_preview.setFixedSize(64, 64)
        self._foto_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._foto_preview.setStyleSheet(
            f"background-color: {C['surface_container_highest']}; border-radius: 8px;"
            f" border: 1px solid {C['border_secondary']};"
        )
        self._foto_preview.setScaledContents(True)
        foto_row.addWidget(self._foto_preview)

        foto_btn_col = QVBoxLayout()
        foto_btn_col.setSpacing(6)
        btn_foto = QPushButton("Scegli foto…")
        btn_foto.setFixedHeight(34)
        btn_foto.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_foto.clicked.connect(self._pick_foto)
        foto_btn_col.addWidget(btn_foto)

        btn_rm_foto = QPushButton("Rimuovi foto")
        btn_rm_foto.setObjectName("btn_danger")
        btn_rm_foto.setFixedHeight(34)
        btn_rm_foto.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_rm_foto.clicked.connect(self._rimuovi_foto)
        foto_btn_col.addWidget(btn_rm_foto)
        foto_btn_col.addStretch()

        foto_row.addLayout(foto_btn_col)
        foto_row.addStretch()
        layout.addLayout(foto_row)

        self._aggiorna_foto_preview()

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
        layout.addLayout(btn_row)

    def _field_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {C['on_surface_variant']}; font-size: 9pt; font-weight: 600; background: transparent;")
        return lbl

    def _toggle_quantita(self, checked: bool):
        self._qty_input.setEnabled(checked)
        self._limite_input.setEnabled(checked)

    def _pick_color(self):
        color = QColorDialog.getColor(QColor(self._colore), self, "Scegli colore tile")
        if color.isValid():
            self._colore = color.name()
            self._color_preview.setStyleSheet(
                f"background-color: {self._colore}; border-radius: 6px; border: 1px solid {C['border_secondary']};"
            )

    def _pick_foto(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Scegli foto prodotto", "",
            "Immagini (*.png *.jpg *.jpeg *.webp *.bmp *.gif)"
        )
        if path:
            self._foto_path = path
            self._aggiorna_foto_preview()

    def _rimuovi_foto(self):
        self._foto_path = ""
        self._aggiorna_foto_preview()

    def _aggiorna_foto_preview(self):
        if self._foto_path:
            px = QPixmap(self._foto_path)
            if not px.isNull():
                self._foto_preview.setPixmap(px)
                self._foto_preview.setText("")
                return
        self._foto_preview.setPixmap(QPixmap())
        self._foto_preview.setText("—")

    def _salva(self):
        nome = self._nome_input.text().strip()
        if not nome:
            QMessageBox.warning(self, "Errore", "Il nome del prodotto è obbligatorio.")
            return
        prezzo = self._prezzo_input.value()
        categoria = self._cat_input.currentText().strip() or "Altro"
        colore = self._colore
        foto = self._foto_path
        traccia = self._traccia_chk.isChecked()
        quantita_magazzino = self._qty_input.value() if traccia else None
        limite_scorta = (self._limite_input.value() or None) if traccia else None

        if self._prodotto:
            self._db.modifica_prodotto(
                self._prodotto["id"], nome, prezzo, categoria, colore,
                self._prodotto.get("attivo", 1), foto, quantita_magazzino, limite_scorta
            )
        else:
            self._db.aggiungi_prodotto(nome, prezzo, categoria, colore, foto, quantita_magazzino, limite_scorta)

        self.accept()


class GestioneProdotti(QDialog):
    prodotti_modificati = pyqtSignal()

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self._db = db
        self.setWindowTitle("Gestione Prodotti e Categorie")
        self.setMinimumSize(760, 560)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {C['surface_container']}; color: {C['on_surface']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Gestione Prodotti e Categorie")
        title.setStyleSheet(f"font-size: 14pt; font-weight: 700; color: {C['on_surface']}; background: transparent;")
        layout.addWidget(title)

        # ── Tab widget ────────────────────────────────────────────────
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # ── Tab Prodotti ──────────────────────────────────────────────
        tab_prodotti = QWidget()
        tab_prodotti.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        tab_prodotti.setStyleSheet("background: transparent;")
        tp_layout = QVBoxLayout(tab_prodotti)
        tp_layout.setContentsMargins(12, 12, 12, 12)
        tp_layout.setSpacing(10)

        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(["ID", "Nome", "Prezzo", "Categoria", "Foto", "Magazzino", "Attivo"])
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(4, 60)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(False)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(52)
        self._table.setIconSize(QSize(44, 44))
        self._table.doubleClicked.connect(self._modifica)
        tp_layout.addWidget(self._table)

        btn_prodotti = QHBoxLayout()
        btn_prodotti.setSpacing(8)

        btn_add = QPushButton("+ Aggiungi")
        btn_add.setObjectName("btn_primary")
        btn_add.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add.clicked.connect(self._aggiungi)
        btn_prodotti.addWidget(btn_add)

        btn_mod = QPushButton("Modifica")
        btn_mod.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_mod.clicked.connect(self._modifica)
        btn_prodotti.addWidget(btn_mod)

        self._btn_toggle = QPushButton("Disattiva")
        self._btn_toggle.setObjectName("btn_danger")
        self._btn_toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_toggle.clicked.connect(self._toggle_attivo)
        btn_prodotti.addWidget(self._btn_toggle)

        btn_prodotti.addStretch()

        btn_import = QPushButton("Import CSV")
        btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_import.clicked.connect(self._import_csv)
        btn_prodotti.addWidget(btn_import)

        btn_export = QPushButton("Export CSV")
        btn_export.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export.clicked.connect(self._export_csv)
        btn_prodotti.addWidget(btn_export)

        tp_layout.addLayout(btn_prodotti)
        tabs.addTab(tab_prodotti, "Prodotti")

        # ── Tab Categorie ─────────────────────────────────────────────
        tab_categorie = QWidget()
        tab_categorie.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        tab_categorie.setStyleSheet("background: transparent;")
        tc_layout = QVBoxLayout(tab_categorie)
        tc_layout.setContentsMargins(12, 12, 12, 12)
        tc_layout.setSpacing(10)

        hint = QLabel(
            "Attiva 'Scontrino Separato' per stampare una comanda aggiuntiva per quella categoria "
            "(oltre allo scontrino principale che contiene sempre tutti i prodotti)."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet(f"color: {C['on_surface_variant']}; font-size: 9pt; background: transparent;")
        tc_layout.addWidget(hint)

        self._cat_table = QTableWidget()
        self._cat_table.setColumnCount(2)
        self._cat_table.setHorizontalHeaderLabels(["Categoria", "Scontrino Separato"])
        self._cat_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._cat_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self._cat_table.setColumnWidth(1, 160)
        self._cat_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._cat_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._cat_table.verticalHeader().setVisible(False)
        self._cat_table.verticalHeader().setDefaultSectionSize(44)
        tc_layout.addWidget(self._cat_table)

        btn_categorie = QHBoxLayout()
        btn_categorie.setSpacing(8)

        btn_add_cat = QPushButton("+ Aggiungi Categoria")
        btn_add_cat.setObjectName("btn_primary")
        btn_add_cat.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_add_cat.clicked.connect(self._aggiungi_categoria)
        btn_categorie.addWidget(btn_add_cat)

        btn_del_cat = QPushButton("Elimina Categoria")
        btn_del_cat.setObjectName("btn_danger")
        btn_del_cat.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_del_cat.clicked.connect(self._elimina_categoria)
        btn_categorie.addWidget(btn_del_cat)

        btn_categorie.addStretch()
        tc_layout.addLayout(btn_categorie)

        tabs.addTab(tab_categorie, "Categorie")

        # ── Close button ──────────────────────────────────────────────
        btn_close_row = QHBoxLayout()
        btn_close_row.addStretch()
        btn_close = QPushButton("Chiudi")
        btn_close.setObjectName("btn_secondary")
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.clicked.connect(self.accept)
        btn_close_row.addWidget(btn_close)
        layout.addLayout(btn_close_row)

        self._carica_prodotti()
        self._carica_categorie()

    # ── Prodotti ──────────────────────────────────────────────────────

    def _carica_prodotti(self):
        prodotti = self._db.get_prodotti_tutti()
        self._table.setRowCount(len(prodotti))
        self._prodotti = prodotti
        for i, p in enumerate(prodotti):
            self._table.setItem(i, 0, QTableWidgetItem(str(p["id"])))
            self._table.setItem(i, 1, QTableWidgetItem(p["nome"]))
            prezzo_str = f"€{p['prezzo']:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            self._table.setItem(i, 2, QTableWidgetItem(prezzo_str))
            self._table.setItem(i, 3, QTableWidgetItem(p["categoria"]))

            foto_item = QTableWidgetItem()
            foto_path = p.get("foto", "")
            if foto_path:
                px = QPixmap(foto_path)
                if not px.isNull():
                    foto_item.setIcon(QIcon(px))
                else:
                    foto_item.setText("—")
            else:
                foto_item.setText("—")
            foto_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 4, foto_item)

            qm = p.get("quantita_magazzino")
            qm_item = QTableWidgetItem("∞" if qm is None else str(qm))
            qm_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if qm is not None and qm == 0:
                qm_item.setForeground(QColor(C["error"]))
            self._table.setItem(i, 5, qm_item)

            attivo_item = QTableWidgetItem("Sì" if p["attivo"] else "No")
            attivo_item.setForeground(QColor(C["primary"] if p["attivo"] else C["error"]))
            self._table.setItem(i, 6, attivo_item)

            color_item = self._table.item(i, 0)
            if color_item:
                try:
                    color_item.setBackground(QColor(p["colore"]))
                except Exception:
                    pass

    def _get_selected_prodotto(self):
        row = self._table.currentRow()
        if row < 0 or row >= len(self._prodotti):
            return None
        return self._prodotti[row]

    def _aggiungi(self):
        dlg = _FormProdotto(self._db, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._carica_prodotti()
            self._carica_categorie()
            self.prodotti_modificati.emit()

    def _modifica(self):
        prodotto = self._get_selected_prodotto()
        if not prodotto:
            QMessageBox.information(self, "Info", "Selezionare un prodotto.")
            return
        dlg = _FormProdotto(self._db, prodotto, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._carica_prodotti()
            self._carica_categorie()
            self.prodotti_modificati.emit()

    def _toggle_attivo(self):
        prodotto = self._get_selected_prodotto()
        if not prodotto:
            QMessageBox.information(self, "Info", "Selezionare un prodotto.")
            return
        if prodotto["attivo"]:
            self._db.elimina_prodotto(prodotto["id"])
        else:
            self._db.modifica_prodotto(
                prodotto["id"], prodotto["nome"], prodotto["prezzo"],
                prodotto["categoria"], prodotto["colore"], True,
                prodotto.get("foto", ""), prodotto.get("quantita_magazzino"),
                prodotto.get("limite_scorta")
            )
        self._carica_prodotti()
        self.prodotti_modificati.emit()

    def _import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Importa prodotti CSV", "", "CSV Files (*.csv)")
        if path:
            try:
                self._db.import_csv_prodotti(path)
                self._carica_prodotti()
                self._carica_categorie()
                self.prodotti_modificati.emit()
                QMessageBox.information(self, "Importazione completata", "Prodotti importati con successo.")
            except Exception as e:
                QMessageBox.critical(self, "Errore", f"Errore durante l'importazione:\n{e}")

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Esporta prodotti CSV", "prodotti.csv", "CSV Files (*.csv)")
        if path:
            try:
                self._db.export_csv_prodotti(path)
                QMessageBox.information(self, "Esportazione completata", "Prodotti esportati con successo.")
            except Exception as e:
                QMessageBox.critical(self, "Errore", f"Errore durante l'esportazione:\n{e}")

    # ── Categorie ─────────────────────────────────────────────────────

    def _carica_categorie(self):
        categorie = self._db.get_categorie_full()
        self._categorie = categorie
        self._cat_table.setRowCount(len(categorie))
        for i, cat in enumerate(categorie):
            nome_item = QTableWidgetItem(cat["nome"])
            nome_item.setData(Qt.ItemDataRole.UserRole, cat["id"])
            self._cat_table.setItem(i, 0, nome_item)
            self._cat_table.setCellWidget(i, 1, self._make_check_cell(cat["id"], bool(cat["scontrino_separato"])))

    def _make_check_cell(self, cat_id: int, checked: bool) -> QWidget:
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 0, 0, 0)
        h.setAlignment(Qt.AlignmentFlag.AlignCenter)
        cb = QCheckBox()
        cb.setChecked(checked)
        cb.setCursor(Qt.CursorShape.PointingHandCursor)
        cb.toggled.connect(lambda val, cid=cat_id: self._db.set_scontrino_separato(cid, val))
        h.addWidget(cb)
        return w

    def _aggiungi_categoria(self):
        nome, ok = QInputDialog.getText(self, "Nuova Categoria", "Nome categoria:")
        if not ok or not nome.strip():
            return
        nome = nome.strip()
        if not self._db.aggiungi_categoria(nome):
            QMessageBox.warning(self, "Errore", f"La categoria '{nome}' esiste già.")
            return
        self._carica_categorie()

    def _elimina_categoria(self):
        row = self._cat_table.currentRow()
        if row < 0 or row >= len(self._categorie):
            QMessageBox.information(self, "Info", "Selezionare una categoria.")
            return
        cat = self._categorie[row]
        bloccati = self._db.elimina_categoria(cat["id"])
        if bloccati > 0:
            QMessageBox.warning(
                self, "Impossibile eliminare",
                f"La categoria '{cat['nome']}' è usata da {bloccati} prodotto/i attivo/i.\n"
                "Riassegna prima i prodotti a un'altra categoria."
            )
            return
        self._carica_categorie()
