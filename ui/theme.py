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
    # Modo escuro: terminal de inteligência de mercado, espaço profundo com neon ciano e violeta
    "Dark": {
        "canvas": "#02040D", "canvas2": "#060B22", "field": "#081230",
        "surface": "rgba(8,18,46,.58)", "surface_solid": "#071030", "raised": "rgba(0,229,255,.05)",
        "ink": "#E4F6FF", "muted": "#8AB0C8", "faint": "#4E6A88",
        "line": "rgba(0,229,255,.13)", "line_strong": "rgba(0,229,255,.30)", "line_hex": "#123058",
        "primary": "#00E5FF", "primary_hover": "#7AF3FF", "primary_soft": "rgba(0,229,255,.13)",
        "up": "#3DFFA8", "up_soft": "rgba(61,255,168,.12)", "down": "#FF4D9A", "down_soft": "rgba(255,77,154,.13)",
        "amber": "#FFC24D", "amber_soft": "rgba(255,194,77,.14)",
        "glow1": "rgba(0,229,255,.20)", "glow2": "rgba(155,92,255,.22)", "grid": "rgba(0,229,255,.055)",
        "highlight": "rgba(0,229,255,.08)",
        "shadow": "0 0 0 1px rgba(0,229,255,.06) inset, 0 22px 50px -26px rgba(0,229,255,.35)",
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
    # Modo Optimus (estrela): preto absoluto, fibra de carbono e neon azul e vermelho
    "Optimus": {
        "canvas": "#030305", "canvas2": "#08090E", "field": "#0C0E15",
        "surface": "rgba(12,14,22,.66)", "surface_solid": "#0B0D14", "raised": "rgba(255,255,255,.04)",
        "ink": "#F3F6FB", "muted": "#9BA4B6", "faint": "#5C6476",
        "line": "rgba(46,120,255,.17)", "line_strong": "rgba(46,120,255,.36)", "line_hex": "#1A2234",
        "primary": "#2F7BFF", "primary_hover": "#6AA3FF", "primary_soft": "rgba(47,123,255,.16)",
        "up": "#29C5FF", "up_soft": "rgba(41,197,255,.14)", "down": "#FF2D55", "down_soft": "rgba(255,45,85,.15)",
        "amber": "#FFB020", "amber_soft": "rgba(255,176,32,.15)",
        "glow1": "rgba(47,123,255,.26)", "glow2": "rgba(255,45,85,.20)", "grid": "rgba(255,255,255,.03)",
        "highlight": "rgba(255,255,255,.06)",
        "shadow": "0 0 0 1px rgba(47,123,255,.08) inset, 0 24px 54px -26px rgba(47,123,255,.45)",
    },
}
# apelidos usados pelas telas
for _t in TOKENS.values():
    _t.update(alert=_t["down"], alert_soft=_t["down_soft"], ok=_t["up"], ok_soft=_t["up_soft"],
              tag=_t["amber"], tag_ink="#0B1220", warn_soft=_t["amber_soft"],
              varejo=_t["primary"], atacado=_t["down"], pdv=_t["amber"])


MODOS = ["Light", "Dark", "Optimus"]          # sol, lua e estrela (o botão do topo passa de um para o outro)


def modo() -> str:
    m = st.session_state.get("tema")
    if m in ("Quantum", "Prisma"):           # nomes antigos: Quantum virou o escuro; Prisma deu lugar ao Optimus
        m = st.session_state["tema"] = "Dark" if m == "Quantum" else "Optimus"
    return m if m in TOKENS else "Light"


def escuro() -> bool:
    """Fundo escuro (lua ou estrela Optimus): logos, gráficos e o tema nativo do Streamlit seguem o escuro."""
    return modo() in ("Dark", "Optimus")


def proximo_modo() -> str:
    return MODOS[(MODOS.index(modo()) + 1) % len(MODOS)]


def extra_componente() -> str:
    """Efeitos do modo Quantum dentro das telas HTML (Início, PriceMetrics, Promo, PriceBot, Pesquisa).
    As telas recebem as cores como variáveis em :root{...}; aqui fechamos esse bloco, acrescentamos as regras e reabrimos."""
    if modo() == "Optimus":
        return ("}"
                "body{background:radial-gradient(900px 480px at 0% -10%,rgba(47,123,255,.16),transparent 60%),radial-gradient(900px 480px at 100% -10%,rgba(255,45,85,.13),transparent 60%),repeating-linear-gradient(45deg,rgba(255,255,255,.012) 0 2px,transparent 2px 6px) !important}"
                ".glass,.kc,.card,.pop,.mcard{border-color:rgba(47,123,255,.22) !important;box-shadow:0 0 0 1px rgba(47,123,255,.06) inset,0 -1px 0 rgba(255,45,85,.25) inset,0 0 30px -14px rgba(47,123,255,.55) !important}"
                ".kc b{text-shadow:0 0 12px rgba(47,123,255,.45)}"
                ".chip.on,.seg .on,button.pri{background:linear-gradient(120deg,#2F7BFF,#FF2D55) !important;color:#fff !important;border-color:transparent !important;box-shadow:0 0 18px -6px rgba(47,123,255,.8)}"
                ".row.sel{background:linear-gradient(90deg,rgba(47,123,255,.16),rgba(255,45,85,.08)) !important;box-shadow:inset 3px 0 0 #2F7BFF}"
                ".row:hover{background:rgba(47,123,255,.06)}"
                "::selection{background:rgba(255,45,85,.35)}"
                ":root{")
    if modo() == "Light":
        return ("}"
                ".glass,.kc,.card,.pop,.mcard{border-color:rgba(45,75,255,.20) !important;box-shadow:0 0 0 1px rgba(45,75,255,.04) inset,0 -1px 0 rgba(14,159,110,.22) inset,0 0 26px -16px rgba(45,75,255,.55) !important}"
                ".chip.on,.seg .on,button.pri{box-shadow:0 0 16px -6px rgba(45,75,255,.75)}"
                ".row.sel{box-shadow:inset 3px 0 0 #2D4BFF}"
                ":root{")
    if modo() != "Dark":
        return ""
    return ("}"
            "body{background:radial-gradient(900px 500px at 85% -10%,rgba(0,229,255,.10),transparent 60%),radial-gradient(800px 500px at -10% 30%,rgba(155,92,255,.12),transparent 60%) !important}"
            ".glass,.kc,.card,.pop,.mcard{border-color:rgba(0,229,255,.18) !important;box-shadow:0 0 0 1px rgba(0,229,255,.05) inset,0 -1px 0 rgba(155,92,255,.35) inset,0 0 28px -14px rgba(0,229,255,.5) !important}"
            ".kc b,.big,.num b{text-shadow:0 0 12px rgba(0,229,255,.35)}"
            ".chip.on,.seg .on,button.pri{background:linear-gradient(135deg,#00E5FF,#9B5CFF) !important;color:#02040D !important;border-color:transparent !important}"
            ".row.sel{background:linear-gradient(90deg,rgba(0,229,255,.12),rgba(155,92,255,.06)) !important;box-shadow:inset 3px 0 0 #00E5FF}"
            ".hd,.thead,.cab{background:linear-gradient(180deg,rgba(0,229,255,.06),transparent) !important}"
            "::selection{background:rgba(0,229,255,.35)}"
            ":root{")


