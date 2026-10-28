"""Componentes de interface reutilizáveis."""
from __future__ import annotations

import base64
import html
import json
from datetime import date, datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from core import state
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
def cabecalho(titulo: str, descricao: str | None = None) -> None:
    esq, dir_ = st.columns([1, 0.36], vertical_alignment="bottom")
    with esq:
        desc = f"<p>{esc(descricao)}</p>" if descricao else ""
        st.html(f"<div class='ps-head'><h1>{esc(titulo)}</h1>{desc}</div>")
    with dir_:
        _area_usuario()


def secao(titulo: str, descricao: str | None = None) -> None:
    desc = f"<p>{esc(descricao)}</p>" if descricao else ""
    st.html(f"<div class='ps-sec'><h2>{esc(titulo)}</h2>{desc}</div>")


def avatar_html(tamanho: int = 44) -> str:
    foto = st.session_state.get("foto_perfil")
    estilo = f"width:{tamanho}px;height:{tamanho}px"
    if foto:
        return f"<img class='ps-avatar' style='{estilo}' src='data:image/jpeg;base64,{foto}' alt=''>"
    inicial = esc((st.session_state.get("usuario_logado") or "U")[:1].upper())
    return f"<div class='ps-avatar' style='{estilo}'>{inicial}</div>"


def _area_usuario() -> None:
    with st.container(horizontal=True, horizontal_alignment="right", vertical_alignment="center", gap="small"):
        escuro = theme.modo() == "Dark"
        if st.button("Claro" if escuro else "Escuro", icon=":material/light_mode:" if escuro else ":material/dark_mode:",
                     type="tertiary", key="tema_toggle", help="Alternar tema"):
            st.session_state.tema = "Light" if escuro else "Dark"
            st.rerun()
        with st.popover(state.primeiro_nome(), icon=":material/account_circle:"):
            cargo = st.session_state.get("usuario_cargo") or st.session_state.get("usuario_login")
            st.html(f"<div class='ps-user'>{avatar_html()}<div><b>{esc(st.session_state.get('usuario_logado', ''))}</b>"
                    f"<span>{esc(cargo or '')}</span></div></div>")
            paginas = state.paginas()
            if "perfil" in paginas:
                st.page_link(paginas["perfil"], label="Meu perfil", icon=":material/person:")
            if "sair" in paginas:
                st.page_link(paginas["sair"], label="Sair", icon=":material/logout:")


def vazio(titulo: str, texto: str) -> None:
    st.html(f"<div class='ps-empty'><h3>{esc(titulo)}</h3><p>{esc(texto)}</p></div>")


# ---------------------------------------------------------------- etiquetas
def _preco_html(valor: float, sufixo: str = "") -> str:
    texto = formatar_brl(valor, prefixo=False)
    inteiro, dec = texto.rsplit(",", 1)
    suf = f"<span class='suf'>{esc(sufixo)}</span>" if sufixo else ""
    return (f"<div class='ps-price' aria-label='R$ {esc(texto)}'><span class='cur'>R$</span>"
            f"<span>{esc(inteiro)}</span><span class='dec'>,{esc(dec)}</span>{suf}</div>")


def etiqueta(rotulo: str, valor, tipo: str = "preco", tom: str = "neutro", nota: str = "") -> str:
    """Etiqueta de gôndola. tipo: preco | numero | pct. tom: neutro | primary | promo | alert | ok."""
    if tipo == "preco":
        corpo = _preco_html(float(valor or 0))
    elif tipo == "pct":
        corpo = f"<div class='ps-price'><span>{esc(f'{float(valor):.1f}'.replace('.', ','))}</span><span class='suf'>%</span></div>"
    else:
        num = numero(valor)
        corpo = f"<div class='ps-price'><span>{esc(num)}</span></div>"
    classe = "" if tom == "neutro" else f" t-{tom}"
    nota_html = f"<div class='ps-tag-note'>{nota}</div>" if nota else ""
    return (f"<div class='ps-tag{classe}'><div class='ps-tag-label'>{esc(rotulo)}</div>"
            f"<div>{corpo}{nota_html}</div></div>")


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


def letreiro(itens: list[dict]) -> None:
    if not itens:
        return
    blocos = "".join(
        f"<span class='ps-ticker-item'><b>{esc(i['empresa'])}</b>"
        f"<small>varejo</small><span class='v'>{esc(formatar_brl(i['varejo']))}</span>"
        f"<small>atacado</small><span class='a'>{esc(formatar_brl(i['atacado'])) if i['atacado'] and i['atacado'] > 0 else '-'}</span></span>"
        for i in itens
    )
    duracao = max(30, len(itens) * 7)
    st.html(f"<div class='ps-ticker' aria-label='Menor preço recente por concorrente'>"
            f"<div class='ps-ticker-track' style='--dur:{duracao}s'>{blocos}{blocos}</div></div>")


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


def relatorio_html(conteudo: str, altura: int) -> None:
    """Exibe um relatório HTML isolado num iframe sem acesso ao app (sandbox sem same-origin)."""
    t = theme.tokens()
    srcdoc = html.escape(conteudo, quote=True)
    components.html(
        f"<!doctype html><html><head><style>html,body{{margin:0;height:100%;background:transparent}}"
        f"iframe{{display:block;width:100%;height:100%;border:1px solid {t['line']};border-radius:10px;background:#fff}}</style></head>"
        f"<body><iframe title='Relatório' sandbox='allow-scripts allow-popups allow-popups-to-escape-sandbox allow-downloads allow-modals allow-forms' "
        f"srcdoc=\"{srcdoc}\"></iframe></body></html>",
        height=altura, scrolling=False,
    )
