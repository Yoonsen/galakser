# Bruk en lett og moderne Python-versjon
FROM python:3.11-slim

# Sett arbeidskatalog i containeren
WORKDIR /app

# Kopier requirements og installer (gjøres først for å utnytte Docker cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopier selve applikasjonskoden
COPY main.py network_explorer.py ./

# Porten FastAPI vil lytte på internt i containeren
EXPOSE 8000

# Definer standard miljøvariabler (kan overstyres)
ENV DB_PATH=/app/data/koordinasjoner.db
ENV ROOT_PATH=""

# Start Uvicorn-serveren og koble FastAPI til ROOT_PATH hvis proxyen (dhlab) krever det
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port 8000 --root-path \"$ROOT_PATH\""]
