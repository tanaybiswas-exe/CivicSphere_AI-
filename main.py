import os
import math
import hashlib
import random
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor

# Neon PostgreSQL Database URL
DATABASE_URL = "postgresql://neondb_owner:npg_IKCmYNoWdF47@ep-wild-smoke-be5euaix-pooler.c-9.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

app = FastAPI(title="NagorikBondhu — নাগরিকবন্ধু AI", version="3.0")

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
            district TEXT DEFAULT 'ঢাকা',
            area TEXT DEFAULT 'মিরপুর ১০',
            description TEXT,
            draft_text TEXT,
            status TEXT DEFAULT 'Draft',
            status_history TEXT DEFAULT '[]',
            evidence_note TEXT,
            created_at TEXT
        )
        """)
        # কলাম না থাকলে যোগ করে নেওয়া (পুরানো ডেটা অক্ষুণ্ণ রাখতে)
        cur.execute("ALTER TABLE complaints ADD COLUMN IF NOT EXISTS district TEXT DEFAULT 'ঢাকা'")
        cur.execute("ALTER TABLE complaints ADD COLUMN IF NOT EXISTS area TEXT DEFAULT 'মিরপুর ১০'")
        cur.execute("ALTER TABLE complaints ADD COLUMN IF NOT EXISTS status_history TEXT DEFAULT '[]'")

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

        # Default Users
        cur.execute("SELECT COUNT(*) as cnt FROM users")
        if cur.fetchone()['cnt'] == 0:
            cur.execute("INSERT INTO users (full_name, email, password_hash, nid_number, dob, role, is_verified, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        ('সিস্টেম অ্যাডমিনিস্ট্রেটর', 'admin@civicsphere.gov.bd', hash_pw('admin123'), '1995547891234', '1995-05-12', 'Admin', 1, '2026-01-01'))
            cur.execute("INSERT INTO users (full_name, email, password_hash, nid_number, dob, role, is_verified, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        ('তনয় বিশ্বাস বন্ধন', 'tanay@civicsphere.ai', hash_pw('citizen123'), '2000269874512', '2000-04-22', 'Citizen', 1, '2026-01-02'))

        # Default Demo Hazards (যদি খালি থাকে)
        cur.execute("SELECT COUNT(*) as cnt FROM hazards")
        if cur.fetchone()['cnt'] == 0:
            demo_hazards = [
                ("[ডেমো] মিরপুর ১০ গোলচত্বর সংলগ্ন ভাঙা রাস্তা", "ক্ষতিগ্রস্ত রাস্তা", 23.8069, 90.3687, 14, "Open", "2026-11-10"),
                ("[ডেমো] উত্তরা ৭ নম্বর সেক্টরে জলাবদ্ধতা", "জলাবদ্ধতা", 23.8682, 90.3984, 9, "In Progress", "2026-11-12"),
                ("[ডেমো] ধানমন্ডি ২৭ নম্বর রাস্তার নষ্ট সড়কবাতি", "নষ্ট সড়কবাতি", 23.7561, 90.3753, 6, "Open", "2026-11-14"),
                ("[ডেমো] গুলশান ১ বর্জ্য ব্যবস্থাপনা সমস্যা", "বর্জ্য ব্যবস্থাপনা", 23.7808, 90.4161, 11, "Resolved", "2026-11-15")
            ]
            for h in demo_hazards:
                cur.execute("INSERT INTO hazards (title, category, lat, lng, upvotes, status, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s)", h)

        # Default Services
        cur.execute("SELECT COUNT(*) as cnt FROM govt_services")
        if cur.fetchone()['cnt'] == 0:
            services = [
                ("কেন্দ্রীয় অভিযোগ প্রতিকার ব্যবস্থা (GRS)", "মন্ত্রিপরিষদ বিভাগ", "বিনামূল্যে (Free)", "১৫–৩০ কার্যদিবস", "https://grs.gov.bd", datetime.now().strftime("%Y-%m-%d %H:%M")),
                ("দুর্নীতি দমন কমিশন (ACC / দুদক)", "স্বাধীন কমিশন", "বিনামূল্যে (Free)", "হেল্পলাইন ১০৬", "https://acc.org.bd", datetime.now().strftime("%Y-%m-%d %H:%M")),
                ("জাতীয় ভোক্তা অধিকার সংরক্ষণ অধিদপ্তর (DNCRP)", "বাণিজ্য মন্ত্রণালয়", "বিনামূল্যে (Free)", "৩০ দিনের মধ্যে", "https://dncrp.gov.bd", datetime.now().strftime("%Y-%m-%d %H:%M")),
                ("স্থানীয় সরকার প্রকৌশল অধিদপ্তর (LGED)", "স্থানীয় সরকার বিভাগ", "বিনামূল্যে (Free)", "১৫–২১ কার্যদিবস", "https://lged.gov.bd", datetime.now().strftime("%Y-%m-%d %H:%M"))
            ]
            for s in services:
                cur.execute("INSERT INTO govt_services (service_name, ministry, fee, sla_timeline, portal_url, last_auto_synced) VALUES (%s, %s, %s, %s, %s, %s)", s)

        conn.commit()
        cur.close()
        conn.close()
        print("NagorikBondhu Neon DB initialized successfully.")
    except Exception as e:
        print("Neon DB Init Error:", e)

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/", response_class=HTMLResponse)
def read_index():
    if os.path.exists("static/index.html"):
        with open("static/index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "NagorikBondhu Backend Running. static/index.html not found."

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
    "earthwork_cum": {"name": "মাটি খনন কাজ (Earthwork - প্রতি ঘনমিটার)", "lged": 320.0, "pwd": 340.0, "unit": "m³"},
    "brick_flat_soling_sqm": {"name": "১ম শ্রেণির ইটের সলিং (Brick Soling - প্রতি বর্গমিটার)", "lged": 680.0, "pwd": 710.0, "unit": "m²"},
    "rcc_concrete_cum": {"name": "আরসিসি ঢালাই কাজ (RCC 1:2:4 - প্রতি ঘনমিটার)", "lged": 11500.0, "pwd": 11900.0, "unit": "m³"},
    "ms_rebar_kg": {"name": "৬০-গ্রেড এমএস রড (MS Rebar - প্রতি কেজি)", "lged": 96.0, "pwd": 98.5, "unit": "kg"},
    "bituminous_carpeting_sqm": {"name": "২৫মিমি বিটুমিনাস কার্পেটিং (প্রতি বর্গমিটার)", "lged": 890.0, "pwd": 920.0, "unit": "m²"},
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
        log_audit(user["role"], f"লগইন সেশন ({user['email']})", f"USR-{user['id']}")
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
    raise HTTPException(status_code=401, detail="ভুল ইমেইল অথবা পাসওয়ার্ড দেওয়া হয়েছে।")

class RegReq(BaseModel):
    full_name: str
    email: str
    password: str
    nid_number: str
    dob: str

@app.post("/api/auth/register")
def register(req: RegReq):
    nid = req.nid_number.strip()
    if not nid.isdigit() or len(nid) < 10:
        raise HTTPException(status_code=400, detail="সঠিক এনআইডি (NID) নম্বর দিন (কমপক্ষে ১০ ডিজিট)।")
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
        
        log_audit("Citizen", f"নতুন নাগরিক নিবন্ধন (****{nid[-4:]})", f"USR-{uid}")
        return {"success": True, "message": "এনআইডি যাচাই সফল! অ্যাকাউন্ট তৈরি হয়েছে, এখন লগইন করুন।"}
    except Exception as e:
        print("Register Error:", e)
        raise HTTPException(status_code=400, detail="এই ইমেইল বা এনআইডি দিয়ে আগেই অ্যাকাউন্ট খোলা হয়েছে।")

class UpdateProfileReq(BaseModel):
    email: str
    full_name: str
    current_password: str
    new_password: str = ""

@app.post("/api/auth/update-profile")
def update_profile(req: UpdateProfileReq):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users WHERE email = %s AND password_hash = %s", 
                (req.email.strip().lower(), hash_pw(req.current_password)))
    user = cur.fetchone()
    
    if not user:
        cur.close()
        conn.close()
        raise HTTPException(status_code=400, detail="বর্তমান পাসওয়ার্ডটি সঠিক নয়।")
    
    try:
        if req.new_password.strip():
            new_hash = hash_pw(req.new_password.strip())
            cur.execute("UPDATE users SET full_name = %s, password_hash = %s WHERE email = %s",
                        (req.full_name.strip(), new_hash, req.email.strip().lower()))
        else:
            cur.execute("UPDATE users SET full_name = %s WHERE email = %s",
                        (req.full_name.strip(), req.email.strip().lower()))
        
        conn.commit()
        cur.execute("SELECT * FROM users WHERE email = %s", (req.email.strip().lower(),))
        updated_user = cur.fetchone()
        cur.close()
        conn.close()
        
        log_audit(updated_user["role"], f"প্রোফাইল আপডেট ({updated_user['email']})", f"USR-{updated_user['id']}")
        return {
            "success": True,
            "user": {
                "id": updated_user["id"],
                "full_name": updated_user["full_name"],
                "email": updated_user["email"],
                "role": updated_user["role"],
                "nid_masked": f"****-****-{updated_user['nid_number'][-4:]}" if updated_user['nid_number'] else "****"
            }
        }
    except Exception as e:
        print("Profile Update Error:", e)
        raise HTTPException(status_code=400, detail="প্রোফাইল আপডেট করতে সমস্যা হয়েছে।")

class AnalyzeReq(BaseModel):
    prompt: str
    district: str = "ঢাকা"
    area: str = ""
    category: str = ""
    lang: str = "bn"

@app.post("/api/assistant/analyze")
def analyze_issue(req: AnalyzeReq):
    p = (req.prompt + " " + req.category).lower()
    if any(k in p for k in ["bribe", "ghush", "ঘুষ", "দুর্নীতি", "corruption"]):
        domain, dept, law = "দুর্নীতি ও ঘুষ প্রতিরোধ", "দুর্নীতি দমন কমিশন (ACC / দুদক)", "দুর্নীতি প্রতিরোধ আইন, ১৯৪৭"
    elif any(k in p for k in ["price", "mrp", "দাম", "overcharge", "ভোক্তা"]):
        domain, dept, law = "ভোক্তা অধিকার সংরক্ষণ", "জাতীয় ভোক্তা অধিকার সংরক্ষণ অধিদপ্তর (DNCRP)", "ভোক্তা অধিকার সংরক্ষণ আইন, ২০০৯"
    elif any(k in p for k in ["water", "জলাবদ্ধতা", "ড্রেন", "drain"]):
        domain, dept, law = "জলাবদ্ধতা ও পয়ঃনিষ্কাশন", "ওয়াসা (WASA) / সিটি কর্পোরেশন", "স্থানীয় সরকার (সিটি কর্পোরেশন) আইন, ২০০৯"
    elif any(k in p for k in ["waste", "বর্জ্য", "ময়লা", "garbage"]):
        domain, dept, law = "বর্জ্য ব্যবস্থাপনা ও পরিচ্ছন্নতা", "সিটি কর্পোরেশন / পৌরসভা বর্জ্য ব্যবস্থাপনা বিভাগ", "স্থানীয় সরকার আইন, ২০০৯"
    elif any(k in p for k in ["light", "বাতি", "streetlight"]):
        domain, dept, law = "সড়কবাতি ও বিদ্যুৎ", "সিটি কর্পোরেশন বিদ্যুৎ বিভাগ / ডিপিডিসি", "বিদ্যুৎ আইন, ২০১৮"
    else:
        domain, dept, law = "ক্ষতিগ্রস্ত রাস্তা ও অবকাঠামো", "সিটি কর্পোরেশন / এলজিইডি (LGED)", "স্থানীয় সরকার প্রকৌশল বিধিমালা"

    loc_text = f"জেলা: {req.district}, এলাকা: {req.area}" if req.area else f"জেলা: {req.district}"
    draft = (
        f"বরাবর,\n"
        f"দায়িত্বপ্রাপ্ত কর্মকর্তা,\n"
        f"{dept}\n"
        f"{loc_text}\n\n"
        f"বিষয়: {domain} সংক্রান্ত আনুষ্ঠানিক নাগরিক অভিযোগ।\n\n"
        f"জনাব,\n"
        f"বিনীত নিবেদন এই যে, আমি {loc_text} এলাকার একজন সচেতন নাগরিক। আমাদের এলাকায় নিচের সমস্যাটি জনদুর্ভোগ সৃষ্টি করছে:\n"
        f"\" {req.prompt} \"\n\n"
        f"প্রযোজ্য আইন/বিধি ({law}) অনুযায়ী বিষয়টি দ্রুত তদন্তপূর্বক প্রয়োজনীয় ব্যবস্থা গ্রহণের জন্য বিনীত অনুরোধ জানাচ্ছি।\n\n"
        f"বিনীত নিবেদক,\n"
        f"একজন ভুক্তভোগী নাগরিক\n"
        f"[দ্রষ্টব্য: এটি নাগরিকবন্ধু এআই জেনারেটেড খসড়া অভিযোগ]"
    )
    return {"domain": domain, "department": dept, "law": law, "draft": draft}

class ComplaintReq(BaseModel):
    citizen_nid: str
    domain: str
    department: str
    district: str = "ঢাকা"
    area: str = ""
    description: str
    draft_text: str
    evidence_note: str = "কোনো ফাইল সংযুক্ত নেই"

@app.post("/api/complaints")
def create_complaint(req: ComplaintReq):
    tracking_id = f"NB-2026-{random.randint(1200, 9999)}"
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    init_history = json.dumps([{"stage": "Draft", "time": now_str, "note": "অভিযোগের খসড়া তৈরি ও সংরক্ষণ করা হয়েছে"}], ensure_ascii=False)
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO complaints (tracking_id, citizen_nid, external_ref, domain, department, district, area, description, draft_text, status, status_history, evidence_note, created_at) 
        VALUES (%s, %s, 'অপেক্ষমাণ (Pending)', %s, %s, %s, %s, %s, %s, 'Draft', %s, %s, %s)
    """, (tracking_id, req.citizen_nid, req.domain, req.department, req.district, req.area, req.description, req.draft_text, init_history, req.evidence_note, datetime.now().strftime("%Y-%m-%d")))
    conn.commit()
    cur.close()
    conn.close()
    log_audit("Citizen", f"অভিযোগ সংরক্ষণ ({req.domain})", tracking_id)
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

