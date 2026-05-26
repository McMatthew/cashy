_C_DARK: dict = {
    "background":                "#0b1326",
    "surface":                   "#0b1326",
    "surface_container_lowest":  "#080f1e",
    "surface_container_low":     "#0f1a2e",
    "surface_container":         "#131f35",
    "surface_container_high":    "#182440",
    "surface_container_highest": "#1e2b4a",
    "surface_bright":            "#2a3a5a",
    "on_surface":                "#e2e8f0",
    "on_surface_variant":        "#94a3b8",
    "outline":                   "#334155",
    "outline_variant":           "#1e3a5f",
    "border_secondary":          "#3c4a42",
    "primary":                   "#10B981",
    "on_primary":                "#0b1326",
    "primary_container":         "#0d3d2a",
    "on_primary_container":      "#a7f3d0",
    "primary_hover":             "#6ee7b7",
    "primary_pressed":           "#34d399",
    "secondary":                 "#60a5fa",
    "on_secondary":              "#0b1326",
    "error":                     "#f87171",
    "error_container":           "#3d1515",
    "on_background":             "#e2e8f0",
    "rgba_secondary_hover":      "rgba(96, 165, 250, 0.12)",
    "rgba_secondary_pressed":    "rgba(96, 165, 250, 0.2)",
    "rgba_error_hover":          "rgba(248, 113, 113, 0.12)",
    "rgba_overlay":              "rgba(255, 255, 255, 0.06)",
}

_C_LIGHT: dict = {
    "background":                "#F8FAFC",
    "surface":                   "#F8FAFC",
    "surface_container_lowest":  "#F1F5F9",
    "surface_container_low":     "#E2E8F0",
    "surface_container":         "#E2E8F0",
    "surface_container_high":    "#CBD5E1",
    "surface_container_highest": "#B8C4CE",
    "surface_bright":            "#94A3B8",
    "on_surface":                "#0F172A",
    "on_surface_variant":        "#475569",
    "outline":                   "#94A3B8",
    "outline_variant":           "#CBD5E1",
    "border_secondary":          "#CBD5E1",
    "primary":                   "#10B981",
    "on_primary":                "#0F172A",
    "primary_container":         "#D1FAE5",
    "on_primary_container":      "#065F46",
    "primary_hover":             "#059669",
    "primary_pressed":           "#047857",
    "secondary":                 "#2563EB",
    "on_secondary":              "#FFFFFF",
    "error":                     "#DC2626",
    "error_container":           "#FEE2E2",
    "on_background":             "#0F172A",
    "rgba_secondary_hover":      "rgba(37, 99, 235, 0.10)",
    "rgba_secondary_pressed":    "rgba(37, 99, 235, 0.18)",
    "rgba_error_hover":          "rgba(220, 38, 38, 0.10)",
    "rgba_overlay":              "rgba(0, 0, 0, 0.06)",
}

# C is always the same dict object — mutated by set_theme() so all
# modules that imported it see the updated values at widget-build time.
C: dict = {}
GLOBAL_STYLESHEET: str = ""
THEME_MODE: str = "dark"


