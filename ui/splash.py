from PyQt6.QtWidgets import QSplashScreen, QApplication
from PyQt6.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt6.QtCore import Qt
from PyQt6.QtSvg import QSvgRenderer

from core.paths import get_assets_dir
from core.version import __version__


def make_splash() -> QSplashScreen:
    """Build the boot splash: the bootsplash.svg rendered crisply at a
    screen-fitting size, with the version number in white at bottom-right."""
    svg_path = str(get_assets_dir() / "assets" / "bootsplash.svg")
    renderer = QSvgRenderer(svg_path)

    size = renderer.defaultSize()  # 1051 x 679
    w, h = size.width(), size.height()

    # Scale down to fit comfortably on screen, never upscale past native size.
    screen = QApplication.primaryScreen()
    if screen is not None:
        avail = screen.availableGeometry()
        fit = min(avail.width() * 0.8 / w, avail.height() * 0.8 / h, 1.0)
        w, h = round(w * fit), round(h * fit)

    pixmap = QPixmap(w, h)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHints(
        QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
    )
    renderer.render(painter)  # vector → crisp at any size

    margin = max(16, round(h * 0.04))
    font = QFont("Oxanium", max(10, round(h * 0.028)), QFont.Weight.DemiBold)
    painter.setFont(font)
    painter.setPen(QColor("#FFFFFF"))
    painter.drawText(
        pixmap.rect().adjusted(0, 0, -margin, -margin),
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom,
        f"v{__version__}",
    )
    painter.end()

    splash = QSplashScreen(pixmap)
    splash.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
    return splash
