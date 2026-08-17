# Whitfield Fulfillment — Warehouse Management System

Whitfield Fulfillment is a full-stack Warehouse Management System (WMS) for
controlling warehouse users, inbound receiving, inventory, damage evidence,
outbound fulfilment, and audit history in one connected application.

The project uses a React + Vite frontend, a FastAPI backend, and MongoDB for
persistent warehouse data.

## What problem does it solve?

Warehouse work often becomes difficult when stock is received manually,
different teams use disconnected spreadsheets, damaged products have no proof,
and there is no clear record of who changed inventory.

This system solves those operational problems by:

- keeping each employee restricted to their assigned warehouse;
- letting Admin plan expected inbound shipments before goods arrive;
- calculating good and damaged stock automatically during receiving;
- tracking reserved, available, damaged, and quarantined inventory separately;
- recording photos of damaged inbound goods for manager review;
- guiding outbound staff through pick, pack, label, and ship steps;
- preventing duplicate carrier tracking numbers;
- recording important activity in immutable audit logs.

## Users and permissions

### Warehouse Owner / Admin

- Approves manager registrations.
- Creates warehouses, sellers, products/SKUs, and expected inbound shipments.
- Creates and assigns outbound customer orders to eligible warehouses.
- Views company-wide inventory, reports, employees, issues, and audit logs.
- Resolves damage reports when needed.

### Warehouse Manager

- Works only inside their assigned warehouse.
- Approves employee registration requests for that warehouse.
- Monitors inbound, outbound, inventory, damage reports, and the warehouse team.
- Reviews damage photos and chooses a disposition: return, dispose, move to good
  stock, or keep quarantined.
- Sends operational issues to Admin.

### Inbound Employee

- Works only inside their assigned warehouse.
- Finds Admin-created expected shipments using a tracking number or drop-off
  ticket.
- Records received and damaged quantities.
- The system calculates good quantity and updates inventory automatically.
- Uploads damage-photo evidence for manager review.

### Outbound Employee

- Works only inside their assigned warehouse.
- Starts picking, confirms picked items, completes picking, packs the order, and
  enters carrier details/tracking at packing time.
- Prints shipping labels before or after shipping.
- Marks packed packages as shipped; inventory is then consumed automatically.

## Main workflows

### Inbound workflow

```text
Admin creates seller + SKU + expected inbound shipment
    -> Inbound employee finds shipment
    -> Employee records received and damaged quantities
    -> Good quantity is calculated automatically
    -> Inventory, damage report, transaction, employee, timestamp, and audit log update
```

### Damage evidence workflow

```text
Inbound employee records damaged quantity
    -> Damage report is created as OPEN
    -> Employee uploads photos
    -> Manager/Admin opens evidence and decides the disposition
    -> Inventory and audit history update
```

### Outbound workflow

```text
Admin creates customer order
    -> System finds warehouses with enough available stock
    -> Admin assigns one warehouse and stock is reserved
    -> Outbound employee picks and confirms items
    -> Employee packs, enters carrier/tracking number, and prints label
    -> Employee marks shipment as shipped
    -> Reserved and on-hand inventory are reduced safely
```

## Features

- JWT authentication, logout revocation, and password hashing.
- Registration approval flow: Admin approves Managers; Managers approve Employees.
- Warehouse-scoped access control for Managers, Inbound, and Outbound roles.
- Warehouse, seller/supplier, product, and SKU master data.
- Barcode/UPC support for inbound product identification.
- Expected inbound carrier and seller drop-off workflows.
- Automatic inventory calculations: on hand, reserved, available, damaged, and
  quarantine balances.
- Damage reports with photo evidence and manager decisions.
- Safe outbound order allocation and inventory reservation.
- Pick, pack, carrier tracking, printable QR shipping labels, and shipment status.
- Labels remain printable after an order is shipped.
- Manager issue reporting to Admin.
- Audit logs and inventory transactions for accountability.
- Search, role-specific dashboards, database health checks, and MongoDB indexes.

## Project structure

