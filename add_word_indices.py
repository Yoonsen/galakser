import sqlite3

def main():
    con = sqlite3.connect('koordinasjoner.db')
    cur = con.cursor()
    
    tables = [
        'avis_og', 'avis_eller', 
        'bok_nob_og', 'bok_nob_eller', 
        'bok_nno_og', 'bok_nno_eller'
    ]
    
    for t in tables:
        print(f"Adding indices for {t}...")
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{t}_w1 ON {t}(word1)")
        cur.execute(f"CREATE INDEX IF NOT EXISTS idx_{t}_w2 ON {t}(word2)")
        
    con.commit()
    con.close()
    print("Done adding word indices.")

if __name__ == '__main__':
    main()
