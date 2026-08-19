# Warehouse Backend

FastAPI backend for Whitfield Fulfillment. Supabase PostgreSQL is the required
runtime database. MongoDB is used only by the optional one-time migration tool.

## Request flow

```text
routes -> authentication/permissions -> controllers/services -> CRUD repositories
       -> AsyncPG -> Supabase PostgreSQL
```

Expected inbound completion runs inside one PostgreSQL transaction so shipment,
inventory, transaction, damage, and audit changes roll back together on failure.

## Structure

```text
warehouse-backend/
|-- main.py                         # FastAPI/Uvicorn entry point
|-- core/
|   |-- apis/routes/                # REST endpoints
|   |-- apis/schemas/               # Request validation
|   |-- controllers/                # Request orchestration
|   |-- cruds/                      # Database-neutral repositories
|   |-- database/postgres.py        # AsyncPG adapter and transactions
|   |-- dependencies/               # JWT and role checks
|   |-- models/                     # Domain models
|   `-- services/                   # Warehouse workflows
|-- scripts/                        # Migration, audit, smoke, and admin tools
|-- supabase_schema.sql             # Tables, repairs, and indexes
`-- tests/                           # Backend test suite
```

## Environment

Copy `.env.example` to the ignored `.env` file and configure:

```text
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_DB_PASSWORD=YOUR_DATABASE_PASSWORD
SUPABASE_DB_REGION=YOUR_POOLER_REGION
JWT_SECRET_KEY=YOUR_LONG_RANDOM_SECRET
CORS_ORIGINS=http://localhost:5200,http://127.0.0.1:5200
```

Alternatively, provide a complete `DATABASE_URL`. Cloudinary settings are
optional unless damage-image uploads are required.

## Install and initialize

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python scripts\migrate_supabase.py
python scripts\check_supabase.py
```

## Run

```powershell
uvicorn main:app --host 127.0.0.1 --port 8012 --reload
```

- Health: `http://127.0.0.1:8012/health`
- API documentation: `http://127.0.0.1:8012/docs`
- API prefix: `/api/v1`

## Useful scripts

```powershell
# Read-only Supabase schema/repository audit
python scripts\check_supabase.py

# Apply schema and compatibility repairs
python scripts\migrate_supabase.py

# Preview and then apply a legacy MongoDB merge
$env:LEGACY_MONGODB_URL="mongodb://127.0.0.1:27017"
python scripts\migrate_mongodb_data_to_supabase.py
python scripts\migrate_mongodb_data_to_supabase.py --apply

# Exercise authenticated Supabase API contracts
python scripts\smoke_supabase_api.py
```

Keep database passwords and admin credentials in `.env` or the deployment
provider's secret store. Do not add them to scripts or documentation.

## Verification

```powershell
.venv\Scripts\python.exe -m pytest -q
```

The suite covers authentication, permissions, warehouse isolation, receiving,
inventory, damage handling, fulfilment, approvals, audit logs, and Supabase
schema compatibility.
