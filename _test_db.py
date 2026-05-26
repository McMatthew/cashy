import sys
sys.path.insert(0, ".")
from core.database import DatabaseManager
db = DatabaseManager()
cats = db.get_categorie()
prods = db.get_prodotti_attivi()
print("Categories:", cats)
print("Products count:", len(prods))
for p in prods[:3]:
    print(p["nome"], p["prezzo"], p["categoria"])
