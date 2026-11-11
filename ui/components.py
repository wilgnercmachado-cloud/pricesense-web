"""Componentes de interface reutilizáveis."""
from __future__ import annotations

import base64
import html
import json
from datetime import date, datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from core.market_engine import formatar_brl
from ui import theme

def esc(valor) -> str:
    """Escapa qualquer valor para HTML (números e vazios inclusive; o banco pode devolver int ou None)."""
    return "" if valor is None else html.escape(str(valor))


ASSETS = Path(__file__).resolve().parent.parent / "assets"
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]
DIAS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]


# ---------------------------------------------------------------- formatação
def data_extenso(d: date | None = None) -> str:
    d = d or date.today()
    return f"{DIAS[d.weekday()].capitalize()}, {d.day} de {MESES[d.month - 1]} de {d.year}"


def data_curta(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(str(iso).replace("Z", "+00:00")).strftime("%d/%m/%Y")
    except ValueError:
        return str(iso)[:10]


def gaveta_topo(titulo: str, subtitulo: str = "") -> None:
    """Cabeçalho de gaveta lateral (o popover vira um painel à direita com o fundo desfocado)."""
    st.html(f"<div class='ps-gaveta'><div><b>{esc(titulo)}</b><span>{esc(subtitulo)}</span></div>"
            f"<button class='ps-gaveta-x' title='Fechar' aria-label='Fechar'>✕</button></div>")


def data_hora(iso: str | None) -> str:
    """dd/mm/aaaa às hh:mm, no horário de Brasília/Bahia."""
    if not iso:
        return ""
    try:
        from zoneinfo import ZoneInfo
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        if d.tzinfo:
            d = d.astimezone(ZoneInfo("America/Bahia"))
        return d.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        return str(iso)[:16].replace("T", " ")


def numero(n) -> str:
    return f"{int(n or 0):,}".replace(",", ".")


def tamanho_legivel(n: int | None) -> str:
    n = int(n or 0)
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.1f} MB".replace(".", ",")
    return f"{max(1, round(n / 1024))} KB"


def marca_html() -> str:
    svg = (ASSETS / f"marca_{'dark' if theme.escuro() else 'light'}.svg").read_bytes()
    return f"<img alt='' src='data:image/svg+xml;base64,{base64.b64encode(svg).decode()}'><span>PriceSense</span>"


# ---------------------------------------------------------------- estrutura de página
def cabecalho(titulo: str, descricao: str | None = None, extra_html: str = "") -> None:
    desc = f"<p>{esc(descricao)}</p>" if descricao else ""
    st.html(f"<div class='ps-head'><h1>{esc(titulo)}</h1>{desc}{extra_html}</div>")


def secao(titulo: str, descricao: str | None = None) -> None:
    desc = f"<p>{esc(descricao)}</p>" if descricao else ""
    st.html(f"<div class='ps-sec'><h2>{esc(titulo)}</h2>{desc}</div>")


def avatar_html(tamanho: int = 52) -> str:
    foto = st.session_state.get("foto_perfil")
    estilo = f"width:{tamanho}px;height:{tamanho}px"
    if foto:
        return f"<img class='ps-avatar' style='{estilo}' src='data:image/jpeg;base64,{foto}' alt=''>"
    inicial = esc((st.session_state.get("usuario_logado") or "U")[:1].upper())
    return f"<div class='ps-avatar' style='{estilo}'>{inicial}</div>"


@st.cache_data(show_spinner=False, max_entries=64)
def _miniatura_avatar(b64: str) -> str:
    """Foto do perfil reduzida para o círculo do menu (96 px, leve)."""
    import base64
    import io
    from PIL import Image
    try:
        img = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGB")
        lado = min(img.size); x0, y0 = (img.width - lado) // 2, (img.height - lado) // 2
        img = img.crop((x0, y0, x0 + lado, y0 + lado)).resize((96, 96))
        buf = io.BytesIO(); img.save(buf, "JPEG", quality=82)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ""


def avatar_no_menu(nome_curto: str, nome: str, foto_b64: str) -> None:
    """No lugar do nome, no menu do topo: a foto do usuário num círculo com luz neon (sem foto, as iniciais).
    O script do menu lê esta marca e monta o círculo; o menu Meu perfil continua abrindo ao passar o mouse."""
    ini = "".join(p[0] for p in (nome or nome_curto or "?").split()[:2]).upper()
    foto = _miniatura_avatar(foto_b64) if foto_b64 else ""
    st.html(f"<div id='ps-conta-dados' hidden data-nome='{esc(nome_curto)}' data-completo='{esc(nome)}' data-ini='{esc(ini)}' data-foto='{foto}'></div>")


def vazio(titulo: str, texto: str) -> None:
    st.html(f"<div class='ps-empty'><h3>{esc(titulo)}</h3><p>{esc(texto)}</p></div>")


