import streamlit as st
import anthropic
import yaml
import json
import csv
import io
import os
import time
import zipfile
import urllib.parse
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

load_dotenv(Path(__file__).parent.parent / ".env")
import db
import apollo
import re as _re
db.init()
db.purge_old_kits(int(os.getenv("DATA_RETENTION_DAYS", "365")))
db.purge_old_demo_visits(30)

DEMO_MODE      = os.getenv("DEMO_MODE", "false").lower() == "true"
DEMO_MAX_USES  = int(os.getenv("DEMO_MAX_USES", "2"))
CONTACT_NAME   = os.getenv("CONTACT_NAME", "Gianmarco")
CONTACT_EMAIL  = os.getenv("CONTACT_EMAIL", "gianmarco.milocco@gmail.com")
CONTACT_PHONE  = os.getenv("CONTACT_PHONE", "")

st.set_page_config(
    page_title="AI SDR Agent — Enterprise",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ════════════════════════════════════════════════════════
# CSS
# ════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap');

/* ── Reset & base ── */
*, *::before, *::after {
    font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    box-sizing: border-box;
}
#MainMenu, footer, header,
[data-testid="stDecoration"], [data-testid="stToolbar"],
div[data-testid="stStatusWidget"] { display: none !important; }
.block-container { padding: 1.8rem 2.4rem 3rem !important; max-width: 1480px !important; }
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 8px; }

