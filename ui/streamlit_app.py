import base64
import io
import json
import math
import re
import sys
import wave
from pathlib import Path
from typing import Any, Dict, List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from ui.backend import CopilotBackend


st.set_page_config(
    page_title="Terraform Infrastructure Copilot",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# VISUAL DESIGN
# ============================================================

st.markdown(
    r"""
<style>
/* ==========================================================
   POLISHED ENTERPRISE UI
   ========================================================== */
:root {
    --ink: #101828;
    --muted: #667085;
    --line: #e4e7ec;
    --panel: #ffffff;
    --sidebar: #0b1220;
    --sidebar-panel: #111c2e;
    --sidebar-line: #263449;
    --sidebar-text: #f8fafc;
    --sidebar-muted: #aab6c8;
    --accent: #f97316;
}

.stApp {
    background:
        radial-gradient(circle at 5% 0%, rgba(249,115,22,.07), transparent 24%),
        radial-gradient(circle at 100% 0%, rgba(59,130,246,.08), transparent 28%),
        #f5f7fa;
    color: var(--ink);
    font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}

.block-container {
    max-width: 1450px;
    padding-top: 1.25rem;
    padding-bottom: 3rem;
}

/* ---------- Hero ---------- */
.hero {
    padding: 1.65rem 2rem 1.55rem;
    border: 1px solid #e7eaf0;
    border-radius: 22px;
    background: rgba(255,255,255,.96);
    box-shadow: 0 12px 35px rgba(16,24,40,.06);
    margin-bottom: 1rem;
}
.hero-kicker {
    font-size: .68rem;
    font-weight: 800;
    letter-spacing: .14em;
    text-transform: uppercase;
    color: #c2410c;
}
.hero-title {
    font-size: clamp(2rem, 3vw, 2.65rem);
    line-height: 1.05;
    font-weight: 850;
    color: var(--ink);
    margin: .3rem 0 0;
    letter-spacing: -.035em;
}
.hero-subtitle {
    margin-top: .65rem;
    color: #667085;
    font-size: .94rem;
    line-height: 1.55;
    max-width: 980px;
}
.hero-badge {
    display: inline-block;
    margin-top: .8rem;
    padding: .38rem .7rem;
    border-radius: 999px;
    background: #fff4ed;
    color: #9a3412;
    border: 1px solid #fed7aa;
    font-size: .68rem;
    font-weight: 750;
}

.section-title {
    font-size: 1.12rem;
    font-weight: 800;
    color: var(--ink);
    margin-top: 1rem;
    margin-bottom: .22rem;
    letter-spacing: -.01em;
}
.section-caption {
    color: var(--muted);
    font-size: .78rem;
    line-height: 1.5;
    margin-bottom: .72rem;
}

/* ---------- Sidebar ---------- */

/* ---------- Enterprise sidebar controls ---------- */
[data-testid="stSidebar"] .sidebar-field-label {
    color: #cbd5e1 !important;
    font-size: .72rem;
    font-weight: 700;
    margin: .2rem 0 .35rem;
}

[data-testid="stSidebar"] .registry-card {
    background: linear-gradient(145deg, #111c2e, #0d1728);
    border: 1px solid #263449;
    border-radius: 11px;
    padding: .72rem .78rem;
    margin-top: .2rem;
}

[data-testid="stSidebar"] .registry-name {
    color: #f8fafc !important;
    font-size: .82rem;
    font-weight: 800;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

[data-testid="stSidebar"] .registry-meta {
    color: #94a3b8 !important;
    font-size: .66rem;
    margin-top: .14rem;
}

[data-testid="stSidebar"] .registry-branch {
    display: inline-block;
    margin-top: .5rem;
    padding: .18rem .45rem;
    border-radius: 5px;
    background: #172337;
    border: 1px solid #2b3a50;
    color: #cbd5e1 !important;
    font-size: .62rem;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}

[data-testid="stSidebar"] [data-testid="stSelectbox"] {
    margin-bottom: .15rem;
}

[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] > div {
    min-height: 42px !important;
    padding-left: .72rem !important;
    padding-right: .55rem !important;
    background: #111c2e !important;
    border: 1px solid #304158 !important;
    border-radius: 10px !important;
    color: #f8fafc !important;
}

[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] > div:hover {
    border-color: #64748b !important;
    background: #142238 !important;
}

[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] span,
[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] div {
    color: #f8fafc !important;
}

[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] input {
    color: #f8fafc !important;
    -webkit-text-fill-color: #f8fafc !important;
    background: transparent !important;
}

[data-testid="stSidebar"] [data-testid="stSelectbox"] svg {
    fill: #94a3b8 !important;
}

[data-baseweb="popover"] {
    z-index: 999999 !important;
}

[data-baseweb="menu"] {
    background: #101828 !important;
    border: 1px solid #344054 !important;
}

[data-baseweb="menu"] li,
[data-baseweb="menu"] li * {
    color: #f8fafc !important;
}

[data-baseweb="menu"] li:hover {
    background: #1d2939 !important;
}

[data-testid="stSidebar"] .stCheckbox {
    padding: .1rem 0;
}


[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0b1220 0%, #0d1728 100%);
    border-right: 1px solid #172238;
}
[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.2rem;
}
[data-testid="stSidebar"] * {
    color: var(--sidebar-text);
}
[data-testid="stSidebar"] .sidebar-brand-title {
    font-size: 1.1rem;
    font-weight: 850;
    letter-spacing: -.015em;
}
[data-testid="stSidebar"] .sidebar-brand-sub {
    font-size: .68rem;
    color: var(--sidebar-muted) !important;
    margin-top: .15rem;
    margin-bottom: .8rem;
}
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4 {
    color: #f8fafc !important;
    font-size: .84rem !important;
    font-weight: 800 !important;
    margin-top: .55rem !important;
    margin-bottom: .35rem !important;
}
[data-testid="stSidebar"] label {
    color: #cbd5e1 !important;
    font-size: .72rem !important;
    font-weight: 650 !important;
}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
[data-testid="stSidebar"] .stCaption {
    color: var(--sidebar-muted) !important;
    font-size: .67rem !important;
    line-height: 1.45 !important;
}

/* Text inputs, select boxes and all BaseWeb controls in sidebar.
   The old UI had white controls with white text. */
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea {
    background: var(--sidebar-panel) !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    border: 1px solid var(--sidebar-line) !important;
    border-radius: 9px !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] input::placeholder,
[data-testid="stSidebar"] textarea::placeholder {
    color: #718096 !important;
    -webkit-text-fill-color: #718096 !important;
}
[data-testid="stSidebar"] input:focus,
[data-testid="stSidebar"] textarea:focus {
    border-color: #64748b !important;
    box-shadow: 0 0 0 1px #64748b !important;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] > div {
    background: var(--sidebar-panel) !important;
    color: #ffffff !important;
    border: 1px solid var(--sidebar-line) !important;
    border-radius: 9px !important;
    min-height: 40px !important;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"] [data-baseweb="select"] * {
    color: #ffffff !important;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"] svg {
    fill: #94a3b8 !important;
}
[data-testid="stSidebar"] [data-testid="stSelectbox"] [aria-expanded="true"] > div {
    border-color: #64748b !important;
}

[data-testid="stSidebar"] hr {
    border-color: #263449 !important;
    margin: .85rem 0 !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: #172337 !important;
    color: #f8fafc !important;
    border: 1px solid #2b3a50 !important;
    border-radius: 9px !important;
    font-size: .73rem !important;
    font-weight: 750 !important;
    min-height: 38px !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    border-color: #64748b !important;
    background: #1b2a40 !important;
}

/* ---------- Flow ---------- */
.flow-node {
    text-align: center;
    padding: .62rem .3rem;
    border-radius: 13px;
    background: rgba(255,255,255,.9);
    border: 1px solid var(--line);
    box-shadow: 0 4px 12px rgba(16,24,40,.035);
}
.flow-icon { font-size: 1.05rem; }
.flow-label {
    font-size: .65rem;
    font-weight: 800;
    color: #344054;
    margin-top: .18rem;
}
.flow-arrow {
    text-align: center;
    font-size: .9rem;
    color: #98a2b3;
    padding-top: .7rem;
}

/* ---------- Cards ---------- */
.metric-card,
.inventory-card,
.module-card,
.info-panel {
    background: var(--panel);
    border: 1px solid var(--line);
    box-shadow: 0 6px 20px rgba(16,24,40,.04);
}
.metric-card {
    padding: .9rem 1rem;
    border-radius: 15px;
    min-height: 88px;
}
.metric-label {
    color: #667085;
    font-size: .62rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .08em;
}
.metric-value {
    color: var(--ink);
    font-size: 1.28rem;
    font-weight: 850;
    margin-top: .16rem;
    word-break: break-word;
}
.metric-sub {
    color: #98a2b3;
    font-size: .67rem;
    margin-top: .1rem;
}
.inventory-card {
    padding: .82rem .9rem;
    border-radius: 14px;
    min-height: 100px;
}
.inventory-name {
    font-size: .84rem;
    font-weight: 800;
    color: var(--ink);
}
.inventory-path {
    color: #667085;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: .65rem;
    line-height: 1.4;
    margin-top: .18rem;
    overflow-wrap: anywhere;
}
.module-card {
    padding: .9rem;
    border-radius: 15px;
    min-height: 118px;
}
.module-name { font-size: .9rem; font-weight: 850; color: var(--ink); }
.module-role { color: #667085; font-size: .7rem; margin: .12rem 0 .45rem; }

/* ---------- Status pills ---------- */
.pill {
    display: inline-block;
    padding: .24rem .5rem;
    border-radius: 999px;
    font-size: .62rem;
    font-weight: 800;
    margin-right: .16rem;
    margin-bottom: .16rem;
}
.pill-create { background:#ecfdf3; color:#027a48; }
.pill-reuse { background:#eff8ff; color:#175cd3; }
.pill-adapt { background:#fff7ed; color:#c2410c; }
.pill-review { background:#fffaeb; color:#b54708; }
.pill-blocked { background:#fef3f2; color:#b42318; }
.pill-approved { background:#eef4ff; color:#3538cd; }
.pill-existing { background:#f2f4f7; color:#475467; }
.pill-dependency { background:#f2f4f7; color:#475467; }
.pill-new { background:#ecfdf3; color:#027a48; }

.branch-banner,
.success-banner,
.warning-banner {
    padding: .72rem .9rem;
    border-radius: 12px;
    font-size: .76rem;
    line-height: 1.45;
}
.branch-banner { background:#eef4ff; border:1px solid #dbe5ff; color:#344054; }
.success-banner { background:#ecfdf3; border:1px solid #abefc6; color:#05603a; }
.warning-banner { background:#fffaeb; border:1px solid #fedf89; color:#7a2e0b; }
.mapping {
    padding: .55rem .7rem;
    margin: .3rem 0;
    border-radius: 9px;
    background: #f8f9fc;
    border: 1px solid #eaecf0;
    font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    font-size: .68rem;
    color: #344054;
    overflow-wrap: anywhere;
}
.info-title { font-weight: 800; color: #344054; margin-bottom: .35rem; }

/* ---------- Main controls ---------- */
[data-testid="stTextArea"] textarea,
[data-testid="stTextInput"] input {
    border-radius: 10px !important;
    border: 1px solid #d0d5dd !important;
    background: #ffffff !important;
    color: #101828 !important;
    -webkit-text-fill-color: #101828 !important;
    box-shadow: none !important;
}
[data-testid="stTextArea"] textarea:focus,
[data-testid="stTextInput"] input:focus {
    border-color: #98a2b3 !important;
    box-shadow: 0 0 0 1px #98a2b3 !important;
}
[data-testid="stTextArea"] textarea::placeholder,
[data-testid="stTextInput"] input::placeholder {
    color: #98a2b3 !important;
    -webkit-text-fill-color: #98a2b3 !important;
}
.stButton > button {
    border-radius: 10px !important;
    font-weight: 750 !important;
}

/* ---------- Processing ---------- */
.processing-card {
    padding: .72rem .9rem;
    border-radius: 12px;
    background: #111827;
    color: #f8fafc;
    border: 1px solid #263449;
    box-shadow: 0 8px 22px rgba(16,24,40,.12);
}
.processing-row {
    display:flex;
    align-items:center;
    gap:.6rem;
    font-size:.75rem;
    font-weight:750;
}
.processing-dot {
    width:7px;
    height:7px;
    border-radius:50%;
    background:#cbd5e1;
    animation:copilotPulse 1.1s infinite ease-in-out;
}
.processing-dot:nth-child(2) { animation-delay:.15s; }
.processing-dot:nth-child(3) { animation-delay:.3s; }
.processing-dots { display:flex; gap:.16rem; }
@keyframes copilotPulse {
    0%,80%,100% { opacity:.25; transform:scale(.75); }
    40% { opacity:1; transform:scale(1); }
}

.sound-label {
    color: #cbd5e1;
    font-size: .70rem;
    font-weight: 700;
    padding-top: .25rem;
}
[data-testid="stSidebar"] [data-testid="stCheckbox"] label {
    color: #cbd5e1 !important;
}

.footer {
    text-align:center;
    color:#98a2b3;
    font-size:.66rem;
    padding:1.4rem 0 .2rem;
}

/* Keep Streamlit's native labels compact and readable. */
[data-testid="stWidgetLabel"] p {
    font-size: .74rem !important;
    font-weight: 700 !important;
    color: #344054 !important;
}

/* ---------- Premium visual polish ---------- */
.hero {
    background: linear-gradient(135deg, rgba(255,255,255,.98), rgba(248,250,252,.96));
    border-color: #dfe4ec;
}

.hero-badge {
    letter-spacing: .055em;
}

.flow-node {
    min-height: 66px;
    display: flex;
    flex-direction: column;
    justify-content: center;
}

.section-title {
    margin-top: 1.25rem;
}

.inventory-card,
.module-card {
    transition: transform .12s ease, box-shadow .12s ease, border-color .12s ease;
}

.inventory-card:hover,
.module-card:hover {
    transform: translateY(-1px);
    border-color: #cbd5e1;
    box-shadow: 0 10px 25px rgba(16,24,40,.07);
}

.info-panel {
    padding: 1rem 1.05rem;
    border-radius: 14px;
}


</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# STATE
# ============================================================

backend = CopilotBackend()

for key, value in {
    "result": None,
    "variable_values": {},
    "generated_result": None,
    "publish_result": None,
    "selected_repo": None,
    "selected_branch": None,
    "selection_signature": None,
    "module_decisions": {},
    "working_branch": "",
    "working_branch_created": False,
    "sounds_enabled": True,
    "last_repo_value": None,
    "last_branch_value": None,
    "last_working_branch_value": None,
    "sound_counter": 0,
}.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# HELPERS
# ============================================================


def slugify_branch(requirement: str) -> str:
    text = requirement.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    words = text.split("-")[:5]
    slug = "-".join(words) or "terraform-change"
    return f"ai/{slug}"


def action_class(action: str) -> str:
    return {
        "CREATE": "pill-create",
        "REUSE": "pill-reuse",
        "ADAPT": "pill-adapt",
        "REVIEW": "pill-review",
        "BLOCKED": "pill-blocked",
    }.get(str(action).upper(), "pill-review")


def action_icon(action: str) -> str:
    return {
        "CREATE": "✦",
        "REUSE": "↻",
        "ADAPT": "⌘",
        "REVIEW": "!",
        "BLOCKED": "×",
    }.get(str(action).upper(), "•")


def module_name(item: Any) -> str:
    if isinstance(item, dict):
        return str(item.get("module") or item.get("name") or "unknown")
    return str(item)


def get_actions(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    actions = plan.get("actions") or plan.get("modules") or []
    return [x for x in actions if isinstance(x, dict)]


def render_metric(label: str, value: str, sub: str = "") -> None:
    st.markdown(
        f'<div class="metric-card"><div class="metric-label">{label}</div>'
        f'<div class="metric-value">{value}</div><div class="metric-sub">{sub}</div></div>',
        unsafe_allow_html=True,
    )


def render_processing(text: str) -> None:
    st.markdown(
        f'<div class="processing-card"><div class="processing-row">'
        f'<span>⚡</span><span>{text}</span>'
        f'<span class="processing-dots"><span class="processing-dot"></span>'
        f'<span class="processing-dot"></span><span class="processing-dot"></span></span>'
        f'</div></div>',
        unsafe_allow_html=True,
    )



def _envelope_wav_base64(
    notes: List[tuple[float, float, float]],
    duration: float,
    volume: float = 0.075,
) -> str:
    """Generate restrained enterprise UI audio as an in-memory WAV.

    notes = [(frequency_hz, start_seconds, note_duration_seconds), ...]
    The tones use smooth attack/release curves so they sound like interface
    feedback rather than alarms or notification jingles.
    """
    sample_rate = 24000
    samples = int(sample_rate * duration)
    buffer = io.BytesIO()

    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        frames = bytearray()
        for i in range(samples):
            t = i / sample_rate
            sample_value = 0.0

            for frequency, start_time, note_duration in notes:
                local = t - start_time
                if local < 0 or local > note_duration:
                    continue

                attack = min(1.0, local / 0.018)
                release = min(1.0, (note_duration - local) / 0.075)
                envelope = max(0.0, min(attack, release))

                # Fundamental + a very quiet upper partial gives a clean,
                # modern product-interface character.
                fundamental = math.sin(2 * math.pi * frequency * local)
                partial = 0.16 * math.sin(2 * math.pi * (frequency * 2.0) * local)
                sample_value += envelope * (fundamental + partial)

            sample_value = max(-1.0, min(1.0, sample_value))
            sample = int(32767 * volume * sample_value)
            frames.extend(sample.to_bytes(2, byteorder="little", signed=True))

        wav_file.writeframes(frames)

    return base64.b64encode(buffer.getvalue()).decode("ascii")


# Deliberately restrained sounds: short, warm and non-intrusive.
_SOUND_DATA = {
    # Very short confirmation tick.
    "click": _envelope_wav_base64(
        [(740, 0.0, 0.075)],
        0.09,
        0.055,
    ),

    # Two-note "activity started" cue.
    "processing": _envelope_wav_base64(
        [(392, 0.0, 0.11), (523.25, 0.105, 0.12)],
        0.27,
        0.052,
    ),

    # Clean three-note completion chime.
    "success": _envelope_wav_base64(
        [(523.25, 0.0, 0.13), (659.25, 0.115, 0.14), (783.99, 0.235, 0.20)],
        0.48,
        0.058,
    ),

    # Low, brief acknowledgement for validation failures.
    "error": _envelope_wav_base64(
        [(329.63, 0.0, 0.11), (246.94, 0.105, 0.15)],
        0.30,
        0.048,
    ),
}


def play_ui_sound(kind: str) -> None:
    """Play a restrained browser UI sound on the current Streamlit rerun."""
    if not st.session_state.get("sounds_enabled", True):
        return

    data = _SOUND_DATA.get(kind)
    if not data:
        return

    sound_id = f"copilot-sound-{kind}-{st.session_state.get('sound_counter', 0)}"
    st.session_state.sound_counter = st.session_state.get("sound_counter", 0) + 1

    html = (
        f'<audio id="{sound_id}" autoplay preload="auto" '
        f'aria-hidden="true" style="display:none">'
        f'<source src="data:audio/wav;base64,{data}" type="audio/wav">'
        '</audio>'
    )
    st.markdown(html, unsafe_allow_html=True)


def sound_on_change(current: str, state_key: str, kind: str = "click") -> None:
    """Play a sound only after the first rendered value, when a widget changes."""
    previous = st.session_state.get(state_key)
    if previous is not None and previous != current:
        play_ui_sound(kind)
    st.session_state[state_key] = current


@st.cache_data(ttl=60, show_spinner=False)
def load_repositories() -> List[Dict[str, Any]]:
    return backend.list_target_repositories()


@st.cache_data(ttl=60, show_spinner=False)
def load_branches(repository: str) -> List[Dict[str, Any]]:
    return backend.list_target_branches(repository)


@st.cache_data(ttl=60, show_spinner=False)
def load_inventory(repository: str, branch: str) -> Dict[str, Any]:
    return backend.inspect_target_modules(repository, branch)


# ============================================================
# HERO
# ============================================================

st.markdown(
    """
    <div class="hero">
        <div class="hero-kicker">Infrastructure Engineering Workspace</div>
        <div class="hero-title">⚡ Terraform Infrastructure Copilot</div>
        <div class="hero-subtitle">
            Select the exact GitHub target, inspect the infrastructure already present on that branch,
            choose what to reuse or create, and turn a natural-language requirement into approved Terraform.
        </div>
        <div class="hero-badge">TARGET → INVENTORY → GOVERNANCE → AI PLAN → TERRAFORM → PULL REQUEST</div>
    </div>
    """,
    unsafe_allow_html=True,
)

flow_cols = st.columns([1,.18,1,.18,1,.18,1,.18,1,.18,1])
for i, (icon, label) in enumerate([
    ("🎯", "Target"),
    ("🔎", "Inventory"),
    ("👤", "Decisions"),
    ("🧠", "AI Plan"),
    ("⚙️", "Terraform"),
    ("🚀", "GitHub PR"),
]):
    flow_cols[i * 2].markdown(
        f'<div class="flow-node"><div class="flow-icon">{icon}</div><div class="flow-label">{label}</div></div>',
        unsafe_allow_html=True,
    )
    if i < 5:
        flow_cols[i * 2 + 1].markdown('<div class="flow-arrow">→</div>', unsafe_allow_html=True)

st.write("")


# ============================================================
# SIDEBAR: TARGET + WORKING BRANCH
# ============================================================

with st.sidebar:
    st.markdown(
        '<div class="sidebar-brand-title">⚡ Deployment Console</div>'
        '<div class="sidebar-brand-sub">Target selection, governance and delivery</div>',
        unsafe_allow_html=True,
    )

    sound_col1, sound_col2 = st.columns([1.8, 1])
    with sound_col1:
        st.markdown('<div class="sound-label">🔊 Interface audio</div>', unsafe_allow_html=True)
    with sound_col2:
        st.checkbox(
            "Enable",
            key="sounds_enabled",
            label_visibility="collapsed",
        )

    st.markdown("### Deployment target")

    try:
        with st.spinner("Connecting to GitHub and loading repositories..."):
            repositories = load_repositories()
    except Exception as exc:
        st.error(f"Could not load GitHub repositories: {exc}")
        repositories = []

    if not repositories:
        st.warning("No writable repositories were found for the configured GitHub account/token.")
        st.stop()

    repo_names = [item["name"] for item in repositories]
    repo_map = {item["name"]: item for item in repositories}
    repo_index = repo_names.index(st.session_state.selected_repo) if st.session_state.selected_repo in repo_names else 0

    selected_repo = st.selectbox(
        "Repository",
        repo_names,
        index=repo_index,
        format_func=lambda name: f"{name}  {'🔒' if repo_map[name].get('private') else '🌐'}",
        key="repo_selector",
        help="Writable repositories available to the authenticated GitHub account.",
    )

    sound_on_change(selected_repo, "last_repo_value", "click")

    with st.spinner(f"Loading branches for {selected_repo}..."):
        try:
            branches = load_branches(selected_repo)
        except Exception as exc:
            st.error(f"Could not load branches: {exc}")
            branches = []

    if not branches:
        st.warning("No branches were returned for this repository.")
        st.stop()

    branch_names = [item["name"] for item in branches]
    branch_map = {item["name"]: item for item in branches}
    default_branch = repo_map[selected_repo].get("default_branch")
    previous_branch = st.session_state.selected_branch
    if previous_branch not in branch_names:
        previous_branch = default_branch if default_branch in branch_names else branch_names[0]

    selected_branch = st.selectbox(
        "Base branch",
        branch_names,
        index=branch_names.index(previous_branch),
        format_func=lambda name: f"{name}  {'🛡️ protected' if branch_map[name].get('protected') else ''}".strip(),
        key="branch_selector",
        help="This exact branch is scanned for existing Terraform modules and becomes the PR base.",
    )

    sound_on_change(selected_branch, "last_branch_value", "click")

    signature = f"{selected_repo}::{selected_branch}"
    if st.session_state.selection_signature != signature:
        st.session_state.selection_signature = signature
        st.session_state.selected_repo = selected_repo
        st.session_state.selected_branch = selected_branch
        st.session_state.result = None
        st.session_state.generated_result = None
        st.session_state.publish_result = None
        st.session_state.variable_values = {}
        st.session_state.module_decisions = {}
        st.session_state.working_branch_created = False

    st.divider()
    st.markdown("### Change branch")
    st.caption("Changes are isolated on a new branch. The selected base branch is never modified directly.")

    working_branch = st.text_input(
        "New working branch",
        value=st.session_state.working_branch or "ai/terraform-change",
        key="working_branch_input",
        help="This branch will be created from the selected base branch when you publish the generated Terraform.",
    ).strip()
    st.session_state.working_branch = working_branch
    sound_on_change(working_branch, "last_working_branch_value", "click")

    if st.button("Validate change branch", use_container_width=True):
        play_ui_sound("click")
        if not working_branch:
            st.error("Working branch name cannot be empty.")
        elif working_branch == selected_branch:
            st.error("Working branch must be different from the base branch.")
        else:
            try:
                validation = backend.validate_working_branch(selected_repo, working_branch)
                if validation.get("valid"):
                    st.success(validation.get("message", "Branch name is available."))
                    play_ui_sound("success")
                else:
                    st.error(validation.get("message", "Branch name is not available."))
                    play_ui_sound("error")
            except Exception as exc:
                st.error(f"Could not validate branch: {exc}")

    st.divider()
    st.markdown('<div class="sidebar-field-label">Approved module registry</div>', unsafe_allow_html=True)
    st.markdown('<div class="registry-card"><div class="registry-name">umbrella</div><div class="registry-meta">Approved Terraform catalog</div><div class="registry-branch">feature</div></div>', unsafe_allow_html=True)


# ============================================================
# BRANCH INVENTORY
# ============================================================

st.markdown('<div class="section-title">🔎 Branch infrastructure inventory</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="section-caption">Exact GitHub state under review: <b>{selected_repo}/{selected_branch}</b>. '
    'The scan is branch-wide: root-level main.tf/variables.tf/outputs.tf and Terraform under arbitrary folders are all inspected.</div>',
    unsafe_allow_html=True,
)

processing_placeholder = st.empty()
processing_placeholder.markdown(
    f'<div class="processing-card"><div class="processing-row">'
    f'<span>Scanning {selected_repo}/{selected_branch}</span><span class="processing-dots"><span class="processing-dot"></span><span class="processing-dot"></span><span class="processing-dot"></span></span>'
    f'<span class="processing-dots"><span class="processing-dot"></span>'
    f'<span class="processing-dot"></span><span class="processing-dot"></span></span>'
    f'</div></div>',
    unsafe_allow_html=True,
)
try:
    with st.spinner(f"Scanning {selected_repo}/{selected_branch} recursively..."):
        inventory = load_inventory(selected_repo, selected_branch)
except Exception as exc:
    st.error(f"Could not inspect `{selected_repo}/{selected_branch}`: {exc}")
    inventory = None
finally:
    processing_placeholder.empty()

if inventory is not None:
    module_count = int(inventory.get("module_count", 0))
    approved_count = int(inventory.get("approved_module_count", 0))
    unmanaged_count = int(inventory.get("unmanaged_module_count", 0))
    terraform_file_count = int(inventory.get("terraform_file_count", 0))
    resource_count = int(inventory.get("resource_count", 0))
    module_call_count = int(inventory.get("module_call_count", 0))

    cols = st.columns(4)
    for col, metric in zip(cols, [
        ("REPOSITORY", selected_repo, "selected target"),
        ("BASE BRANCH", selected_branch, "exact branch scanned"),
        ("TERRAFORM FILES", str(terraform_file_count), "entire branch"),
        ("RESOURCES", str(resource_count), f"{module_call_count} module call(s)"),
    ]):
        with col:
            render_metric(*metric)

    st.write("")

    if not inventory.get("exists") or terraform_file_count == 0:
        st.markdown(
            f'<div class="branch-banner">ℹ️ {inventory.get("message", "No Terraform .tf files were found anywhere on this branch.")}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown("**Terraform files discovered anywhere on the branch**")
        file_rows = inventory.get("terraform_files", [])
        for start in range(0, len(file_rows), 3):
            row = file_rows[start:start + 3]
            inv_cols = st.columns(3)
            for col, file_info in zip(inv_cols, row):
                with col:
                    st.markdown(
                        f'<div class="inventory-card">'
                        f'<div class="inventory-name">📄 {file_info["name"]}</div>'
                        f'<div class="inventory-path">{file_info["path"]}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

        resource_types = inventory.get("resource_types", [])
        if resource_types:
            st.markdown("**Resource types found:** " + ", ".join(f"`{x}`" for x in resource_types))

        module_calls = inventory.get("module_calls", [])
        if module_calls:
            st.markdown("**Terraform module blocks found:**")
            for call in module_calls:
                source = call.get("source") or "source not resolved"
                st.caption(f'`module.{call.get("name")}` · `{call.get("path")}` · `{source}`')


# ============================================================
# USER DECISIONS — GENERIC FOR EVERY EXISTING APPROVED MODULE
# ============================================================

st.markdown('<div class="section-title">🛡️ Infrastructure governance</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-caption">These choices apply when the corresponding module is required by the AI plan. '
    'Your explicit choice takes precedence over automatic duplicate detection.</div>',
    unsafe_allow_html=True,
)

existing_modules = (inventory or {}).get("modules", [])
existing_module_calls = (inventory or {}).get("approved_module_calls", [])

decision_entries = {}
for module in existing_modules:
    if module.get("approved"):
        name = str(module.get("name"))
        decision_entries.setdefault(name, {"name": name, "path": module.get("path"), "kind": "directory"})
for call in existing_module_calls:
    name = str(call.get("name"))
    if name:
        entry = decision_entries.setdefault(name, {"name": name, "path": call.get("path"), "kind": "module call"})
        entry["module_call"] = call

approved_existing = list(decision_entries.values())

if not approved_existing:
    st.info("No approved catalog modules are currently present as Terraform module calls or reusable directories on this branch. Required modules will be created from the approved catalog.")
else:
    decision_cols = st.columns(2)
    for index, module in enumerate(approved_existing):
        name = str(module.get("name"))
        label = name.replace("_", " ").title()
        state_key = f"decision_{name}"
        current = st.session_state.module_decisions.get(name, "USE_EXISTING")
        if current not in {"USE_EXISTING", "CREATE"}:
            current = "USE_EXISTING"

        with decision_cols[index % 2]:
            with st.container(border=True):
                st.markdown(f"**📦 {label}**")
                st.caption(
                    f"Existing on `{selected_repo}/{selected_branch}` · "
                    f"{module.get('kind', 'Terraform configuration')} · `{module.get('path')}`"
                )
                choice = st.radio(
                    "Infrastructure strategy",
                    ["Use existing", "Create new"],
                    index=0 if current == "USE_EXISTING" else 1,
                    horizontal=True,
                    key=state_key,
                )
                st.session_state.module_decisions[name] = (
                    "USE_EXISTING" if choice == "Use existing" else "CREATE"
                )

# Convert UI decisions to the planner contract.
infrastructure_decisions = dict(st.session_state.module_decisions)


# ============================================================
# REQUIREMENT
# ============================================================

st.markdown('<div class="section-title">💬 Define the desired infrastructure</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="section-caption">Describe the desired end state. The copilot maps the requirement to approved modules; '
    'the selected branch inventory and your decisions determine reuse versus creation.</div>',
    unsafe_allow_html=True,
)

requirement = st.text_area(
    "Infrastructure requirement",
    height=120,
    label_visibility="collapsed",
    placeholder="Example: Create an AKS cluster with networking and storage. Use a production-sized node pool.",
)

if requirement.strip() and not st.session_state.working_branch_input:
    st.session_state.working_branch = slugify_branch(requirement)

analyze_left, analyze_center, analyze_right = st.columns([1, 1, 1])
with analyze_center:
    analyze_clicked = st.button("Analyze infrastructure", type="primary", use_container_width=True)

if analyze_clicked:
    if not requirement.strip():
        play_ui_sound("error")
        st.error("Please enter an infrastructure requirement.")
    elif not working_branch:
        play_ui_sound("error")
        st.error("Please provide a working branch name.")
    else:
        try:
            with st.spinner(f"Analyzing {selected_repo}/{selected_branch} and resolving approved modules..."):
                st.session_state.result = backend.process_request(
                    requirement=requirement,
                    target_repository=selected_repo,
                    target_branch=selected_branch,
                    infrastructure_decisions=infrastructure_decisions,
                )
            st.session_state.generated_result = None
            st.session_state.publish_result = None
            st.session_state.variable_values = {}
            st.success("Infrastructure analysis completed.")
        except Exception as exc:
            st.error(f"Analysis failed: {exc}")


# ============================================================
# ANALYSIS + GENERATION
# ============================================================

result = st.session_state.result

if result:
    plan = result.get("generation_plan", {})
    actions = get_actions(plan)
    action_map = {str(a.get("module")): a for a in actions}
    generation_order = plan.get("generation_order") or result.get("deployment_order") or []

    selected_modules = result.get("selected_modules", [])
    primary_names = {
        module_name(item) for item in selected_modules
    }
    dependency_names = [
        str(name) for name in generation_order
        if str(name) not in primary_names
    ]
    status = str(plan.get("status", "UNKNOWN")).upper()

    st.divider()
    st.markdown('<div class="section-title">🧠 Copilot plan</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-caption">AI-selected modules are separated from dependencies automatically added by the approved catalog.</div>',
        unsafe_allow_html=True,
    )

    metric_cols = st.columns(4)
    metric_data = [
        ("AI SELECTED", str(len(primary_names)), ", ".join(sorted(primary_names)) or "none"),
        ("DEPENDENCIES", str(len(dependency_names)), ", ".join(dependency_names) or "none"),
        ("FINAL PLAN", str(len(generation_order)), "modules in execution order"),
        ("STATUS", status, "generation readiness"),
    ]
    for col, metric in zip(metric_cols, metric_data):
        with col:
            render_metric(*metric)

    st.write("")
    st.markdown('<div class="section-title">🧩 Execution plan</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-caption">Every module that can affect the Terraform output is visible, including auto-resolved dependencies.</div>',
        unsafe_allow_html=True,
    )

    final_names = generation_order or list(action_map.keys())
    for start in range(0, len(final_names), 3):
        row = final_names[start:start + 3]
        cols = st.columns(3)
        for col, name in zip(cols, row):
            action = action_map.get(str(name), {"module": name, "action": "UNKNOWN"})
            action_type = str(action.get("action", "UNKNOWN")).upper()
            role = "AI-selected" if str(name) in primary_names else "Auto-resolved dependency"
            deps = action.get("dependencies") or []
            dep_html = "".join(f'<span class="pill pill-dependency">depends on {d}</span>' for d in deps)
            with col:
                st.markdown(
                    f'<div class="module-card">'
                    f'<div class="module-name">{action_icon(action_type)} {name}</div>'
                    f'<div class="module-role">{role}</div>'
                    f'<span class="pill {action_class(action_type)}">{action_type}</span>{dep_html}'
                    f'</div>',
                    unsafe_allow_html=True,
                )

    st.write("")
    st.markdown('<div class="section-title">🔗 Dependency sequence</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-caption">Dependency modules appear before the modules that consume their outputs.</div>',
        unsafe_allow_html=True,
    )
    if generation_order:
        flow = st.columns(len(generation_order))
        for i, name in enumerate(generation_order):
            action = action_map.get(str(name), {})
            action_type = str(action.get("action", "UNKNOWN")).upper()
            with flow[i]:
                st.markdown(
                    f'<div class="module-card"><div class="metric-label">STEP {i+1}</div>'
                    f'<div class="module-name">{action_icon(action_type)} {name}</div>'
                    f'<span class="pill {action_class(action_type)}">{action_type}</span></div>',
                    unsafe_allow_html=True,
                )

    # Generation plan details.
    st.markdown('<div class="section-title">📋 Governance details</div>', unsafe_allow_html=True)
    for action in actions:
        module = action.get("module", "unknown")
        action_type = str(action.get("action", "UNKNOWN")).upper()
        user_decision = action.get("user_decision")
        reason = action.get("reason")
        mappings = action.get("mappings") or action.get("mapping") or {}
        with st.expander(f"{action_icon(action_type)} {module} · {action_type}"):
            if user_decision:
                st.write(f"**User decision:** `{user_decision}`")
            if reason:
                st.write(f"**Reason:** {reason}")
            if action.get("dependencies"):
                st.write("**Dependencies:** " + ", ".join(map(str, action["dependencies"])))
            if mappings:
                st.write("**Automatic mappings:**")
                for key, expression in mappings.items():
                    st.markdown(
                        f'<div class="mapping"><b>{module}.{key}</b> ← {expression}</div>',
                        unsafe_allow_html=True,
                    )

    # ========================================================
    # VARIABLES
    # ========================================================

    if status == "READY":
        st.divider()
        st.markdown('<div class="section-title">⚙️ Terraform parameters</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-caption">Only user-configurable inputs are shown. Dependency-generated values are wired automatically.</div>',
            unsafe_allow_html=True,
        )

        schema = backend.get_variable_schema(plan)
        values = st.session_state.variable_values

        for start in range(0, len(schema), 2):
            row = schema[start:start + 2]
            cols = st.columns(2)
            for col, var in zip(cols, row):
                with col:
                    name = str(var["name"])
                    label = str((var.get("ui") or {}).get("label") or name)
                    if var.get("required"):
                        label += " *"
                    description = str(var.get("description") or "")
                    default = var.get("default")
                    var_type = str(var.get("type") or "string").lower()
                    ui = var.get("ui") or {}
                    control = ui.get("control") if isinstance(ui, dict) else None
                    key = f"tfvar_{name}"

                    if control == "select" and ui.get("options"):
                        options = ui["options"]
                        index = options.index(default) if default in options else 0
                        value = st.selectbox(label, options, index=index, key=key, help=description)
                    elif control == "checkbox" or var_type == "bool":
                        value = st.checkbox(label, value=bool(default) if default is not None else False, key=key, help=description)
                    elif control == "number" or var_type == "number":
                        value = st.number_input(label, value=float(default or 0), step=1.0, key=key, help=description)
                        if float(value).is_integer():
                            value = int(value)
                    elif var_type.startswith("list"):
                        text = st.text_area(label, value="\n".join(map(str, default or [])), key=key, help=description)
                        value = [x.strip() for x in text.splitlines() if x.strip()]
                    elif var_type.startswith("map"):
                        text = st.text_area(label, value=json.dumps(default or {}, indent=2), key=key, help=description)
                        try:
                            parsed = json.loads(text)
                            value = parsed if isinstance(parsed, dict) else {}
                        except json.JSONDecodeError:
                            st.error(f"Invalid JSON for `{name}`.")
                            value = {}
                    else:
                        value = st.text_input(label, value=str(default) if default is not None else "", key=key, help=description)
                    values[name] = value

        st.session_state.variable_values = values

        mappings = []
        for action in actions:
            for key, expression in (action.get("mappings") or action.get("mapping") or {}).items():
                mappings.append((action.get("module"), key, expression))
        if mappings:
            with st.expander("🔗 Automatic dependency mappings", expanded=True):
                for module, key, expression in mappings:
                    st.markdown(
                        f'<div class="mapping"><b>{module}.{key}</b> ← {expression}</div>',
                        unsafe_allow_html=True,
                    )

        generate_left, generate_center, generate_right = st.columns([1, 1, 1])
        with generate_center:
            generate_clicked = st.button("Generate Terraform", type="primary", use_container_width=True)

        if generate_clicked:
            play_ui_sound("processing")
            missing = [
                var["name"] for var in schema
                if var.get("required") and values.get(var["name"]) in (None, "", [])
            ]
            if missing:
                st.error("Required variables missing: " + ", ".join(missing))
            else:
                try:
                    with st.spinner("Generating Terraform files..."):
                        st.session_state.generated_result = backend.generate_terraform(plan, values)
                    st.session_state.publish_result = None
                    st.success("Terraform generated successfully.")
                    play_ui_sound("success")
                except Exception as exc:
                    st.error(f"Terraform generation failed: {exc}")


# ============================================================
# GENERATED TERRAFORM + PR
# ============================================================

generated = st.session_state.generated_result
if generated:
    st.divider()
    st.markdown('<div class="section-title">📦 Terraform change set</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-caption">Review the generated artifacts before publishing them to the working branch.</div>',
        unsafe_allow_html=True,
    )

    generated_files = generated.get("files", [])
    cols = st.columns(3)
    for col, metric in zip(cols, [
        ("FILES", str(len(generated_files)), "Terraform artifacts"),
        ("BASE", selected_branch, "PR destination"),
        ("WORKING", working_branch, "new source branch"),
    ]):
        with col:
            render_metric(*metric)

    for path in generated_files:
        st.success(f"✓ `{path}`")

    output = generated.get("output_directory")
    if output:
        out = Path(output)
        for filename in ["main.tf", "variables.tf", "terraform.tfvars", "outputs.tf", "providers.tf"]:
            file_path = out / filename
            if file_path.exists():
                with st.expander(f"📄 {filename}", expanded=filename in {"main.tf", "terraform.tfvars"}):
                    st.code(file_path.read_text(encoding="utf-8"), language="hcl")

    st.divider()
    st.markdown('<div class="section-title">🚀 Delivery preview</div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="info-panel"><div class="info-title">Ready to publish</div>'
        f'<b>{selected_repo}</b><br>'
        f'<span style="font-family:monospace">{working_branch}</span> → '
        f'<span style="font-family:monospace">{selected_branch}</span><br><br>'
        f'{len(generated_files)} Terraform file(s) will be committed to the new working branch and submitted as a pull request.</div>',
        unsafe_allow_html=True,
    )

    publish_left, publish_center, publish_right = st.columns([1, 1, 1])
    with publish_center:
        publish_clicked = st.button("Create branch + pull request", type="primary", use_container_width=True)

    if publish_clicked:
        play_ui_sound("processing")
        if not working_branch:
            st.error("Working branch name is required.")
        elif working_branch == selected_branch:
            st.error("Working branch must be different from the base branch.")
        else:
            try:
                validation = backend.validate_working_branch(selected_repo, working_branch)
                if not validation.get("valid"):
                    st.error(validation.get("message", "Working branch is not available."))
                else:
                    with st.spinner("Creating working branch, publishing Terraform, and opening pull request..."):
                        st.session_state.publish_result = backend.publish_to_github(
                            plan,
                            working_branch=working_branch,
                        )
                    st.success("Pull request created successfully.")
                    play_ui_sound("success")
            except Exception as exc:
                st.error(f"Publishing failed: {exc}")


publish_result = st.session_state.publish_result
if publish_result:
    st.divider()
    st.markdown(
        '<div class="hero"><div class="hero-kicker">Workflow complete</div>'
        '<div class="hero-title">🚀 Pull Request Ready</div>'
        '<div class="hero-subtitle">The generated Terraform is now available for review on the new working branch.</div></div>',
        unsafe_allow_html=True,
    )

    pr = publish_result.get("pull_request", {})
    cols = st.columns(3)
    for col, metric in zip(cols, [
        ("WORKING BRANCH", publish_result.get("branch", "unknown"), "created from selected base"),
        ("BASE BRANCH", publish_result.get("base_branch", selected_branch), "PR destination"),
        ("PULL REQUEST", f'#{pr.get("number", "OPEN")}', "ready for code review"),
    ]):
        with col:
            render_metric(*metric)

    if pr.get("url"):
        st.link_button("Open Pull Request ↗", pr["url"], use_container_width=True)


st.markdown(
    '<div class="footer">Terraform Infrastructure Copilot · Governed inventory · Approved modules · Dependency-aware generation · Pull request delivery</div>',
    unsafe_allow_html=True,
)