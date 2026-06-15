"""Dialoghi per inviare/ricevere il listino prodotti via Bluetooth (RFCOMM).

- ``InviaListinoDialog``: elenca i dispositivi Bluetooth accoppiati, lascia scegliere
  il computer di destinazione e invia il listino, mostrando esito o errore.
- ``RiceviListinoDialog``: mette l'app in ascolto; alla ricezione di un pacchetto
  chiede conferma all'utente prima di sostituire il catalogo locale.

Tutto l'I/O di rete avviene in QThread dedicati per non bloccare l'interfaccia.
"""

import socket
import threading

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from ui.theme import C
from core.database import DatabaseManager
from core import bluetooth_sync as bt


# ── Worker: scoperta dispositivi ────────────────────────────────────────────

class _DiscoveryWorker(QThread):
    trovati = pyqtSignal(list)
    errore = pyqtSignal(str)

    def run(self):
        try:
            self.trovati.emit(bt.scopri_dispositivi())
        except Exception as e:  # noqa: BLE001 - vogliamo riportare qualsiasi errore
            self.errore.emit(str(e))


# ── Worker: invio ────────────────────────────────────────────────────────────

class _InvioWorker(QThread):
    completato = pyqtSignal(bytes)
    errore = pyqtSignal(str)

    def __init__(self, mac: str, payload: bytes, parent=None):
        super().__init__(parent)
        self._mac = mac
        self._payload = payload

    def run(self):
        try:
            ack = bt.invia_listino(self._mac, self._payload)
            self.completato.emit(ack)
        except Exception as e:  # noqa: BLE001
            self.errore.emit(str(e))


# ── Worker: ricezione ────────────────────────────────────────────────────────

class _RicezioneWorker(QThread):
    in_ascolto = pyqtSignal(str)                 # MAC dell'adattatore locale
    pacchetto_ricevuto = pyqtSignal(dict, str)  # (package, indirizzo mittente)
    terminato = pyqtSignal()
    errore = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._stop = threading.Event()
        self._decisione = threading.Event()
        self._esito = bt.ACK_ERRORE

    def imposta_esito(self, ack: bytes):
        """Chiamato dal thread GUI dopo che l'utente ha deciso; sblocca il worker."""
        self._esito = ack
        self._decisione.set()

    def richiedi_stop(self):
        self._stop.set()

    def run(self):
        srv = None
        conn = None
        try:
            srv = bt.apri_server()
        except Exception as e:  # noqa: BLE001
            self.errore.emit(
                f"Impossibile mettersi in ascolto via Bluetooth:\n{e}\n\n"
                "Verifica che il Bluetooth sia attivo e che le due app usino lo stesso canale."
            )
            return
        try:
            try:
                self.in_ascolto.emit(srv.getsockname()[0])
            except OSError:
                pass
            risultato = bt.accetta_con_stop(srv, self._stop)
            if risultato is None:
                return  # stop richiesto prima di ricevere
            conn, addr = risultato
            addr_str = addr[0] if isinstance(addr, (tuple, list)) else str(addr)
            try:
                package = bt.leggi_pacchetto(conn)
            except Exception as e:  # noqa: BLE001 - pacchetto corrotto/troncato
                bt.invia_ack(conn, bt.ACK_ERRORE)
                self.errore.emit(f"Pacchetto ricevuto non leggibile:\n{e}")
                return
            # Consegna il pacchetto alla GUI e attende la decisione dell'utente.
            self.pacchetto_ricevuto.emit(package, addr_str)
            self._decisione.wait()
            bt.invia_ack(conn, self._esito)
            self.terminato.emit()
        finally:
            for s in (conn, srv):
                if s is not None:
                    try:
                        s.close()
                    except OSError:
                        pass


def _conta(package: dict) -> tuple[int, int]:
    prodotti = package.get("prodotti") if isinstance(package, dict) else None
    categorie = package.get("categorie") if isinstance(package, dict) else None
    return (
        len(prodotti) if isinstance(prodotti, list) else 0,
        len(categorie) if isinstance(categorie, list) else 0,
    )


# ── Dialog: invio ─────────────────────────────────────────────────────────────

