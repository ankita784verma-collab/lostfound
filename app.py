import os
import csv
import io
from datetime import datetime

from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, jsonify, g, Response, abort
)
from flask_login import (
    LoginManager, login_user, logout_user, login_required,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

import db
from config import Config
from models import User

app = Flask(__name__)
app.config.from_object(Config)

os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Please log in to continue."
login_manager.login_message_category = "info"


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)


# ----------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------
def allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]
    )


CATEGORIES = [
    "Electronics", "Documents & Cards", "Bags & Luggage", "Jewelry & Accessories",
    "Keys", "Clothing", "Pets", "Books & Stationery", "Other"
]


@app.context_processor
def inject_globals():
    return {"categories": CATEGORIES, "current_year": datetime.now().year}


# ----------------------------------------------------------------
# Public pages
# ----------------------------------------------------------------
@app.route("/")
def index():
    recent_lost = db.query(
        "SELECT * FROM items WHERE item_type='lost' ORDER BY created_at DESC LIMIT 4"
    )
    recent_found = db.query(
        "SELECT * FROM items WHERE item_type='found' ORDER BY created_at DESC LIMIT 4"
    )
    stats = db.query(
        """
        SELECT
            (SELECT COUNT(*) FROM items WHERE item_type='lost') AS lost_count,
            (SELECT COUNT(*) FROM items WHERE item_type='found') AS found_count,
            (SELECT COUNT(*) FROM items WHERE status='resolved') AS resolved_count,
            (SELECT COUNT(*) FROM users) AS user_count
        """,
        fetchone=True,
    )
    return render_template(
        "index.html", recent_lost=recent_lost, recent_found=recent_found, stats=stats
    )


@app.route("/browse")
def browse():
    return render_template("browse.html")


@app.route("/api/items")
def api_items():
    item_type = request.args.get("type", "").strip()
    category = request.args.get("category", "").strip()
    q = request.args.get("q", "").strip()
    location = request.args.get("location", "").strip()
    status = request.args.get("status", "open").strip()

    sql = "SELECT items.*, users.full_name AS reporter_name FROM items JOIN users ON users.id = items.user_id WHERE 1=1"
    params = []

    if item_type in ("lost", "found"):
        sql += " AND item_type = %s"
        params.append(item_type)

    if category:
        sql += " AND category = %s"
        params.append(category)

    if location:
        sql += " AND location LIKE %s"
        params.append(f"%{location}%")

    if status in ("open", "matched", "resolved"):
        sql += " AND status = %s"
        params.append(status)

    if q:
        sql += " AND (title LIKE %s OR description LIKE %s)"
        params.append(f"%{q}%")
        params.append(f"%{q}%")

    sql += " ORDER BY created_at DESC LIMIT 100"

    rows = db.query(sql, params)
    for r in rows:
        if r.get("event_date"):
            r["event_date"] = r["event_date"].strftime("%Y-%m-%d")
        if r.get("created_at"):
            r["created_at"] = r["created_at"].strftime("%Y-%m-%d %H:%M")
    return jsonify(rows)


@app.route("/item/<int:item_id>")
def item_detail(item_id):
    item = db.query(
        "SELECT items.*, users.full_name AS reporter_name, users.email AS reporter_email "
        "FROM items JOIN users ON users.id = items.user_id WHERE items.id = %s",
        (item_id,), fetchone=True,
    )
    if not item:
        abort(404)
    claims = db.query(
        "SELECT claims.*, users.full_name AS claimant_name FROM claims "
        "JOIN users ON users.id = claims.claimant_id WHERE item_id = %s ORDER BY created_at DESC",
        (item_id,),
    )
    return render_template("item_detail.html", item=item, claims=claims)


@app.route("/item/<int:item_id>/claim", methods=["POST"])
@login_required
def submit_claim(item_id):
    item = db.query("SELECT * FROM items WHERE id = %s", (item_id,), fetchone=True)
    if not item:
        abort(404)
    message = request.form.get("message", "").strip()
    if not message:
        flash("Please enter a message describing why you believe this is yours.", "error")
        return redirect(url_for("item_detail", item_id=item_id))

    db.query(
        "INSERT INTO claims (item_id, claimant_id, message) VALUES (%s, %s, %s)",
        (item_id, current_user.id, message), commit=True,
    )
    flash("Your claim has been submitted. The reporter will review it soon.", "success")
    return redirect(url_for("item_detail", item_id=item_id))


@app.route("/claim/<int:claim_id>/respond", methods=["POST"])
@login_required
def respond_claim(claim_id):
    action = request.form.get("action")
    claim = db.query(
        "SELECT claims.*, items.user_id AS item_owner_id, items.id AS item_id FROM claims "
        "JOIN items ON items.id = claims.item_id WHERE claims.id = %s",
        (claim_id,), fetchone=True,
    )
    if not claim:
        abort(404)
    if claim["item_owner_id"] != current_user.id:
        abort(403)

    if action not in ("accepted", "rejected"):
        flash("Invalid action.", "error")
        return redirect(url_for("item_detail", item_id=claim["item_id"]))

    db.query("UPDATE claims SET status = %s WHERE id = %s", (action, claim_id), commit=True)
    if action == "accepted":
        db.query("UPDATE items SET status = 'resolved' WHERE id = %s", (claim["item_id"],), commit=True)
        flash("Claim accepted. Item marked as resolved.", "success")
    else:
        flash("Claim rejected.", "info")
    return redirect(url_for("item_detail", item_id=claim["item_id"]))


