# RMA (Returns & Refunds) Testing Guide

This guide will walk you through testing the complete RMA workflow from purchasing a product to requesting a return and tracking its status.

## Prerequisites

1. Containers must be running:
   ```bash
   docker-compose up -d
   ```

2. Database should be seeded with test data (automatically done on startup)

3. Application accessible at: http://localhost:5000

## Test Users

The system comes with 3 pre-seeded users:

| Username | Password | Role |
|----------|----------|------|
| john | password123 | Customer |
| jane | password123 | Customer |
| alice | password123 | Customer |

## Complete RMA Test Workflow

### Step 1: Login and Purchase a Product

1. Open http://localhost:5000 in your browser
2. Click **Login** (or navigate to http://localhost:5000/login)
3. Login credentials:
   - Username: `john`
   - Password: `password123`
4. Click **Products** to view available products
5. Select a product (e.g., "Laptop - $999.99")
6. Click **Buy** to purchase
7. You should see a receipt page showing:
   - Order details
   - Payment information
   - Order status: **COMPLETED**
   - **"Request Return"** button (only visible for completed orders)

### Step 2: Request a Return

1. From the receipt page, click the **"Request Return"** button
   - Or navigate to: `http://localhost:5000/rma/request?sale_id=YOUR_SALE_ID`

2. On the RMA Request Form:
   - **Order Information**: Review order details
   - **Select Items**: Check the items you want to return
   - **Reason**: Choose from dropdown (e.g., "Product defective")
   - **Description**: Provide details (e.g., "Screen is cracked")
   - **Photo URL** (optional): Add evidence URL
   - Click **"Submit Return Request"**

3. You should be redirected to the RMA detail page showing:
   - RMA Number (e.g., RMA-2024-001)
   - Status: **SUBMITTED**
   - Return information
   - Items being returned
   - Activity timeline

### Step 3: View Your Returns

1. Navigate to: http://localhost:5000/rma/my-returns
2. You should see a table listing all your return requests with:
   - RMA Number
   - Order ID
   - Reason
   - Status badge
   - Submit date
   - **View Details** link

### Step 4: Track Return Status

1. Click **"View Details"** on any return request
2. The detail page shows:
   - Current status with color-coded badge
   - Return information (reason, description, photos)
   - Items being returned with prices
   - Activity timeline (all actions taken)
   - Next steps (if any action is required)

### Step 5: Provide Shipping Information (After Approval)

**Note**: For testing, you'll need admin access to approve the RMA first.

Once approved (status changes to **APPROVED**):

1. View the RMA detail page
2. You'll see a form with fields:
   - **Carrier**: Enter shipping carrier (e.g., "UPS", "FedEx")
   - **Tracking Number**: Enter tracking code (e.g., "1Z999AA10123456784")
3. Click **"Submit Tracking Info"**
4. Status changes to **SHIPPING**

### Step 6: Monitor Progress

The RMA will progress through these statuses:

1. **SUBMITTED** - Customer submitted return request
2. **APPROVED** - Admin validated and approved
3. **SHIPPING** - Customer provided tracking info
4. **RECEIVED** - Warehouse received the package
5. **INSPECTING** - Quality team inspecting items
6. **COMPLETED** - Return processed and refund issued

At each stage, you can view:
- Current status
- Activity log showing who did what and when
- Any notes from administrators
- Refund information (when processed)

### Step 7: Cancel a Return (Optional)

If you need to cancel a return (only works for SUBMITTED or APPROVED status):

1. Go to **My Returns** page
2. Click **"Cancel"** next to the return you want to cancel
3. Confirm cancellation
4. Status changes to **CANCELLED**

## Testing Admin Workflow (via API)

For complete testing, you can simulate admin actions using curl or Postman:

### 2. Validate RMA (Step 2)
```bash
curl -X POST http://localhost:5000/rma/admin/validate/1 \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'
```

### 3. Mark as Received (Step 4)
```bash
curl -X POST http://localhost:5000/rma/admin/1/received \
  -H "Content-Type: application/json"
```

### 4. Start Inspection (Step 5)
```bash
curl -X POST http://localhost:5000/rma/admin/1/inspect/start \
  -H "Content-Type: application/json" \
  -d '{"inspector_notes": "Beginning quality inspection"}'
```

### 5. Complete Inspection (Step 5)
```bash
curl -X POST http://localhost:5000/rma/admin/1/inspect/complete \
  -H "Content-Type: application/json" \
  -d '{"passed": true, "notes": "All items in good condition"}'
```

### 6. Make Disposition (Step 6)
```bash
curl -X POST http://localhost:5000/rma/admin/1/disposition \
  -H "Content-Type: application/json" \
  -d '{
    "disposition": "RESTOCK",
    "notes": "Items will be restocked"
  }'
```

### 7. Process Refund (Step 7)
```bash
curl -X POST http://localhost:5000/rma/admin/1/refund \
  -H "Content-Type: application/json" \
  -d '{
    "amount": 999.99,
    "method": "original_payment",
    "transaction_id": "TXN-123456"
  }'
```

## Expected Results

### Customer Experience

✅ Can view receipt after purchase
✅ "Request Return" button appears only for completed orders
✅ Can select multiple items to return
✅ Receives RMA number immediately after submission
✅ Can view all returns in one place
✅ Can track real-time status updates
✅ Can provide shipping info when approved
✅ Can see refund details when processed
✅ Cannot access other users' returns

### System Behavior

✅ RMA numbers are unique (RMA-YYYY-NNN format)
✅ Status transitions are enforced (can't skip steps)
✅ Activity log tracks all actions
✅ Refund amount calculated from returned items
✅ Database triggers maintain metrics
✅ Cancelled RMAs cannot be reactivated
✅ Authentication required for all pages

## Troubleshooting

### "Please login to access this page"
- Make sure you're logged in
- Session may have expired - login again

### "Only completed orders can be returned"
- Order status must be "COMPLETED"
- Check the receipt page for status

### "Order not found"
- Verify the sale_id is correct
- Ensure you own this order

### "Please select at least one item to return"
- Check at least one item checkbox on the form
- JavaScript must be enabled

### Can't see "Request Return" button
- Button only shows for orders with status="COMPLETED"
- Check order status on receipt page

## Database Verification

To verify data directly in the database:

```bash
# Access database in container
docker exec -it checkpoint3-web sqlite3 /app/app.sqlite

# Query RMA requests
SELECT rma_number, status, reason FROM rma_requests;

# Query RMA items
SELECT * FROM rma_items WHERE rma_request_id = 1;

# Query activity log
SELECT action, actor_type, created_at FROM rma_activity_log WHERE rma_request_id = 1;

# Query refunds
SELECT amount, status, method FROM refunds WHERE rma_request_id = 1;
```

## URLs Quick Reference

| Page | URL |
|------|-----|
| Login | http://localhost:5000/login |
| Products | http://localhost:5000/products |
| Request Return | http://localhost:5000/rma/request?sale_id=X |
| My Returns | http://localhost:5000/rma/my-returns |
| View Return | http://localhost:5000/rma/view/RMA-2024-001 |
| Health Check | http://localhost:5000/health |

## Additional Resources

- **RMA API Documentation**: See `RMA_API.md`
- **Database Schema**: See `migrations/0002_add_rma_tables.sql`
- **Admin Pages**: See `ADMIN_PAGES.md`
- **Docker Setup**: See `DOCKER.md`
