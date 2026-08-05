"""Mappa la dimensione del font scontrino (config['font_scontrino_pt']) sui
diversi backend: anteprima a schermo, fallback GDI e stampa termica ESC/POS.

Le stampanti termiche non supportano punti arbitrari: espongono solo un
raddoppio di altezza e/o larghezza carattere. I punti impostati dall'utente
vengono quindi convertiti in scatti discreti oltre la dimensione di base.
"""

DEFAULT_PT = 10
MIN_PT = 8
MAX_PT = 20


def get_pt(config: dict) -> int:
    """Dimensione (in punti) usata per l'anteprima a schermo dello scontrino."""
    try:
        pt = int(config.get("font_scontrino_pt", DEFAULT_PT))
    except (TypeError, ValueError):
        pt = DEFAULT_PT
    return max(MIN_PT, min(MAX_PT, pt))


def get_gdi_pt(config: dict) -> int:
    """Dimensione per il fallback di stampa GDI (QFont), leggermente più piccola
    dell'anteprima per restare coerente con la resa storica a 8pt di default."""
    return max(6, get_pt(config) - 2)


def get_esc_bang(config: dict) -> int:
    """Byte per il comando ESC ! (0x1B 0x21) usato dalla stampa raw win32print."""
    pt = get_pt(config)
    if pt >= DEFAULT_PT + 4:
        return 0x30  # doppia altezza + doppia larghezza
    if pt >= DEFAULT_PT + 2:
        return 0x10  # doppia altezza
    return 0x00  # normale


def get_escpos_size(config: dict) -> tuple[int, int]:
    """Coppia (width, height) per printer.set() di python-escpos."""
    pt = get_pt(config)
    if pt >= DEFAULT_PT + 4:
        return 2, 2
    if pt >= DEFAULT_PT + 2:
        return 1, 2
    return 1, 1
