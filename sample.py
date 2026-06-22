import sqlite3
import random

con = sqlite3.connect('koordinasjoner.db')
cur = con.cursor()

# Get marginals for 'og' in 'avis'
cur.execute("SELECT SUM(freq) FROM avis WHERE conjunction = 'og'")
N = cur.fetchone()[0]

cur.execute("SELECT word1, SUM(freq) FROM avis WHERE conjunction = 'og' GROUP BY word1")
marg_A = {row[0]: row[1] for row in cur.fetchall()}

cur.execute("SELECT word2, SUM(freq) FROM avis WHERE conjunction = 'og' GROUP BY word2")
marg_B = {row[0]: row[1] for row in cur.fetchall()}

# Iterate through pairs and find some with ratio around 10 and 5
ratio_100 = []
ratio_50 = []

# Fetch a chunk of pairs
cur.execute("SELECT word1, word2, SUM(freq) FROM avis WHERE conjunction = 'og' GROUP BY word1, word2 HAVING SUM(freq) > 100")

for row in cur:
    w1, w2, freq = row
    f_A = marg_A[w1]
    f_B = marg_B[w2]
    
    ratio = (freq * N) / (f_A * f_B)
    
    if 95.0 <= ratio <= 105.0:
        ratio_100.append((w1, w2, freq, ratio))
    elif 45.0 <= ratio <= 55.0:
        ratio_50.append((w1, w2, freq, ratio))
        
    if len(ratio_100) > 1000 and len(ratio_50) > 1000:
        break

print("=== SAMPLES MED RATIO ~100 ===")
for w1, w2, freq, ratio in random.sample(ratio_100, min(10, len(ratio_100))):
    print(f"{w1:20} og {w2:20} (Freq: {freq:5}, Ratio: {ratio:.2f})")

print("\n=== SAMPLES MED RATIO ~50 ===")
for w1, w2, freq, ratio in random.sample(ratio_50, min(10, len(ratio_50))):
    print(f"{w1:20} og {w2:20} (Freq: {freq:5}, Ratio: {ratio:.2f})")


con.close()
