"""Sistema visual "Etiqueta de gôndola": tokens, tema nativo do Streamlit e CSS."""
from __future__ import annotations

import streamlit as st
from streamlit import config as st_config

FONTE = "Archivo"
FONTE_URL = "https://fonts.googleapis.com/css2?family=Archivo:ital,wdth,wght@0,62..125,100..900;1,62..125,100..900&display=swap"

TOKENS = {
    "Light": {
        "canvas": "#ECEEF1",      # piso de loja
        "surface": "#FFFFFF",
        "raised": "#F5F6F8",
        "ink": "#161A22",
        "muted": "#5A6372",
        "line": "#D6DAE1",
        "primary": "#2424ED",     # azul PriceSense
        "primary_hover": "#1515B8",
        "primary_soft": "rgba(36,36,237,.09)",
        "tag": "#FFD000",         # amarelo encarte
        "tag_ink": "#161A22",
        "alert": "#D7192D",       # vermelho oferta
        "alert_soft": "rgba(215,25,45,.10)",
        "ok": "#0C8A57",
        "ok_soft": "rgba(12,138,87,.11)",
        "warn_soft": "rgba(255,208,0,.30)",
        "varejo": "#2424ED",
        "atacado": "#D7192D",
        "shadow": "0 1px 0 rgba(22,26,34,.04), 0 10px 28px -16px rgba(22,26,34,.22)",
    },
    "Dark": {
        "canvas": "#0E1424",      # loja à noite
        "surface": "#151D31",
        "raised": "#1B2540",
        "ink": "#EEF1F8",
        "muted": "#9AA5BD",
        "line": "#2A3550",
        "primary": "#7B83FF",
        "primary_hover": "#9AA0FF",
        "primary_soft": "rgba(123,131,255,.14)",
        "tag": "#FFD000",
        "tag_ink": "#161A22",
        "alert": "#FF5468",
        "alert_soft": "rgba(255,84,104,.14)",
        "ok": "#3DD598",
        "ok_soft": "rgba(61,213,152,.13)",
        "warn_soft": "rgba(255,208,0,.16)",
        "varejo": "#8C93FF",
        "atacado": "#FF6B7C",
        "shadow": "0 1px 0 rgba(0,0,0,.25), 0 14px 32px -18px rgba(0,0,0,.6)",
    },
}


def modo() -> str:
    return "Dark" if st.session_state.get("tema") == "Dark" else "Light"


def tokens() -> dict:
    return TOKENS[modo()]


def _tema_nativo(t: dict) -> None:
    opcoes = {
        "theme.base": "dark" if modo() == "Dark" else "light",
        "theme.primaryColor": t["primary"],
        "theme.backgroundColor": t["canvas"],
        "theme.secondaryBackgroundColor": t["raised"],
        "theme.textColor": t["ink"],
        "theme.borderColor": t["line"],
        "theme.dataframeBorderColor": t["line"],
        "theme.dataframeHeaderBackgroundColor": t["raised"],
        "theme.linkColor": t["primary"],
        "theme.redColor": t["alert"],
        "theme.greenColor": t["ok"],
        "theme.blueColor": t["primary"],
        "theme.yellowColor": t["tag"],
        "theme.font": f"{FONTE}:{FONTE_URL}, sans-serif",
        "theme.headingFont": f"{FONTE}:{FONTE_URL}, sans-serif",
        "theme.baseRadius": "0.5rem",
        "theme.buttonRadius": "0.5rem",
        "theme.showWidgetBorder": True,
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
  --ps-font: '{FONTE}', 'Helvetica Neue', Arial, sans-serif;
}}

/* ---------- base ---------- */
html, body, .stApp, button, input, textarea, select, [data-testid="stMarkdownContainer"] {{
  font-family: var(--ps-font);
}}
[data-testid="stIconMaterial"] {{ font-family: 'Material Symbols Rounded' !important; }}
.stApp {{ background: var(--ps-canvas); color: var(--ps-ink); }}
[data-testid="stAppDeployButton"], [data-testid="stMainMenu"], [data-testid="stDecoration"] {{ display: none !important; }}
[data-testid="stSidebar"], [data-testid="stSidebarCollapsedControl"] {{ display: none !important; }}

