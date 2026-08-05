from datetime import datetime

from core.font_scontrino import get_escpos_size

WIDTH = 48

try:
    import escpos.printer as escpos_printer
    HAS_ESCPOS = True
except ImportError:
    HAS_ESCPOS = False


def _is_escpos_porta(porta: str) -> bool:
    """True if porta refers to a raw ESC/POS port (USB / COMx / LPTx)."""
    p = porta.upper()
    return p == "USB" or p.startswith("COM") or p.startswith("LPT")


def _fmt_price(value: float) -> str:
    """Format price with comma decimal separator and euro sign."""
    return f"€{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _line(label: str, price_str: str, width: int = WIDTH) -> str:
    """Build a receipt line with label on left and price right-aligned."""
    available = width - len(price_str)
    if len(label) >= available:
        label = label[: available - 1]
    return label.ljust(available) + price_str


def genera_scontrino(
    config: dict,
    righe_carrello: list,
    totale: float,
    ricevuto: float,
    resto: float,
    numero: int = None,
) -> str:
    sep_thick = "=" * WIDTH
    sep_thin = "-" * WIDTH

    lines = []
    lines.append(sep_thick)

    nome_evento = config.get("nome_evento", "Cassa")
    lines.append(nome_evento.center(WIDTH))

    data_evento = config.get("data_evento", "")
    now_time = datetime.now().strftime("%H:%M")
    data_line = f"{data_evento} {now_time}".strip()
    lines.append(data_line.center(WIDTH))

    if numero is not None:
        num_line = f"Scontrino #{numero:03d}"
        lines.append(num_line.center(WIDTH))

    lines.append(sep_thick)

    for riga in righe_carrello:
        qty = riga.get("quantita", 1)
        nome = riga.get("nome", "")
        prezzo_unit = riga.get("prezzo", 0.0)
        totale_riga = prezzo_unit * qty
        label = f"{qty}x {nome}"
        price_str = _fmt_price(totale_riga)
        lines.append(_line(label, price_str))

    lines.append(sep_thin)
    lines.append(_line("TOTALE", _fmt_price(totale)))
    lines.append(_line("Ricevuto", _fmt_price(ricevuto)))
    lines.append(_line("RESTO", _fmt_price(resto)))
    lines.append(sep_thick)

    messaggio = config.get("messaggio_scontrino", "Grazie!")
    lines.append(messaggio.center(WIDTH))
    lines.append(sep_thick)

    return "\n".join(lines)


def genera_scontrino_categoria(config: dict, categoria: str, righe: list, subtotale: float) -> str:
    """Generate a category slip (comanda) with no payment info."""
    sep_thick = "=" * WIDTH
    sep_thin = "-" * WIDTH
    lines = []
    lines.append(sep_thick)
    lines.append(f"COMANDA: {categoria.upper()}".center(WIDTH))
    nome_evento = config.get("nome_evento", "Cassa")
    lines.append(nome_evento.center(WIDTH))
    data_evento = config.get("data_evento", "")
    now_time = datetime.now().strftime("%H:%M")
    lines.append(f"{data_evento} {now_time}".strip().center(WIDTH))
    lines.append(sep_thick)
    for riga in righe:
        qty = riga.get("quantita", 1)
        nome = riga.get("nome", "")
        prezzo_unit = riga.get("prezzo", 0.0)
        totale_riga = prezzo_unit * qty
        label = f"{qty}x {nome}"
        price_str = _fmt_price(totale_riga)
        lines.append(_line(label, price_str))
    lines.append(sep_thin)
    lines.append(_line("TOT. CATEGORIA", _fmt_price(subtotale)))
    lines.append(sep_thick)
    return "\n".join(lines)


def genera_resoconto(
    config: dict,
    data_ora: str,
    righe_aggregate: list,
    n_ordini: int,
    totale_giornata: float,
) -> str:
    """Generate a daily summary receipt aggregated by product."""
    sep_thick = "=" * WIDTH
    sep_thin = "-" * WIDTH

    lines = []
    lines.append(sep_thick)
    lines.append("RESOCONTO GIORNATA".center(WIDTH))
    nome_evento = config.get("nome_evento", "")
    if nome_evento:
        lines.append(nome_evento.center(WIDTH))
    lines.append(data_ora.center(WIDTH))
    lines.append(sep_thick)

    total_qty = 0
    for r in righe_aggregate:
        qty = r["quantita"]
        total_qty += qty
        label = f"{r['nome']} ({qty}x)"
        price_str = _fmt_price(r["incasso"])
        lines.append(_line(label, price_str))

    lines.append(sep_thin)
    lines.append(_line("Articoli venduti:", str(total_qty)))
    lines.append(_line("N. ordini:", str(n_ordini)))
    lines.append(sep_thick)
    lines.append(_line("INCASSO TOTALE:", _fmt_price(totale_giornata)))
    lines.append(sep_thick)

    return "\n".join(lines)


def _get_printer(porta: str):
    porta_upper = porta.upper()
    if porta_upper == "USB":
        return escpos_printer.Usb(0x0416, 0x5011, timeout=2)
    if porta_upper.startswith("COM"):
        return escpos_printer.Serial(porta_upper, baudrate=9600, timeout=2)
    if porta_upper.startswith("LPT"):
        return escpos_printer.Win32Raw(porta_upper)
    raise ValueError(f"Porta non supportata: {porta}")


def stampa_termico(testo: str, porta: str, config: dict | None = None) -> tuple[bool, str]:
    """Send a single receipt to a printer.

    Dispatches to Windows raw ESC/POS for system printers,
    or to python-escpos for USB/COM/LPT ports.
    """
    if not _is_escpos_porta(porta):
        from core.printing import stampa_silent
        return stampa_silent(testo, porta, config)
    if not HAS_ESCPOS:
        return False, "Libreria python-escpos non installata.\nInstallare con: pip install python-escpos"
    try:
        width, height = get_escpos_size(config or {})
        printer = _get_printer(porta)
        printer.set(align="left", font="a", bold=False, underline=0, width=width, height=height)
        printer.text(testo + "\n\n\n")
        printer.cut()
        return True, ""
    except Exception as exc:
        return False, str(exc)


def stampa_multiplo(testi: list[str], porta: str, config: dict | None = None) -> tuple[bool, str]:
    """Send multiple receipts to a printer, cutting between each."""
    if not _is_escpos_porta(porta):
        from core.printing import stampa_silent_multiplo
        return stampa_silent_multiplo(testi, porta, config)
    if not HAS_ESCPOS:
        return False, "Libreria python-escpos non installata.\nInstallare con: pip install python-escpos"
    try:
        width, height = get_escpos_size(config or {})
        printer = _get_printer(porta)
        printer.set(align="left", font="a", bold=False, underline=0, width=width, height=height)
        for testo in testi:
            printer.text(testo + "\n\n\n")
            printer.cut()
        return True, ""
    except Exception as exc:
        return False, str(exc)
