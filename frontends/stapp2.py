import os, sys, subprocess
import html
from urllib.request import urlopen
from urllib.parse import quote
if sys.stdout is None: sys.stdout = open(os.devnull, "w")
if sys.stderr is None: sys.stderr = open(os.devnull, "w")
try: sys.stdout.reconfigure(errors='replace')
except: pass
try: sys.stderr.reconfigure(errors='replace')
except: pass
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import streamlit as st
try:
    from streamlit import html as _st_html  # 1.57+
    def _embed_html(body, **kw):
        # st.html() only accepts body; use components.v1.html for iframe-style embedding
        if any(k in kw for k in ("width", "height")):
            from streamlit.components.v1 import html as _comp_html
            _comp_html(body, **kw)
        else:
            _st_html(body)
except (ImportError, AttributeError):
    from streamlit.components.v1 import html as _embed_html  # ≤1.55
import time, json, re, threading, queue
from datetime import datetime
from agentmain import GeneraticAgent
import chatapp_common
from continue_cmd import handle_frontend_command, reset_conversation, list_sessions, extract_ui_messages

st.set_page_config(page_title="DabaoAgent", layout="wide")

ANTHROPIC_CSS = """
<style>
/* ===== Root variables ===== */
:root {
    --anthropic-primary: #D4A27F;
    --anthropic-primary-hover: #C4895F;
    --anthropic-bg: #FAF9F6;
    --anthropic-bg-secondary: #EEECE2;
    --anthropic-code-bg: #F4F1EB;
    --anthropic-text: #1A1714;
    --anthropic-text-secondary: #6B6560;
    --anthropic-border: #D5CEC5;
    --anthropic-sidebar-bg: #F0EDE4;
    --anthropic-accent: #CC785C;
    --anthropic-success: #5A8A5E;
    --anthropic-warning: #C4885A;
    --anthropic-error: #C45A5A;
    --anthropic-info: #5A7A8A;
    --anthropic-font: 'Source Sans Pro', sans-serif;
    --anthropic-mono: 'Source Code Pro', monospace;
}

/* ===== Global ===== */
body, [data-testid="stAppViewContainer"] {
    background-color: var(--anthropic-bg) !important;
    color: var(--anthropic-text) !important;
}

.stApp {
    background-color: var(--anthropic-bg) !important;
}

/* ===== Header / Top bar ===== */
[data-testid="stHeader"], header[data-testid="stHeader"] {
    background-color: var(--anthropic-bg) !important;
    border-bottom: 1px solid var(--anthropic-border) !important;
}
/* Hide default Streamlit toolbar buttons (deploy, hamburger, etc.) */
[data-testid="stToolbar"] {
    visibility: hidden !important;
}
[data-testid="stDecoration"],
#MainMenu {
    display: none !important;
    visibility: hidden !important;
}
/* Restore sidebar expand button (lives inside stToolbar) */
[data-testid="stExpandSidebarButton"],
[data-testid="stExpandSidebarButton"] * {
    visibility: visible !important;
}
/* Only restore ancestor divs that contain the sidebar button */
[data-testid="stToolbar"] div:has([data-testid="stExpandSidebarButton"]) {
    visibility: visible !important;
}
/* Make top-left settings/sidebar toggle darker and easier to see */
button[data-testid="stExpandSidebarButton"] {
    visibility: visible !important;
    background: #F4F1EA !important;
    background-color: #F4F1EA !important;
    border: none !important;
    color: #3B2F2A !important;
    border-radius: 10px !important;
    box-shadow: none !important;
}
button[data-testid="stExpandSidebarButton"]:hover {
    background: #EAE4D9 !important;
    background-color: #EAE4D9 !important;
    border-color: transparent !important;
}
button[data-testid="stExpandSidebarButton"],
button[data-testid="stExpandSidebarButton"] *,
button[data-testid="stExpandSidebarButton"] [data-testid="stIconMaterial"] {
    color: #3B2F2A !important;
    fill: #3B2F2A !important;
    stroke: #3B2F2A !important;
}
/* Hide other toolbar buttons (deploy, etc.) */
button[kind="header"] {
    visibility: hidden !important;
}

/* ===== Sidebar ===== */
[data-testid="stSidebar"], section[data-testid="stSidebar"] {
    background-color: var(--anthropic-sidebar-bg) !important;
    border-right: 1px solid var(--anthropic-border) !important;
}

[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label {
    color: var(--anthropic-text) !important;
}

[data-testid="stSidebar"] hr {
    border-color: var(--anthropic-border) !important;
}

/* ===== Sidebar Selectbox ===== */
[data-testid="stSidebar"] [data-testid="stSelectbox"] {
    width: fit-content !important;
    max-width: 100% !important;
}

[data-testid="stSidebar"] [data-testid="stSelectbox"] > div {
    width: fit-content !important;
    max-width: 100% !important;
}

[data-testid="stSidebar"] [data-testid="stSelectbox"] label,
[data-testid="stSidebar"] .stSelectbox label {
    color: var(--anthropic-text-secondary) !important;
    font-size: 0.9rem !important;
    font-weight: 500 !important;
}

[data-testid="stSidebar"] [data-baseweb="select"] {
    width: fit-content !important;
    max-width: 100% !important;
    display: inline-block !important;
}

[data-testid="stSidebar"] [data-baseweb="select"] > div {
    width: fit-content !important;
    max-width: 100% !important;
    background: #F7F3EC !important;
    border: none !important;
    box-shadow: none !important;
    border-radius: 12px !important;
    min-height: 42px !important;
    padding-right: 1.6rem !important;
    position: relative !important;
}

[data-testid="stSidebar"] [data-baseweb="select"] > div:hover,
[data-testid="stSidebar"] [data-baseweb="select"] > div:focus-within {
    background: #EFE9DE !important;
    border: none !important;
    box-shadow: none !important;
}

[data-testid="stSidebar"] [data-baseweb="select"] input,
[data-testid="stSidebar"] [data-baseweb="select"] span,
[data-testid="stSidebar"] [data-baseweb="select"] div {
    color: var(--anthropic-text) !important;
}

[data-testid="stSidebar"] [data-baseweb="select"] span {
    white-space: nowrap !important;
}

[data-baseweb="popover"],
[data-baseweb="menu"],
[data-baseweb="popover"] > div,
[data-baseweb="popover"] [role="presentation"],
[data-baseweb="popover"] ul,
[data-baseweb="popover"] li,
[data-baseweb="popover"] [role="listbox"],
[data-baseweb="popover"] [role="option"] {
    background: #F7F3EC !important;
    color: var(--anthropic-text) !important;
}

[role="listbox"] {
    background: #F7F3EC !important;
    border: 1px solid var(--anthropic-border) !important;
    border-radius: 14px !important;
    box-shadow: 0 10px 30px rgba(58, 47, 42, 0.12) !important;
    padding: 0.35rem !important;
    color: var(--anthropic-text) !important;
}

[role="option"] {
    color: var(--anthropic-text) !important;
    background: transparent !important;
    border-radius: 10px !important;
}

[role="option"]:hover,
[role="option"][aria-selected="true"] {
    background: #EFE9DE !important;
    color: var(--anthropic-text) !important;
}

/* ===== Title ===== */
h1, .stTitle, [data-testid="stHeading"] h1 {
    color: var(--anthropic-text) !important;
    font-weight: 600 !important;
    letter-spacing: -0.02em !important;
}

/* ===== Agent name input fixed in header bar ===== */
[data-testid="stTextInput"] {
    position: fixed !important;
    top: 0 !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    z-index: 999999 !important;
    height: 60px !important;
    display: flex !important;
    align-items: center !important;
    margin: 0 !important;
    padding: 0 !important;
}
/* Hide the empty container left behind */
[data-testid="stMainBlockContainer"] > [data-testid="stVerticalBlock"] > [data-testid="stElementContainer"]:first-child {
    height: 0 !important;
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
}
[data-testid="stTextInput"] > div {
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    margin: 0 !important;
    position: relative !important;
}
[data-testid="stTextInput"] > label {
    display: none !important;
}
[data-testid="stTextInput"] input[type="text"] {
    font-size: 1.6rem !important;
    font-weight: 600 !important;
    letter-spacing: -0.02em !important;
    color: var(--anthropic-text) !important;
    background-color: var(--anthropic-bg) !important;
    border: none !important;
    border-radius: 0 !important;
    padding: 0.3rem 1.8rem 0.3rem 0.5rem !important;
    box-shadow: none !important;
    width: 320px !important;
    text-align: center !important;
    transition: all 0.2s ease !important;
    cursor: default !important;
    caret-color: #1a1714 !important;
}
[data-testid="stTextInput"] input[type="text"]:hover {
    background-color: var(--anthropic-bg-secondary) !important;
    border-radius: 6px !important;
}
[data-testid="stTextInput"] input[type="text"]:focus {
    background-color: var(--anthropic-bg-secondary) !important;
    border-radius: 6px !important;
    box-shadow: none !important;
    cursor: text !important;
    caret-color: #1a1714 !important;
}
/* Edit pencil icon - visible by default, semi-transparent on focus */
[data-testid="stTextInput"] > div::after {
    content: '✎' !important;
    position: absolute !important;
    right: 8px !important;
    top: 50% !important;
    transform: translateY(-50%) !important;
    font-size: 0.9rem !important;
    color: var(--anthropic-text-secondary) !important;
    pointer-events: none !important;
    opacity: 0.6 !important;
    transition: opacity 0.2s ease !important;
}
[data-testid="stTextInput"] > div:hover::after {
    opacity: 0.85 !important;
}
[data-testid="stTextInput"] > div:focus-within::after {
    opacity: 0 !important;
}

h2, h3, h4, h5, h6 {
    color: var(--anthropic-text) !important;
    font-weight: 500 !important;
}

/* ===== Buttons ===== */
.stButton > button {
    background-color: var(--anthropic-bg-secondary) !important;
    color: var(--anthropic-text) !important;
    border: 1px solid var(--anthropic-border) !important;
    border-radius: 8px !important;
    padding: 0.4rem 1rem !important;
    font-weight: 500 !important;
    transition: all 0.2s ease !important;
}

.stButton > button:hover {
    background-color: var(--anthropic-primary) !important;
    color: white !important;
    border-color: var(--anthropic-primary) !important;
}

.stButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"] {
    background-color: var(--anthropic-primary) !important;
    color: white !important;
    border-color: var(--anthropic-primary) !important;
}

.stButton > button[kind="primary"]:hover,
.stButton > button[data-testid="stBaseButton-primary"]:hover {
    background-color: var(--anthropic-primary-hover) !important;
    border-color: var(--anthropic-primary-hover) !important;
}

/* ===== Chat input ===== */
[data-testid="stChatInput"],
[data-testid="stChatInput"] > div {
    background-color: var(--anthropic-bg) !important;
    border-color: var(--anthropic-border) !important;
}

[data-testid="stChatInput"] {
    margin-bottom: 12px !important;
}

[data-testid="stChatInput"] textarea,
[data-testid="stChatInputTextArea"] {
    color: var(--anthropic-text) !important;
    background-color: var(--anthropic-bg) !important;
    caret-color: #1A1714 !important;
}

[data-testid="stChatInput"] textarea::placeholder {
    color: var(--anthropic-text-secondary) !important;
    opacity: 0.7 !important;
}

/* Chat input container border */
[data-testid="stChatInput"] > div {
    border: 1px solid var(--anthropic-border) !important;
    border-radius: 12px !important;
    min-height: 60px !important;
    padding: 0.35rem 0.45rem 0.35rem 0.8rem !important;
    align-items: center !important;
    gap: 0.5rem !important;
    transition: none !important;
    animation: none !important;
}

[data-testid="stChatInput"] > div:focus-within {
    border-color: var(--anthropic-primary) !important;
    box-shadow: 0 0 0 2px rgba(212, 162, 127, 0.2) !important;
}

[data-testid="stChatInput"] textarea,
[data-testid="stChatInputTextArea"] {
    min-height: 1.5rem !important;
    padding: 0.35rem 0 !important;
    line-height: 1.5 !important;
    transition: none !important;
    animation: none !important;
}

/* Chat send button */
[data-testid="stChatInput"] button,
[data-testid="stChatInputSubmitButton"] {
    background-color: var(--anthropic-primary) !important;
    color: white !important;
    border-radius: 12px !important;
    width: 60px !important;
    height: 60px !important;
    min-width: 60px !important;
    min-height: 60px !important;
    padding: 0 !important;
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    flex-shrink: 0 !important;
    transition: none !important;
    animation: none !important;
}

[data-testid="stChatInput"] button svg,
[data-testid="stChatInputSubmitButton"] svg,
[data-testid="stChatInput"] button [data-testid="stIconMaterial"],
[data-testid="stChatInputSubmitButton"] [data-testid="stIconMaterial"] {
    width: 1.25rem !important;
    height: 1.25rem !important;
    font-size: 1.25rem !important;
}

[data-testid="stChatInput"] button:hover {
    background-color: var(--anthropic-primary-hover) !important;
}

/* Stop streaming button - fixed at bottom center, above chat input */
.stop-btn-anchor {
    display: none !important;
}

/* Collapse the wrapper so it doesn't push chat bubbles */
[data-testid="stElementContainer"]:has(.stop-btn-anchor) {
    height: 0 !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: visible !important;
}

[data-testid="stVerticalBlock"]:has(.stop-btn-anchor):not(:has([data-testid="stChatMessage"])) {
    position: fixed !important;
    bottom: 5.75rem !important;
    left: 50% !important;
    transform: translateX(-50%) !important;
    z-index: 1000 !important;
    width: auto !important;
    background: transparent !important;
    pointer-events: none !important;
    gap: 0 !important;
}

[data-testid="stVerticalBlock"]:has(.stop-btn-anchor):not(:has([data-testid="stChatMessage"])) > * {
    pointer-events: auto !important;
}

[data-testid="stVerticalBlock"]:has(.stop-btn-anchor):not(:has([data-testid="stChatMessage"])) [data-testid="stButton"] {
    margin: 0 !important;
}

[data-testid="stVerticalBlock"]:has(.stop-btn-anchor):not(:has([data-testid="stChatMessage"])) [data-testid="stButton"] > button {
    border-radius: 999px !important;
    padding: 0.35rem 1.1rem !important;
    min-height: 2rem !important;
    font-size: 0.84rem !important;
    font-weight: 500 !important;
    line-height: 1 !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.12) !important;
    white-space: nowrap !important;
}

[data-testid="stVerticalBlock"]:has(.stop-btn-anchor):not(:has([data-testid="stChatMessage"])) [data-testid="stButton"] > button[kind="primary"],
[data-testid="stVerticalBlock"]:has(.stop-btn-anchor):not(:has([data-testid="stChatMessage"])) [data-testid="stButton"] > button[data-testid="stBaseButton-primary"] {
    background-color: rgba(212, 162, 127, 0.95) !important;
    border-color: rgba(212, 162, 127, 0.95) !important;
}

[data-testid="stVerticalBlock"]:has(.stop-btn-anchor):not(:has([data-testid="stChatMessage"])) [data-testid="stButton"] > button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 3px 12px rgba(0,0,0,0.15) !important;
}

/* ===== Chat messages ===== */
[data-testid="stChatMessage"] {
    background-color: var(--anthropic-bg) !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 1rem 1.2rem !important;
    margin-bottom: 0.5rem !important;
}

/* Assistant messages - clean white like Anthropic */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
    background-color: var(--anthropic-bg) !important;
}

/* User messages - subtle bordered box */
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
    background-color: var(--anthropic-bg) !important;
    border: 1px solid var(--anthropic-border) !important;
    border-radius: 12px !important;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
}

/* Chat message text */
[data-testid="stChatMessage"] p,
[data-testid="stChatMessage"] .stMarkdown {
    color: var(--anthropic-text) !important;
    line-height: 1.6 !important;
}

/* Message timestamp */
.msg-timestamp {
    text-align: left;
    font-size: 0.73rem;
    color: var(--anthropic-text-secondary);
    margin-top: -0.3rem;
    margin-bottom: 0.2rem;
    opacity: 0.55;
    font-family: var(--anthropic-mono);
    letter-spacing: 0.02em;
}

/* ===== Chat avatars ===== */
[data-testid="stChatMessageAvatarContainer"] {
    width: 36px !important;
    height: 36px !important;
}
[data-testid="stChatMessageAvatarContainer"] > div,
[data-testid*="stChatMessageAvatar"],
[data-testid*="chatAvatar"] {
    width: 36px !important;
    height: 36px !important;
    border-radius: 50% !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    overflow: hidden !important;
}

/* User avatar - warm brown gradient */
[data-testid*="stChatMessageAvatar"]:has(svg),
[data-testid*="chatAvatar"][data-testid*="user"],
[data-testid*="stChatMessageAvatar"][data-testid*="User"],
[data-testid*="stChatMessageAvatar"][data-testid*="user"] {
    background: linear-gradient(145deg, #D8B08A 0%, #B98259 100%) !important;
    border: 1px solid rgba(150, 102, 67, 0.22) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.34), 0 2px 6px rgba(104, 76, 54, 0.10) !important;
}
/* Assistant avatar - cream gradient */
[data-testid*="chatAvatar"][data-testid*="assistant"],
[data-testid*="stChatMessageAvatar"][data-testid*="Assistant"],
[data-testid*="stChatMessageAvatar"][data-testid*="assistant"],
[data-testid="stChatMessageAvatarContainer"] > div {
    background: linear-gradient(145deg, #F6F1E9 0%, #E5D7C7 100%) !important;
    border: 1px solid rgba(187, 165, 141, 0.50) !important;
    box-shadow: inset 0 1px 0 rgba(255,255,255,0.72), 0 2px 6px rgba(104, 76, 54, 0.08) !important;
}

/* ===== Inline code (not inside pre/code blocks) ===== */
:not(pre) > code {
    background-color: var(--anthropic-code-bg) !important;
    border: 1px solid var(--anthropic-border) !important;
    border-radius: 4px !important;
    padding: 0.15em 0.4em !important;
    font-size: 0.9em !important;
    color: var(--anthropic-text) !important;
}

/* ===== Code blocks (pre) ===== */
pre, .stCodeBlock, .stCodeBlock pre {
    background-color: var(--anthropic-code-bg) !important;
    border: 1px solid var(--anthropic-border) !important;
    border-radius: 8px !important;
}

/* Code inside pre blocks: no extra border/background */
pre code,
.stCodeBlock code,
[data-testid="stChatMessage"] pre code,
[data-testid="stChatMessage"] .stCodeBlock code {
    background-color: transparent !important;
    border: none !important;
    padding: 0 !important;
    font-size: inherit !important;
    color: var(--anthropic-text) !important;
}

/* ===== Toast / Alerts ===== */
[data-testid="stToast"] {
    background-color: var(--anthropic-bg-secondary) !important;
    border: 1px solid var(--anthropic-border) !important;
    border-radius: 8px !important;
    color: var(--anthropic-text) !important;
}

/* ===== Captions ===== */
.stCaption, [data-testid="stCaptionContainer"] {
    color: var(--anthropic-text-secondary) !important;
}

/* ===== Divider ===== */
[data-testid="stHorizontalBlock"] hr,
hr {
    border-color: var(--anthropic-border) !important;
}

/* ===== Scrollbar ===== */
::-webkit-scrollbar {
    width: 6px;
    height: 6px;
}
::-webkit-scrollbar-track {
    background: var(--anthropic-bg);
}
::-webkit-scrollbar-thumb {
    background: var(--anthropic-border);
    border-radius: 3px;
}
::-webkit-scrollbar-thumb:hover {
    background: var(--anthropic-text-secondary);
}

/* ===== Links ===== */
a {
    color: var(--anthropic-accent) !important;
}
a:hover {
    color: var(--anthropic-primary-hover) !important;
}

/* ===== Error/Warning/Info/Success ===== */
[data-testid="stAlert"] {
    border-radius: 8px !important;
}

/* ===== Bottom padding for chat ===== */
[data-testid="stBottomBlockContainer"] {
    background-color: var(--anthropic-bg) !important;
}

/* ===== Gear icon to open sidebar ===== */
#sidebar-gear-toggle {
    position: fixed !important;
    top: 12px !important;
    left: 12px !important;
    z-index: 999999 !important;
    width: 36px !important;
    height: 36px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 1.3rem !important;
    color: var(--anthropic-text-secondary) !important;
    background: var(--anthropic-bg-secondary) !important;
    border: 1px solid var(--anthropic-border) !important;
    border-radius: 8px !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    opacity: 0.7 !important;
    user-select: none !important;
}
#sidebar-gear-toggle:hover {
    opacity: 1 !important;
    color: var(--anthropic-primary) !important;
    border-color: var(--anthropic-primary) !important;
    transform: rotate(30deg) !important;
}
/* Hide gear when sidebar is open */
body:has([data-testid="stSidebar"][aria-expanded="true"]) #sidebar-gear-toggle {
    display: none !important;
}
</style>
"""