[data-testid="stMainBlockContainer"] {{
  max-width: 1440px;
  padding: 5.4rem 2.5rem 5rem;
}}
@media (max-width: 760px) {{
  [data-testid="stMainBlockContainer"] {{ padding: 4.6rem 1rem 4rem; }}
}}

header[data-testid="stHeader"] {{
  background: var(--ps-surface);
  border-bottom: 1px solid var(--ps-line);
}}

/* superfícies (containers com key que começa em psc_) */
[class*="st-key-psc_"] {{
  background: var(--ps-surface);
  box-shadow: var(--ps-shadow);
}}

button[kind="primary"], button[kind="secondary"], button[kind="tertiary"],
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-secondary"] {{ font-weight: 600; }}

:focus-visible {{ outline: 2px solid var(--ps-primary) !important; outline-offset: 2px; }}

/* área de colagem do Preço Bot: colunas alinhadas por TAB */
.st-key-pb_texto textarea {{
  font-family: ui-monospace, 'SFMono-Regular', Menlo, Consolas, monospace;
  font-size: .9rem; tab-size: 8; -moz-tab-size: 8; line-height: 1.55;
}}

/* ---------- cabeçalho de página ---------- */
.ps-head h1 {{
  font-family: var(--ps-font); font-stretch: 116%; font-weight: 800;
  font-size: clamp(1.85rem, 1.1rem + 2.1vw, 2.75rem);
  letter-spacing: -.028em; line-height: 1.02; margin: 0; padding: 0; color: var(--ps-ink);
}}
.ps-head p {{ color: var(--ps-muted); margin: .45rem 0 0; font-size: 1.02rem; max-width: 68ch; line-height: 1.45; }}

.ps-sec {{ margin: 1.6rem 0 .55rem; }}
.ps-sec h2 {{
  font-family: var(--ps-font); font-stretch: 108%; font-weight: 750; font-size: 1.22rem;
  letter-spacing: -.012em; margin: 0; padding: 0; color: var(--ps-ink);
}}
[class*="st-key-psc_"] .ps-sec {{ margin-top: .1rem; }}
.ps-sec p {{ color: var(--ps-muted); margin: .2rem 0 0; font-size: .93rem; max-width: 72ch; }}

/* ---------- etiqueta de gôndola (elemento assinatura) ---------- */
.ps-tags {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(178px, 1fr)); gap: 12px; }}
.ps-tag {{
  --band: var(--ps-ink);
  position: relative; overflow: hidden;
  background: var(--ps-surface); border: 1px solid var(--ps-line); border-radius: 10px;
  padding: 14px 16px 13px 24px; min-height: 124px;
  display: flex; flex-direction: column; justify-content: space-between; gap: 10px;
  box-shadow: var(--ps-shadow);
}}
.ps-tag::before {{ content: ""; position: absolute; inset: 0 auto 0 0; width: 8px; background: var(--band); }}
.ps-tag::after {{
  content: ""; position: absolute; top: 12px; right: 12px; width: 9px; height: 9px; border-radius: 50%;
  background: var(--ps-canvas); box-shadow: inset 0 0 0 1px var(--ps-line);
}}
.ps-tag.t-primary {{ --band: var(--ps-primary); }}
.ps-tag.t-promo {{ --band: var(--ps-tag); }}
.ps-tag.t-alert {{ --band: var(--ps-alert); }}
.ps-tag.t-ok {{ --band: var(--ps-ok); }}
.ps-tag-label {{ font-size: .88rem; font-weight: 600; color: var(--ps-ink); padding-right: 18px; line-height: 1.25; }}
.ps-price {{
  display: flex; align-items: flex-start; color: var(--ps-ink);
  font-family: var(--ps-font); font-stretch: 62%; font-weight: 800; font-size: 3.1rem;
  line-height: .86; letter-spacing: -.01em; font-variant-numeric: tabular-nums lining-nums;
}}
.ps-price .cur {{ font-stretch: 100%; font-size: .3em; font-weight: 700; margin: .28em .3em 0 0; letter-spacing: 0; }}
.ps-price .dec {{
  font-size: .5em; margin-top: .06em; text-decoration: underline;
  text-decoration-thickness: .07em; text-underline-offset: .13em;
}}
.ps-price .suf {{ font-stretch: 100%; font-size: .3em; font-weight: 700; margin: .28em 0 0 .3em; }}
.ps-tag-note {{ font-size: .8rem; color: var(--ps-muted); line-height: 1.3; }}
.ps-tag-note b {{ color: var(--ps-ink); font-weight: 600; }}

