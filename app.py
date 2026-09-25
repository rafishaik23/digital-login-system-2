from flask import Flask, render_template, request, redirect, session, flash
import sqlite3
from datetime import datetime
import uuid
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "my_secret_key")


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect("database.db", timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout = 10000")
    return conn


def create_tables():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            checkin_id TEXT UNIQUE,
            name TEXT NOT NULL,
            age INTEGER NOT NULL,
            gender TEXT NOT NULL,
            contact TEXT,
            address TEXT NOT NULL,
            qualification TEXT NOT NULL,
            purpose TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS login_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            login_time TEXT NOT NULL,
            logout_time TEXT,
            purpose TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    # Add checkin_id to older databases
    user_columns = {
        column["name"]
        for column in conn.execute("PRAGMA table_info(users)").fetchall()
    }

    if "checkin_id" not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN checkin_id TEXT")

    # Generate IDs for existing users
    users_without_id = conn.execute("""
        SELECT id FROM users
        WHERE checkin_id IS NULL OR checkin_id = ''
    """).fetchall()

    for user in users_without_id:
        checkin_id = "USR-" + uuid.uuid4().hex[:8].upper()

        while conn.execute(
            "SELECT 1 FROM users WHERE checkin_id = ?",
            (checkin_id,)
        ).fetchone():
            checkin_id = "USR-" + uuid.uuid4().hex[:8].upper()

        conn.execute(
            "UPDATE users SET checkin_id = ? WHERE id = ?",
            (checkin_id, user["id"])
        )

    # Add purpose to older login_logs tables
    log_columns = {
        column["name"]
        for column in conn.execute("PRAGMA table_info(login_logs)").fetchall()
    }

    if "purpose" not in log_columns:
        conn.execute("ALTER TABLE login_logs ADD COLUMN purpose TEXT")

    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_users_checkin_id
        ON users(checkin_id)
    """)

    conn.commit()
    conn.close()


# ---------------- HOME ----------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- ADMIN ----------------

@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username == "admin" and password == "admin123":
            session["admin_logged_in"] = True
            return redirect("/admin-dashboard")

        flash("Invalid Admin Username or Password")

    return render_template("admin-login.html")


@app.route("/admin-dashboard")
def admin_dashboard():
    if not session.get("admin_logged_in"):
        return redirect("/admin-login")

    return render_template("admin-dashboard.html")
@app.route("/admin/users")
def admin_users():

    if not session.get("admin_logged_in"):
        return redirect("/admin-login")

    conn = get_db()

    users = conn.execute("""
        SELECT * FROM users
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return render_template("admin-users.html", users=users)






@app.route("/admin-logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    flash("You have been logged out.")
    return redirect("/admin-login")




# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"]
        age = request.form["age"]
        gender = request.form["gender"]
        contact = request.form["contact"]
        address = request.form["address"]
        qualification = request.form["qualification"]
        purpose = request.form["purpose"]
        email = request.form["email"].strip().lower()

        conn = None
        try:
            conn = get_db()

            existing_user = conn.execute(
                "SELECT 1 FROM users WHERE lower(email) = ?",
                (email,)
            ).fetchone()

            if existing_user:
                return render_template(
                    "register.html",
                    error="An account with this email already exists."
                )

            checkin_id = "USR-" + uuid.uuid4().hex[:8].upper()

            conn.execute("""
                INSERT INTO users
                (checkin_id, name, age, gender, contact, address,
                 qualification, purpose, email)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                checkin_id, name, age, gender, contact, address,
                qualification, purpose, email
            ))

            conn.commit()
            conn.close()

            flash(f"Registration successful. Your Check-in ID is {checkin_id}")
            return redirect("/login")

        except sqlite3.IntegrityError:
            return render_template(
                "register.html",
                error="An account with this email already exists."
            )
        finally:
            if conn is not None:
                conn.close()

    return render_template("register.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        checkin_id = request.form["checkin_id"].strip().upper()
        purpose = request.form["purpose"].strip()

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE checkin_id = ?",
            (checkin_id,)
        ).fetchone()

        if user:
            session["user_id"] = user["id"]
            session["user_name"] = user["name"]
            session["checkin_id"] = user["checkin_id"]

            login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            conn.execute("""
                INSERT INTO login_logs
                (user_id, login_time, purpose)
                VALUES (?, ?, ?)
            """, (user["id"], login_time, purpose))

            conn.commit()
            conn.close()

            return redirect("/dashboard")

        conn.close()
        flash("Invalid Check-in ID.")

    return render_template("login.html")


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    user = conn.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()

    conn.close()

    return render_template("dashboard.html", user=user)


# ---------------- LOGBOOK ----------------

@app.route("/logbook")
def logbook():
    if "user_id" not in session:
        return redirect("/login")

    conn = get_db()

    logs = conn.execute("""
        SELECT * FROM login_logs
        WHERE user_id = ?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template("logbook.html", logs=logs)


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    if "user_id" in session:
        conn = get_db()

        log = conn.execute("""
            SELECT * FROM login_logs
            WHERE user_id = ? AND logout_time IS NULL
            ORDER BY id DESC
            LIMIT 1
        """, (session["user_id"],)).fetchone()

        if log:
            logout_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            conn.execute("""
                UPDATE login_logs
                SET logout_time = ?
                WHERE id = ?
            """, (logout_time, log["id"]))

            conn.commit()

        conn.close()

    session.clear()
    flash("You have been logged out.")

    return redirect("/login")


# ---------------- RUN APPLICATION ----------------
# The built-in Flask server is for local development only.
# Production deployments should run the app through a WSGI server such as Gunicorn.

if __name__ == "__main__":
    create_tables()
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000)),
        debug=False,
        use_reloader=False,
    )