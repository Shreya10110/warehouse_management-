# WMS Backend

FastAPI backend for the warehouse management system. The API follows:

```text
routes → controllers → services → cruds → MongoDB
```

## Local setup

1. Start MongoDB locally on port `27017`. The development configuration supports a standard standalone MongoDB server:

   ```powershell
   mongod --dbpath <your-data-directory>
   ```

2. Copy `.env.example` to `.env` and set a strong `JWT_SECRET_KEY`. Add Cloudinary credentials to enable damage-image uploads.

3. Install and run:

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements-dev.txt
   uvicorn main:app --reload
   ```

4. Create the first owner:

   ```powershell
   python scripts/create_user.py --first-name Warehouse --last-name Owner --email owner@example.com --mobile 9999999999 --password StrongPass123 --role OWNER
   ```

Open `http://localhost:8000/docs` for the complete API.

Use a MongoDB replica set in production for transactional multi-line order reservations. A compensated reservation fallback is used by standalone local MongoDB installations.

## Verification

```powershell
pytest tests -q -p no:cacheprovider
```

The integration suite covers authentication, warehouse isolation, inbound receiving, inventory movements, order allocation, reservation, picking, packing, QR label generation, shipping, audit history, and logout revocation.
