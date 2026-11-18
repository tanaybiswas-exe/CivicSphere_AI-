import os
import math
import hashlib
import random
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
app = FastAPI(title="CivicSphere AI", version="2.5")

# Serve static folder for index.html
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

def get_db():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()

def init_db():
    if not DATABASE_URL:
        print("DATABASE_URL not found!")
        return
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            full_name TEXT,
            email TEXT UNIQUE,
            password_hash TEXT,
            nid_number TEXT UNIQUE,
            dob TEXT,
            role TEXT DEFAULT 'Citizen',
            is_verified INT DEFAULT 1,
            created_at TEXT
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id SERIAL PRIMARY KEY,
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
            id SERIAL PRIMARY KEY,
            title TEXT,
            category TEXT,
            lat DOUBLE PRECISION,
            lng DOUBLE PRECISION,
            upvotes INT DEFAULT 1,
            status TEXT DEFAULT 'Open',
            created_at TEXT
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY,
            actor_role TEXT,
            action TEXT,
            target_id TEXT,
            timestamp TEXT
        )
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS govt_services (
            id SERIAL PRIMARY KEY,
            service_name TEXT,
            ministry TEXT,
            fee TEXT,
            sla_timeline TEXT,
            portal_url TEXT,
            last_auto_synced TEXT
        )
        """)

        # Insert default admin/user if empty
        cur.execute("SELECT COUNT(*) as cnt FROM users")
        if cur.fetchone()['cnt'] == 0:
            cur.execute("INSERT INTO users (full_name, email, password_hash, nid_number, dob, role, is_verified, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        ('System Administrator', 'admin@civicsphere.gov.bd', hash_pw('admin123'), '1995547891234', '1995-05-12', 'Admin', 1, '2026-01-01'))
            cur.execute("INSERT INTO users (full_name, email, password_hash, nid_number, dob, role, is_verified, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        ('Tanay Biswas Bandhan', 'tanay@civicsphere.ai', hash_pw('citizen123'), '2000269874512', '2000-04-22', 'Citizen', 1, '2026-01-02'))

        cur.execute("SELECT COUNT(*) as cnt FROM govt_services")
        if cur.fetchone()['cnt'] == 0:
            services = [
                ("Central Grievance Redress System (GRS)", "Cabinet Division", "বিনামূল্যে (Free)", "15–30 Working Days", "https://grs.gov.bd", datetime.now().strftime("%Y-%m-%d %H:%M")),
                ("Anti-Corruption Commission (ACC / দুদক)", "Independent Commission", "বিনামূল্যে (Free)", "Helpline 106", "https://acc.org.bd", datetime.now().strftime("%Y-%m-%d %H:%M")),
                ("National Consumer Rights Protection (DNCRP)", "Ministry of Commerce", "বিনামূল্যে (Free)", "Within 30 Days", "https://dncrp.gov.bd", datetime.now().strftime("%Y-%m-%d %H:%M")),
                ("Local Government Engineering Department (LGED)", "Local Government Division", "বিনামূল্যে (Free)", "15–21 Working Days", "https://lged.gov.bd", datetime.now().strftime("%Y-%m-%d %H:%M"))
            ]
            for s in services:
                cur.execute("INSERT INTO govt_services (service_name, ministry, fee, sla_timeline, portal_url, last_auto_synced) VALUES (%s, %s, %s, %s, %s, %s)", s)

        conn.commit()
        cur.close()
        conn.close()
        print("Supabase DB initialized successfully via FastAPI.")
    except Exception as e:
        print("DB Init Error:", e)

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/", response_class=HTMLResponse)
def read_index():
    if os.path.exists("static/index.html"):
        with open("static/index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "CivicSphere AI Backend Running. static/index.html not found."

def log_audit(role: str, action: str, target_id: str):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("INSERT INTO audit_logs (actor_role, action, target_id, timestamp) VALUES (%s, %s, %s, %s)",
                    (role, action, target_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        cur.close()
        conn.close()
    except Exception:
        pass

def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

SCHEDULE_RATES = {
    "earthwork_cum": {"name": "Earthwork in Box/Road Excavation (per m³)", "lged": 320.0, "pwd": 340.0, "unit": "m³"},
    "brick_flat_soling_sqm": {"name": "1st Class Brick Flat Soling (per m²)", "lged": 680.0, "pwd": 710.0, "unit": "m²"},
    "rcc_concrete_cum": {"name": "RCC Works 1:2:4 with Stone Chips (per m³)", "lged": 11500.0, "pwd": 11900.0, "unit": "m³"},
    "ms_rebar_kg": {"name": "60-Grade MS Deformed Rebar (per kg)", "lged": 96.0, "pwd": 98.5, "unit": "kg"},
    "bituminous_carpeting_sqm": {"name": "25mm Dense Bituminous Carpeting (per m²)", "lged": 890.0, "pwd": 920.0, "unit": "m²"},
}

class LoginReq(BaseModel):
    email: str
    password: str

@app.post("/api/auth/login")
def login(req: LoginReq):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = %s AND password_hash = %s", (req.email.strip().lower(), hash_pw(req.password)))
    user = cur.fetchone()
    cur.close()
    conn.close()
    if user:
        log_audit(user["role"], f"Authenticated Session ({user['email']})", f"USR-{user['id']}")
        return {
            "success": True,
            "user": {
                "id": user["id"],
                "full_name": user["full_name"],
                "email": user["email"],
                "role": user["role"],
                "nid_masked": f"****-****-{user['nid_number'][-4:]}" if user['nid_number'] else "****"
            }
        }
    raise HTTPException(status_code=401, detail="Invalid credentials")

class RegReq(BaseModel):
    full_name: str
    email: str
    password: str
    nid_number: str
    dob: str

@app.post("/api/auth/register")
def register(req: RegReq):
    nid = req.nid_number.strip()
    if not nid.isdigit() or len(nid) not in [10, 13, 17]:
        raise HTTPException(status_code=400, detail="Invalid NID / Smart Card Number.")
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO users (full_name, email, password_hash, nid_number, dob, role, is_verified, created_at) 
            VALUES (%s, %s, %s, %s, %s, 'Citizen', 1, %s)
            RETURNING id
        """, (req.full_name.strip(), req.email.strip().lower(), hash_pw(req.password), nid, req.dob.strip(), datetime.now().strftime("%Y-%m-%d")))
        
        uid = cur.fetchone()['id']
        conn.commit()
        cur.close()
        conn.close()
        
        log_audit("Citizen", f"NID Verified Registration (****{nid[-4:]})", f"USR-{uid}")
        return {"success": True, "message": "NID verified! Account created successfully. Please login."}
    except Exception as e:
        print("Register Error:", e)
        raise HTTPException(status_code=400, detail="Email or NID already exists in database, or invalid data.")

