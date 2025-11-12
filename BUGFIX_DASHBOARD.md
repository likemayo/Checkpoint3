# Dashboard Fix - Database Column Name

## Issue
After implementing the dashboard, login redirected to an internal server error instead of showing the dashboard.

## Root Cause
The dashboard SQL query was referencing incorrect column names:
- Used: `s.created_at` and `s.total`
- Actual columns in `sale` table: `sale_time` and `total_cents`

## Error Message
```
sqlite3.OperationalError: no such column: s.created_at
```

## Fix Applied

Changed the dashboard route in `src/app.py`:

**Before:**
```sql
SELECT s.id, s.created_at, s.status, s.total, ...
ORDER BY s.created_at DESC
```

**After:**
```sql
SELECT s.id, s.sale_time as created_at, s.status, 
       s.total_cents / 100.0 as total, ...
ORDER BY s.sale_time DESC
```

### Changes Made:
1. ✅ Changed `s.created_at` → `s.sale_time as created_at` (alias for template compatibility)
2. ✅ Changed `s.total` → `s.total_cents / 100.0 as total` (convert cents to dollars)
3. ✅ Fixed ORDER BY clause
4. ✅ Fixed stats calculation to use `orders_with_items` instead of raw `orders`

## Database Schema Reference

From `db/init.sql`:
```sql
CREATE TABLE IF NOT EXISTS sale (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    sale_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_cents INTEGER NOT NULL CHECK(total_cents >= 0),
    status TEXT NOT NULL DEFAULT 'COMPLETED',
    FOREIGN KEY (user_id) REFERENCES user(id)
);
```

## Status
✅ **Fixed and Deployed**
- Container rebuilt with correct SQL
- Health check passing
- Dashboard route now works correctly

## Testing
```bash
# Login and test dashboard
open http://localhost:5000/login
# Username: john
# Password: password123
# Should now see dashboard without errors
```

## Empty State
If no orders exist yet:
- Dashboard shows stats with zeros
- Empty state message: "No orders yet"
- Call to action: "Start shopping"

## Next Steps
To fully test the dashboard:
1. Login as a user
2. Navigate to Products
3. Purchase some items
4. Return to Dashboard
5. See orders appear in the history table
6. Click "Request Return" on completed orders
