"""Dialoghi per inviare/ricevere il listino prodotti via Bluetooth (RFCOMM).

- ``InviaListinoDialog``: elenca i dispositivi Bluetooth accoppiati, lascia scegliere
  il computer di destinazione e invia il listino, mostrando esito o errore.
- ``RiceviListinoDialog``: mette l'app in ascolto; alla ricezione di un pacchetto
  chiede conferma all'utente prima di sostituire il catalogo locale.

Tutto l'I/O di rete avviene in QThread dedicati per non bloccare l'interfaccia.
"""

import json
import socket
import threading
import time

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QMessageBox, QWidget, QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from ui.theme import C
from core.database import DatabaseManager
from core import bluetooth_sync as bt
from core import stock_receiver as sr


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


# ── Ricezione scorte (protocollo cashy.stock-transfer, app mobile) ───────────

class _RicezioneScorteWorker(QThread):
    """Ascolta un singolo trasferimento di scorte via Bluetooth SPP, lo applica al
    DB automaticamente (per rispettare i 12 s di attesa ack del client) e invia
    l'ack JSON. Ciclo di vita "uno e chiudi": accetta una connessione poi termina.
    """
    in_ascolto = pyqtSignal(object)        # canale RFCOMM (int) o None
    completato = pyqtSignal(dict, str)     # (ricevuti, indirizzo mittente)
    errore = pyqtSignal(str)
    log = pyqtSignal(str)                  # riga di diagnostica per la UI
    terminato = pyqtSignal()

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self._db = db
        self._stop = threading.Event()

    def richiedi_stop(self):
        self._stop.set()

    def run(self):
        srv = None
        conn = None
        _log = self.log.emit
        try:
            try:
                _log("Apertura del server Bluetooth…")
                srv, canale = sr.apri_server(log=_log)
            except Exception as e:  # noqa: BLE001
                _log(f"ERRORE apertura server: {e}")
                self.errore.emit(
                    f"Impossibile mettersi in ascolto via Bluetooth sul canale "
                    f"{sr.CANALE_SCORTE}:\n{e}\n\n"
                    "Verifica che il Bluetooth sia attivo e che non ci sia un'altra "
                    "finestra 'Ricevi scorte' già aperta."
                )
                return

            self.in_ascolto.emit(canale)
            _log("In attesa di una connessione dal telefono…")
            risultato = bt.accetta_con_stop(srv, self._stop)
            if risultato is None:
                _log("Ascolto interrotto (finestra chiusa).")
                return  # stop richiesto prima di ricevere

            conn, addr = risultato
            addr_str = addr[0] if isinstance(addr, (tuple, list)) else str(addr)
            _log(f"Connessione accettata da {addr_str}. Lettura del payload…")

            try:
                riga = sr.leggi_messaggio_delimitato(conn, log=_log)
                _log(f"Payload completo: {len(riga)} caratteri. Validazione…")
                categorie, prodotti = sr.valida_ed_estrai(riga)
                _log(f"Protocollo valido: {len(categorie)} categorie, {len(prodotti)} prodotti. Applico…")
                ricevuti = self._db.applica_trasferimento_scorte(categorie, prodotti)
                ack = {"ok": True, "ricevuti": ricevuti}
            except json.JSONDecodeError:
                _log("Payload JSON malformato.")
                ack = {"ok": False, "error": "JSON malformato"}
            except ValueError as e:  # protocollo/versione/payload non validi
                _log(f"Payload rifiutato: {e}")
                ack = {"ok": False, "error": str(e)}
            except Exception as e:  # noqa: BLE001
                _log(f"Errore durante la ricezione: {e}")
                ack = {"ok": False, "error": str(e)}

            _log(f"Invio ack: {ack}")
            sr.invia_ack(conn, ack)
            if ack.get("ok"):
                self.completato.emit(ack["ricevuti"], addr_str)
            else:
                self.errore.emit(ack.get("error", "Errore sconosciuto"))
        finally:
            for s in (conn, srv):
                if s is not None:
                    try:
                        s.close()
                    except OSError:
                        pass
            self.terminato.emit()


