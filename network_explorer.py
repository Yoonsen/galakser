import sqlite3
import json
import argparse
import os

class NetworkExplorer:
    def __init__(self, db_path='koordinasjoner.db', bitmap_db_path='koordinasjoner_bitmaps.db'):
        self.con = sqlite3.connect(db_path)
        self.cur = self.con.cursor()
        
        # Sjekk om bitmap db eksisterer
        self.bm_con = None
        self.bm_cur = None
        if os.path.exists(bitmap_db_path):
            self.bm_con = sqlite3.connect(bitmap_db_path)
            self.bm_cur = self.bm_con.cursor()

    def get_neighborhood_roaring(self, start_word, table='avis_og', max_depth=2, top_n=50, sample_k=None, seed=None):
        if not self.bm_cur:
            raise Exception("Bitmap database not found!")
            
        import pyroaring
        
        # 1. Finn ID for startordet (case-folded)
        start_word_lower = start_word.lower()
        self.bm_cur.execute("SELECT id FROM word_dict WHERE word = ?", (start_word_lower,))
        row = self.bm_cur.fetchone()
        if not row:
            return [], []
        start_id = row[0]
        
        # Hjelpefunksjon for å hente bitmap
        def fetch_bm(word_id):
            self.bm_cur.execute(f"SELECT neighbors FROM {table}_bitmaps WHERE word_id = ? AND top_n = ?", (word_id, top_n))
            res = self.bm_cur.fetchone()
            if res:
                return pyroaring.BitMap.deserialize(res[0])
            return pyroaring.BitMap()
            
        import random
        # 2. Utforsk med BFS i minnet ved å gjøre Bitwise OR
        current_layer = pyroaring.BitMap([start_id])
        all_nodes = pyroaring.BitMap([start_id])
        
        for depth in range(1, max_depth + 1):
            next_layer = pyroaring.BitMap()
            import random
            for w_id in current_layer:
                bm = fetch_bm(w_id)
                
                # Beholder mulighet for sampling hvis vi f.eks henter Top 100 men bare vil ha 10 tilfeldige av dem
                if sample_k is not None and len(bm) > sample_k:
                    if seed is not None:
                        # For reproduserbarhet bruker vi hash av seed + word_id
                        # Dette sikrer ulik sampling per node, men lik totalgraf for en gitt seed.
                        rnd = random.Random(hash((seed, w_id)))
                    else:
                        rnd = random.Random() # Ekte randomisering fra system-entropi
                    bm = pyroaring.BitMap(rnd.sample(list(bm), sample_k))
                
                next_layer |= bm
            
            # Fjern noder vi allerede har besøkt
            next_layer -= all_nodes
            all_nodes |= next_layer
            current_layer = next_layer
            
        # 3. Nå har vi all_nodes som er hele klikke-nettverket (garantert fullstendig opp til dybde).
        # Vi vil ha alle interne kanter (klyngesammenskruing er implisitt!)
        edges_set = set()
        
        for w_id in all_nodes:
            bm = fetch_bm(w_id)
            # Finn hvilke naboer som også er med i vårt uthentede nettverk
            internal_neighbors = bm & all_nodes
            
            for n_id in internal_neighbors:
                edge_key = tuple(sorted((w_id, n_id)))
                edges_set.add(edge_key)
                
        # 4. Oversett IDs tilbake til ord
        id_list = list(all_nodes)
        placeholders = ','.join('?' * len(id_list))
        self.bm_cur.execute(f"SELECT id, word FROM word_dict WHERE id IN ({placeholders})", id_list)
        id_to_word = {r[0]: r[1] for r in self.bm_cur.fetchall()}
        
        final_nodes = [id_to_word[w_id] for w_id in all_nodes]
        final_edges = [(id_to_word[u], id_to_word[v], 0, top_n, 0) for u, v in edges_set]
        
        return final_nodes, final_edges

    def get_neighborhood(self, start_word, table, max_depth=2, top_k=20, min_ratio=10.0):
        # We will collect edges as (word1, word2, freq, ratio, pmi)
        edges = {}
        visited_nodes = set()
        
        current_level_words = {start_word}
        all_words_found = {start_word}
        
        for depth in range(1, max_depth + 1):
            next_level_words = set()
            print(f"Level {depth}: Exploring {len(current_level_words)} words...")
            
            for word in current_level_words:
                if word in visited_nodes:
                    continue
                
                visited_nodes.add(word)
                
                # Fetch neighbors where word is word1
                self.cur.execute(f"""
                    SELECT word1, word2, freq, ratio, pmi FROM {table} 
                    WHERE word1 = ? AND ratio >= ?
                    ORDER BY ratio DESC LIMIT ?
                """, (word, min_ratio, top_k))
                
                for row in self.cur.fetchall():
                    w1, w2, freq, ratio, pmi = row
                    edge_key = tuple(sorted((w1, w2)))
                    edges[edge_key] = row
                    next_level_words.add(w2)
                    all_words_found.add(w2)

                # Fetch neighbors where word is word2
                self.cur.execute(f"""
                    SELECT word1, word2, freq, ratio, pmi FROM {table} 
                    WHERE word2 = ? AND ratio >= ?
                    ORDER BY ratio DESC LIMIT ?
                """, (word, min_ratio, top_k))
                
                for row in self.cur.fetchall():
                    w1, w2, freq, ratio, pmi = row
                    edge_key = tuple(sorted((w1, w2)))
                    edges[edge_key] = row
                    next_level_words.add(w1)
                    all_words_found.add(w1)
            
            current_level_words = next_level_words
        
        # Clique-closure step: find all internal cross-connections between all_words_found
        print("Finding internal clique connections...")
        # We process in batches to avoid SQLite IN clause limits (usually 999)
        words_list = list(all_words_found)
        batch_size = 900
        for i in range(0, len(words_list), batch_size):
            batch1 = words_list[i:i+batch_size]
            placeholders1 = ','.join('?' * len(batch1))
            
            for j in range(0, len(words_list), batch_size):
                batch2 = words_list[j:j+batch_size]
                placeholders2 = ','.join('?' * len(batch2))
                
                query = f"""
                    SELECT word1, word2, freq, ratio, pmi FROM {table}
                    WHERE word1 IN ({placeholders1}) AND word2 IN ({placeholders2})
                    AND ratio >= ?
                """
                params = batch1 + batch2 + [min_ratio]
                self.cur.execute(query, params)
                
                for row in self.cur.fetchall():
                    w1, w2, freq, ratio, pmi = row
                    edge_key = tuple(sorted((w1, w2)))
                    if edge_key not in edges:
                        edges[edge_key] = row
                        
        print(f"Extraction complete. Found {len(all_words_found)} nodes and {len(edges)} edges.")
        return list(all_words_found), list(edges.values())

    def get_clustered_json_dict(self, nodes, edges):
        """
        Bygger en linjegraf og kjører Louvain for å få overlappende klynger for noder.
        """
        import networkx as nx
        import community as community_louvain

        # 1. Bygg originalgraf G
        G = nx.Graph()
        G.add_nodes_from(nodes)
        for e in edges:
            G.add_edge(e[0], e[1], freq=e[2], ratio=e[3], pmi=e[4])

        # 2. Bygg Linjegraf L(G)
        L = nx.line_graph(G)

        # 3. Klynge L(G) med Louvain
        # L(G) noder er originalgrafens kanter: f.eks. ('demokrati', 'frihet')
        # Hvis L mangler kanter (dvs stjerne-graf), vil partition fange dem likevel.
        if len(L.nodes()) > 0:
            partition = community_louvain.best_partition(L)
        else:
            partition = {}

        # 4. Map kant-klynger tilbake til noder for overlappende medlemskap
        node_groups = {n: set() for n in nodes}
        for edge_tuple, cluster_id in partition.items():
            u, v = edge_tuple
            node_groups[u].add(cluster_id)
            node_groups[v].add(cluster_id)

        # 5. Bygg JSON responsen
        data = {
            "nodes": [
                {
                    "id": n, 
                    "label": n, 
                    "groups": list(node_groups[n])
                } 
                for n in nodes
            ],
            "links": [
                {
                    "source": e[0], 
                    "target": e[1], 
                    "freq": e[2], 
                    "ratio": e[3], 
                    "pmi": e[4]
                } 
                for e in edges
            ]
        }
        return data

    def export_to_json(self, nodes, edges, output_file='network.json'):
        data = self.get_clustered_json_dict(nodes, edges)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"Exported to {output_file}")

    def close(self):
        self.con.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--word', default='demokrati')
    parser.add_argument('--table', default='avis_og')
    parser.add_argument('--depth', type=int, default=2)
    parser.add_argument('--top_k', type=int, default=20)
    parser.add_argument('--min_ratio', type=float, default=10.0)
    parser.add_argument('--out', default='demokrati_network.json')
    
    args = parser.parse_args()
    
    explorer = NetworkExplorer()
    nodes, edges = explorer.get_neighborhood(args.word, args.table, args.depth, args.top_k, args.min_ratio)
    explorer.export_to_json(nodes, edges, args.out)
    explorer.close()
