# Docker Deployment Testing Guide

This document provides step-by-step instructions for testing the Docker deployment.

## Prerequisites Checklist

- [ ] Docker Desktop installed and running
- [ ] Docker Compose available (run `docker-compose --version`)
- [ ] Port 5000 is available (not used by another service)
- [ ] At least 2GB free disk space

## Testing Steps

### 1. Build the Docker Images

```bash
cd /path/to/Checkpoint3
docker-compose build
```

**Expected Output:**
- Should complete without errors
- Should see "Successfully built" and "Successfully tagged" messages

**Troubleshooting:**
- If build fails, check that Dockerfile exists
- Ensure requirements.txt is present and valid
- Check Docker daemon is running: `docker info`

### 2. Start the Services

```bash
docker-compose up
```

Or run in background:
```bash
docker-compose up -d
```

**Expected Output:**
- Services should start: `checkpoint3-web`, `checkpoint3-worker`
- Database initialization should complete
- Migrations should run successfully
- Flask app should start on port 5000

**Look for these log messages:**
```
checkpoint3-web | Starting Checkpoint3 application...
checkpoint3-web | Initializing database...
checkpoint3-web | Running database migrations...
checkpoint3-web | Starting Flask application on port 5000...
```

### 3. Verify Health Endpoints

Wait 30-40 seconds for services to fully start, then test:

```bash
# Basic health check
curl http://localhost:5000/health

# Expected: {"status": "ok", "service": "checkpoint3-web"}

# Readiness check
curl http://localhost:5000/ready

# Expected: {"status": "ready", "database": "connected"}
```

**Troubleshooting:**
- If connection refused: Wait a bit longer, services may still be starting
- Check container status: `docker-compose ps`
- View logs: `docker-compose logs web`

### 4. Test Web Interface

Open browser and navigate to:
```
http://localhost:5000
```

**Expected Behavior:**
- Should redirect to login page
- Should see registration link
- No error messages in browser console

**Test User Registration:**
1. Click "Register" (if available)
2. Create a test account:
   - Name: Test User
   - Username: testuser
   - Password: test123
3. Should redirect to login or products page

**Test Login:**
1. Go to http://localhost:5000/login
2. Login with credentials
3. Should see products page

### 5. Seed Database (Optional)

If products aren't showing up:

```bash
docker-compose exec web python src/seed.py
```

**Expected Output:**
```
Seeding database at: /app/data/app.sqlite
Inserted user: john
Inserted user: jane
Inserted user: alice
Products seeded successfully!
Total users: 3
Total active products: 5
```

### 6. Test Product Functionality

1. **View Products**: Navigate to products page
2. **Add to Cart**: Click "Add to Cart" on any product
3. **View Cart**: Should see items in cart
4. **Checkout**: Complete checkout process
5. **View Receipt**: Should see order confirmation

### 7. Run Automated Tests

```bash
# Run all tests
docker-compose exec web python -m pytest -v

# Run specific test file
docker-compose exec web python -m pytest tests/test_product_repo.py -v

# Run with coverage
docker-compose exec web python -m pytest --cov=src --cov-report=term
```

**Expected Output:**
- All tests should pass
- No import errors
- Coverage report (if using --cov)

### 8. Test Database Persistence

```bash
# 1. Add some data (register user, add products to cart)

# 2. Stop services
docker-compose down

# 3. Start services again
docker-compose up -d

# 4. Check data persists
curl http://localhost:5000/ready

# Login with same user - data should still be there
```

**Expected Behavior:**
- User accounts persist
- Products persist
- Cart data persists (if saved to DB)

### 9. Test Background Worker

```bash
# View worker logs
docker-compose logs worker

# Should see worker startup messages
```

**Expected Output:**
```
checkpoint3-worker | Worker started...
```

### 10. Test Migrations

```bash
# Check current migration state
docker-compose exec web python scripts/run_migrations.py

# Should complete without errors
```

