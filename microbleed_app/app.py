from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import json
from datetime import datetime
from functools import wraps

# ─── Model inference (plug your model here) ───────────────────────────────────
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image

CLASS_NAMES = ["No Microbleed", "Microbleed - Mild", "Microbleed - Moderate", "Microbleed - Severe"]
CLASS_COLORS = ["#10b981", "#f59e0b", "#f97316", "#ef4444"]

def load_model(model_path="model/model.pt"):
    model = models.resnet18(weights=None)
    model.fc = torch.nn.Linear(512, 4)
    state_dict = torch.load(model_path, map_location="cpu", weights_only=False)
    model.load_state_dict(state_dict)
    model.eval()
    return model

MODEL = None
try:
    MODEL = load_model()
    print("✅ Model loaded successfully")
except Exception as e:
    print(f"⚠️  Model not loaded: {e}. Place model.pt in the model/ folder.")

TRANSFORM = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])

def predict(image_path):
    if MODEL is None:
        # Demo mode — return mock result
        import random
        idx = random.randint(0, 3)
        probs = [round(random.uniform(0.01, 0.1), 4) for _ in range(4)]
        probs[idx] = round(1 - sum(probs) + probs[idx], 4)
        return CLASS_NAMES[idx], probs, idx
    img = Image.open(image_path).convert("RGB")
    tensor = TRANSFORM(img).unsqueeze(0)
    with torch.no_grad():
        logits = MODEL(tensor)
        probs = torch.softmax(logits, dim=1)[0].tolist()
    idx = int(torch.argmax(torch.tensor(probs)).item())
    return CLASS_NAMES[idx], [round(p, 4) for p in probs], idx
# ─────────────────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.secret_key = "microbleed_secret_2024_change_in_production"

# ─── MySQL config ─────────────────────────────────────────────────────────────
app.config["MYSQL_HOST"] = "localhost"
app.config["MYSQL_USER"] = "root"
app.config["MYSQL_PASSWORD"] = "John88cena@"          # ← change to your MySQL password
app.config["MYSQL_DB"] = "microbleed_db"
app.config["MYSQL_CURSORCLASS"] = "DictCursor"

mysql = MySQL(app)

# ─── Upload config ────────────────────────────────────────────────────────────
UPLOAD_FOLDER = os.path.join("static", "uploads")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "bmp", "tiff", "dcm"}
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ─── Auth decorator ───────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "admin_id" not in session:
            flash("Please log in to access this page.", "warning")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    if "admin_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM admins WHERE username = %s", (username,))
        admin = cur.fetchone()
        cur.close()
        if admin and check_password_hash(admin["password_hash"], password):
            session["admin_id"] = admin["id"]
            session["admin_name"] = admin["full_name"]
            session["admin_username"] = admin["username"]
            flash(f"Welcome back, {admin['full_name']}!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials. Please try again.", "danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) as total FROM scans")
    total = cur.fetchone()["total"]
    cur.execute("SELECT COUNT(*) as cnt FROM scans WHERE result_class = 0")
    no_bleed = cur.fetchone()["cnt"]
    cur.execute("SELECT COUNT(*) as cnt FROM scans WHERE result_class > 0")
    detected = cur.fetchone()["cnt"]
    cur.execute("SELECT s.*, a.username FROM scans s JOIN admins a ON s.uploaded_by = a.id ORDER BY s.created_at DESC LIMIT 6")
    recent = cur.fetchall()
    cur.close()
    stats = {"total": total, "no_bleed": no_bleed, "detected": detected,
             "detection_rate": round((detected / total * 100) if total else 0, 1)}
    return render_template("dashboard.html", stats=stats, recent=recent,
                           class_names=CLASS_NAMES, class_colors=CLASS_COLORS)

