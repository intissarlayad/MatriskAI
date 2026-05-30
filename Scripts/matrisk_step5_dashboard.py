"""
MatriskAI — Dashboard Streamlit | Supply Chain Risk Intelligence
================================================================
VERSION 2.1 — Bugs corrigés
LANCER :
  streamlit run matrisk_step5_dashboard.py
  streamlit run matrisk_step5_dashboard.py -- --fichier /chemin/vers/mon_fichier.xlsx

FIXES v2.1 :
  - Navigation sidebar fonctionnelle (boutons invisibles mais cliquables via opacity:0 + position:absolute)
  - Bouton toggle thème visible (type="primary" exemptédu masquage)
  - Bouton "Effacer conversation" visible (type="primary")
  - CSS triple :root nettoyé (glassmorphism supprimé, nexus supprimé, tasko conservé)
  - Boucle infinie chat corrigée (flag st.session_state.pending_reply)
  - Colonne supplierHoldingName / fournisseur corrigée dans build_dashboard_context
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import os
import sys
import pickle
import io
import time
import json
import requests
from datetime import datetime, timedelta

# ── Chargement de la clé API depuis le fichier local .env (sécurisé pour Git)
_env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
if os.path.exists(_env_path):
    try:
        with open(_env_path, "r", encoding="utf-8") as f:
            for line in f:
                line_str = line.strip()
                if line_str and not line_str.startswith("#") and "=" in line_str:
                    k, v = line_str.split("=", 1)
                    os.environ[k.strip()] = v.strip()
    except Exception:
        pass


st.set_page_config(
    page_title="MatriskAI — Supply Chain Risk",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

if "ui_theme" not in st.session_state:
    st.session_state.ui_theme = "light"

# ── Gestion des query params (navigation depuis le bot flottant) ──
_qp = st.query_params
if "page" in _qp:
    st.session_state.page = _qp["page"]
if "q" in _qp:
    _question = _qp["q"]
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    # Éviter les doublons si la question est déjà la dernière
    if not st.session_state.chat_history or st.session_state.chat_history[-1].get("content") != _question:
        st.session_state.chat_history.append({"role": "user", "content": _question})
        st.session_state.pending_reply = True

if "page" in _qp or "q" in _qp:
    # Nettoyer les query params pour éviter les re-triggers
    st.query_params.clear()

# ══════════════════════════════════════════════════════════════════
# DESIGN SYSTEM — CSS (simplifié : un seul bloc :root actif)
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

/* ── LIGHT THEME (défaut) ── */
:root {
    --bg-base:        #F7FAF6;
    --bg-surface:     #FFFFFF;
    --bg-elevated:    #FFFFFF;
    --border:         #E4ECE3;
    --border-strong:  rgba(22,101,52,0.22);
    --text-primary:   #1F2A24;
    --text-secondary: #5B6B61;
    --text-muted:     #8A9A90;
    --accent-blue:    #2563EB;
    --accent-cyan:    #0EA5A4;
    --accent-purple:  #7C3AED;
    --accent-green:   #166534;
    --accent-amber:   #D97706;
    --accent-red:     #DC2626;
    --accent-orange:  #EA580C;
    --gradient-blue:  linear-gradient(135deg, #166534, #22C55E);
    --gradient-green: linear-gradient(135deg, #166534, #34D399);
    --gradient-red:   linear-gradient(135deg, #DC2626, #F97316);
    --glow-blue:      0 16px 42px rgba(22,101,52,0.12);
}

html, body, .stApp {
    font-family: 'Space Grotesk', sans-serif;
    background:
        radial-gradient(circle at 88% 8%, rgba(34,197,94,0.10), transparent 26rem),
        radial-gradient(circle at 8%  18%, rgba(22,101,52,0.06), transparent 28rem),
        linear-gradient(135deg, #F7FAF6 0%, #EFF6ED 100%) !important;
    color: var(--text-primary) !important;
}

.stApp > header {
    background: rgba(247,250,246,0.88) !important;
    border-bottom: 1px solid #E4ECE3 !important;
}

section[data-testid="stSidebar"] {
    background: rgba(255,255,255,0.94) !important;
    border-right: 1px solid #E4ECE3 !important;
    box-shadow: 18px 0 50px rgba(31,42,36,0.07);
}

.main .block-container {
    max-width: 1460px !important;
    padding-top: 1rem !important;
    padding-bottom: 3rem !important;
}

/* ── Typography ── */
h1 { font-family:'Space Grotesk',sans-serif!important; font-weight:700!important; font-size:1.75rem!important; color:#1F2A24!important; letter-spacing:-0.03em!important; margin-bottom:0!important; }
h2, h3 { font-family:'Space Grotesk',sans-serif!important; font-weight:600!important; color:#1F2A24!important; letter-spacing:0.04em!important; font-size:0.95rem!important; text-transform:uppercase; }
hr { border-color:#E4ECE3!important; margin:1.5rem 0!important; }

/* ── KPI Cards ── */
div[data-testid="metric-container"] {
    background:#FFFFFF!important;
    border:1px solid #E4ECE3!important;
    border-radius:16px!important;
    padding:1.2rem 1.3rem!important;
    min-height:124px;
    box-shadow:0 16px 40px rgba(31,42,36,0.08)!important;
    position:relative;
    overflow:hidden;
    transition:all 0.3s cubic-bezier(0.4,0,0.2,1)!important;
}
div[data-testid="metric-container"]::before {
    content:'';position:absolute;inset:0;border-radius:16px;
    background:radial-gradient(circle at 92% 12%, rgba(22,101,52,0.10), transparent 42%);
    pointer-events:none;
}
div[data-testid="metric-container"]:hover {
    border-color:rgba(22,101,52,0.22)!important;
    box-shadow:0 22px 52px rgba(31,42,36,0.12)!important;
    transform:translateY(-2px)!important;
}
div[data-testid="metric-container"] label { color:#6B7C71!important; font-size:0.68rem!important; font-weight:600!important; letter-spacing:0.1em!important; text-transform:uppercase!important; }
div[data-testid="metric-container"] div[data-testid="stMetricValue"] { color:#1F2A24!important; font-size:1.8rem!important; font-weight:700!important; font-family:'Space Grotesk',sans-serif!important; }

/* First KPI accent */
div[data-testid="stHorizontalBlock"] > div:nth-child(1) div[data-testid="metric-container"] { background:#166534!important; border-color:#166534!important; }
div[data-testid="stHorizontalBlock"] > div:nth-child(1) div[data-testid="metric-container"] label,
div[data-testid="stHorizontalBlock"] > div:nth-child(1) div[data-testid="metric-container"] div[data-testid="stMetricValue"],
div[data-testid="stHorizontalBlock"] > div:nth-child(1) div[data-testid="metric-container"] div { color:#ECFDF5!important; }

/* ── Boutons généraux ── */
.stButton > button {
    background:#FFFFFF!important;
    border:1px solid #E4ECE3!important;
    border-radius:12px!important;
    color:#1F2A24!important;
    font-family:'Space Grotesk',sans-serif!important;
    font-weight:600!important;
    font-size:0.85rem!important;
    padding:0.55rem 1.6rem!important;
    box-shadow:0 8px 22px rgba(31,42,36,0.06)!important;
    transition:all 0.25s ease!important;
}
.stButton > button:hover {
    background:#F1F6EF!important;
    border-color:rgba(22,101,52,0.22)!important;
    color:#166534!important;
}
/* Bouton primary (thème, clear chat, actions) */
.stButton > button[data-testid="baseButton-primary"],
.stButton > button[kind="primary"] {
    background:#166534!important;
    border-color:#166534!important;
    color:#FFFFFF!important;
    box-shadow:0 8px 22px rgba(22,101,52,0.18)!important;
}
.stButton > button[data-testid="baseButton-primary"]:hover,
.stButton > button[kind="primary"]:hover {
    background:#14532D!important;
    border-color:#14532D!important;
    color:#FFFFFF!important;
}

/* ── NAVIGATION SIDEBAR ──────────────────────────────────────────
   FIX: les boutons secondaires (nav) sont rendus invisibles MAIS
   restent cliquables via opacity:0 + position:absolute overlayés
   sur les div HTML qui les précèdent.
   Les boutons primary (toggle thème, effacer chat) restent visibles.
──────────────────────────────────────────────────────────────────*/
div[data-testid="stRadio"] { display:none!important; }

/* Conteneur du stButton nav : hauteur 0, overflow visible pour que le button absolument positionné remonte */
section[data-testid="stSidebar"] .stButton:has(button[data-testid="baseButton-secondary"]) {
    position:relative!important;
    height:0!important;
    overflow:visible!important;
    margin:0!important;
    padding:0!important;
}
/* Bouton nav : transparent, positionné par-dessus l'item HTML au-dessus */
section[data-testid="stSidebar"] button[data-testid="baseButton-secondary"] {
    position:absolute!important;
    bottom:0!important;
    left:0!important;
    width:100%!important;
    height:52px!important;
    opacity:0!important;
    cursor:pointer!important;
    z-index:20!important;
    padding:0!important;
    margin:0!important;
    border:none!important;
    background:transparent!important;
    box-shadow:none!important;
}

/* ── Nav item HTML ── */
.nav-item {
    display:flex; align-items:center; gap:10px;
    padding:9px 12px; border-radius:10px; margin-bottom:2px;
    cursor:pointer; transition:all 0.2s ease;
    min-height:52px;
    border:1px solid transparent;
    position:relative; z-index:1;
}
.nav-item:hover { background:rgba(22,101,52,0.06)!important; }
.nav-icon { width:30px; height:30px; border-radius:9px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.nav-label-main { font-family:'Space Grotesk',sans-serif; font-size:0.84rem; font-weight:700; line-height:1.2; color:#5B6B61; }
.nav-label-sub { font-size:0.65rem; color:#8A9A90; margin-top:1px; }

/* ── DataFrames ── */
div[data-testid="stDataFrame"] { border-radius:14px!important; border:1px solid #E4ECE3!important; }
div[data-testid="stDataFrame"] [role="grid"] { background:#FFFFFF!important; }

/* ── Charts panels ── */
div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stPlotlyChart"]),
div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stDataFrame"]) {
    background:#FFFFFF;
    border:1px solid #E4ECE3;
    border-radius:16px;
    padding:1rem;
    box-shadow:0 16px 42px rgba(31,42,36,0.08);
}

/* ── Alerts ── */
div[data-testid="stAlert"] {
    background:#FFFFFF!important; border:1px solid #E4ECE3!important;
    border-left:3px solid var(--accent-green)!important;
    color:#1F2A24!important; border-radius:12px!important;
    font-size:0.85rem!important;
    box-shadow:0 12px 30px rgba(31,42,36,0.06);
}

/* ── Inputs ── */
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div, textarea {
    background:#FFFFFF!important; border:1px solid #E4ECE3!important;
    border-radius:12px!important; color:#1F2A24!important;
}
div[data-testid="stFileUploader"] {
    background:rgba(22,101,52,0.03)!important;
    border:2px dashed rgba(22,101,52,0.25)!important;
    border-radius:16px!important; transition:all 0.3s ease!important;
}
div[data-testid="stFileUploader"]:hover {
    border-color:rgba(22,101,52,0.5)!important;
    background:rgba(22,101,52,0.06)!important;
}

/* ── Tabs ── */
button[data-baseweb="tab"] { font-family:'Space Grotesk',sans-serif!important; font-size:0.8rem!important; font-weight:500!important; color:#6B7C71!important; border-radius:12px!important; }
button[data-baseweb="tab"][aria-selected="true"] { background:#166534!important; color:#FFFFFF!important; }

/* ── Expander ── */
details { background:#FFFFFF!important; border:1px solid #E4ECE3!important; border-radius:12px!important; padding:0.4rem 0.8rem!important; }

/* ── Scrollbar ── */
::-webkit-scrollbar { width:6px; height:6px; }
::-webkit-scrollbar-track { background:transparent; }
::-webkit-scrollbar-thumb { background:rgba(22,101,52,0.15); border-radius:3px; }
::-webkit-scrollbar-thumb:hover { background:rgba(22,101,52,0.3); }

/* ── Animations ── */
@keyframes fadeInUp { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:translateY(0)} }
.animate-in { animation:fadeInUp 0.5s cubic-bezier(0.4,0,0.2,1) forwards; }

/* ── Logo ── */
.logo-block { display:flex; align-items:center; gap:0.7rem; padding:1.4rem 1rem 1.1rem; border-bottom:1px solid #E4ECE3; margin:0 -0.25rem 1rem; }
.logo-mark { width:34px; height:34px; background:#166534; border-radius:50%; box-shadow:0 12px 28px rgba(22,101,52,0.22); }
.logo-text { font-family:'Space Grotesk',sans-serif; font-size:1.1rem; font-weight:700; color:#1F2A24; }
.logo-sub  { font-size:0.6rem; color:#8A9A90; text-transform:uppercase; letter-spacing:0.1em; }

/* ── Topbar ── */
.topbar { display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:1rem 0 1.25rem; border-bottom:1px solid #E4ECE3; margin-bottom:1.4rem; }
.topbar-brand { display:flex; align-items:center; gap:0.75rem; }
.topbar-mark { width:32px; height:32px; background:#166534; border-radius:50%; }
.topbar-title { color:#1F2A24; font-size:1.05rem; font-weight:800; }
.topbar-sub   { color:#8A9A90; font-size:0.72rem; margin-top:1px; }
.topbar-tools { display:flex; align-items:center; gap:0.65rem; flex-wrap:wrap; justify-content:flex-end; }
.status-pill  { display:inline-flex; align-items:center; gap:0.45rem; min-height:36px; padding:0 0.85rem; border:1px solid #E4ECE3; border-radius:999px; background:#FFFFFF; color:#5B6B61; font-size:0.78rem; box-shadow:0 4px 12px rgba(31,42,36,0.06); }
.status-dot   { width:7px; height:7px; border-radius:999px; background:#16A34A; box-shadow:0 0 0 5px rgba(34,197,94,0.12); }

/* ── Ops grid ── */
.ops-grid { display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:0.85rem; margin:0 0 1.25rem; }
.ops-card { min-height:108px; padding:0.95rem 1rem; border:1px solid #E4ECE3; border-radius:16px; background:#FFFFFF; box-shadow:0 14px 36px rgba(31,42,36,0.08); }
.ops-card:first-child { background:#166534; border-color:#166534; }
.ops-card:first-child .ops-label, .ops-card:first-child .ops-value, .ops-card:first-child .ops-note { color:#ECFDF5; }
.ops-label { color:#8A9A90; font-size:0.66rem; font-weight:800; letter-spacing:0.1em; text-transform:uppercase; }
.ops-value { margin-top:0.38rem; color:#1F2A24; font-family:'JetBrains Mono',monospace; font-size:1.55rem; font-weight:700; }
.ops-note  { margin-top:0.2rem; color:#6B7C71; font-size:0.72rem; }
@media(max-width:760px)  { .ops-grid{ grid-template-columns:1fr; } }
@media(min-width:761px) and (max-width:1120px) { .ops-grid{ grid-template-columns:repeat(2,minmax(0,1fr)); } }

/* ── AI banner ── */
.ai-banner { background:#FFFFFF!important; border:1px solid #E4ECE3!important; border-top:2px solid #166534!important; border-radius:16px!important; padding:1rem 1.2rem; margin:0.8rem 0; box-shadow:0 14px 36px rgba(31,42,36,0.07); }
.ai-banner-label { font-size:0.62rem; font-weight:700; text-transform:uppercase; letter-spacing:0.12em; color:#166534; margin-bottom:0.3rem; }
.ai-banner-text  { font-size:0.88rem; color:#1F2A24; line-height:1.5; }
.ai-banner-text strong { color:#1F2A24; }

/* ── Section header ── */
.section-header { display:flex; align-items:center; gap:10px; margin-bottom:0.8rem; margin-top:1.2rem; }
.section-dot    { width:6px; height:6px; border-radius:50%; background:#166534; box-shadow:0 0 0 5px rgba(22,101,52,0.10); }
.section-title  { font-size:0.82rem; font-weight:700; color:#1F2A24; }

/* ── Badges ── */
.badge         { display:inline-flex; align-items:center; gap:5px; padding:3px 10px; border-radius:20px; font-size:0.7rem; font-weight:600; letter-spacing:0.05em; }
.badge-red     { background:rgba(220,38,38,0.12);  color:#DC2626; border:1px solid rgba(220,38,38,0.2); }
.badge-amber   { background:rgba(217,119,6,0.12);  color:#D97706; border:1px solid rgba(217,119,6,0.2); }
.badge-green   { background:#DCFCE7; color:#166534; border:1px solid #BBF7D0; }
.badge-blue    { background:#EEF5EC; color:#166534; border:1px solid #DCEBDA; }
.badge-purple  { background:#F3E8FF; color:#7C3AED; border:1px solid #E9D5FF; }
.badge-cyan    { background:rgba(14,165,164,0.12); color:#0EA5A4; border:1px solid rgba(14,165,164,0.2); }

/* ── Sidebar status bars ── */
.side-status { margin:0.35rem 0 0.95rem; }
.side-label  { display:flex; justify-content:space-between; color:#5B6B61; font-size:0.76rem; }
.side-bar    { height:7px; margin-top:0.38rem; background:#EEF5EC; border-radius:999px; overflow:hidden; }
.side-fill   { height:100%; border-radius:inherit; }

/* ── Quick actions ── */
.quick-actions { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:0.7rem; margin:0.7rem 0 0.2rem; }
.quick-action  { min-height:74px; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:0.45rem; border:1px solid #E4ECE3; border-radius:10px; background:#F7FAF6; color:#1F2A24; font-size:0.78rem; font-weight:700; }
.quick-action span:first-child { color:#166534; font-size:1.05rem; }

/* ── Pipeline step ── */
.pipeline-step { background:#FFFFFF; border:1px solid #E4ECE3; border-radius:12px; padding:1rem 1.2rem; margin-bottom:0.5rem; display:flex; align-items:center; gap:12px; transition:all 0.2s ease; }
.pipeline-step:hover { border-color:rgba(22,101,52,0.22); }
.pipeline-step-num   { width:28px; height:28px; border-radius:8px; background:#DCFCE7; color:#166534; font-size:0.75rem; font-weight:700; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.pipeline-step-info  { flex:1; }
.pipeline-step-title { font-size:0.84rem; font-weight:600; color:#1F2A24; }
.pipeline-step-desc  { font-size:0.7rem; color:#8A9A90; margin-top:2px; }

/* ── Upload zone ── */
.upload-zone { background:rgba(22,101,52,0.04); border:2px dashed rgba(22,101,52,0.25); border-radius:16px; padding:2rem; text-align:center; transition:all 0.3s ease; }
.upload-zone:hover { border-color:rgba(22,101,52,0.5); background:rgba(22,101,52,0.08); }

/* ── Chat ── */
.chat-msg   { display:flex; gap:0.75rem; align-items:flex-start; animation:fadeInUp 0.3s ease; }
.chat-msg.user { flex-direction:row-reverse; }
.chat-avatar { width:34px; height:34px; border-radius:10px; display:flex; align-items:center; justify-content:center; font-size:0.85rem; flex-shrink:0; font-weight:700; }
.chat-avatar.bot  { background:#166534; color:#fff; }
.chat-avatar.user { background:#E4ECE3; color:#5B6B61; border:1px solid #E4ECE3; }
.chat-bubble      { max-width:75%; padding:0.75rem 1rem; border-radius:14px; font-size:0.87rem; line-height:1.6; }
.chat-bubble.bot  { background:#FFFFFF; border:1px solid #E4ECE3; color:#1F2A24; border-top-left-radius:4px; box-shadow:0 8px 20px rgba(31,42,36,0.06); }
.chat-bubble.user { background:#166534; color:#fff; border-top-right-radius:4px; }
.chat-bubble.bot strong { color:#166534; }
.chat-welcome     { text-align:center; padding:2.5rem 1.5rem; color:#8A9A90; }
.chat-welcome h3  { color:#1F2A24; font-size:1rem; margin-bottom:0.4rem; }
.chat-welcome p   { font-size:0.8rem; margin:0; }

/* ── Misc ── */
.stMarkdown p { color:#5B6B61; }
.stCaption, small { color:#8A9A90!important; font-size:0.7rem!important; }
</style>
""", unsafe_allow_html=True)