# ---------------------------------------------------------------- etiquetas
def sparkline(valores: list[float], cor: str, altura: int = 34) -> str:
    vals = [float(v) for v in valores if v is not None]
    if len(vals) < 2:
        return ""
    lo, hi = min(vals), max(vals)
    faixa = (hi - lo) or 1.0
    n = len(vals) - 1
    pts = [(round(100 * i / n, 2), round(2 + (altura - 4) * (1 - (v - lo) / faixa), 2)) for i, v in enumerate(vals)]
    linha = " ".join(f"{x},{y}" for x, y in pts)
    gid = f"sg{abs(hash((tuple(vals), cor))) % 10**8}"
    svg = (f"<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 {altura}' preserveAspectRatio='none'>"
            f"<defs><linearGradient id='{gid}' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='{cor}' stop-opacity='.35'/>"
            f"<stop offset='1' stop-color='{cor}' stop-opacity='0'/></linearGradient></defs>"
            f"<polygon points='0,{altura} {linha} 100,{altura}' fill='url(#{gid})'/>"
            f"<polyline points='{linha}' fill='none' stroke='{cor}' stroke-width='1.6' vector-effect='non-scaling-stroke' stroke-linejoin='round'/>"
            f"</svg>")
    # st.html remove <svg> embutido; como imagem, o SVG é preservado.
    return f"<img class='ps-spark' alt='' src='data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}'>"


def variacao_html(pct: float | None, inverter: bool = False) -> str:
    if pct is None:
        return ""
    if abs(pct) < 0.05:
        return "<span class='ps-d flat'>0,0%</span>"
    subiu = pct > 0
    bom = subiu != inverter
    seta = "▲" if subiu else "▼"
    return f"<span class='ps-d {'up' if bom else 'down'}'>{seta} {f'{abs(pct):.1f}'.replace('.', ',')}%</span>"


def etiqueta(rotulo: str, valor, tipo: str = "preco", tom: str = "neutro", nota: str = "",
             serie: list[float] | None = None, variacao: float | None = None, inverter: bool = False) -> str:
    """Card de cotação. tipo: preco | numero | pct | indice. tom: neutro | primary | promo | alert | ok."""
    if tipo == "preco":
        corpo = f"<small>R$</small>{esc(formatar_brl(float(valor or 0), prefixo=False))}"
    elif tipo in ("pct", "indice"):
        corpo = esc(f"{float(valor or 0):.1f}".replace(".", ",")) + ("<small>%</small>" if tipo == "pct" else "")
    else:
        corpo = esc(numero(valor))
    t = theme.tokens()
    cor = {"primary": t["primary"], "promo": t["amber"], "alert": t["down"], "ok": t["up"]}.get(tom, t["muted"])
    spark = sparkline(serie, cor) if serie else ""
    nota_html = f"<div class='ps-q-n'>{nota}</div>" if nota else ""
    return (f"<div class='ps-q t-{tom}'><div class='ps-q-top'><div class='ps-q-l'>{esc(rotulo)}</div>{variacao_html(variacao, inverter)}</div>"
            f"<div class='ps-q-v'>{corpo}</div>{nota_html}{spark}</div>")


def etiquetas(itens: list[str]) -> None:
    st.html(f"<div class='ps-tags'>{''.join(itens)}</div>")


def barra_validacao(validos: int, criticos: int) -> None:
    total = max(validos + criticos, 1)
    pct = 100 * criticos / total
    barras = ""
    if validos:
        barras += f"<span class='ok' style='flex:{validos}'></span>"
    if criticos:
        barras += f"<span class='alert' style='flex:{criticos}'></span>"
    st.html(
        f"<div class='ps-split' role='img' aria-label='{validos} válidos e {criticos} críticos'>"
        f"<div class='ps-split-bar'>{barras}</div><div class='ps-split-legend'>"
        f"<span><i style='background:var(--ps-ok)'></i>Válidos <b>{numero(validos)}</b></span>"
        f"<span><i style='background:var(--ps-alert)'></i>Críticos <b>{numero(criticos)}</b> ({f'{pct:.1f}'.replace('.', ',')}%)</span>"
        f"</div></div>"
    )


def letreiro(itens: list[dict], referencias: dict | None = None) -> None:
    """referencias: moda de cada produto; cada cotação é comparada à moda do próprio produto."""
    if not itens:
        return
    blocos = ""
    for i in itens:
        var = ""
        referencia = (referencias or {}).get(i.get("produto"))
        if referencia:
            pct = 100 * (float(i["varejo"]) - referencia) / referencia
            var = (f"<span class='{'down' if pct > 0 else 'up'}'>{'▲' if pct > 0 else '▼'} {f'{abs(pct):.1f}'.replace('.', ',')}%</span>"
                   if abs(pct) >= 0.05 else "<span class='a'>=</span>")
        atac = esc(formatar_brl(i['atacado'])) if i['atacado'] and i['atacado'] > 0 else '-'
        blocos += (f"<span class='ps-ticker-item'><b>{esc(i['empresa'])}</b><span class='v'>{esc(formatar_brl(i['varejo']))}</span>"
                   f"{var}<small>atacado</small><span class='a'>{atac}</span></span>")
    duracao = max(30, len(itens) * 7)
    st.html(f"<div class='ps-ticker' aria-label='Menor preço recente por concorrente, comparado à moda de mercado'>"
            f"<div class='ps-ticker-track' style='--dur:{duracao}s'>{blocos}{blocos}</div></div>")


def ranking(linhas: list[tuple[str, float, str]]) -> None:
    """linhas: (rótulo, valor, html extra à direita)."""
    if not linhas:
        return
    maximo = max(v for _, v, _ in linhas) or 1
    html_ = "".join(f"<div class='ps-rank-row'><span title='{esc(r)}'>{esc(r)}</span><div class='bar'><i style='width:{100 * v / maximo:.1f}%'></i></div>"
                    f"<div><b>{esc(formatar_brl(v))}</b>{extra}</div></div>" for r, v, extra in linhas)
    st.html(f"<div class='ps-rank'>{html_}</div>")


