import sqlite3
import math
import sys

def create_export_table(cur, con, source_table, conjunction, lang, target_table, min_freq=5):
    print(f"Creating {target_table}...")
    
    cur.execute(f"DROP TABLE IF EXISTS {target_table}")
    cur.execute(f'''
    CREATE TABLE {target_table} (
        word1 TEXT,
        word2 TEXT,
        freq INTEGER,
        ratio REAL,
        pmi REAL
    )
    ''')
    
    where_clause = "conjunction = ?"
    params = [conjunction]
    
    if source_table == 'bok' and lang:
        where_clause += " AND lang = ?"
        params.append(lang)
        
    # Total N
    cur.execute(f"SELECT SUM(freq) FROM {source_table} WHERE {where_clause}", params)
    N = cur.fetchone()[0]
    if N is None or N == 0:
        print(f"No data for {target_table}")
        return
        
    print("Fetching marginals...")
    cur.execute(f"SELECT word1, SUM(freq) FROM {source_table} WHERE {where_clause} GROUP BY word1", params)
    marg_A = {row[0]: row[1] for row in cur.fetchall()}
    
    cur.execute(f"SELECT word2, SUM(freq) FROM {source_table} WHERE {where_clause} GROUP BY word2", params)
    marg_B = {row[0]: row[1] for row in cur.fetchall()}
    
    print("Calculating and inserting pairs...")
    
    select_cur = con.cursor()
    insert_cur = con.cursor()
    
    select_cur.execute(f"SELECT word1, word2, SUM(freq) FROM {source_table} WHERE {where_clause} GROUP BY word1, word2 HAVING SUM(freq) >= ?", params + [min_freq])
    
    batch = []
    insert_sql = f"INSERT INTO {target_table} VALUES (?, ?, ?, ?, ?)"
    count = 0
    for row in select_cur:
        w1, w2, freq_AB = row
        f_A = marg_A.get(w1, 1)
        f_B = marg_B.get(w2, 1)
        
        ratio = (freq_AB * N) / (f_A * f_B)
        pmi = math.log2(ratio) if ratio > 0 else 0
        
        batch.append((w1, w2, freq_AB, ratio, pmi))
        if len(batch) >= 100000:
            insert_cur.executemany(insert_sql, batch)
            count += len(batch)
            print(f"  Inserted {count} rows...")
            batch = []
            
    if batch:
        insert_cur.executemany(insert_sql, batch)
        count += len(batch)
        print(f"  Inserted {count} rows...")
        
    con.commit()
    
    # Create indices for the new table for fast querying
    cur.execute(f"CREATE INDEX idx_{target_table}_freq ON {target_table}(freq)")
    cur.execute(f"CREATE INDEX idx_{target_table}_ratio ON {target_table}(ratio)")
    
    print(f"Done with {target_table}.")

def main():
    db_path = 'koordinasjoner.db'
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    cur.execute('PRAGMA synchronous = OFF')
    cur.execute('PRAGMA journal_mode = MEMORY')
    
    configs = [
        ('avis', 'og', None, 'avis_og'),
        ('avis', 'eller', None, 'avis_eller'),
        ('bok', 'og', 'nob', 'bok_nob_og'),
        ('bok', 'eller', 'nob', 'bok_nob_eller'),
        ('bok', 'og', 'nno', 'bok_nno_og'),
        ('bok', 'eller', 'nno', 'bok_nno_eller')
    ]
    
    for source_table, conjunction, lang, target_table in configs:
        create_export_table(cur, con, source_table, conjunction, lang, target_table, min_freq=5)
        
    con.close()
    print("All exports finished successfully.")

if __name__ == '__main__':
    main()
