"""Sistema visual "Pregão": terminal de mercado com vidro translúcido."""
from __future__ import annotations

import streamlit as st
from streamlit import config as st_config

FONTE = "Geist"
FONTE_MONO = "Geist Mono"
FONTE_URL = "https://fonts.googleapis.com/css2?family=Geist:wght@300..700&family=Geist+Mono:wght@400..600&display=swap"
_URL_GEIST = "https://fonts.googleapis.com/css2?family=Geist:wght@300..700&display=swap"
_URL_MONO = "https://fonts.googleapis.com/css2?family=Geist+Mono:wght@400..600&display=swap"

TOKENS = {
    "Dark": {
        "canvas": "#060A13", "canvas2": "#0A1122", "field": "#0E1628",
        "surface": "rgba(20,29,52,.52)", "surface_solid": "#0F1729", "raised": "rgba(255,255,255,.05)",
        "ink": "#E9EEF7", "muted": "#8D97AD", "faint": "#5B6680",
        "line": "rgba(255,255,255,.09)", "line_strong": "rgba(255,255,255,.18)", "line_hex": "#1F2A42",
        "primary": "#5B8CFF", "primary_hover": "#7FA6FF", "primary_soft": "rgba(91,140,255,.15)",
        "up": "#2BD99F", "up_soft": "rgba(43,217,159,.13)", "down": "#FF5C7A", "down_soft": "rgba(255,92,122,.13)",
        "amber": "#F5B547", "amber_soft": "rgba(245,181,71,.15)",
        "glow1": "rgba(91,140,255,.20)", "glow2": "rgba(43,217,159,.09)", "grid": "rgba(255,255,255,.035)",
        "highlight": "rgba(255,255,255,.07)",
        "shadow": "0 1px 0 rgba(255,255,255,.04) inset, 0 20px 40px -24px rgba(0,0,0,.8)",
    },
    "Light": {
        "canvas": "#EDF1F7", "canvas2": "#F8FAFD", "field": "#FFFFFF",
        "surface": "rgba(255,255,255,.62)", "surface_solid": "#FFFFFF", "raised": "rgba(15,23,42,.04)",
        "ink": "#0B1220", "muted": "#566176", "faint": "#8A94A8",
        "line": "rgba(15,23,42,.09)", "line_strong": "rgba(15,23,42,.18)", "line_hex": "#DCE2EC",
        "primary": "#2D4BFF", "primary_hover": "#1F38D6", "primary_soft": "rgba(45,75,255,.10)",
        "up": "#0E9F6E", "up_soft": "rgba(14,159,110,.11)", "down": "#E11D48", "down_soft": "rgba(225,29,72,.10)",
        "amber": "#C47A0A", "amber_soft": "rgba(245,181,71,.20)",
        "glow1": "rgba(45,75,255,.13)", "glow2": "rgba(14,159,110,.08)", "grid": "rgba(15,23,42,.04)",
        "highlight": "rgba(255,255,255,.7)",
        "shadow": "0 1px 0 rgba(255,255,255,.8) inset, 0 18px 40px -26px rgba(15,23,42,.35)",
    },
}
# apelidos usados pelas telas
for _t in TOKENS.values():
    _t.update(alert=_t["down"], alert_soft=_t["down_soft"], ok=_t["up"], ok_soft=_t["up_soft"],
              tag=_t["amber"], tag_ink="#0B1220", warn_soft=_t["amber_soft"],
              varejo=_t["primary"], atacado=_t["down"], pdv=_t["amber"])


def modo() -> str:
    return "Dark" if st.session_state.get("tema") == "Dark" else "Light"


def tokens() -> dict:
    return TOKENS[modo()]


def _tema_nativo(t: dict) -> None:
    opcoes = {
        "theme.base": "dark" if modo() == "Dark" else "light",
        "theme.primaryColor": t["primary"], "theme.backgroundColor": t["canvas"],
        "theme.secondaryBackgroundColor": t["field"], "theme.textColor": t["ink"],
        "theme.borderColor": t["line_hex"], "theme.dataframeBorderColor": t["line_hex"],
        "theme.dataframeHeaderBackgroundColor": t["field"], "theme.linkColor": t["primary"],
        "theme.redColor": t["down"], "theme.greenColor": t["up"], "theme.blueColor": t["primary"],
        "theme.yellowColor": t["amber"],
        "theme.font": f"{FONTE}:{_URL_GEIST}, sans-serif", "theme.headingFont": f"{FONTE}:{_URL_GEIST}, sans-serif",
        "theme.codeFont": f"{FONTE_MONO}:{_URL_MONO}, monospace",
        "theme.baseRadius": "0.65rem", "theme.buttonRadius": "0.65rem", "theme.showWidgetBorder": True,
    }
    for chave, valor in opcoes.items():
        try:
            st_config.set_option(chave, valor)
        except Exception:
            pass


def aplicar() -> None:
    t = tokens()
    _tema_nativo(t)
    st.html(f"<style>{_css(t)}</style>")