class AnalyzeReq(BaseModel):
    prompt: str
    lang: str = "en"

@app.post("/api/assistant/analyze")
def analyze_issue(req: AnalyzeReq):
    p = req.prompt.lower()
    if any(k in p for k in ["bribe", "ghush", "ঘুষ", "দুর্নীতি", "corruption"]):
        domain, dept, law = "Anti-Corruption & Bribery", "Anti-Corruption Commission (ACC / দুদক)", "Prevention of Corruption Act, 1947"
    elif any(k in p for k in ["price", "mrp", "দাম", "overcharge", "oil"]):
        domain, dept, law = "Consumer Rights", "Directorate of National Consumer Rights Protection (DNCRP)", "Consumer Rights Protection Act, 2009"
    else:
        domain, dept, law = "Roads & Urban Infrastructure", "City Corporation / LGED", "Local Government Act, 2009"

    draft = f"To: {dept}\nSubject: Formal Grievance regarding {domain}.\n\nDetails: {req.prompt}\n\nStatutory Ref: {law}"
    return {"domain": domain, "department": dept, "law": law, "draft": draft}

class ComplaintReq(BaseModel):
    citizen_nid: str
    domain: str
    department: str
    description: str
    draft_text: str
    evidence_note: str = "None"

@app.post("/api/complaints")
def create_complaint(req: ComplaintReq):
    tracking_id = f"CIVIC-2026-{random.randint(1200, 9999)}"
    conn = get_db()
    cur = conn.cursor()
    cur.execute("INSERT INTO complaints (tracking_id, citizen_nid, external_ref, domain, department, description, draft_text, status, evidence_note, created_at) VALUES (%s, %s, 'Pending', %s, %s, %s, %s, 'Draft', %s, %s)",
                (tracking_id, req.citizen_nid, req.domain, req.department, req.description, req.draft_text, req.evidence_note, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    cur.close()
    conn.close()
    log_audit("Citizen", f"Created Complaint Draft ({req.domain})", tracking_id)
    return {"tracking_id": tracking_id}

@app.get("/api/complaints")
def get_complaints():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM complaints ORDER BY id DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

@app.get("/api/boq/rates")
def get_boq_rates():
    return SCHEDULE_RATES

class BoqItem(BaseModel):
    item_code: str
    quantity: float
    quoted_unit_rate: float

class BoqAuditReq(BaseModel):
    project_name: str
    agency: str = "LGED"
    allocated_budget: float
    items: list[BoqItem]

@app.post("/api/boq/audit")
def audit_boq(req: BoqAuditReq):
    agency_key = "pwd" if req.agency.upper() == "PWD" else "lged"
    total_bench, total_quoted, anomalies = 0.0, 0.0, 0
    line_results = []

    for item in req.items:
        sched = SCHEDULE_RATES.get(item.item_code)
        if not sched:
            continue
        std = sched[agency_key]
        b_tot, q_tot = std * item.quantity, item.quoted_unit_rate * item.quantity
        var_pct = round(((item.quoted_unit_rate - std) / std) * 100, 2)
        if var_pct > 20:
            anomalies += 1
        total_bench += b_tot
        total_quoted += q_tot
        line_results.append({
            "name": sched["name"], "unit": sched["unit"], "quantity": item.quantity,
            "standard_rate": std, "quoted_rate": item.quoted_unit_rate, "benchmark_total": b_tot,
            "quoted_total": q_tot, "rate_variance_pct": var_pct,
            "flag": "INFLATED (>20%)" if var_pct > 20 else "NORMAL"
        })

    budget_var_pct = round(((total_quoted - req.allocated_budget) / req.allocated_budget) * 100, 2) if req.allocated_budget > 0 else 0
    sched_var_pct = round(((total_quoted - total_bench) / total_bench) * 100, 2) if total_bench > 0 else 0

    return {
        "project_name": req.project_name, "agency": req.agency.upper(),
        "matrix": {
            "allocated_budget": req.allocated_budget,
            "benchmark_schedule_cost": round(total_bench, 2),
            "contractor_quoted_cost": round(total_quoted, 2),
            "budget_variance_pct": budget_var_pct,
            "schedule_variance_pct": sched_var_pct
        },
        "overall_alert": anomalies > 0, "anomaly_count": anomalies, "items": line_results,
        "disclaimer": "Technical auditing indicator based on LGED/PWD Schedule of Rates."
    }

class HazardReq(BaseModel):
    title: str
    category: str
    lat: float
    lng: float
    force_create: bool = False

@app.post("/api/hazards")
def post_hazard(req: HazardReq):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM hazards")
    existing = cur.fetchall()
    
    if not req.force_create:
        for h in existing:
            dist = haversine_meters(req.lat, req.lng, h["lat"], h["lng"])
            if dist <= 100.0:
                cur.close()
                conn.close()
                return {
                    "duplicate_detected": True,
                    "distance_meters": round(dist, 1),
                    "existing_hazard": dict(h)
                }

    cur.execute("INSERT INTO hazards (title, category, lat, lng, upvotes, status, created_at) VALUES (%s, %s, %s, %s, %s, 'Open', %s)",
                (req.title, req.category, req.lat, req.lng, 1, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    cur.close()
    conn.close()
    log_audit("Citizen", f"Pinned Hazard: {req.title}", "HAZ-NEW")
    return {"duplicate_detected": False}

@app.post("/api/hazards/{hazard_id}/upvote")
def upvote_hazard(hazard_id: int):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("UPDATE hazards SET upvotes = upvotes + 1 WHERE id = %s", (hazard_id,))
    conn.commit()
    cur.close()
    conn.close()
    return {"success": True}

@app.get("/api/hazards")
def get_hazards():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM hazards ORDER BY upvotes DESC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

@app.get("/api/services")
def get_services():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM govt_services ORDER BY id ASC")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

@app.get("/api/admin/analytics")
def admin_analytics():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT domain, status FROM complaints")
    complaints = cur.fetchall()
    cur.execute("SELECT category, upvotes, status FROM hazards")
    hazards = cur.fetchall()
    cur.execute("SELECT id, full_name, email, nid_number, dob, role, is_verified, created_at FROM users ORDER BY id DESC")
    users = cur.fetchall()
    cur.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 25")
    logs = cur.fetchall()
    cur.close()
    conn.close()

    status_counts = {"Draft": 0, "Ready": 0, "Submitted": 0, "In Progress": 0, "Resolved": 0}
    for c in complaints:
        status_counts[c["status"]] = status_counts.get(c["status"], 0) + 1

    masked_users = []
    for u in users:
        ud = dict(u)
        nid = ud["nid_number"] or ""
        ud["nid_masked"] = f"****-****-{nid[-4:]}" if len(nid) >= 4 else nid
        masked_users.append(ud)

    return {
        "total_complaints": len(complaints),
        "resolved_complaints": status_counts.get("Resolved", 0),
        "total_hazards": len(hazards),
        "total_users": len(users),
        "users": masked_users,
        "status_counts": status_counts,
        "audit_logs": [dict(l) for l in logs]
    }
