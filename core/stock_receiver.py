"""Ricevitore Bluetooth per il protocollo ``cashy.stock-transfer``.

Riceve un trasferimento di scorte inviato dall'app mobile **Cashy Quick Stock**
(React Native, Android) via **Bluetooth Classic RFCOMM**. Contratto di trasporto:

* framing: **un** messaggio JSON su **riga singola** terminato da ``\n``;
* charset UTF-8;
* risposta: **un** ack JSON terminato da ``\n``, entro **12 s**.

**Canale RFCOMM fisso, senza SDP.** Su Windows la registrazione SDP via
``WSASetService`` con i socket della stdlib non risulta browsabile dal client
Android (la chiamata "riesce" ma il record non viene servito da remoto), e il
canale 1 — su cui la libreria del client ripiega — è riservato da Windows. La
soluzione, identica a quella già collaudata nel sync Cashy↔Cashy
(:mod:`core.bluetooth_sync`, canale 5), è concordare un **canale RFCOMM fisso** e
connettersi direttamente ad esso: il client vi si connette con
``createRfcommSocket(CANALE_SCORTE)`` (vedi la patch a
``react-native-bluetooth-classic`` nel repo Quick Stock). **Il valore di
``CANALE_SCORTE`` DEVE combaciare con quello usato dal client.**

Il modulo è privo di dipendenze da Qt: espone primitive che la UI orchestra in un
proprio thread.
"""

import json
import socket

from core.bluetooth_sync import _nuovo_socket, BluetoothNonDisponibile  # noqa: F401

# ── Contratto applicativo (deve combaciare col client) ──────────────────────

PROTOCOL_ID = "cashy.stock-transfer"
PROTOCOL_VERSION = 1
DELIMITER = b"\n"

# Canale RFCOMM concordato col client. DEVE essere identico nella patch del client
# (react-native-bluetooth-classic) che si connette direttamente a questo canale.
CANALE_SCORTE = 11

# Tetto di sicurezza sulla dimensione del messaggio (16 MiB).
_MAX_PAYLOAD = 16 * 1024 * 1024

# Timeout di lettura del payload: deve stare sotto i 12 s di attesa ack del client.
_READ_TIMEOUT_S = 8.0


# ── Framing / validazione ────────────────────────────────────────────────────

def leggi_messaggio_delimitato(conn: socket.socket, timeout: float = _READ_TIMEOUT_S, log=None) -> str:
    """Legge un singolo messaggio delimitato da ``\\n`` e lo ritorna (senza il
    terminatore) come stringa UTF-8. Solleva ``TimeoutError``/``ConnectionError``
    o ``ValueError`` se il messaggio è troppo grande."""
    conn.settimeout(timeout)
    buf = bytearray()
    while True:
        try:
            chunk = conn.recv(4096)
        except socket.timeout as e:
            raise TimeoutError(
                f"Timeout in lettura payload dopo {len(buf)} byte ricevuti"
            ) from e
        if not chunk:
            raise ConnectionError(
                f"Connessione chiusa prima del terminatore di riga ({len(buf)} byte ricevuti)."
            )
        if log:
            log(f"Ricevuti {len(chunk)} byte (totale {len(buf) + len(chunk)}).")
        idx = chunk.find(b"\n")
        if idx != -1:
            buf.extend(chunk[:idx])
            return buf.decode("utf-8")
        buf.extend(chunk)
        if len(buf) > _MAX_PAYLOAD:
            raise ValueError("Payload troppo grande.")


def valida_ed_estrai(riga: str) -> tuple[list, list]:
    """Valida ``protocol``/``version`` e ritorna ``(categorie, prodotti)``.

    Solleva ``ValueError`` con il messaggio da usare nell'ack in caso di
    protocollo/versione non validi. ``json.JSONDecodeError`` propaga per il JSON
    malformato (il chiamante lo distingue perché è sottoclasse di ``ValueError``).
    """
    msg = json.loads(riga)
    if not isinstance(msg, dict):
        raise ValueError("Payload non valido")
    if msg.get("protocol") != PROTOCOL_ID:
        raise ValueError("Protocollo non riconosciuto")
    if msg.get("version") != PROTOCOL_VERSION:
        raise ValueError("Versione protocollo non supportata")
    categorie = msg.get("categorie") or []
    prodotti = msg.get("prodotti") or []
    return categorie, prodotti


def invia_ack(conn: socket.socket, ack: dict) -> None:
    """Invia l'ack come singola riga JSON terminata da ``\\n``. Best effort."""
    try:
        conn.sendall(json.dumps(ack, ensure_ascii=False).encode("utf-8") + DELIMITER)
    except OSError:
        pass  # il client potrebbe essersi già disconnesso


# ── Server RFCOMM su canale fisso ────────────────────────────────────────────

def apri_server(log=None):
    """Apre un socket RFCOMM in ascolto sul canale fisso :data:`CANALE_SCORTE`.

    Ritorna ``(srv, canale)``. Solleva ``OSError`` se il canale non è bindabile
    (p.es. già occupato da un'altra istanza in ascolto). ``log`` è un callback
    opzionale ``(str) -> None`` per tracciare le fasi.
    """
    def _log(msg: str) -> None:
        if log:
            log(msg)

    srv = _nuovo_socket()
    try:
        srv.bind((socket.BDADDR_ANY, CANALE_SCORTE))
        srv.listen(1)
    except OSError as e:
        try:
            srv.close()
        except OSError:
            pass
        _log(f"Bind sul canale RFCOMM {CANALE_SCORTE} non riuscito: {e}")
        raise
    _log(f"In ascolto sul canale RFCOMM {CANALE_SCORTE} (connessione diretta, senza SDP).")
    return srv, CANALE_SCORTE
