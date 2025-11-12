# RMA Feature - Quick Reference

## 🚀 Getting Started (30 seconds)

```bash
# Start system
docker-compose up -d

# Test it's running
curl http://localhost:5000/health

# Open in browser
open http://localhost:5000
```

## 🎯 Testing RMA in 5 Steps

### 1. Login
- Go to: http://localhost:5000/login
- Username: `john`
- Password: `password123`

### 2. Buy Something
- Click **Products**
- Click **Buy** on any product
- You'll see a receipt

### 3. Request Return
- On receipt page, click **"Request Return"** button
- Select items to return
- Choose reason from dropdown
- Add description
- Click **Submit Return Request**

### 4. Track Your Return
- You're automatically redirected to the return details page
- Or go to: http://localhost:5000/rma/my-returns

### 5. View All Returns
- http://localhost:5000/rma/my-returns shows all your returns
- Click any RMA to see detailed status

## 📋 Key URLs

| Page | URL |
|------|-----|
| Login | http://localhost:5000/login |
| Products | http://localhost:5000/products |
| My Returns | http://localhost:5000/rma/my-returns |
| Health Check | http://localhost:5000/health |

## 🎨 RMA Status Colors

- 🟡 **SUBMITTED** - Waiting for approval
- 🟢 **APPROVED** - You can ship it back now
- 🔵 **SHIPPING** - In transit to warehouse
- 🔷 **RECEIVED** - Arrived at warehouse
- ⚫ **INSPECTING** - Being checked
- ✅ **COMPLETED** - Done! Refund issued
- 🔴 **REJECTED** - Return denied
- ⚪ **CANCELLED** - You cancelled it

## 💡 What You Can Do

### As a Customer
✅ Submit return requests
✅ View all your returns
✅ Track status in real-time
✅ Provide shipping tracking
✅ Cancel pending returns
✅ See refund details

### Admin Actions (via API)
Use curl commands to simulate admin:

```bash
# Approve a return
curl -X POST http://localhost:5000/rma/admin/validate/1 \
  -H "Content-Type: application/json" \
  -d '{"approved": true}'

# Mark as received
curl -X POST http://localhost:5000/rma/admin/1/received \
  -H "Content-Type: application/json"

# Process refund
curl -X POST http://localhost:5000/rma/admin/1/refund \
  -H "Content-Type: application/json" \
  -d '{"amount": 999.99, "method": "original_payment", "transaction_id": "TXN-123"}'
```

## 🐛 Troubleshooting

**Can't see "Request Return" button?**
→ Only COMPLETED orders can be returned

**"Please login" error?**
→ Login at http://localhost:5000/login first

**Containers not running?**
→ Run `docker-compose up -d`

**Database issues?**
→ Check: `docker logs checkpoint3-web`

## 📖 More Info

- **Full API Docs**: See `RMA_API.md`
- **Detailed Testing**: See `RMA_TESTING.md`
- **Implementation**: See `RMA_IMPLEMENTATION_SUMMARY.md`

## ✅ What's Implemented

✅ Complete 7-step RMA pipeline
✅ Customer web UI (request, view, track)
✅ REST API (12 endpoints)
✅ Database (5 tables with triggers)
✅ Authentication & authorization
✅ Activity audit logging
✅ Automatic metrics tracking
✅ Docker deployment

## 🎉 You're Ready!

Just login and buy a product to test the complete return flow!