# ── Dark mode override ────────────────────────────────────────────
if st.session_state.ui_theme == "dark":
    st.markdown("""
<style>
:root {
    --bg-base:        #0D1511;
    --bg-surface:     #111C16;
    --bg-elevated:    #16231C;
    --border:         rgba(194,214,199,0.14);
    --text-primary:   #F2F8F3;
    --text-secondary: #BDD0C2;
    --text-muted:     #7F9887;
}
html, body, .stApp {
    background:
        radial-gradient(circle at 88% 8%,  rgba(74,222,128,0.13), transparent 28rem),
        radial-gradient(circle at 12% 18%, rgba(20,184,166,0.08), transparent 26rem),
        linear-gradient(135deg, #08100C 0%, #111C16 100%) !important;
    color:#F2F8F3!important;
}
.stApp > header                           { background:rgba(8,16,12,0.88)!important; border-bottom-color:rgba(194,214,199,0.14)!important; }
section[data-testid="stSidebar"]          { background:rgba(13,21,17,0.96)!important; border-right-color:rgba(194,214,199,0.14)!important; }
h1, h2, h3, .topbar-title, .section-title,
.ops-value, .logo-text                    { color:#F2F8F3!important; }
.logo-sub, .topbar-sub, .nav-label-sub, .ops-note, .side-label { color:#8EA092!important; }
.ops-card, .ai-banner, .pipeline-step,
.quick-action, .status-pill               { background:#111C16!important; border-color:rgba(194,214,199,0.14)!important; color:#F2F8F3!important; }
div[data-testid="metric-container"]       { background:#111C16!important; border-color:rgba(194,214,199,0.14)!important; box-shadow:0 16px 42px rgba(0,0,0,0.24)!important; }
div[data-testid="metric-container"] label { color:#8EA092!important; }
div[data-testid="metric-container"] div[data-testid="stMetricValue"] { color:#F2F8F3!important; }
div[data-testid="stHorizontalBlock"] > div:nth-child(1) div[data-testid="metric-container"] { background:#2F7D46!important; border-color:#2F7D46!important; }
div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stPlotlyChart"]),
div[data-testid="stVerticalBlock"] > div:has(> div[data-testid="stDataFrame"]) { background:#111C16!important; border-color:rgba(194,214,199,0.14)!important; }
div[data-testid="stDataFrame"] [role="grid"] { background:rgba(13,21,17,0.8)!important; }
.stButton > button                        { background:#111C16!important; border-color:rgba(194,214,199,0.14)!important; color:#F2F8F3!important; }
.stButton > button[data-testid="baseButton-primary"],
.stButton > button[kind="primary"]        { background:#2F7D46!important; border-color:#2F7D46!important; color:#ECFDF5!important; }
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div, textarea { background:#16231C!important; border-color:rgba(194,214,199,0.14)!important; color:#F2F8F3!important; }
button[data-baseweb="tab"][aria-selected="true"] { background:#2F7D46!important; }
div[data-testid="stAlert"]                { background:#111C16!important; border-color:rgba(194,214,199,0.14)!important; color:#F2F8F3!important; }
.nav-item:hover                           { background:rgba(74,222,128,0.06)!important; }
.nav-label-main                           { color:#BDD0C2!important; }
.side-bar                                 { background:rgba(194,214,199,0.12)!important; }
.chat-bubble.bot                          { background:#16231C!important; border-color:rgba(194,214,199,0.14)!important; color:#F2F8F3!important; }
.stMarkdown p                             { color:#BDD0C2!important; }
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# UTILITAIRES DESIGN
# ══════════════════════════════════════════════════════════════════
def ai_banner(text: str, icon: str = "✦"):
    st.markdown(f"""
    <div class="ai-banner animate-in">
      <div class="ai-banner-label">{icon} IA Insight</div>
      <div class="ai-banner-text">{text}</div>
    </div>""", unsafe_allow_html=True)

def section_header(title: str, color: str = "#166534"):
    st.markdown(f"""
    <div class="section-header">
      <div class="section-dot" style="background:{color};box-shadow:0 0 0 5px {color}22;"></div>
      <div class="section-title">{title}</div>
    </div>""", unsafe_allow_html=True)

def badge(text: str, cls: str = "blue"):
    return f'<span class="badge badge-{cls}">{text}</span>'

def topbar(page_name: str):
    today = datetime.now().strftime("%d/%m/%Y")
    total_label = f"{len(df_pred):,} matériaux" if not df_pred.empty else "Données non chargées"
    theme_label = "Dark" if st.session_state.ui_theme == "dark" else "Light"
    st.markdown(f"""
    <div class="topbar">
      <div class="topbar-brand">
        <div class="topbar-mark"></div>
        <div>
          <div class="topbar-title">MatriskAI</div>
          <div class="topbar-sub">Supply Chain Risk Intelligence · {page_name}</div>
        </div>
      </div>
      <div class="topbar-tools">
        <div class="status-pill"><span class="status-dot"></span>LIVE</div>
        <div class="status-pill">◐ {theme_label}</div>
        <div class="status-pill">{today}</div>
        <div class="status-pill">{total_label}</div>
      </div>
    </div>""", unsafe_allow_html=True)

def _pct(value, default: str = "0%") -> str:
    if pd.isna(value):
        return default
    return f"{float(value):.0f}%"

def operations_strip():
    if df_pred.empty:
        st.markdown("""
        <div class="ops-grid">
          <div class="ops-card">
            <div class="ops-label">Statut données</div>
            <div class="ops-value">OFFLINE</div>
            <div class="ops-note">Lancez les étapes pipeline pour charger les fichiers.</div>
          </div>
        </div>""", unsafe_allow_html=True)
        return

    n_total  = len(df_pred)
    n_eleve  = int((df_pred["predicted_label"] == "Élevé").sum())  if "predicted_label"   in df_pred.columns else 0
    pct_eleve = (n_eleve / n_total * 100) if n_total else 0
    n_fourn  = df_pred["supplierHoldingName"].nunique() if "supplierHoldingName" in df_pred.columns else 0
    conf_moy = df_pred["confiance_finale"].mean()       if "confiance_finale"    in df_pred.columns else np.nan
    sri_moy  = df_pred["SRI"].mean()                   if "SRI"                 in df_pred.columns else np.nan
    fiab     = df_forc["fiabilite_forecast"].mean()     if not df_forc.empty and "fiabilite_forecast" in df_forc.columns else np.nan
    snapshots = df_hist["date"].nunique()               if not df_hist.empty and "date"    in df_hist.columns else 0

    st.markdown(f"""
    <div class="ops-grid">
      <div class="ops-card">
        <div class="ops-label">Risque élevé</div>
        <div class="ops-value">{n_eleve}</div>
        <div class="ops-note">{pct_eleve:.1f}% du portefeuille surveillé</div>
      </div>
      <div class="ops-card">
        <div class="ops-label">Fournisseurs</div>
        <div class="ops-value">{n_fourn}</div>
        <div class="ops-note">Périmètre actif selon les données chargées</div>
      </div>
      <div class="ops-card">
        <div class="ops-label">SRI moyen</div>
        <div class="ops-value">{_pct(sri_moy)}</div>
        <div class="ops-note">Confiance IA moyenne : {_pct(conf_moy)}</div>
      </div>
      <div class="ops-card">
        <div class="ops-label">Forecast</div>
        <div class="ops-value">{_pct(fiab) if not pd.isna(fiab) else snapshots}</div>
        <div class="ops-note">{"Fiabilité moyenne" if not pd.isna(fiab) else "snapshots historiques"}</div>
      </div>
    </div>""", unsafe_allow_html=True)

def sidebar_status_panel():
    if df_pred.empty:
        return
    n_total = len(df_pred)
    high_pct   = (int((df_pred["predicted_label"] == "Élevé").sum()) / n_total * 100) if "predicted_label" in df_pred.columns and n_total else 0
    medium_pct = (int((df_pred["predicted_label"] == "Moyen").sum()) / n_total * 100) if "predicted_label" in df_pred.columns and n_total else 0
    conf = df_pred["confiance_finale"].mean() if "confiance_finale" in df_pred.columns else 0
    sri  = df_pred["SRI"].mean()              if "SRI"              in df_pred.columns else 0
    items = [
        ("Risque élevé", high_pct,   "#DC2626"),
        ("Risque moyen", medium_pct, "#D97706"),
        ("Confiance IA", conf,       "#166534"),
        ("SRI moyen",    sri,        "#0EA5A4"),
    ]
    html = ['<div style="border-top:1px solid #E4ECE3;padding-top:1rem;margin-top:1rem">']
    html.append('<div style="font-size:0.65rem;font-weight:800;color:#8A9A90;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.75rem">System status</div>')
    for label, value, color in items:
        v = max(0, min(float(value or 0), 100))
        html.append(f"""
        <div class="side-status">
          <div class="side-label"><span>{label}</span><span>{v:.0f}%</span></div>
          <div class="side-bar"><div class="side-fill" style="width:{v:.0f}%;background:{color}"></div></div>
        </div>""")
    html.append("</div>")
    st.markdown("".join(html), unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# PALETTE & PLOTLY
# ══════════════════════════════════════════════════════════════════
COULEURS = {"Élevé": "#DC2626", "Moyen": "#D97706", "Faible": "#16A34A"}
COULEURS_CLUSTER = {
    "Stable fiable": "#16A34A", "En dégradation": "#EA580C",
    "Fragile": "#DC2626",       "À surveiller": "#D97706",
}

_is_dark   = st.session_state.ui_theme == "dark"
PLOTLY_TEXT = "#BDD0C2" if _is_dark else "#5B6B61"
PLOTLY_TICK = "#8EA092" if _is_dark else "#8A9A90"
PLOTLY_GRID = "rgba(194,214,199,0.12)" if _is_dark else "rgba(22,101,52,0.07)"
PLOTLY_LINE = "rgba(194,214,199,0.16)" if _is_dark else "rgba(22,101,52,0.10)"

PLOTLY_BASE = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor ="rgba(0,0,0,0)",
    font=dict(family="Space Grotesk", color=PLOTLY_TEXT, size=11.5),
    margin=dict(t=28, b=30, l=10, r=10),
)
_AXIS = dict(gridcolor=PLOTLY_GRID, linecolor=PLOTLY_LINE, zerolinecolor=PLOTLY_LINE,
             tickfont=dict(size=10.5, color=PLOTLY_TICK))

def plotly_layout(**extra):
    base = {**PLOTLY_BASE, "xaxis": _AXIS, "yaxis": _AXIS}
    for k, v in extra.items():
        if k in ("xaxis", "yaxis") and isinstance(v, dict):
            base[k] = {**_AXIS, **v}
        else:
            base[k] = v
    return base

# ══════════════════════════════════════════════════════════════════
# CHEMINS & CHARGEMENT
# ══════════════════════════════════════════════════════════════════
BASE_PATH    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FICHIERS_DIR = os.path.join(BASE_PATH, "Fichiers Excel")

FICHIER_CUSTOM = None
# BUG FIX : Streamlit injecte ses propres arguments dans sys.argv.
# On parse uniquement les args APRÈS "--" (séparateur Streamlit).
_raw_args = sys.argv[1:]
try:
    _sep = _raw_args.index("--")
    _user_args = _raw_args[_sep + 1:]
except ValueError:
    _user_args = _raw_args
for _i, _a in enumerate(_user_args):
    if _a == "--fichier" and _i + 1 < len(_user_args):
        FICHIER_CUSTOM = _user_args[_i + 1]
        break

@st.cache_data
def charger_donnees():
    chemins = {
        "predictions": os.path.join(FICHIERS_DIR, "step2_predictions.csv"),
        "forecast"   : os.path.join(BASE_PATH, "step3_forecast_fournisseurs.csv"),
        "actions"    : os.path.join(BASE_PATH, "step4_plan_actions.csv"),
        "materiaux"  : os.path.join(BASE_PATH, "step3_forecast_materiaux.csv"),
        "historique" : os.path.join(BASE_PATH, "historique_sri.csv"),
    }
    data = {}
    for nom, chemin in chemins.items():
        if os.path.exists(chemin):
            d = pd.read_csv(chemin, sep=",", encoding="utf-8-sig")
            d.columns = [c.strip() for c in d.columns]
            data[nom] = d
        else:
            data[nom] = pd.DataFrame()
    return data

data    = charger_donnees()
df_pred = data.get("predictions", pd.DataFrame())
df_forc = data.get("forecast",    pd.DataFrame())
df_act  = data.get("actions",     pd.DataFrame())
df_mat  = data.get("materiaux",   pd.DataFrame())
df_hist = data.get("historique",  pd.DataFrame())

# ══════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("""
    <div class="logo-block">
      <div class="logo-mark"></div>
      <div>
        <div class="logo-text">MatriskAI</div>
        <div class="logo-sub">Supply Chain Risk · v2.1</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # FIX: type="primary" → bouton visible (non masqué par le CSS nav)
    theme_next  = "light" if st.session_state.ui_theme == "dark" else "dark"
    theme_label = "◯ Mode clair" if st.session_state.ui_theme == "dark" else "◐ Mode sombre"
    if st.button(theme_label, key="toggle_ui_theme", use_container_width=True, type="primary"):
        st.session_state.ui_theme = theme_next
        st.rerun()

    st.divider()

    if "page" not in st.session_state:
        st.session_state.page = "Vue Globale"

    NAV = [
        ("Vue Globale",        "Vue Globale",        "Tableau de bord",       "#166534",
         '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" width="16" height="16"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 12L11.204 3.045a1.125 1.125 0 011.591 0L21.75 12M4.5 9.75V19.5a.75.75 0 00.75.75h4.5a.75.75 0 00.75-.75v-4.5a.75.75 0 01.75-.75h3a.75.75 0 01.75.75V19.5a.75.75 0 00.75.75h4.5a.75.75 0 00.75-.75V9.75"/></svg>'),
        ("Données & Pipeline", "Données & Pipeline", "Upload · Déclenchement","#0EA5A4",
         '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" width="16" height="16"><path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5"/></svg>'),
        ("Time Series IA",     "Time Series IA",     "Prophet · Anomalies",   "#16A34A",
         '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" width="16" height="16"><path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z"/></svg>'),
        ("Prévisions J+90",    "Prévisions J+90",    "Forecast fournisseurs", "#7C3AED",
         '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" width="16" height="16"><path stroke-linecap="round" stroke-linejoin="round" d="M2.25 18L9 11.25l4.306 4.307a11.95 11.95 0 015.814-5.519l2.74-1.22m0 0l-5.94-2.28m5.94 2.28l-2.28 5.941"/></svg>'),
        ("Plan d'Actions",     "Plan d'Actions",     "Prescriptif",           "#D97706",
         '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" width="16" height="16"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25z"/></svg>'),
        ("Explainability SHAP","Explainability SHAP","Analyse SHAP",          "#0EA5A4",
         '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" width="16" height="16"><path stroke-linecap="round" stroke-linejoin="round" d="M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M6 20.25h12A2.25 2.25 0 0020.25 18V6A2.25 2.25 0 0018 3.75H6A2.25 2.25 0 003.75 6v12A2.25 2.25 0 006 20.25z"/></svg>'),
        ("Anomalies",          "Anomalies",          "Isolation Forest",      "#DC2626",
         '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" width="16" height="16"><path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z"/></svg>'),
        ("Simulateur What-If", "Simulateur What-If", "Scénarios",             "#EA580C",
         '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" width="16" height="16"><path stroke-linecap="round" stroke-linejoin="round" d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0112 15a9.065 9.065 0 00-6.23-.693L5 14.5m14.8.8l1.402 1.402c1 1-.34 2.75-1.931 2.067L12 16.5l-7.271 1.269c-1.591.683-2.931-1.067-1.931-2.067L4.2 14.3"/></svg>'),
        ("Assistant IA",       "Assistant IA",       "Chatbot dashboard",     "#7C3AED",
         '<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="currentColor" width="16" height="16"><path stroke-linecap="round" stroke-linejoin="round" d="M8.625 12a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H8.25m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0H12m4.125 0a.375.375 0 11-.75 0 .375.375 0 01.75 0zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 01-2.555-.337A5.972 5.972 0 015.41 20.97a5.969 5.969 0 01-.474-.065 4.48 4.48 0 00.978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25z"/></svg>'),
    ]

    for key, label, sub, color, icon_svg in NAV:
        active  = st.session_state.page == key
        bg_item = f"rgba(22,101,52,0.08)" if active else "transparent"
        bg_icon = color + "22"
        border  = f"border-left:3px solid {color};" if active else "border-left:3px solid transparent;"
        label_color = "#1F2A24" if active else "#5B6B61"
        # HTML nav item (visuel)
        st.markdown(f"""
        <div class="nav-item" style="background:{bg_item};{border}">
          <div class="nav-icon" style="background:{bg_icon};color:{color};">{icon_svg}</div>
          <div>
            <div class="nav-label-main" style="color:{label_color}">{label}</div>
            <div class="nav-label-sub">{sub}</div>
          </div>
        </div>""", unsafe_allow_html=True)
        # Bouton fonctionnel (secondary → overlay transparent cliquable via CSS)
        if st.button(label, key="nav_" + key, use_container_width=True):
            st.session_state.page = key
            st.rerun()

    page = st.session_state.page
    st.divider()

    # ── Filtres ──────────────────────────────────────────────────
    st.markdown('<p style="font-size:0.65rem;font-weight:700;color:#8A9A90;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:0.5rem">Filtres globaux</p>', unsafe_allow_html=True)
    if not df_pred.empty:
        niveaux   = st.multiselect("Niveau de risque", ["Élevé","Moyen","Faible"], default=["Élevé","Moyen"])
        col_fourn = "supplierHoldingName"
        fourn_sel = st.selectbox("Fournisseur", ["Tous"] + sorted(df_pred[col_fourn].dropna().unique().tolist())) if col_fourn in df_pred.columns else "Tous"
    else:
        niveaux, fourn_sel = ["Élevé","Moyen"], "Tous"

    st.divider()
    sidebar_status_panel()

    nb_snapshots = df_hist["date"].nunique() if not df_hist.empty and "date" in df_hist.columns else 0
    st.caption(f"Snapshots historique : {nb_snapshots}")
    if FICHIER_CUSTOM:
        st.caption(f"◇ Fichier custom : `{os.path.basename(FICHIER_CUSTOM)}`")
    st.caption("Pipeline : Nettoyage → ML → Forecast → Prescriptif → Dashboard")

# ══════════════════════════════════════════════════════════════════
# TOPBAR & OPS STRIP (toutes les pages)
# ══════════════════════════════════════════════════════════════════
topbar(page)
operations_strip()

# ══════════════════════════════════════════════════════════════════
# PAGE : DONNÉES & PIPELINE
# ══════════════════════════════════════════════════════════════════
if page == "Données & Pipeline":
    st.title("Données & Pipeline")
    st.markdown(badge("Nouveau","purple"), unsafe_allow_html=True)
    ai_banner(
        "Importez un nouvel Excel pour relancer automatiquement le pipeline complet. "
        "Chaque import crée un snapshot horodaté pour le suivi temporel."
    )

    tab1, tab2 = st.tabs(["◇ Upload & Déclenchement", "↗ État du Pipeline"])

    with tab1:
        section_header("IMPORTER UN NOUVEL EXCEL")
        st.markdown("""
        <div class="upload-zone">
          <p style="font-size:2rem;margin:0">📁</p>
          <p style="color:#5B6B61;font-size:0.9rem;margin:0.3rem 0">Glissez votre fichier Excel ou cliquez pour parcourir</p>
          <p style="color:#8A9A90;font-size:0.72rem;margin:0">Formats acceptés : .xlsx · .xls · .csv</p>
        </div>""", unsafe_allow_html=True)

        uploaded_file = st.file_uploader("Choisir un fichier", type=["xlsx","xls","csv"], label_visibility="collapsed")

        if uploaded_file is not None:
            st.success(f"✓ Fichier chargé : **{uploaded_file.name}** ({uploaded_file.size/1024:.1f} KB)")
            try:
                df_new = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
                st.markdown(f"""<div style="display:flex;gap:12px;margin:0.8rem 0">
                  {badge(f"{len(df_new):,} lignes","blue")}
                  {badge(f"{len(df_new.columns)} colonnes","purple")}
                  {badge("Chargé avec succès","green")}
                </div>""", unsafe_allow_html=True)
                with st.expander("Aperçu (5 premières lignes)"):
                    st.dataframe(df_new.head(), use_container_width=True)

                section_header("COLONNES DÉTECTÉES", "#16A34A")
                expected_cols = ["STMaterialCode","STMaterialDesc","supplierHoldingName",
                                 "qml_risk_score","asl_risk_score","shelf_life_risk",
                                 "has_ecertificate","days_since_update"]
                col_status = [{"Colonne": c, "Statut": "✓ Présente" if c in df_new.columns else "✗ Manquante",
                               "Type": str(df_new[c].dtype) if c in df_new.columns else "—"} for c in expected_cols]
                st.dataframe(pd.DataFrame(col_status), use_container_width=True, height=250)

                section_header("DÉCLENCHER LE PIPELINE")
                c1, c2, c3 = st.columns(3)
                run_full     = c1.checkbox("Step 1 — Nettoyage",    value=True)
                run_ml       = c2.checkbox("Step 2 — ML / XGBoost", value=True)
                run_forecast = c3.checkbox("Step 3 — Forecast",     value=True)

                if st.button("↗ Lancer le pipeline", type="primary"):
                    os.makedirs(FICHIERS_DIR, exist_ok=True)
                    
                    # Sauvegarder le fichier importé
                    saved_file_path = os.path.join(FICHIERS_DIR, uploaded_file.name)
                    try:
                        with open(saved_file_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                    except Exception as e:
                        st.error(f"Erreur lors de la sauvegarde du fichier importé : {e}")
                        st.stop()
                        
                    progress_bar = st.progress(0)
                    status_text  = st.empty()
                    steps = []
                    if run_full:     
                        steps.append(("Nettoyage & feature engineering", "matrisk_step1_cleaning.py"))
                    if run_ml:       
                        steps.append(("Entraînement XGBoost + prédictions", "matrisk_step2_train.py"))
                    if run_forecast: 
                        steps.append(("Forecast (mode rapide)", "matrisk_step3_forecast.py"))
                        steps.append(("Moteur Prescriptif", "matrisk_step4_prescriptif.py"))
                    
                    import subprocess, copy
                    # Passer NO_PROPHET=1 pour éviter la compilation Stan (très lente sur cloud)
                    env_cloud = copy.copy(os.environ)
                    env_cloud["NO_PROPHET"] = "1"

                    success = True
                    for i, (desc, script_name) in enumerate(steps):
                        status_text.markdown(f'<p style="color:#5B6B61;font-size:0.85rem">⚙ {desc} en cours…</p>', unsafe_allow_html=True)
                        progress_bar.progress((i + 0.1) / len(steps))
                        
                        script_path = os.path.join(BASE_PATH, script_name)
                        cmd = [sys.executable, script_path]
                        if script_name == "matrisk_step1_cleaning.py":
                            cmd.extend(["--fichier", saved_file_path])
                            
                        try:
                            result = subprocess.run(
                                cmd,
                                cwd=BASE_PATH,
                                capture_output=True,
                                text=True,
                                encoding="utf-8",
                                errors="ignore",
                                env=env_cloud,
                                timeout=180  # 3 minutes max par étape
                            )
                            if result.returncode == 0:
                                progress_bar.progress((i + 1.0) / len(steps))
                            else:
                                success = False
                                status_text.markdown(f'<p style="color:#DC2626;font-size:0.85rem">❌ Échec de l\'étape : {desc}</p>', unsafe_allow_html=True)
                                st.error(f"Erreur lors de l'exécution de {script_name} (code retour {result.returncode})")
                                with st.expander("Détails de l'erreur (Stderr/Stdout)"):
                                    st.code(result.stderr or result.stdout)
                                break
                        except subprocess.TimeoutExpired:
                            success = False
                            status_text.markdown(f'<p style="color:#DC2626;font-size:0.85rem">⏱ Timeout : {desc} a dépassé 3 minutes</p>', unsafe_allow_html=True)
                            st.error(f"L'étape '{desc}' a dépassé le délai maximum (3 min). Relancez le pipeline.")
                            break
                        except Exception as e:
                            success = False
                            status_text.markdown(f'<p style="color:#DC2626;font-size:0.85rem">❌ Erreur de lancement : {desc}</p>', unsafe_allow_html=True)
                            st.error(f"Exception : {e}")
                            break
                            
                    if success:
                        status_text.markdown('<p style="color:#16A34A;font-size:0.85rem">✓ Pipeline terminé avec succès</p>', unsafe_allow_html=True)
                        st.balloons()
                        st.success("Pipeline exécuté avec succès. Les KPIs ont été mis à jour.")
                        st.cache_data.clear()
                        st.rerun()
            except Exception as e:
                st.error(f"Erreur de lecture : {e}")
        else:
            st.info("Aucun fichier sélectionné. Importez un Excel pour commencer.")

    with tab2:
        section_header("ÉTAT DES FICHIERS PIPELINE")
        fichiers_pipeline = {
            "step2_predictions.csv"          : ("Prédictions ML",       "excel"),
            "step3_forecast_fournisseurs.csv": ("Forecast fournisseurs", "base"),
            "step4_plan_actions.csv"         : ("Plan d'actions",        "base"),
            "step3_forecast_materiaux.csv"   : ("Forecast matériaux",    "base"),
            "historique_sri.csv"             : ("Historique SRI",        "base"),
            "xgb_model.pkl"                  : ("Modèle XGBoost",        "base"),
            "shap_importance_bar.png"        : ("SHAP — importance",     "base"),
        }
        for fname, (label, folder) in fichiers_pipeline.items():
            full   = os.path.join(FICHIERS_DIR if folder == "excel" else BASE_PATH, fname)
            exists = os.path.exists(full)
            if exists:
                mtime   = datetime.fromtimestamp(os.path.getmtime(full)).strftime("%d/%m/%Y %H:%M")
                size_kb = os.path.getsize(full) / 1024
                status_html = badge("✓ Présent", "green")
                detail = f'<span style="color:#8A9A90;font-size:0.7rem">{mtime} · {size_kb:.1f} KB</span>'
            else:
                status_html = badge("✗ Manquant", "red")
                detail = '<span style="color:#8A9A90;font-size:0.7rem">Non généré</span>'
            st.markdown(f"""
            <div class="pipeline-step">
              <div class="pipeline-step-num">{"✓" if exists else "!"}</div>
              <div class="pipeline-step-info">
                <div class="pipeline-step-title">{label}</div>
                <div class="pipeline-step-desc">{fname}</div>
              </div>
              <div>{status_html} {detail}</div>
            </div>""", unsafe_allow_html=True)

        st.divider()
        section_header("COMMENT RELANCER MANUELLEMENT")
        st.code("""python matrisk_step1_cleaning.py
python matrisk_step2_train.py
python matrisk_step3_forecast.py
python matrisk_step4_prescriptif.py

# Avec un fichier Excel custom :
python matrisk_step1_cleaning.py --fichier /chemin/vers/mon_fichier.xlsx
streamlit run matrisk_step5_dashboard.py -- --fichier /chemin/vers/mon_fichier.xlsx""", language="bash")

# ══════════════════════════════════════════════════════════════════
# PAGE : VUE GLOBALE
# ══════════════════════════════════════════════════════════════════
elif page == "Vue Globale":
    st.title("Vue Globale")
    if df_pred.empty:
        st.error("Données non disponibles. Lancez d'abord les étapes 1 à 4.")
        st.stop()

    n_total  = len(df_pred)
    n_eleve  = int((df_pred["predicted_label"] == "Élevé").sum())
    n_moyen  = int((df_pred["predicted_label"] == "Moyen").sum())
    n_faible = int((df_pred["predicted_label"] == "Faible").sum())
    n_fourn  = df_pred["supplierHoldingName"].nunique() if "supplierHoldingName" in df_pred.columns else 0
    conf_moy = df_pred["confiance_finale"].mean() if "confiance_finale" in df_pred.columns else 0

    pct_eleve = n_eleve / n_total if n_total else 0
    if pct_eleve > 0.3:
        ai_banner(f"<strong>{pct_eleve:.0%} des matériaux sont en risque élevé</strong> — niveau critique. Priorisez immédiatement les fournisseurs fragiles et déclenchez les actions de contingence pour les matériaux à score SRI < 30.")
    elif pct_eleve > 0.15:
        ai_banner(f"<strong>{n_eleve} matériaux en risque élevé</strong> sur {n_total} — situation sous contrôle mais vigilance requise. Consultez le plan d'actions pour les priorités 1.")
    else:
        ai_banner(f"<strong>Portefeuille globalement sain</strong> — seulement {n_eleve} matériaux en risque élevé. Maintenez la surveillance des fournisseurs 'À surveiller'.")

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    c1.metric("Matériaux",     f"{n_total:,}")
    c2.metric("Risque élevé",  f"{n_eleve}",  f"{n_eleve/n_total:.1%}")
    c3.metric("Risque moyen",  f"{n_moyen}",  f"{n_moyen/n_total:.1%}")
    c4.metric("Risque faible", f"{n_faible}", f"{n_faible/n_total:.1%}")
    c5.metric("Fournisseurs",  f"{n_fourn}")
    c6.metric("Confiance IA",  f"{conf_moy:.0f}%")

    # ── Accès rapide au chatbot ──────────────────────────────────
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #1a2e1a 0%, #0d1f0d 100%);
        border: 1px solid #2d5a2d;
        border-radius: 16px;
        padding: 20px 24px;
        margin: 16px 0;
        display: flex;
        align-items: flex-start;
        gap: 18px;
    ">
        <div style="width:52px;height:52px;border-radius:14px;background:linear-gradient(135deg,#166534,#22c55e);display:flex;align-items:center;justify-content:center;flex-shrink:0;box-shadow:0 8px 24px rgba(34,197,94,0.3);">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="white" width="28" height="28"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"/></svg>
        </div>
        <div style="flex:1;">
            <div style="color:#4ade80; font-weight:700; font-size:1.05rem; margin-bottom:4px;">
                Assistant MatriskAI
            </div>
            <div style="color:#86efac; font-size:0.85rem; opacity:0.85;">
                Posez-moi n'importe quelle question sur vos données — je connais tout le dashboard.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    quick_qs = [
        ("◆", "Quels sont les matériaux les plus critiques ?"),
        ("◈", "Quels fournisseurs ont le plus de risques élevés ?"),
        ("▣", "Résume le tableau de bord en 5 points"),
        ("↗", "Que recommandes-tu en priorité ?"),
    ]
    q_cols = st.columns(2)
    for i, (emoji, q) in enumerate(quick_qs):
        with q_cols[i % 2]:
            if st.button(f"{emoji}  {q}", key=f"vue_globale_q_{i}", use_container_width=True):
                st.session_state.chat_history = st.session_state.get("chat_history", [])
                st.session_state.chat_history.append({"role": "user", "content": q})
                st.session_state.pending_reply = True
                st.session_state.page = "Assistant IA"
                st.rerun()
    st.divider()

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        section_header("DISTRIBUTION DES NIVEAUX DE RISQUE")
        counts = df_pred["predicted_label"].value_counts().reset_index()
        counts.columns = ["Risque","Nombre"]
        fig = px.pie(counts, names="Risque", values="Nombre", color="Risque",
                     color_discrete_map=COULEURS, hole=0.62)
        fig.update_traces(textinfo="percent+label", textfont=dict(size=12),
                          marker=dict(line=dict(color="rgba(0,0,0,0.05)", width=2)))
        fig.update_layout(**plotly_layout(showlegend=False, height=320))
        st.plotly_chart(fig, use_container_width=True)

    with col_g2:
        section_header("DISTRIBUTION SRI PAR NIVEAU DE RISQUE")
        fig = px.violin(df_pred, x="predicted_label", y="SRI",
                        color="predicted_label", color_discrete_map=COULEURS,
                        box=True, points=False, labels={"predicted_label":"","SRI":"Score SRI"})
        fig.update_traces(meanline_visible=True)
        fig.update_layout(**plotly_layout(showlegend=False, height=320))
        st.plotly_chart(fig, use_container_width=True)

    if not df_forc.empty and "profil_cluster" in df_forc.columns:
        section_header("PROFILS FOURNISSEURS")
        cc = df_forc["profil_cluster"].value_counts().reset_index()
        cc.columns = ["Profil","Nb"]
        cc["Pct"] = cc["Nb"] / cc["Nb"].sum() * 100
        fig = px.bar(cc, x="Profil", y="Nb", color="Profil", color_discrete_map=COULEURS_CLUSTER,
                     text=cc["Pct"].map(lambda x: f"{x:.0f}%"))
        fig.update_traces(textposition="outside", textfont=dict(size=11), marker_line_width=0)
        fig.update_layout(**plotly_layout(showlegend=False, height=260, bargap=0.3))
        st.plotly_chart(fig, use_container_width=True)

    if "supplierHoldingName" in df_pred.columns:
        section_header("HEATMAP — RISQUE PAR FOURNISSEUR")
        top_fourn = df_pred[df_pred["predicted_label"].isin(["Élevé","Moyen"])]["supplierHoldingName"].value_counts().head(20).index.tolist()
        if top_fourn:
            pivot = pd.crosstab(df_pred[df_pred["supplierHoldingName"].isin(top_fourn)]["supplierHoldingName"],
                                df_pred[df_pred["supplierHoldingName"].isin(top_fourn)]["predicted_label"])
            fig = px.imshow(pivot, color_continuous_scale=[[0,"#16A34A"],[0.5,"#D97706"],[1,"#DC2626"]],
                            labels=dict(color="Nb matériaux"), aspect="auto")
            fig.update_layout(**plotly_layout(height=480))
            st.plotly_chart(fig, use_container_width=True)

    if "SRI" in df_pred.columns:
        section_header("TOP 10 MATÉRIAUX LES PLUS À RISQUE")
        cols_top = [c for c in ["STMaterialCode","STMaterialDesc","supplierHoldingName",
                                 "predicted_label","SRI","confiance_finale"] if c in df_pred.columns]
        st.dataframe(df_pred[df_pred["predicted_label"]=="Élevé"].nsmallest(10,"SRI")[cols_top],
                     use_container_width=True, height=300)

# ══════════════════════════════════════════════════════════════════
# PAGE : TIME SERIES IA
# ══════════════════════════════════════════════════════════════════
elif page == "Time Series IA":
    st.title("Time Series IA")
    st.markdown(badge("Refonte v2","cyan"), unsafe_allow_html=True)

    if df_hist.empty:
        st.warning("Aucun historique disponible. Lancez `matrisk_step1_cleaning.py` — chaque exécution ajoute un snapshot. Prophet s'active à partir de 4 snapshots.")
        st.stop()

    df_hist["date"] = pd.to_datetime(df_hist["date"])
    nb_snap = df_hist["date"].nunique()

    if "SRI" in df_hist.columns:
        dates_uniq = sorted(df_hist["date"].unique())
        if len(dates_uniq) >= 2:
            sri_d1 = df_hist[df_hist["date"] == dates_uniq[-2]]["SRI"].mean()
            sri_d2 = df_hist[df_hist["date"] == dates_uniq[-1]]["SRI"].mean()
            delta  = sri_d2 - sri_d1
            direction = "↑ hausse" if delta > 0 else "↓ baisse"
            col_dir   = "#DC2626" if delta > 0 else "#16A34A"
            ai_banner(f"Le SRI moyen global montre une <strong style='color:{col_dir}'>{direction} de {abs(delta):.1f} points</strong> entre les deux derniers snapshots. " +
                ("Tendance dégradante — action recommandée." if delta > 2 else
                 "Tendance stable à surveiller." if abs(delta) <= 2 else "Tendance améliorante."))

    st.caption(f"{nb_snap} snapshot(s) disponibles · Prophet actif à partir de 4")

    tab1, tab2, tab3 = st.tabs(["↗ SRI Global","◇ Par Fournisseur","✦ Anomalies Timeline"])

    with tab1:
        section_header("ÉVOLUTION DU SRI MOYEN GLOBAL")
        sri_par_date = df_hist.groupby("date")["SRI"].agg(["mean","std","min","max"]).reset_index()
        sri_par_date.columns = ["date","mean","std","min","max"]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=pd.concat([sri_par_date["date"],sri_par_date["date"][::-1]]),
            y=pd.concat([sri_par_date["max"],sri_par_date["min"][::-1]]),
            fill="toself", fillcolor="rgba(22,101,52,0.05)", line=dict(color="rgba(0,0,0,0)"), name="Min-Max"))
        fig.add_trace(go.Scatter(x=pd.concat([sri_par_date["date"],sri_par_date["date"][::-1]]),
            y=pd.concat([sri_par_date["mean"]+sri_par_date["std"],(sri_par_date["mean"]-sri_par_date["std"])[::-1]]),
            fill="toself", fillcolor="rgba(22,101,52,0.10)", line=dict(color="rgba(0,0,0,0)"), name="± 1σ"))
        fig.add_trace(go.Scatter(x=sri_par_date["date"], y=sri_par_date["mean"],
            mode="lines+markers", name="SRI moyen",
            line=dict(color="#166534", width=2.5),
            marker=dict(size=7, color="#166534", line=dict(color="white",width=2))))
        fig.add_hrect(y0=0,  y1=40,  fillcolor="#DC2626", opacity=0.04, line_width=0, annotation_text="Zone critique",  annotation_font_color="#DC2626", annotation_font_size=9)
        fig.add_hrect(y0=40, y1=65,  fillcolor="#D97706", opacity=0.04, line_width=0, annotation_text="Zone vigilance", annotation_font_color="#D97706", annotation_font_size=9)
        fig.add_hrect(y0=65, y1=100, fillcolor="#16A34A", opacity=0.03, line_width=0, annotation_text="Zone saine",     annotation_font_color="#16A34A", annotation_font_size=9)
        fig.update_layout(**plotly_layout(height=380, yaxis=dict(range=[0,100], title="SRI moyen"),
                          legend=dict(orientation="h",y=-0.15,font=dict(size=11))))
        st.plotly_chart(fig, use_container_width=True)

        if nb_snap >= 4:
            section_header("FORECAST PROPHET (J+30)", "#16A34A")
            try:
                from prophet import Prophet
                df_prophet = sri_par_date[["date","mean"]].rename(columns={"date":"ds","mean":"y"})
                m = Prophet(changepoint_prior_scale=0.3, seasonality_mode="additive", interval_width=0.9)
                m.fit(df_prophet)
                future   = m.make_future_dataframe(periods=30)
                forecast = m.predict(future)
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=pd.concat([forecast["ds"],forecast["ds"][::-1]]),
                    y=pd.concat([forecast["yhat_upper"],forecast["yhat_lower"][::-1]]),
                    fill="toself", fillcolor="rgba(22,101,52,0.08)", line=dict(color="rgba(0,0,0,0)"), name="IC 90%"))
                fig2.add_trace(go.Scatter(x=forecast["ds"], y=forecast["yhat"],
                    mode="lines", name="Prévision Prophet", line=dict(color="#16A34A",width=2,dash="dot")))
                fig2.add_trace(go.Scatter(x=df_prophet["ds"], y=df_prophet["y"],
                    mode="markers+lines", name="Historique",
                    marker=dict(size=6,color="#166534"), line=dict(color="#166534",width=1.5)))
                fig2.update_layout(**plotly_layout(height=300))
                st.plotly_chart(fig2, use_container_width=True)
            except ImportError:
                st.info("Prophet non installé — `pip install prophet` pour activer les forecasts.")
        else:
            st.info(f"Prophet nécessite ≥ 4 snapshots. Actuellement : {nb_snap}.")

        if "risk_label" in df_hist.columns:
            section_header("DISTRIBUTION DES LABELS DANS LE TEMPS")
            dist = df_hist.groupby(["date","risk_label"]).size().reset_index(name="count")
            dist["pct"] = dist.groupby("date")["count"].transform(lambda x: x/x.sum()*100)
            fig3 = px.area(dist, x="date", y="pct", color="risk_label",
                           color_discrete_map=COULEURS, labels={"pct":"%","risk_label":""})
            fig3.update_layout(**plotly_layout(height=260, yaxis_title="%"))
            st.plotly_chart(fig3, use_container_width=True)

    with tab2:
        section_header("ÉVOLUTION SRI PAR FOURNISSEUR")
        if "fournisseur" in df_hist.columns:
            top_fourns = df_hist.groupby("fournisseur")["SRI"].mean().sort_values().head(15).index.tolist()
            fourn_choisi = st.multiselect("Sélectionner des fournisseurs",
                options=sorted(df_hist["fournisseur"].unique().tolist()), default=top_fourns[:5])
            if fourn_choisi:
                sri_f = df_hist[df_hist["fournisseur"].isin(fourn_choisi)].groupby(["date","fournisseur"])["SRI"].mean().reset_index()
                fig = px.line(sri_f, x="date", y="SRI", color="fournisseur", markers=True,
                              color_discrete_sequence=px.colors.qualitative.Set2)
                fig.add_hrect(y0=0,  y1=40,  fillcolor="#DC2626", opacity=0.04, line_width=0)
                fig.add_hrect(y0=40, y1=65,  fillcolor="#D97706", opacity=0.03, line_width=0)
                fig.add_hrect(y0=65, y1=100, fillcolor="#16A34A", opacity=0.03, line_width=0)
                fig.update_layout(**plotly_layout(height=440, yaxis=dict(range=[0,100])))
                st.plotly_chart(fig, use_container_width=True)
                rank_df = sri_f.groupby("fournisseur")["SRI"].mean().sort_values().reset_index()
                rank_df.columns = ["Fournisseur","SRI Moyen"]
                rank_df["SRI Moyen"] = rank_df["SRI Moyen"].round(1)
                rank_df["Risque"] = rank_df["SRI Moyen"].apply(lambda x: "Élevé" if x<40 else("Moyen" if x<65 else "Faible"))
                st.dataframe(rank_df, use_container_width=True, height=200)
        else:
            st.info("Colonne 'fournisseur' non trouvée dans l'historique.")

    with tab3:
        section_header("ANOMALIES TIMELINE", "#DC2626")
        if "est_anomalie" in df_hist.columns:
            anom_time = df_hist[df_hist["est_anomalie"]==1]
            if not anom_time.empty:
                anom_count  = anom_time.groupby("date").size().reset_index(name="nb_anomalies")
                total_count = df_hist.groupby("date").size().reset_index(name="total")
                merged = anom_count.merge(total_count, on="date")
                merged["pct"] = merged["nb_anomalies"] / merged["total"] * 100
                fig = go.Figure()
                fig.add_trace(go.Bar(x=merged["date"], y=merged["nb_anomalies"], name="Anomalies", marker_color="#DC2626", marker_line_width=0))
                fig.add_trace(go.Scatter(x=merged["date"], y=merged["pct"], name="% du total", yaxis="y2",
                    line=dict(color="#D97706",width=2), mode="lines+markers"))
                fig.update_layout(**plotly_layout(height=340,
                    yaxis=dict(title="Nb anomalies"),
                    yaxis2=dict(title="%", overlaying="y", side="right", showgrid=False),
                    legend=dict(orientation="h",y=-0.18)))
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("Aucune anomalie détectée dans l'historique.")
        else:
            st.info("Colonne 'est_anomalie' non présente dans l'historique.")

