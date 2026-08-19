-- Whitfield Fulfillment - Supabase/PostgreSQL schema. Safe to run repeatedly.
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS users (
 id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, first_name TEXT NOT NULL, last_name TEXT NOT NULL,
 email TEXT UNIQUE NOT NULL, mobile TEXT NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL,
 warehouse_id TEXT, is_active BOOLEAN NOT NULL DEFAULT TRUE, approval_status TEXT NOT NULL DEFAULT 'APPROVED',
 approved_by TEXT, approved_at TIMESTAMPTZ, rejection_reason TEXT, last_login TIMESTAMPTZ,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS warehouses (
 id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, warehouse_code TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
 address_line_1 TEXT NOT NULL, address_line_2 TEXT, city TEXT NOT NULL, state TEXT NOT NULL, postal_code TEXT NOT NULL,
 country TEXT NOT NULL DEFAULT 'India', manager_id TEXT, contact_phone TEXT NOT NULL, contact_email TEXT NOT NULL,
 image_url TEXT, is_active BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS products (
 id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, sku TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
 description TEXT, category TEXT NOT NULL, brand TEXT, unit TEXT NOT NULL DEFAULT 'EA', barcode TEXT,
 is_active BOOLEAN NOT NULL DEFAULT TRUE, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS sellers (
 id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, seller_code TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
 contact_name TEXT, email TEXT, phone TEXT, address TEXT, is_active BOOLEAN NOT NULL DEFAULT TRUE,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS inbound_shipments (
 id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, shipment_id TEXT UNIQUE NOT NULL, warehouse_id TEXT NOT NULL,
 source_type TEXT NOT NULL, tracking_number TEXT, ticket_number TEXT, supplier_name TEXT NOT NULL,
 supplier_reference TEXT, status TEXT NOT NULL DEFAULT 'EXPECTED', seller_id TEXT,
 expected_items JSONB NOT NULL DEFAULT '[]'::jsonb, received_items JSONB NOT NULL DEFAULT '[]'::jsonb,
 created_by TEXT NOT NULL, received_by TEXT, received_at TEXT, completed_at TEXT,
 receiving_started_by TEXT, receiving_started_at TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS damage_reports (
 id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, damage_report_id TEXT UNIQUE NOT NULL, shipment_id TEXT NOT NULL,
 warehouse_id TEXT NOT NULL, sku TEXT NOT NULL, damage_quantity INTEGER NOT NULL, damage_type TEXT NOT NULL,
 damage_reason TEXT NOT NULL, notes TEXT, image_urls JSONB NOT NULL DEFAULT '[]'::jsonb, reported_by TEXT NOT NULL,
 reported_at TEXT NOT NULL, resolution_status TEXT NOT NULL DEFAULT 'OPEN', resolved_by TEXT, resolved_at TEXT,
 resolution TEXT, metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS inventory (
 id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, warehouse_id TEXT NOT NULL, product_id TEXT NOT NULL, sku TEXT NOT NULL,
 on_hand_quantity INTEGER NOT NULL DEFAULT 0, reserved_quantity INTEGER NOT NULL DEFAULT 0,
 damaged_quantity INTEGER NOT NULL DEFAULT 0, quarantine_quantity INTEGER NOT NULL DEFAULT 0,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 CONSTRAINT uq_inventory_warehouse_sku UNIQUE (warehouse_id, sku)
);
CREATE TABLE IF NOT EXISTS inventory_transactions (
 id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, warehouse_id TEXT NOT NULL, sku TEXT NOT NULL,
 transaction_type TEXT NOT NULL, quantity INTEGER NOT NULL, before_values JSONB NOT NULL DEFAULT '{}'::jsonb,
 after_values JSONB NOT NULL DEFAULT '{}'::jsonb, reference_type TEXT NOT NULL, reference_id TEXT NOT NULL,
 performed_by TEXT NOT NULL, created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS orders (
 id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, order_id TEXT UNIQUE NOT NULL, customer_name TEXT NOT NULL,
 customer_phone TEXT NOT NULL, customer_email TEXT, shipping_address JSONB NOT NULL, items JSONB NOT NULL,
 status TEXT NOT NULL DEFAULT 'PENDING', eligible_warehouse_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
 assigned_warehouse_id TEXT, rejection_reason TEXT, created_by TEXT NOT NULL, seller_id TEXT, picked_by TEXT,
 picked_at TEXT, picked_items JSONB NOT NULL DEFAULT '[]'::jsonb, package_id TEXT,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS packages (
 id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, package_id TEXT UNIQUE NOT NULL, order_id TEXT NOT NULL,
 warehouse_id TEXT NOT NULL, weight DOUBLE PRECISION NOT NULL, length DOUBLE PRECISION NOT NULL,
 width DOUBLE PRECISION NOT NULL, height DOUBLE PRECISION NOT NULL, packed_by TEXT NOT NULL, packed_at TEXT NOT NULL,
 carrier TEXT NOT NULL, tracking_number TEXT UNIQUE NOT NULL, label_url TEXT, status TEXT NOT NULL DEFAULT 'PACKED',
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS issue_requests (
 id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, issue_id TEXT UNIQUE NOT NULL, warehouse_id TEXT NOT NULL,
 raised_by TEXT NOT NULL, category TEXT NOT NULL, subject TEXT NOT NULL, description TEXT NOT NULL,
 priority TEXT NOT NULL DEFAULT 'MEDIUM', status TEXT NOT NULL DEFAULT 'OPEN', admin_response TEXT,
 resolved_by TEXT, resolved_at TEXT, metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS audit_logs (
 id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, user_id TEXT NOT NULL, user_role TEXT NOT NULL,
 warehouse_id TEXT, action TEXT NOT NULL, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL,
 old_value JSONB, new_value JSONB, metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
 timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(), created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE TABLE IF NOT EXISTS revoked_tokens (
 id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text, jti TEXT UNIQUE NOT NULL, expires_at TIMESTAMPTZ NOT NULL,
 created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Repair columns from the earlier draft without dropping existing data.
ALTER TABLE products ADD COLUMN IF NOT EXISTS brand TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS unit TEXT NOT NULL DEFAULT 'EA';
ALTER TABLE products ADD COLUMN IF NOT EXISTS barcode TEXT;
ALTER TABLE products ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE sellers ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE sellers ADD COLUMN IF NOT EXISTS phone TEXT;
ALTER TABLE sellers ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE sellers ALTER COLUMN contact_name DROP NOT NULL;
DO $$
BEGIN
 IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='sellers' AND column_name='contact_email') THEN
  EXECUTE 'UPDATE sellers SET email = COALESCE(email, contact_email)';
  EXECUTE 'ALTER TABLE sellers ALTER COLUMN contact_email DROP NOT NULL';
 END IF;
 IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='sellers' AND column_name='contact_phone') THEN
  EXECUTE 'UPDATE sellers SET phone = COALESCE(phone, contact_phone)';
  EXECUTE 'ALTER TABLE sellers ALTER COLUMN contact_phone DROP NOT NULL';
 END IF;
END $$;
ALTER TABLE inbound_shipments ADD COLUMN IF NOT EXISTS receiving_started_by TEXT;
ALTER TABLE inbound_shipments ADD COLUMN IF NOT EXISTS receiving_started_at TEXT;
ALTER TABLE damage_reports ADD COLUMN IF NOT EXISTS damage_report_id TEXT;
ALTER TABLE damage_reports ADD COLUMN IF NOT EXISTS damage_quantity INTEGER;
ALTER TABLE damage_reports ADD COLUMN IF NOT EXISTS damage_type TEXT;
ALTER TABLE damage_reports ADD COLUMN IF NOT EXISTS damage_reason TEXT;
ALTER TABLE damage_reports ADD COLUMN IF NOT EXISTS image_urls JSONB NOT NULL DEFAULT '[]'::jsonb;
ALTER TABLE damage_reports ADD COLUMN IF NOT EXISTS reported_at TEXT;
ALTER TABLE damage_reports ADD COLUMN IF NOT EXISTS resolution_status TEXT NOT NULL DEFAULT 'OPEN';
ALTER TABLE damage_reports ADD COLUMN IF NOT EXISTS resolution TEXT;
ALTER TABLE damage_reports ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;
DO $$
BEGIN
 IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='damage_reports' AND column_name='quantity') THEN
  EXECUTE 'UPDATE damage_reports SET damage_quantity = COALESCE(damage_quantity, quantity)';
  EXECUTE 'ALTER TABLE damage_reports ALTER COLUMN quantity SET DEFAULT 0';
 END IF;
END $$;
ALTER TABLE inventory_transactions ADD COLUMN IF NOT EXISTS before_values JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE inventory_transactions ADD COLUMN IF NOT EXISTS after_values JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE packages ADD COLUMN IF NOT EXISTS weight DOUBLE PRECISION;
ALTER TABLE packages ADD COLUMN IF NOT EXISTS length DOUBLE PRECISION;
ALTER TABLE packages ADD COLUMN IF NOT EXISTS width DOUBLE PRECISION;
ALTER TABLE packages ADD COLUMN IF NOT EXISTS height DOUBLE PRECISION;
ALTER TABLE packages ADD COLUMN IF NOT EXISTS label_url TEXT;
ALTER TABLE packages ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'PACKED';
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS user_id TEXT;
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS user_role TEXT;
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS entity_type TEXT;
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS entity_id TEXT;
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS old_value JSONB;
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS new_value JSONB;
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS metadata JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW();
DO $$
BEGIN
 IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='audit_logs' AND column_name='performed_by') THEN
  EXECUTE 'UPDATE audit_logs SET user_id = COALESCE(user_id, performed_by)';
  EXECUTE 'ALTER TABLE audit_logs ALTER COLUMN performed_by DROP NOT NULL';
 END IF;
END $$;
-- Earlier drafts accidentally placed inbound-only required columns on products.
DO $$
DECLARE target_column TEXT;
BEGIN
 FOREACH target_column IN ARRAY ARRAY['supplier_name','created_by'] LOOP
  IF EXISTS (SELECT 1 FROM information_schema.columns c WHERE c.table_name='products' AND c.column_name=target_column) THEN
   EXECUTE format('ALTER TABLE products ALTER COLUMN %I DROP NOT NULL', target_column);
  END IF;
 END LOOP;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_products_barcode ON products(barcode) WHERE barcode IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_inbound_tracking ON inbound_shipments(tracking_number) WHERE tracking_number IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS uq_inbound_ticket ON inbound_shipments(ticket_number) WHERE ticket_number IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_warehouse_id ON users(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_inventory_warehouse_sku ON inventory(warehouse_id, sku);
CREATE INDEX IF NOT EXISTS idx_inbound_warehouse_id ON inbound_shipments(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_orders_assigned_warehouse ON orders(assigned_warehouse_id);
CREATE INDEX IF NOT EXISTS idx_issue_requests_warehouse ON issue_requests(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_warehouse ON audit_logs(warehouse_id);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp DESC);

-- The FastAPI backend owns authorization; anonymous PostgREST access stays disabled.
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE warehouses ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE sellers ENABLE ROW LEVEL SECURITY;
ALTER TABLE inbound_shipments ENABLE ROW LEVEL SECURITY;
ALTER TABLE damage_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory ENABLE ROW LEVEL SECURITY;
ALTER TABLE inventory_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE packages ENABLE ROW LEVEL SECURITY;
ALTER TABLE issue_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_logs ENABLE ROW LEVEL SECURITY;
ALTER TABLE revoked_tokens ENABLE ROW LEVEL SECURITY;