/* ── Palette ── */
[data-testid="stAppViewContainer"] { background: #f5f5f7 !important; }
[data-testid="stSidebar"] { background: #0d0f14 !important; border-right: none !important; }
[data-testid="stSidebar"] * { color: rgba(255,255,255,.8) !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.07) !important; }

/* ── Header ── */
.sdr-header {
    background: #0d0f14; border-radius: 10px;
    padding: 2rem 2.6rem 1.8rem; color: #fff;
    margin-bottom: 1.8rem;
}
.sdr-title { font-size: 1.75rem; font-weight: 700; letter-spacing: -.025em; margin: 0; color: #fff; }
.sdr-sub   { font-size: .88rem; color: rgba(255,255,255,.42); margin: .5rem 0 0; font-weight: 400; }
.badge-ent {
    font-size: .57rem; font-weight: 600; letter-spacing: 1.6px; text-transform: uppercase;
    border: 1px solid rgba(255,255,255,.18); color: rgba(255,255,255,.5);
    padding: 3px 8px; border-radius: 3px; margin-left: 10px; vertical-align: middle;
}
.hdr-metrics { display: flex; gap: 0; margin-top: 1.5rem; padding-top: 1.4rem; border-top: 1px solid rgba(255,255,255,.06); }
.hdr-m { padding-right: 2rem; margin-right: 2rem; border-right: 1px solid rgba(255,255,255,.06); }
.hdr-m:last-child { border-right: none; }
.hdr-m .v { font-size: 1.35rem; font-weight: 700; color: #fff; display: block; line-height: 1; }
.hdr-m .l { font-size: .67rem; color: rgba(255,255,255,.35); display: block; margin-top: 4px; letter-spacing: .3px; }

/* ── Typography ── */
.sec-label  { font-size: .65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1.1px; color: #9ca3af; margin: 0 0 .5rem; }
.page-title { font-size: 1.25rem; font-weight: 700; color: #111318; margin: 0 0 1.4rem; letter-spacing: -.02em; }
.c-label    { font-size: .65rem; font-weight: 700; text-transform: uppercase; letter-spacing: .9px; color: #9ca3af; margin-bottom: .35rem; }
.kit-name   { font-size: .92rem; font-weight: 700; color: #111318; }
.kit-meta   { font-size: .74rem; color: #9ca3af; margin-top: 1px; }

/* ── Cards & containers ── */
.stats-bar { display: flex; background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; margin-bottom: 1.2rem; }
.stat-item { flex: 1; padding: .75rem 1rem; border-right: 1px solid #e5e7eb; text-align: center; }
.stat-item:last-child { border-right: none; }
.stat-item .sv { display: block; font-size: 1.2rem; font-weight: 700; color: #111318; line-height: 1; }
.stat-item .sl { display: block; font-size: .65rem; color: #9ca3af; margin-top: 4px; font-weight: 500; }

.q-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: .9rem 1.1rem; margin-bottom: 1rem; display: flex; align-items: center; gap: 1.2rem; }
.q-score { font-size: 1.8rem; font-weight: 800; color: #111318; min-width: 46px; text-align: center; }
.q-score.good { color: #111318; }
.q-score.ok   { color: #6b7280; }
.q-score.poor { color: #dc2626; }
.q-details p  { margin: 0; font-size: .82rem; color: #4b5563; line-height: 1.5; }
.q-details .ql { font-size: .67rem; font-weight: 700; text-transform: uppercase; letter-spacing: .8px; color: #9ca3af; margin-bottom: 2px; }

.feat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: .65rem; margin-top: .9rem; }
.feat-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 8px; padding: 1rem 1.1rem; }
.feat-card .ic { font-size: 1rem; margin-bottom: .35rem; display: block; }
.feat-card .tt { font-size: .84rem; font-weight: 700; color: #111318; }
.feat-card .dd { font-size: .75rem; color: #6b7280; margin-top: .1rem; line-height: 1.5; }

/* ── Inputs ── */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    border-radius: 6px !important; border: 1px solid #d1d5db !important;
    background: #fff !important; font-size: .875rem !important; color: #111318 !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #1d4ed8 !important;
    box-shadow: 0 0 0 3px rgba(29,78,216,.08) !important; outline: none !important;
}
.stTextInput > label, .stTextArea > label, .stSelectbox > label {
    font-size: .74rem !important; font-weight: 600 !important; color: #4b5563 !important;
}

/* ── Buttons ── */
.stButton > button[kind="primary"] {
    background: #111318 !important; border: none !important; border-radius: 6px !important;
    font-size: .88rem !important; font-weight: 600 !important; color: #fff !important;
    box-shadow: none !important;
}
.stButton > button[kind="primary"]:hover { background: #1d4ed8 !important; }
.stButton > button:not([kind="primary"]) {
    background: #fff !important; border: 1px solid #e5e7eb !important;
    border-radius: 6px !important; color: #374151 !important;
    font-weight: 600 !important; font-size: .82rem !important;
}
.stButton > button:not([kind="primary"]):hover { border-color: #111318 !important; color: #111318 !important; }
.stDownloadButton > button {
    background: #fff !important; border: 1px solid #e5e7eb !important;
    color: #374151 !important; border-radius: 6px !important; font-weight: 600 !important;
}
.stDownloadButton > button:hover { background: #111318 !important; color: #fff !important; border-color: #111318 !important; }

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 1px !important; background: #ebebed !important;
    padding: 3px !important; border-radius: 7px !important; border-bottom: none !important;
}
.stTabs [data-baseweb="tab"] { border-radius: 5px !important; font-weight: 500 !important; font-size: .81rem !important; padding: 5px 13px !important; color: #6b7280 !important; }
.stTabs [aria-selected="true"] { background: #fff !important; color: #111318 !important; font-weight: 700 !important; box-shadow: 0 1px 2px rgba(0,0,0,.06) !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top: .9rem !important; }

/* ── History table ── */
.hist-table { width: 100%; border-collapse: collapse; font-size: .82rem; }
.hist-table th { text-align: left; padding: .5rem .8rem; background: #f5f5f7; color: #6b7280; font-size: .67rem; font-weight: 700; text-transform: uppercase; letter-spacing: .8px; border-bottom: 1px solid #e5e7eb; }
.hist-table td { padding: .6rem .8rem; border-bottom: 1px solid #f3f4f6; color: #111318; vertical-align: middle; }
.hist-table tr:last-child td { border-bottom: none; }
.score-pill { display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: .71rem; font-weight: 700; }
.sc-good { background: #f3f4f6; color: #111318; }
.sc-ok   { background: #f3f4f6; color: #6b7280; }
.sc-poor { background: #fee2e2; color: #991b1b; }

/* ── Alerts ── */
hr { border-color: #e5e7eb !important; margin: 1rem 0 !important; }
[data-testid="stInfo"]    { background: #f9fafb !important; border: 1px solid #e5e7eb !important; border-radius: 6px !important; }
[data-testid="stInfo"] p  { color: #374151 !important; font-size: .82rem !important; }
[data-testid="stSuccess"] { border-radius: 6px !important; }
[data-testid="stAlert"]   { border-radius: 6px !important; }
[data-testid="stWarning"] { border-radius: 6px !important; }

/* ── Email subject ── */
.email-subject-box {
    background: #f9fafb; border: 1px solid #e5e7eb;
    border-radius: 6px; padding: .5rem 1rem;
    margin-bottom: .6rem; display: flex; align-items: baseline; gap: .5rem;
}
.email-subject-label { font-size: .63rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #9ca3af; white-space: nowrap; }
.email-subject-text  { font-size: .88rem; font-weight: 600; color: #111318; }

/* ── Char bar ── */
.char-bar-bg { background: #e5e7eb; border-radius: 4px; height: 3px; margin-top: .3rem; overflow: hidden; }
.char-bar-fill { height: 3px; border-radius: 4px; }

/* ── Trigger Intelligence ── */
.trigger-row { display:flex; flex-wrap:wrap; gap:.35rem; margin-bottom:.8rem; }
.trigger-pill {
    display:inline-flex; align-items:center; gap:.3rem;
    padding:3px 9px; border-radius:4px; font-size:.71rem; font-weight:600;
    background:#f3f4f6; color:#374151; border:1px solid #e5e7eb;
}
.tp-urgenza { display:inline-block; width:6px; height:6px; border-radius:50%; flex-shrink:0; }

/* ── Subject variants ── */
.subj-row {
    display:flex; align-items:center; justify-content:space-between;
    padding:.6rem .85rem; background:#fff; border:1px solid #e5e7eb;
    border-radius:6px; margin-bottom:.35rem; gap:.8rem;
}
.subj-text  { font-size:.87rem; color:#111318; font-weight:500; flex:1; }
.subj-meta  { font-size:.69rem; color:#9ca3af; margin-top:2px; }
.subj-score { font-size:.95rem; font-weight:800; min-width:28px; text-align:center; color:#111318; }
.subj-angolo {
    font-size:.62rem; font-weight:700; text-transform:uppercase;
    letter-spacing:.7px; padding:2px 6px; border-radius:3px; white-space:nowrap;
    background:#f3f4f6; color:#6b7280;
}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
# AUTH
# ════════════════════════════════════════════════════════
if DEMO_MODE:
    username     = "demo_visitor"
    user_display = "Demo"
    # Ricava IP visitatore per tracking persistente
    try:
        fwd = st.context.headers.get("X-Forwarded-For", "")
        _visitor_ip = fwd.split(",")[0].strip() if fwd else st.context.headers.get("X-Real-Ip", "local")
    except Exception:
        _visitor_ip = "local"
    if "demo_ip" not in st.session_state:
        st.session_state.demo_ip   = _visitor_ip
        st.session_state.demo_uses = db.get_demo_uses(_visitor_ip)
else:
    _admin_hash = os.getenv("ADMIN_PASSWORD_HASH", "")
    _admin_user = os.getenv("ADMIN_USERNAME", "admin")
    _cookie_key = os.getenv("AUTH_COOKIE_KEY", "")
    if _admin_hash and _cookie_key:
        cfg = {
            "credentials": {
                "usernames": {
                    _admin_user: {
                        "email": f"{_admin_user}@sdragent.io",
                        "name": _admin_user.title(),
                        "password": _admin_hash,
                    }
                }
            },
            "cookie": {"name": "sdr_agent_auth", "key": _cookie_key, "expiry_days": 7},
        }
    else:
        cfg_path = Path(__file__).parent / "auth_config.yaml"
        with open(cfg_path) as f:
            cfg = yaml.load(f, Loader=SafeLoader)

    authenticator = stauth.Authenticate(
        cfg["credentials"], cfg["cookie"]["name"],
        cfg["cookie"]["key"], cfg["cookie"]["expiry_days"]
    )
    authenticator.login()

    status = st.session_state.get("authentication_status")
    if status is False:
        st.error("Username o password non corretti.")
        st.stop()
    if status is None:
        st.markdown("""
        <div style="max-width:400px;margin:4rem auto;text-align:center">
          <p style="font-size:2rem;margin-bottom:.5rem">🎯</p>
          <h2 style="font-size:1.4rem;font-weight:700;color:#0f172a;margin-bottom:.3rem">AI SDR Agent</h2>
          <p style="color:#64748b;font-size:.88rem">Accedi con le credenziali fornite</p>
        </div>
        """, unsafe_allow_html=True)
        st.stop()

    username     = st.session_state.get("username", "")
    user_display = st.session_state.get("name", username)

client = anthropic.Anthropic()

# ════════════════════════════════════════════════════════
# SIDEBAR
# ════════════════════════════════════════════════════════
with st.sidebar:
    if DEMO_MODE:
        remaining = max(0, DEMO_MAX_USES - st.session_state.get("demo_uses", 0))
        st.markdown(
            f"<p style='font-size:.8rem;color:rgba(255,255,255,.45);margin:0'>Modalità demo</p>"
            f"<p style='font-size:.92rem;font-weight:600;margin:2px 0 0'>Versione di prova</p>"
            f"<p style='font-size:.75rem;color:rgba(255,255,255,.35);margin:4px 0 0'>{remaining}/{DEMO_MAX_USES} generazioni rimanenti</p>",
            unsafe_allow_html=True
        )
        nav = "🎯 Generatore"
    else:
        st.markdown(f"<p style='font-size:.8rem;color:rgba(255,255,255,.45);margin:0'>Connesso come</p><p style='font-size:.92rem;font-weight:600;margin:2px 0 0'>{user_display}</p>", unsafe_allow_html=True)
        st.divider()
        nav = st.radio("Navigazione",
                       ["🎯 Generatore", "🔍 Trova Prospect", "📦 Bulk CSV", "📚 Archivio", "👤 Profili"],
                       key="nav_page", label_visibility="collapsed")
        st.divider()
        authenticator.logout(location="sidebar")
    st.markdown("<p style='font-size:.68rem;color:rgba(255,255,255,.2);margin-top:2rem'>AI SDR Agent · Enterprise</p>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════
PERSONA_NOTES = {
    "Generico":           "",
    "CEO / Fondatore":    "Persona destinatario: CEO/Fondatore. Vuole visione strategica, crescita, vantaggio competitivo. Parla di mercato e ROI strategico. Zero dettagli operativi.",
    "CFO / Finance":      "Persona destinatario: CFO. Vuole ROI misurabile, riduzione costi, rischio basso. Usa numeri concreti, percentuali, payback period.",
    "Dir. Commerciale":   "Persona destinatario: Dir. Commerciale. Vuole più chiusure e pipeline forte. Parla di conversion rate e velocità del ciclo di vendita.",
    "Head of Operations": "Persona destinatario: Head of Operations. Vuole efficienza e processi fluidi. Parla di tempo risparmiato, errori eliminati, scalabilità.",
}

def build_prompt(sn, sc, sp, sv, tn, tc, tr, ti, ctx, tone, lang, ab=False, persona="Generico"):
    ab_note = "Genera DUE versioni della Cold Email (VARIANTE A e VARIANTE B) con hook diversi. Separale SOLO con il token ===AB=== (nient'altro tra le due varianti). Inserisci entrambe nella sezione 1." if ab else ""
    persona_note = PERSONA_NOTES.get(persona, "")
    return f"""Sei un SDR senior con 10 anni di esperienza B2B. Crea un kit di prospecting completo e iper-personalizzato.

VENDITORE: {sn} — {sc} — {sp} | Value prop: {sv or "N/D"} | Tono: {tone}
TARGET: {tn} | {tr} @ {tc} | Settore: {ti or "N/D"} | Contesto: {ctx or "N/D"}
{("ISTRUZIONE PERSONA: " + persona_note) if persona_note else ""}
Genera TUTTO in {lang}. {ab_note}

REGOLE ASSOLUTE — rispettale tutte senza eccezioni:
- Testo PULITO, pronto da copiare e inviare senza modifiche
- VIETATO markdown (no #, no **, no ___, no ---)
- VIETATO trattini lunghi (— oppure –): usa virgole, due punti o punto fermo
- VIETATO punti elenco e liste puntate
- VIETATO aperture generiche ("Spero questa email la trovi bene", "Mi permetto di contattarla", "La contatto perché")
- Scrivi come una persona reale, non come un AI: frasi dirette, naturali, senza enfasi artificiale
- Paragrafi brevi, max 2-3 righe ciascuno
- Niente intestazioni di sezione, niente numerazioni

6 elementi separati SOLO dal token ===SEP===:

1. COLD EMAIL
Oggetto: [specifico, max 7 parole, senza punto interrogativo, cita {tc} o {ti} o {tr}]
[Corpo max 140 parole. Struttura: prima riga — apertura concreta che dimostra ricerca reale su {tc} o {ti}. Seconda parte — problema o opportunità che un {tr} riconosce nella sua realtà. Terza parte — come {sc} lo affronta in modo specifico. Ultima riga — CTA soft: domanda aperta o proposta di 15 minuti precisi.]

===SEP===
2. LINKEDIN — CONNESSIONE
[TASSATIVO: massimo 280 caratteri spazi inclusi — LinkedIn rifiuta messaggi più lunghi. Conta ogni carattere prima di scrivere. Umano, specifico su {tc} o {ti}. NON "Ho visto il tuo profilo". Diretto, niente piaggeria.]

===SEP===
3. LINKEDIN — FOLLOW-UP
[2-3 frasi dopo l'accettazione. Insight concreto utile per {ti}. Zero pressione, zero pitch diretto.]

===SEP===
4. FOLLOW-UP EMAIL 1 — Giorno 3
Oggetto: [angolo diverso dalla cold email, max 6 parole]
[Max 90 parole. Case study concreto o dato di settore per {ti}. CTA morbida.]

===SEP===
5. FOLLOW-UP EMAIL 2 — Giorno 7
Oggetto: [diretto, max 5 parole]
[Max 70 parole. Domanda diretta o scenario FOMO leggero. Porta aperta.]

===SEP===
6. COLD CALL — 15 secondi
[Script parlato e naturale. Chi sei, hook specifico su {tc}, valore in una frase, domanda aperta. NO tono da call center.]"""


def evaluate_quality(kit, tn, tc, tr, ti, tone):
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=220,
            messages=[{"role": "user", "content": f"""Sei un esperto B2B. Valuta questo kit di prospecting.
TARGET: {tn} | {tr} @ {tc} | {ti} | Tono: {tone}
COLD EMAIL: {kit.get("cold_email","")[:500]}
LINKEDIN: {kit.get("li_connect","")[:200]}

Rispondi SOLO con JSON valido, niente altro:
{{"personalizzazione":X,"cta":X,"tono":X,"totale":X,"forte":"una frase","migliorare":"una frase"}}
(valori da 1 a 10)"""}]
        )
        text = resp.content[0].text.strip()
        start = text.find("{"); end = text.rfind("}") + 1
        return json.loads(text[start:end])
    except Exception:
        return None


def research_prospect(name, company, role):
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(f'"{company}" 2024 2025', max_results=5))
        if not results:
            return None
        snippets = "\n".join(f"- {r['title']}: {r['body'][:200]}" for r in results)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=350,
            messages=[{"role": "user", "content": f"""Analizza queste notizie su {company} e identifica i trigger commerciali utili per un SDR che vuole contattare {name} ({role}).
Rispondi SOLO con JSON valido:
{{"triggers":[{{"tipo":"funding|assunzioni|espansione|prodotto|notizia","testo":"descrizione breve max 12 parole","urgenza":1}}],"sintesi":"una frase di contesto utile per personalizzare"}}
(urgenza: 1=bassa, 2=media, 3=alta)

Notizie:
{snippets}"""}]
        )
        text = resp.content[0].text.strip()
        s = text.find("{"); e = text.rfind("}") + 1
        return json.loads(text[s:e])
    except Exception:
        return None


def generate_subjects(cold_email, tn, tc, tr, ti, lang):
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=500,
            messages=[{"role": "user", "content": f"""Sei un esperto di email marketing B2B. Basandoti su questa cold email per {tr} @ {tc} ({ti}), genera 5 oggetti alternativi in {lang} con angoli diversi.
EMAIL: {cold_email[:600]}

Rispondi SOLO con JSON valido:
{{"oggetti":[{{"testo":"oggetto","angolo":"curiosità|urgenza|specificità|problema|roi","score":8,"motivo":"perché funziona in max 8 parole"}}]}}
(score da 1 a 10)"""}]
        )
        text = resp.content[0].text.strip()
        s = text.find("{"); e = text.rfind("}") + 1
        return json.loads(text[s:e])
    except Exception:
        return None


import html as _html
import streamlit.components.v1 as _components

def _clean(text):
    out = []
    for line in text.split("\n"):
        s = line.strip()
        if s.startswith("#"):
            continue
        if s in ("---", "___", "***", "===SEP===", "===AB==="):
            continue
        if s.startswith("===") and s.endswith("==="):
            continue
        out.append(line)
    return "\n".join(out).strip()

def _copyable_block(text, uid):
    display = _html.escape(text).replace("\n", "<br>")
    visual_lines = sum(max(1, (len(l) + 64) // 65) for l in text.split("\n"))
    height = max(140, visual_lines * 26 + 110)
    _components.html(f"""
<!DOCTYPE html><html><head>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  html, body {{ background:transparent; overflow:hidden; }}
  .wrap {{ position:relative; background:#f8fafc; border:1px solid #e2e8f0;
           border-radius:8px; padding:1rem 1.2rem 2.8rem;
           font-family:'IBM Plex Sans',sans-serif; font-size:13.5px;
           line-height:1.8; color:#1e293b; white-space:pre-wrap;
           word-break:break-word; }}
  .copy-btn {{ position:absolute; bottom:8px; right:10px; background:#fff;
               border:1px solid #dce2ec; border-radius:6px; padding:3px 10px;
               font-size:11px; font-weight:600; color:#334155; cursor:pointer;
               font-family:'IBM Plex Sans',sans-serif; }}
  .copy-btn:hover {{ border-color:#1a56db; color:#1a56db; }}
</style></head><body>
<div class="wrap" id="t">{display}
  <button class="copy-btn" onclick="
    var el=document.createElement('textarea');
    el.value=document.getElementById('t').innerText.replace(/\\n📋 Copia$/, '').trim();
    document.body.appendChild(el); el.select();
    document.execCommand('copy'); document.body.removeChild(el);
    this.textContent='✓ Copiato';
    setTimeout(()=>this.textContent='📋 Copia',1800)">📋 Copia</button>
</div>
<script>
  function resize() {{
    var h = document.querySelector('.wrap').scrollHeight + 12;
    window.parent.postMessage({{isStreamlitMessage:true, type:'streamlit:setFrameHeight', height:h}}, '*');
  }}
  window.addEventListener('load', resize);
  window.addEventListener('resize', resize);
</script>
</body></html>""", height=height, scrolling=False)

def _parse_email(text):
    text = _clean(text)
    lines = text.split("\n")
    subj, body_lines = "", []
    for l in lines:
        if not subj and (l.lower().startswith("oggetto") or l.lower().startswith("subject")):
            subj = l.split(":", 1)[-1].strip() if ":" in l else l
        else:
            body_lines.append(l)
    return subj, "\n".join(body_lines).strip()

def _render_single_email(text, uid):
    subj, body = _parse_email(text)
    if subj:
        st.markdown(f'<div class="email-subject-box"><span class="email-subject-label">Oggetto</span><span class="email-subject-text">{_html.escape(subj)}</span></div>', unsafe_allow_html=True)
    _copyable_block(body, uid)

def render_email(text, label, uid="0"):
    st.markdown(f'<p class="c-label">{label}</p>', unsafe_allow_html=True)
    if "===AB===" in text:
        parts = text.split("===AB===")
        ta, tb = st.tabs(["Variante A", "Variante B"])
        with ta:
            _render_single_email(parts[0], uid + "a")
        with tb:
            _render_single_email(parts[1] if len(parts) > 1 else "", uid + "b")
    else:
        _render_single_email(text, uid)

def render_linkedin(text, label, uid="0", max_chars=300):
    text = _clean(text)
    n = len(text)
    pct = min(100, int(n / max_chars * 100))
    color = "#dc2626" if n > max_chars else "#d97706" if n > int(max_chars * 0.87) else "#16a34a"
    st.markdown(f'<p class="c-label">{label}</p>', unsafe_allow_html=True)
    _copyable_block(text, uid)
    st.markdown(f"""
<div style="margin-top:.35rem">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <span style="font-size:.68rem;color:#8896aa">Caratteri</span>
    <span style="font-size:.72rem;font-weight:700;color:{color}">{n} / {max_chars}</span>
  </div>
  <div style="background:#e2e8f0;border-radius:4px;height:3px;margin-top:.3rem;overflow:hidden">
    <div style="width:{pct}%;height:3px;border-radius:4px;background:{color}"></div>
  </div>
</div>""", unsafe_allow_html=True)

def format_kit_txt(kit, meta):
    sep = "─" * 50
    ts  = meta.get("ts", datetime.now().strftime("%d/%m/%Y %H:%M"))
    return (
        f"AI SDR AGENT — ENTERPRISE KIT\n{'═'*54}\n"
        f"Prospect : {meta.get('prospect')}  |  {meta.get('ruolo')}  @  {meta.get('azienda')}\n"
        f"Venditore: {meta.get('sn')}  @  {meta.get('sc')}\n"
        f"Generato : {ts}\n{'═'*54}\n\n"
        f"COLD EMAIL\n{sep}\n{kit.get('cold_email','')}\n\n"
        f"LINKEDIN — CONNESSIONE\n{sep}\n{kit.get('li_connect','')}\n\n"
        f"LINKEDIN — FOLLOW-UP\n{sep}\n{kit.get('li_followup','')}\n\n"
        f"FOLLOW-UP EMAIL 1 — GIORNO 3\n{sep}\n{kit.get('fu1','')}\n\n"
        f"FOLLOW-UP EMAIL 2 — GIORNO 7\n{sep}\n{kit.get('fu2','')}\n\n"
        f"COLD CALL SCRIPT\n{sep}\n{kit.get('cold_call','')}\n"
    )


def render_kit_output(kit, meta, quality=None, triggers=None, subjects=None):
    elapsed = meta.get("elapsed", "—")
    st.markdown(f"""
<div class="stats-bar">
  <div class="stat-item"><span class="sv">6</span><span class="sl">asset pronti</span></div>
  <div class="stat-item"><span class="sv">{elapsed}s</span><span class="sl">tempo reale</span></div>
  <div class="stat-item"><span class="sv">~2h</span><span class="sl">lavoro manuale evitato</span></div>
  <div class="stat-item"><span class="sv">100%</span><span class="sl">personalizzato</span></div>
</div>""", unsafe_allow_html=True)

    if quality:
        score = quality.get("totale", 0)
        css   = "good" if score >= 8 else "ok" if score >= 6 else "poor"
        st.markdown(f"""
<div class="q-card">
  <div class="q-score {css}">{score}<span style="font-size:.9rem">/10</span></div>
  <div class="q-details">
    <p class="ql">Qualità kit</p>
    <p>✅ {quality.get("forte","")}</p>
    <p>💡 {quality.get("migliorare","")}</p>
  </div>
</div>""", unsafe_allow_html=True)

    r1, r2 = st.columns([3, 1])
    with r1:
        ts = meta.get("ts", "")
        st.markdown(f'<div class="kit-row"><div><p class="kit-name">{meta.get("prospect")} · {meta.get("ruolo")} · {meta.get("azienda")}</p><p class="kit-meta">Generato il {ts} · {elapsed}s</p></div></div>', unsafe_allow_html=True)
    with r2:
        st.download_button("⬇️ Scarica .txt",
                           data=format_kit_txt(kit, meta),
                           file_name=f"kit_{meta.get('prospect','').replace(' ','_')}.txt",
                           mime="text/plain", use_container_width=True)

    # CRM CSV export
    crm_rows = [[
        meta.get("prospect",""), meta.get("azienda",""), meta.get("ruolo",""),
        meta.get("settore",""), "Email", kit.get("cold_email","")[:300],
        meta.get("ts","")
    ]]
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Nome","Azienda","Ruolo","Settore","Canale","Messaggio","Data"])
    w.writerows(crm_rows)
    st.download_button("⬇️ Export CRM CSV",
                       data=buf.getvalue(),
                       file_name=f"crm_{meta.get('prospect','').replace(' ','_')}.csv",
                       mime="text/csv", use_container_width=True, key=f"crm_{meta.get('prospect','')}")

    # Trigger Intelligence
    if triggers and triggers.get("triggers"):
        tipo_css = {"funding":"tp-funding","assunzioni":"tp-assunzioni","espansione":"tp-espansione",
                    "prodotto":"tp-prodotto","notizia":"tp-notizia"}
        urgenza_color = {1:"#94a3b8", 2:"#f59e0b", 3:"#ef4444"}
        pills = ""
        for t in triggers["triggers"][:5]:
            css = tipo_css.get(t.get("tipo","notizia"), "tp-notizia")
            uc  = urgenza_color.get(t.get("urgenza",1), "#94a3b8")
            pills += f'<span class="trigger-pill {css}"><span class="tp-urgenza" style="background:{uc}"></span>{t["testo"]}</span>'
        st.markdown(f"""
<p class="sec-label" style="margin-bottom:.4rem">Trigger Intelligence</p>
<div class="trigger-row">{pills}</div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📧 Cold Email", "📬 Oggetti Email", "💼 LinkedIn", "🔄 Follow-up", "📞 Cold Call"])

    with tab1:
        render_email(kit.get("cold_email",""), "Cold Email", uid="ce")
        prospect_email = meta.get("email", "")
        subj_ce, body_ce = _parse_email(kit.get("cold_email", ""))
        if prospect_email:
            gmail_url = (
                "https://mail.google.com/mail/?view=cm&fs=1"
                f"&to={urllib.parse.quote(prospect_email)}"
                f"&su={urllib.parse.quote(subj_ce)}"
                f"&body={urllib.parse.quote(body_ce)}"
            )
            outlook_url = (
                "https://outlook.office.com/mail/deeplink/compose"
                f"?to={urllib.parse.quote(prospect_email)}"
                f"&subject={urllib.parse.quote(subj_ce)}"
                f"&body={urllib.parse.quote(body_ce)}"
            )
            st.markdown(
                f'<div style="display:flex;gap:.6rem;margin-top:.6rem">'
                f'<a href="{gmail_url}" target="_blank" style="display:inline-block;padding:6px 16px;background:#fff;border:1px solid #e5e7eb;border-radius:6px;font-size:.8rem;font-weight:600;color:#374151;text-decoration:none">📤 Apri in Gmail</a>'
                f'<a href="{outlook_url}" target="_blank" style="display:inline-block;padding:6px 16px;background:#fff;border:1px solid #e5e7eb;border-radius:6px;font-size:.8rem;font-weight:600;color:#374151;text-decoration:none">📤 Apri in Outlook</a>'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            st.caption("Aggiungi l'email del prospect nel form per abilitare l'invio diretto.")

    with tab2:
        st.markdown('<p class="c-label">5 varianti oggetto — scegli la più efficace</p>', unsafe_allow_html=True)
        if subjects and subjects.get("oggetti"):
            for obj in subjects["oggetti"]:
                score = obj.get("score", 0)
                sc_color = "#111318" if score >= 8 else "#6b7280" if score >= 6 else "#dc2626"
                ang = obj.get("angolo","")
                st.markdown(f"""
<div class="subj-row">
  <div style="flex:1">
    <div class="subj-text">{_html.escape(obj.get("testo",""))}</div>
    <div class="subj-meta">{_html.escape(obj.get("motivo",""))}</div>
  </div>
  <span class="subj-angolo">{ang}</span>
  <span class="subj-score" style="color:{sc_color}">{score}</span>
</div>""", unsafe_allow_html=True)
        else:
            st.info("Genera un kit per vedere le varianti oggetto.")

    with tab3:
        li_raw = meta.get("linkedin_url", "").strip()
        if li_raw:
            if not li_raw.startswith("http"):
                li_raw = "https://" + li_raw
            li_msg_url = li_raw.rstrip("/") + "/overlay/send-connection-form/"
            st.markdown(
                f'<div style="display:flex;gap:.6rem;margin-bottom:.8rem">'
                f'<a href="{li_raw}" target="_blank" style="display:inline-block;padding:6px 16px;background:#fff;border:1px solid #e5e7eb;border-radius:6px;font-size:.8rem;font-weight:600;color:#374151;text-decoration:none">👤 Profilo LinkedIn</a>'
                f'<a href="{li_msg_url}" target="_blank" style="display:inline-block;padding:6px 16px;background:#0d0f14;border:1px solid #0d0f14;border-radius:6px;font-size:.8rem;font-weight:600;color:#fff;text-decoration:none">💬 Invia richiesta</a>'
                f'</div>',
                unsafe_allow_html=True
            )
        else:
            li_search = (
                "https://www.linkedin.com/search/results/people/?keywords="
                + urllib.parse.quote(f"{meta.get('prospect','')} {meta.get('azienda','')}")
            )
            st.markdown(
                f'<a href="{li_search}" target="_blank" style="display:inline-block;margin-bottom:.8rem;padding:6px 16px;background:#fff;border:1px solid #e5e7eb;border-radius:6px;font-size:.8rem;font-weight:600;color:#374151;text-decoration:none">🔍 Cerca su LinkedIn</a>',
                unsafe_allow_html=True
            )
        a, b = st.columns(2)
        with a:
            render_linkedin(kit.get("li_connect",""), "Messaggio di connessione", uid="li1", max_chars=300)
        with b:
            st.markdown('<p class="c-label">Follow-up dopo accettazione</p>', unsafe_allow_html=True)
            _copyable_block(_clean(kit.get("li_followup","")), uid="li2")

    with tab4:
        a, b = st.columns(2)
        with a:
            render_email(kit.get("fu1",""), "Follow-up 1 — Giorno 3", uid="fu1")
        with b:
            render_email(kit.get("fu2",""), "Follow-up 2 — Giorno 7", uid="fu2")

    with tab5:
        st.markdown('<p class="c-label">Script cold call — 15 secondi</p>', unsafe_allow_html=True)
        _copyable_block(_clean(kit.get("cold_call","")), uid="cc")
        st.info("Leggi ad alta voce 3 volte prima di chiamare. Adattalo al tuo ritmo.")


# ════════════════════════════════════════════════════════
# PAGE — GENERATORE
# ════════════════════════════════════════════════════════
if nav == "🎯 Generatore":
    st.markdown("""
<div class="sdr-header">
  <h1 class="sdr-title">🎯 AI SDR Agent <span class="badge-ent">Enterprise</span></h1>
  <p class="sdr-sub">Kit di prospecting B2B personalizzato — 6 asset pronti in 20 secondi</p>
  <div class="hdr-metrics">
    <div class="hdr-m"><span class="v">6</span><span class="l">Asset per prospect</span></div>
    <div class="hdr-m"><span class="v">~45s</span><span class="l">Generazione</span></div>
    <div class="hdr-m"><span class="v">~2h</span><span class="l">Lavoro manuale evitato</span></div>
    <div class="hdr-m"><span class="v">∞</span><span class="l">Lingue supportate</span></div>
  </div>
</div>""", unsafe_allow_html=True)

    col_sx, col_dx = st.columns([5, 7], gap="large")

    with col_sx:
        # Seller profile selector
        profiles = db.get_profiles(username)
        profile_options = {f"{p['label']} ({p['company']})": p for p in profiles}

        if profiles:
            st.markdown('<p class="sec-label">Profilo venditore</p>', unsafe_allow_html=True)
            pc, pd = st.columns([3, 1])
            with pc:
                sel = st.selectbox("", ["— Inserisci manualmente —"] + list(profile_options.keys()),
                                   label_visibility="collapsed", key="profile_sel")
            with pd:
                if st.button("+ Nuovo", use_container_width=True):
                    st.session_state.show_new_profile = True
            if sel != "— Inserisci manualmente —":
                p = profile_options[sel]
                st.session_state.s_nome    = p["name"]
                st.session_state.s_azienda = p["company"]
                st.session_state.s_prodotto= p["product"]
                st.session_state.s_valore  = p["value_prop"]
            st.divider()
        else:
            if st.button("⚡ Carica Demo", use_container_width=True):
                st.session_state.s_nome    = "Marco Rossi"
                st.session_state.s_azienda = "AutomatIQ Srl"
                st.session_state.s_prodotto= "Piattaforma automazione ordini e preventivi per PMI manifatturiere"
                st.session_state.s_valore  = "Riduciamo del 40% il tempo di gestione ordini"
                st.session_state.t_nome    = "Luca Bianchi"
                st.session_state.t_azienda = "Alfa Componenti Srl"
                st.session_state.t_ruolo   = "Direttore Commerciale"
                st.session_state.t_settore = "Metalmeccanico"
                st.session_state.t_contesto= "Stanno assumendo 3 commerciali, nuova sede a Brescia"

        st.markdown('<p class="sec-label">Il tuo profilo</p>', unsafe_allow_html=True)
        st.text_input("Nome e cognome", key="s_nome", placeholder="es. Marco Rossi")
        st.text_input("Azienda", key="s_azienda", placeholder="es. AutomatIQ Srl")
        st.text_area("Prodotto / Servizio", key="s_prodotto", placeholder="Cosa vendi", height=70)
        st.text_area("Vantaggio competitivo", key="s_valore", placeholder="Perché sceglierti?", height=70)
        st.divider()

        st.markdown('<p class="sec-label">Prospect target</p>', unsafe_allow_html=True)
        ca, cb = st.columns(2)
        with ca: st.text_input("Nome", key="t_nome", placeholder="es. Luca Bianchi")
        with cb: st.text_input("Ruolo", key="t_ruolo", placeholder="es. Dir. Commerciale")
        st.text_input("Azienda", key="t_azienda", placeholder="es. Alfa Componenti Srl")
        ce, cf = st.columns(2)
        with ce: st.text_input("Settore", key="t_settore", placeholder="es. Metalmeccanico")
        with cf: st.text_input("Email prospect", key="t_email", placeholder="es. luca@alfasrl.it",
                               help="Facoltativa. Abilita i bottoni Gmail e Outlook.")


        st.text_input("Profilo LinkedIn (URL)", key="t_linkedin",
                      placeholder="es. linkedin.com/in/lucabianchi",
                      help="Facoltativo. Abilita il bottone per aprire direttamente la chat LinkedIn.")
        st.text_area("Contesto aggiuntivo", key="t_contesto",
                     placeholder="Nuove assunzioni, espansione, problemi noti...", height=65)
        st.divider()

        st.markdown('<p class="sec-label">Opzioni</p>', unsafe_allow_html=True)
        cc, cd = st.columns(2)
        with cc: tone = st.selectbox("Tono", ["Professionale","Diretto","Amichevole","Autorevole"])
        with cd: lang = st.selectbox("Lingua", ["Italiano","Inglese","Spagnolo","Francese","Tedesco"])

        persona = st.selectbox("Persona buyer", list(PERSONA_NOTES.keys()),
                               help="Adatta il tono e il contenuto al ruolo del destinatario")
        ab_mode = st.checkbox("Genera varianti A/B email", help="Due versioni della cold email con hook diversi")

        genera = st.button("🚀 Genera Kit Prospecting", type="primary", use_container_width=True)

    with col_dx:
        if genera:
            # Demo mode: block after limit
            if DEMO_MODE and st.session_state.demo_uses >= DEMO_MAX_USES:
                phone_line = f"<p style='margin:.25rem 0;font-size:.88rem;color:#334155'>📱 {CONTACT_PHONE}</p>" if CONTACT_PHONE else ""
                st.markdown(f"""
<div style="background:#fff;border:2px solid #1a56db;border-radius:12px;padding:2.2rem 2rem;text-align:center;margin-top:1rem">
  <p style="font-size:1.6rem;margin:0 0 .5rem">🎯</p>
  <h3 style="font-size:1.15rem;font-weight:700;color:#0f172a;margin:0 0 .5rem">Demo completata</h3>
  <p style="color:#64748b;font-size:.87rem;margin:0 0 1.4rem;line-height:1.6">Hai utilizzato le {DEMO_MAX_USES} generazioni disponibili nella versione demo.<br>Contatta <strong>{CONTACT_NAME}</strong> per accedere alla versione completa.</p>
  <p style="margin:.25rem 0;font-size:.9rem;color:#334155">✉️ <a href="mailto:{CONTACT_EMAIL}" style="color:#1a56db;font-weight:600;text-decoration:none">{CONTACT_EMAIL}</a></p>
  {phone_line}
  <hr style="margin:1.2rem 0;border-color:#e4eaf2">
  <p style="font-size:.76rem;color:#8896aa;margin:0;line-height:1.5">Versione enterprise: generazioni illimitate · bulk CSV · storico completo · profili multipli</p>
</div>""", unsafe_allow_html=True)
            else:
                sn  = st.session_state.get("s_nome","")
                sc  = st.session_state.get("s_azienda","")
                sp  = st.session_state.get("s_prodotto","")
                sv  = st.session_state.get("s_valore","")
                tn  = st.session_state.get("t_nome","")
                tc  = st.session_state.get("t_azienda","")
                tr  = st.session_state.get("t_ruolo","")
                ti  = st.session_state.get("t_settore","")
                ctx = st.session_state.get("t_contesto","")

                t_email_val = st.session_state.get("t_email", "").strip()
                if t_email_val and not _re.match(r"^[^@\s]{1,64}@[^@\s]{1,255}$", t_email_val):
                    st.error("L'email del prospect non è valida.")
                elif not all([sn, sc, sp, tn, tc, tr]):
                    st.error("Compila: nome + azienda + prodotto (tuo) e nome + azienda + ruolo (prospect).")
                else:
                    t0 = time.time()
                    with st.spinner("Analizzando il prospect e generando il kit..."):
                        # Trigger Intelligence — sempre attiva
                        triggers_data = research_prospect(tn, tc, tr)
                        if triggers_data and triggers_data.get("sintesi"):
                            ctx = (ctx + "\n\nIntelligence:\n" + triggers_data["sintesi"]).strip()

                        prompt = build_prompt(sn, sc, sp, sv, tn, tc, tr, ti, ctx, tone, lang, ab_mode, persona)
                        resp = client.messages.create(
                            model="claude-sonnet-4-6", max_tokens=3200,
                            messages=[{"role": "user", "content": prompt}]
                        )
                        testo = resp.content[0].text
                        sezioni = [s.strip() for s in testo.split("===SEP===")]
                        chiavi  = ["cold_email","li_connect","li_followup","fu1","fu2","cold_call"]
                        kit = {k: sezioni[i] if i < len(sezioni) else "" for i, k in enumerate(chiavi)}
                        quality  = evaluate_quality(kit, tn, tc, tr, ti, tone)
                        subjects = generate_subjects(kit.get("cold_email",""), tn, tc, tr, ti, lang)

                    elapsed = round(time.time() - t0, 1)
                    meta = {
                        "prospect": tn, "azienda": tc, "ruolo": tr, "settore": ti,
                        "sn": sn, "sc": sc, "tone": tone, "lang": lang,
                        "ts": datetime.now().strftime("%d/%m/%Y %H:%M"), "elapsed": elapsed,
                        "email": st.session_state.get("t_email", ""),
                        "linkedin_url": st.session_state.get("t_linkedin", ""),
                    }
                    q_score   = quality.get("totale") if quality else None
                    q_strong  = quality.get("forte") if quality else None
                    q_improve = quality.get("migliorare") if quality else None
                    db.save_kit(username, meta, kit, elapsed, q_score, q_strong, q_improve)
                    if DEMO_MODE:
                        new_uses = db.increment_demo_uses(st.session_state.get("demo_ip", "local"))
                        st.session_state.demo_uses = new_uses
                    st.session_state.current_kit      = kit
                    st.session_state.current_meta     = meta
                    st.session_state.current_qual     = quality
                    st.session_state.current_triggers = triggers_data
                    st.session_state.current_subjects = subjects

        if st.session_state.get("current_kit"):
            render_kit_output(
                st.session_state.current_kit,
                st.session_state.current_meta,
                st.session_state.get("current_qual"),
                st.session_state.get("current_triggers"),
                st.session_state.get("current_subjects"),
            )
            if DEMO_MODE:
                remaining = max(0, DEMO_MAX_USES - st.session_state.demo_uses)
                if remaining > 0:
                    st.info(f"Demo: {remaining} generazion{'e' if remaining == 1 else 'i'} rimanent{'e' if remaining == 1 else 'i'}. Contatta **{CONTACT_NAME}** ({CONTACT_EMAIL}) per la versione enterprise.")
                else:
                    phone_line = f" · {CONTACT_PHONE}" if CONTACT_PHONE else ""
                    st.warning(f"Generazioni demo esaurite. Contatta {CONTACT_EMAIL}{phone_line} per accedere alla versione completa.")
        else:
            st.markdown("""
<p style="font-size:1.05rem;font-weight:700;color:#0f172a;margin:0 0 .3rem">Genera il tuo kit</p>
<p style="color:#64748b;font-size:.87rem;margin:0 0 1.2rem">Compila il form e clicca Genera. Ogni asset è pronto all'uso.</p>
<div class="feat-grid">
  <div class="feat-card"><span class="ic">📧</span><div class="tt">Cold Email</div><div class="dd">Oggetto + corpo personalizzato con hook sul prospect</div></div>
  <div class="feat-card"><span class="ic">💼</span><div class="tt">LinkedIn x2</div><div class="dd">Connessione max 280 char + follow-up dopo accettazione</div></div>
  <div class="feat-card"><span class="ic">🔄</span><div class="tt">Sequenza Follow-up</div><div class="dd">Due email angoli diversi: giorno 3 e giorno 7</div></div>
  <div class="feat-card"><span class="ic">📞</span><div class="tt">Cold Call Script</div><div class="dd">15 secondi precisi, pronti da leggere ad alta voce</div></div>
</div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
# PAGE — TROVA PROSPECT (Apollo)
# ════════════════════════════════════════════════════════
elif nav == "🔍 Trova Prospect":
    st.markdown('<p class="page-title">🔍 Trova Prospect — Apollo Intelligence</p>', unsafe_allow_html=True)

    if not apollo.configured():
        st.warning("Chiave Apollo non configurata. Aggiungi **APOLLO_API_KEY** nel file `.env` o nelle variabili d'ambiente Render.")
        st.code("APOLLO_API_KEY=la-tua-master-api-key", language="bash")
    else:
        col_form, col_res = st.columns([2, 5], gap="large")

        with col_form:
            st.markdown('<p class="sec-label">Filtri ricerca</p>', unsafe_allow_html=True)
            ap_titles    = st.text_input("Ruolo / Titolo", placeholder="CEO, Direttore Commerciale, CFO",
                                         help="Separati da virgola. Apollo cerca anche titoli simili.")
            ap_keywords  = st.text_input("Keywords / Settore", placeholder="SaaS, manifatturiero, retail")
            ap_loc       = st.text_input("Location persone", value="Italy", placeholder="Italy, Milan, Rome")
            ap_emp       = st.multiselect("Dimensione azienda", list(apollo.EMP_RANGES.keys()),
                                          default=["11–50", "51–200"])
            ap_seniority = st.multiselect("Seniority", list(apollo.SENIORITY_MAP.keys()),
                                          default=["C-Suite / Founder", "VP / Head", "Director"])
            ap_per_page  = st.selectbox("Risultati", [10, 25, 50], index=1)
            ap_search    = st.button("🔍 Cerca", type="primary", use_container_width=True)

        with col_res:
            if ap_search:
                titles_list = [t.strip() for t in ap_titles.split(",") if t.strip()] or None
                locs_list   = [l.strip() for l in ap_loc.split(",") if l.strip()] or None
                emp_flat    = []
                for lbl in ap_emp:
                    emp_flat.extend(apollo.EMP_RANGES.get(lbl, []))
                sen_flat = []
                for lbl in ap_seniority:
                    sen_flat.extend(apollo.SENIORITY_MAP.get(lbl, []))

                with st.spinner("Ricerca su Apollo..."):
                    try:
                        data = apollo.search_people(
                            titles=titles_list,
                            keywords=ap_keywords or None,
                            person_locations=locs_list,
                            emp_ranges=emp_flat or None,
                            seniorities=sen_flat or None,
                            per_page=ap_per_page,
                        )
                        st.session_state.apollo_results = data.get("people", [])
                        st.session_state.apollo_total   = data.get("total_entries", 0)
                    except Exception as e:
                        st.error(f"Errore Apollo: {e}")
                        st.session_state.apollo_results = []
                        st.session_state.apollo_total   = 0

            people = st.session_state.get("apollo_results", [])
            total  = st.session_state.get("apollo_total", 0)

            if not people and not ap_search:
                st.markdown("""
<p style="color:#6b7280;font-size:.87rem;margin-top:1rem">
Imposta i filtri e clicca <strong>Cerca</strong>.<br>
Apollo restituisce i cognomi parzialmente oscurati per privacy — completa il nome nel Generatore se necessario.
</p>""", unsafe_allow_html=True)
            elif people:
                st.markdown(f'<p class="sec-label">{total:,} prospect trovati — mostro {len(people)}</p>',
                            unsafe_allow_html=True)

                for i, p in enumerate(people):
                    fname  = p.get("first_name", "")
                    lname  = p.get("last_name_obfuscated", "")
                    name   = f"{fname} {lname}".strip()
                    title  = p.get("title") or "—"
                    org    = (p.get("organization") or {}).get("name", "—")
                    has_em = p.get("has_email", False)

                    c1, c2 = st.columns([5, 1])
                    with c1:
                        em_tag = " · ✉️ email disponibile" if has_em else ""
                        st.markdown(f"**{name}**{em_tag}")
                        st.caption(f"{title} · {org}")
                    with c2:
                        if st.button("Kit →", key=f"apl_{i}_{p.get('id',i)}", use_container_width=True):
                            st.session_state.t_nome    = name
                            st.session_state.t_azienda = org
                            st.session_state.t_ruolo   = title
                            st.session_state.t_settore = ""
                            st.session_state.t_contesto = ""
                            st.session_state["nav_page"] = "🎯 Generatore"
                            st.rerun()
                    st.divider()
            elif ap_search:
                st.info("Nessun risultato. Prova a modificare i filtri o amplia i criteri.")

# ════════════════════════════════════════════════════════
# PAGE — BULK CSV
# ════════════════════════════════════════════════════════
elif nav == "📦 Bulk CSV":
    st.markdown('<p class="page-title">Generazione in bulk da CSV</p>', unsafe_allow_html=True)

    # Template download
    template_buf = io.StringIO()
    w = csv.writer(template_buf)
    w.writerow(["nome","azienda","ruolo","settore","contesto"])
    w.writerow(["Luca Bianchi","Alfa Srl","Direttore Commerciale","Metalmeccanico","Nuova sede a Brescia"])
    w.writerow(["Sara Rossi","Beta SpA","CEO","SaaS B2B","Stanno assumendo sviluppatori"])
    st.download_button("⬇️ Scarica template CSV", data=template_buf.getvalue(),
                       file_name="template_prospect.csv", mime="text/csv")

    st.divider()
    uploaded = st.file_uploader("Carica CSV prospect", type=["csv"])

    if uploaded:
        reader = list(csv.DictReader(io.StringIO(uploaded.read().decode("utf-8", errors="ignore"))))
        st.info(f"**{len(reader)}** prospect trovati nel file.")
        st.dataframe([{k: r.get(k,"") for k in ["nome","azienda","ruolo","settore"]} for r in reader[:5]], use_container_width=True)

        profiles = db.get_profiles(username)
        if profiles:
            sel_profile = st.selectbox("Profilo venditore", [f"{p['label']} ({p['company']})" for p in profiles])
            chosen = profiles[[f"{p['label']} ({p['company']})" for p in profiles].index(sel_profile)]
            sn, sc, sp, sv = chosen["name"], chosen["company"], chosen["product"], chosen["value_prop"]
        else:
            st.warning("Nessun profilo venditore salvato. Vai in **Profili** e crea il tuo prima.")
            sn = sc = sp = sv = ""

        bc1, bc2 = st.columns(2)
        with bc1: b_tone = st.selectbox("Tono", ["Professionale","Diretto","Amichevole","Autorevole"])
        with bc2: b_lang = st.selectbox("Lingua", ["Italiano","Inglese","Spagnolo"])

        BULK_MAX = 20
        if len(reader) > BULK_MAX:
            st.warning(f"Il file contiene {len(reader)} righe. Verranno elaborati solo i primi {BULK_MAX} prospect per sessione.")
            reader = reader[:BULK_MAX]

        if st.button("🚀 Genera kit per tutti i prospect", type="primary"):
            if not all([sn, sc, sp]):
                st.error("Seleziona un profilo venditore valido.")
            else:
                progress = st.progress(0, text="Avvio generazione...")
                zip_buf = io.BytesIO()
                csv_rows = [["Nome","Azienda","Ruolo","Settore","Cold Email Oggetto","Cold Email Corpo","LinkedIn Conn.","Giorno 3 Oggetto","Giorno 7 Oggetto"]]

                with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zf:
                    for i, row in enumerate(reader):
                        tn  = row.get("nome","Prospect")
                        tc  = row.get("azienda","Azienda")
                        tr  = row.get("ruolo","Ruolo")
                        ti  = row.get("settore","")
                        ctx = row.get("contesto","")
                        progress.progress((i+1)/len(reader), text=f"Generando kit {i+1}/{len(reader)}: {tn} @ {tc}")
                        prompt = build_prompt(sn, sc, sp, sv, tn, tc, tr, ti, ctx, b_tone, b_lang)
                        resp = client.messages.create(
                            model="claude-sonnet-4-6", max_tokens=2800,
                            messages=[{"role": "user", "content": prompt}]
                        )
                        sezioni = [s.strip() for s in resp.content[0].text.split("===SEP===")]
                        chiavi  = ["cold_email","li_connect","li_followup","fu1","fu2","cold_call"]
                        kit = {k: sezioni[idx] if idx < len(sezioni) else "" for idx, k in enumerate(chiavi)}
                        meta = {"prospect": tn, "azienda": tc, "ruolo": tr, "settore": ti,
                                "sn": sn, "sc": sc, "ts": datetime.now().strftime("%d/%m/%Y %H:%M"), "elapsed": 0}
                        db.save_kit(username, meta, kit)
                        fname = f"kit_{tn.replace(' ','_')}_{tc.replace(' ','_')}.txt"
                        zf.writestr(fname, format_kit_txt(kit, meta))

                        lines = kit["cold_email"].split("\n")
                        obj   = next((l.replace("Oggetto:","").strip() for l in lines if l.lower().startswith("oggetto")), "")
                        corpo = "\n".join(l for l in lines if not l.lower().startswith("oggetto")).strip()[:300]
                        f1_obj = kit["fu1"].split("\n")[0].replace("Oggetto:","").strip() if kit["fu1"] else ""
                        f2_obj = kit["fu2"].split("\n")[0].replace("Oggetto:","").strip() if kit["fu2"] else ""
                        csv_rows.append([tn, tc, tr, ti, obj, corpo, kit.get("li_connect","")[:200], f1_obj, f2_obj])

                progress.progress(1.0, text="✅ Completato!")
                st.success(f"Generati {len(reader)} kit!")
                st.download_button("⬇️ Scarica tutti i kit (.zip)", data=zip_buf.getvalue(),
                                   file_name="bulk_kit_sdr.zip", mime="application/zip")
                crm_buf = io.StringIO()
                csv.writer(crm_buf).writerows(csv_rows)
                st.download_button("⬇️ Export CRM CSV (tutti)", data=crm_buf.getvalue(),
                                   file_name="bulk_crm_export.csv", mime="text/csv")

# ════════════════════════════════════════════════════════
# PAGE — ARCHIVIO
# ════════════════════════════════════════════════════════
elif nav == "📚 Archivio":
    st.markdown('<p class="page-title">Archivio kit generati</p>', unsafe_allow_html=True)
    history = db.get_history(username)

    if not history:
        st.info("Nessun kit generato ancora. Vai nel **Generatore** per crearne uno.")
    else:
        search = st.text_input("🔍 Cerca per nome o azienda", placeholder="es. Bianchi, Alfa...")
        if search:
            history = [h for h in history if search.lower() in (h.get("prospect_name","") + h.get("prospect_co","")).lower()]

        def score_pill(s):
            if s is None: return '<span style="color:#aab4c4">—</span>'
            cls = "sc-good" if s >= 8 else "sc-ok" if s >= 6 else "sc-poor"
            return f'<span class="score-pill {cls}">{s}/10</span>'

        rows_html = "".join(
            f'<tr><td><strong>{h["prospect_name"]}</strong></td>'
            f'<td>{h["prospect_co"]}</td>'
            f'<td>{h["prospect_role"]}</td>'
            f'<td>{score_pill(h.get("q_score"))}</td>'
            f'<td style="color:#8896aa">{h["generated_at"][:16]}</td>'
            f'<td><button onclick="window.location.href=\'?load={h["id"]}\'" style="font-size:.75rem;padding:3px 10px;border:1px solid #dce2ec;border-radius:5px;background:#fff;cursor:pointer;color:#1a56db;font-weight:600">Carica</button></td></tr>'
            for h in history
        )
        st.markdown(f"""
<table class="hist-table">
<thead><tr>
  <th>Prospect</th><th>Azienda</th><th>Ruolo</th>
  <th>Score</th><th>Generato il</th><th></th>
</tr></thead>
<tbody>{rows_html}</tbody>
</table>""", unsafe_allow_html=True)

        st.divider()

        col_load, col_del = st.columns([3, 1])
        with col_load:
            st.markdown('<p class="sec-label">Carica un kit dallo storico</p>', unsafe_allow_html=True)
        options = {f"{h['prospect_name']} @ {h['prospect_co']} — {h['generated_at'][:16]}": h["id"] for h in history}
        sel = st.selectbox("Seleziona kit", list(options.keys()), label_visibility="collapsed")
        c1, c2 = st.columns([2, 1])
        with c1:
            load_btn = st.button("Carica questo kit", type="primary")
        with c2:
            if st.button("🗑 Elimina", help="Elimina definitivamente questo kit"):
                db.delete_kit(options[sel], username)
                st.success("Kit eliminato.")
                st.rerun()
        if load_btn:
            row = db.get_kit(options[sel])
            if row:
                meta = {
                    "prospect": row["prospect_name"], "azienda": row["prospect_co"],
                    "ruolo": row["prospect_role"], "settore": row.get("prospect_sector",""),
                    "sn": row.get("seller_name",""), "sc": row.get("seller_co",""),
                    "ts": row["generated_at"][:16], "elapsed": row.get("elapsed","—"),
                }
                quality = None
                if row.get("q_score"):
                    quality = {"totale": row["q_score"], "forte": row.get("q_strong",""), "migliorare": row.get("q_improve","")}
                st.session_state.current_kit  = row["kit"]
                st.session_state.current_meta = meta
                st.session_state.current_qual = quality
                st.success("Kit caricato. Vai nel **Generatore** per vederlo.")

# ════════════════════════════════════════════════════════
# PAGE — PROFILI
# ════════════════════════════════════════════════════════
elif nav == "👤 Profili":
    st.markdown('<p class="page-title">Profili venditore</p>', unsafe_allow_html=True)
    st.markdown("Salva il tuo profilo una volta sola e selezionalo nel Generatore senza reinserire ogni volta.")

    with st.expander("➕ Aggiungi nuovo profilo", expanded=not db.get_profiles(username)):
        pl = st.text_input("Etichetta profilo", placeholder='es. "Prodotto A – IT" o "Version inglese"')
        pn = st.text_input("Nome e cognome")
        pc = st.text_input("Azienda")
        pp = st.text_area("Prodotto / Servizio", height=70)
        pv = st.text_area("Vantaggio competitivo", height=70)
        if st.button("Salva profilo", type="primary"):
            if all([pl, pn, pc, pp]):
                db.save_profile(username, pl, pn, pc, pp, pv)
                st.success("Profilo salvato.")
                st.rerun()
            else:
                st.error("Compila etichetta, nome, azienda e prodotto.")

    st.divider()
    profiles = db.get_profiles(username)
    if not profiles:
        st.info("Nessun profilo ancora. Creane uno sopra.")
    else:
        for p in profiles:
            with st.container():
                c1, c2 = st.columns([5, 1])
                with c1:
                    st.markdown(f"**{p['label']}** · {p['name']} @ {p['company']}")
                    st.caption(p["product"][:120] + ("..." if len(p["product"]) > 120 else ""))
                with c2:
                    if st.button("Elimina", key=f"del_{p['id']}"):
                        db.delete_profile(p["id"])
                        st.rerun()
                st.divider()