# ══════════════════════════════════════════════════════════════════
# PAGE : PRÉVISIONS J+90
# ══════════════════════════════════════════════════════════════════
elif page == "Prévisions J+90":
    st.title("Prévisions J+90 — Fournisseurs")
    if df_forc.empty:
        st.error("Lancez d'abord les étapes de forecast.")
        st.stop()

    if "methode_forecast" in df_forc.columns:
        nb_prophet = int((df_forc["methode_forecast"] == "prophet").sum())
        nb_lin     = len(df_forc) - nb_prophet
        pct_p      = nb_prophet / len(df_forc) * 100 if len(df_forc) else 0
        ai_banner(f"<strong>{nb_prophet} fournisseurs</strong> modélisés via Prophet ({pct_p:.0f}%) et <strong>{nb_lin}</strong> via projection linéaire.")
        c1,c2,c3 = st.columns(3)
        c1.metric("Via Prophet",        nb_prophet)
        c2.metric("Via proj. linéaire", nb_lin)
        if "fiabilite_forecast" in df_forc.columns:
            c3.metric("Fiabilité moyenne", f"{df_forc['fiabilite_forecast'].mean():.0f}%")

    st.divider()
    section_header("TOP FOURNISSEURS À RISQUE — SRI ACTUEL vs J+30 vs J+90")

    # FIX: utiliser la colonne "fournisseur" si elle existe
    fourn_col = "fournisseur" if "fournisseur" in df_forc.columns else ("supplierHoldingName" if "supplierHoldingName" in df_forc.columns else None)
    top_risque = df_forc.sort_values("sri_actuel").head(20) if "sri_actuel" in df_forc.columns else df_forc.head(20)

    if fourn_col and all(c in top_risque.columns for c in ["sri_actuel","sri_j90"]):
        fig = go.Figure()
        x_labels = top_risque[fourn_col].astype(str).str[:22]
        if "sri_j30" in top_risque.columns:
            fig.add_trace(go.Bar(name="J+30",      x=x_labels, y=top_risque["sri_j30"],    marker_color="#7C3AED", marker_line_width=0))
        fig.add_trace(go.Bar(name="SRI Actuel",    x=x_labels, y=top_risque["sri_actuel"], marker_color="#5B6B61", marker_line_width=0))
        fig.add_trace(go.Bar(name="SRI J+90",      x=x_labels, y=top_risque["sri_j90"],    marker_color="#DC2626", marker_line_width=0))
        if "sri_j90_upper" in top_risque.columns:
            fig.add_trace(go.Scatter(name="IC sup J+90", x=x_labels, y=top_risque["sri_j90_upper"],
                mode="markers", marker=dict(symbol="line-ns",size=12,color="#EA580C",line=dict(width=2))))
        fig.update_layout(**plotly_layout(barmode="group", height=460, xaxis_tickangle=-38,
            yaxis=dict(range=[0,100],title="SRI"), legend=dict(orientation="h",y=-0.22),
            bargap=0.18, bargroupgap=0.04))
        st.plotly_chart(fig, use_container_width=True)

    if fourn_col and all(c in df_forc.columns for c in ["sri_actuel","sri_j90"]):
        section_header("SCATTER — DÉGRADATION ATTENDUE")
        color_col = "profil_cluster" if "profil_cluster" in df_forc.columns else None
        fig2 = px.scatter(df_forc, x="sri_actuel", y="sri_j90", color=color_col,
                          color_discrete_map=COULEURS_CLUSTER if color_col else None,
                          hover_name=fourn_col, size_max=12,
                          labels={"sri_actuel":"SRI Actuel","sri_j90":"SRI J+90"})
        fig2.add_trace(go.Scatter(x=[0,100],y=[0,100],mode="lines",
            line=dict(color="rgba(0,0,0,0.1)",dash="dash"),name="Pas de changement"))
        fig2.update_layout(**plotly_layout(height=380, legend=dict(orientation="h",y=-0.18)))
        st.plotly_chart(fig2, use_container_width=True)

    section_header("TABLEAU DÉTAILLÉ")
    cols_afficher = [c for c in [fourn_col,"alerte","profil_cluster","sri_actuel","sri_j30","sri_j90",
                                  "label_j90","fiabilite_forecast","methode_forecast","nb_materiaux"] if c and c in df_forc.columns]
    st.dataframe(df_forc[cols_afficher].sort_values("sri_actuel") if "sri_actuel" in df_forc.columns else df_forc[cols_afficher],
                 use_container_width=True, height=400)

