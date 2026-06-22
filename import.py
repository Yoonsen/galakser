import sqlite3
import csv
import sys
import os

# Increase max field size for CSV
csv.field_size_limit(sys.maxsize)

db_path = 'koordinasjoner.db'
if os.path.exists(db_path):
    os.remove(db_path)

con = sqlite3.connect(db_path)
cur = con.cursor()

# Performance pragmas
cur.execute('PRAGMA synchronous = OFF')
cur.execute('PRAGMA journal_mode = MEMORY')

cur.execute('''
CREATE TABLE avis (
    freq INTEGER,
    word1 TEXT,
    conjunction TEXT,
    word2 TEXT,
    data JSON
)
''')

cur.execute('''
CREATE TABLE bok (
    freq INTEGER,
    lang TEXT,
    word1 TEXT,
    conjunction TEXT,
    word2 TEXT,
    data JSON
)
''')

def import_table(filename, tablename, cols):
    print(f"Starting import for {tablename}...")
    with open(filename, 'r', encoding='utf-8') as f:
        reader = csv.reader(f, delimiter='|', quoting=csv.QUOTE_NONE)
        batch = []
        q = ', '.join(['?'] * cols)
        sql = f"INSERT INTO {tablename} VALUES ({q})"
        
        for i, row in enumerate(reader):
            if len(row) == cols:
                batch.append(row)
            if len(batch) >= 100000:
                cur.executemany(sql, batch)
                batch = []
            if i % 1000000 == 0 and i > 0:
                print(f"{tablename}: {i} rows processed")
        if batch:
            cur.executemany(sql, batch)
    con.commit()
    print(f"Finished import for {tablename}.")

try:
    import_table('koordinasjoner-avis.tsv', 'avis', 5)
    import_table('koordinasjoner-bok.tsv', 'bok', 6)
finally:
    con.close()