ANTHROPIC_SELECTBOX_SCRIPT = """
<div></div>
<script>
(function() {
    const hostWin = window.parent;
    const doc = hostWin.document;
    const LABEL_TEXT = '备用链路';
    const EXTRA_WIDTH = 56;
    const TIMER_KEY = '__anthropicSelectboxFixedWidthTimer';
    const FONT_LABELS = {
        '100': '标准（100%）',
        '112.5': '偏大（112.5%）',
        '125': '更大（125%）',
        '137.5': '超大（137.5%）'
    };

    function measureTextWidth(text, sourceEl) {
        const canvas = hostWin.__anthropicSelectboxMeasureCanvas || (hostWin.__anthropicSelectboxMeasureCanvas = doc.createElement('canvas'));
        const ctx = canvas.getContext('2d');
        const style = sourceEl ? hostWin.getComputedStyle(sourceEl) : null;
        const font = style ? `${style.fontWeight} ${style.fontSize} ${style.fontFamily}` : '400 14px sans-serif';
        ctx.font = font;
        return Math.ceil(ctx.measureText(text || '').width);
    }

    function ensureSidebarSettingsTitle() {
        const sidebar = doc.querySelector('[data-testid="stSidebar"]');
        if (!sidebar) return;
        const collapseBtn = sidebar.querySelector('button[kind="header"], [data-testid="stSidebarCollapseButton"] button, [data-testid="stSidebarCollapseButton"]');
        if (!collapseBtn || !collapseBtn.parentElement) return;
        let title = doc.getElementById('custom-sidebar-settings-title');
        if (!title) {
            title = doc.createElement('span');
            title.id = 'custom-sidebar-settings-title';
            title.textContent = '设置';
            title.style.cssText = 'font-size:14px;font-weight:600;color:rgb(38,39,48);margin-right:8px;line-height:1;display:inline-flex;align-items:center;white-space:nowrap;';
        }
        if (collapseBtn.previousElementSibling !== title) {
            collapseBtn.parentElement.insertBefore(title, collapseBtn);
        }
    }

    function applyLiveFontPreview() {
        const sidebar = doc.querySelector('[data-testid="stSidebar"]');
        if (!sidebar) return;
        const sliderLabel = Array.from(sidebar.querySelectorAll('label, p')).find((el) => el.textContent && el.textContent.trim() === '字体大小');
        if (!sliderLabel) return;
        const container = sliderLabel.closest('[data-testid="stWidgetLabel"]')?.parentElement?.parentElement || sliderLabel.closest('[data-testid="stSlider"]') || sliderLabel.closest('div');
        if (!container) return;
        const input = container.querySelector('input[type="range"]');
        if (!input) return;
        const caption = container.querySelector('[data-testid="stCaptionContainer"] p, p');

        const updateFont = () => {
            const raw = parseFloat(input.value);
            if (!Number.isFinite(raw)) return;
            doc.documentElement.style.setProperty('font-size', raw + '%', 'important');
            if (caption) {
                const key = String(raw % 1 === 0 ? raw.toFixed(0) : raw);
                caption.textContent = FONT_LABELS[key] || `${raw.toFixed(1)}%`;
            }
        };

        if (input.dataset.liveFontBound !== '1') {
            input.addEventListener('input', updateFont);
            input.addEventListener('change', updateFont);
            input.dataset.liveFontBound = '1';
        }
        updateFont();
    }

    function applyFixedWidth() {
        const sidebar = doc.querySelector('[data-testid="stSidebar"]');
        if (!sidebar) return;
        const boxes = sidebar.querySelectorAll('[data-testid="stSelectbox"]');
        boxes.forEach((box) => {
            const labelNode = box.querySelector('label [data-testid="stMarkdownContainer"] p, label p');
            if (!labelNode || labelNode.textContent.trim() !== LABEL_TEXT) return;
            const selectRoot = box.querySelector('[data-baseweb="select"]');
            const trigger = selectRoot && selectRoot.firstElementChild;
            const maxLabelNode = box.querySelector('[data-testid="sidebar-llm-max-label"]');
            const text = ((maxLabelNode && maxLabelNode.textContent) || '').trim();
            if (!selectRoot || !trigger || !text) return;

            const textWidth = measureTextWidth(text, trigger);
            const targetWidth = Math.min(sidebar.clientWidth - 32, Math.max(96, textWidth + EXTRA_WIDTH));
            const valueWrap = trigger.firstElementChild;
            const arrowWrap = valueWrap && valueWrap.nextElementSibling;
            const valueNode = valueWrap && valueWrap.querySelector('[value]');

            box.style.setProperty('width', targetWidth + 'px', 'important');
            box.style.setProperty('max-width', targetWidth + 'px', 'important');
            box.style.setProperty('flex', '0 0 ' + targetWidth + 'px', 'important');

            selectRoot.style.setProperty('width', targetWidth + 'px', 'important');
            selectRoot.style.setProperty('min-width', targetWidth + 'px', 'important');
            selectRoot.style.setProperty('max-width', targetWidth + 'px', 'important');

            trigger.style.setProperty('width', targetWidth + 'px', 'important');
            trigger.style.setProperty('min-width', targetWidth + 'px', 'important');
            trigger.style.setProperty('max-width', targetWidth + 'px', 'important');
            trigger.style.setProperty('padding-right', '0px', 'important');
            trigger.style.setProperty('justify-content', 'flex-start', 'important');
            trigger.style.setProperty('box-sizing', 'border-box', 'important');

            if (valueWrap) {
                valueWrap.style.setProperty('flex', '1 1 auto', 'important');
                valueWrap.style.setProperty('min-width', '0px', 'important');
                valueWrap.style.setProperty('max-width', 'calc(100% - 24px)', 'important');
                valueWrap.style.setProperty('padding-right', '4px', 'important');
            }
            if (valueNode) {
                valueNode.style.setProperty('max-width', '100%', 'important');
            }
            if (arrowWrap) {
                arrowWrap.style.setProperty('margin-left', 'auto', 'important');
                arrowWrap.style.setProperty('padding-right', '0px', 'important');
                arrowWrap.style.setProperty('width', '24px', 'important');
                arrowWrap.style.setProperty('min-width', '24px', 'important');
                arrowWrap.style.setProperty('display', 'flex', 'important');
                arrowWrap.style.setProperty('justify-content', 'flex-end', 'important');
                arrowWrap.style.setProperty('align-items', 'center', 'important');
                arrowWrap.style.setProperty('overflow', 'visible', 'important');
            }
        });
        ensureSidebarSettingsTitle();
        applyLiveFontPreview();
    }

    if (hostWin[TIMER_KEY]) {
        hostWin.clearInterval(hostWin[TIMER_KEY]);
    }
    hostWin[TIMER_KEY] = hostWin.setInterval(applyFixedWidth, 300);
    hostWin.setTimeout(applyFixedWidth, 60);
    hostWin.setTimeout(applyFixedWidth, 300);
    hostWin.setTimeout(applyFixedWidth, 1000);
    applyFixedWidth();
})();
</script>
"""

