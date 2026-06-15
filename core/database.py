import sqlite3
import csv
import os
from pathlib import Path

from core.paths import get_app_dir

DB_PATH = get_app_dir() / "data" / "cashy.db"

SEED_PRODUCTS = [
    ("Birra Media", 3.50, "Bevande", "#1a3a5c"),
    ("Birra Grande", 5.00, "Bevande", "#1a3a5c"),
    ("Acqua", 1.00, "Bevande", "#1a4a5c"),
    ("Bibita", 2.00, "Bevande", "#1a4a5c"),
    ("Vino Rosso", 3.00, "Vino", "#4a1a2c"),
    ("Vino Bianco", 3.00, "Vino", "#3a3a1a"),
    ("Panino", 3.50, "Cibo", "#3a2a1a"),
    ("Hamburger", 5.00, "Cibo", "#3a2a1a"),
    ("Patatine", 2.50, "Cibo", "#3a3a1a"),
    ("Pizza", 4.00, "Cibo", "#4a2a1a"),
    ("Caffè", 1.50, "Bar", "#2a1a0a"),
    ("Amaro", 3.00, "Bar", "#1a2a1a"),
]


class DatabaseManager:
    def __init__(self):
        DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS prodotti (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL,
                    prezzo REAL NOT NULL,
                    categoria TEXT NOT NULL DEFAULT '',
                    colore TEXT NOT NULL DEFAULT '#1a2a3a',
                    attivo INTEGER NOT NULL DEFAULT 1
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS ordini (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    data_ora TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                    totale REAL NOT NULL,
                    ricevuto REAL NOT NULL,
                    resto REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS righe_ordine (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ordine_id INTEGER NOT NULL REFERENCES ordini(id),
                    prodotto_id INTEGER,
                    nome_snap TEXT NOT NULL,
                    prezzo_snap REAL NOT NULL,
                    quantita INTEGER NOT NULL DEFAULT 1
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS categorie (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome TEXT NOT NULL UNIQUE,
                    scontrino_separato INTEGER NOT NULL DEFAULT 0
                )
            """)
            conn.commit()
            # Migrate: add foto column if missing
            cols = [c["name"] for c in conn.execute("PRAGMA table_info(prodotti)").fetchall()]
            if "foto" not in cols:
                conn.execute("ALTER TABLE prodotti ADD COLUMN foto TEXT NOT NULL DEFAULT ''")
                conn.commit()
            # Migrate: add quantita_magazzino column if missing (NULL = scorta illimitata)
            if "quantita_magazzino" not in cols:
                conn.execute("ALTER TABLE prodotti ADD COLUMN quantita_magazzino INTEGER")
                conn.commit()
            # Seed prodotti if empty
            row = conn.execute("SELECT COUNT(*) as cnt FROM prodotti").fetchone()
            if row["cnt"] == 0:
                conn.executemany(
                    "INSERT INTO prodotti (nome, prezzo, categoria, colore) VALUES (?,?,?,?)",
                    SEED_PRODUCTS,
                )
                conn.commit()
            # Populate categorie from prodotti if empty
            cat_cnt = conn.execute("SELECT COUNT(*) as cnt FROM categorie").fetchone()
            if cat_cnt["cnt"] == 0:
                cats = conn.execute(
                    "SELECT DISTINCT categoria FROM prodotti WHERE categoria != '' ORDER BY categoria"
                ).fetchall()
                for c in cats:
                    conn.execute("INSERT OR IGNORE INTO categorie (nome) VALUES (?)", (c["categoria"],))
                conn.commit()

    def get_prodotti_attivi(self):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM prodotti WHERE attivo=1 ORDER BY categoria, nome"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_prodotti_tutti(self):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM prodotti ORDER BY attivo DESC, categoria, nome"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_categorie(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute("SELECT nome FROM categorie ORDER BY nome").fetchall()
        return [r["nome"] for r in rows]

    def get_categorie_full(self) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute("SELECT * FROM categorie ORDER BY nome").fetchall()
        return [dict(r) for r in rows]

    def aggiungi_categoria(self, nome: str) -> bool:
        """Insert a new category. Returns False if name already exists."""
        try:
            with self._connect() as conn:
                conn.execute("INSERT INTO categorie (nome) VALUES (?)", (nome,))
                conn.commit()
            return True
        except Exception:
            return False

    def elimina_categoria(self, cat_id: int) -> int:
        """Delete a category. Returns count of active products still using it (0 = deleted ok)."""
        with self._connect() as conn:
            cat = conn.execute("SELECT nome FROM categorie WHERE id=?", (cat_id,)).fetchone()
            if not cat:
                return 0
            count = conn.execute(
                "SELECT COUNT(*) as cnt FROM prodotti WHERE categoria=? AND attivo=1",
                (cat["nome"],)
            ).fetchone()["cnt"]
            if count > 0:
                return count
            conn.execute("DELETE FROM categorie WHERE id=?", (cat_id,))
            conn.commit()
        return 0

    def set_scontrino_separato(self, cat_id: int, valore: bool):
        with self._connect() as conn:
            conn.execute(
                "UPDATE categorie SET scontrino_separato=? WHERE id=?",
                (int(valore), cat_id)
            )
            conn.commit()

    def get_nomi_categorie_separate(self) -> set[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT nome FROM categorie WHERE scontrino_separato=1"
            ).fetchall()
        return {r["nome"] for r in rows}

    def aggiungi_prodotto(self, nome, prezzo, categoria, colore, foto="", quantita_magazzino=None):
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO prodotti (nome, prezzo, categoria, colore, foto, quantita_magazzino) VALUES (?,?,?,?,?,?)",
                (nome, prezzo, categoria, colore, foto, quantita_magazzino),
            )
            if categoria:
                conn.execute("INSERT OR IGNORE INTO categorie (nome) VALUES (?)", (categoria,))
            conn.commit()

    def modifica_prodotto(self, pid, nome, prezzo, categoria, colore, attivo, foto="", quantita_magazzino=None):
        with self._connect() as conn:
            conn.execute(
                "UPDATE prodotti SET nome=?, prezzo=?, categoria=?, colore=?, attivo=?, foto=?, quantita_magazzino=? WHERE id=?",
                (nome, prezzo, categoria, colore, int(attivo), foto, quantita_magazzino, pid),
            )
            if categoria:
                conn.execute("INSERT OR IGNORE INTO categorie (nome) VALUES (?)", (categoria,))
            conn.commit()

    def elimina_prodotto(self, pid):
        with self._connect() as conn:
            conn.execute("UPDATE prodotti SET attivo=0 WHERE id=?", (pid,))
            conn.commit()

    def salva_ordine(self, righe, totale, ricevuto, resto):
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO ordini (totale, ricevuto, resto) VALUES (?,?,?)",
                (totale, ricevuto, resto),
            )
            ordine_id = cur.lastrowid
            for r in righe:
                conn.execute(
                    "INSERT INTO righe_ordine (ordine_id, prodotto_id, nome_snap, prezzo_snap, quantita) VALUES (?,?,?,?,?)",
                    (ordine_id, r["id"], r["nome"], r["prezzo"], r["quantita"]),
                )
                # Scala il magazzino solo se il prodotto ne tiene traccia (quantita_magazzino non NULL).
                # NULL = scorta illimitata, non viene mai decrementata.
                if r["id"] is not None:
                    conn.execute(
                        "UPDATE prodotti SET quantita_magazzino = MAX(quantita_magazzino - ?, 0) "
                        "WHERE id=? AND quantita_magazzino IS NOT NULL",
                        (r["quantita"], r["id"]),
                    )
            conn.commit()
        return ordine_id

    def get_ordine_by_id(self, ordine_id: int):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM ordini WHERE id=?", (ordine_id,)
            ).fetchone()
        return dict(row) if row else None

    def get_last_order(self):
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM ordini ORDER BY id DESC LIMIT 1"
            ).fetchone()
        return dict(row) if row else None

    def get_righe_ordine(self, ordine_id):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM righe_ordine WHERE ordine_id=?", (ordine_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_ordini(self):
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM ordini ORDER BY id DESC"
            ).fetchall()
        return [dict(r) for r in rows]

    def get_next_numero(self):
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) as cnt FROM ordini").fetchone()
        return (row["cnt"] or 0) + 1

    def get_resoconto_per_ordini(self, ordine_ids: list[int]) -> list[dict]:
        """Aggregate product quantities and revenue for the given order IDs."""
        if not ordine_ids:
            return []
        placeholders = ",".join("?" * len(ordine_ids))
        with self._connect() as conn:
            rows = conn.execute(f"""
                SELECT
                    nome_snap        AS nome,
                    prezzo_snap      AS prezzo_unit,
                    SUM(quantita)    AS quantita,
                    SUM(quantita * prezzo_snap) AS incasso
                FROM righe_ordine
                WHERE ordine_id IN ({placeholders})
                GROUP BY nome_snap, prezzo_snap
                ORDER BY incasso DESC
            """, ordine_ids).fetchall()
        return [dict(r) for r in rows]

    def export_csv_prodotti(self, path):
        prodotti = self.get_prodotti_tutti()
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=["id", "nome", "prezzo", "categoria", "colore", "attivo", "foto", "quantita_magazzino"],
            )
            writer.writeheader()
            writer.writerows(prodotti)

    def import_csv_prodotti(self, path):
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            with self._connect() as conn:
                for row in reader:
                    try:
                        nome = row["nome"]
                        prezzo = float(row["prezzo"])
                        categoria = row.get("categoria", "")
                        colore = row.get("colore", "#1a2a3a")
                        qm_raw = (row.get("quantita_magazzino") or "").strip()
                        quantita_magazzino = int(qm_raw) if qm_raw else None
                        conn.execute(
                            "INSERT INTO prodotti (nome, prezzo, categoria, colore, quantita_magazzino) VALUES (?,?,?,?,?)",
                            (nome, prezzo, categoria, colore, quantita_magazzino),
                        )
                    except (KeyError, ValueError):
                        continue
                conn.commit()

    def annulla_ordine(self, ordine_id: int):
        with self._connect() as conn:
            # Ripristina il magazzino per i prodotti tracciati prima di eliminare le righe.
            righe = conn.execute(
                "SELECT prodotto_id, quantita FROM righe_ordine WHERE ordine_id = ?", (ordine_id,)
            ).fetchall()
            for r in righe:
                if r["prodotto_id"] is not None:
                    conn.execute(
                        "UPDATE prodotti SET quantita_magazzino = quantita_magazzino + ? "
                        "WHERE id=? AND quantita_magazzino IS NOT NULL",
                        (r["quantita"], r["prodotto_id"]),
                    )
            conn.execute("DELETE FROM righe_ordine WHERE ordine_id = ?", (ordine_id,))
            conn.execute("DELETE FROM ordini WHERE id = ?", (ordine_id,))
            conn.commit()

    def export_csv_ordini(self, path):
        with self._connect() as conn:
            ordini = conn.execute("SELECT * FROM ordini ORDER BY id DESC").fetchall()
            righe = conn.execute("SELECT * FROM righe_ordine").fetchall()
        ordini_list = [dict(o) for o in ordini]
        righe_list = [dict(r) for r in righe]
        righe_map = {}
        for r in righe_list:
            righe_map.setdefault(r["ordine_id"], []).append(r)
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["ordine_id", "data_ora", "totale", "ricevuto", "resto", "prodotto", "quantita", "prezzo_snap"])
            for o in ordini_list:
                for r in righe_map.get(o["id"], []):
                    writer.writerow([
                        o["id"], o["data_ora"], o["totale"], o["ricevuto"], o["resto"],
                        r["nome_snap"], r["quantita"], r["prezzo_snap"],
                    ])