# ══════════════════════════════════════════════════════════════════
# PAGE : PLAN D'ACTIONS
# ══════════════════════════════════════════════════════════════════
elif page == "Plan d'Actions":
    st.title("Plan d'Actions")
    if df_act.empty:
        st.error("Lancez d'abord l'étape de génération du plan.")
        st.stop()

    n_p1  = int((df_act["priorite"]==1).sum()) if "priorite"      in df_act.columns else 0
    n_p2  = int((df_act["priorite"]==2).sum()) if "priorite"      in df_act.columns else 0
    n_p3  = int((df_act["priorite"]==3).sum()) if "priorite"      in df_act.columns else 0
    n_mat = df_act["materiau_code"].nunique()  if "materiau_code"  in df_act.columns else 0

    ai_banner(f"<strong>{n_p1} actions de priorité 1</strong> requièrent une intervention immédiate. {n_p2} actions en priorité 2 à planifier cette semaine. {n_mat} matériaux distincts concernés.")

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Priorité 1 — Urgent",      n_p1)
    c2.metric("Priorité 2 — Important",   n_p2)
    c3.metric("Priorité 3 — À planifier", n_p3)
    c4.metric("Matériaux concernés",      n_mat)
    st.divider()

    col_f1, col_f2 = st.columns([3,1])
    prio_sel = col_f1.multiselect("Filtrer par priorité", [1,2,3], default=[1])
    cat_sel  = col_f2.selectbox("Catégorie", ["Toutes"]+sorted(df_act["categorie"].dropna().unique().tolist())) if "categorie" in df_act.columns else "Toutes"

    df_filtre = df_act.copy()
    if prio_sel:  df_filtre = df_filtre[df_filtre["priorite"].isin(prio_sel)]
    if cat_sel != "Toutes" and "categorie" in df_filtre.columns: df_filtre = df_filtre[df_filtre["categorie"]==cat_sel]

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        if "score_urgence" in df_filtre.columns and "categorie" in df_filtre.columns:
            section_header("URGENCE PAR CATÉGORIE")
            urgence_cat = df_filtre.groupby("categorie")["score_urgence"].mean().sort_values(ascending=True).reset_index()
            fig = px.bar(urgence_cat, x="score_urgence", y="categorie", orientation="h",
                         color="score_urgence", color_continuous_scale=["#16A34A","#D97706","#DC2626"])
            fig.update_layout(**plotly_layout(showlegend=False, height=280))
            st.plotly_chart(fig, use_container_width=True)
    with col_g2:
        if "priorite" in df_filtre.columns:
            section_header("RÉPARTITION PAR PRIORITÉ")
            pc = df_filtre["priorite"].value_counts().reset_index()
            pc.columns = ["Priorité","Nb"]
            fig2 = px.pie(pc, names="Priorité", values="Nb",
                          color="Priorité", color_discrete_map={"1":"#DC2626","2":"#D97706","3":"#16A34A"}, hole=0.5)
            fig2.update_traces(textinfo="percent+label", marker=dict(line=dict(color="white",width=2)))
            fig2.update_layout(**plotly_layout(showlegend=False, height=280))
            st.plotly_chart(fig2, use_container_width=True)

    section_header("ACTIONS DÉTAILLÉES")
    cols_afficher = [c for c in ["priorite","score_urgence","date_limite","materiau_code","fournisseur",
                                  "label_predit","sri","categorie","action","confiance"] if c in df_filtre.columns]
    st.dataframe(df_filtre[cols_afficher], use_container_width=True, height=480)

    resume_path = os.path.join(BASE_PATH, "step4_resume_executif.txt")
    if os.path.exists(resume_path):
        with open(resume_path,"r",encoding="utf-8") as f:
            contenu = f.read()
        st.download_button("↓ Résumé exécutif", data=contenu,
                           file_name="MatriskAI_Resume_Executif.txt", mime="text/plain")