@st.cache_resource
def init():
    try:
        agent = GeneraticAgent()
    except Exception:
        return None
    if agent.llmclient is None:
        return None
    threading.Thread(target=agent.run, daemon=True).start()
    return agent


def build_dynamic_font_css(scale_percent: float) -> str:
    root_percent = max(100.0, min(200.0, float(scale_percent)))
    rem_scale = root_percent / 100.0
    return f"""
<style id="dynamic-font-scale-style">
:root, html, body, [data-testid="stAppViewContainer"], .stApp {{
    font-size: {root_percent:.1f}% !important;
}}
body, [data-testid="stAppViewContainer"], .stApp {{
    --app-font-scale: {rem_scale:.3f};
}}
[data-testid="stAppViewContainer"], .stApp, .stApp p, .stApp li, .stApp label,
.stApp div[data-testid="stMarkdownContainer"], .stApp textarea, .stApp input,
.stApp button, .stApp [data-testid="stChatMessageContent"], .stApp .stCaption {{
    font-size: calc(1rem * var(--app-font-scale, 1)) !important;
}}
</style>
"""


def build_dynamic_font_update_script(scale_percent: float) -> str:
    css = json.dumps(build_dynamic_font_css(scale_percent))
    return f"""
<script>
(() => {{
    const cssText = {css};
    const parser = new DOMParser();
    const parsed = parser.parseFromString(cssText, 'text/html');
    const nextStyle = parsed.querySelector('#dynamic-font-scale-style');
    if (!nextStyle) return;
    const hostDoc = window.parent && window.parent.document ? window.parent.document : document;
    const existing = hostDoc.querySelector('#dynamic-font-scale-style');
    if (existing) {{
        existing.textContent = nextStyle.textContent;
    }} else {{
        hostDoc.head.appendChild(nextStyle);
    }}
}})();
</script>
"""


