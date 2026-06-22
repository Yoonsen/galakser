# Arkitektur for Galakser

Dette dokumentet definerer den tekniske arkitekturen og designbeslutningene for Galakser-applikasjonen.

## 1. Databaselag (SQLite)
Vi benytter SQLite (`koordinasjoner.db`) da datamengden (titalls millioner rader) håndteres lynraskt gitt korrekte indekser, og muliggjør enkle, portofrie lesinger.

### Skjema for filtrerte tabeller (f.eks. `avis_og`):
- `word1` (TEXT)
- `word2` (TEXT)
- `freq` (INTEGER) - Samlet frekvens for "word1 [conjunction] word2"
- `ratio` (REAL) - Radon-Nikodym ratio. Formel: $(freq_{AB} \times N) / (freq_A \times freq_B)$
- `pmi` (REAL) - Pointwise Mutual Information. Formel: $\log_2(ratio)$

**Indekser:** Det er kritisk at alle disse tabellene har indekser på `word1`, `word2`, `freq`, og `ratio` for å støtte umiddelbare relasjonsoppslag (O(1) / O(log N)).

## 2. Arbeidsdeling: Backend vs. Frontend
For å sikre en performant og skalerbar web-applikasjon, fordeles ansvaret strengt mellom Python (Backend) og Javascript (Frontend).

### Backend (Python + FastAPI)
Ansvarlig for "Tunge løft" og "Business Logic".
- **Database-spørringer:** Utfører BFS (Breadth-First Search) via SQLite (se algoritmen i `network_explorer.py`).
- **Klynging med Overlapp (Line Graph Clustering):** For å løse utfordringen med at klikk-klynger mister mange noder, mens standard Louvain/Leiden på nodenivå ikke tillater overlapp (en node får kun én klynge), vil backend implementere **Linjegraf-klynging (Link Community Detection)**.
  - *Metode:* Algoritmen bygger linjegrafen $L(G)$ der kantene fra originalgrafen blir nodene. Deretter kjøres f.eks. Louvain på $L(G)$. Siden en opprinnelig node kan være del av flere opprinnelige kanter (som nå ligger i ulike klynger), vil utpakkingen av disse gi *overlappende klynger* i originalgrafen! Dette passer perfekt for ord som har distinkte semantiske betydninger i ulike kontekster (f.eks. "demokrati" kan tilhøre både en jus-klynge og en politikk-klynge).
  - All graf-matematikk og utpakking gjøres i Python (f.eks. med `NetworkX.line_graph`) før nodene stemples med et array av `group_ids` og returneres til frontend.

### Frontend (Javascript / D3.js / Vis.js)
Ansvarlig for rendering, fysikk og interaksjon.
- **Layout:** Utfører nettverksfysikk (Force-directed layout) i nettleseren ved bruk av WebGL/Canvas for høy oppdateringsfrekvens. Nodene plasseres organisk, avstøter hverandre, og trekkes sammen av lenkene ("fjærene").
- **Stilisering:** Bruker `group_id` fra backend til å fargekode noder. Tykkelsen på lenkene kan bindes til `ratio` eller `pmi`.
- **Interaksjon:** Håndterer dra-og-slipp av noder, zoom, og klikk-events (f.eks. å klikke på en node fyrer av et nytt asynkront kall til backend for å utvide nettverket fra dette nye ordet).

## 3. Infrastruktur (Docker)
Applikasjonen pakkes som en mikrotjeneste.
- En Dockerfile bygger et image med Python, FastAPI-avhengigheter, og baker inn `koordinasjoner.db`. Dette gjør det trivielt å deploye på en intern server og utsette API-et på en angitt port uten konfigurasjonsvansker.