### 11. Test Database Access

```bash
# Open SQLite shell
docker-compose exec web sqlite3 /app/data/app.sqlite

# Run a query
.tables
SELECT COUNT(*) FROM user;
SELECT COUNT(*) FROM product;
.quit
```

### 12. Test Admin Features (if implemented)

```bash
# Test metrics endpoint (requires admin session)
curl -H "Cookie: session=..." http://localhost:5000/metrics

# Or test with API key if configured
export ADMIN_API_KEY=admin-demo-key
curl -H "X-Admin-Key: $ADMIN_API_KEY" http://localhost:5000/partner/jobs
```

### 13. Test Cleanup

```bash
# Stop services
docker-compose down

# Remove volumes (clean slate)
docker-compose down -v

# Verify containers are stopped
docker-compose ps
```

## Performance Testing

### Load Testing (Optional)

If you want to test under load:

```bash
# Install Apache Bench (if not available)
# macOS: brew install httpd

# Simple load test
ab -n 1000 -c 10 http://localhost:5000/health

# Expected: All requests should succeed
```

### Concurrent Checkout Test

```bash
docker-compose exec web python -m tests.test_concurrent_checkout

# Should demonstrate proper stock locking
```

## Common Issues and Solutions

### Issue: Port 5000 already in use
**Solution:**
```bash
# Find what's using port 5000
lsof -i :5000

# Kill the process or change port in docker-compose.yml
# Edit ports: - "8000:5000" to use port 8000 instead
```

### Issue: Database locked
**Solution:**
```bash
# Stop all containers
docker-compose down -v

# Clean rebuild
docker-compose up --build
```

### Issue: Container keeps restarting
**Solution:**
```bash
# Check logs for errors
docker-compose logs web

# Common causes:
# - Database initialization failed
# - Missing dependencies
# - Syntax error in Python code
```

### Issue: Cannot connect to database
**Solution:**
```bash
# Exec into container
docker-compose exec web /bin/bash

# Check if database file exists
ls -la /app/data/

# Try manual initialization
python src/main.py
```

### Issue: Tests failing
**Solution:**
```bash
# Check Python environment
docker-compose exec web python --version

# Check installed packages
docker-compose exec web pip list

# Rebuild with no cache
docker-compose build --no-cache
```

## Verification Checklist

After completing tests, verify:

- [ ] Docker images built successfully
- [ ] Containers start without errors
- [ ] Health endpoint returns 200 OK
- [ ] Readiness endpoint returns 200 OK
- [ ] Web interface loads in browser
- [ ] User registration works
- [ ] User login works
- [ ] Products display correctly
- [ ] Add to cart functionality works
- [ ] Checkout completes successfully
- [ ] Tests pass in container
- [ ] Database persists after restart
- [ ] Worker starts successfully
- [ ] Migrations run successfully
- [ ] Can access database via SQLite shell
- [ ] Cleanup works (docker-compose down)

## Success Criteria

✅ **Deployment Successful** if:
1. All containers start with `docker-compose up`
2. Health endpoints return success
3. Web interface is accessible
4. Core functionality works (login, products, checkout)
5. Tests pass in containerized environment
6. Data persists across restarts

## Next Steps

After successful testing:
1. Document any environment-specific configurations
2. Update .env.example with required variables
3. Add any missing tests
4. Update documentation with lessons learned
5. Consider adding docker-compose.prod.yml for production

## Support

If you encounter issues not covered here:
1. Check Docker logs: `docker-compose logs`
2. Verify Docker Desktop is running
3. Check system resources (CPU, memory, disk)
4. Review Dockerfile and docker-compose.yml syntax
5. Test with minimal configuration first

For more information:
- [DOCKER.md](./DOCKER.md) - Detailed Docker documentation
- [README.md](./README.md) - General application documentation
- [docs/Runbook.md](./docs/Runbook.md) - Operations runbook