def build_header_agent_badge_script() -> str:
    return """
<script>
(() => {
    const hostWin = window.parent || window;
    const hostDoc = hostWin.document || document;
    const BADGE_ID = 'generic-agent-header-badge';
    const STYLE_ID = 'generic-agent-header-badge-style';

    const ensureStyle = () => {
        if (hostDoc.getElementById(STYLE_ID)) return;
        const style = hostDoc.createElement('style');
        style.id = STYLE_ID;
        style.textContent = `
            #${BADGE_ID} {
                position: absolute;
                left: 50%;
                top: 50%;
                transform: translate(-50%, -50%);
                display: inline-flex;
                align-items: center;
                justify-content: center;
                white-space: nowrap;
                font-size: 2.75rem;
                font-weight: 600;
                line-height: 1.2;
                color: #000000;
                padding: 0;
                border-radius: 0;
                background: transparent;
                border: none;
                box-shadow: none;
                pointer-events: none;
                z-index: 20;
            }
        `;
        hostDoc.head.appendChild(style);
    };

    const findHeaderRoot = () => {
        const candidates = [
            'header[data-testid="stHeader"]',
            '[data-testid="stHeader"]',
            'header',
        ];
        for (const selector of candidates) {
            const root = hostDoc.querySelector(selector);
            if (root) return root;
        }
        return null;
    };

    const ensureBadge = () => {
        ensureStyle();
        const headerRoot = findHeaderRoot();
        if (!headerRoot) return;
        headerRoot.style.position = 'relative';

        let badge = hostDoc.getElementById(BADGE_ID);
        if (!badge) {
            badge = hostDoc.createElement('div');
            badge.id = BADGE_ID;
            badge.textContent = 'DabaoAgent';
        }
        if (badge.parentElement !== headerRoot) {
            headerRoot.appendChild(badge);
        }

        const titleEl = hostDoc.querySelector('h1');
        if (titleEl) {
            const titleStyle = hostWin.getComputedStyle(titleEl);
            badge.style.fontSize = titleStyle.fontSize;
            badge.style.fontWeight = titleStyle.fontWeight;
            badge.style.lineHeight = titleStyle.lineHeight;
            badge.style.fontFamily = titleStyle.fontFamily;
            badge.style.letterSpacing = titleStyle.letterSpacing;
            badge.style.color = '#000000';
        }
    };

    if (hostWin.__genericAgentHeaderBadgeTimer) {
        hostWin.clearInterval(hostWin.__genericAgentHeaderBadgeTimer);
    }
    hostWin.__genericAgentHeaderBadgeTimer = hostWin.setInterval(ensureBadge, 500);
    hostWin.setTimeout(ensureBadge, 80);
    hostWin.setTimeout(ensureBadge, 400);
    ensureBadge();
})();
</script>
"""

