from flask import Flask, render_template, request, redirect, send_file
import uuid
import ipaddress
import sqlite3
import time

# Custom utility imports
from utils.qr_generator import generate_qr_code
from utils.token_manager import generate_session_token, verify_session_token
from utils.validator import is_ip_allowed
from utils.report_generator import generate_report

app = Flask(__name__)

# -------------------------
# Step 1: Configuration & Database Initialization
# -------------------------
app.config["SECRET_KEY"] = "lpaf_super_secret_key"

def init_db():
    """Ensures the local SQLite database is ready for attendance records."""
    conn = sqlite3.connect("database/attendance.db")
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT,
        name TEXT,
        roll TEXT,
        ip TEXT
    )
    """)
    conn.commit()
    conn.close()

# Initialize DB and create a global dictionary for in-memory session tracking
init_db()
active_sessions = {}

# -------------------------
# Step 2: Homepage Route
# -------------------------
@app.route("/")
def home():
    return render_template("index.html")

# -------------------------
# Step 3: Professor Dashboard (Session Creation)
# -------------------------
@app.route("/professor", methods=["GET", "POST"])
def professor():
    if request.method == "POST":
        # Capture all form data
        email = request.form["email"]
        subject = request.form["subject"]
        section = request.form["section"]
        department = request.form["department"]

        # Generate a unique 8-character ID for this specific lecture
        session_id = str(uuid.uuid4())[:8]

        # Network Logic: Capture professor's IP to define the allowed subnet
        professor_ip = request.remote_addr
        network = ipaddress.ip_network(professor_ip + "/24", strict=False)
        allowed_network = str(network)

        # Generate the first rotating token
        token = generate_session_token(session_id)
        
        # Deployment-friendly relative URL
        student_link = f"/student?token={token}"
        
        # Generate the QR Code image (Base64)
        qr_image = generate_qr_code(student_link)

        # Store the session metadata in memory
        session_data = {
            "email": email,
            "subject": subject,
            "section": section,
            "department": department,
            "professor_ip": professor_ip,
            "allowed_network": allowed_network,
            "token": token,
            "start_time": time.time()  # To track the 5-minute limit
        }
        active_sessions[session_id] = session_data

        return render_template(
            "professor.html",
            qr_image=qr_image,
            session_id=session_id,
            token=token,
            start_time=session_data["start_time"]
        )

    return render_template("professor.html")

# -------------------------
# Step 4: API Endpoints (QR Refresh, Stats, & Reports)
# -------------------------
@app.route("/refresh_qr/<session_id>")
def refresh_qr(session_id):
    if session_id not in active_sessions:
        return {"error": "Invalid session"}, 404

    session = active_sessions[session_id]

    # Enforcement of the 5-minute (300s) session window
    if time.time() - session["start_time"] > 300:
        return {"error": "Session expired"}, 403

    # Generate a new token for rotation
    token = generate_session_token(session_id)
    session["token"] = token

    student_link = f"/student?token={token}"
    qr_image = generate_qr_code(student_link)

    return {
        "qr": qr_image,
        "token": token
    }

@app.route("/session_stats/<session_id>")
def session_stats(session_id):
    conn = sqlite3.connect("database/attendance.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, roll FROM attendance WHERE session_id=?", (session_id,))
    rows = cursor.fetchall()
    conn.close()

    return {
        "count": len(rows),
        "recent": rows[-5:] # Last 5 students for live feedback
    }

@app.route("/download_report/<session_id>")
def download_report(session_id):
    file_path = generate_report(session_id)
    if not file_path:
        return "No records available for download.", 404
    
    return send_file(file_path, as_attachment=True)

# -------------------------
# Step 5: Student Verification & Submission
# -------------------------
@app.route("/student")
def student():
    token = request.args.get("token")
    if not token:
        return "Invalid QR Code - Missing Token", 400

    # Decrypt and verify the JWT
    decoded = verify_session_token(token)
    if not decoded:
        return "The QR link has expired or is invalid.", 401

    session_id = decoded["session_id"]
    return render_template("student.html", token=token, session_id=session_id)

@app.route("/submit_attendance", methods=["POST"])
def submit_attendance():
    name = request.form.get("name")
    roll = request.form.get("roll")
    token = request.form.get("token")

    # Security Check: Ensure fields aren't empty
    if not name or not roll:
        return "Name and Roll number are required.", 400

    # Security Check 1: Verify the JWT Token
    decoded = verify_session_token(token)
    if not decoded:
        return "Session has expired.", 401

    session_id = decoded["session_id"]
    student_ip = request.remote_addr

    # Security Check 2: Verify Session exists in memory
    session = active_sessions.get(session_id)
    if not session:
        return "This attendance session is no longer active.", 400

    # Security Check 3: Layered Presence (Network Subnet Validation)
    allowed_network = session["allowed_network"]
    if not is_ip_allowed(student_ip, allowed_network):
        return "You must be connected to the campus network to mark attendance.", 403

    # Step 6: Database Logging & Duplicate Prevention
    conn = sqlite3.connect("database/attendance.db")
    cursor = conn.cursor()

    # Check if this roll number already marked attendance for this session
    cursor.execute(
        "SELECT id FROM attendance WHERE session_id=? AND roll=?",
        (session_id, roll)
    )

    if cursor.fetchone():
        conn.close()
        return "Attendance already recorded for this roll number.", 409

    # Final Insertion
    cursor.execute(
        "INSERT INTO attendance (session_id, name, roll, ip) VALUES (?, ?, ?, ?)",
        (session_id, name, roll, student_ip)
    )

    conn.commit()
    conn.close()

    return render_template("success.html")

# -------------------------
# Step 7: Run Server
# -------------------------
if __name__ == "__main__":
    app.run(debug=True)