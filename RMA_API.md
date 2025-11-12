# RMA (Returns & Refunds) API Documentation

## Overview

The RMA system implements a complete 7-step returns and refunds workflow:

1. **RMA Request Submission** - Customer submits return request
2. **Validation & Authorization** - Support validates and approves/rejects
3. **Return Shipping** - Customer ships item back, tracking logged
4. **Inspection & Diagnosis** - QA inspects returned item
5. **Disposition Decision** - Warranty team decides refund/replacement/etc
6. **Refund Processing** - System issues refund
7. **Closure & Reporting** - Case closed, metrics updated

## Base URL

```
http://localhost:5000/rma
```

## Authentication

- Customer endpoints: Require user login (session-based)
- Admin endpoints: Currently no authentication (TODO: add admin auth)

---

## API Endpoints

### 1. Submit RMA Request (Customer)

**Step 1: Customer submits return request**

```http
POST /rma/submit
Content-Type: application/json
Cookie: session=<user_session>

{
  "sale_id": 123,
  "reason": "Product defective",
  "description": "Screen is cracked",
  "items": [
    {
      "sale_item_id": 1,
      "product_id": 1,
      "quantity": 1,
      "reason": "Screen defect"
    }
  ],
  "photo_urls": ["http://example.com/photo1.jpg"]
}
```

**Response (201 Created):**
```json
{
  "success": true,
  "rma_id": 1,
  "rma_number": "RMA-20251111-0001",
  "status": "SUBMITTED",
  "message": "RMA request submitted successfully. Your RMA number is RMA-20251111-0001"
}
```

---

### 2. Get My RMA Requests (Customer)

```http
GET /rma/my-requests?status=SUBMITTED
Cookie: session=<user_session>
```

**Response (200 OK):**
```json
{
  "success": true,
  "count": 2,
  "rmas": [
    {
      "id": 1,
      "rma_number": "RMA-20251111-0001",
      "sale_id": 123,
      "status": "SUBMITTED",
      "reason": "Product defective",
      "created_at": "2025-11-11 10:00:00"
    }
  ]
}
```

---

### 3. Get RMA Details (Customer)

```http
GET /rma/RMA-20251111-0001
Cookie: session=<user_session>
```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "rma": {
      "id": 1,
      "rma_number": "RMA-20251111-0001",
      "sale_id": 123,
      "user_id": 1,
      "status": "SUBMITTED",
      "reason": "Product defective",
      "description": "Screen is cracked",
      "created_at": "2025-11-11 10:00:00"
    },
    "items": [
      {
        "id": 1,
        "product_id": 1,
        "product_name": "Laptop",
        "quantity": 1,
        "reason": "Screen defect"
      }
    ],
    "activities": [
      {
        "action": "SUBMITTED",
        "actor": "customer",
        "notes": "RMA request submitted by customer",
        "created_at": "2025-11-11 10:00:00"
      }
    ],
    "refund": null
  }
}
```

---

### 4. Validate RMA (Admin - Step 2)

**Step 2: Support/System validates the request**

```http
POST /rma/admin/validate/1
Content-Type: application/json

{
  "approve": true,
  "validation_notes": "Verified warranty is valid. Purchase within 30 days.",
  "validated_by": "support_agent_01"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "rma_id": 1,
  "approved": true,
  "message": "RMA has been approved"
}
```

---

### 5. Update Shipping Info (Customer - Step 3)

**Step 3: Customer ships return and provides tracking**

```http
POST /rma/1/shipping
Content-Type: application/json
Cookie: session=<user_session>

{
  "carrier": "UPS",
  "tracking_number": "1Z999AA10123456784"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Shipping information updated",
  "tracking": "UPS 1Z999AA10123456784"
}
```

---

### 6. Mark as Received (Admin - Step 3)

**Step 3: Warehouse receives the return**

```http
POST /rma/admin/1/received
Content-Type: application/json

