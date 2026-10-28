"""Tela de entrada: painel de mercado animado e acesso."""
from __future__ import annotations

import json

import streamlit as st
import streamlit.components.v1 as components

from core import auth, state
from ui import components as ui
from ui import theme


def _grafico_mercado() -> None:
    """Índice de preço desenhando-se até "hoje" e seguindo como projeção com faixa de confiança."""
    t = theme.tokens()
    cores = {k: t[k] for k in ("ink", "muted", "faint", "primary", "up", "down", "amber", "surface_solid")}
    components.html(f"""<!doctype html><html><head><meta charset="utf-8">
<style>@import url('{theme.FONTE_URL}');html,body{{margin:0;background:transparent;overflow:hidden}}canvas{{display:block;width:100%;height:100%}}</style>
</head><body><canvas id="c" role="img" aria-label="Ilustração: índice de preço com projeção"></canvas><script>
const C = {json.dumps(cores)};
const cv = document.getElementById('c'), ctx = cv.getContext('2d');
let W = 0, H = 0;
function ajustar() {{ const r = cv.getBoundingClientRect(), d = devicePixelRatio || 1; W = r.width; H = r.height;
  cv.width = W * d; cv.height = H * d; ctx.setTransform(d, 0, 0, d, 0, 0); }}
let s = 11; const rnd = () => (s = s * 16807 % 2147483647, (s - 1) / 2147483646);
const N = 64, P = 22, hist = [], conc = [], proj = [], lo = [], hi = [];
let v = 104.5;
for (let i = 0; i < N; i++) {{ v += (rnd() - .56) * 1.05 + Math.sin(i / 6) * .12; hist.push(v); conc.push(v - 1.8 + (rnd() - .5) * 1.4); }}
let pv = hist[N - 1];
for (let k = 1; k <= P; k++) {{ pv += .08 + Math.sin(k / 4) * .05; proj.push(pv); const b = Math.sqrt(k) * .55; lo.push(pv - b); hi.push(pv + b); }}
const todos = hist.concat(conc, lo, hi), yMin = Math.min(...todos) - .6, yMax = Math.max(...todos) + .6;
const pad = {{l: 6, r: 52, t: 28, b: 26}};
const X = i => pad.l + (W - pad.l - pad.r) * i / (N + P - 1);
const Y = y => pad.t + (H - pad.t - pad.b) * (1 - (y - yMin) / (yMax - yMin));
const fmt = n => n.toFixed(1).replace('.', ',');
const reduzir = matchMedia('(prefers-reduced-motion: reduce)').matches;
const alfa = (hex, a) => hex + Math.round(a * 255).toString(16).padStart(2, '0');

function linha(arr, i0, ate, cor, larg, tracejado) {{
  ctx.beginPath(); ctx.setLineDash(tracejado || []); ctx.lineWidth = larg; ctx.strokeStyle = cor; ctx.lineJoin = 'round';
  for (let i = 0; i <= ate; i++) {{ const x = X(i0 + i), y = Y(arr[i]); i ? ctx.lineTo(x, y) : ctx.moveTo(x, y); }}
  ctx.stroke(); ctx.setLineDash([]);
}}
function desenhar(p, pulso) {{
  ctx.clearRect(0, 0, W, H);
  ctx.font = '500 10px "Geist Mono", monospace'; ctx.textBaseline = 'middle';
  for (let g = 0; g <= 4; g++) {{
    const yv = yMin + (yMax - yMin) * g / 4, y = Y(yv);
    ctx.strokeStyle = alfa(C.faint, .18); ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r + 6, y); ctx.stroke();
    ctx.fillStyle = C.faint; ctx.fillText(fmt(yv), W - pad.r + 12, y);
  }}
  const fh = Math.min(1, p / .7), nh = Math.max(1, Math.floor((N - 1) * fh));
  // área do histórico
  const grad = ctx.createLinearGradient(0, pad.t, 0, H - pad.b);
  grad.addColorStop(0, alfa(C.primary, .32)); grad.addColorStop(1, alfa(C.primary, 0));
  ctx.beginPath(); ctx.moveTo(X(0), H - pad.b);
  for (let i = 0; i <= nh; i++) ctx.lineTo(X(i), Y(hist[i]));
  ctx.lineTo(X(nh), H - pad.b); ctx.closePath(); ctx.fillStyle = grad; ctx.fill();
  linha(conc, 0, nh, alfa(C.muted, .55), 1.2, [2, 3]);
  linha(hist, 0, nh, C.primary, 2);
  // hoje + projeção
  if (p > .7) {{
    const fp = Math.min(1, (p - .7) / .3), np = Math.max(1, Math.floor(P * fp)), xh = X(N - 1);
    ctx.strokeStyle = alfa(C.amber, .7); ctx.setLineDash([3, 4]); ctx.beginPath(); ctx.moveTo(xh, pad.t - 8); ctx.lineTo(xh, H - pad.b); ctx.stroke(); ctx.setLineDash([]);
    ctx.fillStyle = C.amber; ctx.font = '500 10px "Geist Mono", monospace'; ctx.fillText('HOJE', xh + 6, pad.t - 10);
    ctx.beginPath(); ctx.moveTo(xh, Y(hist[N - 1]));
    for (let k = 0; k < np; k++) ctx.lineTo(X(N + k), Y(hi[k]));
    for (let k = np - 1; k >= 0; k--) ctx.lineTo(X(N + k), Y(lo[k]));
    ctx.closePath(); ctx.fillStyle = alfa(C.up, .12); ctx.fill();
    linha([hist[N - 1]].concat(proj.slice(0, np)), N - 1, np, C.up, 1.8, [5, 4]);
    ctx.fillStyle = C.up; ctx.fillText('PROJEÇÃO', X(N + Math.min(np, P - 1)) - 64, Y(hi[Math.min(np, P) - 1]) - 12);
  }}
  // ponto atual + etiqueta
  const hx = X(nh), hy = Y(hist[nh]);
  ctx.beginPath(); ctx.arc(hx, hy, 4 + pulso * 7, 0, 7); ctx.fillStyle = alfa(C.primary, .25 * (1 - pulso)); ctx.fill();
  ctx.beginPath(); ctx.arc(hx, hy, 3.5, 0, 7); ctx.fillStyle = C.primary; ctx.fill();
  const var_ = 100 * (hist[nh] - hist[0]) / hist[0], txt = 'Índice de preço ' + fmt(hist[nh]), dt = (var_ < 0 ? '▼ ' : '▲ ') + fmt(Math.abs(var_)) + '%';
  ctx.font = '500 11px "Geist", sans-serif'; const w = ctx.measureText(txt).width + ctx.measureText(dt).width + 30;
  let bx = Math.min(hx + 12, W - pad.r - w), by = hy - 34; if (by < 2) by = hy + 14;
  ctx.fillStyle = alfa(C.surface_solid, .92); ctx.strokeStyle = alfa(C.faint, .4); ctx.lineWidth = 1;
  ctx.beginPath(); ctx.roundRect(bx, by, w, 24, 8); ctx.fill(); ctx.stroke();
  ctx.fillStyle = C.ink; ctx.fillText(txt, bx + 10, by + 12);
  ctx.fillStyle = var_ < 0 ? C.up : C.down; ctx.fillText(dt, bx + 20 + ctx.measureText(txt).width, by + 12);
  // legenda
  ctx.font = '500 11px "Geist", sans-serif';
  [[C.primary, 'Nosso preço vs. moda de mercado'], [C.muted, 'Concorrência'], [C.up, 'Projeção']].reduce((x, [c, t]) => {{
    ctx.fillStyle = c; ctx.fillRect(x, 8, 10, 2); ctx.fillStyle = C.muted; ctx.fillText(t, x + 16, 9); return x + 34 + ctx.measureText(t).width; }}, pad.l);
}}
async function iniciar() {{
  try {{ await document.fonts.ready; }} catch (e) {{}}
  ajustar(); addEventListener('resize', () => {{ ajustar(); }});
  if (reduzir) {{ desenhar(1, 0); return; }}
  const t0 = performance.now(), dur = 2800;
  const passo = now => {{ const p = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - p, 3);
    desenhar(e, ((now - t0) % 1800) / 1800); requestAnimationFrame(passo); }};
  requestAnimationFrame(passo);
}}
iniciar();
</script></body></html>""", height=330)