# ---------------------------------------------------------------- ações com JavaScript
def botao_copiar(texto: str | None = None, rotulo: str = "Copiar", feito: str = "Copiado",
                 link_param: tuple[str, str] | None = None, altura: int = 40) -> None:
    """Copia texto (ou o link da página com um parâmetro) para a área de transferência."""
    t = theme.tokens()
    if link_param:
        chave, valor = link_param
        acao = (f"const u=new URL(window.parent.location.href);u.search='';"
                f"u.searchParams.set({json.dumps(chave)},{json.dumps(valor)});const t=u.toString();")
    else:
        b64 = base64.b64encode((texto or "").encode("utf-8")).decode("ascii")
        acao = (f"const bin=atob('{b64}');const bytes=Uint8Array.from(bin,c=>c.charCodeAt(0));"
                f"const t=new TextDecoder('utf-8').decode(bytes);")
    components.html(f"""
<style>
body{{margin:0;background:transparent;font-family:'Archivo','Helvetica Neue',Arial,sans-serif}}
button{{width:100%;height:{altura}px;border-radius:8px;border:1px solid {t['line']};background:{t['surface_solid']};
color:{t['ink']};font:500 14px 'Archivo','Helvetica Neue',Arial,sans-serif;cursor:pointer;transition:background .15s,border-color .15s}}
button:hover{{border-color:{t['primary']};color:{t['primary']}}}
button.ok{{background:{t['ok']};border-color:{t['ok']};color:#fff}}
button:focus-visible{{outline:2px solid {t['primary']};outline-offset:2px}}
</style>
<button id="b" type="button">{esc(rotulo)}</button>
<script>
const b=document.getElementById('b');
b.addEventListener('click',async()=>{{
  try{{ {acao} await navigator.clipboard.writeText(t); b.textContent={json.dumps(feito)}; b.classList.add('ok'); }}
  catch(e){{ b.textContent='Não foi possível copiar'; }}
  setTimeout(()=>{{ b.textContent={json.dumps(rotulo)}; b.classList.remove('ok'); }},2400);
}});
</script>""", height=altura + 4)


def habilitar_tab_em_textarea() -> None:
    """Permite usar TAB dentro das caixas de texto (colagem de colunas)."""
    components.html("""
<script>
const doc = window.parent.document;
function ligar(){
  doc.querySelectorAll('textarea').forEach(ta => {
    if (ta.dataset.tabListener) return;
    ta.addEventListener('keydown', function(e){
      if (e.key !== 'Tab' || e.shiftKey) return;
      e.preventDefault();
      const s = this.selectionStart, f = this.selectionEnd;
      const setter = Object.getOwnPropertyDescriptor(window.parent.HTMLTextAreaElement.prototype, 'value').set;
      setter.call(this, this.value.substring(0, s) + '\\t' + this.value.substring(f));
      this.selectionStart = this.selectionEnd = s + 1;
      this.dispatchEvent(new Event('input', { bubbles: true }));
    });
    ta.dataset.tabListener = "1";
  });
}
ligar(); setInterval(ligar, 800);
</script>""", height=0, width=0)