{
  "actor": "warehouse_staff_01"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Item marked as received"
}
```

---

### 7. Start Inspection (Admin - Step 4)

**Step 4: QA starts inspecting the item**

```http
POST /rma/admin/1/inspect/start
Content-Type: application/json

{
  "inspected_by": "qa_tech_01"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Inspection started"
}
```

---

### 8. Complete Inspection (Admin - Step 4)

**Step 4: QA completes inspection with result**

```http
POST /rma/admin/1/inspect/complete
Content-Type: application/json

{
  "result": "DEFECTIVE",
  "notes": "Screen is cracked as described. Manufacturing defect confirmed.",
  "inspected_by": "qa_tech_01"
}
```

**Valid inspection results:**
- `DEFECTIVE` - Product has a defect
- `MISUSE` - Product damaged by misuse
- `NORMAL_WEAR` - Normal wear and tear
- `AS_DESCRIBED` - Product is as originally described

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Inspection completed",
  "result": "DEFECTIVE"
}
```

---

### 9. Make Disposition Decision (Admin - Step 5)

**Step 5: Warranty team decides the outcome**

```http
POST /rma/admin/1/disposition
Content-Type: application/json

{
  "disposition": "REFUND",
  "reason": "Defective product confirmed. Full refund approved.",
  "decided_by": "warranty_manager"
}
```

**Valid dispositions:**
- `REFUND` - Issue full refund
- `REPLACEMENT` - Send replacement product
- `REPAIR` - Repair and return
- `REJECT` - Deny the return
- `STORE_CREDIT` - Issue store credit

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Disposition decided",
  "disposition": "REFUND"
}
```

---

### 10. Process Refund (Admin - Step 6)

**Step 6: System issues the refund**

```http
POST /rma/admin/1/refund
Content-Type: application/json

{
  "amount_cents": 99999,
  "method": "ORIGINAL_PAYMENT"
}
```

**Valid refund methods:**
- `ORIGINAL_PAYMENT` - Refund to original payment method
- `STORE_CREDIT` - Issue store credit
- `CHECK` - Mail a check

**Response (200 OK):**
```json
{
  "success": true,
  "message": "Refund processed",
  "refund_id": 1,
  "amount": "$999.99"
}
```

---

### 11. Cancel RMA (Customer)

```http
POST /rma/1/cancel
Content-Type: application/json
Cookie: session=<user_session>

{
  "reason": "Changed my mind"
}
```

**Response (200 OK):**
```json
{
  "success": true,
  "message": "RMA cancelled"
}
```

---

### 12. Get Metrics (Admin - Step 7)

**Step 7: View RMA metrics and reporting data**

```http
GET /rma/admin/metrics?start_date=2025-11-01&end_date=2025-11-30
```

**Response (200 OK):**
```json
{
  "success": true,
  "metrics": [
    {
      "metric_date": "2025-11-11",
      "total_requests": 10,
      "approved_requests": 8,
      "rejected_requests": 2,
      "completed_requests": 5,
      "avg_validation_time_hours": 2.5,
      "avg_inspection_time_hours": 4.0,
      "avg_total_cycle_time_hours": 48.5,
      "total_refund_amount_cents": 500000,
      "defective_count": 6,
      "misuse_count": 2
    }
  ]
}
```

---

## Status Flow

The RMA progresses through these statuses:

```
SUBMITTED → VALIDATING → APPROVED → SHIPPING → RECEIVED → 
INSPECTING → INSPECTED → DISPOSITION → PROCESSING → COMPLETED