# ══════════════════════════════════════════════════════════════════
# PAGE : SHAP
# ══════════════════════════════════════════════════════════════════
elif page == "Explainability SHAP":
    st.title("Explainability SHAP")
    ai_banner("SHAP quantifie la contribution de chaque feature à la décision du modèle XGBoost. Valeur positive → risque élevé ; négative → risque réduit.")

    img_bar    = os.path.join(BASE_PATH, "shap_importance_bar.png")
    img_bswarm = os.path.join(BASE_PATH, "shap_beeswarm_eleve.png")
    c1, c2 = st.columns(2)
    with c1:
        section_header("IMPORTANCE GLOBALE")
        # BUG FIX : ternaire inline retournait DeltaGenerator → affiché en tooltip
        if os.path.exists(img_bar):
            st.image(img_bar, use_container_width=True)
        else:
            st.warning("Image manquante — lancez l'étape d'entraînement.")
    with c2:
        section_header("BEESWARM — RISQUE ÉLEVÉ")
        if os.path.exists(img_bswarm):
            st.image(img_bswarm, use_container_width=True)
        else:
            st.warning("Image manquante — lancez l'étape d'entraînement.")

    st.divider()
    section_header("GUIDE DES FEATURES")
    features_guide = {
        "vitesse_degradation" : ("Vitesse de dégradation mensuelle du score SRI.",          "red"),
        "has_ecertificate"    : ("0 = absent, 1 = présent. Absent = fort signal risque.",   "red"),
        "combined_risk_score" : ("QML×0.6 + ASL×0.4 — de 0 (bon) à 4 (critique).",         "amber"),
        "shelf_life_risk"     : ("0 = OK (>12 mois), 3 = critique (<3 mois).",              "amber"),
        "qml_risk_score"      : ("0 = Certified, 4 = Disqualified.",                        "red"),
        "asl_risk_score"      : ("0 = Approved, 4 = Disapproved.",                          "red"),
        "days_since_update"   : ("Jours depuis la dernière mise à jour.",                   "blue"),
        "text_risk_flag"      : ("Mots-clés de risque dans les notes textuelles.",          "purple"),
    }
    cols = st.columns(2)
    for i, (feat, (expl, color)) in enumerate(features_guide.items()):
        with cols[i % 2]:
            with st.expander(feat):
                st.markdown(f'<span class="badge badge-{color}">{feat}</span><p style="color:#5B6B61;font-size:0.85rem;margin-top:0.5rem">{expl}</p>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════
# PAGE : ANOMALIES
# ══════════════════════════════════════════════════════════════════
elif page == "Anomalies":
    st.title("Anomalies")
    st.markdown("Les anomalies sont détectées par **Isolation Forest** — un matériau est signalé si son profil de features est statistiquement éloigné du reste du dataset.")

    if df_pred.empty or "est_anomalie" not in df_pred.columns:
        st.warning("Données d'anomalies non disponibles — relancez l'étape de prédiction.")
        st.stop()

    anomalies = df_pred[df_pred["est_anomalie"]==1]
    normaux   = df_pred[df_pred["est_anomalie"]==0]
    taux      = len(anomalies) / len(df_pred) if len(df_pred) else 0
    anom_faibles = anomalies[anomalies["predicted_label"]=="Faible"] if "predicted_label" in anomalies.columns else pd.DataFrame()

    if len(anom_faibles) > 0:
        ai_banner(f"<strong>⚠ {len(anom_faibles)} matériaux classés Faible</strong> sont détectés comme anomalies — profil atypique malgré le faible risque apparent. Vérification manuelle recommandée.")
    else:
        ai_banner(f"{len(anomalies)} anomalies détectées sur {len(df_pred)} matériaux ({taux:.1%}). Aucune discordance critique détectée.")

    c1,c2,c3 = st.columns(3)
    c1.metric("Anomalies détectées", len(anomalies))
    c2.metric("Matériaux normaux",   len(normaux))
    c3.metric("Taux d'anomalies",    f"{taux:.1%}")
    st.divider()

    col_g1, col_g2 = st.columns(2)
    with col_g1:
        section_header("ANOMALIES PAR NIVEAU DE RISQUE")
        fig = px.histogram(anomalies, x="predicted_label", color="predicted_label", color_discrete_map=COULEURS,
                           category_orders={"predicted_label":["Faible","Moyen","Élevé"]})
        fig.update_traces(marker_line_width=0)
        fig.update_layout(**plotly_layout(showlegend=False, height=260))
        st.plotly_chart(fig, use_container_width=True)
    with col_g2:
        if "SRI" in anomalies.columns:
            section_header("DISTRIBUTION SRI — ANOMALIES vs NORMAUX")
            fig2 = go.Figure()
            fig2.add_trace(go.Histogram(x=normaux["SRI"],   name="Normaux",   marker_color="#166534", opacity=0.6, histnorm="probability density"))
            fig2.add_trace(go.Histogram(x=anomalies["SRI"], name="Anomalies", marker_color="#DC2626", opacity=0.7, histnorm="probability density"))
            fig2.update_layout(**plotly_layout(barmode="overlay", height=260, legend=dict(orientation="h",y=-0.2)))
            st.plotly_chart(fig2, use_container_width=True)

    section_header("LISTE DES MATÉRIAUX SIGNALÉS", "#DC2626")
    cols = [c for c in ["STMaterialCode","STMaterialDesc","supplierHoldingName","predicted_label","SRI","confiance_finale","qml_risk_score","asl_risk_score"] if c in anomalies.columns]
    st.dataframe(anomalies[cols], use_container_width=True, height=380)

# ══════════════════════════════════════════════════════════════════
# PAGE : SIMULATEUR WHAT-IF
# ══════════════════════════════════════════════════════════════════
elif page == "Simulateur What-If":
    st.title("Simulateur What-If")
    ai_banner("Testez des scénarios hypothétiques. Le modèle XGBoost recalcule les prédictions en temps réel sans modifier les données originales.")

    model_path = os.path.join(BASE_PATH, "xgb_model.pkl")
    if not os.path.exists(model_path):
        st.error(f"Modèle introuvable : `{model_path}` — lancez d'abord l'étape d'entraînement.")
        st.stop()

    with open(model_path,"rb") as f:
        model_data = pickle.load(f)
    model    = model_data["model"]
    le       = model_data["label_encoder"]
    FEATURES = model_data["features"]

    if df_pred.empty:
        st.error("Données non disponibles.")
        st.stop()

    scenario = st.selectbox("Scénario prédéfini", [
        "Obtention d'un e-certificat pour tous les matériaux sans certificat",
        "Passage d'un fournisseur de Probation vers Approved",
        "Requalification : tous les Obsolètes vers Qualified",
        "Amélioration shelf life : +6 mois pour les matériaux critiques",
        "Scénario personnalisé (sliders)",
    ])

    df_sim = df_pred[[f for f in FEATURES if f in df_pred.columns]].copy()
    for f in FEATURES:
        if f not in df_sim.columns:
            df_sim[f] = 0

    section_header("PARAMÈTRES DU SCÉNARIO")

    if "e-certificat" in scenario:
        avant = int((df_sim.get("has_ecertificate", pd.Series([0]))==0).sum())
        df_sim.loc[df_sim["has_ecertificate"]==0,"has_ecertificate"] = 1
        st.info(f"✦ {avant} matériaux recevront un e-certificat.")
    elif "Probation" in scenario:
        if "supplierHoldingName" in df_pred.columns:
            fourn_prob = df_pred[df_pred["asl_risk_score"]==3]["supplierHoldingName"].unique()
            if len(fourn_prob):
                f_sel  = st.selectbox("Fournisseur concerné", options=fourn_prob)
                masque = df_pred["supplierHoldingName"]==f_sel
                df_sim.loc[masque,"asl_risk_score"]      = 0
                df_sim.loc[masque,"combined_risk_score"]  = df_sim.loc[masque,"qml_risk_score"] * 0.6
                st.info(f"✦ {int(masque.sum())} matériaux de **{f_sel}** concernés.")
    elif "Obsolètes" in scenario:
        avant = int((df_sim["qml_risk_score"]==3).sum())
        df_sim.loc[df_sim["qml_risk_score"]==3,"qml_risk_score"] = 1
        df_sim["combined_risk_score"] = df_sim["qml_risk_score"]*0.6 + df_sim["asl_risk_score"]*0.4
        st.info(f"✦ {avant} matériaux obsolètes seront requalifiés.")
    elif "shelf life" in scenario:
        avant = int((df_sim["shelf_life_risk"]==3).sum())
        df_sim.loc[df_sim["shelf_life_risk"]==3,"shelf_life_risk"] = 1
        st.info(f"✦ {avant} matériaux critiques gagnent 6 mois de shelf life.")
    else:
        c1,c2,c3,c4 = st.columns(4)
        qml   = c1.slider("QML risk score",  0,4,2)
        asl   = c2.slider("ASL risk score",  0,4,2)
        shelf = c3.slider("Shelf life risk", 0,3,1)
        ecert = c4.slider("E-certificat",    0,1,0)
        df_sim["qml_risk_score"]      = qml
        df_sim["asl_risk_score"]      = asl
        df_sim["combined_risk_score"] = qml*0.6 + asl*0.4
        df_sim["shelf_life_risk"]     = shelf
        if "has_ecertificate" in df_sim.columns:
            df_sim["has_ecertificate"] = ecert

    if st.button("↗ Lancer la simulation", type="primary"):
        with st.spinner("Simulation en cours…"):
            avant_labels = df_pred["predicted_label"].value_counts()
            y_sim        = le.inverse_transform(model.predict(df_sim[FEATURES]))
            apres_labels = pd.Series(y_sim).value_counts()

        st.success("Simulation terminée.")
        st.divider()
        section_header("RÉSULTATS — AVANT vs APRÈS")

        c1,c2,c3 = st.columns(3)
        for niveau,col in [("Élevé",c1),("Moyen",c2),("Faible",c3)]:
            av = int(avant_labels.get(niveau,0))
            ap = int(apres_labels.get(niveau,0))
            col.metric(f"Risque {niveau}", ap, f"{ap-av:+d}", delta_color="inverse" if niveau!="Faible" else "normal")

        compare_df = pd.DataFrame({
            "Scénario": ["Avant"]*3+["Après"]*3,
            "Risque":   ["Élevé","Moyen","Faible"]*2,
            "Nombre":   [int(avant_labels.get("Élevé",0)),int(avant_labels.get("Moyen",0)),int(avant_labels.get("Faible",0)),
                         int(apres_labels.get("Élevé",0)),int(apres_labels.get("Moyen",0)),int(apres_labels.get("Faible",0))],
        })
        fig = px.bar(compare_df, x="Risque", y="Nombre", color="Scénario", barmode="group",
                     color_discrete_map={"Avant":"#5B6B61","Après":"#166534"}, text="Nombre")
        fig.update_traces(marker_line_width=0, textposition="outside", textfont=dict(size=11))
        fig.update_layout(**plotly_layout(height=320, bargap=0.25, bargroupgap=0.06, legend=dict(orientation="h",y=-0.18)))
        st.plotly_chart(fig, use_container_width=True)

        df_pred_copy = df_pred.copy()
        df_pred_copy["label_apres"] = y_sim
        ameliores = df_pred_copy[df_pred_copy["predicted_label"].isin(["Élevé","Moyen"]) & (df_pred_copy["label_apres"]=="Faible")]
        if len(ameliores):
            st.success(f"✓ {len(ameliores)} matériaux passent en Risque Faible grâce à ce scénario.")
            cols = [c for c in ["STMaterialCode","STMaterialDesc","supplierHoldingName","predicted_label","label_apres"] if c in ameliores.columns]
            st.dataframe(ameliores[cols], use_container_width=True, height=280)
        else:
            st.info("Aucun matériau ne passe en Faible avec ce scénario.")

# ══════════════════════════════════════════════════════════════════
# PAGE : ASSISTANT IA (CHATBOT)
# ══════════════════════════════════════════════════════════════════
elif page == "Assistant IA":
    st.title("Assistant IA")
    ai_banner("Posez vos questions sur le dashboard, les risques fournisseurs, les matériaux critiques ou les prévisions. <strong>L'assistant a accès au contexte complet de vos données.</strong>")

    # Clé API à configurer via variable d'environnement
    GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

    with st.sidebar:
        st.divider()
        section_header("CONFIGURATION CHATBOT","#7C3AED")
        groq_model = st.selectbox("Modèle Groq",
            ["llama-3.3-70b-versatile","llama-3.1-8b-instant","mixtral-8x7b-32768"], index=0)
        if st.button("✕ Effacer la conversation", key="clear_chat", type="primary", use_container_width=True):
            st.session_state.chat_history = []
            st.session_state.pop("pending_reply", None)
            st.rerun()

    # ── Contexte dashboard ────────────────────────────────────────
    def build_dashboard_context() -> str:
        ctx = ["=== CONTEXTE DASHBOARD MATRISK AI ===\n"]
        if not df_pred.empty:
            n_total  = len(df_pred)
            n_eleve  = int((df_pred["predicted_label"]=="Élevé").sum())
            n_moyen  = int((df_pred["predicted_label"]=="Moyen").sum())
            n_faible = int((df_pred["predicted_label"]=="Faible").sum())
            n_fourn  = df_pred["supplierHoldingName"].nunique() if "supplierHoldingName" in df_pred.columns else 0
            conf_moy = df_pred["confiance_finale"].mean() if "confiance_finale" in df_pred.columns else 0
            ctx.append(f"KPIs : {n_total} matériaux | Élevé {n_eleve} ({n_eleve/n_total:.1%}) | Moyen {n_moyen} ({n_moyen/n_total:.1%}) | Faible {n_faible} ({n_faible/n_total:.1%}) | {n_fourn} fournisseurs | Confiance IA {conf_moy:.0f}%\n")
            if "supplierHoldingName" in df_pred.columns:
                top_f = df_pred[df_pred["predicted_label"]=="Élevé"]["supplierHoldingName"].value_counts().head(5)
                if not top_f.empty:
                    ctx.append("Top 5 fournisseurs risque élevé : " + ", ".join([f"{k} ({v} mat.)" for k,v in top_f.items()]) + "\n")
            top_risk_cols = [c for c in ["STMaterialCode","STMaterialDesc","supplierHoldingName","predicted_label","SRI","confiance_finale"] if c in df_pred.columns]
            top10 = df_pred[df_pred["predicted_label"]=="Élevé"].nsmallest(10,"SRI") if "SRI" in df_pred.columns else df_pred[df_pred["predicted_label"]=="Élevé"].head(10)
            if not top10.empty:
                ctx.append("Top 10 matériaux critiques :\n")
                for _,row in top10[top_risk_cols].iterrows():
                    ctx.append("  • " + " | ".join([f"{col}={row[col]}" for col in top_risk_cols]) + "\n")
        if not df_hist.empty:
            nb_snap = df_hist["date"].nunique() if "date" in df_hist.columns else len(df_hist)
            ctx.append(f"\nHistorique : {nb_snap} snapshots.\n")
            if "SRI" in df_hist.columns and "date" in df_hist.columns:
                last_sri = df_hist.groupby("date")["SRI"].mean().tail(3)
                ctx.append("SRI moyen récent : " + ", ".join([f"{d}: {v:.1f}" for d,v in last_sri.items()]) + "\n")
        if not df_forc.empty:
            # FIX: vérifier les deux noms de colonne possibles
            fourn_col_forc = "fournisseur" if "fournisseur" in df_forc.columns else ("supplierHoldingName" if "supplierHoldingName" in df_forc.columns else None)
            if "fiabilite_forecast" in df_forc.columns:
                ctx.append(f"\nPrévisions J+90 : fiabilité moyenne {df_forc['fiabilite_forecast'].mean():.0f}%.\n")
            if fourn_col_forc:
                ctx.append(f"Fournisseurs en prévision : {df_forc[fourn_col_forc].nunique()}\n")
        return "".join(ctx)

    SYSTEM_PROMPT = (
        "Tu es l'Assistant IA de MatriskAI, expert en Supply Chain Risk Intelligence. "
        "Tu analyses les données du dashboard en temps réel. Sois concis, précis, professionnel. "
        "Cite des chiffres réels quand possible. Réponds en français sauf si l'utilisateur écrit en anglais. "
        "Utilise **gras** pour mettre en valeur les chiffres importants.\n\n"
        + build_dashboard_context()
    )

    def call_groq(messages: list, api_key: str, model: str) -> str:
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": [{"role":"system","content":SYSTEM_PROMPT}]+messages,
                      "max_tokens": 1024, "temperature": 0.7},
                timeout=30,
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError:
            if resp.status_code == 401: return "❌ **Clé API Groq invalide.** Vérifiez votre clé (commence par gsk_)."
            if resp.status_code == 429: return "⏳ **Limite de requêtes atteinte.** Réessayez dans quelques secondes."
            return f"❌ Erreur API Groq ({resp.status_code})"
        except requests.exceptions.Timeout:
            return "⏱ **Timeout** — Groq met trop de temps à répondre. Réessayez."
        except Exception as e:
            return f"❌ Erreur inattendue : {e}"

    # ── Session state ─────────────────────────────────────────────
    if "chat_history"  not in st.session_state: st.session_state.chat_history  = []
    if "pending_reply" not in st.session_state: st.session_state.pending_reply = False

    QUICK_QUESTIONS = [
        "Quels sont les matériaux les plus critiques ?",
        "Quels fournisseurs ont le plus de risques élevés ?",
        "Résume le tableau de bord en 5 points",
        "Que recommandes-tu en priorité ?",
        "Comment interpréter le score SRI ?",
        "Explique les anomalies détectées",
    ]

    # ── Affichage conversation ────────────────────────────────────
    with st.container():
        if not st.session_state.chat_history:
            st.markdown("""
<div class="chat-welcome">
  <div style="font-size:2.5rem">◈</div>
  <h3>Assistant MatriskAI</h3>
  <p>Posez une question ou choisissez une suggestion.</p>
</div>""", unsafe_allow_html=True)
            cols = st.columns(3)
            for i, q in enumerate(QUICK_QUESTIONS):
                with cols[i % 3]:
                    if st.button(q, key=f"quick_{i}", use_container_width=True):
                        st.session_state.chat_history.append({"role":"user","content":q})
                        st.session_state.pending_reply = True  # FIX: flag pour éviter boucle infinie
                        st.rerun()
        else:
            for msg in st.session_state.chat_history:
                role   = msg["role"]
                is_bot = role == "assistant"
                avatar = "◈" if is_bot else "👤"
                cls    = "bot" if is_bot else "user"
                st.markdown(f"""
<div class="chat-msg {cls}">
  <div class="chat-avatar {cls}">{avatar}</div>
  <div class="chat-bubble {cls}">{msg["content"]}</div>
</div>""", unsafe_allow_html=True)

    st.divider()

    # ── Zone de saisie ────────────────────────────────────────────
    col_input, col_send = st.columns([9,1])
    with col_input:
        user_input = st.text_input("Votre question", key="chat_input",
                                    placeholder="Ex: Quels sont les fournisseurs les plus risqués ce mois-ci ?",
                                    label_visibility="collapsed")
    with col_send:
        send_clicked = st.button("↗", key="send_btn", use_container_width=True)

    # ── FIX : logique chat unifiée, sans double appel API ─────────
    # Déclenché par le bouton Envoyer OU par une question rapide (pending_reply)
    should_call_api = False
    if send_clicked and user_input.strip():
        st.session_state.chat_history.append({"role":"user","content":user_input.strip()})
        st.session_state.pending_reply = False  # BUG FIX: éviter double appel si pending_reply était True
        should_call_api = True
    elif st.session_state.pending_reply and st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
        should_call_api = True
        st.session_state.pending_reply = False

    if should_call_api:
        if not GROQ_API_KEY:
            st.warning("⚠ Clé API Groq manquante. Définissez la variable d'environnement GROQ_API_KEY.")
        else:
            with st.spinner("L'assistant analyse vos données…"):
                api_messages = [{"role":m["role"],"content":m["content"]} for m in st.session_state.chat_history]
                reply = call_groq(api_messages, GROQ_API_KEY, groq_model)
            st.session_state.chat_history.append({"role":"assistant","content":reply})
            st.rerun()

    if st.session_state.chat_history:
        st.caption(f"💬 {len(st.session_state.chat_history)} messages · Modèle Groq : {groq_model if 'groq_model' in dir() else '—'}")