def _depois_de_entrar() -> None:
    paginas = state.paginas()
    pendente = st.session_state.pop("pending_report", None)
    if pendente and "biblioteca" in paginas:
        st.switch_page(paginas["biblioteca"], query_params={"r": pendente})
    if "inicio" in paginas:
        st.switch_page(paginas["inicio"])


def _form_entrar() -> None:
    st.html("<h2>Acessar o painel</h2><p class='sub'>Entre com o usuário e a senha cadastrados.</p>")
    with st.form("form_login", border=False):
        usuario = st.text_input("Usuário", autocomplete="username")
        senha = st.text_input("Senha", type="password", autocomplete="current-password")
        enviar = st.form_submit_button("Entrar", type="primary", width="stretch")
    if enviar:
        ok, msg = auth.entrar(usuario, senha)
        if ok:
            st.rerun()
        st.error(msg, icon=":material/error:")
    st.divider()
    if st.button("Solicitar acesso", width="stretch", key="ir_cadastro", icon=":material/person_add:"):
        st.session_state.modo_login = "cadastro"
        st.rerun()


def _form_cadastro() -> None:
    st.html("<h2>Solicitar acesso</h2><p class='sub'>Um administrador aprova o cadastro e libera as ferramentas.</p>")
    with st.form("form_cadastro", border=False):
        nome = st.text_input("Nome completo")
        c1, c2 = st.columns(2)
        usuario = c1.text_input("Usuário")
        matricula = c2.text_input("Matrícula")
        cargo = st.text_input("Cargo")
        c3, c4 = st.columns(2)
        senha = c3.text_input("Senha", type="password", help="Mínimo de 6 caracteres.")
        senha2 = c4.text_input("Confirmar senha", type="password")
        enviar = st.form_submit_button("Enviar solicitação", type="primary", width="stretch")
    if enviar:
        ok, msg = auth.solicitar_acesso(nome, usuario, matricula, cargo, senha, senha2)
        if ok:
            st.session_state.modo_login = "login"
            st.session_state._flash_login = msg
            st.rerun()
        st.error(msg, icon=":material/error:")
    if st.button("Voltar para o login", type="tertiary", icon=":material/arrow_back:", key="voltar_login"):
        st.session_state.modo_login = "login"
        st.rerun()


