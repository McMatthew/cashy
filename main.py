import sys
import json
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QFont, QFontDatabase, QIcon

from core.paths import get_app_dir, get_assets_dir

PROJECT_ROOT = get_app_dir()
CONFIG_PATH = PROJECT_ROOT / "config.json"

DEFAULT_CONFIG = {
    "nome_evento": "Sagra della Birra 2026",
    "data_evento": "13/05/2026",
    "orario_evento": "17:00 - 24:00",
    "messaggio_scontrino": "Grazie e buon divertimento!",
    "porta_stampante": "USB",
    "numero_progressivo": True,
    "theme": "dark",
    "font_scontrino_pt": 10,
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    # Write default config
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
    return dict(DEFAULT_CONFIG)


def main():
    config = load_config()

    app = QApplication(sys.argv)
    app.setApplicationName("Cashy")
    app.setOrganizationName("Cashy POS")

    icon_path = str(get_assets_dir() / "assets" / "icon.ico")
    app.setWindowIcon(QIcon(icon_path))

    # Apply theme before any widget is constructed so C is populated correctly.
    import ui.theme as _theme
    _theme.set_theme(config.get("theme", "dark"))

    # Register and apply Oxanium variable font
    font_path = str(get_assets_dir() / "assets" / "font" / "Oxanium-VariableFont_wght.ttf")
    QFontDatabase.addApplicationFont(font_path)
    font = QFont("Oxanium", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    # Apply global stylesheet (read after set_theme so the string is current)
    app.setStyleSheet(_theme.GLOBAL_STYLESHEET)

    # Show the boot splash before the (slower) main window is built.
    from ui.splash import make_splash
    splash = make_splash()
    splash.show()
    app.processEvents()

    from ui.schermata_cassa import SchermataCassa
    window = SchermataCassa(config)
    # showMaximized is called inside SchermataCassa.__init__
    splash.finish(window)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