# ══════════════════════════════════════════════════════════════════
# ASSISTANT FLOTTANT (widget bas-droite, visible sur toutes les pages)
# ══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
/* ── Bouton avatar flottant ── */
#matbot-btn {
    position: fixed;
    bottom: 28px;
    right: 28px;
    width: 68px;
    height: 68px;
    border-radius: 50%;
    background: linear-gradient(135deg, #1a5c1a, #0d3d0d);
    border: 3px solid #4ade80;
    box-shadow: 0 4px 20px rgba(74,222,128,0.4);
    cursor: pointer;
    z-index: 99999;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2.2rem;
    transition: transform 0.2s, box-shadow 0.2s;
    animation: pulse-bot 2.5s infinite;
}
#matbot-btn:hover {
    transform: scale(1.12);
    box-shadow: 0 6px 28px rgba(74,222,128,0.6);
}
@keyframes pulse-bot {
    0%,100% { box-shadow: 0 4px 20px rgba(74,222,128,0.4); }
    50%      { box-shadow: 0 4px 32px rgba(74,222,128,0.75); }
}
</style>

<!-- Bouton avatar flottant -->
<div id="matbot-btn" title="Ouvrir l'Assistant IA">
    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.8" stroke="white" width="32" height="32"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12.75L11.25 15 15 9.75m-3-7.036A11.959 11.959 0 013.598 6 11.99 11.99 0 003 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285z"/></svg>
