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

esc = html.escape
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


def numero(n) -> str:
    return f"{int(n or 0):,}".replace(",", ".")


def tamanho_legivel(n: int | None) -> str:
    n = int(n or 0)
    if n >= 1024 * 1024:
        return f"{n / 1024 / 1024:.1f} MB".replace(".", ",")
    return f"{max(1, round(n / 1024))} KB"


def marca_html() -> str:
    svg = (ASSETS / f"marca_{'dark' if theme.modo() == 'Dark' else 'light'}.svg").read_bytes()
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
button{{width:100%;height:{altura}px;border-radius:8px;border:1px solid {t['line']};background:{t['raised']};
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
button{{height:38px;padding:0 16px;border-radius:8px;border:1px solid {t['line']};background:{t['raised']};color:{t['ink']};
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
