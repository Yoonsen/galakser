import sqlite3
import math
import argparse

def build_graph(db_path, table, conjunction, lang=None, min_freq=5, min_ratio=1.0):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    
    where_clause = "conjunction = ?"
    params = [conjunction]
    
    if table == 'bok' and lang:
        where_clause += " AND lang = ?"
        params.append(lang)
        
    print("Calculating marginals...")
    
    # Total N
    cur.execute(f"SELECT SUM(freq) FROM {table} WHERE {where_clause}", params)
    N = cur.fetchone()[0]
    if N is None or N == 0:
        print("No data found.")
        return []
        
    # marg_A
    cur.execute(f"SELECT word1, SUM(freq) FROM {table} WHERE {where_clause} GROUP BY word1", params)
    marg_A = {row[0]: row[1] for row in cur.fetchall()}
    
    # marg_B
    cur.execute(f"SELECT word2, SUM(freq) FROM {table} WHERE {where_clause} GROUP BY word2", params)
    marg_B = {row[0]: row[1] for row in cur.fetchall()}
    
    print(f"Total N: {N}, Unique word1: {len(marg_A)}, Unique word2: {len(marg_B)}")
    
    print("Calculating ratios and filtering pairs...")
    
    cur.execute(f"SELECT word1, word2, SUM(freq) FROM {table} WHERE {where_clause} GROUP BY word1, word2 HAVING SUM(freq) >= ?", params + [min_freq])
    
    results = []
    for row in cur:
        w1, w2, freq_AB = row
        f_A = marg_A[w1]
        f_B = marg_B[w2]
        
        ratio = (freq_AB * N) / (f_A * f_B)
        
        if ratio >= min_ratio:
            pmi = math.log2(ratio) if ratio > 0 else 0
            results.append((w1, w2, freq_AB, f_A, f_B, ratio, pmi))
            
    # Sort by frequency descending
    results.sort(key=lambda x: x[2], reverse=True)
    
    con.close()
    return results

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--db', default='koordinasjoner.db')
    parser.add_argument('--table', required=True, choices=['avis', 'bok'])
    parser.add_argument('--conj', required=True, default='og')
    parser.add_argument('--lang', default=None)
    parser.add_argument('--min_freq', type=int, default=10)
    parser.add_argument('--min_ratio', type=float, default=2.0)
    parser.add_argument('--limit', type=int, default=50)
    
    args = parser.parse_args()
    
    res = build_graph(args.db, args.table, args.conj, args.lang, args.min_freq, args.min_ratio)
    
    print(f"\nTop {args.limit} results for {args.table} / {args.conj} (min_freq={args.min_freq}, min_ratio={args.min_ratio}):")
    print(f"{'Word1':<20} {'Word2':<20} {'Freq':<10} {'Ratio':<10} {'PMI':<10}")
    print("-" * 75)
    for w1, w2, freq, f_A, f_B, ratio, pmi in res[:args.limit]:
        print(f"{str(w1)[:19]:<20} {str(w2)[:19]:<20} {freq:<10} {ratio:<10.2f} {pmi:<10.2f}")
