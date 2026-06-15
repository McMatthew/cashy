"""Trasporto Bluetooth (RFCOMM) per la sincronizzazione del listino tra due app Cashy.

Usa i socket RFCOMM nativi della stdlib (``socket.AF_BLUETOOTH`` /
``socket.BTPROTO_RFCOMM``), disponibili su Windows, quindi non richiede librerie
esterne (pybluez2 non è compatibile con Python 3.14).

Protocollo applicativo, volutamente minimale:
  mittente -> ricevente : [4 byte big-endian = lunghezza] + [payload JSON UTF-8]
  ricevente -> mittente : 1 byte di esito  (ACK_OK / ACK_RIFIUTATO / ACK_ERRORE)

Questo modulo è privo di dipendenze da Qt: espone primitive di basso livello che la
UI orchestra dentro un proprio thread (l'attesa della conferma utente avviene lato UI).
"""

import json
import re
import socket
import struct
import subprocess

# Canale RFCOMM concordato tra le due app. Dev'essere identico su mittente e ricevente.
RFCOMM_CHANNEL = 5

# Esiti dell'handshake (1 byte).
ACK_OK = b"Y"          # listino accettato e importato dal ricevente
ACK_RIFIUTATO = b"N"   # l'utente del ricevente ha rifiutato il pacchetto
ACK_ERRORE = b"E"      # errore lato ricevente (pacchetto non valido, import fallito)

# Tetto di sicurezza sulla dimensione del pacchetto (16 MiB) per non allocare a vuoto
# in caso di lunghezza corrotta.
_MAX_PAYLOAD = 16 * 1024 * 1024


class BluetoothNonDisponibile(RuntimeError):
    """Sollevata quando lo stack Bluetooth/RFCOMM non è utilizzabile su questo sistema."""


def _rfcomm_supportato() -> bool:
    return hasattr(socket, "AF_BLUETOOTH") and hasattr(socket, "BTPROTO_RFCOMM")


def _nuovo_socket() -> socket.socket:
    if not _rfcomm_supportato():
        raise BluetoothNonDisponibile(
            "Questo sistema non espone i socket Bluetooth RFCOMM."
        )
    return socket.socket(
        socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM
    )


# ── Payload ───────────────────────────────────────────────────────────────────

def costruisci_payload(package: dict) -> bytes:
    return json.dumps(package, ensure_ascii=False).encode("utf-8")


def _recv_esatti(sock: socket.socket, n: int) -> bytes:
    """Legge esattamente n byte o solleva ConnectionError se la connessione si chiude."""
    chunks = []
    rimasti = n
    while rimasti > 0:
        chunk = sock.recv(min(rimasti, 65536))
        if not chunk:
            raise ConnectionError("Connessione chiusa prima di ricevere tutti i dati.")
        chunks.append(chunk)
        rimasti -= len(chunk)
    return b"".join(chunks)


def leggi_pacchetto(conn: socket.socket) -> dict:
    """Legge un pacchetto length-prefixed dalla connessione e lo decodifica in dict."""
    intestazione = _recv_esatti(conn, 4)
    (lunghezza,) = struct.unpack(">I", intestazione)
    if lunghezza <= 0 or lunghezza > _MAX_PAYLOAD:
        raise ValueError(f"Dimensione pacchetto non valida: {lunghezza} byte.")
    grezzo = _recv_esatti(conn, lunghezza)
    return json.loads(grezzo.decode("utf-8"))


def invia_ack(conn: socket.socket, ack: bytes) -> None:
    try:
        conn.sendall(ack)
    except OSError:
        pass  # il mittente potrebbe essersi già disconnesso: non è un errore fatale


# ── Invio (lato mittente) ───────────────────────────────────────────────────

def invia_listino(mac: str, payload: bytes, timeout: float = 25.0) -> bytes:
    """Si connette al ricevente e invia il payload. Ritorna il byte di esito.

    Solleva un'eccezione socket/OSError in caso di problemi di connessione/IO.
    """
    sock = _nuovo_socket()
    sock.settimeout(timeout)
    try:
        sock.connect((mac, RFCOMM_CHANNEL))
        sock.sendall(struct.pack(">I", len(payload)) + payload)
        try:
            ack = _recv_esatti(sock, 1)
        except ConnectionError:
            # Il ricevente ha chiuso senza inviare esito: trattiamo come errore.
            ack = ACK_ERRORE
        return ack
    finally:
        try:
            sock.close()
        except OSError:
            pass


# ── Ricezione (lato ricevente) ──────────────────────────────────────────────

def apri_server() -> socket.socket:
    """Apre un socket RFCOMM in ascolto sul canale concordato."""
    srv = _nuovo_socket()
    try:
        srv.bind((socket.BDADDR_ANY, RFCOMM_CHANNEL))
        srv.listen(1)
    except OSError:
        srv.close()
        raise
    return srv


def accetta_con_stop(srv: socket.socket, stop_event, poll: float = 1.0):
    """Attende una connessione consentendo l'interruzione tramite ``stop_event``.

    Ritorna ``(conn, addr)`` oppure ``None`` se è stato richiesto lo stop.
    """
    srv.settimeout(poll)
    while not stop_event.is_set():
        try:
            return srv.accept()
        except socket.timeout:
            continue
    return None


# ── Scoperta dispositivi accoppiati ─────────────────────────────────────────

_PS_DISCOVERY = (
    "Get-PnpDevice -Class Bluetooth -Status OK | "
    "Select-Object FriendlyName,InstanceId | ConvertTo-Json -Compress"
)
_DEV_RE = re.compile(r"DEV_([0-9A-Fa-f]{12})")


def _mac_da_hex(hex12: str) -> str:
    h = hex12.upper()
    return ":".join(h[i:i + 2] for i in range(0, 12, 2))


def scopri_dispositivi(timeout: float = 12.0) -> list[dict]:
    """Enumera i dispositivi Bluetooth accoppiati/connessi via Get-PnpDevice.

    Ritorna una lista di dict ``{"nome", "mac", "classic"}`` deduplicata per MAC.
    ``classic=True`` indica un dispositivo BR/EDR (compatibile RFCOMM); i dispositivi
    solo-BLE hanno ``classic=False`` e non possono ricevere il listino via RFCOMM.
    """
    try:
        proc = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", _PS_DISCOVERY],
            capture_output=True, text=True, timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired) as e:
        raise BluetoothNonDisponibile(f"Impossibile enumerare i dispositivi: {e}")

    out = (proc.stdout or "").strip()
    if not out:
        return []
    try:
        dati = json.loads(out)
    except json.JSONDecodeError:
        return []
    if isinstance(dati, dict):
        dati = [dati]

    per_mac: dict[str, dict] = {}
    for voce in dati:
        instance_id = (voce.get("InstanceId") or "")
        nome = (voce.get("FriendlyName") or "").strip()
        m = _DEV_RE.search(instance_id)
        if not m:
            continue
        mac = _mac_da_hex(m.group(1))
        is_classic = instance_id.upper().startswith("BTHENUM")
        esistente = per_mac.get(mac)
        if esistente is None:
            per_mac[mac] = {"nome": nome or mac, "mac": mac, "classic": is_classic}
        else:
            # Mantieni un nome non vuoto e segna classic se una qualsiasi voce lo è.
            if is_classic:
                esistente["classic"] = True
            if nome and esistente["nome"] == mac:
                esistente["nome"] = nome

    return sorted(per_mac.values(), key=lambda d: (not d["classic"], d["nome"].lower()))