class RiceviScorteDialog(QDialog):
    """Mette Cashy in ascolto di un trasferimento di scorte dall'app mobile.

    A differenza di :class:`RiceviListinoDialog` (sync Cashy↔Cashy che sostituisce
    il catalogo previa conferma), qui il payload viene applicato in **upsert per
    nome** e **automaticamente**, senza conferma: il client attende l'ack entro 12 s.
    """
    scorte_ricevute = pyqtSignal()

    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self._db = db
        self._worker: _RicezioneScorteWorker | None = None

        self.setWindowTitle("Ricevi scorte via Bluetooth")
        self.setMinimumWidth(460)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"background-color: {C['surface_container']}; color: {C['on_surface']};")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("Ricevi scorte via Bluetooth")
        title.setStyleSheet(f"font-size: 13pt; font-weight: 700; color: {C['on_surface']}; background: transparent;")
        layout.addWidget(title)

        info = QLabel(
            "Questo computer è in attesa di ricevere scorte dall'app mobile Cashy Quick Stock.\n"
            f"Assicurati che il telefono sia accoppiato con questo computer ({socket.gethostname()}), "
            "poi sul telefono seleziona i prodotti e premi 'Invia via Bluetooth'.\n\n"
            "I prodotti e le categorie ricevuti verranno aggiornati o aggiunti "
            "(abbinati per nome); il resto del catalogo non viene toccato."
        )
        info.setWordWrap(True)
        info.setStyleSheet(f"color: {C['on_surface_variant']}; font-size: 9pt; background: transparent;")
        layout.addWidget(info)

        self._stato = QLabel("Avvio ascolto…")
        self._stato.setStyleSheet(
            f"color: {C['primary']}; font-size: 10pt; font-weight: 600; background: transparent;"
        )
        self._stato.setWordWrap(True)
        layout.addWidget(self._stato)

        log_label = QLabel("Diagnostica:")
        log_label.setStyleSheet(f"color: {C['on_surface_variant']}; font-size: 9pt; background: transparent;")
        layout.addWidget(log_label)

        self._log_view = QTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMinimumHeight(160)
        self._log_view.setStyleSheet(
            f"QTextEdit {{ background-color: {C['surface_container_high']};"
            f" color: {C['on_surface']}; border: 1px solid {C['border_secondary']};"
            f" border-radius: 8px; font-family: Consolas, monospace; font-size: 8pt; }}"
        )
        layout.addWidget(self._log_view)

        btn_row = QHBoxLayout()
        self._btn_copia = QPushButton("Copia log")
        self._btn_copia.setObjectName("btn_secondary")
        self._btn_copia.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_copia.clicked.connect(self._copia_log)
        btn_row.addWidget(self._btn_copia)
        btn_row.addStretch()
        self._btn_chiudi = QPushButton("Chiudi")
        self._btn_chiudi.setObjectName("btn_secondary")
        self._btn_chiudi.setCursor(Qt.CursorShape.PointingHandCursor)
        self._btn_chiudi.clicked.connect(self.reject)
        btn_row.addWidget(self._btn_chiudi)
        layout.addLayout(btn_row)

        self._avvia_ascolto()

    def _avvia_ascolto(self):
        self._worker = _RicezioneScorteWorker(self._db, self)
        self._worker.in_ascolto.connect(self._on_in_ascolto)
        self._worker.completato.connect(self._on_completato)
        self._worker.errore.connect(self._on_errore)
        self._worker.log.connect(self._appendi_log)
        self._worker.terminato.connect(self._on_terminato)
        self._worker.start()

    def _appendi_log(self, riga: str):
        self._log_view.append(f"[{time.strftime('%H:%M:%S')}] {riga}")

    def _copia_log(self):
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._log_view.toPlainText())
        self._btn_copia.setText("Copiato ✓")

    def _on_in_ascolto(self, canale):
        suffisso = f"  (canale RFCOMM {canale})" if canale else ""
        self._stato.setText(f"In ascolto…{suffisso}")

    def _on_completato(self, ricevuti: dict, mittente: str):
        n_prod = int(ricevuti.get("prodotti", 0))
        n_cat = int(ricevuti.get("categorie", 0))
        self._stato.setText(f"Ricevuti {n_prod} prodotti e {n_cat} categorie da {mittente}.")
        self.scorte_ricevute.emit()
        QMessageBox.information(
            self, "Scorte ricevute",
            f"Trasferimento completato da {mittente}:\n"
            f"• {n_prod} prodotti\n• {n_cat} categorie\n\n"
            "Il catalogo è stato aggiornato."
        )

    def _on_errore(self, msg: str):
        self._stato.setText("Ricezione non riuscita.")
        QMessageBox.critical(self, "Bluetooth", f"Ricezione non riuscita:\n{msg}")

    def _on_terminato(self):
        self._btn_chiudi.setText("Chiudi")

    def reject(self):
        self._ferma_worker()
        super().reject()

    def closeEvent(self, event):
        self._ferma_worker()
        super().closeEvent(event)

    def _ferma_worker(self):
        if self._worker and self._worker.isRunning():
            self._worker.richiedi_stop()
            self._worker.wait(3000)


def _q_color(hex_color: str):
    from PyQt6.QtGui import QColor
    return QColor(hex_color)
