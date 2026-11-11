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


def _fundo() -> None:
    """Fundo vivo da entrada: uma rede de mercado (lojas e concorrentes) com pulsos de preço correndo entre os pontos."""
    t = theme.tokens()
    cores = {"p": t["primary"], "u": t["up"], "d": t["down"], "f": t["faint"]}
    with st.container(key="ps_login_bg"):
        components.html(f"""<!doctype html><html><head><meta charset="utf-8"><style>html,body{{margin:0;height:100%;background:transparent;overflow:hidden}}
canvas{{display:block;width:100%;height:100%}}</style></head><body><canvas id="c"></canvas><script>
const C = {json.dumps(cores)}, cv = document.getElementById('c'), ctx = cv.getContext('2d');
let W = 0, H = 0, N = [], L = [], pulsos = [];
const reduzir = matchMedia('(prefers-reduced-motion: reduce)').matches;
function ajustar() {{ const d = devicePixelRatio || 1; W = innerWidth; H = innerHeight; cv.width = W * d; cv.height = H * d; ctx.setTransform(d, 0, 0, d, 0, 0);
  const q = Math.round(W * H / 26000); N = [];
  for (let i = 0; i < q; i++) N.push({{ x: Math.random() * W, y: Math.random() * H, vx: (Math.random() - .5) * .18, vy: (Math.random() - .5) * .18,
    r: Math.random() < .12 ? 2.6 : 1.4, c: Math.random() < .15 ? C.u : Math.random() < .1 ? C.d : C.p }}); }}
const hexA = (h, a) => h + Math.round(a * 255).toString(16).padStart(2, '0');
function quadro() {{
  ctx.clearRect(0, 0, W, H);
  for (const n of N) {{ n.x += n.vx; n.y += n.vy; if (n.x < 0 || n.x > W) n.vx *= -1; if (n.y < 0 || n.y > H) n.vy *= -1; }}
  L = [];
  for (let i = 0; i < N.length; i++) for (let j = i + 1; j < N.length; j++) {{ const dx = N[i].x - N[j].x, dy = N[i].y - N[j].y, d = dx * dx + dy * dy;
    if (d < 17000) {{ const a = 1 - d / 17000; L.push([i, j]); ctx.strokeStyle = hexA(C.p, .16 * a); ctx.lineWidth = 1; ctx.beginPath(); ctx.moveTo(N[i].x, N[i].y); ctx.lineTo(N[j].x, N[j].y); ctx.stroke(); }} }}
  if (L.length && Math.random() < .06 && pulsos.length < 14) {{ const [a, b] = L[Math.floor(Math.random() * L.length)]; pulsos.push({{ a, b, t: 0, c: Math.random() < .5 ? C.u : C.p }}); }}
  pulsos = pulsos.filter(p => (p.t += .018) < 1);
  for (const p of pulsos) {{ const A = N[p.a], B = N[p.b], x = A.x + (B.x - A.x) * p.t, y = A.y + (B.y - A.y) * p.t;
    const g = ctx.createRadialGradient(x, y, 0, x, y, 9); g.addColorStop(0, hexA(p.c, .9)); g.addColorStop(1, hexA(p.c, 0)); ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, 9, 0, 7); ctx.fill(); }}
  for (const n of N) {{ ctx.fillStyle = hexA(n.c, n.r > 2 ? .85 : .5); ctx.beginPath(); ctx.arc(n.x, n.y, n.r, 0, 7); ctx.fill();
    if (n.r > 2) {{ ctx.strokeStyle = hexA(n.c, .25); ctx.beginPath(); ctx.arc(n.x, n.y, 6, 0, 7); ctx.stroke(); }} }}
  if (!reduzir) requestAnimationFrame(quadro);
}}
ajustar(); addEventListener('resize', ajustar); quadro();
</script></body></html>""", height=10)


