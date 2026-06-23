import sqlite3
import math
import pyroaring
import os

def build_case_folded_bitmaps(source_db, target_db, table, top_n_limits=[15, 50, 100], min_rn=10, min_freq=5):
    con_src = sqlite3.connect(source_db)
    cur_src = con_src.cursor()
    
    con_dst = sqlite3.connect(target_db)
    cur_dst = con_dst.cursor()
    
    # 1. Bygg skjema for bitmaps
    cur_dst.execute("CREATE TABLE IF NOT EXISTS word_dict (id INTEGER PRIMARY KEY, word TEXT UNIQUE)")
    cur_dst.execute("CREATE INDEX IF NOT EXISTS idx_word_dict ON word_dict(word)")
    cur_dst.execute(f"DROP TABLE IF EXISTS {table}_bitmaps") # Vi sletter den gamle for å bygge på nytt
    cur_dst.execute(f"CREATE TABLE IF NOT EXISTS {table}_bitmaps (word_id INT, top_n INT, neighbors BLOB, PRIMARY KEY (word_id, top_n))")
    
    # 2. Hent all data case-foldet fra kilden og summer opp freq (siden vi slår sammen store/små bokstaver)
    print(f"Reading and case-folding data from {table}...")
    
    # OBS: Siden vi allerede filtrerte på frekvens i export_tables.py, må vi være forsiktige med å aggregere.
    # Det sikreste er å lese fra original rå-tabell, men vi starter med export-tabellen for hastighet.
    cur_src.execute(f"""
        SELECT LOWER(word1), LOWER(word2), SUM(freq)
        FROM {table}
        GROUP BY LOWER(word1), LOWER(word2)
    """)
    
    pairs = {}
    marginals = {}
    N = 0
    
    # Aggregere frekvenser og regn ut nye marginaler
    for row in cur_src:
        w1, w2, f = row
        
        # Symmetrisk
        tup = tuple(sorted((w1, w2)))
        pairs[tup] = pairs.get(tup, 0) + f
        
        marginals[w1] = marginals.get(w1, 0) + f
        marginals[w2] = marginals.get(w2, 0) + f
        N += f
        
    print(f"Total N in case-folded {table}: {N}")
    print(f"Total unique words: {len(marginals)}")
    
    # 3. Bygg word_dict
    word_to_id = {}
    id_to_word = {}
    word_id_counter = 1
    
    # Sorter ord slik at IDene er deterministiske
    for word in sorted(marginals.keys()):
        word_to_id[word] = word_id_counter
        id_to_word[word_id_counter] = word
        word_id_counter += 1
        
    # Sett inn i word_dict i batches
    dict_batch = [(wid, w) for w, wid in word_to_id.items()]
    cur_dst.executemany("INSERT OR IGNORE INTO word_dict (id, word) VALUES (?, ?)", dict_batch)
    con_dst.commit()
    
    # 4. Regn ut ny Radon-Nikodym og samle naboer
    from collections import defaultdict
    neighbors_for_word = defaultdict(list)
    
    print("Calculating RN ratios and collecting neighbors...")
    for (w1, w2), freq_AB in pairs.items():
        f_A = marginals[w1]
        f_B = marginals[w2]
        
        ratio = (freq_AB * N) / (f_A * f_B)
        
        if freq_AB >= min_freq and ratio >= min_rn:
            wid1 = word_to_id[w1]
            wid2 = word_to_id[w2]
            
            neighbors_for_word[wid1].append((wid2, ratio))
            neighbors_for_word[wid2].append((wid1, ratio))

    # Bygg bitmaps for top_n
    bitmaps = {t: {wid: pyroaring.BitMap() for wid in word_to_id.values()} for t in top_n_limits}
    
    print("Sorting neighbors by RN ratio and populating Top N bitmaps...")
    for wid, n_list in neighbors_for_word.items():
        # Sorter synkende på ratio
        n_list.sort(key=lambda x: x[1], reverse=True)
        
        for t in top_n_limits:
            top_neighbors = n_list[:t]
            for neighbor_id, _ in top_neighbors:
                bitmaps[t][wid].add(neighbor_id)
                
    # 5. Lagre bitmaps i SQLite som BLOBs
    print("Serializing and saving Bitmaps to database...")
    insert_sql = f"INSERT OR REPLACE INTO {table}_bitmaps (word_id, top_n, neighbors) VALUES (?, ?, ?)"
    
    for t in top_n_limits:
        batch = []
        for wid, bm in bitmaps[t].items():
            if len(bm) > 0: # Ikke lagre tomme bitmaps
                blob = bm.serialize()
                batch.append((wid, t, blob))
                
            if len(batch) >= 10000:
                cur_dst.executemany(insert_sql, batch)
                batch = []
                
        if batch:
            cur_dst.executemany(insert_sql, batch)
            
    con_dst.commit()
    con_dst.close()
    con_src.close()
    print(f"Done building bitmaps for {table}!")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--table', default='avis_og')
    args = parser.parse_args()
    
    build_case_folded_bitmaps('koordinasjoner.db', 'koordinasjoner_bitmaps.db', args.table)
