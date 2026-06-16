<div align="center">

<img src="assets/logo-3.png" alt="Cashy"/>

# Cashy — Cassa Non Fiscale

**Software di cassa per associazioni, enti ed eventi senza obbligo di emissione di scontrino fiscale.**

Sagre, feste di paese, eventi di volontariato, banchetti associativi, bar interni a circoli.

</div>

---

## Che cos'è

Cashy è un punto cassa (POS) desktop pensato per **associazioni ed enti non soggetti all'obbligo di certificazione fiscale dei corrispettivi**. Permette di gestire un listino prodotti, registrare le vendite, calcolare il resto e stampare una ricevuta/comanda non fiscale su stampante termica.

È un'applicazione **standalone per Windows**: tutti i dati restano in locale in un database SQLite, non richiede connessione a Internet né registrazione ad alcun servizio.

> [!IMPORTANT]
> **Non è un registratore di cassa telematico.** Le ricevute prodotte **non hanno valore fiscale** e non vengono trasmesse all'Agenzia delle Entrate. Cashy è destinato esclusivamente ai soggetti **esonerati** dall'obbligo di memorizzazione/trasmissione dei corrispettivi (es. attività occasionali di enti non commerciali). Verifica sempre la tua posizione fiscale prima dell'uso.

---

## Caratteristiche principali

### 🧾 Cassa
- Interfaccia a tre pannelli: informazioni evento, griglia prodotti a categorie, carrello.
- Tile prodotto personalizzabili con **colore** e **foto**.
- Calcolo automatico di totale e **resto** sull'importo ricevuto.
- Numerazione progressiva degli ordini (opzionale).
- **Storico ordini** con possibilità di annullamento.

### 📦 Gestione listino e magazzino
- Prodotti e **categorie** gestibili dall'app.
- **Tracciamento scorte** opzionale per prodotto: quantità in magazzino, limite scorta e **avviso di scorta bassa** (evidenziazione in rosso sotto il 20% della giacenza piena). Senza tracciamento il prodotto è considerato sempre disponibile.
- **Import / Export CSV** del listino.

### 🖨️ Stampa ESC/POS
- Supporto diretto ai comandi **ESC/POS** per stampanti termiche (taglio automatico, codepage WPC1252 con simbolo €).
- Stampa **raw** via `win32print` (output compatto, byte inviati direttamente alla stampante bypassando il rendering GDI); **fallback** automatico su `QPrinter`/`QTextDocument` se `pywin32` non è disponibile.
- Porte supportate: stampante Windows per nome, **USB**, **COMx**, **LPTx**.
- **Comande separate per categoria**: oltre allo scontrino principale (che contiene sempre tutti i prodotti) è possibile attivare la stampa di una comanda aggiuntiva per singola categoria — utile per inviare gli ordini a postazioni diverse (es. cucina, bar).

### 📡 Sincronizzazione listino via Bluetooth
- Scambio del **listino prezzi tra due dispositivi che eseguono Cashy** tramite **Bluetooth RFCOMM**.
- Usa i socket Bluetooth nativi della libreria standard di Python (`socket.AF_BLUETOOTH` / `BTPROTO_RFCOMM`): **nessuna dipendenza esterna** (compatibile con Python 3.14, dove `pybluez2` non funziona).
- Protocollo applicativo minimale con handshake di conferma (pacchetto JSON length-prefixed + byte di esito ACK/RIFIUTATO/ERRORE); l'utente ricevente conferma o rifiuta l'importazione.
- Scoperta dei dispositivi accoppiati tramite `Get-PnpDevice`, con distinzione tra dispositivi **classic (BR/EDR)** — compatibili RFCOMM — e solo-BLE.

### 🎨 Altro
- Tema **chiaro/scuro**, font Oxanium incluso.
- **Boot splash** all'avvio con numero di versione.

---

## Installazione (utente finale)

1. Avvia **`Cashy-Setup-x.y.z.exe`**.
2. Segui la procedura guidata (in italiano).
3. Avvia Cashy dal menu Start o dall'icona sul desktop.

L'installer contiene **tutto il necessario** (applicazione, runtime Python, librerie Qt): sul computer del cliente **non va installato nient'altro**. La disinstallazione avviene dal Pannello di controllo o dal menu Start.

> I dati (database, configurazione) vengono salvati accanto all'eseguibile e **non** vengono rimossi disinstallando l'app.

---

## Configurazione

Le impostazioni sono modificabili dall'app (sezione Impostazioni) e salvate in `config.json`:

| Chiave | Descrizione |
|---|---|
| `nome_evento` | Nome dell'evento mostrato in testata e sulla ricevuta |
| `data_evento` | Data dell'evento |
| `orario_evento` | Orario dell'evento |
| `messaggio_scontrino` | Messaggio di cortesia stampato in fondo alla ricevuta |
| `porta_stampante` | Nome stampante Windows, oppure `USB` / `COMx` / `LPTx` |
| `numero_progressivo` | Abilita la numerazione progressiva degli ordini |
| `theme` | `dark` o `light` |

---

## Sviluppo e build

### Requisiti
- Windows
- Python 3.14
- Dipendenze: `pip install -r requirements.txt` (PyQt6, psutil, pywin32, pyinstaller)

### Avvio da sorgente
```bash
python main.py
```

### Build dell'applicazione portable (PyInstaller)
```bash
build.bat
```
Genera la cartella autonoma `dist\Cashy\`.

### Creazione dell'installer (Inno Setup)
Richiede [Inno Setup 6](https://jrsoftware.org/isinfo.php) (`winget install JRSoftware.InnoSetup`):
```bash
iscc cashy.iss
```
Produce `Output\Cashy-Setup-x.y.z.exe`.

> **Versione:** allinea sempre `__version__` in `core/version.py` con `MyAppVersion` in `cashy.iss`. Lo splash di avvio legge la prima.

---

## Architettura

```
main.py                 Avvio app, config, tema, splash
core/
  database.py           SQLite: prodotti, categorie, ordini, magazzino (con migrazioni)
  printing.py           Stampa raw ESC/POS (win32print) + fallback QPrinter
  receipt.py            Composizione testo scontrino/comande
  bluetooth_sync.py     Trasporto Bluetooth RFCOMM (stdlib) + scoperta dispositivi
  paths.py              Percorsi app/asset (dev e build congelato)
  version.py            Versione applicazione
ui/
  schermata_cassa.py    Finestra principale (3 pannelli)
  pannello_*.py         Pannelli info / prodotti / carrello
  gestione_prodotti.py  Gestione listino, categorie, magazzino, CSV, BT
  bluetooth_listino.py  Dialoghi invio/ricezione listino via Bluetooth
  storico_ordini.py     Storico e annullamento ordini
  scontrino_dialog.py   Anteprima/stampa ricevuta
  impostazioni.py       Impostazioni evento e stampante
  splash.py             Boot splash
  theme.py              Temi chiaro/scuro e foglio di stile
```

**Stack tecnologico:** Python · PyQt6 · SQLite · ESC/POS · Bluetooth RFCOMM · PyInstaller · Inno Setup.