def _lembrado() -> dict | None:
    """Usuário que já entrou neste computador (cookie guardado no navegador depois do login)."""
    if st.session_state.get("_esquecer_lembrado"):
        return None
    try:
        login = (st.context.cookies or {}).get("ps_usuario")
    except Exception:
        login = None
    if not login:
        return None
    try:
        from core import db
        u = db.buscar_usuario(login)
    except Exception:
        u = None
    return u if u and str(u.get("status")) == "Aprovado" else None


def gravar_lembranca(login: str) -> None:
    """Depois do login, guarda o usuário no navegador (1 ano) para a entrada mostrar a foto e o nome na próxima vez."""
    if st.session_state.get("_cookie_gravado") == login:
        return
    st.session_state._cookie_gravado = login
    components.html(f"<script>try{{parent.document.cookie='ps_usuario={login};path=/;max-age=31536000;SameSite=Lax'}}catch(e){{}}</script>", height=0)


def _saudacao() -> str:
    import datetime as _dt
    h = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=-3))).hour
    return "Bom dia" if 5 <= h < 12 else "Boa tarde" if 12 <= h < 18 else "Boa noite"


def _depois_de_entrar() -> None:
    paginas = state.paginas()
    pendente = st.session_state.pop("pending_report", None)
    if pendente and "biblioteca" in paginas:
        st.switch_page(paginas["biblioteca"], query_params={"r": pendente})
    if "inicio" in paginas:
        st.switch_page(paginas["inicio"])


def _form_entrar() -> None:
    lemb = _lembrado()
    if lemb:
        nome = str(lemb.get("nome") or lemb["usuario"]).split()[0]
        foto = ui._miniatura_avatar(lemb.get("foto_perfil")) if lemb.get("foto_perfil") else ""
        ini = "".join(p[0] for p in str(lemb.get("nome") or lemb["usuario"]).split()[:2]).upper()
        av = f"<img src='{foto}' alt=''>" if foto else f"<b>{ui.esc(ini)}</b>"
        st.html(f"<div class='ps-login-ola'><div class='ps-login-av'>{av}</div>"
                f"<h2>{_saudacao()}, {ui.esc(nome)}</h2><p class='sub'>Que bom te ver de novo. Digite a sua senha para continuar.</p></div>")
    else:
        st.html(f"<div class='ps-login-ola'><div class='ps-login-av marca'>{ui.marca_html()}</div><h2>{_saudacao()}</h2>"
                "<p class='sub'>Entre com o usuário e a senha cadastrados.</p></div>")
    with st.form("form_login", border=False):
        usuario = st.text_input("Usuário", value=(lemb or {}).get("usuario", ""), autocomplete="username")
        senha = st.text_input("Senha", type="password", autocomplete="current-password")
        enviar = st.form_submit_button("Entrar", type="primary", width="stretch", icon=":material/arrow_forward:")
    if enviar:
        ok, msg = auth.entrar(usuario, senha)
        if ok:
            st.session_state.pop("_esquecer_lembrado", None)
            st.rerun()
        st.error(msg, icon=":material/error:")
    c1, c2 = st.columns(2)
    if c1.button("Solicitar acesso", width="stretch", key="ir_cadastro", icon=":material/person_add:"):
        st.session_state.modo_login = "cadastro"
        st.rerun()
    if lemb and c2.button("Não é você?", width="stretch", key="trocar_usuario", icon=":material/switch_account:", type="tertiary"):
        st.session_state._esquecer_lembrado = True
        components.html("<script>try{parent.document.cookie='ps_usuario=;path=/;max-age=0'}catch(e){}</script>", height=0)
        st.rerun()


def _sugerir() -> None:
    """Ao digitar o nome, sugere o login (ex.: João da Costa Silva → joao.silva; se já existir, outra opção livre)."""
    ss = st.session_state
    ss.cad_sugestoes = auth.sugestoes_login(ss.get("cad_nome", ""))
    if ss.cad_sugestoes and not ss.get("cad_usuario_mexido"):
        ss.cad_usuario = ss.cad_sugestoes[0]