# ----------------------------------------------------------------
# Report lost / found
# ----------------------------------------------------------------
@app.route("/report/<item_type>", methods=["GET", "POST"])
@login_required
def report_item(item_type):
    if item_type not in ("lost", "found"):
        abort(404)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        event_date = request.form.get("event_date", "").strip()
        contact_info = request.form.get("contact_info", "").strip()

        errors = []
        if not title:
            errors.append("Title is required.")
        if not category:
            errors.append("Please choose a category.")
        if not location:
            errors.append("Location is required.")
        if not event_date:
            errors.append("Date is required.")
        if not contact_info:
            errors.append("Contact info is required.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("report_item.html", item_type=item_type, form=request.form)

        image_path = None
        file = request.files.get("image")
        if file and file.filename:
            if allowed_file(file.filename):
                filename = secure_filename(f"{item_type}_{datetime.now().timestamp()}_{file.filename}")
                file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
                image_path = filename
            else:
                flash("Image type not allowed. Use png, jpg, jpeg, gif, or webp.", "error")
                return render_template("report_item.html", item_type=item_type, form=request.form)

        db.query(
            """INSERT INTO items
               (user_id, item_type, title, category, description, location, event_date, contact_info, image_path)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (current_user.id, item_type, title, category, description, location,
             event_date, contact_info, image_path),
            commit=True,
        )
        flash(f"Your {item_type} item report has been posted.", "success")
        return redirect(url_for("browse"))

    return render_template("report_item.html", item_type=item_type, form={})


# ----------------------------------------------------------------
# Auth
# ----------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")

        errors = []
        if not full_name:
            errors.append("Full name is required.")
        if not email:
            errors.append("Email is required.")
        if len(password) < 6:
            errors.append("Password must be at least 6 characters.")
        if password != confirm:
            errors.append("Passwords do not match.")
        if User.get_by_email(email):
            errors.append("An account with this email already exists.")

        if errors:
            for e in errors:
                flash(e, "error")
            return render_template("register.html", form=request.form)

        password_hash = generate_password_hash(password)
        db.query(
            "INSERT INTO users (full_name, email, phone, password_hash) VALUES (%s, %s, %s, %s)",
            (full_name, email, phone, password_hash), commit=True,
        )
        flash("Account created. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", form={})


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        row = db.query("SELECT * FROM users WHERE email = %s", (email,), fetchone=True)

        if row and check_password_hash(row["password_hash"], password):
            login_user(User(row))
            flash(f"Welcome back, {row['full_name']}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page or url_for("index"))

        flash("Invalid email or password.", "error")
        return render_template("login.html", form=request.form)

    return render_template("login.html", form={})


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


# ----------------------------------------------------------------
# Dashboard
# ----------------------------------------------------------------
@app.route("/dashboard")
@login_required
def dashboard():
    my_items = db.query(
        "SELECT * FROM items WHERE user_id = %s ORDER BY created_at DESC", (current_user.id,)
    )
    claims_on_my_items = db.query(
        """SELECT claims.*, items.title AS item_title, users.full_name AS claimant_name
           FROM claims
           JOIN items ON items.id = claims.item_id
           JOIN users ON users.id = claims.claimant_id
           WHERE items.user_id = %s ORDER BY claims.created_at DESC""",
        (current_user.id,),
    )
    my_claims = db.query(
        """SELECT claims.*, items.title AS item_title, items.id AS item_id
           FROM claims JOIN items ON items.id = claims.item_id
           WHERE claimant_id = %s ORDER BY claims.created_at DESC""",
        (current_user.id,),
    )
    return render_template(
        "dashboard.html", my_items=my_items,
        claims_on_my_items=claims_on_my_items, my_claims=my_claims
    )


# ----------------------------------------------------------------
# Analytics / Power BI integration
# ----------------------------------------------------------------
@app.route("/api/stats")
def api_stats():
    by_category = db.query(
        "SELECT category, item_type, COUNT(*) AS total FROM items GROUP BY category, item_type"
    )
    by_status = db.query("SELECT status, COUNT(*) AS total FROM items GROUP BY status")
    timeline = db.query(
        "SELECT DATE(created_at) AS day, item_type, COUNT(*) AS total FROM items "
        "GROUP BY DATE(created_at), item_type ORDER BY day"
    )
    for row in timeline:
        row["day"] = row["day"].strftime("%Y-%m-%d")
    return jsonify({
        "by_category": by_category,
        "by_status": by_status,
        "timeline": timeline,
    })


@app.route("/export/items.csv")
def export_items_csv():
    """CSV export of the analytics view - designed to be picked up by
    Power BI's 'Text/CSV' or 'Web' data source connector."""
    rows = db.query("SELECT * FROM vw_items_report")
    output = io.StringIO()
    if rows:
        writer = csv.DictWriter(output, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=lost_found_report.csv"},
    )


# ----------------------------------------------------------------
# Error handlers
# ----------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template("403.html"), 403


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