def _build_stylesheet(t: dict) -> str:
    return f"""
/* ── Base ─────────────────────────────────────────────────────── */
QMainWindow, QDialog {{
    background-color: {t['background']};
    color: {t['on_surface']};
    font-family: "Oxanium", "Segoe UI", sans-serif;
    font-size: 10pt;
}}

QWidget {{
    background-color: transparent;
    color: {t['on_surface']};
    font-family: "Oxanium", "Segoe UI", sans-serif;
    font-size: 10pt;
}}

/* ── Labels ───────────────────────────────────────────────────── */
QLabel {{
    background-color: transparent;
    color: {t['on_surface']};
    padding: 0px;
}}

/* ── Buttons ──────────────────────────────────────────────────── */
QPushButton {{
    background-color: {t['surface_container_high']};
    color: {t['on_surface']};
    border: 1px solid {t['border_secondary']};
    border-radius: 8px;
    padding: 8px 16px;
    min-height: 36px;
    min-width: 64px;
    font-size: 10pt;
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {t['surface_bright']};
    border-color: {t['outline']};
}}

QPushButton:pressed {{
    background-color: {t['surface_container_lowest']};
}}

QPushButton:disabled {{
    background-color: {t['surface_container_low']};
    color: {t['on_surface_variant']};
    border-color: {t['surface_container_high']};
}}

/* Primary button */
QPushButton#btn_primary {{
    background-color: {t['primary']};
    color: {t['on_primary']};
    border: none;
    border-radius: 8px;
    padding: 10px 24px;
    min-height: 48px;
    font-size: 11pt;
    font-weight: 700;
}}

QPushButton#btn_primary:hover {{
    background-color: {t['primary_hover']};
}}

QPushButton#btn_primary:pressed {{
    background-color: {t['primary_pressed']};
}}

QPushButton#btn_primary:disabled {{
    background-color: {t['primary_container']};
    color: {t['on_primary_container']};
}}

/* Secondary button */
QPushButton#btn_secondary {{
    background-color: transparent;
    color: {t['secondary']};
    border: 1px solid {t['border_secondary']};
    border-radius: 8px;
    padding: 10px 24px;
    min-height: 48px;
    font-size: 10pt;
    font-weight: 600;
}}

QPushButton#btn_secondary:hover {{
    background-color: {t['rgba_secondary_hover']};
}}

QPushButton#btn_secondary:pressed {{
    background-color: {t['rgba_secondary_pressed']};
}}

/* Danger button */
QPushButton#btn_danger {{
    background-color: transparent;
    color: {t['error']};
    border: 1px solid {t['error']};
    border-radius: 8px;
    padding: 8px 16px;
    min-height: 36px;
    font-weight: 600;
}}

QPushButton#btn_danger:hover {{
    background-color: {t['rgba_error_hover']};
}}

/* Flat button */
QPushButton#btn_flat {{
    background-color: transparent;
    color: {t['on_surface_variant']};
    border: none;
    padding: 6px 12px;
    min-height: 32px;
    font-weight: 500;
}}

QPushButton#btn_flat:hover {{
    color: {t['on_surface']};
    background-color: {t['rgba_overlay']};
    border-radius: 6px;
}}

/* ── Inputs ───────────────────────────────────────────────────── */
QLineEdit, QDoubleSpinBox, QSpinBox {{
    background-color: {t['surface_container_high']};
    color: {t['on_surface']};
    border: 1px solid {t['border_secondary']};
    border-radius: 8px;
    padding: 6px 10px;
    min-height: 36px;
    selection-background-color: {t['primary_container']};
    selection-color: {t['on_primary_container']};
}}

QLineEdit:focus, QDoubleSpinBox:focus, QSpinBox:focus {{
    border: 2px solid {t['primary']};
    padding: 5px 9px;
}}

QLineEdit:read-only {{
    background-color: {t['surface_container']};
    color: {t['on_surface_variant']};
}}

QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {t['surface_container_highest']};
    border: none;
    border-radius: 4px;
    width: 20px;
}}

QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover,
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {t['surface_bright']};
}}

/* ── ComboBox ─────────────────────────────────────────────────── */
QComboBox {{
    background-color: {t['surface_container_high']};
    color: {t['on_surface']};
    border: 1px solid {t['border_secondary']};
    border-radius: 8px;
    padding: 6px 10px;
    min-height: 36px;
}}

QComboBox:focus {{
    border: 2px solid {t['primary']};
}}

QComboBox::drop-down {{
    border: none;
    width: 24px;
}}

QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {t['on_surface_variant']};
    width: 0;
    height: 0;
}}

QComboBox QAbstractItemView {{
    background-color: {t['surface_container_highest']};
    color: {t['on_surface']};
    border: 1px solid {t['outline']};
    border-radius: 8px;
    selection-background-color: {t['primary_container']};
    selection-color: {t['on_primary_container']};
    outline: none;
}}

/* ── TableWidget ──────────────────────────────────────────────── */
QTableWidget {{
    background-color: {t['surface_container']};
    color: {t['on_surface']};
    border: 1px solid {t['border_secondary']};
    border-radius: 8px;
    gridline-color: {t['border_secondary']};
    outline: none;
}}

QTableWidget::item {{
    padding: 6px 8px;
    border: none;
}}

QTableWidget::item:selected {{
    background-color: {t['primary_container']};
    color: {t['on_primary_container']};
}}

QHeaderView {{
    background-color: transparent;
}}

QHeaderView::section {{
    background-color: {t['surface_container_highest']};
    color: {t['on_surface_variant']};
    border: none;
    border-bottom: 1px solid {t['border_secondary']};
    padding: 8px;
    font-weight: 600;
    font-size: 9pt;
    text-transform: uppercase;
}}

QTableWidget QTableCornerButton::section {{
    background-color: {t['surface_container_highest']};
    border: none;
}}

/* ── ScrollBar ────────────────────────────────────────────────── */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
}}

QScrollBar::handle:vertical {{
    background: {t['outline']};
    border-radius: 3px;
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background: {t['on_surface_variant']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
    background: none;
}}

QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 0;
}}

QScrollBar::handle:horizontal {{
    background: {t['outline']};
    border-radius: 3px;
    min-width: 24px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {t['on_surface_variant']};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0;
    background: none;
}}

/* ── StatusBar ────────────────────────────────────────────────── */
QStatusBar {{
    background-color: {t['surface_container_lowest']};
    color: {t['on_surface_variant']};
    border-top: 1px solid {t['border_secondary']};
    font-size: 9pt;
}}

QStatusBar::item {{
    border: none;
}}

/* ── MenuBar ──────────────────────────────────────────────────── */
QMenuBar {{
    background-color: {t['surface_container_lowest']};
    color: {t['on_surface']};
    border-bottom: 1px solid {t['border_secondary']};
    padding: 2px 4px;
}}

QMenuBar::item {{
    background: transparent;
    padding: 4px 12px;
    border-radius: 4px;
}}

QMenuBar::item:selected, QMenuBar::item:pressed {{
    background-color: {t['surface_container_high']};
}}

QMenu {{
    background-color: {t['surface_container_highest']};
    color: {t['on_surface']};
    border: 1px solid {t['border_secondary']};
    border-radius: 8px;
    padding: 4px;
}}

QMenu::item {{
    padding: 8px 24px 8px 12px;
    border-radius: 4px;
}}

QMenu::item:selected {{
    background-color: {t['primary_container']};
    color: {t['on_primary_container']};
}}

QMenu::separator {{
    height: 1px;
    background: {t['border_secondary']};
    margin: 4px 8px;
}}

/* ── MessageBox ───────────────────────────────────────────────── */
QMessageBox {{
    background-color: {t['surface_container']};
    color: {t['on_surface']};
}}

QMessageBox QLabel {{
    color: {t['on_surface']};
    font-size: 10pt;
}}

QMessageBox QPushButton {{
    min-width: 80px;
}}

/* ── Splitter ─────────────────────────────────────────────────── */
QSplitter::handle {{
    background-color: {t['border_secondary']};
}}

QSplitter::handle:horizontal {{
    width: 1px;
}}

/* ── ScrollArea ───────────────────────────────────────────────── */
QScrollArea {{
    background-color: transparent;
    border: none;
}}

/* ── TextEdit ─────────────────────────────────────────────────── */
QTextEdit {{
    background-color: {t['surface_container_high']};
    color: {t['on_surface']};
    border: 1px solid {t['border_secondary']};
    border-radius: 8px;
    padding: 8px;
}}

QTextEdit:focus {{
    border: 2px solid {t['primary']};
}}

/* ── TabWidget ────────────────────────────────────────────────────── */
QTabWidget::pane {{
    border: 1px solid {t['border_secondary']};
    border-radius: 0px 8px 8px 8px;
    background-color: transparent;
}}

QTabBar::tab {{
    background-color: {t['surface_container_high']};
    color: {t['on_surface_variant']};
    border: 1px solid {t['border_secondary']};
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 6px 20px;
    margin-right: 2px;
    font-weight: 500;
    min-width: 80px;
}}

QTabBar::tab:selected {{
    background-color: {t['primary']};
    color: {t['on_primary']};
    border-color: {t['primary']};
    font-weight: 700;
}}

QTabBar::tab:hover:!selected {{
    background-color: {t['surface_bright']};
    color: {t['on_surface']};
}}

/* ── CheckBox ─────────────────────────────────────────────────────── */
QCheckBox {{
    color: {t['on_surface']};
    spacing: 8px;
    background: transparent;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid {t['outline']};
    border-radius: 4px;
    background-color: {t['surface_container_high']};
}}

QCheckBox::indicator:checked {{
    background-color: {t['primary']};
    border-color: {t['primary']};
}}

QCheckBox::indicator:hover {{
    border-color: {t['primary']};
}}
"""


def set_theme(mode: str = "dark") -> None:
    """Populate C and rebuild GLOBAL_STYLESHEET for the given mode.

    Must be called before any widget is constructed.
    """
    global GLOBAL_STYLESHEET, THEME_MODE
    THEME_MODE = "light" if mode == "light" else "dark"
    tokens = _C_LIGHT if mode == "light" else _C_DARK
    C.clear()
    C.update(tokens)
    GLOBAL_STYLESHEET = _build_stylesheet(C)


# Initialize with dark theme so importing C always yields a populated dict.
set_theme("dark")
