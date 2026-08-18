import sqlite3

conn = sqlite3.connect('db.sqlite3')
cur = conn.cursor()

cur.execute("SELECT id, name, raw_ingredients FROM api_product WHERE name LIKE '%The Daily Set%'")
row = cur.fetchone()
if row:
    pid, name, raw_ing = row
    print("PRODUCT ID:", pid)
    print("PRODUCT NAME:", name)
    print("PRODUCT RAW INGREDIENTS:", repr(raw_ing))
    
    cur.execute("SELECT i.inci_name FROM api_product_product_ingredients pi JOIN api_ingredient i ON pi.ingredient_id = i.id WHERE pi.product_id = ? ORDER BY pi.order", (pid,))
    ings = [r[0] for r in cur.fetchall()]
    print("LINKED INGREDIENTS COUNT:", len(ings))
    print("LINKED INGREDIENTS:", ings)

    cur.execute("SELECT raw_ingredients FROM api_retailerlisting WHERE product_id = ?", (pid,))
    listings = cur.fetchall()
    for idx, l in enumerate(listings):
        print(f"RETAILER LISTING {idx} RAW INGREDIENTS:", repr(l[0]))