Alternative paths:
- SUBMITTED → VALIDATING → REJECTED (validation failed)
- Any status → CANCELLED (customer cancels)
```

---

## Error Responses

All errors follow this format:

```json
{
  "error": "ErrorType",
  "details": "Human-readable error message"
}
```

**Common error codes:**
- `400 Bad Request` - Invalid input (ValidationError, BadRequest)
- `401 Unauthorized` - Not logged in
- `403 Forbidden` - Access denied
- `404 Not Found` - RMA not found
- `500 Internal Server Error` - Server error

---

## Complete Workflow Example

### Customer Flow

1. **Customer completes a purchase** → Gets `sale_id`
2. **Customer submits RMA** → Gets `rma_number`
3. **Customer checks status** → `GET /rma/RMA-xxx`
4. **After approval, customer ships** → `POST /rma/1/shipping`
5. **Customer tracks progress** → `GET /rma/RMA-xxx`

### Admin Flow

1. **Validate RMA** → `POST /rma/admin/validate/1`
2. **Mark received** → `POST /rma/admin/1/received`
3. **Start inspection** → `POST /rma/admin/1/inspect/start`
4. **Complete inspection** → `POST /rma/admin/1/inspect/complete`
5. **Make disposition** → `POST /rma/admin/1/disposition`
6. **Process refund** → `POST /rma/admin/1/refund`
7. **View metrics** → `GET /rma/admin/metrics`

---

## cURL Examples

### Submit RMA (after login)

```bash
# First, login to get session
curl -c cookies.txt -X POST http://localhost:5000/login \
  -F "username=john" \
  -F "password=password123"

# Submit RMA
curl -b cookies.txt -X POST http://localhost:5000/rma/submit \
  -H "Content-Type: application/json" \
  -d '{
    "sale_id": 1,
    "reason": "Product defective",
    "description": "Screen cracked",
    "items": [
      {"sale_item_id": 1, "product_id": 1, "quantity": 1}
    ]
  }'
```

### Admin Workflow

```bash
# Validate RMA
curl -X POST http://localhost:5000/rma/admin/validate/1 \
  -H "Content-Type: application/json" \
  -d '{"approve": true, "validation_notes": "Approved", "validated_by": "admin"}'

# Mark received
curl -X POST http://localhost:5000/rma/admin/1/received \
  -H "Content-Type: application/json" \
  -d '{"actor": "warehouse"}'

# Complete inspection
curl -X POST http://localhost:5000/rma/admin/1/inspect/start \
  -H "Content-Type: application/json" \
  -d '{"inspected_by": "QA"}'

curl -X POST http://localhost:5000/rma/admin/1/inspect/complete \
  -H "Content-Type: application/json" \
  -d '{"result": "DEFECTIVE", "notes": "Confirmed defect", "inspected_by": "QA"}'

# Make disposition
curl -X POST http://localhost:5000/rma/admin/1/disposition \
  -H "Content-Type: application/json" \
  -d '{"disposition": "REFUND", "reason": "Defective confirmed"}'

# Process refund
curl -X POST http://localhost:5000/rma/admin/1/refund \
  -H "Content-Type: application/json" \
  -d '{"amount_cents": 99999, "method": "ORIGINAL_PAYMENT"}'
```

---

## Testing

Run the test suite:

```bash
docker-compose exec web python -m pytest tests/test_rma.py -v
```

---

## Database Schema

### Tables

- `rma_requests` - Main RMA records
- `rma_items` - Items being returned
- `refunds` - Refund transactions
- `rma_activity_log` - Audit trail
- `rma_metrics` - Daily metrics

See `migrations/0002_add_rma_tables.sql` for complete schema.

---

## Notes

- **Warranty Period**: Default 30 days from purchase
- **RMA Number Format**: `RMA-YYYYMMDD-NNNN`
- **Automatic Metrics**: Metrics are updated when RMA closes
- **Audit Trail**: All actions are logged in `rma_activity_log`
- **Idempotency**: Cannot submit duplicate RMA for same sale

---

## Future Enhancements

- [ ] Admin authentication for admin endpoints
- [ ] Email notifications at each step
- [ ] Upload photos directly via API
- [ ] Partial refunds
- [ ] Replacement product tracking
- [ ] Integration with shipping carriers
- [ ] Customer-facing web UI
- [ ] Advanced reporting dashboard