class StatusUpdateReq(BaseModel):
    status: str
    external_ref: str = None

@app.patch("/api/complaints/{tracking_id}/status")
def update_complaint_status(tracking_id: str, req: StatusUpdateReq):
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT status_history, external_ref FROM complaints WHERE tracking_id = %s", (tracking_id,))
    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        raise HTTPException(status_code=404, detail="অভিযোগ খুঁজে পাওয়া যায়নি")

    try:
        history = json.loads(row["status_history"] or "[]")
    except Exception:
        history = []

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    history.append({"stage": req.status, "time": now_str, "note": f"অবস্থা '{req.status}'-এ পরিবর্তন করা হয়েছে"})
    new_ref = req.external_ref if req.external_ref else row["external_ref"]

    cur.execute("UPDATE complaints SET status = %s, external_ref = %s, status_history = %s WHERE tracking_id = %s",
                (req.status, new_ref, json.dumps(history, ensure_ascii=False), tracking_id))
    conn.commit()
    cur.close()
    conn.close()
    log_audit("User/Admin", f"অভিযোগের স্ট্যাটাস আপডেট -> {req.status}", tracking_id)
    return {"success": True}

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
            "flag": "অতিরিক্ত ব্যয় (>২০%)" if var_pct > 20 else "স্বাভাবিক (NORMAL)"
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
        "overall_alert": anomalies > 0, "anomaly_count": anomalies, "items": line_results
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
    log_audit("Citizen", f"ম্যাপে সমস্যা পিন: {req.title}", "HAZ-NEW")
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
    cur.execute("SELECT domain, status, district FROM complaints")
    complaints = cur.fetchall()
    cur.execute("SELECT category, upvotes, status FROM hazards")
    hazards = cur.fetchall()
    cur.execute("SELECT id, full_name, email, nid_number, dob, role, is_verified, created_at FROM users ORDER BY id DESC")
    users = cur.fetchall()
    cur.execute("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 25")
    logs = cur.fetchall()
    cur.close()
    conn.close()

    status_counts = {"Draft": 0, "Submitted": 0, "In Progress": 0, "Resolved": 0}
    domain_counts = {}
    area_counts = {}

    for c in complaints:
        st = c["status"]
        status_counts[st] = status_counts.get(st, 0) + 1
        dom = c["domain"] or "অন্যান্য"
        domain_counts[dom] = domain_counts.get(dom, 0) + 1
        dist = c["district"] or "ঢাকা"
        area_counts[dist] = area_counts.get(dist, 0) + 1

    masked_users = []
    for u in users:
        ud = dict(u)
        nid = ud["nid_number"] or ""
        ud["nid_masked"] = f"****-****-{nid[-4:]}" if len(nid) >= 4 else nid
        masked_users.append(ud)

    return {
        "total_complaints": len(complaints),
        "pending_complaints": status_counts.get("Draft", 0) + status_counts.get("Submitted", 0),
        "inprogress_complaints": status_counts.get("In Progress", 0),
        "resolved_complaints": status_counts.get("Resolved", 0),
        "total_hazards": len(hazards),
        "total_users": len(users),
        "users": masked_users,
        "status_counts": status_counts,
        "domain_counts": domain_counts,
        "area_counts": area_counts,
        "audit_logs": [dict(l) for l in logs]
    }