def render() -> None:
    if st.session_state.get("logado"):
        _depois_de_entrar()
        return

    st.html("<style>header[data-testid='stHeader']{display:none}"
            "[data-testid='stMainBlockContainer']{padding-top:6vh}</style>")
    t = theme.tokens()
    esq, _, dir_ = st.columns([1.3, 0.08, 0.82], vertical_alignment="center")
    with esq:
        st.html(f"<div class='ps-login-brand'>{ui.marca_html()}</div>"
                "<h1 class='ps-login-h1'>Inteligência de mercado para <em>decisões de preço</em>.</h1>"
                "<p class='ps-login-p'>Concorrência, encartes, moda de mercado e projeções no mesmo painel, "
                "a partir das bases que a equipe já usa.</p>")
        _grafico_mercado()
        pills = [(t["primary"], "Moda de mercado"), (t["up"], "Índice de competitividade"),
                 (t["amber"], "Validação de encartes"), (t["muted"], "Relatórios da equipe")]
        st.html("<div class='ps-login-pills'>" + "".join(f"<span><i style='background:{c}'></i>{ui.esc(n)}</span>" for c, n in pills) + "</div>")
    with dir_:
        with st.container(border=True, key="psc_login"):
            aviso = st.session_state.pop("_flash_login", None)
            if aviso:
                st.success(aviso, icon=":material/check_circle:")
            if st.session_state.get("modo_login") == "cadastro":
                _form_cadastro()
            else:
                _form_entrar()
