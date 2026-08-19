# Whitfield Fulfillment — Warehouse Management System

A role-based warehouse management application for inbound receiving, inventory,
damage handling, outbound fulfilment, employee approvals, and audit history.

The active stack is React + Vite, FastAPI, and Supabase PostgreSQL. MongoDB is
supported only by the optional one-time migration utility, not by the runtime.

## Technology stack

| Layer | Technology | Purpose |
| --- | --- | --- |
| Frontend | React, Vite, React Router | Role-based web application |
| Styling | Tailwind CSS, Lucide React | Layout, components, and icons |
| Backend | Python, FastAPI, Uvicorn | REST APIs and business workflows |
| Validation | Pydantic | API and domain validation |
| Database | Supabase PostgreSQL | Primary operational database |
| Database driver | AsyncPG | Asynchronous SQL access and transactions |
| Authentication | JWT, python-jose, bcrypt | Login, claims, revocation, password hashing |
| Media | Cloudinary (optional) | Damage evidence uploads |
| Testing | Pytest | API, security, and workflow verification |

## Application flow

```text
React frontend
    -> REST request (/api/v1/...)
    -> FastAPI route
    -> authentication and role/warehouse checks
    -> controller/service workflow
    -> shared CRUD repository
    -> AsyncPG transaction
    -> Supabase PostgreSQL
    -> JSON response
```

Inbound completion is atomic on PostgreSQL: inventory, transaction history,
damage reports, shipment status, and audit logs either all succeed or all roll
back. A failed request cannot leave a partial receipt.

## Roles

### Owner / Admin

- Manages warehouses, sellers, products/SKUs, and employees.
- Approves managers and creates expected inbound shipments.
- Creates and assigns outbound orders.
- Views company-wide inventory, damage reports, issues, and audit logs.

### Manager

- Operates only inside the assigned warehouse.
- Approves inbound and outbound employees.
- Reviews stock, receiving, fulfilment, damage evidence, and team activity.
- Resolves damage reports and raises issues to the Owner.

### Inbound employee

- Finds expected shipments by tracking or ticket number.
- Records received and damaged quantities.
- Completes receiving and uploads damage evidence.

### Outbound employee

- Picks and confirms assigned orders.
- Packs orders, enters carrier details, and prints QR shipping labels.
- Ships packages and consumes reserved inventory.

## Main features

- JWT authentication and role-based access control.
- Owner/manager approval workflow for new accounts.
- Warehouse isolation for staff accounts.
- Warehouse, seller, product, SKU, barcode, and UPC master data.
- Expected and direct inbound receiving.
- On-hand, reserved, available, damaged, and quarantine balances.
- Damage reports with image evidence and resolution decisions.
- Outbound allocation, reservation, pick, pack, label, and ship workflows.
- Immutable audit logs and inventory transaction history.
- Supabase schema checks and MongoDB-to-Supabase migration utilities.

## Project structure

```text
warehouse_system/
|-- warehouse-frontend/          # React/Vite application
|   `-- src/
|       |-- api/                 # API client modules
|       |-- components/          # Reusable UI components
|       |-- context/             # Authentication state
|       |-- layouts/             # Role-aware application layout
|       `-- pages/               # Admin, manager, inbound, and outbound screens
|-- warehouse-backend/           # FastAPI application
|   |-- core/
|   |   |-- apis/routes/         # REST endpoints
|   |   |-- apis/schemas/        # API validation schemas
|   |   |-- controllers/         # Request orchestration
|   |   |-- cruds/               # Shared persistence layer
|   |   |-- database/            # Supabase connection and AsyncPG adapter
|   |   |-- models/              # Domain models
|   |   `-- services/            # Business workflows
|   |-- scripts/                 # Migration, verification, and admin utilities
|   |-- tests/                   # Backend tests
|   `-- supabase_schema.sql      # PostgreSQL tables, repairs, and indexes
|-- render.yaml                  # Render deployment blueprint
`-- docker-compose.yml           # Optional source for one-time legacy migration
```

## Local setup with Supabase

### 1. Configure the backend

```powershell
cd warehouse-backend
Copy-Item .env.example .env
```

Fill in the private values in `warehouse-backend/.env`. Never commit this file.

```text
SUPABASE_URL=https://YOUR_PROJECT.supabase.co
SUPABASE_DB_PASSWORD=YOUR_DATABASE_PASSWORD
SUPABASE_DB_REGION=YOUR_POOLER_REGION
JWT_SECRET_KEY=YOUR_LONG_RANDOM_SECRET
CORS_ORIGINS=http://localhost:5200,http://127.0.0.1:5200
```

You may provide a complete `DATABASE_URL` instead. Use the Supabase pooler URL
when the direct database host is unavailable over IPv4.

### 2. Install the backend and apply the schema

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python scripts\migrate_supabase.py
python scripts\check_supabase.py
```

### 3. Start the backend

```powershell
uvicorn main:app --host 127.0.0.1 --port 8012 --reload
```

- Health: `http://127.0.0.1:8012/health`
- Swagger API documentation: `http://127.0.0.1:8012/docs`
- API base URL: `http://127.0.0.1:8012/api/v1`

### 4. Start the frontend

Create `warehouse-frontend/.env`:

```text
VITE_API_URL=http://127.0.0.1:8012/api/v1
```

Then run:

```powershell
cd ..\warehouse-frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5200
```

Open `http://127.0.0.1:5200/login`.

## Admin bootstrap

For an empty database, optionally configure:

```text
BOOTSTRAP_OWNER_EMAIL=admin@example.com
BOOTSTRAP_OWNER_PASSWORD=YOUR_PRIVATE_STRONG_PASSWORD
BOOTSTRAP_OWNER_FIRST_NAME=Warehouse
BOOTSTRAP_OWNER_LAST_NAME=Owner
BOOTSTRAP_OWNER_MOBILE=0000000000
```

The backend creates an Owner only when none exists. The password is hashed,
never logged, and existing accounts are never overwritten. Remove
`BOOTSTRAP_OWNER_PASSWORD` after the first successful startup.

## Migrating legacy MongoDB data

Supply the legacy source separately, then run a preview followed by the explicit
migration. These variables are not part of the normal application `.env`:

```powershell
cd warehouse-backend
$env:LEGACY_MONGODB_URL="mongodb://127.0.0.1:27017"
$env:LEGACY_MONGODB_DATABASE="warehouse_management"
python scripts\migrate_mongodb_data_to_supabase.py
python scripts\migrate_mongodb_data_to_supabase.py --apply
python scripts\check_supabase.py
```

The migration merges records without deleting destination data and preserves an
existing Supabase password hash when users share the same email address.

## Tests and build

```powershell
cd warehouse-backend
.venv\Scripts\python.exe -m pytest -q

cd ..\warehouse-frontend
npm run build
```

## Deployment

The repository includes a Render blueprint for the FastAPI service and React
static site. Configure private Supabase, JWT, Cloudinary, bootstrap-owner, and
`VITE_API_URL` values in the hosting dashboard—never in Git.

After deployment, verify `/health`, then test authentication before processing
live warehouse transactions.