def tokens() -> dict:
    return TOKENS[modo()]


def _tema_nativo(t: dict) -> None:
    opcoes = {
        "theme.base": "dark" if escuro() else "light",
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


def _css_neon(c1: str, c2: str, claro: bool) -> str:
    """Toque de neon do Optimus nos modos claro e escuro, cada um com as suas cores (c1 e c2 em "r,g,b"):
    fios de luz nas laterais, barra de luz correndo no topo, brilho no menu, nos botões do canto, nos cartões e nos botões principais."""
    forte, leve = (".55", ".22") if claro else (".75", ".32")
    return f"""
/* ---------- toque neon ({'claro' if claro else 'escuro'}) ---------- */
[data-testid="stAppViewContainer"]::before, [data-testid="stAppViewContainer"]::after {{ content: ""; position: fixed; top: 0; bottom: 0; width: 2px; pointer-events: none; z-index: 2; }}
[data-testid="stAppViewContainer"]::before {{ left: 0; background: linear-gradient(180deg, transparent, rgb({c1}) 30%, rgb({c1}) 70%, transparent);
  box-shadow: 0 0 16px 3px rgba({c1},{forte}), 0 0 50px 8px rgba({c1},{leve}); animation: psn-pulso 3.6s ease-in-out infinite; }}
[data-testid="stAppViewContainer"]::after {{ right: 0; background: linear-gradient(180deg, transparent, rgb({c2}) 30%, rgb({c2}) 70%, transparent);
  box-shadow: 0 0 16px 3px rgba({c2},{forte}), 0 0 50px 8px rgba({c2},{leve}); animation: psn-pulso 3.6s ease-in-out infinite 1.8s; }}
@keyframes psn-pulso {{ 0%, 100% {{ opacity: {'.35' if claro else '.45'}; }} 50% {{ opacity: 1; }} }}
header[data-testid="stHeader"]::after {{ content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 2px;
  background: linear-gradient(90deg, rgb({c1}), rgb({c2}), rgb({c1})); background-size: 300% 100%;
  box-shadow: 0 0 12px rgba({c1},{forte}), 0 0 20px rgba({c2},{leve}); animation: psn-barra 7s linear infinite; }}
@keyframes psn-barra {{ to {{ background-position: 300% 0; }} }}
header [data-testid="stTopNav"], .st-key-ps_tema button, #ps-fs, .st-key-ps_sino [data-testid="stPopoverButton"] {{
  border-color: rgba({c1},.38) !important; box-shadow: 0 0 0 1px rgba({c1},.06) inset, 0 0 18px -6px rgba({c1},{forte}) !important; }}
[data-testid="stTopNavLink"][aria-current="page"] {{ box-shadow: 0 0 14px -4px rgba({c1},{forte}); }}
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {{
  box-shadow: 0 0 20px -6px rgba({c1},{forte}), 0 10px 24px -14px rgba({c2},{forte}) !important; }}
[data-testid="stPopoverBody"], [data-testid="stTopNavPopoverBody"], [class*="st-key-psc_"] {{
  box-shadow: 0 -2px 0 rgba({c2},{'.35' if claro else '.5'}) inset, 0 0 36px -18px rgba({c1},{forte}) !important; }}
.st-key-ps_chat [data-testid="stPopoverButton"] {{ box-shadow: 0 0 22px -4px rgba({c1},{forte}), 0 0 28px -10px rgba({c2},{forte}) !important; }}
"""


def _css_optimus() -> str:
    """Modo estrela (Optimus): preto absoluto com textura de fibra de carbono, luzes de neon azul e vermelho nas bordas da tela,
    uma barra de luz que corre de azul para vermelho no topo, títulos e botões em gradiente azul → vermelho."""
    return """
/* ================= MODO OPTIMUS (estrela): black com neon azul e vermelho ================= */
.stApp {
  background-color: #030305 !important;
  background-image:
    radial-gradient(1000px 560px at -8% -12%, rgba(47,123,255,.30), transparent 60%),
    radial-gradient(1000px 560px at 108% -12%, rgba(255,45,85,.24), transparent 60%),
    radial-gradient(900px 420px at 50% 115%, rgba(47,123,255,.12), transparent 60%),
    repeating-linear-gradient(45deg, rgba(255,255,255,.014) 0 2px, transparent 2px 6px),
    repeating-linear-gradient(-45deg, rgba(255,255,255,.010) 0 2px, transparent 2px 6px),
    linear-gradient(180deg, #08090E, #030305 680px) !important;
  background-attachment: fixed !important;
}
/* luzes laterais: azul à esquerda, vermelho à direita, pulsando devagar */
.stApp::before, .stApp::after { content: ""; position: fixed; top: 0; bottom: 0; width: 2px; pointer-events: none; z-index: 2; }
.stApp::before { left: 0; background: linear-gradient(180deg, transparent, #2F7BFF 30%, #2F7BFF 70%, transparent);
  box-shadow: 0 0 18px 4px rgba(47,123,255,.55), 0 0 60px 10px rgba(47,123,255,.25); animation: pso-pulso 3.2s ease-in-out infinite; }
.stApp::after { right: 0; background: linear-gradient(180deg, transparent, #FF2D55 30%, #FF2D55 70%, transparent);
  box-shadow: 0 0 18px 4px rgba(255,45,85,.55), 0 0 60px 10px rgba(255,45,85,.22); animation: pso-pulso 3.2s ease-in-out infinite 1.6s; }
@keyframes pso-pulso { 0%, 100% { opacity: .45; } 50% { opacity: 1; } }
/* barra de luz no topo: corre de azul para vermelho */
header[data-testid="stHeader"] { background: rgba(3,3,5,.82) !important; border-bottom: 0 !important; }
header[data-testid="stHeader"]::after { content: ""; position: absolute; left: 0; right: 0; bottom: 0; height: 2px;
  background: linear-gradient(90deg, #2F7BFF, #8A5CFF, #FF2D55, #2F7BFF); background-size: 300% 100%;
  box-shadow: 0 0 14px rgba(47,123,255,.6), 0 0 22px rgba(255,45,85,.35); animation: pso-barra 6s linear infinite; }
@keyframes pso-barra { to { background-position: 300% 0; } }
/* ilha do menu e botões do topo */
header [data-testid="stTopNav"], .st-key-ps_tema button, #ps-fs, .st-key-ps_sino [data-testid="stPopoverButton"] {
  background: rgba(10,12,18,.85) !important; border: 1px solid rgba(47,123,255,.38) !important;
  box-shadow: 0 0 0 1px rgba(255,45,85,.10) inset, 0 0 20px -6px rgba(47,123,255,.65) !important; }
[data-testid="stTopNavLink"][aria-current="page"], [data-testid="stTopNavLink"]:hover {
  background: linear-gradient(120deg, rgba(47,123,255,.22), rgba(255,45,85,.16)) !important; box-shadow: 0 0 14px -4px rgba(47,123,255,.7); }
/* títulos: branco → azul → vermelho */
h1, h2, .ps-hero h1 b, .ps-cab h1 { background: linear-gradient(95deg, #FFFFFF 0%, #8FB8FF 40%, #2F7BFF 62%, #FF2D55 100%);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
/* botões principais: azul → vermelho com brilho */
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
  background: linear-gradient(120deg, #2F7BFF, #FF2D55) !important; color: #fff !important; border: 0 !important;
  box-shadow: 0 0 22px -6px rgba(47,123,255,.85), 0 10px 26px -12px rgba(255,45,85,.7) !important; }
[data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover { filter: brightness(1.12); }
[data-testid="stBaseButton-primary"] p, [data-testid="stBaseButton-primaryFormSubmit"] p { color: #fff !important; font-weight: 700; }
/* cartões, gavetas, janelas e menus: vidro preto com contorno azul e um fio vermelho embaixo */
[data-testid="stPopoverBody"], [data-testid="stTopNavPopoverBody"], [class*="st-key-psc_"], [data-testid="stExpander"] details {
  background: rgba(8,10,16,.94) !important; border: 1px solid rgba(47,123,255,.30) !important;
  box-shadow: 0 -2px 0 rgba(255,45,85,.55) inset, 0 0 40px -18px rgba(47,123,255,.6) !important; }
[data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within, [data-testid="stTextInputRootElement"]:focus-within {
  border-color: #2F7BFF !important; box-shadow: 0 0 0 3px rgba(47,123,255,.22), 0 0 16px -4px rgba(255,45,85,.5) !important; }
/* chat e notificações */
.st-key-ps_chat [data-testid="stPopoverButton"] { background: linear-gradient(135deg, #2F7BFF, #FF2D55) !important;
  box-shadow: 0 0 24px -4px rgba(47,123,255,.8), 0 0 30px -8px rgba(255,45,85,.6); }
.ps-msg.eu { background: linear-gradient(135deg, #2F7BFF, #C21E45) !important; }
.ps-pop { background: rgba(8,10,16,.95) !important; border-color: rgba(47,123,255,.4) !important; box-shadow: 0 0 30px -10px rgba(47,123,255,.6), 0 -2px 0 rgba(255,45,85,.6) inset !important; }
::selection { background: rgba(255,45,85,.35); }
"""


def _css_quantum() -> str:
    """Modo escuro: céu estrelado discreto, grade fina, brilho neon e títulos em gradiente."""
    return """
/* ================= MODO ESCURO: terminal de inteligência, neon ciano e violeta ================= */
.stApp {
  background-image:
    radial-gradient(1200px 700px at 88% -14%, rgba(0,229,255,.18), transparent 62%),
    radial-gradient(1000px 640px at -14% 22%, rgba(155,92,255,.20), transparent 60%),
    radial-gradient(700px 420px at 50% 120%, rgba(61,255,168,.07), transparent 60%),
    radial-gradient(1.2px 1.2px at 12% 18%, rgba(255,255,255,.75), transparent 60%),
    radial-gradient(1px 1px at 72% 12%, rgba(255,255,255,.6), transparent 60%),
    radial-gradient(1.4px 1.4px at 38% 66%, rgba(122,243,255,.8), transparent 60%),
    radial-gradient(1px 1px at 86% 54%, rgba(255,255,255,.55), transparent 60%),
    radial-gradient(1.2px 1.2px at 22% 84%, rgba(196,160,255,.75), transparent 60%),
    radial-gradient(1px 1px at 58% 36%, rgba(255,255,255,.5), transparent 60%),
    linear-gradient(rgba(0,229,255,.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,229,255,.05) 1px, transparent 1px),
    linear-gradient(180deg, #060B22, #02040D 720px) !important;
  background-size: auto, auto, auto, 100% 100%, 100% 100%, 100% 100%, 100% 100%, 100% 100%, 100% 100%, 44px 44px, 44px 44px, auto !important;
  background-attachment: fixed !important;
}
/* varredura de radar bem sutil atravessando a tela */
.stApp::before { content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
  background: linear-gradient(180deg, transparent 0%, rgba(0,229,255,.045) 50%, transparent 100%); background-size: 100% 260px;
  background-repeat: no-repeat; animation: psq-scan 9s linear infinite; }
@keyframes psq-scan { from { background-position: 0 -260px; } to { background-position: 0 calc(100vh / var(--ps-zoom, .9)); } }
/* estrelas piscando */
.stApp::after { content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0; opacity: .7;
  background-image: radial-gradient(1.6px 1.6px at 30% 22%, #7AF3FF, transparent 60%), radial-gradient(1.4px 1.4px at 64% 78%, #C4A0FF, transparent 60%),
    radial-gradient(1.2px 1.2px at 90% 30%, #fff, transparent 60%), radial-gradient(1.4px 1.4px at 8% 60%, #7AF3FF, transparent 60%);
  animation: psq-pisca 4.5s ease-in-out infinite alternate; }
@keyframes psq-pisca { from { opacity: .25; } to { opacity: .85; } }
/* ilha do menu e botões do topo com borda neon */
header [data-testid="stTopNav"], .st-key-ps_tema button, #ps-fs, .st-key-ps_sino [data-testid="stPopoverButton"] {
  border-color: rgba(0,229,255,.28) !important; box-shadow: 0 0 0 1px rgba(0,229,255,.06) inset, 0 0 22px -8px rgba(0,229,255,.55) !important; }
header[data-testid="stHeader"] { background: linear-gradient(180deg, rgba(2,4,13,.85), rgba(2,4,13,.55)) !important;
  border-bottom: 1px solid rgba(0,229,255,.14) !important; }
[data-testid="stTopNavLink"][aria-current="page"], [data-testid="stTopNavLink"]:hover {
  background: linear-gradient(135deg, rgba(0,229,255,.16), rgba(155,92,255,.14)) !important; }
/* títulos e destaques em gradiente ciano → violeta */
h1, h2, .ps-hero h1 b, .ps-cab h1 { background: linear-gradient(90deg, #E4F6FF 0%, #7AF3FF 45%, #C4A0FF 100%);
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }
/* botões principais em gradiente neon */
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {
  background: linear-gradient(135deg, #00E5FF, #9B5CFF) !important; color: #02040D !important; border: 0 !important;
  box-shadow: 0 10px 30px -12px rgba(0,229,255,.75) !important; }
[data-testid="stBaseButton-primary"] p, [data-testid="stBaseButton-primaryFormSubmit"] p { color: #02040D !important; font-weight: 700; }
/* cartões, gavetas e janelas com vidro escuro e contorno luminoso */
[data-testid="stPopoverBody"], [data-testid="stTopNavPopoverBody"], [class*="st-key-psc_"], [data-testid="stExpander"] details {
  border-color: rgba(0,229,255,.20) !important; box-shadow: 0 0 0 1px rgba(0,229,255,.05) inset, 0 30px 70px -30px rgba(0,229,255,.40) !important; }
/* campos com foco neon */
[data-baseweb="input"]:focus-within, [data-baseweb="select"] > div:focus-within, [data-testid="stTextInputRootElement"]:focus-within {
  border-color: #00E5FF !important; box-shadow: 0 0 0 3px rgba(0,229,255,.18) !important; }
/* chat e notificações no mesmo clima */
.st-key-ps_chat [data-testid="stPopoverButton"] { background: linear-gradient(135deg, #00E5FF, #9B5CFF) !important; box-shadow: 0 14px 34px -12px rgba(0,229,255,.8); }
.ps-msg.eu { background: linear-gradient(135deg, #00B8D9, #7B4DFF) !important; }
.ps-pop { border-color: rgba(0,229,255,.28) !important; box-shadow: 0 0 30px -10px rgba(0,229,255,.55) !important; }
::selection { background: rgba(0,229,255,.35); }
"""


def _css(t: dict) -> str:
    v = "\n".join(f"  --ps-{k.replace('_', '-')}: {val};" for k, val in t.items() if k != "shadow")
    if modo() == "Dark":
        extra = _css_quantum() + _css_neon("0,229,255", "155,92,255", claro=False)
    elif modo() == "Optimus":
        extra = _css_optimus()
    else:
        extra = _css_neon("45,75,255", "14,159,110", claro=True)
    return _css_base(t, v) + extra


def _css_base(t: dict, v: str) -> str:
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
/* 90% em qualquer máquina: o zoom fica só no corpo do site (.stApp). Menus, listas e janelas suspensas do Streamlit
   ficam fora dele (direto no body), então abrem exatamente embaixo de quem os chamou, sem precisar de correção. */
:root {{ --ps-zoom: .9; }}
/* topo apertado: botões das telas viram só ícones (o texto continua na dica do mouse) */
body.ps-topo-compacto [class*="st-key-reg_topo"] [data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"],
body.ps-topo-compacto [class*="st-key-promo_topo"] [data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"],
body.ps-topo-compacto [class*="st-key-mk_topo"] [data-testid="stPopoverButton"] [data-testid="stMarkdownContainer"] {{ display: none !important; }}
body.ps-topo-compacto [class*="st-key-reg_topo"] [data-testid="stButtonGroup"] button {{ padding: 0 8px !important; font-size: 12px !important; }}
body.ps-topo-compacto [class*="st-key-reg_topo"] {{ gap: 4px !important; }}
.stApp {{ zoom: var(--ps-zoom, .9); }}
iframe[data-testid="stCustomComponentV1"] {{ width: 100% !important; }}
.ps-zfix {{ transform: translate(var(--ps-zx), var(--ps-zy)) !important; }}
[data-testid="stElementContainer"]:has(#ps-conta-dados) {{ display: none !important; }}
/* conta no menu do topo: só a foto num círculo minimalista com luz neon */
[data-testid="stTopNavSection"]:has(> .ps-avatar) {{ padding: 0 4px !important; gap: 0 !important; }}
[data-testid="stTopNavSection"]:has(> .ps-avatar) > span:not(.ps-avatar), [data-testid="stTopNavSection"]:has(> .ps-avatar) > div[aria-hidden] {{ display: none !important; }}
.ps-avatar {{ position: relative; width: 22px; height: 22px; border-radius: 50%; flex: none; display: grid; place-items: center; overflow: visible;
  background: linear-gradient(135deg, var(--ps-primary), #7A3FD1); color: #fff; font: 700 9.5px var(--ps-font); letter-spacing: .02em;
  box-shadow: 0 0 0 1.5px var(--ps-surface-solid), 0 0 0 3px var(--ps-primary), 0 0 10px 1px color-mix(in srgb, var(--ps-primary) 60%, transparent);
  animation: ps-aura 3.2s ease-in-out infinite; transition: transform .2s; }}
.ps-avatar img {{ width: 100%; height: 100%; border-radius: 50%; object-fit: cover; display: block; }}
[data-testid="stTopNavSection"]:hover > .ps-avatar, [data-testid="stTopNavSection"][aria-expanded="true"] > .ps-avatar {{ transform: scale(1.08); }}
@keyframes ps-aura {{ 0%, 100% {{ box-shadow: 0 0 0 1.5px var(--ps-surface-solid), 0 0 0 3px var(--ps-primary), 0 0 8px 0 color-mix(in srgb, var(--ps-primary) 45%, transparent); }}
  50% {{ box-shadow: 0 0 0 1.5px var(--ps-surface-solid), 0 0 0 3px var(--ps-primary), 0 0 15px 3px color-mix(in srgb, var(--ps-primary) 70%, transparent); }} }}
.ps-zoff {{ translate: var(--ps-dx, 0px) var(--ps-dy, 0px) !important; }}   /* deslocamento que alinha o menu embaixo de quem o abriu */   /* menus abrem embaixo de onde foram chamados, mesmo com o zoom de 80% */
[data-testid="stMain"] {{ height: calc(100vh / var(--ps-zoom, .9)) !important; max-height: calc(100vh / var(--ps-zoom, .9)) !important; }}   /* área rolável ocupa a tela inteira mesmo com o zoom */   /* com o zoom do site, o Streamlit mede a largura das telas HTML a menos */   /* o site abre em 80% em qualquer máquina; o zoom do navegador continua funcionando por cima */
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
/* ---------- chat: painel de vidro, mensagens com avatar, prints com zoom ---------- */
[data-testid="stPopoverBody"]:has(.ps-chat-hd) {{ width: 440px !important; max-width: 94vw; padding: 0 !important; overflow-x: hidden; overflow-y: auto;
  max-height: calc(100vh - 110px) !important;
  background: radial-gradient(120% 60% at 0% 0%, color-mix(in srgb, var(--ps-primary) 14%, transparent), transparent 60%),
              radial-gradient(90% 50% at 100% 100%, color-mix(in srgb, #7A3FD1 12%, transparent), transparent 60%), var(--ps-surface-solid) !important;
  border: 1px solid color-mix(in srgb, var(--ps-primary) 25%, var(--ps-line)) !important; border-radius: 22px !important;
  box-shadow: 0 30px 80px -30px rgba(15,23,42,.6), 0 0 0 1px rgba(255,255,255,.04) inset !important; }}
[data-testid="stPopoverBody"]:has(.ps-chat-hd) > div {{ padding: 0 14px 12px !important; }}
.ps-chat-hd {{ display: flex; align-items: center; gap: 10px; margin: 0 -14px 8px; padding: 14px 16px 12px;
  background: linear-gradient(120deg, color-mix(in srgb, var(--ps-primary) 18%, transparent), transparent 70%);
  border-bottom: 1px solid var(--ps-line); }}
.ps-chat-ic {{ width: 36px; height: 36px; border-radius: 12px; display: grid; place-items: center; flex: none;
  background: linear-gradient(135deg, var(--ps-primary), #7A3FD1); box-shadow: 0 10px 24px -10px var(--ps-primary); }}
.ps-chat-tt {{ flex: 1; min-width: 0; }} .ps-chat-tt b {{ display: block; font-size: 15px; letter-spacing: -.01em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
.ps-chat-tt span {{ display: flex; align-items: center; gap: 6px; font-size: 11.5px; color: var(--ps-muted); }}
.ps-chat-tt .ps-live {{ width: 7px; height: 7px; border-radius: 50%; background: var(--ps-up); box-shadow: 0 0 0 3px color-mix(in srgb, var(--ps-up) 25%, transparent); }}
.ps-chat-av {{ display: flex; }} .ps-chat-av i {{ width: 26px; height: 26px; margin-left: -7px; border-radius: 50%; display: grid; place-items: center;
  font: 700 10px var(--ps-font); font-style: normal; color: #fff; border: 2px solid var(--ps-surface-solid); }}
[data-testid="stLayoutWrapper"]:has(> .st-key-ps_chat_msgs) {{ height: auto !important; flex: 0 0 auto !important; }}   /* a altura fica só na área de mensagens, que acompanha a tela */
.st-key-ps_chat_msgs {{ height: clamp(120px, calc(100vh - 470px), 340px) !important; max-height: clamp(120px, calc(100vh - 470px), 340px) !important;
  border: 1px solid var(--ps-line) !important; border-radius: 16px !important;
  background: linear-gradient(var(--ps-line) 1px, transparent 1px) 0 0 / 22px 22px, linear-gradient(90deg, var(--ps-line) 1px, transparent 1px) 0 0 / 22px 22px,
              color-mix(in srgb, var(--ps-canvas) 70%, transparent) !important; background-blend-mode: soft-light; }}
.ps-msgs {{ display: flex; flex-direction: column; gap: 8px; padding: 4px 2px; }}
.ps-dia {{ display: flex; justify-content: center; margin: 6px 0 2px; }}
.ps-dia span {{ font: 600 10px var(--ps-mono); letter-spacing: .08em; text-transform: uppercase; color: var(--ps-muted);
  background: var(--ps-surface-solid); border: 1px solid var(--ps-line); border-radius: 999px; padding: 3px 10px; }}
.ps-linha {{ display: flex; align-items: flex-end; gap: 7px; }} .ps-linha.eu {{ justify-content: flex-end; }}
.ps-ava {{ width: 28px; height: 28px; flex: none; border-radius: 50%; display: grid; place-items: center; font: 700 10.5px var(--ps-font); font-style: normal; color: #fff;
  box-shadow: 0 6px 14px -8px rgba(0,0,0,.5); }}
.ps-msg {{ max-width: 78%; background: var(--ps-surface-solid); border: 1px solid var(--ps-line); border-radius: 14px 14px 14px 4px; padding: 7px 11px 5px;
  box-shadow: 0 8px 20px -16px rgba(15,23,42,.5); animation: ps-msg-in .25s ease-out; }}
.ps-msg.eu {{ background: linear-gradient(135deg, var(--ps-primary), #5B3FE0); border-color: transparent; border-radius: 14px 14px 4px 14px;
  box-shadow: 0 10px 24px -14px var(--ps-primary); }}
@keyframes ps-msg-in {{ from {{ opacity: 0; transform: translateY(4px); }} to {{ opacity: 1; transform: none; }} }}
.ps-msg em {{ display: block; font-style: normal; font-size: 11px; font-weight: 700; color: var(--ps-primary); margin-bottom: 1px; }}
.ps-msg p {{ margin: 1px 0; font-size: 13px; line-height: 1.45; color: var(--ps-ink); white-space: pre-wrap; word-break: break-word; }}
.ps-msg small {{ display: block; text-align: right; font: 500 9.5px var(--ps-mono); color: var(--ps-faint); margin-top: 1px; }}
.ps-msg.eu p, .ps-msg.eu small {{ color: #fff !important; }} .ps-msg.eu small {{ opacity: .75; }}
.ps-mencao {{ color: #7A3FD1; background: color-mix(in srgb, #7A3FD1 12%, transparent); border-radius: 5px; padding: 0 3px; }}
.ps-msg.eu .ps-mencao {{ color: #fff; background: rgba(255,255,255,.18); }}
.ps-anexo {{ margin: 4px 0 3px; }}
.ps-anexo summary {{ list-style: none; position: relative; display: block; border-radius: 10px; overflow: hidden; border: 1px solid var(--ps-line); cursor: zoom-in; }}
.ps-anexo summary::-webkit-details-marker {{ display: none; }}
.ps-anexo summary img {{ display: block; width: 100%; max-height: 190px; object-fit: cover; transition: max-height .35s ease, transform .25s; }}
.ps-anexo:not([open]) summary:hover img {{ transform: scale(1.03); }}
.ps-zoom {{ position: absolute; right: 8px; bottom: 8px; font: 600 10px var(--ps-mono); letter-spacing: .06em; text-transform: uppercase; color: #fff;
  background: rgba(10,14,25,.6); backdrop-filter: blur(4px); padding: 3px 8px; border-radius: 999px; }}
.ps-anexo[open] summary {{ cursor: zoom-out; }} .ps-anexo[open] summary img {{ max-height: 70vh; object-fit: contain; background: #0b1020; }}
.ps-anexo[open] .ps-zoom::after {{ content: " / fechar"; }}
.ps-linha:has(.ps-anexo[open]) .ps-msg {{ max-width: 100%; }}
.ps-baixar {{ display: inline-block; margin-top: 5px; font-size: 11px; font-weight: 600; color: var(--ps-primary) !important; }}
.ps-msg.eu .ps-baixar {{ color: #fff !important; opacity: .9; }}
.ps-chat-ic span {{ font-family: "Material Symbols Rounded"; font-size: 20px; line-height: 1; color: #fff; font-weight: 400; }}
[data-testid="stPopoverBody"]:has(.ps-chat-hd) [data-testid="InputInstructions"] {{ display: none !important; }}
.st-key-ps_chat_msgs {{ gap: 6px !important; }}
.st-key-ps_chat_msgs [data-testid="stElementContainer"]:has([data-testid="stDownloadButton"]) {{ margin-top: -4px; }}
.st-key-ps_chat_msgs [data-testid="stDownloadButton"] button {{ min-height: 0 !important; height: 26px; padding: 0 8px !important; font-size: 11.5px !important;
  color: var(--ps-primary) !important; border-radius: 8px !important; }}
.st-key-ps_chat_msgs [data-testid="stDownloadButton"] button:hover {{ background: var(--ps-primary-soft) !important; }}
.ps-arq {{ display: flex; align-items: center; gap: 8px; margin: 4px 0 2px; padding: 6px 8px; border-radius: 10px; background: color-mix(in srgb, var(--ps-ink) 6%, transparent); }}
.ps-msg.eu .ps-arq {{ background: rgba(255,255,255,.16); }}
.ps-arq i {{ width: 30px; height: 30px; flex: none; border-radius: 8px; display: grid; place-items: center; font: 700 9px var(--ps-mono); font-style: normal; color: #fff;
  background: linear-gradient(135deg, #0EA5A4, #2D4BFF); }}
.ps-arq span {{ min-width: 0; display: flex; flex-direction: column; }}
.ps-arq b {{ font-size: 12px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; color: var(--ps-ink); }}
.ps-arq small {{ text-align: left !important; }}
.ps-msg.eu .ps-arq b {{ color: #fff; }}
.ps-pend {{ display: flex; flex-wrap: wrap; gap: 5px; }}
.ps-pend span {{ font-size: 11px; padding: 3px 8px; border-radius: 999px; background: var(--ps-primary-soft); color: var(--ps-primary); }}
.ps-msg-vazio {{ display: flex; flex-direction: column; gap: 4px; align-items: center; color: var(--ps-faint); font-size: 12px; text-align: center; padding: 70px 20px; }}
.ps-msg-vazio b {{ color: var(--ps-muted); font-size: 13px; }}
/* barra de envio: anexar print compacto + campo + enviar */
.st-key-chat_anexo [data-testid="stFileUploaderDropzone"] {{ padding: 6px 10px !important; min-height: 0 !important; border-radius: 12px !important;
  border: 1px dashed color-mix(in srgb, var(--ps-primary) 35%, var(--ps-line)) !important; background: transparent !important; }}
.st-key-chat_anexo [data-testid="stFileUploaderDropzoneInstructions"] {{ display: none !important; }}
.st-key-chat_anexo [data-testid="stFileUploaderDropzone"]::before {{ content: "Ctrl + V cola um print • ou anexe imagem, texto, Excel, CSV, ZIP, PDF"; font-size: 12px; color: var(--ps-muted); margin-right: auto; align-self: center; }}
[data-testid="stPopoverBody"]:has(.ps-chat-hd) [data-testid="stTextInputRootElement"] {{ border-radius: 999px !important; }}
[data-testid="stPopoverBody"]:has(.ps-chat-hd) [data-testid="stFormSubmitButton"] button {{ border-radius: 999px !important; background: linear-gradient(135deg, var(--ps-primary), #7A3FD1) !important; border: 0 !important; }}
/* ---------- notificações: pop-up que some sozinho e sininho no topo ---------- */
.ps-pops {{ position: fixed; right: 22px; top: 62px; z-index: 1000003; display: flex; flex-direction: column; gap: 8px; width: 340px; pointer-events: none; }}
.ps-pop {{ display: flex; gap: 10px; align-items: flex-start; padding: 12px 14px; border-radius: 14px; pointer-events: auto;
  background: color-mix(in srgb, var(--ps-surface-solid) 88%, transparent); border: 1px solid var(--ps-line);
  backdrop-filter: var(--ps-glass); -webkit-backdrop-filter: var(--ps-glass); box-shadow: 0 22px 50px -22px rgba(15,23,42,.55);
  animation: ps-pop-vida 7s cubic-bezier(.2,.8,.2,1) both; }}
.ps-pop b {{ display: block; font-size: 13px; }} .ps-pop span {{ display: block; font-size: 12px; color: var(--ps-muted); line-height: 1.4; margin-top: 2px; }}
.ps-pop .ps-live {{ width: 8px; height: 8px; margin-top: 5px; flex: none; border-radius: 50%; background: var(--ps-primary); box-shadow: 0 0 0 4px var(--ps-primary-soft); }}
.ps-pop-mais {{ justify-content: center; font-size: 12px; color: var(--ps-muted); }}
@keyframes ps-pop-vida {{ 0% {{ opacity: 0; transform: translateY(-12px) scale(.97); }} 6% {{ opacity: 1; transform: none; }}
  86% {{ opacity: 1; transform: none; }} 100% {{ opacity: 0; transform: translateX(24px); visibility: hidden; pointer-events: none; }} }}
.st-key-ps_sino {{ position: fixed !important; top: 11px; right: 112px; z-index: 1000002; width: auto !important; }}
.st-key-ps_sino [data-testid="stPopoverButton"] {{ height: 38px; min-height: 38px; min-width: 38px; padding: 0 9px; border-radius: 19px;
  background: var(--ps-surface) !important; border: 1px solid var(--ps-line) !important; backdrop-filter: var(--ps-glass); }}
.st-key-ps_sino [data-testid="stPopoverButton"]:hover {{ border-color: var(--ps-primary) !important; box-shadow: 0 0 0 4px var(--ps-primary-soft); }}
.st-key-ps_sino [data-testid="stPopoverButton"] p {{ font: 700 11px var(--ps-mono); color: #fff; background: #E0567A; border-radius: 999px; padding: 1px 6px; }}
.st-key-ps_sino [data-testid="stPopoverButton"] [data-testid="stIconMaterial"] {{ color: var(--ps-ink); font-size: 20px; }}
[data-testid="stPopoverBody"]:has(.ps-sino-top) {{ width: 380px !important; max-width: 92vw; }}
.ps-sino-top b {{ display: block; font-size: 15px; }} .ps-sino-top span {{ font-size: 11.5px; color: var(--ps-muted); }}
.ps-sino-lista {{ display: flex; flex-direction: column; gap: 6px; max-height: calc(100vh - 230px); overflow: auto; margin-top: 6px; }}
.ps-sino-it {{ padding: 8px 10px; border-radius: 10px; border: 1px solid var(--ps-line); }}
.ps-sino-it.nova {{ background: var(--ps-primary-soft); border-color: color-mix(in srgb, var(--ps-primary) 30%, var(--ps-line)); }}
.ps-sino-it b {{ display: block; font-size: 12.5px; }} .ps-sino-it span {{ display: block; font-size: 12px; color: var(--ps-muted); line-height: 1.4; }}
.ps-sino-it small {{ font: 500 10px var(--ps-mono); color: var(--ps-faint); }}
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
[data-testid="stTopNavPopover"] {{ animation: ps-drop .26s cubic-bezier(.16,1,.3,1) both; transform-origin: top center; }}
[data-testid="stTopNavPopover"] a, [data-testid="stTopNavPopover"] [data-testid="stTopNavLink"] {{ animation: ps-drop-item .3s cubic-bezier(.16,1,.3,1) both; }}
[data-testid="stTopNavPopover"] li:nth-child(2) a, [data-testid="stTopNavPopover"] li:nth-child(2) [data-testid="stTopNavLink"] {{ animation-delay: .04s; }}
[data-testid="stTopNavPopover"] li:nth-child(3) a, [data-testid="stTopNavPopover"] li:nth-child(3) [data-testid="stTopNavLink"] {{ animation-delay: .08s; }}
[data-testid="stTopNavPopover"] li:nth-child(4) a, [data-testid="stTopNavPopover"] li:nth-child(4) [data-testid="stTopNavLink"] {{ animation-delay: .12s; }}
@keyframes ps-drop-item {{ from {{ opacity: 0; transform: translateY(-4px); }} to {{ opacity: 1; transform: none; }} }}
[data-testid="stTopNavPopoverBody"] {{
  background: color-mix(in srgb, var(--ps-surface-solid) 82%, transparent) !important;
  backdrop-filter: var(--ps-glass); -webkit-backdrop-filter: var(--ps-glass);
  border: 1px solid var(--ps-line) !important; border-radius: 14px !important; box-shadow: 0 24px 48px -20px rgba(0,0,0,.5) !important;
}}
[data-testid="stTopNavDropdownLink"] {{ border-radius: 9px; transition: background-color .15s ease, color .15s ease; }}
[data-testid="stTopNavDropdownLink"]:hover {{ background: var(--ps-primary-soft) !important; color: var(--ps-primary) !important; }}
[data-testid="stTopNavSection"], [data-testid="stTopNavLink"] {{ transition: background-color .2s ease, color .2s ease; border-radius: 9px; }}
[data-testid="stTopNavSection"]:hover, [data-testid="stTopNavLink"]:hover {{ background: var(--ps-raised) !important; }}
@keyframes ps-drop {{ from {{ opacity: 0; transform: translateY(-8px) scale(.96); filter: blur(2px); }} to {{ opacity: 1; transform: none; filter: none; }} }}

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
/* ---------- entrada: fundo vivo, palavra girando, cartão com borda neon e a foto de quem já entrou ---------- */
.st-key-ps_login_bg {{ position: fixed !important; inset: 0; z-index: 0; pointer-events: none; opacity: .9; }}
.st-key-ps_login_bg iframe {{ position: fixed !important; inset: 0; width: 100vw !important; height: calc(100vh / var(--ps-zoom, .9)) !important; }}
[data-testid="stMainBlockContainer"]:has(.st-key-psc_login) > div {{ position: relative; z-index: 1; }}
.ps-login-live {{ width: 8px; height: 8px; border-radius: 50%; background: var(--ps-up); margin-left: 6px; box-shadow: 0 0 0 0 color-mix(in srgb, var(--ps-up) 60%, transparent);
  animation: ps-vivo 1.8s infinite; }}
.ps-login-brand small {{ font: 600 .7rem var(--ps-mono); letter-spacing: .12em; text-transform: uppercase; color: var(--ps-up); }}
@keyframes ps-vivo {{ 0% {{ box-shadow: 0 0 0 0 color-mix(in srgb, var(--ps-up) 55%, transparent); }} 70% {{ box-shadow: 0 0 0 9px transparent; }} 100% {{ box-shadow: 0 0 0 0 transparent; }} }}
.ps-rot {{ display: inline-block; height: 1.12em; overflow: hidden; vertical-align: bottom; }}
.ps-rot > span {{ display: flex; flex-direction: column; animation: ps-rot 11s cubic-bezier(.7,0,.3,1) infinite; }}
.ps-rot em {{ font-style: normal; line-height: 1.12em; height: 1.12em; background: linear-gradient(90deg, var(--ps-primary), var(--ps-up));
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent; }}
@keyframes ps-rot {{ 0%, 18% {{ transform: translateY(0); }} 23%, 41% {{ transform: translateY(-1.12em); }} 46%, 64% {{ transform: translateY(-2.24em); }}
  69%, 87% {{ transform: translateY(-3.36em); }} 92%, 100% {{ transform: translateY(-4.48em); }} }}
.st-key-ps_login_graf {{ border-radius: 22px; padding: 6px 4px 0; background: color-mix(in srgb, var(--ps-surface-solid) 55%, transparent);
  border: 1px solid var(--ps-line); backdrop-filter: blur(10px); box-shadow: 0 30px 70px -40px color-mix(in srgb, var(--ps-primary) 60%, transparent); margin-top: 1.4rem; }}
.st-key-psc_login {{ position: relative; isolation: isolate; border-radius: 26px !important; overflow: hidden; border: 0 !important;
  background: color-mix(in srgb, var(--ps-surface-solid) 82%, transparent) !important; backdrop-filter: blur(18px);
  box-shadow: 0 40px 90px -40px color-mix(in srgb, var(--ps-primary) 70%, transparent) !important; padding: 26px 24px !important; }}
.st-key-psc_login::before {{ content: ""; position: absolute; inset: -60%; z-index: -1;
  background: conic-gradient(from 0deg, transparent 0 60%, var(--ps-primary) 72%, var(--ps-up) 82%, transparent 92%); animation: ps-gira 6s linear infinite; }}
.st-key-psc_login::after {{ content: ""; position: absolute; inset: 1.5px; z-index: -1; border-radius: 25px; background: var(--ps-surface-solid); }}
@keyframes ps-gira {{ to {{ transform: rotate(360deg); }} }}
.ps-login-ola {{ display: flex; flex-direction: column; align-items: center; text-align: center; gap: 4px; margin-bottom: .6rem; }}
.ps-login-ola h2 {{ margin: .5rem 0 0; font-size: 1.45rem; letter-spacing: -.03em; }}
.ps-login-ola .sub {{ margin: 0; color: var(--ps-muted); font-size: .9rem; }}
.ps-login-av {{ width: 76px; height: 76px; border-radius: 50%; display: grid; place-items: center; color: #fff; font: 700 1.5rem var(--ps-font);
  background: linear-gradient(135deg, var(--ps-primary), #7A3FD1); animation: ps-aura-g 3s ease-in-out infinite; }}
.ps-login-av.marca {{ background: var(--ps-surface-solid); }} .ps-login-av.marca img {{ width: 40px; height: 40px; }} .ps-login-av.marca span {{ display: none; }}
.ps-login-av img {{ width: 100%; height: 100%; border-radius: 50%; object-fit: cover; }}
@keyframes ps-aura-g {{ 0%, 100% {{ box-shadow: 0 0 0 3px var(--ps-surface-solid), 0 0 0 5px var(--ps-primary), 0 0 18px 2px color-mix(in srgb, var(--ps-primary) 45%, transparent); }}
  50% {{ box-shadow: 0 0 0 3px var(--ps-surface-solid), 0 0 0 5px var(--ps-primary), 0 0 34px 8px color-mix(in srgb, var(--ps-primary) 70%, transparent); }} }}
.ps-sug-t {{ margin: -4px 0 -6px; font-size: .78rem; color: var(--ps-muted); }}
.ps-login-pills span {{ border-color: color-mix(in srgb, var(--c) 35%, var(--ps-line)) !important; }}
.ps-login-pills span i {{ background: var(--c); box-shadow: 0 0 10px var(--c); }}
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
    paleta = (["#7FA6FF", "#FF7A93", "#2BD99F", "#F5B547", "#B794FF", "#4CC9F0", "#FF8FC7", "#9AA5BD"] if escuro()
              else ["#2D4BFF", "#E11D48", "#0E9F6E", "#C47A0A", "#7A3FD1", "#0B8DB0", "#C2367A", "#566176"])
    return paleta[sum(ord(c) for c in (nome or "")) % len(paleta)]


def plotly_layout(altura: int = 320) -> dict:
    t = tokens()
    return dict(height=altura, margin=dict(l=8, r=8, t=16, b=8), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(family=f"{FONTE}, sans-serif", color=t["muted"], size=12), separators=",.")
