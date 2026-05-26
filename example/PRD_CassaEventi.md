# PRD — Cassa Non Fiscale per Eventi
**Product Requirements Document · v1.0**
**Data:** Maggio 2026
**Stato:** Draft



---

## 1. Panoramica del prodotto

### 1.1 Descrizione
Applicazione desktop Windows per la gestione di una cassa non fiscale in contesti di eventi temporanei (sagre, mercati, concerti, fiere, stand gastronomici). Permette di comporre rapidamente un ordine, calcolare il resto e stampare uno scontrino non fiscale tramite stampante termica.

### 1.2 Obiettivo
Fornire uno strumento **semplice, veloce e affidabile** che possa essere usato anche da personale non tecnico, riducendo i tempi di coda e gli errori di cassa durante eventi con alto volume di transazioni.

### 1.3 Target utenti
- Organizzatori e volontari di eventi
- Stand gastronomici e bar temporanei
- Associazioni, sagre, mercati
- Personale con competenze informatiche base

### 1.4 Visual Identity & Design System
*   **Theme Name:** Pro-Efficiency POS
*   **Color Palette:** Dark Mode (Surface: #0b1326), primary action accents in emerald green (#10b981).
*   **Typography:** Inter (Sans-serif) for high legibility in fast-paced environments.
*   **Design Tokens:**
    *   **Roundness:** 8px (Round Eight)
    *   **Spacing:** Touch-target optimized (min 48px).

---

## 2. Contesto e requisiti tecnici

| Voce | Specifica |
|---|---|
| **Piattaforma** | Windows 10 / 11 (desktop) |
| **Linguaggio** | Python 3.11+ |
| **UI framework** | PyQt6 |
| **Database** | SQLite3 (file locale `.db`) |
| **Stampa** | Stampante termica ESC/POS via USB o seriale |
| **Librerie principali** | `pyqt6`, `thermalprinter` / `escpos-python`, `psutil`, `sqlite3` |
| **Distribuzione** | Eseguibile standalone `.exe` (PyInstaller) |
| **Connettività** | Non richiesta (funzionamento offline completo) |

---

## 3. Funzionalità principali

### 3.1 Schermata principale — Cassa (priorità massima)

All'apertura dell'applicazione l'utente accede **direttamente** alla schermata di cassa, senza login o schermate intermedie.

**Layout della schermata:**
- **Colonna sinistra** — Catalogo prodotti: griglia di pulsanti grandi con nome e prezzo di ogni prodotto
- **Colonna destra** — Carrello attivo: lista degli articoli aggiunti, con quantità e subtotale per riga
- **Barra in basso** — Totale, campo importo ricevuto, calcolo resto, pulsante stampa

**Comportamenti attesi:**
- Clic su un prodotto → aggiunto immediatamente al carrello (quantità +1 se già presente)
- Clic sulla riga nel carrello → diminuisce la quantità di 1; se arriva a 0 la riga viene rimossa
- Pulsante `×` su ogni riga carrello → rimozione immediata
- Pulsante `Svuota` → reset del carrello con conferma
- Calcolo del resto in tempo reale mentre l'operatore digita l'importo ricevuto
- Pulsante `Stampa & Incassa` → stampa scontrino e azzera il carrello

### 3.2 Gestione prodotti (priorità alta)

Accessibile tramite menu o pulsante dedicato. Non disponibile durante una transazione attiva.

**Funzionalità:**
- Lista di tutti i prodotti con nome, prezzo e categoria
- Aggiunta di un nuovo prodotto (nome, prezzo, categoria, colore pulsante opzionale)
- Modifica di un prodotto esistente
- Disattivazione (soft delete) di un prodotto — rimane in storico ordini ma non appare in cassa
- Import/export prodotti via file CSV

**Campi prodotto:**

| Campo | Tipo | Obbligatorio |
|---|---|---|
| `id` | Integer PK autoincrement | — |
| `nome` | Text | ✅ |
| `prezzo` | Real | ✅ |
| `categoria` | Text | No |
| `attivo` | Boolean | ✅ (default: true) |
| `colore` | Text (hex) | No |

### 3.3 Calcolo del resto (priorità massima)

- Campo numerico per l'importo consegnato dal cliente
- Resto calcolato e visualizzato in **tempo reale** durante la digitazione
- Suggerimenti rapidi: pulsanti con tagli comuni (€5, €10, €20, €50) che popolano automaticamente il campo
- Resto evidenziato in verde se positivo, in rosso se l'importo è insufficiente

### 3.4 Stampa scontrino (priorità alta)

Lo scontrino non fiscale viene stampato su stampante termica. Contenuto:

```
================================
        [NOME EVENTO]
       [data e ora]
================================
1x Birra Media            €3,50
2x Panino                 €7,00
1x Acqua                  €1,00
--------------------------------
TOTALE                   €11,50
Ricevuto                 €20,00
RESTO                     €8,50
================================
   Grazie e buon divertimento!
================================
```

Configurazioni stampabili:
- Nome evento (modificabile nelle impostazioni)
- Slogan o messaggio di chiusura
- Numero scontrino progressivo (opzionale)

### 3.5 Storico ordini (priorità media)

- Elenco degli ordini della sessione corrente con data/ora e totale
- Possibilità di ristampare uno scontrino passato
- Filtro per data e fascia oraria
- Export in CSV della sessione

### 3.6 Impostazioni (priorità bassa)

- Nome evento e messaggio personalizzato sullo scontrino
- Configurazione porta stampante (COM1, COM2, USB)
- Test di stampa
- Backup manuale del database
- Visualizzazione stato batteria e connessione di rete (tramite `psutil`)

---

## 4. Schema del database

### Tabella `prodotti`
```sql
CREATE TABLE prodotti (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT    NOT NULL,
    prezzo    REAL    NOT NULL,
    categoria TEXT,
    colore    TEXT,
    attivo    INTEGER NOT NULL DEFAULT 1
);
```

### Tabella `ordini`
```sql
CREATE TABLE ordini (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp    TEXT    NOT NULL,
    totale       REAL    NOT NULL,
    ricevuto     REAL    NOT NULL,
    resto        REAL    NOT NULL
);
```

### Tabella `righe_ordine`
```sql
CREATE TABLE righe_ordine (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ordine_id    INTEGER NOT NULL REFERENCES ordini(id),
    prodotto_id  INTEGER REFERENCES prodotti(id),
    nome_snap    TEXT    NOT NULL,
    prezzo_snap  REAL    NOT NULL,
    quantita     INTEGER NOT NULL
);
```

> **Nota:** `nome_snap` e `prezzo_snap` conservano il nome e il prezzo al momento dell'ordine, per garantire la correttezza dello storico anche se il prodotto viene modificato in seguito.

---

## 5. Flusso utente principale

```
Apertura app
     ↓
Schermata Cassa
     ↓
Operatore clicca prodotti → aggiunti al carrello
     ↓
Digita importo ricevuto → resto calcolato in real-time
     ↓
Clic "Stampa & Incassa"
     ↓
Scontrino stampato → carrello azzerato → ordine salvato su DB
     ↓
Pronto per il prossimo cliente
```

---

## 6. Requisiti non funzionali

| Requisito | Specifica |
|---|---|
| **Performance** | Apertura app < 3 secondi; risposta a ogni clic < 100ms |
| **Usabilità** | Operabile interamente con mouse o touchscreen; pulsanti min. 80×60px |
| **Affidabilità** | Nessuna perdita di dati in caso di chiusura inattesa (transazioni SQLite) |
| **Offline-first** | Funzionamento completo senza rete |
| **Portabilità** | App + database contenuti in una singola cartella, spostabile su USB |
| **Stampa** | Timeout e gestione errore se la stampante non è disponibile |
| **Backup** | Il file `.db` è human-readable e portabile |

---

## 7. Architettura dei moduli

```
POSApp/
├── Views/
│   ├── MainWindow.xaml
│   ├── ProductPage.xaml
│   └── SettingsPage.xaml
│
├── Models/
│   ├── Product.cs
│   └── Sale.cs
│
├── Services/
│   ├── DatabaseService.cs
│   ├── PrinterService.cs
│   ├── DeviceService.cs
│   └── ReceiptService.cs
│
├── Data/
│   └── app.db
│
└── App.xaml
```

---

## 8. Roadmap e priorità

### Milestone 1 — MVP (settimane 1–3)
- [ ] Schermata cassa funzionante con carrello
- [ ] Database SQLite con prodotti di esempio
- [ ] Calcolo resto in real-time
- [ ] Stampa scontrino base su stampante termica

### Milestone 2 — Completo (settimane 4–5)
- [ ] CRUD gestione prodotti
- [ ] Storico ordini con ristampa
- [ ] Impostazioni evento e configurazione stampante
- [ ] Stato batteria e rete in status bar

### Milestone 3 — Distribuzione (settimana 6)
- [ ] Build eseguibile `.exe` con PyInstaller
- [ ] Import/export CSV prodotti
- [ ] Test su hardware reale (stampante termica)
- [ ] Documentazione utente

---

## 9. Criteri di accettazione

- Un operatore non tecnico è in grado di completare una transazione in meno di **15 secondi**
- Il database non perde dati in caso di chiusura forzata dell'applicazione
- Lo scontrino viene stampato correttamente entro **2 secondi** dal clic
- L'applicazione si avvia e funziona **senza installazione** di Python o dipendenze esterne
- Il file `.db` può essere aperto e letto con qualsiasi client SQLite standard

---

*PRD redatto per uso interno — soggetto a revisione prima dello sviluppo.*