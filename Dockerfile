# Dockerfile für eine Flask Python Anwendung

# Basis-Image (kann je nach Python-Version angepasst werden)
FROM python:3.10-slim

# Arbeitsverzeichnis erstellen
WORKDIR /app

# Requirements in den Container kopieren
COPY requirements.txt requirements.txt

# Abhängigkeiten installieren
RUN pip install --no-cache-dir -r requirements.txt

# Quellcode in den Container kopieren
COPY . .

# Gunicorn Server starten
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8003", "app:app"]
