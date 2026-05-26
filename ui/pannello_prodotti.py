from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QFrame,
    QGridLayout, QLabel, QPushButton, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QPixmap, QPainter, QPainterPath
from ui.theme import C, THEME_MODE
from core.database import DatabaseManager

_GRID_SPACING = 10
_GRID_COLS = 3


def _darken_color(hex_color: str, factor: float = 0.7) -> str:
    try:
        c = QColor(hex_color)
        h, s, v, a = c.getHsvF()
        v = max(0.0, v * factor)
        c.setHsvF(h, s, v, a)
        return c.name()
    except Exception:
        return hex_color


def _lighten_color(hex_color: str) -> str:
    """Return a light, vibrant pastel version of hex_color for the light theme."""
    try:
        c = QColor(hex_color)
        h, s, l, a = c.getHslF()
        # Boost saturation for vibrancy, push lightness to ~0.82 for a clear pastel.
        s = min(1.0, max(0.45, s * 1.15))
        l = 0.82
        c.setHslF(h, s, l, a)
        return c.name()
    except Exception:
        return hex_color


def _adapt_tile_color(hex_color: str) -> str:
    if THEME_MODE == "light":
        return _lighten_color(hex_color)
    return _darken_color(hex_color, 0.85)


class _ProdottoTile(QFrame):
    clicked = pyqtSignal(dict)

    def __init__(self, prodotto: dict, parent=None):
        super().__init__(parent)
        self._prodotto = prodotto
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName("prodotto_tile")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setMinimumWidth(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        self._bg_color = _adapt_tile_color(prodotto.get("colore", "#1a2a3a"))
        self._apply_style(False)

        # Load photo pixmap (None if absent or invalid)
        self._pixmap: QPixmap | None = None
        foto_path = prodotto.get("foto", "")
        if foto_path:
            px = QPixmap(foto_path)
            if not px.isNull():
                self._pixmap = px

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(4)

        self._nome_label = QLabel(prodotto.get("nome", ""))
        self._nome_label.setWordWrap(True)
        self._nome_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self._nome_label.setStyleSheet(f"""
            QLabel {{
                color: {C['on_surface']};
                font-size: 14pt;
                font-weight: 600;
                background: transparent;
            }}
        """)

        prezzo = prodotto.get("prezzo", 0.0)
        prezzo_str = f"€{prezzo:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        prezzo_color = C['on_primary_container'] if THEME_MODE == "light" else C['primary']
        self._prezzo_label = QLabel(prezzo_str)
        self._prezzo_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignBottom)
        self._prezzo_label.setStyleSheet(f"""
            QLabel {{
                color: {prezzo_color};
                font-size: 13pt;
                font-weight: 700;
                background: transparent;
            }}
        """)

        layout.addWidget(self._nome_label)
        layout.addStretch()
        layout.addWidget(self._prezzo_label)

    def _apply_style(self, hovered: bool):
        border_color = C['primary'] if hovered else C['border_secondary']
        self.setStyleSheet(f"""
            QFrame#prodotto_tile {{
                background-color: {self._bg_color};
                border: 2px solid {border_color};
                border-radius: 10px;
            }}
        """)

    def paintEvent(self, event):
        super().paintEvent(event)
        if self._pixmap:
            painter = QPainter(self)
            painter.setRenderHints(
                QPainter.RenderHint.SmoothPixmapTransform | QPainter.RenderHint.Antialiasing
            )
            path = QPainterPath()
            r = self.rect()
            path.addRoundedRect(float(r.x()), float(r.y()), float(r.width()), float(r.height()), 10.0, 10.0)
            painter.setClipPath(path)
            painter.setOpacity(0.28)
            scaled = self._pixmap.scaled(
                r.size(),
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = (scaled.width() - r.width()) // 2
            y = (scaled.height() - r.height()) // 2
            painter.drawPixmap(-x, -y, scaled)

    def enterEvent(self, event):
        self._apply_style(True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._apply_style(False)
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._prodotto)
        super().mousePressEvent(event)


class PannelloProdotti(QWidget):
    prodotto_selezionato = pyqtSignal(dict)

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self._db = db
        self._categoria_attiva = "Tutti"
        self._tiles: list[_ProdottoTile] = []

        self.setStyleSheet(f"background-color: {C['background']};")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(8)

        # ── Category filter row (compact) ─────────────────────────────
        self._filter_scroll = QScrollArea()
        self._filter_scroll.setFixedHeight(34)
        self._filter_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._filter_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._filter_scroll.setWidgetResizable(True)
        self._filter_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._filter_container = QWidget()
        self._filter_container.setFixedHeight(34)
        self._filter_container.setStyleSheet("background: transparent;")
        self._filter_layout = QHBoxLayout(self._filter_container)
        self._filter_layout.setContentsMargins(0, 2, 0, 2)
        self._filter_layout.setSpacing(6)
        self._filter_layout.addStretch()
        self._filter_scroll.setWidget(self._filter_container)

        main_layout.addWidget(self._filter_scroll)

        # ── Products scroll area ──────────────────────────────────────
        self._products_scroll = QScrollArea()
        self._products_scroll.setWidgetResizable(True)
        self._products_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        self._products_container = QWidget()
        self._products_container.setStyleSheet("background: transparent;")
        self._grid_layout = QGridLayout(self._products_container)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setSpacing(_GRID_SPACING)
        self._products_scroll.setWidget(self._products_container)

        main_layout.addWidget(self._products_scroll)

        self.ricarica_prodotti()
        QTimer.singleShot(0, self._update_tile_heights)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self._update_tile_heights)

    def _tile_height(self) -> int:
        viewport_h = self._products_scroll.viewport().height()
        # 4 rows with 3 gaps must fit exactly: h = (viewport - 3*gap) / 4
        h = (viewport_h - (_GRID_COLS - 1) * _GRID_SPACING) // 4
        return max(72, h)

    def _update_tile_heights(self):
        h = self._tile_height()
        for tile in self._tiles:
            tile.setFixedHeight(h)

    def ricarica_prodotti(self):
        self._rebuild_filters()
        self._rebuild_grid()

    def _rebuild_filters(self):
        while self._filter_layout.count() > 1:
            item = self._filter_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        categorie = ["Tutti"] + self._db.get_categorie()
        self._filter_buttons = {}

        for cat in categorie:
            btn = QPushButton(cat)
            btn.setCheckable(False)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._filter_buttons[cat] = btn
            self._filter_layout.insertWidget(self._filter_layout.count() - 1, btn)
            btn.clicked.connect(lambda checked, c=cat: self._set_categoria(c))

        self._update_filter_styles()

    def _set_categoria(self, categoria: str):
        self._categoria_attiva = categoria
        self._update_filter_styles()
        self._rebuild_grid()

    def _update_filter_styles(self):
        for cat, btn in self._filter_buttons.items():
            if cat == self._categoria_attiva:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {C['primary']};
                        color: {C['on_primary']};
                        border: none;
                        border-radius: 13px;
                        padding: 0px 14px;
                        font-weight: 700;
                        font-size: 8pt;
                        min-height: 26px;
                        max-height: 26px;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {C['surface_container_highest']};
                        color: {C['on_surface_variant']};
                        border: 1px solid {C['border_secondary']};
                        border-radius: 13px;
                        padding: 0px 14px;
                        font-weight: 500;
                        font-size: 8pt;
                        min-height: 26px;
                        max-height: 26px;
                    }}
                    QPushButton:hover {{
                        background-color: {C['surface_bright']};
                        color: {C['on_surface']};
                    }}
                """)

    def _rebuild_grid(self):
        while self._grid_layout.count():
            item = self._grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._tiles.clear()

        prodotti = self._db.get_prodotti_attivi()
        if self._categoria_attiva != "Tutti":
            prodotti = [p for p in prodotti if p["categoria"] == self._categoria_attiva]

        h = self._tile_height()
        for i, prodotto in enumerate(prodotti):
            row = i // _GRID_COLS
            col = i % _GRID_COLS
            tile = _ProdottoTile(prodotto, self)
            tile.setFixedHeight(h)
            tile.clicked.connect(self.prodotto_selezionato)
            self._grid_layout.addWidget(tile, row, col)
            self._tiles.append(tile)

        # Fill remaining columns in last row so tiles don't stretch horizontally
        if prodotti:
            remaining = _GRID_COLS - (len(prodotti) % _GRID_COLS)
            if remaining < _GRID_COLS:
                last_row = (len(prodotti) - 1) // _GRID_COLS
                for col in range(_GRID_COLS - remaining, _GRID_COLS):
                    spacer = QWidget()
                    spacer.setStyleSheet("background: transparent;")
                    self._grid_layout.addWidget(spacer, last_row, col)