/* ---------- barra de validação ---------- */
.ps-split {{ background: var(--ps-surface); border: 1px solid var(--ps-line); border-radius: 10px; padding: 14px 16px; box-shadow: var(--ps-shadow); }}
.ps-split-bar {{ display: flex; height: 12px; border-radius: 6px; overflow: hidden; background: var(--ps-raised); gap: 2px; }}
.ps-split-bar span {{ display: block; }}
.ps-split-bar .ok {{ background: var(--ps-ok); }}
.ps-split-bar .alert {{ background: var(--ps-alert); }}
.ps-split-legend {{ display: flex; gap: 18px; margin-top: 10px; font-size: .86rem; color: var(--ps-muted); flex-wrap: wrap; }}
.ps-split-legend i {{ display: inline-block; width: 9px; height: 9px; border-radius: 2px; margin-right: 6px; vertical-align: 0; }}
.ps-split-legend b {{ color: var(--ps-ink); font-variant-numeric: tabular-nums; }}

/* ---------- régua de concorrentes (letreiro) ---------- */
.ps-ticker {{
  position: relative; overflow: hidden; background: var(--ps-surface);
  border: 1px solid var(--ps-line); border-radius: 10px; box-shadow: var(--ps-shadow);
}}
.ps-ticker-track {{ display: inline-flex; white-space: nowrap; padding: 11px 0; animation: ps-ticker var(--dur) linear infinite; }}
.ps-ticker:hover .ps-ticker-track {{ animation-play-state: paused; }}
.ps-ticker-item {{ display: inline-flex; align-items: baseline; gap: 10px; padding: 0 26px; border-right: 1px dashed var(--ps-line); font-size: .9rem; }}
.ps-ticker-item b {{ font-weight: 700; letter-spacing: .01em; }}
.ps-ticker-item .v {{ color: var(--ps-varejo); font-weight: 800; font-stretch: 75%; font-size: 1.05rem; font-variant-numeric: tabular-nums; }}
.ps-ticker-item .a {{ color: var(--ps-atacado); font-weight: 800; font-stretch: 75%; font-size: 1.05rem; font-variant-numeric: tabular-nums; }}
.ps-ticker-item small {{ color: var(--ps-muted); font-size: .76rem; }}
@keyframes ps-ticker {{ from {{ transform: translateX(0); }} to {{ transform: translateX(-50%); }} }}
@media (prefers-reduced-motion: reduce) {{
  .ps-ticker {{ overflow-x: auto; }}
  .ps-ticker-track {{ animation: none; }}
}}

/* ---------- avisos e estados vazios ---------- */
.ps-empty {{
  border: 1.5px dashed var(--ps-line); border-radius: 12px; padding: 34px 28px;
  background: color-mix(in srgb, var(--ps-surface) 55%, transparent);
}}
.ps-empty h3 {{ font-family: var(--ps-font); font-stretch: 108%; font-size: 1.1rem; font-weight: 750; margin: 0 0 .35rem; padding: 0; color: var(--ps-ink); }}
.ps-empty p {{ margin: 0; color: var(--ps-muted); max-width: 62ch; line-height: 1.5; }}

.ps-chip {{
  display: inline-flex; align-items: center; gap: 6px; font-size: .78rem; font-weight: 600;
  padding: 3px 9px; border-radius: 999px; background: var(--ps-raised); color: var(--ps-ink);
  border: 1px solid var(--ps-line); white-space: nowrap;
}}
.ps-chip i {{ width: 8px; height: 8px; border-radius: 50%; display: inline-block; }}
.ps-chip.promo {{ background: var(--ps-tag); color: var(--ps-tag-ink); border-color: transparent; }}

