-- Migration: Add RMA (Returns & Refunds) tables
-- Created: 2025-11-11
-- Description: Implements complete RMA workflow with tracking, inspection, and disposition

-- =============================
-- RMA Requests Table
-- =============================
CREATE TABLE IF NOT EXISTS rma_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rma_number TEXT NOT NULL UNIQUE,           -- e.g., "RMA-2025-001234"
    sale_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    
    -- Request details
    reason TEXT NOT NULL,                       -- Customer's reason for return
    description TEXT,                           -- Detailed description
    photo_urls TEXT,                            -- JSON array of photo URLs
    
    -- Status tracking (follows the 7-step pipeline)
    status TEXT NOT NULL DEFAULT 'SUBMITTED' CHECK(status IN (
        'SUBMITTED',        -- Step 1: Customer submitted
        'VALIDATING',       -- Step 2: Under validation
        'APPROVED',         -- Step 2: Validation passed, RMA approved
        'REJECTED',         -- Step 2: Validation failed
        'SHIPPING',         -- Step 3: Customer shipping back
        'RECEIVED',         -- Step 3: Warehouse received
        'INSPECTING',       -- Step 4: Under inspection
        'INSPECTED',        -- Step 4: Inspection complete
        'DISPOSITION',      -- Step 5: Awaiting disposition decision
        'PROCESSING',       -- Step 6: Refund/replacement processing
        'COMPLETED',        -- Step 7: Case closed
        'CANCELLED'         -- Customer cancelled
    )),
    
    -- Validation & Authorization (Step 2)
    validation_notes TEXT,
    validated_by TEXT,                          -- User/system who validated
    validated_at TIMESTAMP,
    
    -- Eligibility checks
    is_eligible INTEGER DEFAULT 1 CHECK(is_eligible IN (0,1)),
    warranty_valid INTEGER CHECK(warranty_valid IN (0,1)),
    purchase_date_valid INTEGER CHECK(purchase_date_valid IN (0,1)),
    
    -- Return Shipping (Step 3)
    shipping_carrier TEXT,
    tracking_number TEXT,
    shipped_at TIMESTAMP,
    received_at TIMESTAMP,
    
    -- Inspection (Step 4)
    inspection_result TEXT CHECK(inspection_result IN (NULL, 'DEFECTIVE', 'MISUSE', 'NORMAL_WEAR', 'AS_DESCRIBED')),
    inspection_notes TEXT,
    inspected_by TEXT,
    inspected_at TIMESTAMP,
    
    -- Disposition (Step 5)
    disposition TEXT CHECK(disposition IN (NULL, 'REFUND', 'REPLACEMENT', 'REPAIR', 'REJECT', 'STORE_CREDIT')),
    disposition_reason TEXT,
    disposition_by TEXT,
    disposition_at TIMESTAMP,
    
    -- Financial
    refund_amount_cents INTEGER,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP,
    
    FOREIGN KEY (sale_id) REFERENCES sale(id) ON DELETE RESTRICT,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS idx_rma_rma_number ON rma_requests(rma_number);
CREATE INDEX IF NOT EXISTS idx_rma_sale_id ON rma_requests(sale_id);
CREATE INDEX IF NOT EXISTS idx_rma_user_id ON rma_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_rma_status ON rma_requests(status);
CREATE INDEX IF NOT EXISTS idx_rma_created_at ON rma_requests(created_at);

-- =============================
-- RMA Items Table (which items are being returned)
-- =============================
CREATE TABLE IF NOT EXISTS rma_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rma_id INTEGER NOT NULL,
    sale_item_id INTEGER NOT NULL,             -- Link to original sale_item
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK(quantity > 0),
    reason TEXT,                                -- Item-specific reason
    
    FOREIGN KEY (rma_id) REFERENCES rma_requests(id) ON DELETE CASCADE,
    FOREIGN KEY (sale_item_id) REFERENCES sale_item(id) ON DELETE RESTRICT,
    FOREIGN KEY (product_id) REFERENCES product(id) ON DELETE RESTRICT,
    UNIQUE (rma_id, sale_item_id)
);

CREATE INDEX IF NOT EXISTS idx_rma_items_rma_id ON rma_items(rma_id);
CREATE INDEX IF NOT EXISTS idx_rma_items_product_id ON rma_items(product_id);

-- =============================
-- Refunds Table (Step 6: Financial processing)
-- =============================
CREATE TABLE IF NOT EXISTS refunds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rma_id INTEGER NOT NULL,
    sale_id INTEGER NOT NULL,
    
    -- Refund details
    amount_cents INTEGER NOT NULL CHECK(amount_cents >= 0),
    method TEXT NOT NULL,                       -- ORIGINAL_PAYMENT, STORE_CREDIT, CHECK
    status TEXT NOT NULL DEFAULT 'PENDING' CHECK(status IN ('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', 'CANCELLED')),
    
    -- Payment gateway response
    reference TEXT,                             -- Transaction/reference ID
    error_message TEXT,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP,
    completed_at TIMESTAMP,
    
    FOREIGN KEY (rma_id) REFERENCES rma_requests(id) ON DELETE RESTRICT,
    FOREIGN KEY (sale_id) REFERENCES sale(id) ON DELETE RESTRICT,
    UNIQUE (rma_id)
);

CREATE INDEX IF NOT EXISTS idx_refunds_rma_id ON refunds(rma_id);
CREATE INDEX IF NOT EXISTS idx_refunds_status ON refunds(status);

-- =============================
-- RMA Activity Log (Audit trail for all actions)
-- =============================
CREATE TABLE IF NOT EXISTS rma_activity_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rma_id INTEGER NOT NULL,
    
    -- Activity details
    action TEXT NOT NULL,                       -- e.g., 'STATUS_CHANGE', 'INSPECTION', 'REFUND_ISSUED'
    old_status TEXT,
    new_status TEXT,
    actor TEXT,                                 -- Who performed the action (user/system)
    notes TEXT,
    metadata TEXT,                              -- JSON for additional data
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (rma_id) REFERENCES rma_requests(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_rma_activity_rma_id ON rma_activity_log(rma_id);
CREATE INDEX IF NOT EXISTS idx_rma_activity_created_at ON rma_activity_log(created_at);

-- =============================
-- RMA Metrics (Step 7: Reporting)
-- =============================
CREATE TABLE IF NOT EXISTS rma_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Time period
    metric_date DATE NOT NULL,
    
    -- Volume metrics
    total_requests INTEGER DEFAULT 0,
    approved_requests INTEGER DEFAULT 0,
    rejected_requests INTEGER DEFAULT 0,
    completed_requests INTEGER DEFAULT 0,
    
    -- Performance metrics
    avg_validation_time_hours REAL,            -- Time from submitted to approved/rejected
    avg_inspection_time_hours REAL,            -- Time from received to inspected
    avg_total_cycle_time_hours REAL,           -- Time from submitted to completed
    
    -- Financial metrics
    total_refund_amount_cents INTEGER DEFAULT 0,
    
    -- Quality metrics
    defective_count INTEGER DEFAULT 0,
    misuse_count INTEGER DEFAULT 0,
    
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE (metric_date)
);

CREATE INDEX IF NOT EXISTS idx_rma_metrics_date ON rma_metrics(metric_date);

-- =============================
-- Trigger: Update rma_requests.updated_at on any change
-- =============================
CREATE TRIGGER IF NOT EXISTS update_rma_timestamp 
AFTER UPDATE ON rma_requests
FOR EACH ROW
BEGIN
    UPDATE rma_requests SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

-- =============================
-- Initial data / seed (optional)
-- =============================
-- None required; tables are ready for use
