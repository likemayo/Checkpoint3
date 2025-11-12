from __future__ import annotations
from .product_repo import AProductRepo

from werkzeug.security import generate_password_hash, check_password_hash

import os
from pathlib import Path
from typing import Dict

from flask import Flask, redirect, render_template, request, session, url_for, flash
import sqlite3
import time
import uuid

from . import observability

from .dao import SalesRepo, ProductRepo, get_connection
from .payment import process as payment_process
from .main import init_db
from .adapters.registry import get_adapter
from .partners.partner_ingest_service import validate_products, upsert_products


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates")
    app.secret_key = os.environ.get("APP_SECRET_KEY", "dev-insecure-secret")

    from .flash_sales.routes import flash_bp
    app.register_blueprint(flash_bp)
    
    # Register partners blueprint (ingest, diagnostics, integrability)
    try:
        from .partners.routes import bp as partners_bp
        app.register_blueprint(partners_bp, url_prefix='/partners')
    except Exception as e:
        # If partners blueprint can't be imported, log the exception so missing
        # dependencies or syntax errors are visible in the startup logs, then
        # continue to allow the rest of the app to start for tests.
        app.logger.exception("Failed to import/register partners blueprint; admin routes unavailable")
    
    # Register RMA (Returns & Refunds) blueprint
    try:
        from .rma.routes import bp as rma_bp
        app.register_blueprint(rma_bp)
    except Exception as e:
        app.logger.exception("Failed to import/register RMA blueprint; returns/refunds unavailable")

    root = Path(__file__).resolve().parents[1]
    db_path = os.environ.get("APP_DB_PATH", str(root / "app.sqlite"))
    init_db(db_path)

    def get_conn():
        return get_connection(db_path)

    def get_repo(conn: sqlite3.Connection) -> SalesRepo:
        return SalesRepo(conn, AProductRepo(conn))

    # Start background ingest worker if partners blueprint is available
    try:
        from .partners.ingest_queue import start_worker
        root = Path(__file__).resolve().parents[1]
        db_path = os.environ.get("APP_DB_PATH", str(root / "app.sqlite"))
        start_worker(db_path)
    except Exception:
        # best-effort: don't fail app startup if worker can't be started
        pass

    @app.route("/")
    def index():
        return redirect(url_for("login"))

    @app.route("/health")
    def health():
        """Basic health check endpoint for container orchestration."""
        return {"status": "ok", "service": "checkpoint3-web"}, 200

    @app.route("/ready")
    def ready():
        """Readiness check - verifies database connectivity."""
        try:
            conn = get_conn()
            conn.execute("SELECT 1").fetchone()
            conn.close()
            return {"status": "ready", "database": "connected"}, 200
        except Exception as e:
            return {"status": "not ready", "database": "disconnected", "error": str(e)}, 503

    # Configure structured logging for the app
    try:
        observability.configure_logging()
    except Exception:
        pass

    @app.before_request
    def _start_timer():
        request._start_time = time.time()
        request.request_id = request.headers.get('X-Request-Id') or str(uuid.uuid4())

    @app.after_request
    def _record_metrics(response):
        try:
            path = request.path
            elapsed = time.time() - getattr(request, '_start_time', time.time())
            observability.HTTP_REQUESTS.labels(request.method, path, str(response.status_code)).inc()
            observability.HTTP_LATENCY.labels(path).observe(elapsed)
        except Exception:
            pass
        return response

    @app.get('/metrics')
    def metrics():
        # Require session-based admin access to view process metrics
        try:
            if not session.get('is_admin'):
                return ("Missing or invalid admin key", 401)
            return observability.metrics_endpoint()
        except Exception:
            return ("metrics unavailable", 503)

    @app.get("/admin")
    def admin_home():
        """General Admin Homepage linking RMA and Partner admin tools."""
        # This landing page is visible without auth; individual sections enforce admin where needed
        return render_template("admin_home.html")

    @app.route("/products")
    def products():
        q = request.args.get("q", "").strip()
        conn = get_conn()
        try:
            try:
                repo = AProductRepo(conn)
                if q:
                    rows = repo.search_products(q)
                else:
                    rows = repo.get_all_products()
            except Exception:
                rows = []
                flash(
                    "Product table not available. Partner A needs to add user/product schema and seed.",
                    "error",
                )
            return render_template("products.html", products=rows, q=q)
        finally:
            conn.close()

    @app.post("/cart/add")
    def cart_add():
        pid = int(request.form.get("product_id", 0))
        qty = int(request.form.get("qty", 1))
        
        if qty <= 0:
            flash("Quantity must be > 0", "error")
            return redirect(url_for("products"))
        
        # Check if product exists and is active
        conn = get_conn()
        try:
            repo = AProductRepo(conn)
            product = repo.get_product(pid)
            
            if not product:
                flash(f"Product ID {pid} not found", "error")
                return redirect(url_for("products"))
            
            # Check if sufficient stock
            if not repo.check_stock(pid, qty):
                flash(f"Only {product['stock']} in stock for {product['name']}", "error")
                return redirect(url_for("products"))
            
            # Add to cart if everything is valid
            cart = session.get("cart", {})
            cart[str(pid)] = cart.get(str(pid), 0) + qty
            session["cart"] = cart
            flash(f"Added {qty} x {product['name']} to cart", "info")
            return redirect(url_for("cart_view"))
            
        except ValueError:
            flash("Invalid product ID", "error")
            return redirect(url_for("products"))
        finally:
            conn.close()

    @app.get("/cart")
    def cart_view():
        cart: Dict[str, int] = session.get("cart", {})
        conn = get_conn()
        items = []
        total = 0
        try:
            repo = AProductRepo(conn)  # Use your repo instead of raw SQL
            for pid_str, qty in cart.items():
                pid = int(pid_str)
                prod = repo.get_product(pid)  # This returns flash price if active!
                
                if not prod:
                    continue
                
                unit = int(prod["price_cents"])
                items.append({
                    "id": pid,
                    "name": prod["name"],
                    "qty": qty,
                    "unit": unit,
                    "line": unit * qty,
                    "is_flash_sale": prod.get("is_flash_sale", False),
                    "original_price": prod.get("original_price", unit)
                })
                total += unit * qty
        finally:
            conn.close()
        return render_template("cart.html", items=items, total=total)

    @app.post("/cart/clear")
    def cart_clear():
        session.pop("cart", None)
        flash("Cart cleared", "info")
        return redirect(url_for("products"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            username = request.form["username"]
            password = request.form["password"]
            
            conn = get_conn()
            try:
                user = conn.execute(
                    "SELECT id, username, password, name FROM user WHERE username = ?", 
                    (username,)
                ).fetchone()
                
                if user:
                    try:
                        ok = check_password_hash(user["password"], password)
                    except ValueError as e:
                        # Handle unsupported hash types (e.g., scrypt) gracefully
                        flash("Your account uses an unsupported password hash. Please reset your password or contact support.", "error")
                        ok = False
                    if ok:
                        session["user_id"] = user["id"]
                        session["username"] = user["username"]
                        
                        # Check if this is an admin user (name starts with "Admin: ")
                        if user["name"] and user["name"].startswith("Admin: "):
                            session["is_admin"] = True
                            flash("Admin login successful!", "success")
                            return redirect(url_for("admin_home"))
                        
                        flash("Login successful!", "success")
                        return redirect(url_for("dashboard"))
                
                flash("Invalid username or password", "error")
            finally:
                conn.close()
        
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        session.clear()
        flash("You have been logged out", "info")
        return redirect(url_for("login"))

    @app.route("/dashboard")
    def dashboard():
        """User dashboard showing order history and stats."""
        if "user_id" not in session:
            flash("Please login to access your dashboard", "error")
            return redirect(url_for("login"))
        
        user_id = session["user_id"]
        username = session.get("username", "User")
        
        conn = get_conn()
        try:
            # Get all user orders with items
            orders = conn.execute("""
                SELECT s.id, s.sale_time as created_at, s.status, 
                       s.total_cents / 100.0 as total,
                       GROUP_CONCAT(p.name || ' (' || si.quantity || 'x)', ', ') as items_summary
                FROM sale s
                LEFT JOIN sale_item si ON s.id = si.sale_id
                LEFT JOIN product p ON si.product_id = p.id
                WHERE s.user_id = ?
                GROUP BY s.id
                ORDER BY s.sale_time DESC
            """, (user_id,)).fetchall()
            
            # Get items for each order
            orders_with_items = []
            for order in orders:
                items_rows = conn.execute("""
                    SELECT si.*, p.name as product_name
                    FROM sale_item si
                    JOIN product p ON si.product_id = p.id
                    WHERE si.sale_id = ?
                """, (order["id"],)).fetchall()
                
                # Convert Row objects to dicts for template
                items_list = [dict(item) for item in items_rows]
                
                # Check if this is a replacement order (created by an RMA)
                is_replacement = conn.execute("""
                    SELECT COUNT(*) as count
                    FROM rma_activity_log
                    WHERE notes LIKE ?
                """, (f"%Replacement order created: #{order['id']}%",)).fetchone()
                
                # Check if this order already has an RMA request
                has_rma = conn.execute("""
                    SELECT COUNT(*) as count
                    FROM rma_requests
                    WHERE sale_id = ?
                """, (order["id"],)).fetchone()

                # Compute display status based on RMA disposition
                # Check for active (in-progress) RMAs first
                active_rma = conn.execute("""
                    SELECT disposition, status
                    FROM rma_requests
                    WHERE sale_id = ? AND status NOT IN ('COMPLETED','REJECTED','CANCELLED')
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (order["id"],)).fetchone()
                
                # Check for completed RMAs to show final outcome
                completed_rma = conn.execute("""
                    SELECT disposition, status
                    FROM rma_requests
                    WHERE sale_id = ? AND status = 'COMPLETED'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (order["id"],)).fetchone()
                
                # Check for rejected RMAs
                rejected_rma = conn.execute("""
                    SELECT disposition, status
                    FROM rma_requests
                    WHERE sale_id = ? AND status = 'REJECTED'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (order["id"],)).fetchone()
                
                display_status = order["status"]
                
                # Active RMA takes precedence (show in-progress status)
                if active_rma:
                    if active_rma["disposition"] == "REPAIR":
                        display_status = "REPAIRING"
                    elif active_rma["disposition"] == "REPLACEMENT":
                        display_status = "REPLACING"
                    elif active_rma["disposition"] == "REFUND":
                        display_status = "REFUNDING"
                    elif active_rma["disposition"] == "STORE_CREDIT":
                        display_status = "STORE_CREDIT"
                    elif active_rma["disposition"] == "REJECT":
                        display_status = "RETURN_REJECTED"
                # Rejected RMA shows rejection
                elif rejected_rma:
                    display_status = "RETURN_REJECTED"
                # Completed RMA shows final outcome
                elif completed_rma and order["status"] == "COMPLETED":
                    if completed_rma["disposition"] == "REPAIR":
                        display_status = "REPAIRED"
                    elif completed_rma["disposition"] == "REPLACEMENT":
                        display_status = "REPLACED"
                    elif completed_rma["disposition"] == "STORE_CREDIT":
                        display_status = "CREDITED"
                    # REFUND changes order status to REFUNDED, so no override needed
                
                orders_with_items.append({
                    "id": order["id"],
                    "created_at": order["created_at"],
                    "status": order["status"],
                    "display_status": display_status,
                    "total": order["total"],
                    "items": items_list,
                    "is_replacement": is_replacement["count"] > 0,
                    "has_rma": has_rma["count"] > 0
                })
            
            # Calculate stats
            stats = {
                "total_orders": len(orders),
                "total_spent": sum(o["total"] for o in orders_with_items),
                "active_returns": 0,
                "store_credit": 0.0
            }
            
            # Count active returns and calculate store credit
            try:
                active_returns = conn.execute("""
                    SELECT COUNT(*) as count 
                    FROM rma_requests 
                    WHERE user_id = ? AND status NOT IN ('COMPLETED', 'REJECTED', 'CANCELLED')
                """, (user_id,)).fetchone()
                stats["active_returns"] = active_returns["count"] if active_returns else 0
                
                # Calculate total store credit from completed STORE_CREDIT RMAs
                store_credit_result = conn.execute("""
                    SELECT COALESCE(SUM(refund_amount_cents), 0) as total_credit
                    FROM rma_requests 
                    WHERE user_id = ? AND status = 'COMPLETED' AND disposition = 'STORE_CREDIT'
                """, (user_id,)).fetchone()
                stats["store_credit"] = (store_credit_result["total_credit"] or 0) / 100.0
            except:
                pass  # RMA table might not exist yet
            
        finally:
            conn.close()
        
        return render_template("dashboard.html", 
                             username=username, 
                             orders=orders_with_items,
                             stats=stats)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            name = request.form["name"]
            username = request.form["username"]
            password = request.form["password"]
            
            conn = get_conn()
            try:
                # Check if username exists
                existing = conn.execute("SELECT id FROM user WHERE username = ?", (username,)).fetchone()
                if existing:
                    flash("Username already exists", "error")
                else:
                    # Create user with PBKDF2 for compatibility across environments
                    hashed_password = generate_password_hash(password, method="pbkdf2:sha256")
                    conn.execute(
                        "INSERT INTO user (name, username, password) VALUES (?, ?, ?)",
                        (name, username, hashed_password)
                    )
                    conn.commit()
                    flash("Registration successful! Please login.", "success")
                    return redirect(url_for("login"))
            finally:
                conn.close()
        
        # Return register template (you'd need to create this)
        return render_template("register.html")

    @app.route("/register-admin", methods=["POST"])
    def register_admin():
        """Handle admin registration - validates super admin key then creates new admin account."""
        super_admin_key = request.form.get("super_admin_key", "").strip()
        admin_username = request.form.get("admin_username", "").strip()
        admin_password = request.form.get("admin_password", "").strip()
        
        expected_super_key = os.environ.get("ADMIN_API_KEY", "admin-demo-key")
        
        # First verify super admin key
        if super_admin_key != expected_super_key:
            flash("Invalid super admin key. You need the super admin key to create admin accounts.", "error")
            return redirect(url_for("register"))
        
        # Validate inputs
        if not admin_username or not admin_password:
            flash("Username and password are required for admin account.", "error")
            return redirect(url_for("register"))
        
        # Create admin account in database
        conn = get_conn()
        try:
            # Check if admin username already exists
            existing = conn.execute("SELECT id FROM user WHERE username = ?", (admin_username,)).fetchone()
            if existing:
                flash("Admin username already exists. Choose a different username.", "error")
                return redirect(url_for("register"))
            
            # Create admin user with a flag to identify them as admin
            hashed_password = generate_password_hash(admin_password, method="pbkdf2:sha256")
            conn.execute(
                "INSERT INTO user (name, username, password) VALUES (?, ?, ?)",
                (f"Admin: {admin_username}", admin_username, hashed_password)
            )
            conn.commit()
            
            # Don't auto-login, redirect to login page
            flash(f"Admin account '{admin_username}' created successfully! Please login with your new credentials.", "success")
            return redirect(url_for("login"))
            
        except Exception as e:
            flash(f"Error creating admin account: {str(e)}", "error")
            return redirect(url_for("register"))
        finally:
            conn.close()

    @app.route("/uploads/rma/<filename>")
    def serve_rma_upload(filename):
        """Serve uploaded RMA photos."""
        from flask import send_from_directory
        import os
        upload_dir = os.path.join('/app', 'data', 'uploads', 'rma')
        return send_from_directory(upload_dir, filename)

    # Add login requirement to protected routes
    def login_required(f):
        from functools import wraps
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                flash("Please login to access this page", "error")
                return redirect(url_for("login"))
            return f(*args, **kwargs)
        return decorated_function
    @app.post("/checkout")
    def checkout():
        pay_method = request.form.get("payment_method", "CARD")
        user_id = session["user_id"]
        cart: Dict[str, int] = session.get("cart", {})
        cart_list = [(int(pid), qty) for pid, qty in cart.items()]

        conn = get_conn()
        repo = get_repo(conn)
        try:
            # Use the resilient payment path (retry + circuit breaker)
            # Import lazily to avoid circular import issues
            try:
                from .flash_sales.payment_resilience import process_payment_resilient
                payment_cb = process_payment_resilient
            except Exception:
                # Fallback to the simple payment processor if resilience module unavailable
                payment_cb = payment_process

            sale_id = repo.checkout_transaction(
                user_id=user_id,
                cart=cart_list,
                pay_method=pay_method,
                payment_cb=payment_cb,
            )
        except Exception as e:
            flash(str(e), "error")
            return redirect(url_for("cart_view"))
        finally:
            conn.close()

        session.pop("cart", None)
        flash(f"Checkout success. Sale #{sale_id}", "success")
        return redirect(url_for("receipt", sale_id=sale_id))
    
    @app.post('/partner/ingest')
    def partner_ingest_main():
        api_key = request.headers.get('X-API-Key') or request.form.get('api_key')
        if not api_key:
            return ("Missing API key", 401)

        # validate key against DB
        conn_check = get_conn()
        try:
            cur = conn_check.execute('SELECT partner_id FROM partner_api_keys WHERE api_key = ?', (api_key,))
            row = cur.fetchone()
            if not row:
                return ("Invalid API key", 401)
        finally:
            conn_check.close()

        content_type = request.content_type or ''
        payload = request.get_data()
        adapter = get_adapter(content_type)
        if not adapter:
            if content_type.startswith('application/json'):
                adapter = get_adapter('application/json')
            elif content_type.startswith('text/csv') or content_type == 'text/plain':
                adapter = get_adapter('text/csv')
        if not adapter:
            return ('No adapter for content type', 415)

        try:
            products = adapter(payload, content_type)
        except Exception as e:
            return (f'Adapter parse error: {e}', 400)

        valid_items, validation_errors = validate_products(products)
        ingested = 0
        errors = validation_errors[:]
        if valid_items:
            conn = get_conn()
            try:
                upserted, upsert_errors = upsert_products(conn, valid_items)
                ingested = upserted
                errors.extend(upsert_errors)
            finally:
                conn.close()

        return ({'ingested': ingested, 'errors': errors}, 200)
    @app.post("/cart/remove")
    def cart_remove():
        pid = request.form.get("product_id")
        cart = session.get("cart", {})
        
        if pid in cart:
            del cart[pid]
            session["cart"] = cart
            flash("Item removed from cart", "info")
        
        return redirect(url_for("cart_view"))


    

    @app.get("/receipt/<int:sale_id>")
    def receipt(sale_id: int):
        conn = get_conn()
        try:
            sale = conn.execute(
                "SELECT id, user_id, sale_time, total_cents, status FROM sale WHERE id = ?",
                (sale_id,),
            ).fetchone()
            # Compute display status based on RMA disposition
            display_status = sale["status"] if sale else ""
            try:
                # Check for active (in-progress) RMAs first
                active_rma = conn.execute(
                    """
                    SELECT disposition, status
                    FROM rma_requests
                    WHERE sale_id = ? AND status NOT IN ('COMPLETED','REJECTED','CANCELLED')
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (sale_id,),
                ).fetchone()
                
                # Check for completed RMAs to show final outcome
                completed_rma = conn.execute(
                    """
                    SELECT disposition, status
                    FROM rma_requests
                    WHERE sale_id = ? AND status = 'COMPLETED'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (sale_id,),
                ).fetchone()
                
                # Check for rejected RMAs
                rejected_rma = conn.execute(
                    """
                    SELECT disposition, status
                    FROM rma_requests
                    WHERE sale_id = ? AND status = 'REJECTED'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (sale_id,),
                ).fetchone()
                
                # Active RMA takes precedence (show in-progress status)
                if active_rma:
                    if active_rma["disposition"] == "REPAIR":
                        display_status = "REPAIRING"
                    elif active_rma["disposition"] == "REPLACEMENT":
                        display_status = "REPLACING"
                    elif active_rma["disposition"] == "REFUND":
                        display_status = "REFUNDING"
                    elif active_rma["disposition"] == "STORE_CREDIT":
                        display_status = "STORE_CREDIT"
                    elif active_rma["disposition"] == "REJECT":
                        display_status = "RETURN_REJECTED"
                # Rejected RMA shows rejection
                elif rejected_rma:
                    display_status = "RETURN_REJECTED"
                # Completed RMA shows final outcome
                elif completed_rma and sale["status"] == "COMPLETED":
                    if completed_rma["disposition"] == "REPAIR":
                        display_status = "REPAIRED"
                    elif completed_rma["disposition"] == "REPLACEMENT":
                        display_status = "REPLACED"
                    elif completed_rma["disposition"] == "STORE_CREDIT":
                        display_status = "CREDITED"
            except Exception:
                # rma tables may not exist in some setups
                pass
            items = conn.execute(
                "SELECT si.product_id, p.name as product_name, si.quantity, si.price_cents "
                "FROM sale_item si JOIN product p ON si.product_id = p.id "
                "WHERE si.sale_id = ?",
                (sale_id,),
            ).fetchall()
            payment = conn.execute(
                "SELECT method, amount_cents, status, ref FROM payment WHERE sale_id = ?",
                (sale_id,),
            ).fetchone()
        finally:
            conn.close()
        return render_template("receipt.html", sale=sale, items=items, payment=payment, display_status=display_status)


    @app.get("/admin/flash-sale")
    def admin_flash_sale():
        """Admin page to manage flash sales"""
        conn = get_conn()
        try:
            cursor = conn.execute("""
                SELECT id, name, price_cents, flash_sale_active, flash_sale_price_cents
                FROM product 
                WHERE active = 1
                ORDER BY name
            """)
            products = cursor.fetchall()
            return render_template("admin_flash_sale.html", products=products)
        finally:
            conn.close()

    @app.post("/admin/flash-sale/set")
    def admin_flash_sale_set():
        """Set a product as flash sale"""
        product_id = int(request.form.get("product_id"))
        flash_price = float(request.form.get("flash_price"))
        flash_price_cents = int(flash_price * 100)
        
        conn = get_conn()
        try:
            conn.execute("""
                UPDATE product 
                SET flash_sale_active = 1, flash_sale_price_cents = ?
                WHERE id = ?
            """, (flash_price_cents, product_id))
            conn.commit()
            flash("Flash sale activated!", "success")
        finally:
            conn.close()
        
        return redirect(url_for("admin_flash_sale"))

    @app.post("/admin/flash-sale/remove")
    def admin_flash_sale_remove():
        """Remove flash sale from product"""
        product_id = int(request.form.get("product_id"))
        
        conn = get_conn()
        try:
            conn.execute("""
                UPDATE product 
                SET flash_sale_active = 0, flash_sale_price_cents = NULL
                WHERE id = ?
            """, (product_id,))
            conn.commit()
            flash("Flash sale removed", "info")
        finally:
            conn.close()
        
        return redirect(url_for("admin_flash_sale"))

    return app
    

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, host="127.0.0.1", port=int(os.environ.get("PORT", "5000")))