```text
warehouse_system/
|-- warehouse-frontend/          # React + Vite user interface
|   `-- src/
|       |-- pages/               # Login, dashboards, inventory, inbound, outbound, etc.
|       |-- components/          # Reusable UI components
|       |-- api/                 # Backend API client
|       `-- context/             # Authentication state
|-- warehouse-backend/           # FastAPI application
|   |-- commons/                 # Shared logging and authentication exports
|   |-- core/
|   |   |-- apis/routes/         # API endpoints
|   |   |-- apis/schemas/        # Request and response validation
|   |   |-- controllers/         # Request orchestration
|   |   |-- cruds/               # Persistence layer
|   |   |-- database/            # MongoDB lifecycle, health, and indexes
|   |   |-- dependencies/        # Authentication and permissions
|   |   |-- models/              # MongoDB documents
|   |   |-- services/            # Business workflows
|   |   `-- utils/               # Shared helpers
|   |-- scripts/                 # Database/user administration utilities
|   `-- tests/                   # Backend tests
|-- render.yaml                  # Render backend + frontend deployment blueprint
`-- docker-compose.yml           # MongoDB replica-set setup with persistent storage
```

## Technology

- Frontend: React, Vite, Tailwind CSS, Lucide icons.
- Backend: FastAPI, Pydantic, Motor.
- Database: MongoDB.
- Optional image storage: Cloudinary for damage-photo evidence.
- Local infrastructure: Docker Compose for MongoDB replica-set support.

## Run locally

### 1. Start MongoDB

From the project root:

```powershell
docker compose up -d
```

This starts MongoDB on `127.0.0.1:27017` and keeps its data in the persistent
`mongodb_data` Docker volume. Do not run `docker compose down -v` unless you
intentionally want to delete the Docker database volume.

### 2. Start the backend

```powershell
cd warehouse-backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
uvicorn main:app --host 127.0.0.1 --port 8011 --reload
```

Backend API documentation: `http://127.0.0.1:8011/docs`

Set these values in `warehouse-backend/.env`:

```text
MONGODB_URL=mongodb://127.0.0.1:27017
MONGODB_DATABASE=warehouse_management
JWT_SECRET_KEY=use-a-long-private-value
CORS_ORIGINS=http://localhost:5199,http://127.0.0.1:5199
```

For damage-image uploads, also add valid Cloudinary credentials to `.env`.

### 3. Start the frontend

```powershell
cd warehouse-frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5199
```

Open: `http://127.0.0.1:5199`

## Deploy on Render

The repository includes `render.yaml`, which defines both services:

- `warehouse-backend`: FastAPI web service using Python 3.12;
- `warehouse-frontend`: React/Vite static site with React Router rewrites.

In Render, choose **New > Blueprint**, connect this repository, and use the
root `render.yaml`. During the initial Blueprint setup, provide these secret
values when prompted:

```text
MONGODB_URL=mongodb+srv://...your Atlas URI...
CLOUDINARY_CLOUD_NAME=...
CLOUDINARY_API_KEY=...
CLOUDINARY_API_SECRET=...
VITE_API_URL=https://YOUR-BACKEND.onrender.com/api/v1
```

Never commit those values. Render generates `JWT_SECRET_KEY` automatically.
After the backend is live, confirm `/health` reports a connected database,
then clear the frontend build cache and redeploy so Vite embeds its API URL.

## Database safety and inspection

The application database is named `warehouse_management`. Your warehouse data
is stored in MongoDB, not inside the source folders; reorganizing code does not
delete warehouse records.

To inspect it in MongoDB Compass, create a connection using:

```text
mongodb://127.0.0.1:27017/warehouse_management
```

Run the read-only database audit:

```powershell
cd warehouse-backend
.venv\Scripts\python.exe scripts\check_database.py
```

Create a backup outside the repository:

```powershell
mongodump --uri="mongodb://127.0.0.1:27017" --db=warehouse_management --out="D:\warehouse_backups"
```

## Tests

```powershell
cd warehouse-backend
.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider
```

The backend test suite covers roles, authentication, warehouse isolation,
inventory, inbound receiving, damage reports, outbound allocation, picking,
packing, shipping, approvals, and audit behaviour.
