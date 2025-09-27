from flask import Flask, request, jsonify, send_from_directory, g
import sqlite3, os, json, base64, datetime

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(APP_DIR, "data.db")
CONTENT_PATH = os.path.join(os.path.dirname(APP_DIR), "content", "clinician_content.json")

def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DB_PATH)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = get_db()
    db.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        language TEXT,
        age_group TEXT,
        consent INTEGER,
        contact TEXT,
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        role TEXT,
        message TEXT,
        risk_level TEXT,
        created_at TEXT
    );
    CREATE TABLE IF NOT EXISTS moods (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        rating INTEGER,
        note TEXT,
        created_at TEXT
    );
    """)
    db.commit()

# Simple reversible encoding for "demo encryption" (NOT secure; for demo only)
def encode(s):
    if s is None: return None
    return base64.b64encode(s.encode("utf-8")).decode("utf-8")
def decode(s):
    if s is None: return None
    return base64.b64decode(s.encode("utf-8")).decode("utf-8")

# Minimal multilingual high-risk keywords dictionary
HIGH_RISK = {
    "en": ["i want to die","kill myself","end my life","suicide"],
    "bn": ["আমি মরে যেতে চাই","আত্মহত্যা","মরে যেতে চাই"],
    "es": ["quiero morir","suicidio","matarme"],
    "fr": ["je veux mourir","suicide"],
    "zh": ["想自殺","自杀","我想死"],
    "hi": ["मैं मरना चाहता हूँ","आत्महत्या","मुझे मरना है"],
    "ar": ["أريد أن أموت","انتحار"],
    "ru": ["хочу умереть","самоубийство"],
    "pt": ["quero morrer","suicídio","me matar"],
    "ur": ["میں مر جانا چاہتا ہوں","خودکشی"]
}

# Load clinician content
with open(CONTENT_PATH, "r", encoding="utf-8") as f:
    CLINICIAN_CONTENT = json.load(f)

app = Flask(__name__, static_folder="../frontend", template_folder="../frontend")
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

@app.before_first_request
def setup():
    init_db()

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Serve frontend
@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def static_proxy(path):
    if path == "" or path.endswith(".html"):
        return send_from_directory(app.static_folder, "index.html")
    # static files
    return send_from_directory(app.static_folder, path)

# API: register (onboarding)
@app.route("/api/register", methods=["POST"])
def register():
    data = request.json or {}
    lang = data.get("language","en")
    age = data.get("age_group","unknown")
    consent = 1 if data.get("consent", False) else 0
    contact = data.get("contact")
    db = get_db()
    cur = db.execute("INSERT INTO users (language, age_group, consent, contact, created_at) VALUES (?,?,?,?,?)",
                     (lang, age, consent, encode(contact) if contact else None, datetime.datetime.utcnow().isoformat()))
    db.commit()
    uid = cur.lastrowid
    return jsonify({"user_id": uid})

# API: chat
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json or {}
    user_id = data.get("user_id")
    text = data.get("text","").strip()
    lang = data.get("language","en")
    risk = "low"
    lower = text.lower()
    # simple rule-based high risk detection
    for kw in HIGH_RISK.get(lang, []) + HIGH_RISK.get("en", []):
        if kw in lower:
            risk = "high"
            break
    # store user message
    db = get_db()
    db.execute("INSERT INTO chats (user_id, role, message, risk_level, created_at) VALUES (?,?,?,?,?)",
               (user_id, "user", encode(text), risk, datetime.datetime.utcnow().isoformat()))
    db.commit()

    # generate reply (templated)
    if risk == "high":
        reply = CLINICIAN_CONTENT.get("safety_templates", {}).get(lang) or CLINICIAN_CONTENT["safety_templates"].get("en")
        # store assistant message
        db.execute("INSERT INTO chats (user_id, role, message, risk_level, created_at) VALUES (?,?,?,?,?)",
                   (user_id, "assistant", encode(reply), risk, datetime.datetime.utcnow().isoformat()))
        db.commit()
        return jsonify({"reply": reply, "risk_level": risk})
    else:
        # basic empathetic template and offer interventions
        reply = ""
        if len(text) < 5:
            reply = CLINICIAN_CONTENT["small_talk"].get(lang) or CLINICIAN_CONTENT["small_talk"]["en"]
        else:
            reply = CLINICIAN_CONTENT["default_reply"].get(lang) or CLINICIAN_CONTENT["default_reply"]["en"]
        db.execute("INSERT INTO chats (user_id, role, message, risk_level, created_at) VALUES (?,?,?,?,?)",
                   (user_id, "assistant", encode(reply), risk, datetime.datetime.utcnow().isoformat()))
        db.commit()
        return jsonify({"reply": reply, "risk_level": risk})

# API: get content list
@app.route("/api/content", methods=["GET"])
def content_list():
    lang = request.args.get("lang","en")
    # return CBT and breathing templates in requested language (or fallback)
    cbt = CLINICIAN_CONTENT.get("cbt", {}).get(lang) or CLINICIAN_CONTENT.get("cbt", {}).get("en")
    breathing = CLINICIAN_CONTENT.get("breathing", {}).get(lang) or CLINICIAN_CONTENT.get("breathing", {}).get("en")
    safety = CLINICIAN_CONTENT.get("safety_templates", {}).get(lang) or CLINICIAN_CONTENT.get("safety_templates", {}).get("en")
    return jsonify({"cbt": cbt, "breathing": breathing, "safety": safety})

# API: mood save/get
@app.route("/api/mood", methods=["POST","GET"])
def mood():
    db = get_db()
    if request.method == "POST":
        data = request.json or {}
        user_id = data.get("user_id")
        rating = int(data.get("rating",0))
        note = data.get("note")
        db.execute("INSERT INTO moods (user_id, rating, note, created_at) VALUES (?,?,?,?)",
                   (user_id, rating, encode(note) if note else None, datetime.datetime.utcnow().isoformat()))
        db.commit()
        return jsonify({"status":"ok"})
    else:
        user_id = request.args.get("user_id")
        cur = db.execute("SELECT rating, note, created_at FROM moods WHERE user_id=? ORDER BY created_at DESC LIMIT 100", (user_id,))
        rows = []
        for r in cur.fetchall():
            rows.append({"rating": r["rating"], "note": decode(r["note"]) if r["note"] else None, "created_at": r["created_at"]})
        return jsonify(rows)

# API: export data (simple)
@app.route("/api/export", methods=["GET"])
def export_data():
    user_id = request.args.get("user_id")
    db = get_db()
    u = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not u:
        return jsonify({"error":"user not found"}), 404
    user = {"id": u["id"], "language": u["language"], "age_group": u["age_group"], "consent": u["consent"], "contact": decode(u["contact"]) if u["contact"] else None, "created_at":u["created_at"]}
    chats = []
    for r in db.execute("SELECT role,message,risk_level,created_at FROM chats WHERE user_id=? ORDER BY created_at", (user_id,)).fetchall():
        chats.append({"role": r["role"], "message": decode(r["message"]) if r["message"] else None, "risk_level": r["risk_level"], "created_at": r["created_at"]})
    moods = []
    for r in db.execute("SELECT rating,note,created_at FROM moods WHERE user_id=? ORDER BY created_at", (user_id,)).fetchall():
        moods.append({"rating": r["rating"], "note": decode(r["note"]) if r["note"] else None, "created_at": r["created_at"]})
    return jsonify({"user":user,"chats":chats,"moods":moods})

# API: delete (GDPR-like)
@app.route("/api/delete", methods=["POST"])
def delete_user():
    data = request.json or {}
    user_id = data.get("user_id")
    db = get_db()
    # remove PII: contact and notes replaced with NULL; chats and moods kept but anonymized (message redacted)
    db.execute("UPDATE users SET contact=NULL WHERE id=?", (user_id,))
    db.execute("UPDATE chats SET message=? WHERE user_id=?", ("<redacted by user request>", user_id))
    db.execute("UPDATE moods SET note=NULL WHERE user_id=?", (user_id,))
    db.commit()
    return jsonify({"status":"deleted"})

if __name__ == "__main__":
    with app.app_context():
        init_db()
    app.run(debug=True, host="0.0.0.0", port=8000)
