import sqlite3
import json
import hashlib
import os
from pathlib import Path

DB = Path(__file__).parent / "sdr_agent.db"

def conn():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init():
    with conn() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS seller_profiles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT NOT NULL,
            label       TEXT NOT NULL,
            name        TEXT NOT NULL,
            company     TEXT NOT NULL,
            product     TEXT NOT NULL,
            value_prop  TEXT DEFAULT '',
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS demo_visits (
            ip    TEXT PRIMARY KEY,
            uses  INTEGER DEFAULT 0,
            last_visit TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS kits (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            username        TEXT NOT NULL,
            prospect_name   TEXT,
            prospect_co     TEXT,
            prospect_role   TEXT,
            prospect_sector TEXT,
            seller_name     TEXT,
            seller_co       TEXT,
            kit_json        TEXT,
            tone            TEXT,
            language        TEXT,
            elapsed         REAL DEFAULT 0,
            q_score         INTEGER,
            q_strong        TEXT,
            q_improve       TEXT,
            generated_at    TEXT DEFAULT (datetime('now'))
        );
        """)

# ── Demo visits (IP stored as one-way hash — GDPR compliant) ─────────────

_IP_SALT = os.getenv("IP_HASH_SALT", "sdr_default_salt_2025")

def _hash_ip(ip: str) -> str:
    return hashlib.sha256(f"{_IP_SALT}:{ip}".encode()).hexdigest()

def get_demo_uses(ip):
    hashed = _hash_ip(ip)
    with conn() as c:
        r = c.execute("SELECT uses FROM demo_visits WHERE ip=?", (hashed,)).fetchone()
        return r["uses"] if r else 0

def increment_demo_uses(ip):
    hashed = _hash_ip(ip)
    with conn() as c:
        c.execute("""
            INSERT INTO demo_visits (ip, uses, last_visit) VALUES (?, 1, datetime('now'))
            ON CONFLICT(ip) DO UPDATE SET uses = uses + 1, last_visit = datetime('now')
        """, (hashed,))
        r = c.execute("SELECT uses FROM demo_visits WHERE ip=?", (hashed,)).fetchone()
        return r["uses"] if r else 1

def purge_old_demo_visits(days=30):
    with conn() as c:
        c.execute("DELETE FROM demo_visits WHERE datetime(last_visit) < datetime('now', ?)", (f"-{int(days)} days",))

# ── Seller profiles ──────────────────────────────────────

def save_profile(username, label, name, company, product, value_prop=""):
    with conn() as c:
        c.execute(
            "INSERT INTO seller_profiles (username,label,name,company,product,value_prop) VALUES (?,?,?,?,?,?)",
            (username, label, name, company, product, value_prop)
        )

def get_profiles(username):
    with conn() as c:
        return [dict(r) for r in c.execute(
            "SELECT * FROM seller_profiles WHERE username=? ORDER BY created_at DESC", (username,)
        ).fetchall()]

def delete_profile(pid):
    with conn() as c:
        c.execute("DELETE FROM seller_profiles WHERE id=?", (pid,))

# ── Kits ─────────────────────────────────────────────────

def save_kit(username, meta, kit, elapsed=0, q_score=None, q_strong=None, q_improve=None):
    with conn() as c:
        cur = c.execute("""
        INSERT INTO kits
          (username,prospect_name,prospect_co,prospect_role,prospect_sector,
           seller_name,seller_co,kit_json,tone,language,elapsed,q_score,q_strong,q_improve)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            username,
            meta.get("prospect"), meta.get("azienda"), meta.get("ruolo"), meta.get("settore",""),
            meta.get("sn"), meta.get("sc"),
            json.dumps(kit, ensure_ascii=False),
            meta.get("tone",""), meta.get("lang",""),
            elapsed, q_score, q_strong, q_improve
        ))
        return cur.lastrowid

def get_history(username, limit=60):
    with conn() as c:
        rows = c.execute(
            "SELECT * FROM kits WHERE username=? ORDER BY generated_at DESC LIMIT ?",
            (username, limit)
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["kit"] = json.loads(d.pop("kit_json"))
        result.append(d)
    return result

def get_kit(kid):
    with conn() as c:
        r = c.execute("SELECT * FROM kits WHERE id=?", (kid,)).fetchone()
    if r:
        d = dict(r)
        d["kit"] = json.loads(d.pop("kit_json"))
        return d
    return None

def delete_kit(kid, username):
    with conn() as c:
        c.execute("DELETE FROM kits WHERE id=? AND username=?", (kid, username))

def purge_old_kits(days=365):
    with conn() as c:
        c.execute("DELETE FROM kits WHERE datetime(generated_at) < datetime('now', ?)", (f"-{int(days)} days",))