agent = init()

st.session_state.setdefault("autonomous_enabled", False)
st.session_state.setdefault("messages", [])
st.session_state.setdefault("streaming", False)
st.session_state.setdefault("stopping", False)
st.session_state.setdefault("partial_response", "")
st.session_state.setdefault("reply_ts", "")
st.session_state.setdefault("current_prompt", "")
st.session_state.setdefault("display_queue", None)
st.session_state.setdefault("last_reply_time", 0)
st.session_state.setdefault("selected_llm_idx", 0)
st.session_state.setdefault("agent_name", "DabaoAgent")

_embed_html(build_dynamic_font_css(110.0))
_embed_html(ANTHROPIC_SELECTBOX_SCRIPT, height=0, width=0)
_embed_html(build_header_agent_badge_script(), height=0, width=0)

if agent is None:
    st.warning("⚠️ 未配置任何可用的 LLM 接口，请在侧边栏打开 🔑 API 密钥设置，填入信息后点击保存。")
else:
    with st.chat_message("assistant"):
        st.markdown(f'<div class="msg-timestamp">{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</div>', unsafe_allow_html=True)
        st.write("欢迎使用 DabaoAgent ~")


def fold_turns(text):
    """Return list of segments: [{'type':'text','content':...}, {'type':'fold','title':...,'content':...}]"""
    # 先把4+反引号块替换为占位符，避免误切子agent嵌套的 LLM Running
    _ph = []
    safe = re.sub(r'`{4,}.*?`{4,}', lambda m: (_ph.append(m.group(0)), f'\x00PH{len(_ph)-1}\x00')[1], text, flags=re.DOTALL)
    # 流式中间态：末尾可能有未闭合的4+反引号块，也需保护
    safe = re.sub(r'`{4,}[^`].*$', lambda m: (_ph.append(m.group(0)), f'\x00PH{len(_ph)-1}\x00')[1], safe, flags=re.DOTALL)
    parts = re.split(r'(\**LLM Running \(Turn \d+\) \.\.\.\*\**)', safe)
    parts = [re.sub(r'\x00PH(\d+)\x00', lambda m: _ph[int(m.group(1))], p) for p in parts]
    if len(parts) < 4: return [{'type': 'text', 'content': text}]
    segments = []
    if parts[0].strip(): segments.append({'type': 'text', 'content': parts[0]})
    turns = []
    for i in range(1, len(parts), 2):
        marker = parts[i]
        content = parts[i+1] if i+1 < len(parts) else ''
        turns.append((marker, content))
    for idx, (marker, content) in enumerate(turns):
        if idx < len(turns) - 1:
            _c = re.sub(r'`{3,}.*?`{3,}|<thinking>.*?</thinking>', '', content, flags=re.DOTALL)
            matches = re.findall(r'<summary>\s*((?:(?!<summary>).)*?)\s*</summary>', _c, re.DOTALL)
            if matches:
                title = matches[0].strip()
                title = title.split('\n')[0]
                if len(title) > 50: title = title[:50] + '...'
            else: title = marker.strip('*')
            segments.append({'type': 'fold', 'title': title, 'content': content})
        else: segments.append({'type': 'text', 'content': marker + content})
    return segments
