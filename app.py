import streamlit as st
import anthropic
import yaml
import json
import csv
import io
import os
import time
import zipfile
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from yaml.loader import SafeLoader
import streamlit_authenticator as stauth

load_dotenv(Path(__file__).parent.parent / ".env")
import db
db.init()

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
*, *::before, *::after {
    font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    box-sizing: border-box;
}
#MainMenu, footer, header,
[data-testid="stDecoration"], [data-testid="stToolbar"],
div[data-testid="stStatusWidget"] { display: none !important; }
.block-container { padding: 1.8rem 2.4rem 3rem !important; max-width: 1480px !important; }
[data-testid="stAppViewContainer"] { background: #f4f6f9 !important; }
[data-testid="stSidebar"] { background: #07101f !important; border-right: none !important; }
[data-testid="stSidebar"] * { color: rgba(255,255,255,.85) !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.08) !important; }
::-webkit-scrollbar { width: 5px; }
::-webkit-scrollbar-thumb { background: #d1d9e6; border-radius: 8px; }

.sdr-header {
    background: #07101f; border-radius: 12px;
    padding: 2rem 2.6rem 1.8rem; color: #fff;
    margin-bottom: 1.8rem; position: relative; overflow: hidden;
    box-shadow: 0 4px 20px rgba(7,16,31,.14);
}
.sdr-header::before {
    content: ''; position: absolute; inset: 0;
    background-image: radial-gradient(rgba(255,255,255,.03) 1px, transparent 1px);
    background-size: 30px 30px; pointer-events: none;
}
.sdr-title { font-size: 1.85rem; font-weight: 700; letter-spacing: -.02em; margin: 0; color: #fff; }
.sdr-sub   { font-size: .9rem; color: rgba(255,255,255,.5); margin: .5rem 0 0; font-weight: 400; }
.badge-ent {
    font-size: .58rem; font-weight: 600; letter-spacing: 1.8px; text-transform: uppercase;
    border: 1px solid rgba(255,255,255,.25); color: rgba(255,255,255,.65);
    padding: 3px 9px; border-radius: 4px; margin-left: 10px; vertical-align: middle;
}
.hdr-metrics { display: flex; gap: 0; margin-top: 1.6rem; padding-top: 1.5rem; border-top: 1px solid rgba(255,255,255,.07); }
.hdr-m { padding-right: 2.2rem; margin-right: 2.2rem; border-right: 1px solid rgba(255,255,255,.07); }
.hdr-m:last-child { border-right: none; }
.hdr-m .v { font-size: 1.45rem; font-weight: 700; color: #fff; display: block; line-height: 1; }
.hdr-m .l { font-size: .68rem; color: rgba(255,255,255,.4); display: block; margin-top: 3px; }

.sec-label { font-size: .67rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #8896aa; margin: 0 0 .55rem; }
.page-title { font-size: 1.3rem; font-weight: 700; color: #0f172a; margin: 0 0 1.4rem; letter-spacing: -.02em; }

.stats-bar { display: flex; background: #fff; border: 1px solid #dce2ec; border-radius: 10px; overflow: hidden; margin-bottom: 1.3rem; }
.stat-item { flex: 1; padding: .8rem 1rem; border-right: 1px solid #dce2ec; text-align: center; }
.stat-item:last-child { border-right: none; }
.stat-item .sv { display: block; font-size: 1.25rem; font-weight: 700; color: #0f172a; line-height: 1; }
.stat-item .sl { display: block; font-size: .67rem; color: #8896aa; margin-top: 3px; font-weight: 500; }

.q-card { background: #fff; border: 1px solid #dce2ec; border-radius: 10px; padding: 1rem 1.2rem; margin-bottom: 1.1rem; display: flex; align-items: center; gap: 1.2rem; }
.q-score { font-size: 2rem; font-weight: 800; color: #0f172a; min-width: 48px; text-align: center; }
.q-score.good  { color: #16a34a; }
.q-score.ok    { color: #d97706; }
.q-score.poor  { color: #dc2626; }
.q-details p { margin: 0; font-size: .83rem; color: #334155; line-height: 1.5; }
.q-details .ql { font-size: .7rem; font-weight: 700; text-transform: uppercase; letter-spacing: .8px; color: #8896aa; margin-bottom: 2px; }

.kit-row { display: flex; align-items: center; justify-content: space-between; margin-bottom: .9rem; }
.kit-name  { font-size: .92rem; font-weight: 700; color: #0f172a; }
.kit-meta  { font-size: .75rem; color: #8896aa; margin-top: 1px; }
.c-label   { font-size: .67rem; font-weight: 700; text-transform: uppercase; letter-spacing: .9px; color: #8896aa; margin-bottom: .3rem; }
.char-cc   { font-size: .7rem; color: #aab4c4; text-align: right; margin-top: .2rem; }
.char-warn { color: #d97706; font-weight: 600; }
.char-over { color: #dc2626; font-weight: 700; }

.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    border-radius: 8px !important; border: 1px solid #dce2ec !important;
    background: #fff !important; font-size: .875rem !important; color: #0f172a !important;
    transition: border-color .12s, box-shadow .12s !important;
}
.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #1a56db !important;
    box-shadow: 0 0 0 3px rgba(26,86,219,.1) !important; outline: none !important;
}
.stTextInput > label, .stTextArea > label, .stSelectbox > label {
    font-size: .75rem !important; font-weight: 600 !important; color: #4a5568 !important;
}

.stButton > button[kind="primary"] {
    background: #1a56db !important; border: none !important; border-radius: 8px !important;
    font-size: .9rem !important; font-weight: 600 !important; color: #fff !important;
    box-shadow: none !important; transition: background .12s !important;
}
.stButton > button[kind="primary"]:hover { background: #1648c0 !important; }
.stButton > button:not([kind="primary"]) {
    background: #fff !important; border: 1px solid #dce2ec !important;
    border-radius: 8px !important; color: #334155 !important;
    font-weight: 600 !important; font-size: .82rem !important;
    transition: border-color .12s, color .12s !important;
}
.stButton > button:not([kind="primary"]):hover { border-color: #1a56db !important; color: #1a56db !important; }
.stDownloadButton > button {
    background: #fff !important; border: 1px solid #1a56db !important;
    color: #1a56db !important; border-radius: 8px !important;
    font-weight: 600 !important; transition: background .12s, color .12s !important;
}
.stDownloadButton > button:hover { background: #1a56db !important; color: #fff !important; }

.stTabs [data-baseweb="tab-list"] {
    gap: 2px !important; background: #eaeff6 !important;
    padding: 4px !important; border-radius: 9px !important; border-bottom: none !important;
}
.stTabs [data-baseweb="tab"] { border-radius: 6px !important; font-weight: 500 !important; font-size: .82rem !important; padding: 6px 14px !important; color: #64748b !important; }
.stTabs [aria-selected="true"] { background: #fff !important; color: #0f172a !important; font-weight: 700 !important; box-shadow: 0 1px 3px rgba(10,15,30,.08) !important; }
.stTabs [data-baseweb="tab-panel"] { padding-top: .9rem !important; }

.feat-grid { display: grid; grid-template-columns: 1fr 1fr; gap: .75rem; margin-top: 1rem; }
.feat-card { background: #fff; border: 1px solid #dce2ec; border-radius: 10px; padding: 1.1rem 1.2rem; }
.feat-card .ic { font-size: 1.1rem; margin-bottom: .4rem; display: block; }
.feat-card .tt { font-size: .85rem; font-weight: 700; color: #0f172a; }
.feat-card .dd { font-size: .76rem; color: #64748b; margin-top: .15rem; line-height: 1.5; }

.hist-table { width: 100%; border-collapse: collapse; font-size: .82rem; }
.hist-table th { text-align: left; padding: .5rem .8rem; background: #f4f6f9; color: #64748b; font-size: .68rem; font-weight: 700; text-transform: uppercase; letter-spacing: .8px; border-bottom: 1px solid #dce2ec; }
.hist-table td { padding: .6rem .8rem; border-bottom: 1px solid #f0f3f7; color: #0f172a; vertical-align: middle; }
.hist-table tr:last-child td { border-bottom: none; }
.score-pill { display: inline-block; padding: 2px 8px; border-radius: 20px; font-size: .72rem; font-weight: 700; }
.sc-good  { background: #d1fae5; color: #065f46; }
.sc-ok    { background: #fef3c7; color: #92400e; }
.sc-poor  { background: #fee2e2; color: #991b1b; }

hr { border-color: #e4eaf2 !important; margin: 1rem 0 !important; }
[data-testid="stInfo"]    { background: #eff6ff !important; border: 1px solid #bfdbfe !important; border-radius: 8px !important; }
[data-testid="stInfo"] p  { color: #1e40af !important; font-size: .82rem !important; }
[data-testid="stSuccess"] { border-radius: 8px !important; }
[data-testid="stAlert"]   { border-radius: 8px !important; }
[data-testid="stWarning"] { border-radius: 8px !important; }

/* Document viewer — override code block stile */
[data-testid="stCode"] pre {
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    padding: 1.2rem 1.4rem !important;
    margin: 0 !important;
}
[data-testid="stCode"] code {
    font-family: 'IBM Plex Sans', -apple-system, sans-serif !important;
    font-size: .875rem !important;
    line-height: 1.8 !important;
    color: #1e293b !important;
    white-space: pre-wrap !important;
    word-break: break-word !important;
    background: transparent !important;
}
.email-subject-box {
    background: #eff6ff; border: 1px solid #bfdbfe;
    border-radius: 7px; padding: .55rem 1.1rem;
    margin-bottom: .65rem; display: flex; align-items: baseline; gap: .5rem;
}
.email-subject-label {
    font-size: .65rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1px; color: #3b82f6; white-space: nowrap;
}
.email-subject-text { font-size: .88rem; font-weight: 600; color: #0f172a; }
.char-bar-wrap { margin-top: .45rem; }
.char-bar-bg { background: #e2e8f0; border-radius: 4px; height: 3px; margin-top: .3rem; overflow: hidden; }
.char-bar-fill { height: 3px; border-radius: 4px; transition: width .2s; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
# AUTH
# ════════════════════════════════════════════════════════
if DEMO_MODE:
    username     = "demo_visitor"
    user_display = "Demo"
    if "demo_uses" not in st.session_state:
        st.session_state.demo_uses = 0
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
        nav = st.radio("Navigazione", ["🎯 Generatore", "📦 Bulk CSV", "📚 Archivio", "👤 Profili"],
                       label_visibility="collapsed")
        st.divider()
        authenticator.logout(location="sidebar")
    st.markdown("<p style='font-size:.68rem;color:rgba(255,255,255,.2);margin-top:2rem'>AI SDR Agent · Enterprise</p>", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════
def build_prompt(sn, sc, sp, sv, tn, tc, tr, ti, ctx, tone, lang, ab=False):
    ab_note = "Genera DUE versioni della Cold Email (VARIANTE A e VARIANTE B) con hook diversi. Inserisci entrambe nella sezione 1." if ab else ""
    return f"""Sei un SDR di élite. Crea un kit di prospecting B2B completo e iper-personalizzato.

VENDITORE: {sn} | {sc} | {sp} | Value prop: {sv or "N/D"} | Tono: {tone}
TARGET: {tn} | {tr} @ {tc} | Settore: {ti or "N/D"} | Contesto: {ctx or "N/D"}

Genera TUTTO in {lang}. {ab_note}
6 elementi separati SOLO dal token ===SEP===:

1. COLD EMAIL
Oggetto: [specifico, cita dettaglio su {tc} o {tr}]
[Corpo max 150 parole. Apertura personalizzata su {tc}/{ti}. Problema reale di {tr}. Come {sc} lo risolve. CTA morbida. NO "Spero questa email la trovi bene".]

===SEP===
2. LINKEDIN — CONNESSIONE
[Max 280 caratteri. NON "Ho visto il tuo profilo". Umano, specifico.]

===SEP===
3. LINKEDIN — FOLLOW-UP
[2-3 frasi. Insight per {ti}. Zero pressione.]

===SEP===
4. FOLLOW-UP EMAIL 1 — Giorno 3
Oggetto: [angolo diverso]
[max 100 parole. Case study o dato {ti}. CTA morbida.]

===SEP===
5. FOLLOW-UP EMAIL 2 — Giorno 7
Oggetto: [diretto]
[max 80 parole. FOMO o domanda diretta. Porta aperta.]

===SEP===
6. COLD CALL — 15 secondi
[Script naturale. Chi sei, hook su {tc}, valore, domanda aperta.]"""


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
            results = list(ddgs.text(f'"{company}" {role} 2024 2025', max_results=4))
        if not results:
            return ""
        snippets = "\n".join(f"- {r['title']}: {r['body'][:180]}" for r in results)
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001", max_tokens=250,
            messages=[{"role": "user", "content": f"Estrai i 2-3 fatti più utili per contattare {name} ({role} in {company}). Conciso e pratico.\n\n{snippets}"}]
        )
        return resp.content[0].text.strip()
    except Exception:
        return ""


import html as _html

def _copyable_block(text, uid):
    display = _html.escape(text).replace("\n", "<br>")
    js_text = text.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")
    st.markdown(f"""
<div style="position:relative;background:#f8fafc;border:1px solid #e2e8f0;
            border-radius:8px;padding:1.1rem 1.3rem 2.8rem;margin-bottom:.3rem">
  <div style="font-family:'IBM Plex Sans',sans-serif;font-size:.875rem;
              line-height:1.8;color:#1e293b;white-space:pre-wrap;
              word-break:break-word">{display}</div>
  <button onclick="navigator.clipboard.writeText(`{js_text}`);this.innerHTML='✓ Copiato';setTimeout(()=>this.innerHTML='📋 Copia',1800)"
          style="position:absolute;bottom:8px;right:10px;background:#fff;
                 border:1px solid #dce2ec;border-radius:6px;padding:3px 10px;
                 font-size:.72rem;font-weight:600;color:#334155;cursor:pointer;
                 font-family:'IBM Plex Sans',sans-serif">
    📋 Copia
  </button>
</div>""", unsafe_allow_html=True)

def render_email(text, label, uid="0"):
    lines = text.split("\n")
    subj, body_lines = "", []
    for l in lines:
        if not subj and (l.lower().startswith("oggetto") or l.lower().startswith("subject")):
            subj = l.split(":", 1)[-1].strip() if ":" in l else l
        else:
            body_lines.append(l)
    body = "\n".join(body_lines).strip()
    st.markdown(f'<p class="c-label">{label}</p>', unsafe_allow_html=True)
    if subj:
        st.markdown(f'<div class="email-subject-box"><span class="email-subject-label">Oggetto</span><span class="email-subject-text">{_html.escape(subj)}</span></div>', unsafe_allow_html=True)
    _copyable_block(body, uid)

def render_linkedin(text, label, uid="0", max_chars=300):
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


def render_kit_output(kit, meta, quality=None):
    elapsed = meta.get("elapsed", "—")
    st.markdown(f"""
<div class="stats-bar">
  <div class="stat-item"><span class="sv">6</span><span class="sl">asset pronti</span></div>
  <div class="stat-item"><span class="sv">{elapsed}s</span><span class="sl">generazione</span></div>
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

    st.markdown("<br>", unsafe_allow_html=True)
    tab1, tab2, tab3, tab4 = st.tabs(["📧 Cold Email", "💼 LinkedIn", "🔄 Follow-up", "📞 Cold Call"])

    with tab1:
        render_email(kit.get("cold_email",""), "Cold Email", uid="ce")

    with tab2:
        a, b = st.columns(2)
        with a:
            render_linkedin(kit.get("li_connect",""), "Messaggio di connessione", uid="li1", max_chars=300)
        with b:
            st.markdown('<p class="c-label">Follow-up dopo accettazione</p>', unsafe_allow_html=True)
            _copyable_block(kit.get("li_followup",""), uid="li2")

    with tab3:
        a, b = st.columns(2)
        with a:
            render_email(kit.get("fu1",""), "Follow-up 1 — Giorno 3", uid="fu1")
        with b:
            render_email(kit.get("fu2",""), "Follow-up 2 — Giorno 7", uid="fu2")

    with tab4:
        st.markdown('<p class="c-label">Script cold call — 15 secondi</p>', unsafe_allow_html=True)
        _copyable_block(kit.get("cold_call",""), uid="cc")
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
    <div class="hdr-m"><span class="v">~20s</span><span class="l">Generazione</span></div>
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
        st.text_input("Settore", key="t_settore", placeholder="es. Metalmeccanico")
        st.text_area("Contesto aggiuntivo", key="t_contesto",
                     placeholder="Nuove assunzioni, espansione, problemi noti...", height=65)
        st.divider()

        st.markdown('<p class="sec-label">Opzioni</p>', unsafe_allow_html=True)
        cc, cd = st.columns(2)
        with cc: tone = st.selectbox("Tono", ["Professionale","Diretto","Amichevole","Autorevole"])
        with cd: lang = st.selectbox("Lingua", ["Italiano","Inglese","Spagnolo","Francese","Tedesco"])

        opt1, opt2 = st.columns(2)
        with opt1: ab_mode     = st.checkbox("Genera varianti A/B", help="Due versioni della cold email")
        with opt2: do_research = st.checkbox("Ricerca prospect", help="Cerca notizie recenti online")

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

                if not all([sn, sc, sp, tn, tc, tr]):
                    st.error("Compila: nome + azienda + prodotto (tuo) e nome + azienda + ruolo (prospect).")
                else:
                    t0 = time.time()
                    research_ctx = ""
                    with st.status(f"Generando kit per {tn} @ {tc}...", expanded=True) as status:
                        if do_research:
                            st.write("🔍 Ricercando informazioni su " + tc + "...")
                            research_ctx = research_prospect(tn, tc, tr)
                            if research_ctx:
                                ctx = (ctx + "\n\nRicerca web:\n" + research_ctx).strip()
                        st.write("✍️ Costruendo la sequenza outreach...")
                        prompt = build_prompt(sn, sc, sp, sv, tn, tc, tr, ti, ctx, tone, lang, ab_mode)
                        resp = client.messages.create(
                            model="claude-sonnet-4-6", max_tokens=3000,
                            messages=[{"role": "user", "content": prompt}]
                        )
                        testo = resp.content[0].text
                        st.write("📊 Valutando qualità del kit...")
                        sezioni = [s.strip() for s in testo.split("===SEP===")]
                        chiavi  = ["cold_email","li_connect","li_followup","fu1","fu2","cold_call"]
                        kit = {k: sezioni[i] if i < len(sezioni) else "" for i, k in enumerate(chiavi)}
                        quality = evaluate_quality(kit, tn, tc, tr, ti, tone)
                        status.update(label="✅ Kit completato!", state="complete")

                    elapsed = round(time.time() - t0, 1)
                    meta = {
                        "prospect": tn, "azienda": tc, "ruolo": tr, "settore": ti,
                        "sn": sn, "sc": sc, "tone": tone, "lang": lang,
                        "ts": datetime.now().strftime("%d/%m/%Y %H:%M"), "elapsed": elapsed,
                    }
                    q_score   = quality.get("totale") if quality else None
                    q_strong  = quality.get("forte") if quality else None
                    q_improve = quality.get("migliorare") if quality else None
                    db.save_kit(username, meta, kit, elapsed, q_score, q_strong, q_improve)
                    if DEMO_MODE:
                        st.session_state.demo_uses += 1
                    st.session_state.current_kit  = kit
                    st.session_state.current_meta = meta
                    st.session_state.current_qual = quality

        if st.session_state.get("current_kit"):
            render_kit_output(
                st.session_state.current_kit,
                st.session_state.current_meta,
                st.session_state.get("current_qual")
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
        st.markdown('<p class="sec-label">Carica un kit dallo storico</p>', unsafe_allow_html=True)
        options = {f"{h['prospect_name']} @ {h['prospect_co']} — {h['generated_at'][:16]}": h["id"] for h in history}
        sel = st.selectbox("Seleziona kit", list(options.keys()), label_visibility="collapsed")
        if st.button("Carica questo kit", type="primary"):
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