def _form_cadastro() -> None:
    ss = st.session_state
    st.html("<div class='ps-login-ola'><h2>Solicitar acesso</h2><p class='sub'>Um administrador aprova o cadastro e libera as ferramentas.</p></div>")
    st.text_input("Nome completo", placeholder="Ex.: João da Costa Silva", key="cad_nome", on_change=_sugerir)
    sug = ss.get("cad_sugestoes") or []
    c1, c2 = st.columns(2)
    c1.text_input("Usuário", placeholder="Ex.: joao.silva", key="cad_usuario", help="Sugerido pelo seu nome; pode trocar. Sem espaços nem acentos.",
                  on_change=lambda: ss.__setitem__("cad_usuario_mexido", True))
    if sug:
        st.html("<p class='ps-sug-t'>Disponíveis:</p>")
        cols = st.columns(len(sug[:4]))
        for k, (col, s_) in enumerate(zip(cols, sug[:4])):
            if col.button(s_, key=f"sug_login_{k}", width="stretch", type="secondary"):
                ss.cad_usuario = s_; ss.cad_usuario_mexido = True; st.rerun()
    with st.form("form_cadastro", border=False):
        matricula = c2.text_input("Matrícula", placeholder="Ex.: 123456", key="cad_matricula")
        cargo = st.text_input("Cargo", placeholder="Ex.: Comprador")
        c3, c4 = st.columns(2)
        senha = c3.text_input("Senha", type="password", help="Mínimo de 6 caracteres.")
        senha2 = c4.text_input("Confirmar senha", type="password")
        enviar = st.form_submit_button("Enviar solicitação", type="primary", width="stretch", icon=":material/send:")
    if enviar:
        ok, msg = auth.solicitar_acesso(ss.get("cad_nome", ""), ss.get("cad_usuario", ""), ss.get("cad_matricula", ""), cargo, senha, senha2)
        if ok:
            ss.modo_login = "login"
            ss._flash_login = msg
            for k in ("cad_nome", "cad_usuario", "cad_matricula", "cad_sugestoes", "cad_usuario_mexido"):
                ss.pop(k, None)
            st.rerun()
        st.error(msg, icon=":material/error:")
    if st.button("Voltar para o login", type="tertiary", icon=":material/arrow_back:", key="voltar_login"):
        ss.modo_login = "login"
        st.rerun()


def render() -> None:
    if st.session_state.get("logado"):
        _depois_de_entrar()
        return

    st.html("<style>header[data-testid='stHeader'],#ps-fs{display:none !important}"
            "[data-testid='stMainBlockContainer']{padding-top:5vh}</style>")
    _fundo()
    t = theme.tokens()
    esq, _, dir_ = st.columns([1.3, 0.08, 0.82], vertical_alignment="center")
    with esq:
        st.html(f"<div class='ps-login-brand'>{ui.marca_html()}<i class='ps-login-live'></i><small>ao vivo</small></div>"
                "<h1 class='ps-login-h1'>Inteligência de mercado para decisões de "
                "<span class='ps-rot'><span><em>preço</em><em>margem</em><em>competitividade</em><em>sortimento</em><em>preço</em></span></span>.</h1>"
                "<p class='ps-login-p'>Concorrência, encartes, moda de mercado e projeções no mesmo painel, "
                "a partir das bases que a equipe já usa.</p>")
        with st.container(key="ps_login_graf"):
            _grafico_mercado()
        pills = [(t["primary"], "Moda de mercado"), (t["up"], "Índice de competitividade"),
                 (t["amber"], "Validação de encartes"), (t["down"], "Optimus"), (t["muted"], "Relatórios da equipe")]
        st.html("<div class='ps-login-pills'>" + "".join(f"<span style='--c:{c}'><i></i>{ui.esc(n)}</span>" for c, n in pills) + "</div>")
    with dir_:
        with st.container(border=True, key="psc_login"):
            aviso = st.session_state.pop("_flash_login", None)
            if aviso:
                st.success(aviso, icon=":material/check_circle:")
            if st.session_state.get("modo_login") == "cadastro":
                _form_cadastro()
            else:
                _form_entrar()
