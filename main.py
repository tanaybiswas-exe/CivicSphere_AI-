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

    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
        INSERT INTO users (full_name, email, password_hash, nid_number, dob, role, is_verified, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            ('System Administrator', 'admin@civicsphere.gov.bd', hash_pw('admin123'), '1995547891234', '1995-05-12', 'Admin', 1, '2026-01-01'),
            ('Tanay Biswas Bandhan', 'tanay@civicsphere.ai', hash_pw('citizen123'), '2000269874512', '2000-04-22', 'Citizen', 1, '2026-01-02')
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
            ),
            (
                'CIVIC-2026-1089', '2000269874512', 'DNCRP-4490', 'Consumer Rights & Market Overcharge',
                'Directorate of National Consumer Rights Protection (DNCRP)',
                'Retailer charging 210 BDT for 1L soybean oil against printed MRP of 175 BDT.',
                'Date: 14 November 2026\nTo, The Director General, DNCRP...\nSubject: Formal Complaint Under Section 40 of Consumer Rights Protection Act, 2009.',
                'Submitted', 'cash_memo_#4092.pdf', '2026-11-14 15:20'
            ),
            (
                'CIVIC-2026-1104', '2000269874512', 'GRS-90115', 'Public Utilities (Power, Water, Gas)',
                'Dhaka Electric Supply Company (DESCO)',
                'Exposed high-voltage transformer wiring hanging near Uttara Sector 7 school gate.',
                'Date: 16 November 2026\nTo, Managing Director, DESCO...\nSubject: Immediate Safety Intervention for Exposed Wiring.',
                'Resolved', 'video_clip_uttara7.mp4', '2026-11-16 09:15'
            )
        ])

    cur.execute("SELECT COUNT(*) FROM hazards")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
        INSERT INTO hazards (title, category, lat, lng, upvotes, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            ('Uncovered Deep Manhole on Main Road', 'Drainage Hazard', 23.8069, 90.3687, 34, 'Verified', '2026-11-12'),
            ('Severe Crater Pothole Causing Bottleneck', 'Road Damage', 23.7509, 90.3935, 19, 'Open', '2026-11-15'),
            ('Broken Streetlights in School Zone', 'Public Safety', 23.8759, 90.3795, 12, 'Open', '2026-11-16')
        ])

    cur.execute("SELECT COUNT(*) FROM audit_logs")
    if cur.fetchone()[0] == 0:
        cur.execute("""
        INSERT INTO audit_logs (actor_role, action, target_id, timestamp)
        VALUES ('System', 'Initialized NID-Verified Ledger & LGED/PWD Rate Schedules', 'SYS-BOOT', ?)
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
    if any(k in p for k in ["bribe", "ghush", "ঘুষ", "দুর্নীতি", "corruption", "commission"]):
        domain = "Anti-Corruption & Bribery"
        dept = "Anti-Corruption Commission (ACC / দুদক) — Helpline 106"
        law = "Prevention of Corruption Act, 1947 & Public Interest Information Disclosure Act, 2011"
    elif any(k in p for k in ["price", "mrp", "দাম", "বেশি", "overcharge", "expired", "ভেজাল", "food", "oil"]):
        domain = "Consumer Rights & Market Overcharge"
        dept = "Directorate of National Consumer Rights Protection (DNCRP) — Helpline 16121"
        law = "Consumer Rights Protection Act, 2009 (Sections 37, 40, 51)"
    elif any(k in p for k in ["road", "pothole", "রাস্তা", "গর্ত", "drain", "জলাবদ্ধতা", "manhole", "waterlog", "culvert"]):
        domain = "Roads, Drainage & Urban Infrastructure"
        dept = "City Corporation / LGED / Roads & Highways Department (RHD)"
        law = "Local Government (City Corporation) Act, 2009 & Citizen Charter (GRS)"
    elif any(k in p for k in ["electricity", "power", "বিদ্যুৎ", "water", "wasa", "পানি", "gas", "transformer"]):
        domain = "Public Utilities (Power, Water, Gas)"
        dept = "DESCO / DPDC / BREB / WASA (via Central GRS Portal)"
        law = "Bangladesh Energy Regulatory Commission Act & GRS Guidelines"
    elif any(k in p for k in ["hospital", "doctor", "হাসপাতাল", "চিকিৎসা", "medicine"]):
        domain = "Public Healthcare Services"
        dept = "Directorate General of Health Services (DGHS) / Ministry of Health"
        law = "Citizen Charter & Central Grievance Redress System (GRS)"
    elif any(k in p for k in ["school", "college", "শিক্ষা", "স্কুল", "stipend"]):
        domain = "Public Education & Institutions"
        dept = "Directorate of Secondary and Higher Education (DSHE) / DPE"
        law = "National Education Policy & GRS Guidelines"
    elif any(k in p for k in ["land", "জমি", "mutation", "নামজারি", "khatian"]):
        domain = "Land Administration & Mutation"
        dept = "AC Land Office / Ministry of Land (Hotline: 16122)"
        law = "State Acquisition and Tenancy Act & Land Management Manual"
    elif any(k in p for k in ["police", "gd", "থানা", "harassment", "safety"]):
        domain = "Law Enforcement & Public Safety"
        dept = "Bangladesh Police (IGP Complain Cell / National Emergency 999)"
        law = "Police Regulations of Bengal (PRB) & Penal Code"
    else:
        domain = "General Public Administration"
        dept = "Cabinet Division — Central Grievance Redress System (GRS)"
        law = "Grievance Redress System (GRS) Guidelines, 2015 (Revised 2018)"

    date_str = datetime.now().strftime("%d %B %Y")
    if lang == "bn":
        draft = f"""তারিখ: {date_str}
বরাবর,
যথাযথ কর্তৃপক্ষ,
{dept}

বিষয়: {domain} সংক্রান্ত জরুরি অভিযোগ ও প্রতিকার প্রসঙ্গে।

জনাব,
সবিনয় নিবেদন এই যে, আমি বাংলাদেশের একজন NID-যাচাইকৃত সচেতন নাগরিক। নিম্নোক্ত জনস্বার্থ সংশ্লিষ্ট বিষয়টি আপনার সদয় অবগতি ও প্রয়োজনীয় ব্যবস্থা গ্রহণের জন্য উপস্থাপন করছি:

অভিযোগের বিবরণ:
"{prompt}"

প্রযোজ্য আইন ও বিধিমালা ({law}) অনুযায়ী বিষয়টি দ্রুত তদন্তপূর্বক প্রয়োজনীয় প্রশাসনিক ব্যবস্থা গ্রহণ করার জন্য বিনীত অনুরোধ জানাচ্ছি।

বিনীত নিবেদক,
একজন সচেতন নাগরিক
(CivicSphere AI নাগরিক সহায়তা পোর্টালের মাধ্যমে প্রস্তুতকৃত — এটি কোনো সরকারি ওয়েবসাইট নয়)"""
    else:
        draft = f"""Date: {date_str}
To,
The Competent Authority,
{dept}

Subject: Formal Civic Grievance Regarding {domain}

Dear Sir/Madam,
I am writing as a verified citizen to formally bring to your immediate attention an urgent civic issue affecting public welfare:

Statement of Grievance:
"{prompt}"

In accordance with the provisions of {law}, I respectfully request your office to investigate this matter and initiate appropriate remedial action within the stipulated Citizen Charter timeframe.

Sincerely,
A Concerned Citizen
(Drafted via CivicSphere AI — Independent Citizen Assistance Platform)"""

    ai_powered = False
    if GEMINI_API_KEY:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
            sys_instruction = (
                "You are CivicSphere AI, an independent citizen assistance platform in Bangladesh (NOT a government website). "
                f"Write a formal, legally accurate complaint in {'Bangla' if lang == 'bn' else 'English'} addressed to {dept} "
                f"citing {law}. Keep it structured, polite, and actionable. End with a brief disclaimer that CivicSphere AI is an independent platform."
            )
            body = json.dumps({
                "contents": [{"parts": [{"text": f"{sys_instruction}\n\nCitizen Issue: {prompt}"}]}]
            }).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    text = candidates[0]["content"]["parts"][0]["text"]
                    if text.strip():
                        draft = text.strip()
                        ai_powered = True
        except Exception:
            pass

    return {"domain": domain, "department": dept, "law": law, "draft": draft, "ai_powered": ai_powered}

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
                "total_upvotes": sum(h["upvotes"] for h in hazards),
                "total_users": len(users),
                "users": masked_users,
                "status_counts": status_counts,
                "domain_counts": domain_counts,
                "audit_logs": [dict(l) for l in logs],
                "gemini_active": bool(GEMINI_API_KEY)
            })
            return

        self._send_json({"error": "Not Found"}, 404)

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._read_json()

        # NID / Smart Card Verified Registration
        if path == "/api/auth/register":
            name = (body.get("full_name") or "").strip()
            email = (body.get("email") or "").strip().lower()
            password = body.get("password") or ""
            nid = (body.get("nid_number") or "").strip()
            dob = (body.get("dob") or "").strip()

            if not name or not email or len(password) < 6:
                self._send_json({"success": False, "message": "Please fill all fields (Password min 6 chars)."}, 400)
                return

            if not nid.isdigit() or len(nid) not in [10, 13, 17]:
                self._send_json({"success": False, "message": "Invalid NID / Smart Card Number. Must be 10, 13, or 17 digits."}, 400)
                return

            if not dob:
                self._send_json({"success": False, "message": "Date of Birth is required for NID cross-verification."}, 400)
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
                self._send_json({"success": True, "message": "NID/Smart Card verified! Registration complete. You may now log in."})
            except sqlite3.IntegrityError:
                conn.close()
                self._send_json({"success": False, "message": "This Email or NID Number is already registered."}, 400)
            return

        # Role-Based Login
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
                self._send_json({"success": False, "message": "Invalid email or password."}, 401)
            return

        if path == "/api/assistant/analyze":
            result = classify_issue(body.get("prompt", ""), body.get("lang", "en"))
            self._send_json(result)
            return

        if path == "/api/complaints":
            tracking_id = f"CIVIC-2026-{random.randint(1200, 9999)}"
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
            conn = get_db()
            conn.execute(
                """INSERT INTO complaints (tracking_id, citizen_nid, external_ref, domain, department, description, draft_text, status, evidence_note, created_at)
                   VALUES (?, ?, 'Pending Filing', ?, ?, ?, ?, 'Draft', ?, ?)""",
                (
                    tracking_id, body.get("citizen_nid", "Verified-Citizen"),
                    body.get("domain", "General"), body.get("department", "GRS"),
                    body.get("description", ""), body.get("draft_text", ""),
                    body.get("evidence_note", "No file attached"), created_at
                )
            )
            conn.commit()
            conn.close()
            log_audit("Citizen", f"Created Complaint Draft ({body.get('domain')})", tracking_id)
            self._send_json({"tracking_id": tracking_id, "status": "Draft"})
            return

        if path == "/api/boq/audit":
            agency = body.get("agency", "LGED").upper()
            agency_key = "pwd" if agency == "PWD" else "lged"
            allocated_budget = float(body.get("allocated_budget", 0))
            items = body.get("items", [])

            line_results = []
            total_benchmark = 0.0
            total_quoted = 0.0
            anomaly_count = 0

            for item in items:
                sched = SCHEDULE_RATES.get(item.get("item_code"))
                if not sched:
                    continue
                qty = float(item.get("quantity", 0))
                quoted_rate = float(item.get("quoted_unit_rate", 0))
                std_rate = sched[agency_key]

                bench_total = round(std_rate * qty, 2)
                quoted_total = round(quoted_rate * qty, 2)
                var_pct = round(((quoted_rate - std_rate) / std_rate) * 100, 2) if std_rate > 0 else 0.0
                is_inflated = var_pct > 20.0
                if is_inflated:
                    anomaly_count += 1

                total_benchmark += bench_total
                total_quoted += quoted_total

                line_results.append({
                    "name": sched["name"],
                    "unit": sched["unit"],
                    "quantity": qty,
                    "standard_rate": std_rate,
                    "quoted_rate": quoted_rate,
                    "benchmark_total": bench_total,
                    "quoted_total": quoted_total,
                    "rate_variance_pct": var_pct,
                    "flag": "INFLATED (>20%)" if is_inflated else "NORMAL"
                })

            budget_var = round(total_quoted - allocated_budget, 2)
            budget_var_pct = round((budget_var / allocated_budget) * 100, 2) if allocated_budget > 0 else 0.0
            sched_var = round(total_quoted - total_benchmark, 2)
            sched_var_pct = round((sched_var / total_benchmark) * 100, 2) if total_benchmark > 0 else 0.0
            overall_alert = anomaly_count > 0 or abs(budget_var_pct) > 20.0 or sched_var_pct > 20.0

            log_audit(body.get("actor_role", "Citizen"), f"Audited BOQ: {body.get('project_name')} ({agency})", f"FLAGS:{anomaly_count}")
            self._send_json({
                "project_name": body.get("project_name", "Public Infrastructure Project"),
                "agency": agency,
                "matrix": {
                    "allocated_budget": allocated_budget,
                    "benchmark_schedule_cost": round(total_benchmark, 2),
                    "contractor_quoted_cost": round(total_quoted, 2),
                    "budget_variance_bdt": budget_var,
                    "budget_variance_pct": budget_var_pct,
                    "schedule_variance_bdt": sched_var,
                    "schedule_variance_pct": sched_var_pct
                },
                "overall_alert": overall_alert,
                "anomaly_count": anomaly_count,
                "items": line_results,
                "disclaimer": "Technical auditing indicator based on published LGED/PWD Schedule of Rates; does not constitute a legal accusation of fraud."
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
                "INSERT INTO hazards (title, category, lat, lng, upvotes, status, created_at) VALUES (?, ?, ?, ?, 1, 'Open', ?)",
                (body.get("title", "Civic Hazard"), body.get("category", "Road Damage"), lat, lng, datetime.now().strftime("%Y-%m-%d"))
            )
            new_id = cur.lastrowid
            conn.commit()
            conn.close()
            log_audit("Citizen", f"Pinned Hazard: {body.get('title')}", f"HAZ-{new_id}")
            self._send_json({"duplicate_detected": False, "id": new_id})
            return

        if path.startswith("/api/hazards/") and path.endswith("/upvote"):
            hazard_id = int(path.split("/")[3])
            conn = get_db()
            conn.execute("UPDATE hazards SET upvotes = upvotes + 1 WHERE id = ?", (hazard_id,))
            conn.commit()
            row = conn.execute("SELECT upvotes FROM hazards WHERE id = ?", (hazard_id,)).fetchone()
            conn.close()
            self._send_json({"id": hazard_id, "upvotes": row["upvotes"] if row else 0})
            return

        self._send_json({"error": "Not Found"}, 404)

    def do_PATCH(self):
        path = urlparse(self.path).path
        body = self._read_json()

        if path.startswith("/api/complaints/") and path.endswith("/status"):
            tracking_id = path.split("/")[3]
            new_status = body.get("status", "Draft")
            ext_ref = body.get("external_ref")
            role = self.headers.get("X-Role", "Citizen")

            conn = get_db()
            if ext_ref:
                conn.execute("UPDATE complaints SET status = ?, external_ref = ? WHERE tracking_id = ?", (new_status, ext_ref, tracking_id))
            else:
                conn.execute("UPDATE complaints SET status = ? WHERE tracking_id = ?", (new_status, tracking_id))
            conn.commit()
            conn.close()
            log_audit(role, f"Updated Status to '{new_status}'", tracking_id)
            self._send_json({"tracking_id": tracking_id, "status": new_status})
            return

        self._send_json({"error": "Not Found"}, 404)

if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", PORT), CivicSphereHandler)
    print(f"============================================================")
    print(f" CivicSphere AI (All 8 Modules + NID Auth) on http://127.0.0.1:{PORT}")
    print(f"============================================================")
    server.serve_forever()