def render_segments(segments, suffix=''):
    # 整块重画：调用方用 slot.container() 包裹，保证 DOM 路径稳定、跨 rerun 对齐（消除"灰色重影"）。
    # heartbeat 空转时 segments 不变 → Streamlit 后端 diff 无变化 → 前端零闪烁；
    # 但 container/markdown 本身是 API 调用，StopException 仍会被抛出（abort 照常起作用）。
    for seg in segments:
        if seg['type'] == 'fold':
            with st.expander(seg['title'], expanded=False): st.markdown(seg['content'])
        else:
            st.markdown(seg['content'] + suffix)



@st.fragment
def render_sidebar():
    st.session_state.setdefault("autonomous_enabled", False)
    if agent is not None:
        llm_options, current_idx = agent.list_llms(), agent.llm_no
        st.session_state.selected_llm_idx = current_idx
        llm_labels = {idx: f"{idx}: {(name or "").strip()}" for idx, name, _ in llm_options}
        st.caption(f"当前使用的LLM为：{current_idx}: {agent.get_llm_name()}", help="可在下方选择链路")
        st.markdown(f'<div data-testid="sidebar-llm-max-label" style="display:none">{html.escape(max(llm_labels.values(), key=len, default=""))}</div>', unsafe_allow_html=True)
        selected_idx = st.selectbox("选择链路：", [idx for idx, _, _ in llm_options], index=next((i for i, (idx, _, _) in enumerate(llm_options) if idx == current_idx), 0), format_func=llm_labels.get, key="sidebar_llm_select")
        if selected_idx != current_idx:
            agent.next_llm(selected_idx)
            st.session_state.selected_llm_idx = selected_idx
            st.toast(f"已切换到备用链路：{llm_labels[selected_idx]}")
            st.rerun()
    else:
        st.caption("🔴 未加载 LLM 配置")

    last_reply_time = st.session_state.get("last_reply_time", 0)
    if last_reply_time > 0 and agent is not None:
        st.caption(f"空闲时间：{int(time.time()) - last_reply_time}秒", help="当超过30分钟未收到回复时，系统会自动任务")

    if agent is not None:
        if st.button("强行停止任务"):
            agent.abort(); st.toast("已发送停止信号")

    if agent is not None:
        if st.button("重新注入工具"):
            agent.llmclient.last_tools = ""
            try:
                import os as _os
                hist_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "assets", "tool_usable_history.json")
                with open(hist_path, "r", encoding="utf-8") as _f: tool_hist = json.load(_f)
                agent.llmclient.backend.history.extend(tool_hist)
                st.toast(f"已重新注入工具，追加了 {len(tool_hist)} 条示范记录")
            except Exception as e: st.toast(f"注入工具示范失败: {e}")

    if agent is not None:
        if st.button("🐱 桌面宠物"):
            kwargs = {"creationflags": 0x08} if sys.platform == "win32" else {}
            import os as _os
            pet_script = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "desktop_pet_v2.pyw")
            if not _os.path.exists(pet_script): pet_script = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "desktop_pet.pyw")
            subprocess.Popen([sys.executable, pet_script], **kwargs)
            def _pet_req(q):
                def _do():
                    try: urlopen(f"http://127.0.0.1:41983/?{q}", timeout=2)
                    except Exception: pass
                threading.Thread(target=_do, daemon=True).start()
            agent._pet_req = _pet_req
            if not hasattr(agent, "_turn_end_hooks"): agent._turn_end_hooks = {}
            def _pet_hook(ctx):
                parts = [f"Turn {ctx.get('turn','?')}"]
                if ctx.get("summary"): parts.append(ctx["summary"])
                if ctx.get("exit_reason"): parts.append("任务已完成")
                _pet_req(f"msg={quote(chr(10).join(parts))}")
                if ctx.get("exit_reason"): _pet_req("state=idle")
            agent._turn_end_hooks["pet"] = _pet_hook
            st.toast("桌面宠物已启动")

    st.divider()
    with st.expander("🔑 API 密钥设置", expanded=(agent is None)):
        api_key = st.text_input("API Key", type="password", placeholder="sk-...", key="sidebar_api_key")
        api_base = st.text_input("API Base URL", placeholder="https://api.openai.com/v1", key="sidebar_api_base")
        model_name = st.text_input("模型名称", placeholder="gpt-5.4", key="sidebar_api_model")
        cfg_name = st.text_input("配置标识", placeholder="ui-config", key="sidebar_api_cfg_name")
        if st.button("💾 保存并加载", key="sidebar_save_api"):
            if not api_key or not api_base or not model_name:
                st.toast("❌ 请填写 API Key、Base URL 和模型名称")
            else:
                try:
                    import json as _json, os as _os
                    json_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "..", "mykey.json")
                    existing = {}
                    if _os.path.exists(json_path):
                        with open(json_path, "r", encoding="utf-8") as _f:
                            existing = _json.load(_f)
                    cfg_key = "native_oai_ui_config_sidebar"
                    existing[cfg_key] = {
                        "name": cfg_name or "UI配置",
                        "apikey": api_key,
                        "apibase": api_base,
                        "model": model_name,
                    }
                    with open(json_path, "w", encoding="utf-8") as _f:
                        _json.dump(existing, _f, indent=2, ensure_ascii=False)
                    import llmcore as _lm
                    _lm._mykey_mtime = None
                    if agent is not None:
                        agent.load_llm_sessions()
                    else:
                        st.cache_resource.clear()
                    st.toast("✅ API 配置已保存并加载")
                    st.rerun()
                except Exception as e:
                    st.toast(f"❌ 保存失败: {e}")

    st.divider()
    if st.button("开始空闲自主行动"):
        st.session_state.last_reply_time = int(time.time()) - 1800
        st.toast("已将上次回复时间设为1800秒前"); st.rerun()
    if st.session_state.autonomous_enabled:
        if st.button("⏸️ 禁止自主行动"):
            st.session_state.autonomous_enabled = False
            st.toast("⏸️ 已禁止自主行动"); st.rerun()
        st.caption("🟢 自主行动运行中，会在你离开它30分钟后自动进行")
    else:
        if st.button("▶️ 允许自主行动", type="primary"):
            st.session_state.autonomous_enabled = True
            st.toast("✅ 已允许自主行动"); st.rerun()
        st.caption("🔴 自主行动已停止")

