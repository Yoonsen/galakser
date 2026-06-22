# Manifest: Prosjekt Galakser

## Visjon og Formål
"Galakser" er et prosjekt for å analysere, utvinne og visualisere ordnettverk bygget på koordinasjoner ("og" / "eller") fra store norske tekstkorpus. 

Hovedmålet er å skille mellom synonym-lignende relasjoner (som ofte opptrer med "eller") og konseptuelt tilknyttede relasjoner (som ofte opptrer med "og"). Dette gjøres for ulike granulat, slik som sjangre (avis vs. bok) og målformer (bokmål vs. nynorsk).

## Domenekunnskap og Metode
- Siden rådataene består av trigrammer ("A og/eller B"), inneholder de mye "spuriøs" støy fra frasekoordinasjoner (f.eks. "en mann og en kvinne" -> "mann og en").
- For å filtrere bort dette støyet, og kun beholde sanne logiske koordinasjoner, benytter vi en frekvens-basert **Radon-Nikodym ratio** (PMI uten logaritme) kombinert med PMI (Pointwise Mutual Information).
- Høy ratio (f.eks. > 10 eller 50) korrelerer sterkt med meningsbærende relasjoner.
- Vi bevarer tegnsetting (som komma og utropstegn) i databasen, da de lett kan filtreres bort i SQL, men også kan bære domenespesifikk informasjon (f.eks. klokkeslett-koordinasjoner for radio/TV-sjangre).

## Nåværende Status
- Omtrent 2.5 GB med rå TSV-data er prosessert og importert til en SQLite-database (`koordinasjoner.db`).
- Utregning av marginaler og ratiokalkulering er fullført.
- **Ferdige eksporttabeller** er tilgjengelige i databasen for umiddelbar spørring:
  - `avis_og`
  - `avis_eller`
  - `bok_nob_og`
  - `bok_nob_eller`
  - `bok_nno_og`
  - `bok_nno_eller`
- Et Python-skript (`network_explorer.py`) er utviklet for å kjøre BFS (Breadth-First Search) til Dybde $D$ (f.eks. 3) for å hente ut klynger og eksportere dem som graf-tilpasset JSON.

## Videre Fremdriftsplan (TODO)
1. Etablere FastAPI backend.
2. Legge inn clustering-algoritmer (f.eks. Louvain) i backend-rørledningen.
3. Kontainerisering av SQLite + FastAPI i Docker.
4. Utvikle Javascript frontend for force-directed nettverksvisning.
