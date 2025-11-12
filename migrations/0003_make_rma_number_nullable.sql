-- Migration 0003: Make rma_requests.rma_number nullable and keep it UNIQUE
-- SQLite does not support altering NOT NULL constraints directly, so we recreate the table.

PRAGMA foreign_keys = OFF;

BEGIN TRANSACTION;

-- Create new table without NOT NULL on rma_number
CREATE TABLE IF NOT EXISTS rma_requests_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rma_number TEXT UNIQUE,
    sale_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,

    reason TEXT NOT NULL,
    description TEXT,
    photo_urls TEXT,

    status TEXT NOT NULL DEFAULT 'SUBMITTED' CHECK(status IN (
        'SUBMITTED','VALIDATING','APPROVED','REJECTED','SHIPPING','RECEIVED','INSPECTING','INSPECTED','DISPOSITION','PROCESSING','COMPLETED','CANCELLED'
    )),

    validation_notes TEXT,
    validated_by TEXT,
    validated_at TIMESTAMP,

    is_eligible INTEGER DEFAULT 1 CHECK(is_eligible IN (0,1)),
    warranty_valid INTEGER CHECK(warranty_valid IN (0,1)),
    purchase_date_valid INTEGER CHECK(purchase_date_valid IN (0,1)),

    shipping_carrier TEXT,
    tracking_number TEXT,
    shipped_at TIMESTAMP,
    received_at TIMESTAMP,

    inspection_result TEXT CHECK(inspection_result IN (NULL, 'DEFECTIVE', 'MISUSE', 'NORMAL_WEAR', 'AS_DESCRIBED')),
    inspection_notes TEXT,
    inspected_by TEXT,
    inspected_at TIMESTAMP,

    disposition TEXT CHECK(disposition IN (NULL, 'REFUND', 'REPLACEMENT', 'REPAIR', 'REJECT', 'STORE_CREDIT')),
    disposition_reason TEXT,
    disposition_by TEXT,
    disposition_at TIMESTAMP,

    refund_amount_cents INTEGER,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,

    FOREIGN KEY (sale_id) REFERENCES sale(id) ON DELETE RESTRICT,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE RESTRICT
);

-- Copy data
INSERT INTO rma_requests_new (
    id, rma_number, sale_id, user_id,
    reason, description, photo_urls,
    status,
    validation_notes, validated_by, validated_at,
    is_eligible, warranty_valid, purchase_date_valid,
    shipping_carrier, tracking_number, shipped_at, received_at,
    inspection_result, inspection_notes, inspected_by, inspected_at,
    disposition, disposition_reason, disposition_by, disposition_at,
    refund_amount_cents,
    created_at, updated_at, closed_at
) 
SELECT 
    id, rma_number, sale_id, user_id,
    reason, description, photo_urls,
    status,
    validation_notes, validated_by, validated_at,
    is_eligible, warranty_valid, purchase_date_valid,
    shipping_carrier, tracking_number, shipped_at, received_at,
    inspection_result, inspection_notes, inspected_by, inspected_at,
    disposition, disposition_reason, disposition_by, disposition_at,
    refund_amount_cents,
    created_at, updated_at, closed_at
FROM rma_requests;

-- Replace old table
DROP TABLE rma_requests;
ALTER TABLE rma_requests_new RENAME TO rma_requests;

-- Recreate indexes (matching 0002)
CREATE INDEX IF NOT EXISTS idx_rma_status ON rma_requests(status);
CREATE INDEX IF NOT EXISTS idx_rma_created_at ON rma_requests(created_at);

COMMIT;

PRAGMA foreign_keys = ON;
