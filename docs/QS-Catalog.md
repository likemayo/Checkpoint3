# Quality Scenarios - E-Commerce System (RMA, Flash Sales, Partner Integration, Observability)

**Project:** Checkpoint 3 - Quality Attributes Implementation & Monitoring  
**Date:** November 13, 2025  
**Team:** Retail System — RMA (Returns), Flash Sales, Partner Integration, Observability

This document specifies all quality attribute scenarios for the complete e-commerce system, covering Flash Sales, Partner Integration, RMA (Returns), and Observability modules.

---

## Table of Contents
1. [Availability Scenarios](#availability-scenarios) (2 scenarios)
2. [Security Scenarios](#security-scenarios) (2 scenarios)
3. [Modifiability Scenarios](#modifiability-scenarios) (2 scenarios)
4. [Performance Scenarios](#performance-scenarios) (2 scenarios)
5. [Integrability Scenarios](#integrability-scenarios) (2 scenarios)
6. [Testability Scenarios](#testability-scenarios) (2 scenarios)
7. [Usability Scenarios](#usability-scenarios) (2 scenarios)
8. [Reliability Scenarios](#reliability-scenarios) (2 scenarios)
9. [Observability Scenarios](#observability-scenarios) (2 scenarios)
10. [Summary Table](#summary-table)

---

## Availability Scenarios

### Scenario A1: Flash Sale Traffic Overload Protection (Flash Sales Module)

| Aspect | Description |
|--------|-------------|
| **Source** | Multiple concurrent users (1000+ simultaneous requests) |
| **Stimulus** | Users attempt to access flash sale products and checkout during peak sale hours |
| **Environment** | Normal system operation during an active flash sale with high traffic volume |
| **Artifact** | Flash sale checkout endpoint (`/flash/checkout`) |
| **Response** | System applies rate limiting to prevent overload, queuing excessive requests and responding with appropriate HTTP 429 (Too Many Requests) status for requests exceeding the limit. Users receive clear instructions to retry after waiting period. |
| **Response Measure** | - No more than 5 checkout requests per user per 60-second window are processed<br>- Rate-limited requests receive clear error messages within 100ms<br>- System remains responsive for legitimate requests<br>- No system crashes or downtime occurs<br>- 99% uptime maintained during flash sales |

**Architectural Tactics:**
- **Rate Limiting:** Sliding window algorithm prevents system overload
- **Implicit Client-Side Queuing:** Users told when to retry, distributing load
- **Graceful Degradation:** System remains functional, provides clear feedback

**Implementation:**
- `src/flash_sales/rate_limiter.py` - RateLimiter class with sliding window
- `tests/flash_sales/test_rate_limiter.py` - Comprehensive unit tests

**Module:** Flash Sales

---

### Scenario A2: Payment Service Failure Recovery (Flash Sales Module)

| Aspect | Description |
|--------|-------------|
| **Source** | External payment processing service |
| **Stimulus** | Payment service experiences temporary outage or becomes unresponsive during flash sale checkout |
| **Environment** | High-load conditions during active flash sale with concurrent payment processing attempts |
| **Artifact** | Payment processing function in flash sale checkout flow |
| **Response** | - System detects payment service failures through circuit breaker monitoring<br>- After 3 consecutive failures, circuit opens and prevents further attempts<br>- Failed payment attempts are retried up to 3 times with exponential backoff<br>- Users receive clear error messages indicating payment issues<br>- Circuit automatically attempts to close after 30-second timeout period |
| **Response Measure** | - Circuit breaker opens after 3 failures within 60 seconds<br>- No more than 3 retry attempts per transaction<br>- Circuit breaker timeout of 30 seconds before half-open state<br>- 95% of transient failures recovered through retry mechanism<br>- Users receive response within 5 seconds even when service is down<br>- No cascade failures to other system components |

**Architectural Tactics:**
- **Circuit Breaker Pattern:** Prevents cascade failures and protects downstream services
- **Retry with Exponential Backoff:** Recovers from transient failures automatically
- **Timeout Management:** Bounded retry attempts prevent indefinite hangs

**Implementation:**
- `src/flash_sales/circuit_breaker.py` - CircuitBreaker class with state management
- `src/flash_sales/retry.py` - Retry decorator with exponential backoff
- `src/flash_sales/payment_resilience.py` - Integration of both tactics
- `tests/flash_sales/test_circuit_breaker.py` - Circuit breaker behavior tests
- `tests/flash_sales/test_retry.py` - Retry logic validation

**Module:** Flash Sales

---

## Security Scenarios

### Scenario S1: Partner API Authentication (Partner Integration Module)

| Aspect | Description |
|--------|-------------|
| **Source** | External partner attempting to upload product feed |
| **Stimulus** | Partner submits HTTP request to `/partner/ingest` endpoint with or without valid API key |
| **Environment** | Production environment with multiple registered partners |
| **Artifact** | Partner ingest API endpoint and authentication middleware |
| **Response** | - System validates API key before processing request<br>- Invalid or missing API keys result in HTTP 401 Unauthorized response<br>- Valid API keys allow request to proceed to validation layer<br>- All authentication attempts are logged for security audit |
| **Response Measure** | - 100% of requests without valid API keys are rejected<br>- Authentication check completes in <50ms<br>- No unauthorized access to partner endpoints<br>- All authentication failures logged with timestamp and source IP<br>- Zero false positives (valid partners never incorrectly rejected) |

**Architectural Tactics:**
- **Authentication:** API key-based authentication for partner identification
- **Authorization:** Middleware validates credentials before granting access
- **Audit Logging:** All authentication attempts logged for security analysis

**Implementation:**
- `src/partners/auth_middleware.py` - API key verification
- Partner API keys stored securely in database
- `tests/partners/test_auth_middleware.py` - Authentication validation tests

**Module:** Partner Integration

---

### Scenario S2: Malicious Input Protection (Partner Integration Module)

| Aspect | Description |
|--------|-------------|
| **Source** | Malicious actor or compromised partner system |
| **Stimulus** | Partner submits product feed containing SQL injection attempts, XSS payloads, or malformed data |
| **Environment** | Production environment receiving external partner feeds |
| **Artifact** | Input validation layer and partner feed parser |
| **Response** | - All input data sanitized and validated before processing<br>- SQL injection attempts detected and rejected<br>- XSS payloads neutralized through input sanitization<br>- Malformed data rejected with clear error messages<br>- Malicious attempts logged for security investigation |
| **Response Measure** | - 100% of SQL injection attempts blocked<br>- All input validated against schema before database insertion<br>- Malicious feeds rejected within 100ms of detection<br>- No data corruption or unauthorized database access<br>- Security events logged with full request details for forensic analysis |

**Architectural Tactics:**
- **Input Validation:** Schema-based validation of all partner data
- **Input Sanitization:** Remove or escape potentially dangerous characters
- **Parameterized Queries:** All database operations use prepared statements to prevent SQL injection
- **Whitelisting:** Only allowed data formats and structures accepted

**Implementation:**
- `src/partners/validators.py` - Input validation and sanitization
- `src/partners/partner_adapters.py` - Safe feed parsing
- `tests/partners/test_input_validation.py` - Validation logic tests

**Module:** Partner Integration

---

## Modifiability Scenarios

### Scenario M1: Adding New Partner Feed Format (Partner Integration Module)

| Aspect | Description |
|--------|-------------|
| **Source** | Development team |
| **Stimulus** | Business requirement to support new partner with XML feed format (currently support CSV and JSON) |
| **Environment** | Development environment with existing partner integration system |
| **Artifact** | Partner adapter layer and feed parsing logic |
| **Response** | - Developer creates new adapter class implementing standard interface<br>- New adapter added to adapter registry without modifying existing code<br>- System automatically routes XML feeds to new adapter<br>- No changes required to validation, queue, or worker components |
| **Response Measure** | - New feed format support added in <4 hours of development time<br>- Zero changes to existing adapter code (Open/Closed Principle)<br>- All existing tests continue to pass<br>- New adapter covered by unit tests<br>- No system downtime required for deployment |

**Architectural Tactics:**
- **Adapter Pattern:** Isolates feed format differences behind common interface
- **Plugin Architecture:** New adapters added through registration without core changes
- **Open/Closed Principle:** System open for extension, closed for modification

**Implementation:**
- `src/partners/partner_adapters.py` - Adapter interface and implementations
- Abstract base class defines adapter contract
- Adapter registry maps content types to adapter classes
- `tests/partners/test_partner_adapters.py` - Adapter behavior tests

**Module:** Partner Integration

---

### Scenario M2: Adding New Payment Method (Shared Module)

| Aspect | Description |
|--------|-------------|
| **Source** | Product management team |
| **Stimulus** | Business requirement to support cryptocurrency payment option |
| **Environment** | Production system with existing payment methods (credit card, PayPal) |
| **Artifact** | Payment processing layer and payment adapter |
| **Response** | - Developer implements new payment strategy class<br>- New payment method registered in payment strategy registry<br>- Checkout UI automatically includes new payment option<br>- No changes to checkout flow logic or transaction handling |
| **Response Measure** | - New payment method added in <8 hours of development time<br>- Zero changes to existing payment method implementations<br>- Checkout logic unchanged (strategy pattern abstraction)<br>- New payment method fully tested in isolation<br>- Rollout possible without affecting existing payment methods |

**Architectural Tactics:**
- **Strategy Pattern:** Different payment methods implemented as interchangeable strategies
- **Dependency Injection:** Payment strategies injected at runtime
- **Interface Segregation:** Each payment method implements common interface

**Implementation:**
- `src/payment.py` - Payment adapter with strategy pattern
- Each payment method as separate strategy class
- Payment strategy registry for dynamic selection
- Circuit breaker and retry apply to all payment strategies uniformly

**Module:** Shared (Both Modules)

---

## Performance Scenarios

### Scenario P1: Bounded Flash Sale Product Listing Latency (Flash Sales Module)

| Aspect | Description |
|--------|-------------|
| **Source** | Multiple users browsing flash sale products |
| **Stimulus** | Users navigate to flash sale product listing page during active sales |
| **Environment** | High concurrent user load (500+ simultaneous users) during peak flash sale hours |
| **Artifact** | Flash sale product listing endpoint (`/flash/products`) |
| **Response** | - System serves flash sale product data from in-memory cache<br>- Cache is populated on first request and refreshed every 30 seconds<br>- Expensive database queries are minimized through caching<br>- Cache automatically expires and refreshes to ensure data accuracy |
| **Response Measure** | - Product listing page loads in under 200ms for cached requests<br>- Cache hit rate of >90% during flash sale periods<br>- Maximum of 1 database query per 30-second window for product listings<br>- System handles 1000+ requests per second for product listings<br>- Database CPU usage remains below 30% during peak traffic |

**Architectural Tactics:**
- **Caching:** In-memory cache with TTL-based expiration
- **Read Optimization:** Cache frequently accessed flash sale product data
- **Lazy Loading:** Cache populated on-demand

**Implementation:**
- `src/flash_sales/cache.py` - SimpleCache class with TTL management
- Applied to flash sale routes for product listing optimization

**Module:** Flash Sales

---

### Scenario P2: Concurrent Checkout Processing (Flash Sales Module)

| Aspect | Description |
|--------|-------------|
| **Source** | Multiple users attempting simultaneous checkout |
| **Stimulus** | 100+ users attempt to purchase flash sale items concurrently during final minutes of sale |
| **Environment** | High-load conditions with limited product inventory |
| **Artifact** | Flash sale checkout transaction processing |
| **Response** | - System processes checkout requests concurrently<br>- Database transactions ensure inventory consistency<br>- Rate limiting prevents system overload from excessive requests<br>- Each successful checkout completes atomically (payment + inventory update)<br>- Stock checks and decrements happen atomically to prevent overselling |
| **Response Measure** | - Individual checkout completes in under 2 seconds under normal load<br>- No overselling of products (inventory remains consistent)<br>- Rate limiting maintains <3 second response time under extreme load<br>- System throughput of 50+ successful checkouts per second<br>- Database transaction deadlocks occur in <0.1% of transactions |

**Architectural Tactics:**
- **Rate Limiting:** Controls request volume to maintain performance
- **Transaction Management:** Ensures data consistency under concurrent access
- **Optimistic Concurrency:** Database-level stock checks prevent overselling
- **Resource Pooling:** Database connection pooling for efficient resource usage

**Implementation:**
- `src/flash_sales/rate_limiter.py` - Checkout endpoint protection
- Database transaction handling in checkout flow with BEGIN/COMMIT/ROLLBACK
- Stock validation logic in FlashSaleManager with atomic operations

**Module:** Flash Sales

---

## Integrability Scenarios

### Scenario I1: Onboarding New Partner (Partner Integration Module)

| Aspect | Description |
|--------|-------------|
| **Source** | Business development team |
| **Stimulus** | New partner company needs to integrate their product catalog with our system |
| **Environment** | Production environment with existing partner integrations |
| **Artifact** | Partner onboarding process and API integration |
| **Response** | - Partner provided with API documentation and sample feeds<br>- API key generated for partner authentication<br>- Partner submits test feed to staging environment for validation<br>- System validates feed format and provides detailed feedback<br>- Upon successful validation, partner enabled in production |
| **Response Measure** | - Partner onboarding completed in <1 business day<br>- API documentation provides all necessary integration details<br>- Test environment available for partner validation<br>- Detailed error messages guide partner to fix issues<br>- No custom code changes required for standard feed formats<br>- Partner can validate integration independently without engineering support |

**Architectural Tactics:**
- **API Documentation:** Clear, comprehensive API documentation for self-service integration
- **Standardized Interface:** Common API contract for all partners
- **Validation Feedback:** Detailed error messages guide correct integration
- **Sandbox Environment:** Test environment for safe partner validation

**Implementation:**
- `docs/API.md` - Partner API documentation
- `src/partners/partner_ingest_service.py` - Standardized ingest endpoint
- `src/partners/validators.py` - Validation with detailed error reporting
- Admin interface for API key generation

**Module:** Partner Integration

---

### Scenario I2: Partner Webhook Integration (Partner Integration Module)

| Aspect | Description |
|--------|-------------|
| **Source** | External partner system |
| **Stimulus** | Partner's inventory system sends real-time stock updates via webhook |
| **Environment** | Production environment with asynchronous webhook processing |
| **Artifact** | Webhook receiver endpoint and event processing |
| **Response** | - System receives webhook POST request from partner<br>- Webhook validated and authenticated<br>- Stock updates processed asynchronously through job queue<br>- Acknowledgment sent immediately to partner<br>- Partner notified of processing completion via callback URL |
| **Response Measure** | - Webhook requests acknowledged within 100ms<br>- All webhook payloads validated for authenticity<br>- Stock updates processed within 5 seconds of receipt<br>- Failed webhooks retried up to 3 times with exponential backoff<br>- 99.9% of webhooks successfully processed<br>- Partner receives confirmation of successful processing |

**Architectural Tactics:**
- **Asynchronous Processing:** Webhooks processed in background to avoid blocking
- **Queue-Based Architecture:** Job queue decouples webhook receipt from processing
- **Event-Driven Integration:** Real-time updates through event notifications
- **Idempotency:** Duplicate webhook deliveries handled gracefully

**Implementation:**
- `src/partners/webhook_handler.py` - Webhook receiver endpoint (if implemented)
- `src/partners/ingest_queue.py` - Asynchronous job queue
- `src/partners/ingest_worker.py` - Background webhook processing
- Webhook authentication using partner API keys

**Module:** Partner Integration

---

## Testability Scenarios

### Scenario T1: Automated Flash Sale Load Testing (Flash Sales Module)

| Aspect | Description |
|--------|-------------|
| **Source** | Development/QA team |
| **Stimulus** | Developer needs to verify system behavior under flash sale load conditions |
| **Environment** | Test environment with automated test suite |
| **Artifact** | Flash sale module (rate limiter, circuit breaker, retry logic, flash sale manager) |
| **Response** | - Comprehensive unit tests verify each component in isolation<br>- Tests can simulate failure conditions (payment failures, service timeouts)<br>- Tests verify rate limiting behavior under load<br>- Tests confirm circuit breaker state transitions<br>- All tests executable via pytest with no manual intervention |
| **Response Measure** | - 100% code coverage for critical flash sale components<br>- All tests execute in under 30 seconds<br>- Tests can reliably reproduce failure scenarios<br>- Zero flaky tests (consistent pass/fail behavior)<br>- Tests provide clear failure messages for debugging |

**Architectural Tactics:**
- **Unit Testing:** Isolated tests for each component
- **Mocking/Stubbing:** Simulate external dependencies and failure conditions
- **Automated Test Execution:** pytest framework integration
- **Test Fixtures:** Reusable test database and mock objects

**Implementation:**
- `tests/flash_sales/test_rate_limiter.py` - Rate limiter validation
- `tests/flash_sales/test_circuit_breaker.py` - Circuit breaker state tests
- `tests/flash_sales/test_retry.py` - Retry logic verification
- `tests/flash_sales/test_flash_sale_manager.py` - Flash sale business logic tests

**Module:** Flash Sales

---

### Scenario T2: Partner Feed Validation Testing (Partner Integration Module)

| Aspect | Description |
|--------|-------------|
| **Source** | Development/QA team |
| **Stimulus** | Developer needs to verify partner feed validation handles all edge cases |
| **Environment** | Test environment with sample partner feeds |
| **Artifact** | Partner feed validation and parsing logic |
| **Response** | - Unit tests cover valid and invalid feed formats<br>- Tests verify SQL injection prevention<br>- Tests confirm malformed data rejection<br>- Tests validate error message clarity<br>- Sample feeds available for regression testing |
| **Response Measure** | - 100% code coverage for validation logic<br>- Tests execute in under 20 seconds<br>- All validation rules tested with positive and negative cases<br>- Security vulnerabilities (SQL injection, XSS) tested explicitly<br>- Clear test failure messages identify exact validation rule violated |

**Architectural Tactics:**
- **Unit Testing:** Comprehensive validation rule testing
- **Test Data Generation:** Sample feeds representing valid and invalid scenarios
- **Security Testing:** Explicit tests for injection attacks
- **Boundary Testing:** Edge cases and malformed data tested

**Implementation:**
- `tests/partners/test_partner_ingest.py` - Integration tests
- `tests/partners/test_input_validation.py` - Validation logic tests
- `tests/partners/test_partner_adapters.py` - Feed parsing tests
- Sample feed files in `tests/fixtures/`

**Module:** Partner Integration

---

## Usability Scenarios

### Scenario U1: Clear Error Feedback for Failed Checkouts (Flash Sales Module)

| Aspect | Description |
|--------|-------------|
| **Source** | End user attempting flash sale purchase |
| **Stimulus** | User encounters error during checkout (rate limit exceeded, payment failure, or out of stock) |
| **Environment** | Normal system operation during flash sale |
| **Artifact** | Flash sale checkout user interface and error handling |
| **Response** | - System provides specific, actionable error messages<br>- User understands why checkout failed<br>- Error messages suggest next steps (e.g., "Please try again in 60 seconds")<br>- No technical jargon or stack traces shown to users<br>- Error messages maintain professional, helpful tone |
| **Response Measure** | - Error messages display within 100ms of error occurrence<br>- All error types have user-friendly messages:<br>&nbsp;&nbsp;• Rate limit: "Too many requests. Please wait and try again."<br>&nbsp;&nbsp;• Payment failure: "Payment could not be processed. Please try again or use different payment method."<br>&nbsp;&nbsp;• Out of stock: "This item is no longer available."<br>&nbsp;&nbsp;• Service unavailable: "System experiencing high traffic. Please try again shortly."<br>- 95% of users understand error message without contacting support<br>- Error messages logged for developer debugging while hiding technical details |

**Architectural Tactics:**
- **User-Centered Error Handling:** Friendly, actionable error messages
- **Graceful Degradation:** System remains functional and communicative during failures
- **Separation of Concerns:** Technical error logging separate from user-facing messages
- **Progressive Disclosure:** Show user-friendly message, log technical details

**Implementation:**
- Error handling in `src/flash_sales/routes.py`
- HTTP status codes (429, 503, 400) with descriptive JSON responses
- User-facing error messages in checkout flow

**Module:** Flash Sales

---

### Scenario U2: Partner Feed Upload Feedback (Partner Integration Module)

| Aspect | Description |
|--------|-------------|
| **Source** | Partner administrator uploading product feed |
| **Stimulus** | Partner submits product feed via web interface or API |
| **Environment** | Normal system operation with partner upload interface |
| **Artifact** | Partner upload UI and validation feedback system |
| **Response** | - System provides immediate acknowledgment of feed receipt<br>- Real-time validation feedback shows progress<br>- Clear indication of feed acceptance or rejection<br>- Detailed error messages for rejected feeds with line numbers<br>- Success confirmation includes number of products processed |
| **Response Measure** | - Feed receipt acknowledged within 100ms<br>- Validation status visible within 2 seconds<br>- Error messages include specific line/field causing failure<br>- 90% of partners can fix feed errors without support<br>- Job status queryable via API endpoint<br>- Email notification sent upon completion (success or failure) |

**Architectural Tactics:**
- **User Feedback:** Clear, timely feedback on upload status
- **Progress Indication:** Status updates during async processing
- **Detailed Error Reporting:** Specific error location and description
- **Multi-Channel Notification:** UI status + email confirmation

**Implementation:**
- `src/partners/routes.py` - Upload endpoint with validation feedback
- `src/templates/partners/partner_upload.html` - Upload UI with progress indicator
- `src/partners/validators.py` - Detailed validation error messages
- Job status endpoint for progress polling

**Module:** Partner Integration

---

## Reliability Scenarios

### Scenario R1: RMA Workflow Consistency & Integrity (RMA Module)

| Aspect | Description |
|--------|-------------|
| **Source** | Customer submitting or updating an RMA request |
| **Stimulus** | Multiple RMA requests and updates occur concurrently (submit, validate, approve, disposition, complete) |
| **Environment** | Normal operation with simultaneous admin actions (Support, Warehouse, Finance) |
| **Artifact** | RMA workflow routes and DB transactions |
| **Response** | - Status transitions enforced according to workflow rules<br>- Each transition is atomic with DB transaction boundaries<br>- Inventory, store credit, and refunds remain consistent |
| **Response Measure** | - 0 illegal status transitions<br>- 0 lost updates under concurrent actions<br>- 100% audit log entries for each state change |

**Architectural Tactics:**
- Transactions with commit/rollback
- Status transition validation (state machine rules)
- Audit logging on each change

**Implementation:**
- `src/rma/routes.py` — transition endpoints and validation
- `src/dao.py` — transaction handling
- Tests: `tests/test_worker_end_to_end.py`, `tests/test_validation.py`

**Module:** RMA (Returns)

---

### Scenario R2: Refund Disposition Accuracy & Auditability (RMA Module)

| Aspect | Description |
|--------|-------------|
| **Source** | Finance/Admin setting refund disposition |
| **Stimulus** | Admin chooses REFUND, REPLACEMENT, REPAIR, STORE_CREDIT, or REJECT |
| **Environment** | Normal operations; multiple RMAs processed per hour |
| **Artifact** | Disposition logic and audit table |
| **Response** | - Disposition stored accurately and reflected in metrics<br>- Store credit and order state updated consistently<br>- Audit row written with who/when/what |
| **Response Measure** | - 100% of completed RMAs have disposition set<br>- Metrics Approved/Rejected/Pending match DB query results<br>- Audit trail present for 100% of changes |

**Architectural Tactics:**
- Multi-stage validation before disposition
- Consistent write + audit trail pattern
- Metrics instrumentation on disposition

**Implementation:**
- `src/rma/routes.py` — disposition handling
- `src/observability/metrics_collector.py` — refunds query logic
- Tests: `tests/test_audit_entries.py`, `tests/test_testability_integration.py`

**Module:** RMA (Returns)

---

## Observability Scenarios

### Scenario O1: Monitoring Dashboard Accuracy from Persistent Metrics (Observability)

| Aspect | Description |
|--------|-------------|
| **Source** | Administrator viewing Monitoring Dashboard |
| **Stimulus** | Dashboard auto-refreshes every 5 seconds |
| **Environment** | System recently restarted (in-memory counters reset) |
| **Artifact** | Metrics aggregator and dashboard view |
| **Response** | - Orders and Refunds cards use DB-backed counts so values persist across restarts<br>- In-memory rates complement DB counts for freshness |
| **Response Measure** | - Orders/Refunds totals match database at time of query<br>- No all-zero regressions after restart |

**Architectural Tactics:**
- Hybrid metrics: DB queries for totals + in-memory for rates
- Smart seeding (first-run only) to preserve data

**Implementation:**
- `src/observability/metrics_collector.py` — DB-backed metrics
- `docker-entrypoint.sh` — seed only if DB empty
- `src/templates/monitoring/dashboard.html` — admin-only

**Module:** Observability

---

### Scenario O2: Response Time Tracking and Percentiles (Observability)

| Aspect | Description |
|--------|-------------|
| **Source** | Any HTTP request |
| **Stimulus** | Requests flow through Flask app middleware |
| **Environment** | Normal operation |
| **Artifact** | Observability middleware and histogram store |
| **Response** | - Each request duration recorded via after_request middleware<br>- Percentiles (P50/P95/P99) computed from histogram |
| **Response Measure** | - Non-zero avg and percentiles after generating traffic<br>- P95 available for SLO checks on dashboard |

**Architectural Tactics:**
- Middleware timing via `before_request`/`after_request`
- Histogram observations for `http_request_duration_seconds`

**Implementation:**
- `src/app.py` — after_request metrics observe
- `src/observability/metrics_collector.py` — histogram stats and percentiles
- Tests: `tests/test_usability_endpoints.py` — endpoint-level checks

**Module:** Observability

---

## Summary Table

| Quality Attribute | Scenario ID | Module | Scenario Name | Tactic/Pattern | Implementation |
|-------------------|-------------|--------|---------------|----------------|----------------|
| **Availability** | A1 | Flash Sales | Traffic Overload Protection | Rate Limiting + Implicit Queuing | `rate_limiter.py` |
| **Availability** | A2 | Flash Sales | Payment Failure Recovery | Circuit Breaker + Retry | `circuit_breaker.py`, `retry.py`, `payment_resilience.py` |
| **Security** | S1 | Partner | API Authentication | Authentication + Authorization | `auth_middleware.py` |
| **Security** | S2 | Partner | Malicious Input Protection | Input Validation + Sanitization | `validators.py` |
| **Modifiability** | M1 | Partner | New Partner Feed Format | Adapter Pattern | `partner_adapters.py` |
| **Modifiability** | M2 | Shared | New Payment Method | Strategy Pattern | `payment.py` |
| **Performance** | P1 | Flash Sales | Bounded Listing Latency | Caching | `cache.py` |
| **Performance** | P2 | Flash Sales | Concurrent Checkout | Rate Limiting + Transactions | `rate_limiter.py` + DB transactions |
| **Integrability** | I1 | Partner | Onboarding New Partner | API Documentation + Validation Feedback | API docs, validators |
| **Integrability** | I2 | Partner | Partner Webhook Integration | Async Processing + Queue | `webhook_handler.py`, `ingest_queue.py` |
| **Testability** | T1 | Flash Sales | Automated Load Testing | Unit Testing + Mocking | `tests/flash_sales/*` |
| **Testability** | T2 | Partner | Feed Validation Testing | Unit Testing + Security Testing | `tests/partners/*` |
| **Usability** | U1 | Flash Sales | Clear Error Feedback | User-Centered Error Handling | Error responses in routes |
| **Usability** | U2 | Partner | Upload Feedback | User Feedback + Progress Indication | Partner upload UI |
| **Reliability** | R1 | RMA | RMA Workflow Consistency & Integrity | Transactions + Status Transition Validation | `src/rma/routes.py`, `src/dao.py` |
| **Reliability** | R2 | RMA | Refund Disposition Accuracy & Audit | Multi-stage Validation + Audit Trail | `src/rma/routes.py`, `src/partners/metrics.py` |
| **Observability** | O1 | Observability | Dashboard Accuracy from Persistent Metrics | DB-backed Metrics + Smart Seeding | `src/observability/metrics_collector.py`, `docker-entrypoint.sh` |
| **Observability** | O2 | Observability | Response Time Tracking (P95/P99) | Middleware Timing + Histograms | `src/app.py`, `src/observability/metrics_collector.py` |

### Tactics Summary

**Total Unique Tactics Implemented: 18**

#### Flash Sales Module (6 tactics):
1. **Rate Limiting** - Sliding window algorithm (Availability & Performance)
2. **Circuit Breaker** - State-based failure detection (Availability)
3. **Retry with Exponential Backoff** - Transient failure recovery (Availability)
4. **Caching** - In-memory TTL-based cache (Performance)
5. **Unit Testing & Mocking** - Comprehensive test coverage (Testability)
6. **User-Centered Error Handling** - Clear, actionable messages (Usability)

#### Partner Integration Module (8 tactics):
7. **Authentication & Authorization** - API key validation (Security)
8. **Input Validation & Sanitization** - Malicious input protection (Security)
9. **Adapter Pattern** - Feed format abstraction (Modifiability)
10. **Strategy Pattern** - Payment method flexibility (Modifiability)
11. **API Documentation** - Self-service integration (Integrability)
12. **Asynchronous Processing** - Webhook handling (Integrability)
13. **Security Testing** - Injection prevention validation (Testability)
14. **User Feedback** - Upload progress indication (Usability)

#### RMA & Observability (4 tactics):
15. **Status Transition Validation** - Enforce legal RMA workflow states (Reliability)
16. **Audit Trail on Changes** - Record who/when/what for disposition/state (Reliability)
17. **DB-backed Metrics + Smart Seeding** - Persistent counts with first-run-only seed (Observability)
18. **Middleware Timing + Histograms** - Request duration and percentile tracking (Observability)

---

## Testing Coverage

All scenarios are validated through comprehensive testing:

### Flash Sales Tests
```bash
pytest tests/flash_sales/ -v
```

**Test Files:**
- `test_rate_limiter.py` - Rate limiting behavior
- `test_circuit_breaker.py` - State transitions
- `test_retry.py` - Retry logic
- `test_flash_sale_manager.py` - Business logic
- `test_cache.py` - Caching behavior (if implemented)

### Partner Integration Tests
```bash
pytest tests/partners/ -v
```

**Test Files:**
- `test_partner_ingest.py` - Integration tests
- `test_auth_middleware.py` - Authentication
- `test_input_validation.py` - Security validation
- `test_partner_adapters.py` - Feed parsing

### Full Test Suite
```bash
pytest -v --cov=src --cov-report=term-missing
```

---



