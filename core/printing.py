"""Windows raw ESC/POS and GDI fallback printing.

Raw ESC/POS via win32print is attempted first — this sends bytes directly
to the printer bypassing GDI page rendering, producing compact receipts.
QPrinter/QTextDocument is used only as fallback when pywin32 is unavailable.
"""
from PyQt6.QtPrintSupport import QPrinter, QPrinterInfo
from PyQt6.QtGui import QTextDocument, QFont

from core.font_scontrino import get_esc_bang, get_gdi_pt

try:
    import win32print
    HAS_WIN32PRINT = True
except ImportError:
    HAS_WIN32PRINT = False


def get_stampanti_windows() -> list[str]:
    """Return the names of all printers currently registered in Windows."""
    return [p.printerName() for p in QPrinterInfo.availablePrinters()]


def _build_escpos(testo: str, config: dict | None = None) -> bytes:
    """Encode receipt text as raw ESC/POS bytes with auto-cut at the end."""
    esc_bang = get_esc_bang(config or {})

    buf = bytearray()
    buf += b'\x1b\x40'       # ESC @  — initialize printer
    buf += b'\x1b\x74\x10'  # ESC t 16 — select WPC1252 codepage (Western + €)
    buf += b'\x1b\x61\x00'  # ESC a 0  — left align
    buf += b'\x1b\x21' + bytes([esc_bang])  # ESC ! n — font size (normal/double)

    text = testo.replace('\r\n', '\n').replace('\r', '\n')
    if not text.endswith('\n'):
        text += '\n'
    # cp1252 == WPC1252: è=0xE8, à=0xE0, €=0x80 — all match printer's codepage
    buf += text.encode('cp1252', errors='replace')

    buf += b'\x1b\x64\x04'  # ESC d 4 — feed 4 lines before cutter
    buf += b'\x1d\x56\x00'  # GS V 0  — full cut
    return bytes(buf)


def _stampa_raw_win32(data: bytes, nome_stampante: str) -> tuple[bool, str]:
    """Send raw bytes to a Windows printer bypassing GDI rendering."""
    try:
        hprinter = win32print.OpenPrinter(nome_stampante)
        try:
            hJob = win32print.StartDocPrinter(hprinter, 1, ("Scontrino", None, "RAW"))
            try:
                win32print.StartPagePrinter(hprinter)
                win32print.WritePrinter(hprinter, data)
                win32print.EndPagePrinter(hprinter)
            finally:
                win32print.EndDocPrinter(hprinter)
        finally:
            win32print.ClosePrinter(hprinter)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def stampa_silent(testo: str, nome_stampante: str, config: dict | None = None) -> tuple[bool, str]:
    """Send a receipt to a named Windows printer.

    Sends raw ESC/POS bytes via win32print (compact output, exact cut).
    Falls back to QPrinter/QTextDocument when pywin32 is not installed.
    """
    if HAS_WIN32PRINT:
        return _stampa_raw_win32(_build_escpos(testo, config), nome_stampante)

    # Fallback: GDI rendering (receipt length depends on paper size in driver)
    try:
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        printer.setPrinterName(nome_stampante)
        doc = QTextDocument()
        font = QFont("Courier New", get_gdi_pt(config or {}))
        font.setFixedPitch(True)
        doc.setDefaultFont(font)
        doc.setPlainText(testo)
        doc.print(printer)
        return True, ""
    except Exception as exc:
        return False, str(exc)


def stampa_silent_multiplo(testi: list[str], nome_stampante: str, config: dict | None = None) -> tuple[bool, str]:
    """Print multiple receipts as separate jobs to the same Windows printer."""
    if HAS_WIN32PRINT:
        # Send all receipts in a single connection for efficiency
        errors: list[str] = []
        for testo in testi:
            ok, err = _stampa_raw_win32(_build_escpos(testo, config), nome_stampante)
            if not ok:
                errors.append(err)
        return (False, "\n".join(errors)) if errors else (True, "")

    errors = []
    for testo in testi:
        ok, err = stampa_silent(testo, nome_stampante, config)
        if not ok:
            errors.append(err)
    return (False, "\n".join(errors)) if errors else (True, "")