@app.route("/upload", methods=["GET", "POST"])
@login_required
def upload():
    if request.method == "POST":
        if "mri_image" not in request.files:
            flash("No file selected.", "danger")
            return redirect(request.url)
        file = request.files["mri_image"]
        patient_name = request.form.get("patient_name", "Unknown").strip()
        patient_id   = request.form.get("patient_id", "").strip()
        notes        = request.form.get("notes", "").strip()
        if file.filename == "":
            flash("No file selected.", "danger")
            return redirect(request.url)
        if file and allowed_file(file.filename):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = secure_filename(f"{timestamp}_{file.filename}")
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)
            # Run inference
            label, probs, class_idx = predict(filepath)
            confidence = round(probs[class_idx] * 100, 1)
            cur = mysql.connection.cursor()
            cur.execute("""
                INSERT INTO scans
                  (patient_name, patient_id, image_filename, result_label,
                   result_class, confidence, probabilities, notes, uploaded_by)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (patient_name, patient_id, filename, label, class_idx,
                  confidence, json.dumps(probs), notes, session["admin_id"]))
            mysql.connection.commit()
            scan_id = cur.lastrowid
            cur.close()
            flash("Scan analysed successfully!", "success")
            return redirect(url_for("result", scan_id=scan_id))
        else:
            flash("Invalid file type. Allowed: PNG, JPG, JPEG, BMP, TIFF.", "danger")
    return render_template("upload.html")

@app.route("/result/<int:scan_id>")
@login_required
def result(scan_id):
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT s.*, a.full_name as doctor_name
        FROM scans s JOIN admins a ON s.uploaded_by = a.id
        WHERE s.id = %s
    """, (scan_id,))
    scan = cur.fetchone()
    cur.close()
    if not scan:
        flash("Scan not found.", "danger")
        return redirect(url_for("dashboard"))
    scan["probabilities"] = json.loads(scan["probabilities"])
    return render_template("result.html", scan=scan,
                           class_names=CLASS_NAMES, class_colors=CLASS_COLORS)

@app.route("/history")
@login_required
def history():
    page = int(request.args.get("page", 1))
    per_page = 10
    offset = (page - 1) * per_page
    search = request.args.get("q", "").strip()
    cur = mysql.connection.cursor()
    if search:
        cur.execute("SELECT COUNT(*) as cnt FROM scans WHERE patient_name LIKE %s OR patient_id LIKE %s",
                    (f"%{search}%", f"%{search}%"))
    else:
        cur.execute("SELECT COUNT(*) as cnt FROM scans")
    total = cur.fetchone()["cnt"]
    if search:
        cur.execute("""SELECT s.*, a.username FROM scans s JOIN admins a ON s.uploaded_by = a.id
                       WHERE s.patient_name LIKE %s OR s.patient_id LIKE %s
                       ORDER BY s.created_at DESC LIMIT %s OFFSET %s""",
                    (f"%{search}%", f"%{search}%", per_page, offset))
    else:
        cur.execute("""SELECT s.*, a.username FROM scans s JOIN admins a ON s.uploaded_by = a.id
                       ORDER BY s.created_at DESC LIMIT %s OFFSET %s""", (per_page, offset))
    scans = cur.fetchall()
    cur.close()
    pages = (total + per_page - 1) // per_page
    return render_template("history.html", scans=scans, page=page, pages=pages,
                           total=total, search=search, class_names=CLASS_NAMES, class_colors=CLASS_COLORS)

@app.route("/scan/<int:scan_id>/delete", methods=["POST"])
@login_required
def delete_scan(scan_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT image_filename FROM scans WHERE id = %s", (scan_id,))
    scan = cur.fetchone()
    if scan:
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], scan["image_filename"])
        if os.path.exists(filepath):
            os.remove(filepath)
        cur.execute("DELETE FROM scans WHERE id = %s", (scan_id,))
        mysql.connection.commit()
        flash("Scan deleted.", "info")
    cur.close()
    return redirect(url_for("history"))

@app.route("/api/stats")
@login_required
def api_stats():
    cur = mysql.connection.cursor()
    cur.execute("""SELECT result_class, COUNT(*) as cnt FROM scans GROUP BY result_class""")
    rows = cur.fetchall()
    cur.close()
    data = [0, 0, 0, 0]
    for r in rows:
        data[r["result_class"]] = r["cnt"]
    return jsonify({"labels": CLASS_NAMES, "data": data, "colors": CLASS_COLORS})

if __name__ == "__main__":
    app.run(debug=True, port=5000)