with st.sidebar: render_sidebar()


def _reset_and_rerun():
    st.session_state.streaming = False
    st.session_state.stopping = False
    st.session_state.display_queue = None
    st.session_state.partial_response = ""
    st.session_state.reply_ts = ""
    st.session_state.current_prompt = ""
    st.session_state.last_reply_time = int(time.time())
    st.rerun()


_js_scroll_fix = (
    "!function(){var p=window.parent;if(p.__sfx2)return;p.__sfx2=1;var d=p.document;"
    "function f(){var m=d.querySelector('section.main');if(!m)return;"
    "var s=m.scrollTop;m.style.minHeight=m.scrollHeight+1+'px';void m.offsetHeight;"
    "m.style.minHeight='';void m.offsetHeight;m.scrollTop=s}"
    "d.addEventListener('transitionend',function(e){"
    "e.target.closest&&e.target.closest('details')&&setTimeout(f,60)},!0);"
    "new MutationObserver(function(){setTimeout(f,80)})"
    ".observe(d.body,{subtree:1,attributes:1,attributeFilter:['open']});"
    "setInterval(f,5000)}()"
)
_js_ime_fix = ("" if os.name == "nt" else
    "!function(){if(window.parent.__imeFix)return;window.parent.__imeFix=1;"
    "var d=window.parent.document,c=0;"
    "d.addEventListener('compositionstart',()=>c=1,!0);"
    "d.addEventListener('compositionend',()=>c=0,!0);"
    "function f(){d.querySelectorAll('textarea[data-testid=stChatInputTextArea]')"
    ".forEach(t=>{t.__imeFix||(t.__imeFix=1,t.addEventListener('keydown',e=>{"
    "e.key==='Enter'&&!e.shiftKey&&(e.isComposing||c||e.keyCode===229)&&"
    "(e.stopImmediatePropagation(),e.preventDefault())},!0))})}"
    "f();new MutationObserver(f).observe(d.body,{childList:1,subtree:1})}()")
_embed_html(f'<script>{_js_scroll_fix};{_js_ime_fix}</script>', height=0)