</div>

""", unsafe_allow_html=True)

# ── INJECTION JAVASCRIPT FIABLE VIA IFRAME ──
# Streamlit bloque l'exécution des balises <script> et supprime les attributs onclick="" 
# dans st.markdown pour des raisons de sécurité. La seule façon garantie d'exécuter du JS
# est via st.components.v1.html, qui tourne dans une iframe et modifie le DOM parent.
st.components.v1.html("""
<script>
    function setupBotButton() {
        // On cible le document de l'application Streamlit principale
        const parentDoc = window.parent.document;
        const btn = parentDoc.getElementById('matbot-btn');
        
        // Si le bouton existe et n'a pas encore l'événement
        if (btn && !btn.hasAttribute('data-js-bound')) {
            btn.setAttribute('data-js-bound', 'true');
            
            btn.addEventListener('click', function() {
                // Chercher et cliquer sur le vrai bouton "Assistant IA" de Streamlit
                const buttons = Array.from(parentDoc.querySelectorAll('section[data-testid="stSidebar"] button'));
                const targetBtn = buttons.find(b => (b.innerText || b.textContent || '').includes('Assistant IA'));
                
                if (targetBtn) {
                    targetBtn.click();
                } else {
                    // Fallback
                    const url = new URL(window.parent.location.href);
                    url.searchParams.set('page', 'Assistant IA');
                    window.parent.location.href = url.toString();
                }
            });
        }
    }
    // Vérifier régulièrement (utile quand Streamlit recharge le DOM partiel)
    setInterval(setupBotButton, 500);
</script>
""", height=0, width=0)

# ══════════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════════
st.divider()
st.markdown(
    '<p style="text-align:center;color:#8A9A90;font-size:0.7rem;letter-spacing:0.06em">'
    'MATRISK AI · Supply Chain Risk Intelligence · '
    'Pipeline : Nettoyage → XGBoost + Calibration → Prophet / Linéaire → Prescriptif → Dashboard'
    '</p>', unsafe_allow_html=True)