class InviaListinoDialog(QDialog):
    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self._db = db
        self._payload = bt.costruisci_payload(db.esporta_listino())
        self._discovery: _DiscoveryWorker | None = None
        self._invio: _InvioWorker | None = None

        self.setWindowTitle("Invia listino via Bluetooth")
        self.setMinimumSize(460, 420)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {C['surface_container']}; color: {C['on_surface']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Invia listino via Bluetooth")
        title.setStyleSheet(f"font-size: 13pt; font-weight: 700; color: {C['on_surface']}; background: transparent;")
        layout.addWidget(title)

        n_prod, n_cat = _conta(self._db.esporta_listino())
        sub = QLabel(
            f"Verranno inviati {n_prod} prodotti e {n_cat} categorie (foto escluse). "
            "Seleziona il computer di destinazione tra i dispositivi accoppiati."
        )
        sub.setWordWrap(True)
        sub.setStyleSheet(f"color: {C['on_surface_variant']}; font-size: 9pt; background: transparent;")
        layout.addWidget(sub)

        self._lista = QListWidget()
        self._lista.setStyleSheet(
            f"QListWidget {{ background-color: {C['surface_container_high']};"
            f" border: 1px solid {C['border_secondary']}; border-radius: 8px; }}"
        )
        self._lista.itemSelectionChanged.connect(self._aggiorna_stato_invio)
        self._lista.itemDoubleClicked.connect(lambda _: self._invia())
        layout.addWidget(self._lista)

        self._stato = QLabel("")
        self._stato.setStyleSheet(f"color: {C['on_surface_variant']}; font-size: 9pt; background: transparent;")
        layout.addWidget(self._stato)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        self._btn_aggiorna = QPushButton("Aggiorna elenco")
        self._btn_aggiorna.setObjectName("btn_secondary")
        self._btn_aggiorna.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_aggiorna.clicked.connect(self._scansiona)
        btn_row.addWidget(self._btn_aggiorna)

        btn_row.addStretch()

        btn_chiudi = QPushButton("Chiudi")
        btn_chiudi.setObjectName("btn_secondary")
        btn_chiudi.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_chiudi.clicked.connect(self.reject)
        btn_row.addWidget(btn_chiudi)

        self._btn_invia = QPushButton("Invia")
        self._btn_invia.setObjectName("btn_primary")
        self._btn_invia.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_invia.clicked.connect(self._invia)
        self._btn_invia.setEnabled(False)
        btn_row.addWidget(self._btn_invia)

        layout.addLayout(btn_row)

        self._scansiona()

    # ── Scoperta ──
    def _scansiona(self):
        if self._discovery and self._discovery.isRunning():
            return
        self._lista.clear()
        self._stato.setText("Ricerca dei dispositivi accoppiati in corso…")
        self._btn_aggiorna.setEnabled(False)
        self._discovery = _DiscoveryWorker(self)
        self._discovery.trovati.connect(self._on_trovati)
        self._discovery.errore.connect(self._on_discovery_errore)
        self._discovery.start()

    def _on_trovati(self, dispositivi: list):
        self._btn_aggiorna.setEnabled(True)
        self._lista.clear()
        if not dispositivi:
            self._stato.setText("Nessun dispositivo accoppiato trovato.")
            return
        for d in dispositivi:
            etichetta = d["nome"]
            if not d["classic"]:
                etichetta += "  —  (solo BLE, non compatibile)"
            item = QListWidgetItem(etichetta)
            item.setData(Qt.ItemDataRole.UserRole, d)
            if not d["classic"]:
                item.setForeground(_q_color(C["on_surface_variant"]))
            self._lista.addItem(item)
        self._stato.setText(f"{len(dispositivi)} dispositivi trovati. Seleziona la destinazione.")

    def _on_discovery_errore(self, msg: str):
        self._btn_aggiorna.setEnabled(True)
        self._stato.setText("Errore nella ricerca dei dispositivi.")
        QMessageBox.warning(self, "Bluetooth", f"Impossibile elencare i dispositivi:\n{msg}")

    # ── Invio ──
    def _dispositivo_selezionato(self) -> dict | None:
        item = self._lista.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _aggiorna_stato_invio(self):
        d = self._dispositivo_selezionato()
        in_corso = bool(self._invio and self._invio.isRunning())
        self._btn_invia.setEnabled(d is not None and not in_corso)

    def _invia(self):
        if self._invio and self._invio.isRunning():
            return
        d = self._dispositivo_selezionato()
        if not d:
            return
        if not d["classic"]:
            QMessageBox.warning(
                self, "Dispositivo non compatibile",
                f"'{d['nome']}' è un dispositivo solo BLE e non può ricevere il listino "
                "via RFCOMM. Seleziona un computer Bluetooth classico."
            )
            return
        self._imposta_in_corso(True)
        self._stato.setText(f"Invio a '{d['nome']}' in corso…")
        self._invio = _InvioWorker(d["mac"], self._payload, self)
        self._invio.completato.connect(self._on_invio_completato)
        self._invio.errore.connect(self._on_invio_errore)
        self._invio.start()

    def _imposta_in_corso(self, in_corso: bool):
        self._btn_invia.setEnabled(not in_corso and self._dispositivo_selezionato() is not None)
        self._btn_aggiorna.setEnabled(not in_corso)
        self._lista.setEnabled(not in_corso)

    def _on_invio_completato(self, ack: bytes):
        self._imposta_in_corso(False)
        if ack == bt.ACK_OK:
            self._stato.setText("Listino inviato e accettato.")
            QMessageBox.information(
                self, "Invio riuscito",
                "Il listino è stato inviato e accettato dal dispositivo di destinazione."
            )
        elif ack == bt.ACK_RIFIUTATO:
            self._stato.setText("Listino rifiutato dal destinatario.")
            QMessageBox.warning(
                self, "Listino rifiutato",
                "L'utente del dispositivo di destinazione ha rifiutato il listino."
            )
        else:
            self._stato.setText("Errore sul dispositivo di destinazione.")
            QMessageBox.critical(
                self, "Errore",
                "Il dispositivo di destinazione non è riuscito a importare il listino."
            )

    def _on_invio_errore(self, msg: str):
        self._imposta_in_corso(False)
        self._stato.setText("Invio fallito.")
        QMessageBox.critical(
            self, "Invio fallito",
            f"Impossibile inviare il listino:\n{msg}\n\n"
            "Assicurati che l'app di destinazione sia in ascolto ('Ricevi listino') "
            "e che i due dispositivi siano accoppiati."
        )

    def reject(self):
        self._ferma_worker()
        super().reject()

    def closeEvent(self, event):
        self._ferma_worker()
        super().closeEvent(event)

    def _ferma_worker(self):
        for w in (self._discovery, self._invio):
            if w and w.isRunning():
                w.wait(3000)


# ── Dialog: ricezione ─────────────────────────────────────────────────────────

class RiceviListinoDialog(QDialog):
    listino_importato = pyqtSignal()

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self._db = db
        self._worker: _RicezioneWorker | None = None

        self.setWindowTitle("Ricevi listino via Bluetooth")
        self.setMinimumWidth(440)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {C['surface_container']}; color: {C['on_surface']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Ricevi listino via Bluetooth")
        title.setStyleSheet(f"font-size: 13pt; font-weight: 700; color: {C['on_surface']}; background: transparent;")
        layout.addWidget(title)

        info = QLabel(
            "Questo computer è in attesa di ricevere un listino.\n"
            f"Sul dispositivo mittente seleziona questo computer ({socket.gethostname()}) "
            "tra i dispositivi accoppiati e premi 'Invia'."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {C['on_surface_variant']}; font-size: 9pt; background: transparent;")
        layout.addWidget(info)

        self._stato = QLabel("In ascolto…")
        self._stato.setStyleSheet(
            f"color: {C['primary']}; font-size: 10pt; font-weight: 600; background: transparent;"
        )
        layout.addWidget(self._stato)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_chiudi = QPushButton("Chiudi")
        self._btn_chiudi.setObjectName("btn_secondary")
        self._btn_chiudi.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_chiudi.clicked.connect(self.reject)
        btn_row.addWidget(self._btn_chiudi)
        layout.addLayout(btn_row)

        self._avvia_ascolto()

    def _avvia_ascolto(self):
        self._worker = _RicezioneWorker(self)
        self._worker.in_ascolto.connect(self._on_in_ascolto)
        self._worker.pacchetto_ricevuto.connect(self._on_pacchetto)
        self._worker.terminato.connect(self._on_terminato)
        self._worker.errore.connect(self._on_errore)
        self._worker.start()

    def _on_in_ascolto(self, mac: str):
        self._stato.setText(f"In ascolto…  (indirizzo: {mac})")

    def _on_pacchetto(self, package: dict, mittente: str):
        n_prod, n_cat = _conta(package)
        self._stato.setText(f"Listino ricevuto da {mittente}.")
        risposta = QMessageBox.question(
            self, "Listino ricevuto",
            f"Ricevuto un listino da {mittente}:\n"
            f"• {n_prod} prodotti\n• {n_cat} categorie\n\n"
            "Accettandolo, il catalogo prodotti e categorie di QUESTO computer "
            "verrà sostituito interamente. Procedere?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if risposta != QMessageBox.StandardButton.Yes:
            self._stato.setText("Listino rifiutato.")
            if self._worker:
                self._worker.imposta_esito(bt.ACK_RIFIUTATO)
            return
        try:
            self._db.importa_listino(package)
        except Exception as e:  # noqa: BLE001
            self._stato.setText("Errore durante l'importazione.")
            if self._worker:
                self._worker.imposta_esito(bt.ACK_ERRORE)
            QMessageBox.critical(self, "Errore", f"Impossibile importare il listino:\n{e}")
            return
        if self._worker:
            self._worker.imposta_esito(bt.ACK_OK)
        self._stato.setText("Listino importato con successo.")
        self.listino_importato.emit()
        QMessageBox.information(
            self, "Listino importato",
            f"Il listino è stato importato: {n_prod} prodotti e {n_cat} categorie."
        )

    def _on_terminato(self):
        self._btn_chiudi.setText("Chiudi")

    def _on_errore(self, msg: str):
        self._stato.setText("Errore.")
        QMessageBox.critical(self, "Bluetooth", msg)
        self.reject()

    def reject(self):
        self._ferma_worker()
        super().reject()

    def closeEvent(self, event):
        self._ferma_worker()
        super().closeEvent(event)

    def _ferma_worker(self):
        if self._worker and self._worker.isRunning():
            self._worker.richiedi_stop()
            # Sblocca un'eventuale attesa di decisione (es. chiusura durante la modale).
            self._worker.imposta_esito(bt.ACK_RIFIUTATO)
            self._worker.wait(3000)


def _q_color(hex_color: str):
    from PyQt6.QtGui import QColor
    return QColor(hex_color)