def relatorio_html(gz: bytes | None = None, altura: int = 860, nome_arquivo: str | None = None, barra: bool = True,
                   links: list[str] | None = None) -> None:
    """Exibe um relatório HTML (gzip ou texto puro).

    Com `links`, o navegador baixa as partes direto do Supabase (nada passa pelo servidor do Streamlit).
    Com `gz`, o conteúdo vai embutido (usado na pré-visualização). O navegador descompacta.
    O relatório roda num iframe com sandbox sem same-origin: scripts funcionam, mas não acessam o app.
    `nome_arquivo` habilita o botão de download (só administradores recebem esse parâmetro).
    """
    t = theme.tokens()
    b64 = base64.b64encode(gz).decode("ascii") if gz is not None else ""
    alt_barra = 48 if barra else 0
    download = "<button id='dl' type='button' disabled>Baixar HTML</button>" if nome_arquivo else ""
    barra_html = (f"<div class='bar'><span id='info'>Abrindo o relatório</span><div class='acoes'>{download}"
                  f"<button id='fs' type='button' disabled title='Tela cheia (Esc para sair)'>Tela cheia</button></div></div>"
                  if barra else "")
    components.html(f"""<!doctype html><html><head><meta charset="utf-8"><style>
html,body{{margin:0;height:100%;background:transparent;font:14px 'Archivo','Helvetica Neue',Arial,sans-serif;color:{t['ink']}}}
.bar{{height:{alt_barra}px;display:flex;align-items:center;justify-content:space-between;gap:12px}}
.bar span{{color:{t['muted']};font-size:13px}}
.acoes{{display:flex;gap:8px}}
button{{height:38px;padding:0 16px;border-radius:8px;border:1px solid {t['line']};background:{t['surface_solid']};color:{t['ink']};
font:500 14px 'Archivo','Helvetica Neue',Arial,sans-serif;cursor:pointer}}
button:hover:not(:disabled){{border-color:{t['primary']};color:{t['primary']}}}
button:disabled{{opacity:.5;cursor:default}}
button:focus-visible{{outline:2px solid {t['primary']};outline-offset:2px}}
.box{{height:calc(100% - {alt_barra}px);border:1px solid {t['line']};border-radius:10px;overflow:hidden;background:#fff;position:relative}}
.box:fullscreen{{border:0;border-radius:0}}
.msg{{position:absolute;inset:0;display:grid;place-items:center;color:#5A6372;font-size:15px}}
iframe{{display:block;width:100%;height:100%;border:0}}
</style></head><body>
{barra_html}
<div class="box" id="box"><div class="msg" id="msg">Abrindo o relatório…</div>
<iframe id="f" title="Relatório" sandbox="allow-scripts allow-popups allow-popups-to-escape-sandbox allow-downloads allow-modals allow-forms"></iframe></div>
<script>
const B64 = "{b64}";
const LINKS = {json.dumps(links or [])};
async function obterBytes(msg) {{
  if (!LINKS.length) {{
    const bin = atob(B64), bytes = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return [bytes];
  }}
  const partes = [];
  for (let i = 0; i < LINKS.length; i++) {{
    const r = await fetch(LINKS[i]);
    if (!r.ok) throw new Error('falha ao baixar a parte ' + (i + 1) + ' (HTTP ' + r.status + ')');
    const total = +r.headers.get('content-length') || 0, leitor = r.body.getReader(), pedacos = [];
    let lido = 0;
    for (;;) {{
      const {{done, value}} = await leitor.read();
      if (done) break;
      pedacos.push(value); lido += value.length;
      const pct = total ? Math.round(100 * lido / total) + '%' : (lido / 1048576).toFixed(0) + ' MB';
      msg.textContent = 'Baixando o relatório' + (LINKS.length > 1 ? ' (parte ' + (i + 1) + ' de ' + LINKS.length + ')' : '') + ': ' + pct;
    }}
    partes.push(...pedacos);
  }}
  return partes;
}}
(async () => {{
  const msg = document.getElementById('msg'), info = document.getElementById('info');
  try {{
    const bruto = new Blob(await obterBytes(msg));
    const inicio = new Uint8Array(await bruto.slice(0, 2).arrayBuffer());
    let blob;
    if (inicio[0] === 0x1f && inicio[1] === 0x8b) {{
      msg.textContent = 'Descompactando';
      const stream = bruto.stream().pipeThrough(new DecompressionStream('gzip'));
      blob = new Blob([await new Response(stream).arrayBuffer()], {{type: 'text/html;charset=utf-8'}});
    }} else {{
      blob = new Blob([bruto], {{type: 'text/html;charset=utf-8'}});
    }}
    document.getElementById('f').srcdoc = await blob.text();
    msg.remove();
    const tam = blob.size >= 1048576 ? (blob.size / 1048576).toFixed(1).replace('.', ',') + ' MB'
                                      : Math.max(1, Math.round(blob.size / 1024)) + ' KB';
    if (info) info.textContent = 'Relatório de ' + tam;
    const fs = document.getElementById('fs');
    if (fs) {{
      if (document.fullscreenEnabled) {{
        fs.disabled = false;
        fs.onclick = () => document.getElementById('box').requestFullscreen().catch(() => {{}});
      }} else {{ fs.remove(); }}
    }}
    const dl = document.getElementById('dl');
    if (dl) {{
      dl.disabled = false;
      dl.onclick = () => {{
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob); a.download = {json.dumps(nome_arquivo or "relatorio.html")};
        document.body.appendChild(a); a.click(); setTimeout(() => {{ URL.revokeObjectURL(a.href); a.remove(); }}, 2000);
      }};
    }}
  }} catch (e) {{
    msg.textContent = 'Não foi possível abrir o relatório neste navegador: ' + e;
  }}
}})();
</script></body></html>""", height=altura + alt_barra, scrolling=False)