/* ---------- ferramentas na página inicial ---------- */
.ps-tool h3 {{
  font-family: var(--ps-font); font-stretch: 108%; font-weight: 750; font-size: 1.12rem;
  margin: 0 0 .3rem; padding: 0; color: var(--ps-ink); letter-spacing: -.01em;
}}
.ps-tool p {{ color: var(--ps-muted); font-size: .92rem; line-height: 1.45; margin: 0; min-height: 4.1em; }}
.ps-tool .ps-chip {{ margin-bottom: .7rem; }}

/* ---------- relatórios ---------- */
.ps-rep-cat {{ display: flex; align-items: center; gap: 8px; font-size: .82rem; font-weight: 600; color: var(--ps-muted); margin-bottom: .55rem; }}
.ps-rep-cat i {{ width: 10px; height: 10px; border-radius: 3px; display: inline-block; }}
.ps-rep-title {{
  font-family: var(--ps-font); font-stretch: 104%; font-weight: 750; font-size: 1.12rem;
  line-height: 1.22; color: var(--ps-ink); margin-bottom: .4rem; letter-spacing: -.01em;
}}
.ps-rep-desc {{
  color: var(--ps-muted); font-size: .9rem; line-height: 1.45; min-height: 3.9em;
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
}}
.ps-rep-meta {{ display: flex; flex-wrap: wrap; gap: 6px 14px; margin-top: .8rem; font-size: .8rem; color: var(--ps-muted); }}
.ps-rep-meta span {{ display: inline-flex; align-items: center; gap: 4px; }}
.ps-rep-tags {{ display: flex; flex-wrap: wrap; gap: 6px; margin-top: .7rem; }}

.ps-viewer-head h2 {{
  font-family: var(--ps-font); font-stretch: 112%; font-weight: 800; letter-spacing: -.02em;
  font-size: clamp(1.5rem, 1rem + 1.4vw, 2.1rem); line-height: 1.08; margin: 0; padding: 0; color: var(--ps-ink);
}}
.ps-viewer-head p {{ color: var(--ps-muted); margin: .45rem 0 0; max-width: 80ch; }}

.ps-list-row {{ display: grid; grid-template-columns: 12px 1fr auto; gap: 12px; align-items: center; padding: 11px 2px; border-bottom: 1px solid var(--ps-line); }}
.ps-list-row:last-child {{ border-bottom: none; }}
.ps-list-row i {{ width: 10px; height: 10px; border-radius: 3px; }}
.ps-list-row b {{ font-weight: 650; color: var(--ps-ink); }}
.ps-list-row span {{ color: var(--ps-muted); font-size: .84rem; }}

/* ---------- avatar ---------- */
.ps-avatar {{
  width: 44px; height: 44px; border-radius: 50%; object-fit: cover; display: grid; place-items: center;
  background: var(--ps-primary); color: #fff; font-weight: 800; font-size: 1.05rem;
}}
.ps-user {{ display: flex; gap: 12px; align-items: center; margin-bottom: .5rem; }}
.ps-user b {{ display: block; color: var(--ps-ink); }}
.ps-user span {{ color: var(--ps-muted); font-size: .85rem; }}

