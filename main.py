import os
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from network_explorer import NetworkExplorer

# Hent root_path fra miljøvariabel (viktig for dhlab proxy)
ROOT_PATH = os.getenv("ROOT_PATH", "")

app = FastAPI(title="Galakser Backend", version="1.0", root_path=ROOT_PATH)

# Setup CORS for frontend to communicate
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Koble til databasen angitt av DB_PATH miljøvariabel, fallback til lokal fil
DB_PATH = os.getenv("DB_PATH", "koordinasjoner.db")
explorer = NetworkExplorer(DB_PATH)

@app.get("/api/network")
def get_network(
    word: str = Query(..., description="Startordet for utforskningen"),
    table: str = Query("avis_og", description="Tabellen som skal søkes i (f.eks. avis_og, bok_nob_eller)"),
    depth: int = Query(2, description="Dybde for BFS (maks 3)"),
    top_k: int = Query(20, description="Maks antall naboer per node for B-trær"),
    min_ratio: float = Query(10.0, description="Minimum RN ratio for B-trær"),
    use_bitmaps: bool = Query(True, description="Bruk Roaring Bitmaps for ekstrem ytelse"),
    top_n: int = Query(50, description="Hvilken Top N bitmap som skal brukes (f.eks. 15, 50, 100)"),
    sample_k: int = Query(None, description="Valgfri ned-sampling fra Top N"),
    seed: int = Query(None, description="Valgfri seed for reproduserbar sampling")
):
    # Cap depth to prevent abuse/performance issues
    safe_depth = min(depth, 3)
    
    # 1. Hent rå-grafen via BFS eller Bitmaps
    if use_bitmaps and explorer.bm_cur is not None:
        nodes, edges = explorer.get_neighborhood_roaring(word, table, safe_depth, top_n, sample_k, seed)
    else:
        nodes, edges = explorer.get_neighborhood(word, table, safe_depth, top_k, min_ratio)
    
    # 2. Legg til overlappende klynger (Line Graph Clustering)
    clustered_data = explorer.get_clustered_json_dict(nodes, edges)
    
    return clustered_data