def menu_ao_passar_mouse() -> None:
    """Abre os menus do topo ao passar o mouse (só em dispositivos com mouse) e fecha ao sair."""
    components.html("""<script>
const d = window.parent.document, w = window.parent;
/* botão de tela cheia do site, ao lado do botão de tema (recriado a cada execução) */
{
  const velho = d.getElementById('ps-fs'); if (velho) velho.remove();
  const ab = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M8 3H5a2 2 0 0 0-2 2v3M16 3h3a2 2 0 0 1 2 2v3M8 21H5a2 2 0 0 1-2-2v-3M16 21h3a2 2 0 0 0 2-2v-3"/></svg>';
  const fe = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M8 3v3a2 2 0 0 1-2 2H3M21 8h-3a2 2 0 0 1-2-2V3M3 16h3a2 2 0 0 1 2 2v3M16 21v-3a2 2 0 0 1 2-2h3"/></svg>';
  const b = d.createElement('button'); b.id = 'ps-fs'; b.type = 'button';
  const marca = () => { const on = !!d.fullscreenElement; b.innerHTML = on ? fe : ab; b.title = on ? 'Sair da tela cheia' : 'Tela cheia'; b.setAttribute('aria-label', b.title); };
  b.addEventListener('click', () => { d.fullscreenElement ? d.exitFullscreen() : d.documentElement.requestFullscreen().catch(() => {}); });
  marca(); d.addEventListener('fullscreenchange', marca); (d.querySelector('.stApp') || d.body).appendChild(b);   /* dentro do .stApp: mesmo zoom dos outros botões do topo */
}
/* ilha dinâmica: a largura acompanha os itens do menu (medidos uma vez por mudança) */
{
  const ajustaIlha = () => { const nav = d.querySelector('[data-testid="stTopNav"]'); if (!nav) return;
    /* largura natural = soma dos itens clicáveis (Início, Ferramentas, ...), medidos direto, sem depender da estrutura interna */
    const els = [...nav.querySelectorAll('[data-testid="stTopNavLink"], [data-testid="stTopNavSection"]')].filter(e => e.getClientRects().length);
    if (!els.length) return;
    let alvo = els.reduce((a, e) => a + Math.ceil(e.getBoundingClientRect().width), 0) + 6 * (els.length - 1) + 26;
    const natural = alvo;
    /* nunca encosta na logo nem nos botões da direita (filtros, upload, tela cheia, tema) */
    const W = w.innerWidth, meio = W / 2;
    const logo = d.querySelector('[data-testid="stLogo"], [data-testid="stHeaderLogo"], header img');
    const esq = logo ? logo.getBoundingClientRect().right : 180;
    let dir = W;
    d.querySelectorAll('.st-key-ps_tema, #ps-fs, .st-key-ps_sino, [class*="st-key-reg_topo"], [class*="st-key-promo_topo"], [class*="st-key-mk_topo"]').forEach(el => {
      const r = el.getBoundingClientRect(); if (r.width > 0 && r.top < 70) dir = Math.min(dir, r.left); });
    const maximo = Math.max(120, 2 * Math.min(meio - esq, dir - meio) - 28);
    /* sem espaço: os botões da direita viram só ícones (compacto) antes de a ilha encolher; nada se sobrepõe */
    const b_ = d.body;
    if (natural > maximo && !b_.classList.contains('ps-topo-compacto')) { b_.classList.add('ps-topo-compacto'); return setTimeout(ajustaIlha, 60); }
    if (b_.classList.contains('ps-topo-compacto') && natural + 260 < maximo) b_.classList.remove('ps-topo-compacto');
    alvo = Math.min(alvo, maximo);
    const z = (nav.offsetWidth ? nav.getBoundingClientRect().width / nav.offsetWidth : 1) || 1;   /* zoom efetivo da ilha (do site ou do navegador) */     /* medidas na tela; a largura é aplicada antes do zoom do site */
    alvo = Math.round(alvo / z); const maxCss = Math.round(maximo / z);
    if (Math.abs((parseFloat(nav.style.width) || 0) - alvo) > 1) { nav.style.setProperty('width', alvo + 'px', 'important'); nav.style.setProperty('max-width', maxCss + 'px', 'important'); }
    nav.dataset.ilha = '1'; };
  /* o selo "Atualizado" nunca encosta na ilha: encolhe (só a data) e, se ainda faltar espaço, sai do topo */
  const ajustaSelo = () => { const nav = d.querySelector('[data-testid="stTopNav"]'), selo = d.querySelector('.ps-atualizado'); if (!nav || !selo) return;
    const b = d.body; b.classList.remove('ps-selo-curto', 'ps-selo-oculto');
    const livre = () => { const topo = selo.closest('[class*="st-key-reg_topo"]') || selo; return topo.getBoundingClientRect().left - nav.getBoundingClientRect().right; };
    if (livre() < 14) { b.classList.add('ps-selo-curto'); if (livre() < 14) b.classList.add('ps-selo-oculto'); } };
  if (!w.__psSelo) { w.__psSelo = true; w.addEventListener('resize', () => setTimeout(ajustaSelo, 120)); }
  let tentSelo = 0; const ts = setInterval(() => { ajustaSelo(); if (++tentSelo > 20) clearInterval(ts); }, 300);
  setTimeout(ajustaIlha, 60); setTimeout(ajustaIlha, 400);
  /* os botões de cada tela (filtros, upload...) chegam depois: confere sempre, para a ilha nunca ficar por baixo deles */
  if (w.__psIlhaTimer) w.clearInterval(w.__psIlhaTimer);
  w.__psIlhaTimer = w.setInterval(ajustaIlha, 700);
  if (!w.__psIlha) { w.__psIlha = true; w.addEventListener('resize', () => setTimeout(ajustaIlha, 60)); w.setInterval(ajustaIlha, 1000); }   /* confere sempre: troca de página, botões novos no topo, fonte carregada */
}
if (!d.__psGaveta) { d.__psGaveta = true;            /* botão ✕ das gavetas: fecha como o Esc */
  d.addEventListener('click', e => { if (e.target.closest('.ps-gaveta-x')) { e.preventDefault();
    d.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', code: 'Escape', keyCode: 27, bubbles: true })); setTimeout(() => d.body.click(), 30); } }, true); }
/* zoom do site (80%): menus suspensos, listas de opções e janelas abrem colados em quem os chamou.
   Em vez de supor como cada navegador calcula a posição com zoom, mede onde o menu ficou e onde está o botão/campo
   que o abriu, e corrige só a diferença (funciona em qualquer versão do Chrome, Edge ou Firefox). */
/* menu da conta: a foto do usuário num círculo com luz neon no lugar do nome */
{ /* reinstalado a cada carga do script (o anterior pode ter sido descartado junto com o quadro dele) */
  const montar = () => { const dados = d.getElementById('ps-conta-dados'); if (!dados) return;
    const nome = dados.dataset.nome || '', foto = dados.dataset.foto || '', ini = dados.dataset.ini || '?', completo = dados.dataset.completo || nome;
    const rotulo = x => { const p_ = x.querySelector('[data-testid="stMarkdownContainer"]'); return ((p_ ? p_.textContent : x.textContent) || '').trim(); };
    const sec = [...d.querySelectorAll('[data-testid="stTopNavSection"]')].find(x => x.querySelector('.ps-avatar') || rotulo(x) === nome);
    if (!sec) return;
    let av = sec.querySelector('.ps-avatar');
    const chave = foto ? foto.slice(-40) : 'ini:' + ini;
    if (!av) { av = d.createElement('span'); av.className = 'ps-avatar'; sec.insertBefore(av, sec.firstChild); sec.classList.add('ps-conta');
      av.style.cssText = 'width:22px;height:22px;min-width:22px;max-width:22px;max-height:22px;'; }
    if (av.dataset.chave !== chave) { av.dataset.chave = chave;
      av.innerHTML = foto ? `<img src="${foto}" alt="" style="width:22px;height:22px;border-radius:50%;object-fit:cover;display:block">` : `<b>${ini.replace(/[<>&"]/g, '')}</b>`; }
    sec.title = completo + ' · Meu perfil'; };
  if (w.__psAvatarObs) { try { w.__psAvatarObs.disconnect(); } catch (e) {} }
  if (w.__psAvatarTimer) w.clearInterval(w.__psAvatarTimer);
  w.__psAvatarObs = new w.MutationObserver(() => w.requestAnimationFrame(montar));
  w.__psAvatarObs.observe(d.body, { subtree: true, childList: true, attributes: true, attributeFilter: ['data-foto', 'data-nome'] });
  w.__psAvatarTimer = w.setInterval(montar, 1000); montar();
}
if (!d.__psZoomFix2) { d.__psZoomFix2 = true;
  const SEL = '[data-testid="stTopNavPopoverBody"], [data-testid="stPopoverBody"], [data-testid$="Dropdown"]';
  let ultimoMenu = null;   /* último item do menu do topo em que o mouse passou (vale para qualquer versão do Streamlit) */
  const NAV_ITEM = '[data-testid="stTopNavSection"], [data-testid="stTopNav"] [aria-haspopup], [data-testid="stTopNav"] [role="button"]';
  const marca = e => { const x = e.target.closest && e.target.closest(NAV_ITEM);
    if (x && x.getBoundingClientRect().top < 120) ultimoMenu = x.closest('[data-testid="stTopNavSection"]') || x; };
  d.addEventListener('mouseover', marca, true); d.addEventListener('click', marca, true);
  const ehMenuTopo = el => el.getAttribute('data-testid') === 'stTopNavPopoverBody' || (!el.closest('[data-testid="stTopNav"]') && !!el.querySelector('[data-testid="stTopNavLink"]'));
  const ancora = el => {
    const tid = el.getAttribute('data-testid') || '';
    if (ehMenuTopo(el)) { const aberto = [...d.querySelectorAll('[data-testid="stTopNavSection"], [data-testid="stTopNav"] [aria-expanded="true"]')]
        .find(x => x.getAttribute('aria-expanded') === 'true' || x.querySelector('[aria-expanded="true"]'));
      return ultimoMenu && ultimoMenu.isConnected ? ultimoMenu : aberto; }
    if (tid === 'stPopoverBody') { if (el.querySelector('.ps-gaveta')) return null; return [...d.querySelectorAll('[data-testid="stPopoverButton"]')].find(x => x.getAttribute('aria-expanded') === 'true'); }
    const ae = d.activeElement;
    const sel = ae && ae.closest ? (ae.closest('[data-baseweb="select"]') || ae.closest('[data-testid="stMultiSelect"], [data-testid="stSelectbox"]')) : null;   /* campo que abriu a lista */
    return sel || [...d.querySelectorAll('[data-baseweb="select"]')].find(x => x.querySelector('[aria-expanded="true"]'));
  };
  const lerTr = el => { const vx = parseFloat(el.style.getPropertyValue('--ps-zx')), vy = parseFloat(el.style.getPropertyValue('--ps-zy'));
    if (el.classList.contains('ps-zfix') && isFinite(vx) && isFinite(vy)) return [vx, vy];
    const m = (el.style.transform || '').match(/translate(?:3d)?\\(\\s*(-?[\\d.]+)px\\s*,\\s*(-?[\\d.]+)px/); return m ? [parseFloat(m[1]), parseFloat(m[2])] : null; };
  /* corrige com um deslocamento extra (propriedade CSS "translate", que soma com a posição que o Streamlit der),
     então funciona tanto se o Streamlit posicionar com transform quanto com left/top, em qualquer versão */
  const corrige = el => {
    const a = ancora(el); if (!a) return;
    const r = el.getBoundingClientRect(), b = a.getBoundingClientRect(), cw = parseFloat(w.getComputedStyle(el).width) || el.offsetWidth;
    if (!r.width || !cw) return;
    const s = r.width / cw;                                        // pixels de tela por pixel da página (o zoom real, seja qual for o navegador)
    const alvoX = Math.max(8, Math.min(b.left, w.innerWidth - r.width - 8));
    const abaixo = (r.top + r.bottom) / 2 >= (b.top + b.bottom) / 2 || ehMenuTopo(el);
    const alvoY = abaixo ? b.bottom + 6 : b.top - 6 - r.height;
    const dx = (alvoX - r.left) / s, dy = (alvoY - r.top) / s;
    if (Math.abs(dx) < 1.5 && Math.abs(dy) < 1.5) return;
    const ox = parseFloat(el.style.getPropertyValue('--ps-dx')) || 0, oy = parseFloat(el.style.getPropertyValue('--ps-dy')) || 0;
    el.style.setProperty('--ps-dx', (ox + dx).toFixed(1) + 'px'); el.style.setProperty('--ps-dy', (oy + dy).toFixed(1) + 'px');
    el.classList.add('ps-zoff');
  };
  const menusSoltos = () => { const out = new Set();
    d.querySelectorAll('[data-testid="stTopNavLink"]').forEach(l => { if (l.closest('[data-testid="stTopNav"]')) return;
      let e = l.parentElement; while (e && e !== d.body) { if ((e.style.transform || '').includes('translate')) { out.add(e); break; } e = e.parentElement; } });
    return out; };
  let pend = 0; const varre = () => { if (pend) return; pend = w.requestAnimationFrame(() => { pend = 0;
    const lista = new Set(d.querySelectorAll(SEL)); menusSoltos().forEach(x => lista.add(x)); lista.forEach(corrige); }); };
  new w.MutationObserver(varre).observe(d.body, { subtree: true, childList: true, attributes: true, attributeFilter: ['style', 'aria-expanded'] });
  w.addEventListener('resize', varre); varre();
}
/* Ctrl+V com o chat aberto: o print colado entra no campo de anexo do chat */
if (!d.__psColar) { d.__psColar = true;
  d.addEventListener('paste', e => {
    const corpo = [...d.querySelectorAll('[data-testid="stPopoverBody"]')].find(b => b.querySelector('.ps-chat-hd') && b.getClientRects().length);
    if (!corpo) return;
    const arqs = [...((e.clipboardData || {}).items || [])].filter(x => x.kind === 'file').map(x => x.getAsFile()).filter(Boolean);
    if (!arqs.length) return;
    const inp = corpo.querySelector('input[type="file"]'); if (!inp) return;
    e.preventDefault();
    const dt = new DataTransfer(), agora = new Date().toISOString().slice(0, 19).replace(/[-:T]/g, '');
    arqs.forEach((f, n) => { const ext = (f.type.split('/')[1] || 'png').replace('jpeg', 'jpg');
      dt.items.add(!f.name || f.name === 'image.png' ? new File([f], `print_${agora}${n ? '_' + n : ''}.${ext}`, { type: f.type }) : f); });
    inp.files = dt.files; inp.dispatchEvent(new Event('change', { bubbles: true }));
  }, true);
}
if (!d.__psHover && w.matchMedia('(hover: hover)').matches) {
  d.__psHover = true;
  let aberto = null, timer = null, abertoEm = 0;
  const estaAberto = b => b && b.getAttribute('aria-expanded') === 'true';
  const fechar = () => { if (estaAberto(aberto)) aberto.click(); aberto = null; };
  d.addEventListener('mouseover', e => {
    const alvo = e.target.closest ? e.target : e.target.parentElement;
    if (!alvo || !alvo.closest) return;
    const secao = alvo.closest('[data-testid="stTopNavSection"]');
    const painel = alvo.closest('[data-testid="stTopNavPopover"], [data-testid="stTopNavPopoverBody"]');
    if (secao) {
      clearTimeout(timer);
      if (aberto && aberto !== secao) fechar();
      if (!estaAberto(secao)) { secao.click(); abertoEm = Date.now(); }
      aberto = secao; return;
    }
    if (painel) { clearTimeout(timer); return; }
    if (aberto) { clearTimeout(timer); timer = setTimeout(fechar, 240); }
  });
  // Um clique logo depois de abrir pelo mouse não deve fechar o menu.
  d.addEventListener('click', e => {
    const secao = e.isTrusted && e.target.closest && e.target.closest('[data-testid="stTopNavSection"]');
    if (secao && secao === aberto && Date.now() - abertoEm < 700) { e.stopPropagation(); e.preventDefault(); }
  }, true);
}
</script>""", height=0, width=0)


