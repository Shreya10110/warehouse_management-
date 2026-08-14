# WMS Backend

FastAPI backend for Whitfield Fulfillment. Requests follow this stable flow:

```text
routes -> controllers -> services -> cruds -> MongoDB
```

## Structure

```text
warehouse-backend/
|-- main.py                         # Stable Uvicorn entry point
|-- commons/                        # Cross-cutting logging and auth exports
|-- core/
|   |-- apis/
|   |   |-- api.py                  # Router registry exported to main.py
|   |   |-- routes/                 # FastAPI endpoints grouped by domain
|   |   `-- schemas/                # Request and response validation
|   |-- controllers/                # Request orchestration
|   |-- cruds/                      # Reusable persistence operations
|   |-- database/                   # MongoDB lifecycle, health, and indexes
|   |-- dependencies/               # Authentication and role permissions
|   |-- models/                     # MongoDB domain documents
|   |-- services/                   # Business workflows and transactions
|   |-- utils/                      # Small shared helpers
|   |-- config.py                   # Environment-backed settings
|   |-- exceptions.py               # Consistent API errors
|   `-- security.py                 # Password and JWT security
|-- scripts/                        # Administration and database checks
`-- tests/                          # Domain, security, and end-to-end coverage
```

The public API is unchanged. Frontend URLs, MongoDB collection names, roles,
permissions, and warehouse workflows remain the same.

## Database safety

- The logical database is `warehouse_management`.
- MongoDB data is outside the source-code folders, so reorganizing Python files
  cannot delete or relocate warehouse records.
- Docker Compose uses the named volume `mongodb_data`, which survives container
  recreation and application restarts.
- Startup creates uniqueness, query, and token-expiry indexes idempotently.
- `/health` performs a real MongoDB ping and returns the active database name.
- Secrets and connection strings stay in the ignored `.env` file.

Run the read-only database audit at any time:

```powershell
python scripts/check_database.py
```

For recoverable backups, use MongoDB Database Tools and keep the output outside
the repository:

```powershell
mongodump --uri="mongodb://localhost:27017" --db=warehouse_management --out="D:\warehouse_backups"
```

## Local setup

1. Start MongoDB locally on port `27017`, or run the repository Docker Compose
   configuration.
2. Copy `.env.example` to `.env`, set a strong `JWT_SECRET_KEY`, and optionally
   add Cloudinary credentials for damage-image uploads.
3. Install and run:

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements-dev.txt
   uvicorn main:app --reload
   ```

4. Create the first owner when initializing a new database:

   ```powershell
   python scripts/create_user.py --first-name Warehouse --last-name Owner --email owner@example.com --mobile 9999999999 --password StrongPass123 --role OWNER
   ```

Open `http://localhost:8000/docs` for the complete API. Use a MongoDB replica
set in production for transactional multi-line reservations; standalone local
MongoDB installations use the compensated reservation fallback.

## Verification

```powershell
pytest tests -q -p no:cacheprovider
```

The integration suite covers authentication, warehouse isolation, receiving,
inventory movements, order allocation, picking, packing, labels, shipping,
damage evidence, audits, approvals, and logout revocation.
