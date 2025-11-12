# RMA Inventory Logic - Complete Reference

## Overview
This document describes how inventory (stock) is adjusted for each RMA disposition type.

## Product Table Column
- **Column name**: `stock` (NOT `quantity`)
- All inventory updates must use: `UPDATE product SET stock = stock ± X WHERE id = ?`

## Disposition Types & Inventory Logic

### 1. REFUND
**When**: Customer returns item and gets money back
**Inventory Action**: ✅ RESTORE (stock + returned_quantity)
**Logic**: Item is returned in good condition and can be resold
**Code**: `_adjust_inventory_for_disposition()` in complete_refund()
**Workflow**:
1. Customer returns item → received → inspected
2. Admin sets disposition to REFUND
3. Admin processes refund → money returned to customer
4. System automatically: `UPDATE product SET stock = stock + quantity`
5. Item back in inventory, available for sale

### 2. STORE_CREDIT
**When**: Customer returns item and gets store credit
**Inventory Action**: ✅ RESTORE (stock + returned_quantity)
**Logic**: Item is returned in good condition and can be resold
**Code**: `_adjust_inventory_for_disposition()` in process_store_credit()
**Workflow**:
1. Customer returns item → received → inspected
2. Admin sets disposition to STORE_CREDIT
3. Admin processes store credit → credit issued to customer
4. System automatically: `UPDATE product SET stock = stock + quantity`
5. Item back in inventory, available for sale

### 3. REPLACEMENT
**When**: Item is defective, customer gets replacement
**Inventory Action**: ❌ DO NOT RESTORE returned item
**Additional Action**: ✅ DECREASE (stock - replacement_quantity) for new item
**Logic**: 
- Returned item is defective/damaged, cannot be resold
- New item shipped to customer reduces inventory
**Code**: `process_replacement()` line 526
**Workflow**:
1. Customer returns defective item → received → inspected
2. Admin sets disposition to REPLACEMENT
3. System creates new sale for replacement items
4. System automatically: `UPDATE product SET stock = stock - quantity`
5. New item shipped, old item scrapped/returned to vendor
**BUG FIXED**: Was using `quantity` column, now correctly uses `stock`

### 4. REPAIR
**When**: Item is being repaired and returned to customer
**Inventory Action**: ❌ DO NOT RESTORE
**Logic**: 
- Item is being repaired, not available for sale during repair
- Item eventually returned to customer, not resold
**Code**: `complete_repair()` - no inventory adjustment
**Workflow**:
1. Customer returns item for repair → received → inspected
2. Admin sets disposition to REPAIR
3. Item repaired and shipped back to customer
4. No inventory change (item not resold)

### 5. REJECT
**When**: Return rejected, customer keeps item
**Inventory Action**: ❌ NO CHANGE
**Logic**: Customer keeps the item, so no inventory change needed
**Code**: `process_rejection()` - no inventory adjustment
**Workflow**:
1. Customer requests return → admin reviews
2. Admin sets disposition to REJECT (e.g., out of return window, not defective)
3. Customer keeps item
4. No inventory change (customer still has the item)

## Bug History

### Bug #1: Fixed 2025-11-12
**Location**: `_adjust_inventory_for_disposition()` line 365
**Issue**: Used `quantity` column instead of `stock`
**Impact**: REFUND and STORE_CREDIT dispositions did not restore inventory
**Fix**: Changed to `SET stock = stock + ?`

### Bug #2: Fixed 2025-11-12
**Location**: `process_replacement()` line 526
**Issue**: Used `quantity` column instead of `stock`
**Impact**: REPLACEMENT dispositions did not decrease inventory for new items
**Fix**: Changed to `SET stock = stock - ?`

### Manual Fixes Required
**RMA #3**: USB Cable refund manually completed, required manual stock adjustment from 49→50

## Testing Checklist

### REFUND Scenario
- [ ] Customer purchases item (stock decreases)
- [ ] Customer returns item, admin sets REFUND disposition
- [ ] Admin processes refund
- [ ] Verify: Stock increases by returned quantity
- [ ] Verify: Product visible on catalog with updated stock

### STORE_CREDIT Scenario
- [ ] Customer purchases item (stock decreases)
- [ ] Customer returns item, admin sets STORE_CREDIT disposition
- [ ] Admin processes store credit
- [ ] Verify: Stock increases by returned quantity
- [ ] Verify: Product visible on catalog with updated stock

### REPLACEMENT Scenario
- [ ] Customer purchases item (stock decreases)
- [ ] Customer returns defective item, admin sets REPLACEMENT disposition
- [ ] Admin processes replacement
- [ ] Verify: Stock does NOT increase from returned item
- [ ] Verify: Stock DECREASES again for new replacement item

### REPAIR Scenario
- [ ] Customer purchases item (stock decreases)
- [ ] Customer returns item for repair, admin sets REPAIR disposition
- [ ] Admin completes repair
- [ ] Verify: Stock does NOT change (item returned to customer)

### REJECT Scenario
- [ ] Customer requests return
- [ ] Admin rejects return, sets REJECT disposition
- [ ] Verify: Stock does NOT change (customer keeps item)

## Database Schema Reference

```sql
CREATE TABLE product (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    stock INTEGER DEFAULT 0,  -- ← THIS IS THE INVENTORY COLUMN
    price_cents INTEGER,
    active INTEGER DEFAULT 1,
    ...
);
```

## Key Functions

1. **_adjust_inventory_for_disposition(rma_id, disposition)** - Lines 348-386
   - Called by: complete_refund(), process_store_credit()
   - Handles: REFUND, STORE_CREDIT, REPLACEMENT, REPAIR, REJECT logic
   - Updates: stock column for REFUND/STORE_CREDIT only

2. **complete_refund(refund_id, ...)** - Lines 388-458
   - Calls: _adjust_inventory_for_disposition()
   - Updates: RMA status, sale status, user total_spent, inventory

3. **process_replacement(rma_id, ...)** - Lines 486-542
   - Creates: New sale for replacement
   - Updates: Decreases stock for replacement items
   - Does NOT call _adjust_inventory_for_disposition() (returned item not restored)

4. **process_store_credit(rma_id, amount, ...)** - Lines 554-603
   - Calls: _adjust_inventory_for_disposition()
   - Updates: RMA status, inventory

5. **complete_repair(rma_id, ...)** - Lines 617-651
   - No inventory adjustment (item returned to customer)

6. **process_rejection(rma_id, ...)** - Lines 653-687
   - Calls: _adjust_inventory_for_disposition() (returns "No inventory change")
   - No actual inventory update (customer keeps item)

## Summary

| Disposition | Customer Gets | Returned Item | Inventory Change | Code Location |
|------------|---------------|---------------|------------------|---------------|
| **REFUND** | Money back | Accepted | ✅ +quantity | _adjust_inventory (line 367) |
| **STORE_CREDIT** | Store credit | Accepted | ✅ +quantity | _adjust_inventory (line 367) |
| **REPLACEMENT** | New item | Defective | ✅ -quantity (new) | process_replacement (line 526) |
| **REPAIR** | Repaired item | Temporarily | ❌ No change | complete_repair (no update) |
| **REJECT** | Nothing | Keeps original | ❌ No change | process_rejection (no update) |

## All Bugs Fixed ✅
1. REFUND inventory restoration - FIXED (quantity → stock)
2. REPLACEMENT inventory decrease - FIXED (quantity → stock)
3. Refund form re-submission - FIXED (added existence check)