_ICONES = {
    "link": "<path d='M10 13a5 5 0 0 0 7.07 0l3-3a5 5 0 0 0-7.07-7.07l-1.5 1.5'/><path d='M14 11a5 5 0 0 0-7.07 0l-3 3a5 5 0 0 0 7.07 7.07l1.5-1.5'/>",
    "baixar": "<path d='M12 3v12'/><path d='m7 10 5 5 5-5'/><path d='M5 21h14'/>",
    "tela": "<path d='M8 3H5a2 2 0 0 0-2 2v3'/><path d='M16 3h3a2 2 0 0 1 2 2v3'/><path d='M8 21H5a2 2 0 0 1-2-2v-3'/><path d='M16 21h3a2 2 0 0 0 2-2v-3'/>",
    "ok": "<path d='m5 12 5 5 9-10'/>",
}


def _icone(nome: str) -> str:
    return (f"<svg viewBox='0 0 24 24' fill='none' stroke='currentColor' stroke-width='2' stroke-linecap='round' "
            f"stroke-linejoin='round' aria-hidden='true'>{_ICONES[nome]}</svg>")


def acoes_relatorio(rid: str, links: list[str], nome_arquivo: str | None) -> None:
    """Copiar link, Baixar HTML (só para quem publica) e Tela cheia, no mesmo padrão dos botões do app."""
    t = theme.tokens()
    botoes = [f"<button id='cp' type='button'>{_icone('link')}<span>Copiar link</span></button>"]
    if nome_arquivo:
        botoes.append(f"<button id='dl' type='button'>{_icone('baixar')}<span>Baixar HTML</span></button>")
    botoes.append(f"<button id='fs' type='button' class='pri'>{_icone('tela')}<span>Tela cheia</span></button>")
    largura = 150 * len(botoes) + 8 * (len(botoes) - 1) + 4
    components.html(f"""<!doctype html><html><head><meta charset="utf-8"><style>
@import url('{theme.FONTE_URL}');
html,body{{margin:0;background:transparent;overflow:hidden}}
.row{{display:flex;gap:8px;padding:2px}}
button{{position:relative;overflow:hidden;isolation:isolate;flex:1;height:40px;display:inline-flex;align-items:center;justify-content:center;gap:8px;
  border-radius:.65rem;border:1px solid {t['line']};background:color-mix(in srgb,{t['surface_solid']} 70%,transparent);color:{t['ink']};
  font:550 14px 'Geist',-apple-system,sans-serif;cursor:pointer;box-shadow:0 1px 0 {t['highlight']} inset,0 6px 16px -12px rgba(15,23,42,.35);
  transition:transform .18s cubic-bezier(.2,.7,.2,1),box-shadow .22s ease,border-color .2s ease,color .2s ease}}
button svg{{width:16px;height:16px;flex:none}}
button::after{{content:"";position:absolute;inset:0;z-index:-1;pointer-events:none;
  background:linear-gradient(105deg,transparent 35%,rgba(255,255,255,.38) 50%,transparent 65%);transform:translateX(-130%);transition:transform .7s cubic-bezier(.2,.7,.2,1)}}
button:hover::after{{transform:translateX(130%)}}
button:hover{{transform:translateY(-1px);border-color:color-mix(in srgb,{t['primary']} 55%,transparent);color:{t['primary']};box-shadow:0 1px 0 {t['highlight']} inset,0 12px 26px -14px {t['primary']}}}
button:active{{transform:scale(.98)}}
button.pri{{background:linear-gradient(180deg,{t['primary_hover']},{t['primary']});color:#fff;border-color:color-mix(in srgb,{t['primary']} 70%,#fff);
  box-shadow:0 1px 0 rgba(255,255,255,.3) inset,0 10px 24px -12px {t['primary']}}}
button.pri:hover{{color:#fff;box-shadow:0 1px 0 rgba(255,255,255,.3) inset,0 16px 32px -12px {t['primary']}}}
button.ok{{background:{t['up']};border-color:{t['up']};color:#fff}}
button:focus-visible{{outline:2px solid {t['primary']};outline-offset:2px}}
button:disabled{{opacity:.6;cursor:progress}}
</style></head><body><div class="row">{''.join(botoes)}</div><script>
const LINKS = {json.dumps(links)}, NOME = {json.dumps(nome_arquivo or "")}, RID = {json.dumps(str(rid))};
const pai = window.parent.document;
function aviso(b, texto, ms) {{ const s = b.querySelector('span'), o = s.textContent; s.textContent = texto; b.classList.add('ok');
  setTimeout(() => {{ s.textContent = o; b.classList.remove('ok'); }}, ms || 2200); }}
document.getElementById('cp').onclick = async e => {{
  const b = e.currentTarget, u = new URL(window.parent.location.href); u.search = ''; u.searchParams.set('r', RID);
  try {{ await navigator.clipboard.writeText(u.toString()); aviso(b, 'Link copiado'); }} catch (_) {{ b.querySelector('span').textContent = 'Não foi possível copiar'; }}
}};
document.getElementById('fs').onclick = () => {{
  const alvo = pai.querySelector('.st-key-rel_quadro iframe');
  if (alvo && alvo.requestFullscreen) alvo.requestFullscreen().catch(() => {{}});
}};
const dl = document.getElementById('dl');
if (dl) dl.onclick = async () => {{
  const s = dl.querySelector('span'), o = s.textContent; dl.disabled = true;
  try {{
    const partes = [];
    for (let i = 0; i < LINKS.length; i++) {{ s.textContent = 'Baixando ' + Math.round(100 * i / LINKS.length) + '%';
      const r = await fetch(LINKS[i]); if (!r.ok) throw new Error(r.status); partes.push(await r.arrayBuffer()); }}
    let blob = new Blob(partes); const ini = new Uint8Array(await blob.slice(0, 2).arrayBuffer());
    if (ini[0] === 0x1f && ini[1] === 0x8b) blob = await new Response(blob.stream().pipeThrough(new DecompressionStream('gzip'))).blob();
    const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([blob], {{type: 'text/html'}})); a.download = NOME;
    document.body.appendChild(a); a.click(); setTimeout(() => {{ URL.revokeObjectURL(a.href); a.remove(); }}, 3000);
    dl.disabled = false; s.textContent = o; aviso(dl, 'Download iniciado');
  }} catch (err) {{ dl.disabled = false; s.textContent = 'Falha no download'; setTimeout(() => s.textContent = o, 2500); }}
}};
</script></body></html>""", height=46, width=largura)




def pasta_telas() -> str:
    """Pasta das telas HTML (Início, PriceMetrics, Metrics Promo, PriceBot, Pesquisa de Mercado).

    O arquivo tem nome único, ui/metrics_comp/pricesense_telas.html, e é copiado como index.html para uma pasta temporária:
    assim, subir por engano outro "index.html" no GitHub nunca mais troca as telas do site.
    """
    import shutil
    import tempfile
    from pathlib import Path as _P
    origem = _P(__file__).resolve().parent / "metrics_comp"
    fonte = origem / "pricesense_telas.html"
    if not fonte.exists():
        return str(origem)                                   # versão antiga do repositório: usa o index.html que estiver lá
    destino = _P(tempfile.gettempdir()) / "pricesense_telas"
    destino.mkdir(parents=True, exist_ok=True)
    alvo = destino / "index.html"
    if not alvo.exists() or alvo.stat().st_size != fonte.stat().st_size or alvo.stat().st_mtime < fonte.stat().st_mtime:
        shutil.copyfile(fonte, alvo)
    for extra in ("xlsx.mini.min.js", "LICENSE-sheetjs.txt"):
        if (origem / extra).exists() and not (destino / extra).exists():
            shutil.copyfile(origem / extra, destino / extra)
    return str(destino)