/* ---------- login ---------- */
.ps-hero {{ padding: 2vh 0; }}
.ps-hero-brand {{ display: flex; align-items: center; gap: 10px; margin-bottom: 2.4rem; }}
.ps-hero-brand img {{ width: 40px; height: 40px; display: block; }}
.ps-hero-brand span {{ font-stretch: 112%; font-weight: 800; font-size: 1.7rem; letter-spacing: -.03em; color: var(--ps-ink); }}
.ps-hero-tag {{
  position: relative; background: var(--ps-tag); color: var(--ps-tag-ink); border-radius: 18px;
  padding: 26px 30px 24px 44px; max-width: 560px; box-shadow: 0 30px 60px -32px rgba(22,26,34,.55);
  transform: rotate(-1.6deg);
}}
.ps-hero-tag::before {{ content: ""; position: absolute; inset: 0 auto 0 0; width: 16px; background: var(--ps-tag-ink); border-radius: 18px 0 0 18px; }}
.ps-hero-tag::after {{
  content: ""; position: absolute; top: 22px; right: 24px; width: 16px; height: 16px; border-radius: 50%;
  background: var(--ps-canvas); box-shadow: inset 0 0 0 2px rgba(22,26,34,.25);
}}
.ps-hero-desc {{ font-weight: 700; font-size: 1.05rem; line-height: 1.3; max-width: 30ch; margin-bottom: 18px; }}
.ps-hero-price {{
  display: flex; align-items: flex-start; font-stretch: 62%; font-weight: 850;
  font-size: clamp(6rem, 4rem + 7vw, 10.5rem); line-height: .82; letter-spacing: -.02em;
  font-variant-numeric: tabular-nums lining-nums;
}}
.ps-hero-price .cur {{ font-stretch: 100%; font-size: .22em; font-weight: 800; margin: .3em .22em 0 0; }}
.ps-hero-price .dec {{ display: inline-flex; font-size: .5em; margin-top: .05em; border-bottom: .07em solid currentColor; }}
.ps-roll {{ display: inline-block; height: 1em; overflow: hidden; line-height: 1; vertical-align: top; }}
.ps-reel {{
  display: flex; flex-direction: column; transform: translateY(calc(var(--to) * -1em));
  animation: ps-roll 1.6s cubic-bezier(.16,.84,.24,1) both; animation-delay: var(--d);
}}
.ps-reel span {{ display: block; height: 1em; line-height: 1; }}
@keyframes ps-roll {{ from {{ transform: translateY(0); }} to {{ transform: translateY(calc(var(--to) * -1em)); }} }}
@media (prefers-reduced-motion: reduce) {{ .ps-reel {{ animation: none; }} }}
.ps-hero-foot {{ display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; margin-top: 18px; border-top: 2px dashed rgba(22,26,34,.35); padding-top: 14px; }}
.ps-hero-foot .atac {{ font-weight: 700; font-size: .95rem; }}
.ps-hero-foot .atac strong {{ font-stretch: 70%; font-weight: 850; font-size: 1.9rem; letter-spacing: -.01em; margin-left: 6px; }}
.ps-hero-foot .bars {{ display: flex; gap: 2px; align-items: flex-end; height: 34px; }}
.ps-hero-foot .bars i {{ display: block; width: 2px; background: var(--ps-tag-ink); }}
.ps-hero-copy {{ margin-top: 2.4rem; color: var(--ps-muted); max-width: 46ch; line-height: 1.5; font-size: 1.02rem; }}
.st-key-psc_login h2 {{ font-family: var(--ps-font); font-stretch: 110%; font-weight: 800; font-size: 1.6rem; margin: 0 0 .2rem; padding: 0; letter-spacing: -.02em; }}
.st-key-psc_login p.sub {{ color: var(--ps-muted); margin: 0 0 1rem; }}
@media (max-width: 760px) {{ .ps-hero-tag {{ transform: none; padding-left: 34px; }} }}
"""


def cor_categoria(nome: str) -> str:
    paleta = (["#8C93FF", "#FF6B7C", "#3DD598", "#FFB648", "#B58CFF", "#4CC9F0", "#FF7EB6", "#9AA5BD"] if modo() == "Dark"
              else ["#2424ED", "#D7192D", "#0C8A57", "#E08A00", "#7A3FD1", "#0B8DB0", "#C2367A", "#5A6372"])
    return paleta[sum(ord(c) for c in (nome or "")) % len(paleta)]


def plotly_layout(altura: int = 320) -> dict:
    t = tokens()
    return dict(
        height=altura,
        margin=dict(l=8, r=8, t=16, b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=f"{FONTE}, sans-serif", color=t["muted"], size=12),
        hovermode="x unified",
        hoverlabel=dict(bgcolor=t["surface"], bordercolor=t["line"], font=dict(family=f"{FONTE}, sans-serif", color=t["ink"], size=13)),
        xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(color=t["muted"], size=11), linecolor=t["line"]),
        yaxis=dict(showgrid=True, gridcolor=t["line"], zeroline=False, tickprefix="R$ ", tickfont=dict(color=t["muted"], size=11)),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0, font=dict(color=t["ink"])),
        separators=",.",
    )
