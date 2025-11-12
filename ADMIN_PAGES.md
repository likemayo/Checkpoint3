# Admin Pages Reference

This document lists all available admin pages and how to access them.

## 🔑 Admin Authentication

To access admin pages, you need to login first:

**Admin Login URL**: http://localhost:5000/partner/admin/login

**Default Admin Credentials**:
- Admin API Key: `admin-demo-key` (set via `ADMIN_API_KEY` environment variable)

### How to Login (Browser)

1. Go to: http://localhost:5000/partner/admin/login
2. Enter admin key: `admin-demo-key`
3. Click "Login"
4. You'll be redirected to the admin dashboard

### How to Login (API/CLI)

```bash
# Set admin key header
export ADMIN_KEY="admin-demo-key"

# Access admin endpoints
curl -H "X-Admin-Key: $ADMIN_KEY" http://localhost:5000/partner/admin/jobs
```

## 📊 Available Admin Pages

### 1. Partner Admin Dashboard
**URL**: http://localhost:5000/partner/admin

**Description**: Main admin dashboard with links to all admin features

**Access**: Public page (but actions require login)

**Features**:
- Links to all admin tools
- Partner management
- Job monitoring
- Metrics viewing
- Audit log access

---

### 2. Admin Login Page
**URL**: http://localhost:5000/partner/admin/login

**Description**: Login page for admin authentication

**Method**: GET (show form) / POST (submit credentials)

**Form Fields**:
- `admin_key`: The admin API key

---

### 3. Admin Metrics Dashboard
**URL**: http://localhost:5000/partner/admin/metrics

**Description**: View Prometheus-style metrics and statistics

**Access**: Requires admin login

**Displays**:
- HTTP request counts per endpoint
- Latency statistics (approximate p95)
- Onboarding success rate
- Contract validation attempts
- System performance metrics

---

### 4. Admin Jobs Viewer
**URL**: http://localhost:5000/partner/admin/jobs

**Description**: View and manage partner ingest jobs

**Access**: Requires admin login

**Features**:
- List all pending/in-progress/failed jobs
- View job details and diagnostics
- Requeue failed jobs
- Monitor job status

---

### 5. Admin Audit Log
**URL**: http://localhost:5000/partner/admin/audit

**Description**: View security audit log of partner operations

**Access**: Requires admin login

**Shows**:
- Partner API key usage
- Ingest attempts
- Job operations
- Admin actions
- Timestamps and details

---

### 6. Flash Sale Admin
**URL**: http://localhost:5000/admin/flash-sale

**Description**: Manage flash sales for products

**Access**: Currently no authentication required (TODO: add protection)

**Features**:
- View all active products
- Set flash sale price for products
- Remove flash sale from products
- See current flash sale status

**Actions**:
- POST `/admin/flash-sale/set` - Set flash sale
- POST `/admin/flash-sale/remove` - Remove flash sale

---

## 🔐 Admin Logout

**URL**: http://localhost:5000/partner/admin/logout (POST)

**Description**: Clear admin session

```bash
curl -X POST -b cookies.txt http://localhost:5000/partner/admin/logout
```

---

## 🧪 Testing Admin Pages in Docker

```bash
# Make sure containers are running
docker-compose ps

# Access admin login page
open http://localhost:5000/partner/admin/login

# Or use curl
curl http://localhost:5000/partner/admin/login

# Login via API
curl -X POST http://localhost:5000/partner/admin/login \
  -H "Content-Type: application/json" \
  -d '{"admin_key":"admin-demo-key"}'

# Access protected page with header
curl -H "X-Admin-Key: admin-demo-key" \
  http://localhost:5000/partner/admin/metrics
```

---

## 📝 Admin Routes Summary

| URL | Method | Auth Required | Description |
|-----|--------|---------------|-------------|
| `/partner/admin` | GET | No (but actions need auth) | Main admin dashboard |
| `/partner/admin/login` | GET | No | Login form |
| `/partner/admin/login` | POST | No | Submit login |
| `/partner/admin/logout` | POST | Yes | Logout |
| `/partner/admin/metrics` | GET | Yes | Metrics dashboard |
| `/partner/admin/jobs` | GET | Yes | Jobs viewer |
| `/partner/admin/audit` | GET | Yes | Audit log |
| `/admin/flash-sale` | GET | No ⚠️ | Flash sale management |
| `/admin/flash-sale/set` | POST | No ⚠️ | Set flash sale |
| `/admin/flash-sale/remove` | POST | No ⚠️ | Remove flash sale |

⚠️ = Currently not protected, should add authentication

---

## 🎨 Admin Templates

Admin page templates are located in:
- `/src/partners/templates/partners/admin.html` - Main dashboard
- `/src/partners/templates/partners/admin_login.html` - Login form
- `/src/partners/templates/partners/admin_metrics.html` - Metrics view
- `/src/partners/templates/partners/admin_jobs.html` - Jobs list
- `/src/templates/admin_flash_sale.html` - Flash sale management

---

## 🔧 Environment Variables

```bash
# Admin API key (default: admin-demo-key)
ADMIN_API_KEY=your-secure-admin-key

# In docker-compose.yml or .env
ADMIN_API_KEY=admin-demo-key
```

---

## 🚀 Quick Access Guide

### For Development (Docker)

1. **Start the application**:
   ```bash
   docker-compose up -d
   ```

2. **Access main admin dashboard**:
   ```
   http://localhost:5000/partner/admin
   ```

3. **Login with default key**:
   - Go to login page
   - Enter: `admin-demo-key`
   - Click Login

4. **Access admin features**:
   - Metrics: http://localhost:5000/partner/admin/metrics
   - Jobs: http://localhost:5000/partner/admin/jobs
   - Audit: http://localhost:5000/partner/admin/audit
   - Flash Sales: http://localhost:5000/admin/flash-sale

### For Production

1. **Change the admin key**:
   ```bash
   export ADMIN_API_KEY="your-secure-random-key-here"
   ```

2. **Update docker-compose.yml**:
   ```yaml
   environment:
     - ADMIN_API_KEY=${ADMIN_API_KEY}
   ```

3. **Restart services**:
   ```bash
   docker-compose restart
   ```

---

## 🐛 Troubleshooting

### "Missing or invalid admin key"

**Problem**: Can't access admin pages  
**Solution**: 
1. Login at `/partner/admin/login` with `admin-demo-key`
2. Or set `X-Admin-Key: admin-demo-key` header
3. Check `ADMIN_API_KEY` environment variable is set

### Admin pages return 404

**Problem**: Partners blueprint not registered  
**Solution**: 
1. Check `src/app.py` imports partners blueprint correctly
2. Look for import errors in logs: `docker-compose logs web`
3. Verify `src/partners/routes.py` exists

### Can't login

**Problem**: Login form doesn't work  
**Solution**:
1. Check browser console for errors
2. Verify POST to `/partner/admin/login` with correct JSON
3. Check session is being set (look for `Set-Cookie` header)

---

## 📚 Related Documentation

- [README.md](./README.md) - Main application documentation
- [DOCKER.md](./DOCKER.md) - Docker deployment guide
- [docs/ADR/0006-admin-access-control.md](./docs/ADR/0006-admin-access-control.md) - Admin security design