def _css(t: dict) -> str:
    v = "\n".join(f"  --ps-{k.replace('_', '-')}: {val};" for k, val in t.items() if k != "shadow")
    return f"""
@import url('{FONTE_URL}');
:root {{
{v}
  --ps-shadow: {t['shadow']};
  --ps-font: '{FONTE}', -apple-system, 'Segoe UI', sans-serif;
  --ps-mono: '{FONTE_MONO}', ui-monospace, 'SFMono-Regular', Menlo, monospace;
  --ps-glass: blur(22px) saturate(160%);
}}

/* ---------- base e fundo ---------- */
html, body, .stApp, button, input, textarea, select, [data-testid="stMarkdownContainer"] {{ font-family: var(--ps-font); }}
[data-testid="stIconMaterial"], .ms {{ font-family: 'Material Symbols Rounded' !important; font-weight: 400; }}
.stApp {{
  color: var(--ps-ink);
  background-color: var(--ps-canvas);
  background-image:
    radial-gradient(1100px 620px at 88% -12%, var(--ps-glow1), transparent 62%),
    radial-gradient(900px 560px at -12% 18%, var(--ps-glow2), transparent 60%),
    linear-gradient(180deg, transparent 0, transparent 140px, var(--ps-canvas) 720px),
    linear-gradient(var(--ps-grid) 1px, transparent 1px),
    linear-gradient(90deg, var(--ps-grid) 1px, transparent 1px),
    linear-gradient(180deg, var(--ps-canvas2), var(--ps-canvas) 720px);
  background-size: auto, auto, auto, 56px 56px, 56px 56px, auto;
  background-attachment: fixed;
}}
[data-testid="stAppViewContainer"], [data-testid="stMain"], [data-testid="stBottomBlockContainer"] {{ background: transparent !important; }}
[data-testid="stAppDeployButton"], [data-testid="stMainMenu"], [data-testid="stDecoration"],
[data-testid="stToolbarActions"], [data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {{ display: none !important; }}
[data-testid="stMainBlockContainer"] {{ max-width: 1440px; padding: 5.2rem 2.5rem 5rem; }}
@media (max-width: 760px) {{ [data-testid="stMainBlockContainer"] {{ padding: 4.6rem 1rem 4rem; }} }}
/* troca de tema suave, só em propriedades baratas de animar */
.stApp, header[data-testid="stHeader"], [class*="st-key-psc_"], .ps-q, .ps-split, .ps-ticker, [data-testid="stExpander"] details,
[data-baseweb="select"] > div, [data-baseweb="input"], [data-testid="stBaseButton-secondary"] {{
  transition: background-color .35s ease, border-color .35s ease, color .35s ease, box-shadow .35s ease;
}}
@media (prefers-reduced-motion: reduce) {{ [data-testid="stMainBlockContainer"] * {{ animation: none !important; transition: none !important; }} }}

/* botão de tema fixo no topo */
.st-key-ps_tema {{ position: fixed !important; top: 11px; right: 20px; z-index: 1000002; width: auto !important; gap: 0; }}
.st-key-ps_tema [data-testid="stElementContainer"]:has(iframe) {{ display: none; }}
.st-key-ps_tema button {{
  width: 38px; height: 38px; min-height: 38px; padding: 0; border-radius: 50%;
  background: var(--ps-surface) !important; border: 1px solid var(--ps-line) !important;
  backdrop-filter: var(--ps-glass); -webkit-backdrop-filter: var(--ps-glass);
  transition: transform .25s cubic-bezier(.2,.7,.2,1), border-color .2s ease, box-shadow .2s ease !important;
}}
.st-key-ps_tema button:hover {{ transform: rotate(-18deg) scale(1.06); border-color: var(--ps-primary) !important;
  box-shadow: 0 0 0 4px var(--ps-primary-soft); }}
.st-key-ps_tema button [data-testid="stIconMaterial"] {{ color: var(--ps-ink); font-size: 20px; }}
@media (max-width: 760px) {{ .st-key-ps_tema {{ top: 9px; right: 12px; }} }}
#ps-fs {{
  position: fixed; top: 11px; right: 66px; z-index: 1000002; width: 38px; height: 38px; border-radius: 50%; display: grid; place-items: center;
  background: var(--ps-surface); border: 1px solid var(--ps-line); color: var(--ps-ink); cursor: pointer;
  backdrop-filter: var(--ps-glass); -webkit-backdrop-filter: var(--ps-glass);
  transition: transform .25s cubic-bezier(.2,.7,.2,1), border-color .2s ease, box-shadow .2s ease;
}}
#ps-fs svg {{ width: 18px; height: 18px; }}
#ps-fs:hover {{ transform: scale(1.06); border-color: var(--ps-primary); box-shadow: 0 0 0 4px var(--ps-primary-soft); }}
@media (max-width: 760px) {{ #ps-fs {{ top: 9px; right: 58px; }} }}

/* presença */
.ps-user-meta {{ display: flex; flex-wrap: wrap; gap: 4px 12px; margin-top: .45rem; font-size: .78rem; color: var(--ps-muted); }}
.ps-status {{ display: inline-flex; align-items: center; gap: 6px; color: var(--ps-faint); font-weight: 500; }}
.ps-status i {{ width: 7px; height: 7px; border-radius: 50%; background: var(--ps-faint); }}
.ps-status.on {{ color: var(--ps-up); }}
.ps-status.on i {{ background: var(--ps-up); animation: ps-pulse 2s infinite; }}

/* aviso de novas solicitações (administradores) */
.st-key-ps_chat {{ position: fixed !important; left: 22px; bottom: 22px; z-index: 1000001; width: auto !important; }}
.st-key-ps_chat [data-testid="stPopoverButton"] {{ height: 52px; min-width: 52px; border-radius: 26px; background: linear-gradient(135deg, var(--ps-primary), #7A3FD1) !important;
  border: 0 !important; box-shadow: 0 14px 34px -12px var(--ps-primary); transition: transform .2s; }}
.st-key-ps_chat [data-testid="stPopoverButton"]:hover {{ transform: translateY(-2px) scale(1.04); }}
.st-key-ps_chat [data-testid="stPopoverButton"], .st-key-ps_chat [data-testid="stPopoverButton"] * {{ color: #fff !important; font-weight: 700; }}
[data-testid="stPopoverBody"]:has(.ps-chat-top) {{ width: 420px !important; max-width: 92vw; }}
.ps-chat-top b {{ display: block; font-size: 15px; }} .ps-chat-top span {{ font-size: 11.5px; color: var(--ps-muted); }}
.ps-msgs {{ display: flex; flex-direction: column; gap: 6px; }}
.ps-msg {{ max-width: 82%; align-self: flex-start; background: var(--ps-raised); border-radius: 12px 12px 12px 4px; padding: 6px 10px; }}
.ps-msg.eu {{ align-self: flex-end; background: var(--ps-primary); border-radius: 12px 12px 4px 12px; }}
.ps-msg.eu p, .ps-msg.eu small {{ color: #fff !important; }}
.ps-msg i {{ font-style: normal; font-size: 11px; font-weight: 700; color: var(--ps-primary); }}
.ps-msg p {{ margin: 2px 0; font-size: 13px; line-height: 1.4; color: var(--ps-ink); white-space: pre-wrap; word-break: break-word; }}
.ps-msg small {{ font-size: 10px; color: var(--ps-faint); }}
.ps-mencao {{ color: #7A3FD1; }} .ps-msg.eu .ps-mencao {{ color: #fff; text-decoration: underline; }}
.ps-msg-vazio {{ color: var(--ps-faint); font-size: 12.5px; text-align: center; padding: 30px 0; }}
.st-key-ps_notif {{ position: fixed !important; right: 22px; bottom: 150px; z-index: 1000001; width: 340px !important; padding: 12px 14px; border-radius: 16px; background: var(--ps-surface-solid); border: 1px solid var(--ps-line); box-shadow: 0 18px 48px -18px rgba(15,23,42,.5); animation: ps-entra .35s ease-out; }}
.st-key-ps_notif .ps-aviso span {{ white-space: normal; line-height: 1.4; }}
.st-key-ps_aviso {{
  position: fixed !important; right: 22px; bottom: 22px; z-index: 1000001; width: 340px !important; padding: 16px;
  background: color-mix(in srgb, var(--ps-surface-solid) 78%, transparent); border: 1px solid var(--ps-line);
  border-radius: 16px; backdrop-filter: var(--ps-glass); -webkit-backdrop-filter: var(--ps-glass);
  box-shadow: 0 30px 60px -24px rgba(0,0,0,.45); animation: ps-aviso .45s cubic-bezier(.2,.8,.2,1) both;
}}
@keyframes ps-aviso {{ from {{ opacity: 0; transform: translateY(16px) scale(.98); }} to {{ opacity: 1; transform: none; }} }}
.ps-aviso {{ display: flex; gap: 12px; align-items: flex-start; }}
.ps-aviso .ps-live {{ margin-top: 6px; flex: none; background: var(--ps-amber); }}
.ps-aviso b {{ display: block; font-weight: 600; color: var(--ps-ink); }}
.ps-aviso span {{ color: var(--ps-muted); font-size: .86rem; }}

/* menus do topo: vidro e abertura suave */
[data-testid="stTopNavPopover"] {{ animation: ps-drop .22s cubic-bezier(.2,.8,.2,1) both; transform-origin: top left; }}
[data-testid="stTopNavPopoverBody"] {{
  background: color-mix(in srgb, var(--ps-surface-solid) 82%, transparent) !important;
  backdrop-filter: var(--ps-glass); -webkit-backdrop-filter: var(--ps-glass);
  border: 1px solid var(--ps-line) !important; border-radius: 14px !important; box-shadow: 0 24px 48px -20px rgba(0,0,0,.5) !important;
}}
[data-testid="stTopNavDropdownLink"] {{ border-radius: 9px; transition: background-color .15s ease, color .15s ease; }}
[data-testid="stTopNavDropdownLink"]:hover {{ background: var(--ps-primary-soft) !important; color: var(--ps-primary) !important; }}
[data-testid="stTopNavSection"], [data-testid="stTopNavLink"] {{ transition: background-color .2s ease, color .2s ease; border-radius: 9px; }}
[data-testid="stTopNavSection"]:hover, [data-testid="stTopNavLink"]:hover {{ background: var(--ps-raised) !important; }}
@keyframes ps-drop {{ from {{ opacity: 0; transform: translateY(-6px) scale(.98); }} to {{ opacity: 1; transform: none; }} }}

/* ---------- ilha dinâmica: menu das ferramentas centralizado no topo ---------- */
[data-testid="stTopNav"] {{
  position: absolute !important; left: 50% !important; top: 50% !important; transform: translate(-50%, -50%);
  max-width: calc(100vw - 560px); flex: none !important; gap: 2px; justify-content: center;
  padding: 5px 8px !important; border-radius: 999px !important;
  background: color-mix(in srgb, var(--ps-surface-solid) 72%, transparent) !important;
  border: 1px solid var(--ps-line); backdrop-filter: blur(18px) saturate(170%); -webkit-backdrop-filter: blur(18px) saturate(170%);
  box-shadow: 0 10px 30px -16px rgba(15,23,42,.38), inset 0 1px 0 rgba(255,255,255,.28);
  transition: padding .35s cubic-bezier(.2,.8,.2,1), box-shadow .35s ease, transform .35s cubic-bezier(.2,.8,.2,1);
}}
[data-testid="stTopNav"]::before {{
  content: ""; position: absolute; inset: -1px; border-radius: inherit; padding: 1.2px; pointer-events: none; opacity: 0;
  background: linear-gradient(90deg, transparent 0%, var(--ps-primary) 30%, var(--ps-up) 50%, var(--ps-primary) 70%, transparent 100%) 0 0 / 200% 100%;
  -webkit-mask: linear-gradient(#000 0 0) content-box, linear-gradient(#000 0 0); -webkit-mask-composite: xor; mask-composite: exclude;
  transition: opacity .35s ease; animation: ps-gira 3.2s linear infinite paused;
}}
[data-testid="stTopNav"]:hover {{
  padding: 7px 12px !important; transform: translate(-50%, -50%) scale(1.03);
  box-shadow: 0 18px 44px -18px color-mix(in srgb, var(--ps-primary) 60%, transparent), inset 0 1px 0 rgba(255,255,255,.3);
}}
[data-testid="stTopNav"]:hover::before {{ opacity: 1; animation-play-state: running; }}
@keyframes ps-gira {{ from {{ background-position: 0% 0; }} to {{ background-position: 200% 0; }} }}
[data-testid="stTopNav"] [data-testid="stTopNavLink"], [data-testid="stTopNav"] [data-testid="stTopNavSection"] {{
  border-radius: 999px !important; transition: background-color .2s ease, color .2s ease, transform .2s cubic-bezier(.2,.8,.2,1) !important;
}}
[data-testid="stTopNav"] [data-testid="stTopNavLink"]:hover, [data-testid="stTopNav"] [data-testid="stTopNavSection"]:hover {{
  transform: translateY(-1px); background: var(--ps-primary-soft) !important; color: var(--ps-primary) !important;
}}
[data-testid="stTopNavPopover"] {{ transform-origin: top center; }}

/* ---------- gaveta lateral (filtros e uploads) com fundo desfocado ---------- */
[data-testid="stPopoverBody"]:has(.ps-gaveta) {{
  position: fixed !important; inset: 10px 10px 10px auto !important; transform: none !important; translate: none !important;
  width: min(420px, 94vw) !important; max-width: none !important; height: calc(100vh - 20px) !important; max-height: none !important;
  z-index: 1000010 !important; overflow-y: auto !important; padding: 18px 20px 22px !important; border-radius: 22px !important;
  background: color-mix(in srgb, var(--ps-surface-solid) 90%, transparent) !important; border: 1px solid var(--ps-line) !important;
  box-shadow: -24px 0 60px -30px rgba(15,23,42,.45), 0 0 0 100vmax color-mix(in srgb, var(--ps-canvas) 30%, transparent) !important;
  animation: ps-gaveta-in .38s cubic-bezier(.2,.8,.2,1);
}}
/* fundo desfocado: o site inteiro (fora da gaveta, que fica num portal à parte) ganha desfoque enquanto a gaveta está aberta */
body:has([data-testid="stPopoverBody"] .ps-gaveta) [data-testid="stApp"] {{
  filter: blur(7px) saturate(120%) brightness(.96); transition: filter .28s ease-out; pointer-events: none;
}}
[data-testid="stApp"] {{ transition: filter .22s ease-out; }}
[data-testid="stPopoverBody"]:has(.ps-gaveta) [data-testid="stWidgetLabel"] p {{ font-size: .78rem; color: var(--ps-muted); }}
@keyframes ps-gaveta-in {{ from {{ opacity: 0; transform: translateX(28px); }} to {{ opacity: 1; transform: none; }} }}
@keyframes ps-fundo-in {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}
.ps-gaveta {{ display: flex; align-items: flex-start; justify-content: space-between; gap: 10px; margin-bottom: 6px; }}
.ps-gaveta b {{ font-size: 1.28rem; letter-spacing: -.02em; margin-right: 10px; }}
.ps-gaveta span {{ font-size: .8rem; color: var(--ps-muted); }}
.ps-gaveta-x {{ width: 32px; height: 32px; border-radius: 50%; border: 1px solid var(--ps-line); background: var(--ps-surface-solid); color: var(--ps-ink);
  cursor: pointer; font-size: 14px; display: grid; place-items: center; transition: transform .2s, background .2s; flex: none; }}
.ps-gaveta-x:hover {{ transform: rotate(90deg); background: var(--ps-primary-soft); color: var(--ps-primary); }}
.ps-atualizado {{ display: inline-flex; align-items: center; gap: 7px; height: 30px; padding: 0 12px; border-radius: 999px; white-space: nowrap;
  font-size: .78rem; color: var(--ps-muted); background: var(--ps-surface); border: 1px solid var(--ps-line); backdrop-filter: blur(12px); }}
body.ps-selo-curto .ps-atualizado .ps-at-txt {{ display: none; }}
body.ps-selo-oculto .st-key-reg_topo [data-testid="stHtml"]:has(.ps-atualizado) {{ display: none; }}
.ps-atualizado i {{ width: 8px; height: 8px; border-radius: 50%; background: var(--ps-up); box-shadow: 0 0 0 3px color-mix(in srgb, var(--ps-up) 22%, transparent); }}

/* ---------- cores sempre do tema DESTA sessão ----------
   O tema nativo do Streamlit é do servidor inteiro: com um usuário no claro e outro no escuro, ele pode chegar trocado.
   Menu, menus suspensos, gavetas e campos usam então as cores da sessão (variáveis --ps-*), nunca as do tema nativo. */
[data-testid="stTopNav"] [data-testid="stTopNavLink"], [data-testid="stTopNav"] [data-testid="stTopNavSection"],
[data-testid="stTopNav"] [data-testid="stTopNavLink"] *, [data-testid="stTopNav"] [data-testid="stTopNavSection"] * {{ color: var(--ps-ink) !important; }}
[data-testid="stTopNav"] [data-testid="stTopNavLink"][aria-current="page"], [data-testid="stTopNav"] [data-testid="stTopNavLink"][aria-current="page"] *,
[data-testid="stTopNav"] [data-testid="stTopNavSection"][aria-expanded="true"], [data-testid="stTopNav"] [data-testid="stTopNavSection"][aria-expanded="true"] * {{ color: var(--ps-primary) !important; }}
[data-testid="stTopNavPopoverBody"], [data-testid="stTopNavPopover"] > div {{ background: color-mix(in srgb, var(--ps-surface-solid) 94%, transparent) !important; }}
[data-testid="stTopNavDropdownLink"], [data-testid="stTopNavDropdownLink"] * {{ color: var(--ps-ink) !important; opacity: 1 !important; }}
[data-testid="stTopNavDropdownLink"]:hover, [data-testid="stTopNavDropdownLink"]:hover * {{ color: var(--ps-primary) !important; }}
[data-testid="stPopoverBody"] {{ background: var(--ps-surface-solid) !important; color: var(--ps-ink) !important; border-color: var(--ps-line) !important; }}
[data-testid="stPopoverBody"] p, [data-testid="stPopoverBody"] label, [data-testid="stPopoverBody"] span:not([data-baseweb="tag"] *),
[data-testid="stPopoverBody"] [data-testid="stMarkdownContainer"] {{ color: var(--ps-ink); }}
[data-testid="stPopoverBody"] [data-testid="stCaptionContainer"], [data-testid="stPopoverBody"] [data-testid="stCaptionContainer"] * {{ color: var(--ps-muted) !important; }}
[data-testid="stWidgetLabel"] p, [data-testid="stWidgetLabel"] label {{ color: var(--ps-muted) !important; }}
[data-baseweb="select"] > div, [data-baseweb="input"] > div, [data-baseweb="base-input"], [data-baseweb="textarea"] > div {{
  background: var(--ps-field) !important; border-color: var(--ps-line) !important; color: var(--ps-ink) !important; }}
[data-baseweb="select"] *, [data-baseweb="input"] input, [data-baseweb="textarea"] textarea, [data-baseweb="base-input"] input {{ color: var(--ps-ink) !important; -webkit-text-fill-color: var(--ps-ink); }}
[data-baseweb="select"] input::placeholder, [data-baseweb="input"] input::placeholder {{ color: var(--ps-faint) !important; -webkit-text-fill-color: var(--ps-faint); }}
[data-baseweb="select"] svg {{ fill: var(--ps-muted) !important; color: var(--ps-muted) !important; }}
[data-baseweb="tag"] {{ background: var(--ps-primary) !important; }}
[data-baseweb="tag"] * {{ color: #fff !important; }}
[data-baseweb="popover"] ul[role="listbox"], [data-baseweb="popover"] [data-baseweb="menu"], [data-baseweb="popover"] [role="listbox"] {{
  background: var(--ps-surface-solid) !important; border: 1px solid var(--ps-line) !important; }}
[data-baseweb="popover"] li[role="option"], [data-baseweb="popover"] li[role="option"] * {{ color: var(--ps-ink) !important; background: transparent; }}
[data-baseweb="popover"] li[role="option"]:hover, [data-baseweb="popover"] li[role="option"][aria-selected="true"] {{ background: var(--ps-primary-soft) !important; }}
[data-testid="stCheckbox"] label *, [data-testid="stToggle"] label *, [data-testid="stRadio"] label * {{ color: var(--ps-ink) !important; }}
[data-testid="stButtonGroup"] button {{ background: var(--ps-field) !important; color: var(--ps-ink) !important; border-color: var(--ps-line) !important; }}
[data-testid="stButtonGroup"] button[kind*="Active"], [data-testid="stButtonGroup"] button[aria-checked="true"] {{ background: var(--ps-primary-soft) !important; color: var(--ps-primary) !important; border-color: var(--ps-primary) !important; }}
[data-testid="stPopoverBody"] button[kind="secondary"], [data-testid="stBaseButton-secondary"] {{ background: var(--ps-surface-solid) !important; color: var(--ps-ink) !important; border-color: var(--ps-line) !important; }}
[data-testid="stFileUploaderDropzone"] {{ background: var(--ps-field) !important; border-color: var(--ps-line) !important; }}
[data-testid="stFileUploaderDropzone"] * {{ color: var(--ps-muted) !important; }}
[data-testid="stFileUploaderDropzone"] button, [data-testid="stFileUploaderDropzone"] button * {{ color: var(--ps-ink) !important; }}
[data-testid="stPopoverButton"], [data-testid="stPopoverButton"] * {{ color: var(--ps-ink) !important; }}
[data-testid="stToggle"] label[data-baseweb="checkbox"] > div:first-child {{ box-shadow: inset 0 0 0 1px var(--ps-line-strong); }}

/* ---------- carregamento: anel tecnológico (spinners e execuções demoradas do site) ---------- */
@keyframes ps-gira-anel {{ to {{ transform: rotate(360deg); }} }}
@keyframes ps-gira-volta {{ to {{ transform: rotate(-360deg); }} }}
@keyframes ps-aparece {{ from {{ opacity: 0; scale: .85; }} to {{ opacity: 1; scale: 1; }} }}
@keyframes ps-pulso-nucleo {{ 0%, 100% {{ transform: scale(.7); opacity: .65; }} 50% {{ transform: scale(1); opacity: 1; }} }}
[data-testid="stSpinnerIcon"] {{ display: none !important; }}
[data-testid="stSpinner"] {{ display: flex; align-items: center; gap: 12px; }}
[data-testid="stSpinner"]::before {{
  content: ""; width: 26px; height: 26px; border-radius: 50%; flex: none;
  background: conic-gradient(from 0deg, transparent 0 25%, var(--ps-primary) 60%, var(--ps-up) 100%);
  -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 3.5px), #000 calc(100% - 3px));
          mask: radial-gradient(farthest-side, transparent calc(100% - 3.5px), #000 calc(100% - 3px));
  animation: ps-gira-anel .8s linear infinite; filter: drop-shadow(0 0 6px color-mix(in srgb, var(--ps-primary) 55%, transparent));
}}
/* execução que passa de ~0,7 s (troca de página, leitura de base): anel duplo no centro da tela */
.stApp[data-test-script-state="running"]::before, .stApp[data-test-script-state="running"]::after {{
  content: ""; position: fixed; left: 50%; top: 50%; translate: -50% -50%; z-index: 1000050; pointer-events: none; border-radius: 50%;
  opacity: 0; animation: ps-aparece .35s cubic-bezier(.2,.8,.2,1) .7s forwards;
}}
.stApp[data-test-script-state="running"]::before {{
  width: 76px; height: 76px;
  background: conic-gradient(from 0deg, transparent 0 20%, var(--ps-primary) 55%, var(--ps-up) 80%, #7A3FD1 100%);
  -webkit-mask: radial-gradient(farthest-side, transparent calc(100% - 5px), #000 calc(100% - 4.5px));
          mask: radial-gradient(farthest-side, transparent calc(100% - 5px), #000 calc(100% - 4.5px));
  filter: drop-shadow(0 0 14px color-mix(in srgb, var(--ps-primary) 60%, transparent));
}}
.stApp[data-test-script-state="running"]::after {{
  width: 50px; height: 50px; border: 2px dashed color-mix(in srgb, var(--ps-up) 70%, transparent);
  background: radial-gradient(circle, var(--ps-primary) 0 5px, color-mix(in srgb, var(--ps-primary) 25%, transparent) 6px 9px, transparent 10px),
              color-mix(in srgb, var(--ps-surface-solid) 70%, transparent);
  box-shadow: 0 0 0 14px color-mix(in srgb, var(--ps-surface-solid) 55%, transparent), 0 18px 50px -18px rgba(15,23,42,.5);
  backdrop-filter: blur(6px);
}}
.stApp[data-test-script-state="running"]::before {{ animation: ps-aparece .35s cubic-bezier(.2,.8,.2,1) .7s forwards, ps-gira-anel-c 1s linear infinite; }}
.stApp[data-test-script-state="running"]::after {{ animation: ps-aparece .35s cubic-bezier(.2,.8,.2,1) .7s forwards, ps-gira-volta-c 2.6s linear infinite; }}
@keyframes ps-gira-anel-c {{ from {{ rotate: 0deg; }} to {{ rotate: 360deg; }} }}
@keyframes ps-gira-volta-c {{ from {{ rotate: 0deg; }} to {{ rotate: -360deg; }} }}

/* ---------- toques modernos e leves ---------- */
[data-testid="stMainBlockContainer"] > div {{ animation: ps-entra .35s ease-out; }}
@keyframes ps-entra {{ from {{ opacity: 0; }} to {{ opacity: 1; }} }}   /* só opacidade: transform quebraria os botões fixos do topo */
::selection {{ background: var(--ps-primary-soft); color: var(--ps-primary); }}
* {{ scrollbar-width: thin; scrollbar-color: color-mix(in srgb, var(--ps-ink) 22%, transparent) transparent; }}
::-webkit-scrollbar {{ width: 9px; height: 9px; }}
::-webkit-scrollbar-thumb {{ background: color-mix(in srgb, var(--ps-ink) 20%, transparent); border-radius: 9px; border: 2px solid transparent; background-clip: padding-box; }}
::-webkit-scrollbar-thumb:hover {{ background-color: color-mix(in srgb, var(--ps-primary) 55%, transparent); }}
@media (prefers-reduced-motion: reduce) {{ *:not(.stApp), *:not(.stApp)::before {{ animation: none !important; transition: none !important; }} }}


header[data-testid="stHeader"] {{
  background: color-mix(in srgb, var(--ps-canvas) 62%, transparent);
  backdrop-filter: var(--ps-glass); -webkit-backdrop-filter: var(--ps-glass);
  border-bottom: 1px solid var(--ps-line);
}}

/* ---------- vidro: containers com key psc_*, expanders, popovers ---------- */
[class*="st-key-psc_"], [data-testid="stExpander"] details, [data-testid="stPopoverBody"] {{
  background: var(--ps-surface) !important;
  backdrop-filter: var(--ps-glass); -webkit-backdrop-filter: var(--ps-glass);
  border: 1px solid var(--ps-line) !important; border-radius: 16px !important;
  box-shadow: var(--ps-shadow);
  transition: border-color .2s ease, box-shadow .2s ease;
}}
[class*="st-key-psc_"]:hover {{ border-color: var(--ps-line-strong) !important; }}
[data-testid="stExpander"] summary:hover {{ color: var(--ps-primary); }}

/* campos */
[data-baseweb="select"] > div, [data-baseweb="input"], [data-baseweb="textarea"], [data-baseweb="base-input"] {{
  background-color: color-mix(in srgb, var(--ps-field) 72%, transparent) !important;
  border-color: var(--ps-line) !important;
}}
[data-baseweb="select"] > div:focus-within, [data-baseweb="input"]:focus-within, [data-baseweb="textarea"]:focus-within {{
  border-color: var(--ps-primary) !important; box-shadow: 0 0 0 3px var(--ps-primary-soft) !important;
}}
[data-baseweb="tag"] {{ background: var(--ps-primary-soft) !important; color: var(--ps-ink) !important; border: 1px solid color-mix(in srgb, var(--ps-primary) 40%, transparent) !important; }}
[data-baseweb="tag"] span {{ color: var(--ps-ink) !important; }}

/* botões: vidro translúcido, brilho que atravessa no hover */
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"],
[data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondaryFormSubmit"] {{
  position: relative; overflow: hidden; isolation: isolate; min-height: 40px; font-weight: 550 !important;
  transition: transform .18s cubic-bezier(.2,.7,.2,1), box-shadow .22s ease, border-color .2s ease, color .2s ease !important;
}}
[data-testid="stBaseButton-primary"]::after, [data-testid="stBaseButton-primaryFormSubmit"]::after,
[data-testid="stBaseButton-secondary"]::after, [data-testid="stBaseButton-secondaryFormSubmit"]::after {{
  content: ""; position: absolute; inset: 0; z-index: -1; pointer-events: none;
  background: linear-gradient(105deg, transparent 35%, rgba(255,255,255,.38) 50%, transparent 65%);
  transform: translateX(-130%); transition: transform .7s cubic-bezier(.2,.7,.2,1);
}}
[data-testid^="stBaseButton-"]:hover::after {{ transform: translateX(130%); }}
[data-testid^="stBaseButton-"]:active {{ transform: translateY(0) scale(.98) !important; }}
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {{
  background: linear-gradient(180deg, color-mix(in srgb, var(--ps-primary-hover) 92%, transparent), color-mix(in srgb, var(--ps-primary) 92%, transparent)) !important;
  border: 1px solid color-mix(in srgb, var(--ps-primary) 70%, #fff) !important; color: #fff !important;
  backdrop-filter: blur(10px) saturate(160%); -webkit-backdrop-filter: blur(10px) saturate(160%);
  box-shadow: 0 1px 0 rgba(255,255,255,.3) inset, 0 10px 24px -12px var(--ps-primary);
}}
[data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover {{
  transform: translateY(-1px); box-shadow: 0 1px 0 rgba(255,255,255,.3) inset, 0 16px 32px -12px var(--ps-primary);
}}
[data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondaryFormSubmit"] {{
  background: color-mix(in srgb, var(--ps-surface-solid) 58%, transparent) !important; border: 1px solid var(--ps-line) !important;
  backdrop-filter: blur(10px) saturate(160%); -webkit-backdrop-filter: blur(10px) saturate(160%);
  box-shadow: 0 1px 0 var(--ps-highlight) inset, 0 6px 16px -12px rgba(15,23,42,.35);
}}
[data-testid="stBaseButton-secondary"]:hover, [data-testid="stBaseButton-secondaryFormSubmit"]:hover {{
  transform: translateY(-1px); border-color: color-mix(in srgb, var(--ps-primary) 55%, transparent) !important; color: var(--ps-primary) !important;
  box-shadow: 0 1px 0 var(--ps-highlight) inset, 0 12px 26px -14px var(--ps-primary);
}}
[data-testid="stPageLink-NavLink"] {{ border-radius: 10px; transition: background-color .2s ease, transform .18s ease; }}
[data-testid="stPageLink-NavLink"]:hover {{ background: var(--ps-primary-soft); transform: translateX(2px); }}
.st-key-rel_acoes [data-testid^="stBaseButton-"] {{ height: 40px; min-width: 136px; }}
.st-key-rel_acoes [data-testid^="stBaseButton-"] p {{ font-weight: 550; font-size: 14px; }}
[data-testid="stBaseButton-primary"]:disabled {{ opacity: .4; box-shadow: none; transform: none; filter: saturate(.6); }}
:focus-visible {{ outline: 2px solid var(--ps-primary) !important; outline-offset: 2px; }}
[data-testid="stTabs"] [data-baseweb="tab-list"] {{ gap: 4px; }}
[data-testid="stDataFrame"] {{ border-radius: 12px; overflow: hidden; }}

.st-key-pb_texto textarea {{ font-family: var(--ps-mono); font-size: .9rem; tab-size: 8; -moz-tab-size: 8; line-height: 1.6; }}

/* ---------- títulos ---------- */
.ps-head h1 {{
  font-family: var(--ps-font); font-weight: 600; font-size: clamp(2rem, 1.3rem + 2vw, 2.9rem);
  letter-spacing: -.04em; line-height: 1.04; margin: 0; padding: 0; color: var(--ps-ink);
}}
.ps-head p {{ color: var(--ps-muted); margin: .5rem 0 0; font-size: 1rem; max-width: 72ch; line-height: 1.5; }}
.ps-sec {{ margin: 1.9rem 0 .7rem; display: flex; align-items: baseline; gap: 12px; flex-wrap: wrap; }}
[class*="st-key-psc_"] .ps-sec {{ margin-top: .1rem; }}
.ps-sec h2 {{ font-family: var(--ps-font); font-weight: 600; font-size: 1.12rem; letter-spacing: -.02em; margin: 0; padding: 0; color: var(--ps-ink); }}
.ps-sec p {{ color: var(--ps-muted); margin: 0; font-size: .9rem; }}

/* ---------- cotação (indicador com sparkline) ---------- */
.ps-tags {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 12px; }}
.ps-q {{
  --tone: var(--ps-ink);
  position: relative; overflow: hidden; border-radius: 16px; padding: 16px 18px 14px;
  background: var(--ps-surface); border: 1px solid var(--ps-line); box-shadow: var(--ps-shadow);
  backdrop-filter: var(--ps-glass); -webkit-backdrop-filter: var(--ps-glass);
  display: flex; flex-direction: column; gap: 6px; min-height: 120px; transition: border-color .2s, transform .2s;
}}
.ps-q:hover {{ border-color: var(--ps-line-strong); transform: translateY(-1px); }}
.ps-q::before {{ content: ""; position: absolute; inset: 0 0 auto 0; height: 1px;
  background: linear-gradient(90deg, transparent, var(--tone), transparent); opacity: .7; }}
.ps-q.t-primary {{ --tone: var(--ps-primary); }} .ps-q.t-promo {{ --tone: var(--ps-amber); }}
.ps-q.t-alert {{ --tone: var(--ps-down); }} .ps-q.t-ok {{ --tone: var(--ps-up); }} .ps-q.t-neutro {{ --tone: var(--ps-faint); }}
.ps-q-top {{ display: flex; justify-content: space-between; align-items: center; gap: 8px; }}
.ps-q-l {{ font-size: .82rem; font-weight: 500; color: var(--ps-muted); line-height: 1.25; }}
.ps-q-v {{ font-family: var(--ps-mono); font-weight: 500; font-size: 1.85rem; letter-spacing: -.03em; color: var(--ps-ink);
  font-variant-numeric: tabular-nums; line-height: 1.1; white-space: nowrap; }}
.ps-q-v small {{ font-size: .5em; color: var(--ps-muted); margin-right: .25em; font-weight: 400; letter-spacing: 0; }}
.ps-q-n {{ font-size: .78rem; color: var(--ps-faint); line-height: 1.35; }}
.ps-q-n b {{ color: var(--ps-muted); font-weight: 500; }}
.ps-q .ps-spark {{ display: block; width: 100%; height: 34px; margin-top: auto; }}
.ps-d {{ font-family: var(--ps-mono); font-size: .74rem; font-weight: 500; padding: 2px 7px; border-radius: 999px; white-space: nowrap; }}
.ps-d.up {{ color: var(--ps-up); background: var(--ps-up-soft); }} .ps-d.down {{ color: var(--ps-down); background: var(--ps-down-soft); }}
.ps-d.flat {{ color: var(--ps-muted); background: var(--ps-raised); }}

/* ---------- barra de validação ---------- */
.ps-split {{ background: var(--ps-surface); border: 1px solid var(--ps-line); border-radius: 16px; padding: 14px 18px;
  box-shadow: var(--ps-shadow); backdrop-filter: var(--ps-glass); -webkit-backdrop-filter: var(--ps-glass); }}
.ps-split-bar {{ display: flex; height: 6px; border-radius: 6px; overflow: hidden; background: var(--ps-raised); gap: 3px; }}
.ps-split-bar span {{ display: block; border-radius: 6px; }}
.ps-split-bar .ok {{ background: var(--ps-up); box-shadow: 0 0 12px var(--ps-up); }}
.ps-split-bar .alert {{ background: var(--ps-down); box-shadow: 0 0 12px var(--ps-down); }}
.ps-split-legend {{ display: flex; gap: 20px; margin-top: 10px; font-size: .84rem; color: var(--ps-muted); flex-wrap: wrap; }}
.ps-split-legend i {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 7px; }}
.ps-split-legend b {{ color: var(--ps-ink); font-family: var(--ps-mono); font-weight: 500; }}

/* ---------- fita de cotações ---------- */
.ps-ticker {{ position: relative; overflow: hidden; border-radius: 14px; border: 1px solid var(--ps-line);
  background: var(--ps-surface); backdrop-filter: var(--ps-glass); -webkit-backdrop-filter: var(--ps-glass);
  mask-image: linear-gradient(90deg, transparent, #000 6%, #000 94%, transparent); -webkit-mask-image: linear-gradient(90deg, transparent, #000 6%, #000 94%, transparent); }}
.ps-ticker-track {{ display: inline-flex; white-space: nowrap; padding: 11px 0; animation: ps-ticker var(--dur) linear infinite; }}
.ps-ticker:hover .ps-ticker-track {{ animation-play-state: paused; }}
.ps-ticker-item {{ display: inline-flex; align-items: baseline; gap: 9px; padding: 0 24px; border-right: 1px solid var(--ps-line); font-size: .86rem; }}
.ps-ticker-item b {{ font-weight: 600; letter-spacing: .01em; color: var(--ps-ink); }}
.ps-ticker-item .v {{ font-family: var(--ps-mono); color: var(--ps-ink); }}
.ps-ticker-item .a {{ font-family: var(--ps-mono); color: var(--ps-muted); }}
.ps-ticker-item small {{ color: var(--ps-faint); font-size: .74rem; }}
.ps-ticker-item .up {{ color: var(--ps-up); font-family: var(--ps-mono); font-size: .78rem; }}
.ps-ticker-item .down {{ color: var(--ps-down); font-family: var(--ps-mono); font-size: .78rem; }}
@keyframes ps-ticker {{ from {{ transform: translateX(0); }} to {{ transform: translateX(-50%); }} }}
@media (prefers-reduced-motion: reduce) {{ .ps-ticker {{ overflow-x: auto; }} .ps-ticker-track {{ animation: none; }} }}

/* ---------- barras horizontais (ranking) ---------- */
.ps-rank {{ display: flex; flex-direction: column; gap: 10px; }}
.ps-rank-row {{ display: grid; grid-template-columns: minmax(90px, 1fr) 2fr auto; gap: 10px; align-items: center; font-size: .85rem; }}
.ps-rank-row span {{ color: var(--ps-ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.ps-rank-row .bar {{ height: 6px; border-radius: 6px; background: var(--ps-raised); overflow: hidden; }}
.ps-rank-row .bar i {{ display: block; height: 100%; border-radius: 6px; background: linear-gradient(90deg, color-mix(in srgb, var(--ps-primary) 50%, transparent), var(--ps-primary)); }}
.ps-rank-row b {{ font-family: var(--ps-mono); font-weight: 500; color: var(--ps-ink); }}
.ps-rank-row em {{ font-style: normal; font-family: var(--ps-mono); font-size: .74rem; margin-left: 8px; }}

/* ---------- linha do tempo de campanhas ---------- */
.ps-gantt {{ position: relative; }}
.ps-gantt-axis {{ display: flex; justify-content: space-between; font-family: var(--ps-mono); font-size: .72rem; color: var(--ps-faint); margin: 0 0 8px 180px; }}
.ps-gantt-row {{ display: grid; grid-template-columns: 170px 1fr; gap: 10px; align-items: center; min-height: 34px; }}
.ps-gantt-row > span {{ font-size: .84rem; color: var(--ps-ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.ps-gantt-lane {{ position: relative; height: 26px; border-radius: 8px; background: repeating-linear-gradient(90deg, var(--ps-grid) 0 1px, transparent 1px 40px); }}
.ps-gantt-bar {{ position: absolute; top: 3px; bottom: 3px; border-radius: 6px; display: flex; align-items: center; padding: 0 8px;
  font-family: var(--ps-mono); font-size: .72rem; color: #fff; overflow: hidden; white-space: nowrap; min-width: 6px; }}
.ps-gantt-bar.ok {{ background: linear-gradient(90deg, color-mix(in srgb, var(--ps-up) 65%, transparent), var(--ps-up)); }}
.ps-gantt-bar.alert {{ background: linear-gradient(90deg, color-mix(in srgb, var(--ps-down) 65%, transparent), var(--ps-down)); box-shadow: 0 0 14px -2px var(--ps-down); }}
.ps-gantt-hoje {{ position: absolute; top: -4px; bottom: -4px; width: 1px; background: var(--ps-amber); }}
@media (max-width: 760px) {{ .ps-gantt-row {{ grid-template-columns: 100px 1fr; }} .ps-gantt-axis {{ margin-left: 110px; }} }}

/* ---------- tabela compacta (prévia do arredondamento) ---------- */
.ps-mini {{ width: 100%; border-collapse: collapse; font-size: .86rem; }}
.ps-mini th {{ text-align: left; font-weight: 500; color: var(--ps-faint); padding: 6px 10px; border-bottom: 1px solid var(--ps-line); }}
.ps-mini td {{ padding: 7px 10px; border-bottom: 1px solid var(--ps-line); font-family: var(--ps-mono); color: var(--ps-ink); }}
.ps-mini td.de {{ color: var(--ps-faint); text-decoration: line-through; }}
.ps-mini tr:last-child td {{ border-bottom: none; }}

/* ---------- estados vazios e chips ---------- */
.ps-empty {{ border: 1px dashed var(--ps-line-strong); border-radius: 16px; padding: 30px 28px;
  background: color-mix(in srgb, var(--ps-surface) 70%, transparent); backdrop-filter: var(--ps-glass); }}
.ps-empty h3 {{ font-family: var(--ps-font); font-size: 1.05rem; font-weight: 600; margin: 0 0 .35rem; padding: 0; color: var(--ps-ink); letter-spacing: -.01em; }}
.ps-empty p {{ margin: 0; color: var(--ps-muted); max-width: 64ch; line-height: 1.5; }}
.ps-chip {{ display: inline-flex; align-items: center; gap: 6px; font-size: .76rem; font-weight: 500; padding: 3px 10px; border-radius: 999px;
  background: var(--ps-raised); color: var(--ps-ink); border: 1px solid var(--ps-line); white-space: nowrap; }}
.ps-chip i {{ width: 6px; height: 6px; border-radius: 50%; display: inline-block; }}
.ps-chip.promo {{ background: var(--ps-amber-soft); color: var(--ps-amber); border-color: transparent; }}

/* ---------- início ---------- */
.ps-tool {{ display: flex; flex-direction: column; gap: 10px; }}
.ps-tool .ic {{ width: 40px; height: 40px; border-radius: 12px; display: grid; place-items: center; font-size: 22px; color: #fff;
  background: linear-gradient(135deg, var(--ps-primary), color-mix(in srgb, var(--ps-primary) 40%, var(--ps-up)));
  box-shadow: 0 8px 22px -10px var(--ps-primary); }}
.ps-tool h3 {{ font-family: var(--ps-font); font-weight: 600; font-size: 1.05rem; margin: 0; padding: 0; color: var(--ps-ink); letter-spacing: -.02em; }}
.ps-tool p {{ color: var(--ps-muted); font-size: .9rem; line-height: 1.45; margin: 0; min-height: 4em; }}
.ps-head .ps-clock {{ font-family: var(--ps-mono); color: var(--ps-muted); font-size: .86rem; display: flex; align-items: center; gap: 9px; }}
.ps-tool .ms {{ font-family: 'Material Symbols Rounded'; font-size: 22px; line-height: 1; font-weight: 300; }}
.ps-live {{ width: 7px; height: 7px; border-radius: 50%; background: var(--ps-up); box-shadow: 0 0 0 0 var(--ps-up); animation: ps-pulse 2s infinite; }}
@keyframes ps-pulse {{ 0% {{ box-shadow: 0 0 0 0 color-mix(in srgb, var(--ps-up) 60%, transparent); }} 100% {{ box-shadow: 0 0 0 10px transparent; }} }}

/* ---------- relatórios ---------- */
.ps-rep-cat {{ display: flex; align-items: center; gap: 8px; font-size: .8rem; font-weight: 500; color: var(--ps-muted); margin-bottom: .5rem; }}
.ps-rep-cat i {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; }}
.ps-rep-meta {{ display: flex; flex-wrap: wrap; gap: 6px 14px; margin-top: .6rem; font-size: .78rem; color: var(--ps-faint); }}
.ps-rep-meta span {{ display: inline-flex; align-items: center; gap: 4px; }}
.ps-rep-tags {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: .6rem; }}
.ps-viewer-head h2 {{ font-family: var(--ps-font); font-weight: 600; letter-spacing: -.035em; font-size: clamp(1.5rem, 1rem + 1.4vw, 2.2rem);
  line-height: 1.1; margin: 0; padding: 0; color: var(--ps-ink); }}
.ps-viewer-head p {{ color: var(--ps-muted); margin: .45rem 0 0; max-width: 80ch; }}
.ps-list-row {{ display: grid; grid-template-columns: 10px 1fr; gap: 12px; align-items: center; padding: 6px 2px; }}
.ps-list-row i {{ width: 8px; height: 8px; border-radius: 50%; }}
.ps-list-row b {{ font-weight: 550; color: var(--ps-ink); }}
.ps-list-row span {{ color: var(--ps-faint); font-size: .82rem; }}
.ps-rel-linha {{ display: grid; grid-template-columns: 8px 1fr; gap: 12px; align-items: start; }}
.ps-rel-linha > i {{ width: 8px; height: 8px; border-radius: 50%; margin-top: .48rem; }}
.ps-rel-linha b {{ font-weight: 550; color: var(--ps-ink); font-size: .96rem; }}
.ps-rel-linha span {{ display: block; color: var(--ps-faint); font-size: .8rem; }}
.ps-rel-linha .ps-chip {{ display: inline-flex; margin-left: 6px; vertical-align: 1px; }}
.ps-rel-linha p {{ color: var(--ps-muted); font-size: .87rem; margin: .15rem 0 0; max-width: 90ch;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }}
.ps-rel-linha .ps-rep-meta {{ margin-top: .35rem; }}
.ps-rel-linha .ps-rep-meta span {{ display: inline-flex; }}
.ps-rel-linha .ps-rep-tags {{ margin-top: .45rem; }}
.ps-rel-sep {{ border-top: 1px solid var(--ps-line); margin: .1rem 0; }}
[class*="st-key-fav1_"] button, [class*="st-key-fav1_"] button * {{ color: var(--ps-amber) !important; }}
[class*="st-key-fav1_"] [data-testid="stIconMaterial"] {{ font-variation-settings: 'FILL' 1; }}
.ps-foco-titulo {{ font-weight: 600; font-size: 1rem; color: var(--ps-ink); letter-spacing: -.01em; }}
.ps-user {{ display: flex; gap: 14px; align-items: center; }}
.ps-user b {{ display: block; color: var(--ps-ink); font-size: 1.05rem; }}
.ps-user span {{ color: var(--ps-muted); font-size: .86rem; }}
.ps-avatar {{ width: 52px; height: 52px; border-radius: 50%; object-fit: cover; display: grid; place-items: center;
  background: linear-gradient(135deg, var(--ps-primary), var(--ps-up)); color: #fff; font-weight: 600; font-size: 1.2rem; }}

/* ---------- login ---------- */
.ps-login-brand {{ display: flex; align-items: center; gap: 10px; margin-bottom: 2.2rem; }}
.ps-login-brand img {{ width: 34px; height: 34px; }}
.ps-login-brand span {{ font-weight: 600; font-size: 1.35rem; letter-spacing: -.03em; color: var(--ps-ink); }}
.ps-login-h1 {{ font-family: var(--ps-font); font-weight: 600; font-size: clamp(2.2rem, 1.4rem + 2.6vw, 3.6rem); letter-spacing: -.045em;
  line-height: 1.02; margin: 0 0 1rem; padding: 0; color: var(--ps-ink); max-width: 15ch; }}
.ps-login-h1 em {{ font-style: normal; background: linear-gradient(90deg, var(--ps-primary), var(--ps-up)); -webkit-background-clip: text; background-clip: text; color: transparent; }}
.ps-login-p {{ color: var(--ps-muted); font-size: 1.05rem; line-height: 1.55; max-width: 48ch; margin: 0; }}
.ps-login-pills {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 1.2rem; }}
.ps-login-pills span {{ display: inline-flex; align-items: center; gap: 8px; font-size: .8rem; color: var(--ps-muted); padding: 6px 12px;
  border-radius: 999px; border: 1px solid var(--ps-line); background: var(--ps-surface); backdrop-filter: var(--ps-glass); }}
.ps-login-pills i {{ width: 6px; height: 6px; border-radius: 50%; }}
.st-key-psc_login {{ padding: 26px 24px !important; }}
.st-key-psc_login [data-baseweb="input"] {{ border-color: var(--ps-line-strong) !important; }}
.st-key-psc_login h2 {{ font-family: var(--ps-font); font-weight: 600; font-size: 1.5rem; margin: 0 0 .25rem; padding: 0; letter-spacing: -.03em; color: var(--ps-ink); }}
.st-key-psc_login p.sub {{ color: var(--ps-muted); margin: 0 0 1rem; }}
"""


def cor_categoria(nome: str) -> str:
    paleta = (["#7FA6FF", "#FF7A93", "#2BD99F", "#F5B547", "#B794FF", "#4CC9F0", "#FF8FC7", "#9AA5BD"] if modo() == "Dark"
              else ["#2D4BFF", "#E11D48", "#0E9F6E", "#C47A0A", "#7A3FD1", "#0B8DB0", "#C2367A", "#566176"])
    return paleta[sum(ord(c) for c in (nome or "")) % len(paleta)]


def plotly_layout(altura: int = 320) -> dict:
    t = tokens()
    return dict(height=altura, margin=dict(l=8, r=8, t=16, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family=f"{FONTE}, sans-serif", color=t["muted"], size=12), separators=",.")
