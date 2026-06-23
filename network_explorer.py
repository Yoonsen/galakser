import sqlite3
import json
import argparse
import os
import pyroaring
import random
from contextlib import closing

class NetworkExplorer:
    def __init__(self, db_path='koordinasjoner.db', bitmap_db_path='koordinasjoner_bitmaps.db'):
        self.db_path = db_path
        self.bitmap_db_path = bitmap_db_path
        
    def has_bitmaps(self):
        return os.path.exists(self.bitmap_db_path)

    def get_neighborhood_roaring(self, start_word, table='avis_og', max_depth=2, top_n=50, sample_k=None, seed=None):
        if not self.has_bitmaps():
            raise Exception("Bitmap database not found!")
            
        with closing(sqlite3.connect(self.bitmap_db_path)) as bm_con:
            bm_cur = bm_con.cursor()
            
            # 1. Finn ID for startordet (case-folded)
            start_word_lower = start_word.lower()
            bm_cur.execute("SELECT id FROM word_dict WHERE word = ?", (start_word_lower,))
            row = bm_cur.fetchone()
            if not row:
                return [], []
            start_id = row[0]
            
            # Hjelpefunksjon for å hente bitmap
            def fetch_bm(word_id):
                bm_cur.execute(f"SELECT neighbors FROM {table}_bitmaps WHERE word_id = ? AND top_n = ?", (word_id, top_n))
                res = bm_cur.fetchone()
                if res:
                    return pyroaring.BitMap.deserialize(res[0])
                return pyroaring.BitMap()
                
            # 2. BFS
            all_nodes = pyroaring.BitMap([start_id])
            current_layer = pyroaring.BitMap([start_id])
            
            for depth in range(1, max_depth + 1):
                next_layer = pyroaring.BitMap()
                
                for w_id in current_layer:
                    bm = fetch_bm(w_id)
                    
                    if sample_k is not None and len(bm) > sample_k:
                        if seed is not None:
                            rnd = random.Random(hash((seed, w_id)))
                        else:
                            rnd = random.Random()
                        bm = pyroaring.BitMap(rnd.sample(list(bm), sample_k))
                    
                    next_layer |= bm
                
                next_layer -= all_nodes
                all_nodes |= next_layer
                current_layer = next_layer
                
            # 3. Hent kanter
            edges_set = set()
            for w_id in all_nodes:
                bm = fetch_bm(w_id)
                internal_neighbors = bm & all_nodes
                
                for n_id in internal_neighbors:
                    edge_key = tuple(sorted((w_id, n_id)))
                    edges_set.add(edge_key)
                    
            # 4. Oversett IDs
            id_list = list(all_nodes)
            placeholders = ','.join('?' * len(id_list))
            bm_cur.execute(f"SELECT id, word FROM word_dict WHERE id IN ({placeholders})", id_list)
            id_to_word = {r[0]: r[1] for r in bm_cur.fetchall()}
            
            final_nodes = [id_to_word.get(w_id, f"unknown_{w_id}") for w_id in all_nodes]
            final_edges = [(id_to_word.get(u, f"unknown_{u}"), id_to_word.get(v, f"unknown_{v}"), 0, top_n, 0) for u, v in edges_set]
            
            return final_nodes, final_edges

    def get_neighborhood(self, start_word, table, max_depth=2, top_k=20, min_ratio=10.0):
        with closing(sqlite3.connect(self.db_path)) as con:
            cur = con.cursor()
            
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
                
                    cur.execute(f"""
                        SELECT word1, word2, freq, ratio, pmi FROM {table} 
                        WHERE word1 = ? AND ratio >= ?
                        ORDER BY ratio DESC LIMIT ?
                    """, (word, min_ratio, top_k))
                
                    for row in cur.fetchall():
                        w1, w2, freq, ratio, pmi = row
                        edge_key = tuple(sorted((w1, w2)))
                        edges[edge_key] = row
                        next_level_words.add(w2)
                        all_words_found.add(w2)

                    cur.execute(f"""
                        SELECT word1, word2, freq, ratio, pmi FROM {table} 
                        WHERE word2 = ? AND ratio >= ?
                        ORDER BY ratio DESC LIMIT ?
                    """, (word, min_ratio, top_k))
                
                    for row in cur.fetchall():
                        w1, w2, freq, ratio, pmi = row
                        edge_key = tuple(sorted((w1, w2)))
                        edges[edge_key] = row
                        next_level_words.add(w1)
                        all_words_found.add(w1)
            
                current_level_words = next_level_words
        
            print("Finding internal clique connections...")
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
                    cur.execute(query, params)
                
                    for row in cur.fetchall():
                        w1, w2, freq, ratio, pmi = row
                        edge_key = tuple(sorted((w1, w2)))
                        if edge_key not in edges:
                            edges[edge_key] = row
                        
            print(f"Extraction complete. Found {len(all_words_found)} nodes and {len(edges)} edges.")
            return list(all_words_found), list(edges.values())

    def get_clustered_json_dict(self, nodes, edges):
        import networkx as nx
        import community as community_louvain

        G = nx.Graph()
        G.add_nodes_from(nodes)
        for e in edges:
            G.add_edge(e[0], e[1], freq=e[2], ratio=e[3], pmi=e[4])

        L = nx.line_graph(G)

        if len(L.nodes()) > 0:
            partition = community_louvain.best_partition(L)
        else:
            partition = {}

        node_groups = {n: set() for n in nodes}
        for edge_tuple, cluster_id in partition.items():
            u, v = edge_tuple
            node_groups[u].add(cluster_id)
            node_groups[v].add(cluster_id)

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

