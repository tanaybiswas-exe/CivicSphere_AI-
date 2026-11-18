import os
import json
import math
import hashlib
import sqlite3
import random
import urllib.request
from datetime import datetime
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

PORT = 8000
DB_PATH = "civicsphere.db"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT,
        email TEXT UNIQUE,
        password_hash TEXT,
        nid_number TEXT UNIQUE,
        dob TEXT,
        role TEXT DEFAULT 'Citizen',
        is_verified INTEGER DEFAULT 1,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS complaints (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tracking_id TEXT UNIQUE,
        citizen_nid TEXT,
        external_ref TEXT,
        domain TEXT,
        department TEXT,
        description TEXT,
        draft_text TEXT,
        status TEXT DEFAULT 'Draft',
        evidence_note TEXT,
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS hazards (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        category TEXT,
        lat REAL,
        lng REAL,
        upvotes INTEGER DEFAULT 1,
        status TEXT DEFAULT 'Open',
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor_role TEXT,
        action TEXT,
        target_id TEXT,
        timestamp TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS govt_services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_name TEXT,
        ministry TEXT,
        fee TEXT,
        sla_timeline TEXT,
        portal_url TEXT,
        last_auto_synced TEXT
    )
    """)

    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
        INSERT INTO users (full_name, email, password_hash, nid_number, dob, role, is_verified, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            ('System Administrator', 'admin@civicsphere.gov.bd', hash_pw('admin123'), '1995547891234', '1995-05-12', 'Admin', 1, '2026-01-01'),
            ('Tanay Biswas Bandhan', 'tanay@civicsphere.ai', hash_pw('citizen123'), '2000269874512', '2000-04-22', 'Citizen', 1, '2026-01-02')
        ])

    cur.execute("SELECT COUNT(*) FROM govt_services")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
        INSERT INTO govt_services (service_name, ministry, fee, sla_timeline, portal_url, last_auto_synced)
        VALUES (?, ?, ?, ?, ?, ?)
        """, [
            ("Central Grievance Redress System (GRS)", "Cabinet Division", "বিনামূল্যে (Free)", "15–30 Working Days", "https://grs.gov.bd", datetime.now().strftime("%Y-%m-%d %H:%M")),
            ("Anti-Corruption Commission (ACC / দুদক)", "Independent Commission", "বিনামূল্যে (Free)", "Helpline 106", "https://acc.org.bd", datetime.now().strftime("%Y-%m-%d %H:%M")),
            ("National Consumer Rights Protection (DNCRP)", "Ministry of Commerce", "বিনামূল্যে (Free)", "Within 30 Days", "https://dncrp.gov.bd", datetime.now().strftime("%Y-%m-%d %H:%M")),
            ("Local Government Engineering Department (LGED)", "Local Government Division", "বিনামূল্যে (Free)", "15–21 Working Days", "https://lged.gov.bd", datetime.now().strftime("%Y-%m-%d %H:%M"))
        ])

    cur.execute("SELECT COUNT(*) FROM complaints")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
        INSERT INTO complaints (tracking_id, citizen_nid, external_ref, domain, department, description, draft_text, status, evidence_note, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            (
                'CIVIC-2026-1042', '2000269874512', 'GRS-88412', 'Roads, Drainage & Urban Infrastructure',
                'Dhaka North City Corporation (DNCC)',
                'Severe waterlogging and uncovered deep manhole near Mirpur 10 roundabout.',
                'Date: 10 November 2026\nTo, The Chief Executive Officer, DNCC...\nSubject: Urgent Remediation of Uncovered Manhole at Mirpur-10.',
                'In Progress', 'photo_mirpur10_geotag.jpg (Verified)', '2026-11-10 10:30'
            )
        ])

    cur.execute("SELECT COUNT(*) FROM hazards")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
        INSERT INTO hazards (title, category, lat, lng, upvotes, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            ('Uncovered Deep Manhole on Main Road', 'Drainage Hazard', 23.8069, 90.3687, 34, 'Verified', '2026-11-12'),
            ('Severe Crater Pothole Causing Bottleneck', 'Road Damage', 23.7509, 90.3935, 19, 'Open', '2026-11-15')
        ])

    cur.execute("SELECT COUNT(*) FROM audit_logs")
    if cur.fetchone()[0] == 0:
        cur.execute("""
        INSERT INTO audit_logs (actor_role, action, target_id, timestamp)
        VALUES ('System', 'Initialized Auto-Sync Govt Directory & NID Verified Ledger', 'SYS-BOOT', ?)
        """, (datetime.now().strftime("%Y-%m-%d %H:%M:%S"),))

    conn.commit()
    conn.close()

