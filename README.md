# Installation steps

## Deployment

### Step 1 - Create config

```
cd app
cp config.py.example config.py
vi config.py
cd ../
```

### Step 2 - Compose and run

```
docker compose up -d --build
```

## Development

```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```

Then go to http://localhost:8003/