# Streamlit toolbar + settings full Chinese translation
_embed_html(f'<script>'
    "!function(){var p=window.parent;if(p.__tbzh)return;p.__tbzh=1;"
    "var M={Rerun:'重新运行',R:'R','Auto rerun':'自动重新运行','Always rerun':'始终自动运行',"
    "Running:'运行中','Please wait':'请稍候','Done!':'完成','Nada':'无',"
    "Deploy:'部署','Deploy now':'立即部署','Deploy this app':'部署此应用','Share this app':'分享应用',"
    "'Host on Community Cloud':'托管至社区云','Streamlit for Teams':'Streamlit团队版','Streamlit Cloud':'Streamlit云',"
    "'Streamlit Community Cloud':'Streamlit社区云',"
    "Settings:'设置',About:'关于',Print:'打印','Clear cache':'清除缓存',"
    "Community:'社区','Get help':'获取帮助','Report a bug':'报告问题',"
    "'Streamlit documentation':'Streamlit文档','Ask a question':'提问',"
    "'Rerun the app':'重新运行应用','Rerun the script':'重新运行脚本','Appearance':'外观','General':'通用',"
    "'Custom Theme':'自定义主题','Use system setting':'使用系统设置',"
    "Light:'浅色',Dark:'深色','Active theme':'当前主题',Font:'字体',"
    "'Font size':'字体大小','Base font size':'基础字体大小',Text:'文本',"
    "Headers:'标题','Code font':'代码字体','Show a button':'显示按钮',"
    "'Show \"Deploy\"':'显示部署按钮','Show the toolbar':'显示工具栏',"
    "'Editor settings':'编辑器设置','Run on save':'保存时运行',"
    "'Show sidebar':'显示侧边栏','Wide mode':'宽屏模式',"
    "Advanced:'高级',Theme:'主题',Server:'服务器',"
    "'Email for bug reports':'问题反馈邮箱','Save settings':'保存设置',"
    "Cancel:'取消','Primary color':'主色调','Background color':'背景色',"
    "'Secondary background color':'次要背景色','Text color':'文本颜色',"
    "'Font family':'字体',Default:'默认','Sans serif':'无衬线',"
    "Serif:'衬线',Monospace:'等宽','Update theme':'更新主题',"
    "'Run on save & auto':'保存时自动运行','Run on save &':'保存时运行',"
    "'Always rerun and show changes':'自动运行并显示变更',"
    "Stop:'停止','Stop recording':'停止录制','Record a screencast':'录制屏幕录像',"
    "'Configuration':'配置','The app is running':'应用正在运行'};"
    "function T(el){"
    "var w=p.document.createTreeWalker(el,NodeFilter.SHOW_TEXT),n=[];"
    "var nd;while(nd=w.nextNode())n.push(nd);"
    "for(var i=0;i<n.length;i++){"
    "var tx=n[i].textContent,t0=tx;"
    "for(var k in M){if(tx.indexOf(k)!==-1){tx=tx.replace(k,M[k])}}"
    "if(tx!==t0)n[i].textContent=tx;}}"
    "function S(){"
    "try{"
    "var tb=p.document.querySelector('[data-testid=\"stToolbar\"]');if(tb)T(tb);"
    "p.document.querySelectorAll('[data-testid=\"stMainMenu\"] *').forEach(function(e){"
    "var v=e.textContent.trim();if(M[v]&&e.childNodes.length===1)e.textContent=M[v];});"
    "p.document.querySelectorAll('[data-testid=\"stMainMenuList\"] *').forEach(function(e){"
    "var v=e.textContent.trim();if(M[v]&&e.childNodes.length===1)e.textContent=M[v];});"
    "p.document.querySelectorAll('[data-baseweb=\"popover\"] [role=\"dialog\"] *').forEach(function(e){"
    "var v=e.textContent.trim();if(M[v]&&e.childNodes.length===1)e.textContent=M[v];});"
    "p.document.querySelectorAll('[data-testid=\"stStatusWidget\"]').forEach(function(e){T(e);});"
    "p.document.querySelectorAll('[data-testid=\"stAppViewBlockContainer\"] [data-testid=\"stText\"]').forEach(function(e){"
    "var v=e.textContent.trim();if(v.indexOf('Running')===0||v.indexOf('Please wait')===0)T(e);});"
    "}catch(e){}}"
    "setTimeout(S,300);setTimeout(S,1500);setTimeout(S,4000);"
    "new MutationObserver(function(){setTimeout(S,300)}).observe(p.document.body,{childList:1,subtree:1});"
    "}()"
    '</script>')


def start_agent_task(prompt):
    st.session_state.display_queue = agent.put_task(prompt, source="user")
    st.session_state.streaming, st.session_state.stopping, st.session_state.partial_response = True, False, ""
    st.session_state.reply_ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.current_prompt = prompt


def poll_agent_output(max_items=20):
    q = st.session_state.display_queue
    if q is None:
        st.session_state.streaming = False
        return False
    done = False
    for _ in range(max_items):
        try:
            item = q.get_nowait()
        except queue.Empty:
            break
        if "next" in item: st.session_state.partial_response = item["next"]
        if "done" in item:
            st.session_state.partial_response = item["done"]
            done = True
            break
    if done: st.session_state.streaming = st.session_state.stopping = False; st.session_state.display_queue = None
    return done


def render_message(role, content, ts="", unsafe_allow_html=True):
    with st.chat_message(role):
        if ts: st.markdown(f'<div class="msg-timestamp">{ts}</div>', unsafe_allow_html=True)
        st.markdown(content, unsafe_allow_html=unsafe_allow_html)


def finish_streaming_message():
    reply_ts = st.session_state.reply_ts
    st.session_state.messages.append({"role": "assistant", "content": st.session_state.partial_response, "time": reply_ts})
    st.session_state.last_reply_time = int(time.time())
    st.session_state.partial_response = st.session_state.reply_ts = st.session_state.current_prompt = ""


def render_streaming_area():
    if not st.session_state.streaming: return
    reply_ts = st.session_state.reply_ts
    with st.container():
        if st.button("⏹️ 停止生成", type="primary"):
            agent.abort(); st.session_state.stopping = True; st.toast("已发送停止信号"); st.rerun()
    with st.chat_message("assistant"):
        st.markdown(f'<div class="msg-timestamp">{reply_ts}</div>', unsafe_allow_html=True)
        segs = fold_turns(st.session_state.partial_response)
        render_segments(segs, suffix=" ▍")
    if poll_agent_output(): finish_streaming_message()
    else: time.sleep(0.2)
    st.rerun()


if agent is not None:
    for msg in st.session_state.messages:
        if msg["role"] == "assistant":
            with st.chat_message("assistant"):
                if msg.get("time"): st.markdown(f'<div class="msg-timestamp">{msg["time"]}</div>', unsafe_allow_html=True)
                render_segments(fold_turns(msg["content"]))
        else:
            render_message(msg["role"], msg["content"], ts=msg.get("time", ""), unsafe_allow_html=True)
    if st.session_state.streaming: render_streaming_area()

if prompt := st.chat_input("请输入指令", disabled=(st.session_state.streaming or agent is None)):
    if agent is None:
        st.toast("❌ 请先在侧边栏配置 API 密钥")
    else:
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        cmd = (prompt or "").strip()
        if cmd == "/new":
            st.session_state.messages = [{"role": "assistant", "content": reset_conversation(agent), "time": ts}]
            _reset_and_rerun()
        elif cmd.startswith("/continue"):
            m = re.match(r'/continue\s+(\d+)\s*$', cmd.strip())
            sessions = list_sessions(exclude_pid=os.getpid()) if m else []
            idx = int(m.group(1)) - 1 if m else -1
            target = sessions[idx][0] if 0 <= idx < len(sessions) else None
            result = handle_frontend_command(agent, cmd)
            history = extract_ui_messages(target) if target and result.startswith("✅") else None
            tail = [{"role": "assistant", "content": result, "time": ts}]
            if history:
                st.session_state.messages = history + tail
            else:
                st.session_state.messages = list(st.session_state.messages) + [{"role": "user", "content": cmd, "time": ts}] + tail
            _reset_and_rerun()
        else:
            st.session_state.messages.append({"role": "user", "content": prompt, "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
            if hasattr(agent, "_pet_req") and not prompt.startswith("/"): agent._pet_req("state=walk")
            start_agent_task(prompt)
            st.rerun()

if agent is not None and st.session_state.autonomous_enabled:
    st.markdown(f'<div id="last-reply-time" style="display:none">{st.session_state.get("last_reply_time", int(time.time()))}</div>', unsafe_allow_html=True)
