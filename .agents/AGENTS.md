# Prosjekt Galakser: Agent-instruksjoner

Dette dokumentet inneholder prosjekt-spesifikke regler og retningslinjer for kunstig intelligens som jobber med prosjektet "Galakser".

## Kjerneinstrukser for nye agenter
Når du starter en ny sesjon eller får en oppgave i dette prosjektet, MÅ du lese de følgende filene for å få full kontekst over hva vi bygger og de tekniske valgene vi har tatt:
1. Les `manifest.md` for å forstå prosjektets formål, status og domenekunnskap.
2. Les `architecture.md` for å forstå databasestrukturen og ansvarsfordelingen mellom frontend og backend.

## Koderegler og Teknologi
- **Backend:** Skal skrives i Python med FastAPI. SQLite brukes som database.
- **Frontend:** Utvikles i Javascript (f.eks. D3.js eller vis-network). Frontend skal fokusere på interaktivitet og layout, ikke tunge algoritmer.
- **Nettverksalgoritmer:** All community detection (klynging, f.eks. Louvain) SKAL utføres av Python-backend før data sendes til frontend.
- **Søk:** Bruk alltid de ferdig-eksporterte tabellene i `koordinasjoner.db` med indekser på `word1`, `word2`, `ratio` og `freq` fremfor å prosessere rådataene på nytt.