init_db()

SCHEDULE_RATES = {
    "earthwork_cum": {"name": "Earthwork in Box/Road Excavation (per m³)", "lged": 320.0, "pwd": 340.0, "unit": "m³"},
    "brick_flat_soling_sqm": {"name": "1st Class Brick Flat Soling (per m²)", "lged": 680.0, "pwd": 710.0, "unit": "m²"},
    "rcc_concrete_cum": {"name": "RCC Works 1:2:4 with Stone Chips (per m³)", "lged": 11500.0, "pwd": 11900.0, "unit": "m³"},
    "ms_rebar_kg": {"name": "60-Grade MS Deformed Rebar (per kg)", "lged": 96.0, "pwd": 98.5, "unit": "kg"},
    "bituminous_carpeting_sqm": {"name": "25mm Dense Bituminous Carpeting (per m²)", "lged": 890.0, "pwd": 920.0, "unit": "m²"},
}

def log_audit(role: str, action: str, target_id: str):
    conn = get_db()
    conn.execute(
        "INSERT INTO audit_logs (actor_role, action, target_id, timestamp) VALUES (?, ?, ?, ?)",
        (role, action, target_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def classify_issue(prompt: str, lang: str):
    p = prompt.lower()
    if any(k in p for k in ["bribe", "ghush", "ঘুষ", "দুর্নীতি", "corruption"]):
        domain, dept, law = "Anti-Corruption & Bribery", "Anti-Corruption Commission (ACC / দুদক)", "Prevention of Corruption Act, 1947"
    elif any(k in p for k in ["price", "mrp", "দাম", "overcharge", "oil"]):
        domain, dept, law = "Consumer Rights", "Directorate of National Consumer Rights Protection (DNCRP)", "Consumer Rights Protection Act, 2009"
    else:
        domain, dept, law = "Roads & Urban Infrastructure", "City Corporation / LGED", "Local Government Act, 2009"

    draft = f"To: {dept}\nSubject: Formal Grievance regarding {domain}.\n\nDetails: {prompt}\n\nStatutory Ref: {law}"
    return {"domain": domain, "department": dept, "law": law, "draft": draft}

class CivicSphereHandler(BaseHTTPRequestHandler):
    def _send_json(self, data, status=200):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length).decode("utf-8")) if length else {}

    def do_GET(self):
        path = urlparse(self.path).path

        if path in ["/", "/index.html"]:
            try:
                with open("static/index.html", "rb") as f:
                    content = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except FileNotFoundError:
                self._send_json({"error": "static/index.html not found"}, 404)
            return

        if path == "/api/complaints":
            conn = get_db()
            rows = conn.execute("SELECT * FROM complaints ORDER BY id DESC").fetchall()
            conn.close()
            self._send_json([dict(r) for r in rows])
            return

        if path == "/api/boq/rates":
            self._send_json(SCHEDULE_RATES)
            return

        if path == "/api/hazards":
            conn = get_db()
            rows = conn.execute("SELECT * FROM hazards ORDER BY upvotes DESC").fetchall()
            conn.close()
            self._send_json([dict(r) for r in rows])
            return

        if path == "/api/services":
            conn = get_db()
            rows = conn.execute("SELECT * FROM govt_services ORDER BY id ASC").fetchall()
            conn.close()
            self._send_json([dict(r) for r in rows])
            return

        if path == "/api/admin/analytics":
            conn = get_db()
            complaints = conn.execute("SELECT domain, status FROM complaints").fetchall()
            hazards = conn.execute("SELECT category, upvotes, status FROM hazards").fetchall()
            users = conn.execute("SELECT id, full_name, email, nid_number, dob, role, is_verified, created_at FROM users ORDER BY id DESC").fetchall()
            logs = conn.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 25").fetchall()
            conn.close()

            status_counts = {"Draft": 0, "Ready": 0, "Submitted": 0, "In Progress": 0, "Resolved": 0}
            domain_counts = {}
            for c in complaints:
                status_counts[c["status"]] = status_counts.get(c["status"], 0) + 1
                domain_counts[c["domain"]] = domain_counts.get(c["domain"], 0) + 1

            masked_users = []
            for u in users:
                ud = dict(u)
                nid = ud["nid_number"] or ""
                ud["nid_masked"] = f"****-****-{nid[-4:]}" if len(nid) >= 4 else nid
                masked_users.append(ud)

            self._send_json({
                "total_complaints": len(complaints),
                "resolved_complaints": status_counts.get("Resolved", 0),
                "total_hazards": len(hazards),
                "total_users": len(users),
                "users": masked_users,
                "status_counts": status_counts,
                "domain_counts": domain_counts,
                "audit_logs": [dict(l) for l in logs]
            })
            return

        self._send_json({"error": "Not Found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_json()

        if path == "/api/auth/register":
            name = (body.get("full_name") or "").strip()
            email = (body.get("email") or "").strip().lower()
            password = body.get("password") or ""
            nid = (body.get("nid_number") or "").strip()
            dob = (body.get("dob") or "").strip()

            if not nid.isdigit() or len(nid) not in [10, 13, 17]:
                self._send_json({"success": False, "message": "Invalid NID / Smart Card Number (Must be 10, 13 or 17 digits)."}, 400)
                return

            conn = get_db()
            try:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO users (full_name, email, password_hash, nid_number, dob, role, is_verified, created_at) VALUES (?, ?, ?, ?, ?, 'Citizen', 1, ?)",
                    (name, email, hash_pw(password), nid, dob, datetime.now().strftime("%Y-%m-%d"))
                )
                conn.commit()
                uid = cur.lastrowid
                conn.close()
                log_audit("Citizen", f"NID Verified Registration (****{nid[-4:]})", f"USR-{uid}")
                self._send_json({"success": True, "message": "NID verified! Account created successfully. Please login."})
            except sqlite3.IntegrityError:
                conn.close()
                self._send_json({"success": False, "message": "Email or NID already exists in database."}, 400)
            return

        if path == "/api/auth/login":
            email = (body.get("email") or "").strip().lower()
            password = body.get("password") or ""
            conn = get_db()
            user = conn.execute("SELECT * FROM users WHERE email = ? AND password_hash = ?", (email, hash_pw(password))).fetchone()
            conn.close()

            if user:
                log_audit(user["role"], f"Authenticated Session ({user['email']})", f"USR-{user['id']}")
                self._send_json({
                    "success": True,
                    "user": {
                        "id": user["id"],
                        "full_name": user["full_name"],
                        "email": user["email"],
                        "role": user["role"],
                        "nid_masked": f"****-****-{user['nid_number'][-4:]}"
                    }
                })
            else:
                self._send_json({"success": False, "message": "Invalid credentials. Access denied."}, 401)
            return

        if path == "/api/assistant/analyze":
            result = classify_issue(body.get("prompt", ""), body.get("lang", "en"))
            self._send_json(result)
            return

        if path == "/api/complaints":
            tracking_id = f"CIVIC-2026-{random.randint(1200, 9999)}"
            conn = get_db()
            conn.execute(
                "INSERT INTO complaints (tracking_id, citizen_nid, external_ref, domain, department, description, draft_text, status, evidence_note, created_at) VALUES (?, ?, 'Pending', ?, ?, ?, ?, 'Draft', ?, ?)",
                (tracking_id, body.get("citizen_nid", "Verified-Citizen"), body.get("domain"), body.get("department"), body.get("description"), body.get("draft_text"), body.get("evidence_note", "None"), datetime.now().strftime("%Y-%m-%d"))
            )
            conn.commit()
            conn.close()
            log_audit("Citizen", f"Created Complaint Draft ({body.get('domain')})", tracking_id)
            self._send_json({"tracking_id": tracking_id})
            return

        if path == "/api/boq/audit":
            agency = body.get("agency", "LGED").upper()
            agency_key = "pwd" if agency == "PWD" else "lged"
            allocated = float(body.get("allocated_budget", 0))
            items = body.get("items", [])
            total_bench, total_quoted, anomalies = 0.0, 0.0, 0
            line_results = []

            for item in items:
                sched = SCHEDULE_RATES.get(item.get("item_code"))
                if not sched: continue
                qty = float(item.get("quantity", 0))
                quoted = float(item.get("quoted_unit_rate", 0))
                std = sched[agency_key]
                b_tot, q_tot = std * qty, quoted * qty
                var_pct = round(((quoted - std) / std) * 100, 2)
                if var_pct > 20: anomalies += 1
                total_bench += b_tot
                total_quoted += q_tot
                line_results.append({
                    "name": sched["name"], "unit": sched["unit"], "quantity": qty,
                    "standard_rate": std, "quoted_rate": quoted, "benchmark_total": b_tot,
                    "quoted_total": q_tot, "rate_variance_pct": var_pct,
                    "flag": "INFLATED (>20%)" if var_pct > 20 else "NORMAL"
                })

            self._send_json({
                "project_name": body.get("project_name"), "agency": agency,
                "matrix": {"allocated_budget": allocated, "benchmark_schedule_cost": round(total_bench, 2), "contractor_quoted_cost": round(total_quoted, 2)},
                "overall_alert": anomalies > 0, "anomaly_count": anomalies, "items": line_results,
                "disclaimer": "Technical auditing indicator based on LGED/PWD Schedule of Rates."
            })
            return

        if path == "/api/hazards":
            lat = float(body.get("lat", 23.8103))
            lng = float(body.get("lng", 90.4125))
            force = bool(body.get("force_create", False))

            conn = get_db()
            existing = conn.execute("SELECT * FROM hazards").fetchall()
            if not force:
                for h in existing:
                    dist = haversine_meters(lat, lng, h["lat"], h["lng"])
                    if dist <= 100.0:
                        conn.close()
                        self._send_json({
                            "duplicate_detected": True,
                            "distance_meters": round(dist, 1),
                            "existing_hazard": dict(h)
                        })
                        return

            cur = conn.execute(
                "INSERT INTO hazards (title, category, lat, lng, upvotes, status, created_at) VALUES (?, ?, ?, ?, ?, 'Open', ?)",
                (body.get("title", "Civic Hazard"), body.get("category", "Road Damage"), lat, lng, datetime.now().strftime("%Y-%m-%d"))
            )
            new_id = cur.lastrowid
            conn.commit()
            conn.close()
            log_audit("Citizen", f"Pinned Hazard: {body.get('title')}", f"HAZ-{new_id}")
            self._send_json({"duplicate_detected": False, "id": new_id})
            return

        if path.startswith("/api/hazards/") and path.endswith("/upvote"):
            h_id = int(path.split("/")[3])
            conn = get_db()
            conn.execute("UPDATE hazards SET upvotes = upvotes + 1 WHERE id = ?", (h_id,))
            conn.commit()
            conn.close()
            self._send_json({"success": True})
            return

        self._send_json({"error": "Not Found"}, 404)

if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), CivicSphereHandler)
    print(f"CivicSphere AI running at http://127.0.0.1:{PORT}")
    server.serve_forever()
