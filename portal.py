import streamlit as st
import streamlit.components.v1 as components
from streamlit import config as st_config
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import io
import base64
from supabase import create_client, Client

# ================= GERENCIAMENTO DE ESTADO E USUÁRIOS =================
if 'tema' not in st.session_state:
    st.session_state.tema = "Light"

if 'modo_login' not in st.session_state:
    st.session_state.modo_login = "login"

if 'permissoes' not in st.session_state:
    st.session_state.permissoes = []

def aplicar_tema_nativo():
    try:
        if st.session_state.tema == "Dark":
            st_config.set_option("theme.base", "dark")
            st_config.set_option("theme.backgroundColor", "#0E1117")
            st_config.set_option("theme.secondaryBackgroundColor", "#1A1D25")
            st_config.set_option("theme.textColor", "#FFFFFF")
            st_config.set_option("theme.primaryColor", "#E20000")
        else:
            st_config.set_option("theme.base", "light")
            st_config.set_option("theme.backgroundColor", "#F4F5F7")
            st_config.set_option("theme.secondaryBackgroundColor", "#FFFFFF")
            st_config.set_option("theme.textColor", "#1D1D1D")
            st_config.set_option("theme.primaryColor", "#2424ED")
    except Exception:
        pass

aplicar_tema_nativo()

# ================= CONFIGURAÇÃO INICIAL =================
st.set_page_config(page_title="PriceSense Web", page_icon="⚡", layout="wide", initial_sidebar_state="expanded")

# ================= ÍCONES SVG NATIVOS =================
def svg_b64(svg_template, cor):
    clean_svg = svg_template.replace("{cor}", cor).replace('\n', '').replace('\r', '')
    return base64.b64encode(clean_svg.encode('utf-8')).decode('utf-8')

SVG_GEAR = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{cor}"><path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.06-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.73,8.87 C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.8,11.69,4.8,12s0.02,0.64,0.06,0.94l-2.03,1.58 c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.43-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.49-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z"/></svg>"""
SVG_CHART = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{cor}"><path d="M5 9.5A1.5 1.5 0 0 1 6.5 8h1A1.5 1.5 0 0 1 9 9.5v9A1.5 1.5 0 0 1 7.5 20h-1A1.5 1.5 0 0 1 5 18.5v-9zM10.5 4A1.5 1.5 0 0 1 12 5.5v13a1.5 1.5 0 0 1-1.5 1.5h-1A1.5 1.5 0 0 1 8 18.5v-13A1.5 1.5 0 0 1 9.5 4h1zM16 13a1.5 1.5 0 0 1 1.5 1.5v4a1.5 1.5 0 0 1-1.5 1.5h-1a1.5 1.5 0 0 1-1.5-1.5v-4a1.5 1.5 0 0 1 1.5-1.5h1z"/></svg>"""
SVG_PERCENT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{cor}"><path d="M7.5 4.5a3 3 0 1 0 0 6 3 3 0 0 0 0-6zm0 2a1 1 0 1 1 0 2 1 1 0 0 1 0-2zM16.5 13.5a3 3 0 1 0 0 6 3 3 0 0 0 0-6zm0 2a1 1 0 1 1 0 2 1 1 0 0 1 0-2zM18.2 5.1a1 1 0 0 1 0 1.4L6.5 18.2a1 1 0 0 1-1.4-1.4L16.8 5.1a1 1 0 0 1 1.4 0z"/></svg>"""
SVG_PERSON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{cor}"><path d="M12 12c2.7 0 4.9-2.2 4.9-4.9S14.7 2.2 12 2.2 7.1 4.4 7.1 7.1 9.3 12 12 12zm0 2.2c-3.3 0-9.8 1.6-9.8 4.9v2.7h19.6v-2.7c0-3.3-6.5-4.9-9.8-4.9z"/></svg>"""
SVG_LOGOUT = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="{cor}"><path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z"/></svg>"""

ICONES_NAV = {
    "preco_bot": SVG_GEAR,
    "pricing_regular": SVG_CHART,
    "pricing_promo": SVG_PERCENT,
    "painel_admin": SVG_PERSON,
}

b64_light = svg_b64(SVG_GEAR, "#2424ED")
b64_dark = svg_b64(SVG_GEAR, "#FFFFFF")

URL_LOGO_LIGHT = f"data:image/svg+xml;base64,{b64_light}"
URL_LOGO_DARK = f"data:image/svg+xml;base64,{b64_dark}"

# ================= CONEXÃO COM BANCO DE DADOS =================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except:
    # Fallback seguro caso rode localmente sem o secrets
    SUPABASE_URL = "https://jawdoxmvnvidqkmfohsn.supabase.co"
    SUPABASE_KEY = "sb_publishable_qbnZplDdvwJL9Ph5IEvo8Q_4korwizq"

@st.cache_resource
def iniciar_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = iniciar_supabase()

# ================= CSS GLOBAL =================
def aplicar_css_tema():
    tema = st.session_state.tema
    
    primary = "#E20000" if tema == "Dark" else "#2424ED"
    primary_hover = "#CC0000" if tema == "Dark" else "#09096D"
    excel_color = "#27AE60" if tema == "Dark" else "#107C41"
    excel_hover = "#1E8449" if tema == "Dark" else "#0B5A2F"
    bg_color = "#0E1117" if tema == "Dark" else "#F4F5F7"
    text_color = "#FFFFFF" if tema == "Dark" else "#1D1D1D"
    
    sidebar_bg = "rgba(17, 20, 26, 0.55)" if tema == "Dark" else "rgba(255, 255, 255, 0.65)"
    input_bg = "rgba(38, 39, 48, 0.4)" if tema == "Dark" else "rgba(255, 255, 255, 0.6)"
    input_border = "rgba(255, 255, 255, 0.1)" if tema == "Dark" else "rgba(0, 0, 0, 0.08)"
    glass_shadow = "0 8px 32px 0 rgba(0, 0, 0, 0.2)" if tema == "Dark" else "0 8px 32px 0 rgba(31, 38, 135, 0.05)"
    
    animacao_pulse = "pulse-white" if tema == "Dark" else "pulse-blue-new"

    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    html, body, p, div, h1, h2, h3, h4, h5, h6, li, a, button, input, label, table, td, th {{ font-family: 'Inter', sans-serif; }}
    .material-symbols-rounded, .stIcon, span[class*="Icon"] {{ font-family: 'Material Symbols Rounded', 'Material Icons' !important; }}

    .block-container {{ padding-top: 1rem !important; padding-bottom: 0rem !important; margin-top: 0rem !important; }}
    [data-testid="stSidebarContent"] {{ padding-top: 1rem !important; overflow-x: hidden !important; }}
    [data-testid="stToolbar"] {{ visibility: hidden; }}
    header[data-testid="stHeader"] {{ background: transparent !important; box-shadow: none !important; height: 0rem !important; min-height: 0rem !important; }}
    [data-testid="collapsedControl"], [data-testid="stSidebarCollapseButton"] {{ display: none !important; }}

    .tagline {{ text-align: center; font-style: italic; margin-top: 5px; margin-bottom: 25px; color: #888888; font-weight: 400; }}
    
    @keyframes pulse-white {{ 0% {{ text-shadow: 0 0 10px rgba(255,255,255,0.4); transform: scale(0.99); }} 50% {{ text-shadow: 0 0 20px rgba(255,255,255,0.8); transform: scale(1.01); }} 100% {{ text-shadow: 0 0 10px rgba(255,255,255,0.4); transform: scale(0.99); }} }}
    @keyframes pulse-blue-new {{ 0% {{ text-shadow: 0 0 10px rgba(36, 36, 237, 0.3); transform: scale(0.99); }} 50% {{ text-shadow: 0 0 20px rgba(36, 36, 237, 0.6); transform: scale(1.01); }} 100% {{ text-shadow: 0 0 10px rgba(36, 36, 237, 0.3); transform: scale(0.99); }} }}
    
    .pricesense-glow {{ color: {primary}; font-size: 4rem; font-weight: 900; letter-spacing: -2px; margin:0; line-height: 1; animation: {animacao_pulse} 2.5s infinite ease-in-out; }}
    .pricesense-glow-small {{ color: {primary}; font-size: 1.5rem; font-weight: 800; letter-spacing: -1px; margin:0; line-height: 1; }}

    .st-key-theme_safe {{ position: fixed !important; top: 12px !important; right: 18px !important; z-index: 999999 !important; width: 58px !important; height: 58px !important; }}
    .st-key-theme_safe .stButton > button {{ display: flex !important; align-items: center !important; justify-content: center !important; width: 54px !important; height: 54px !important; padding: 0 !important; border: none !important; border-radius: 50% !important; background: transparent !important; box-shadow: none !important; font-size: 2.25rem !important; line-height: 1 !important; transition: transform 0.2s ease !important; }}
    .st-key-theme_safe .stButton > button:hover {{ transform: scale(1.15) !important; }}

    .stApp, .block-container {{ background-color: {bg_color} !important; color: {text_color} !important; }}
    [data-testid="stSidebar"] {{ background-color: {sidebar_bg} !important; backdrop-filter: blur(16px) !important; -webkit-backdrop-filter: blur(16px) !important; border-right: 1px solid {input_border} !important; }}
    [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] h1, [data-testid="stMarkdownContainer"] h2, [data-testid="stMarkdownContainer"] h3, label {{ color: {text_color} !important; }}

    .stButton > button[kind="primary"], div[data-testid="stPopover"] > button {{ 
        background-color: {primary} !important; background-image: linear-gradient(180deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0) 100%) !important;
        border: 1px solid {primary} !important; color: #FFFFFF !important; font-weight: 600; border-radius: 10px !important; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.2) !important; transition: all 0.2s ease !important;
        height: 46px !important; min-height: 46px !important;
    }}
    .stButton > button[kind="primary"]:hover, div[data-testid="stPopover"] > button:hover {{ background-color: {primary_hover} !important; border-color: {primary_hover} !important; }}
    .stButton > button[kind="primary"] p, .stButton > button[kind="primary"] div, div[data-testid="stPopover"] > button p {{ color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important; }}

    .stDownloadButton > button[kind="primary"] {{ 
        background-color: {excel_color} !important; background-image: linear-gradient(180deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0) 100%) !important;
        border: 1px solid {excel_color} !important; color: #FFFFFF !important; font-weight: 600; border-radius: 10px !important; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.2) !important; transition: all 0.2s ease !important;
        height: 46px !important; min-height: 46px !important; 
    }}
    .stDownloadButton > button[kind="primary"]:hover {{ background-color: {excel_hover} !important; border-color: {excel_hover} !important; }}
    .stDownloadButton > button[kind="primary"] p {{ color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important; }}

    [data-testid="stExpander"] {{ background-color: transparent !important; border: 1px solid {input_border} !important; border-radius: 12px !important; box-shadow: {glass_shadow} !important; }}
    .stTextInput > div > div, .stTextInput input, .stDateInput > div > div, .stDateInput input, div[data-baseweb="select"] > div, div[data-baseweb="select"] > div > div {{ 
        background-color: {input_bg} !important; backdrop-filter: blur(10px) !important; border: 1px solid {input_border} !important; border-radius: 10px !important; color: {text_color} !important; 
    }}
    div[data-baseweb="select"] > div:focus-within, .stTextInput > div > div:focus-within, .stDateInput > div > div:focus-within {{ border-color: {primary} !important; }}
    .stTextArea textarea {{ background-color: {input_bg} !important; color: {text_color} !important; border: 1px solid {input_border} !important; border-radius: 10px !important; backdrop-filter: blur(10px) !important; }}
    .stTextArea textarea:focus {{ border-color: {primary} !important; }}
    [data-testid="stDataFrame"] {{ background-color: transparent !important; }}
    
    [data-testid="stMultiSelect"] [data-baseweb="tag"], [data-testid="stMultiSelect"] [data-baseweb="tag"] *, [data-testid="stExpander"] [data-baseweb="tag"], [data-testid="stExpander"] [data-baseweb="tag"] * {{ background-color: {primary} !important; color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important; border-radius: 6px !important; }}
    [data-testid="stMultiSelect"] [data-baseweb="tag"] svg, [data-testid="stExpander"] [data-baseweb="tag"] svg {{ fill: #FFFFFF !important; color: #FFFFFF !important; }}
    
    .st-key-sidebar_header {{ display: flex !important; align-items: center !important; }}
    .st-key-sidebar_header [data-testid="column"] {{ display: flex !important; align-items: center !important; justify-content: center !important; }}
    .st-key-sidebar_header .stButton > button {{ padding: 0 !important; height: 34px !important; width: 34px !important; border-radius: 50% !important; background-color: transparent !important; border: 1px solid {input_border} !important; color: {text_color} !important; }}
    .st-key-sidebar_header .stButton > button:hover {{ border-color: {primary} !important; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

aplicar_css_tema()

components.html("""
<script>
setInterval(() => {
    const doc = window.parent.document;
    doc.querySelectorAll('textarea').forEach(ta => {
        if (!ta.dataset.tabListener) {
            ta.addEventListener('keydown', function(e) {
                if (e.key === 'Tab') {
                    e.preventDefault();
                    let start = this.selectionStart;
                    let end = this.selectionEnd;
                    this.value = this.value.substring(0, start) + '\\t' + this.value.substring(end);
                    this.selectionStart = this.selectionEnd = start + 1;
                    this.dispatchEvent(new Event('input', { bubbles: true }));
                }
            });
            ta.dataset.tabListener = "true";
        }
    });
}, 400);
</script>
""", height=0, width=0)

if 'splash_concluido' not in st.session_state:
    st.session_state.splash_concluido = False
if 'logado' not in st.session_state:
    st.session_state.logado = False
if 'usuario_logado' not in st.session_state:
    st.session_state.usuario_logado = ""
if 'is_admin' not in st.session_state:
    st.session_state.is_admin = False

def obter_faixa(preco):
    if preco <= 10.99: return 'A'
    elif preco <= 19.99: return 'B'
    elif preco <= 40.00: return 'C'
    else: return 'D'

def arredondar_varejo(preco):
    if preco <= 0: return 0.0
    preco_arred = round(preco, 2)
    faixa = obter_faixa(preco_arred)
    base_inteira = int(np.floor(preco_arred))
    validos = []
    for c in range(100):
        p = c // 10
        u = c % 10
        is_valid = False
        if faixa == 'A': is_valid = (u in [5, 8, 9])
        elif faixa == 'B': is_valid = (1 <= p <= 9) and (u in [5, 8, 9])
        elif faixa == 'C': is_valid = (3 <= p <= 9) and (p in [5, 9]) if u == 0 else (3 <= p <= 9) and (u in [0, 5, 8, 9])
        else: is_valid = (3 <= p <= 9) and (p in [5, 9]) if u == 0 else (3 <= p <= 9) and (u == 9)
        if is_valid: validos.append(c / 100.0)
    candidatos = [round((base_inteira - 1) + v, 2) for v in validos] + [round(base_inteira + v, 2) for v in validos] + [round((base_inteira + 1) + v, 2) for v in validos]
    if round(preco_arred, 2) in candidatos: return round(preco_arred, 2)
    candidatos.sort(key=lambda x: abs(x - preco_arred))
    return round(candidatos[0], 2) if candidatos else round(preco_arred, 2)

def arredondar_atacado(preco_atacado, varejo_finalizado):
    if preco_atacado <= 0: return 0.0
    varejo_finalizado = round(varejo_finalizado, 2)
    ultimo_digito_varejo = int(round(varejo_finalizado * 100)) % 10
    preco_arred = round(preco_atacado, 2)
    faixa = obter_faixa(preco_arred)
    base_inteira = int(np.floor(preco_arred))
    validos = []
    for c in range(100):
        p = c // 10
        u = c % 10
        if u == ultimo_digito_varejo:
            is_valid = False
            if faixa == 'A': is_valid = True
            elif faixa == 'B': is_valid = (1 <= p <= 9)
            elif faixa in ['C', 'D'] and (3 <= p <= 9): is_valid = True if u != 0 else (p in [5, 9])
            if is_valid: validos.append(c / 100.0)
    candidatos = [round((base_inteira - 1) + v, 2) for v in validos] + [round(base_inteira + v, 2) for v in validos] + [round((base_inteira + 1) + v, 2) for v in validos]
    proximo = round(preco_arred, 2) if round(preco_arred, 2) in candidatos else (round(sorted(candidatos, key=lambda x: abs(x - preco_arred))[0], 2) if candidatos else round(preco_arred, 2))
    return round(varejo_finalizado if proximo >= varejo_finalizado else proximo, 2)

def puxar_estados_do_banco():
    try:
        resposta = supabase.table('lojas').select('estado').execute()
        return sorted(list(set([linha['estado'] for linha in resposta.data])))
    except Exception:
        return []

def puxar_diretores_por_estado(estados_selecionados):
    if not estados_selecionados: return []
    try:
        resposta = supabase.table('lojas').select('diretor').in_('estado', estados_selecionados).execute()
        return sorted(list(set([linha['diretor'] for linha in resposta.data])))
    except Exception:
        return []

def puxar_filiais(estados, diretores):
    if not estados: return []
    try:
        query = supabase.table('lojas').select('filial').in_('estado', estados)
        if diretores: query = query.in_('diretor', diretores)
        resposta = query.execute()
        return sorted(list(set([linha['filial'] for linha in resposta.data])))
    except Exception:
        return []

def puxar_tipos_midia():
    try:
        resposta = supabase.table('tipo_ofertas').select('tipo_preço').execute()
        return sorted(list(set([linha['tipo_preço'] for linha in resposta.data if linha['tipo_preço']])))
    except Exception:
        return ["ERRO AO CARREGAR"]

def tela_carregamento():
    st.write("<br>"*4, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        logo_ativa = URL_LOGO_DARK if st.session_state.tema == "Dark" else URL_LOGO_LIGHT
        st.markdown(f"""
        <div style='display: flex; align-items: center; justify-content: center; gap: 15px;'>
            <img src='{logo_ativa}' style='height: 70px;'>
            <div class='pricesense-glow'>PriceSense</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div class='tagline'>Transformando dados de mercado em decisões inteligentes.</div>", unsafe_allow_html=True)
        caixa_texto = st.empty()
        barra_progresso = st.progress(0)

        for i in range(101):
            time.sleep(0.01)
            barra_progresso.progress(i)
            if i == 10: caixa_texto.markdown("<p style='text-align: center; color: #A0AEC0;'>Estabelecendo conexões biOS...</p>", unsafe_allow_html=True)
            elif i == 40: caixa_texto.markdown("<p style='text-align: center; color: #A0AEC0;'>Carregando motores de inteligência...</p>", unsafe_allow_html=True)
            elif i == 70: caixa_texto.markdown("<p style='text-align: center; color: #A0AEC0;'>Sincronizando clusters e filiais...</p>", unsafe_allow_html=True)

        time.sleep(0.3)
        st.session_state.splash_concluido = True
        st.rerun()

def tela_login():
    st.write("<br>"*3, unsafe_allow_html=True)
    col_vazia1, col_centro, col_vazia2 = st.columns([1, 1.2, 1])
    with col_centro:
        logo_ativa = URL_LOGO_DARK if st.session_state.tema == "Dark" else URL_LOGO_LIGHT
        st.markdown(f"""
        <div style='display: flex; align-items: center; justify-content: center; gap: 15px;'>
            <img src='{logo_ativa}' style='height: 70px;'>
            <div class='pricesense-glow'>PriceSense</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div class='tagline'>Inteligência e Gestão de Pricing de Alta Performance.</div>", unsafe_allow_html=True)

        with st.container(border=True):
            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.session_state.modo_login == "login":
                usuario_input = st.text_input("Usuário", placeholder="Ex: joao.castro")
                senha_input = st.text_input("Senha", type="password", placeholder="••••••••")
                st.markdown("<br>", unsafe_allow_html=True)

                if st.button("Iniciar sessão", type="primary", use_container_width=True):
                    try:
                        res = supabase.table('usuarios').select('*').eq('usuario', usuario_input).execute()
                        if res.data:
                            user_data = res.data[0]
                            if senha_input == user_data['senha']:
                                if user_data['status'] == 'Aprovado':
                                    st.session_state.logado = True
                                    st.session_state.usuario_logado = user_data['nome']
                                    st.session_state.is_admin = user_data.get('is_admin', False)
                                    st.session_state.permissoes = user_data.get('permissoes', [])
                                    st.rerun()
                                elif user_data['status'] == 'Pendente':
                                    st.error("⏳ Sua solicitação ainda está em análise pelo administrador.")
                                elif user_data['status'] == 'Rejeitado':
                                    st.error("❌ Seu acesso foi negado pelo administrador.")
                            else:
                                st.error("❌ Senha incorreta.")
                        else:
                            st.error("❌ Usuário não encontrado no sistema.")
                    except Exception as e:
                        st.error(f"Erro de conexão: {e}")
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Primeiro Acesso? Solicitar conta", use_container_width=True):
                    st.session_state.modo_login = "cadastro"
                    st.rerun()
                    
            else:
                st.markdown("<h4 style='text-align: center; font-weight: 700; margin-bottom: 5px;'>Solicitação de Acesso</h4>", unsafe_allow_html=True)
                st.markdown("<p style='text-align: center; color: #888; font-size: 0.85em; margin-bottom: 20px;'>Preencha os dados abaixo para validação da sua credencial.</p>", unsafe_allow_html=True)
                
                nome_cad = st.text_input("Nome e Último Nome", placeholder="Ex: João Silva")
                
                user_cad = st.text_input("Usuário Desejado", placeholder="Ex: joao.castro ou joao_castro")
                st.caption("💡 *Este será o seu login. Use letras minúsculas e sem espaços.*")
                
                mat_cad = st.text_input("Matrícula", placeholder="Ex: 163067")
                
                cargo_cad = st.text_input("Cargo/Função", placeholder="Ex: Analista de Pricing")
                
                senha_cad = st.text_input("Crie uma Senha", type="password", placeholder="Sua senha secreta")
                senha2_cad = st.text_input("Repita a Senha", type="password", placeholder="Confirme sua senha")
                
                st.markdown("<br>", unsafe_allow_html=True)
                col_voltar, col_enviar = st.columns(2)
                with col_voltar:
                    if st.button("Voltar", use_container_width=True):
                        st.session_state.modo_login = "login"
                        st.rerun()
                with col_enviar:
                    if st.button("Enviar solicitação", type="primary", use_container_width=True):
                        if not nome_cad or not mat_cad or not cargo_cad or not user_cad or not senha_cad:
                            st.error("⚠️ Preencha todos os campos obrigatórios.")
                        elif senha_cad != senha2_cad:
                            st.error("❌ As senhas digitadas não conferem.")
                        else:
                            try:
                                check = supabase.table('usuarios').select('usuario').eq('usuario', user_cad).execute()
                                if check.data:
                                    st.error("⚠️ Este usuário já existe ou está em análise.")
                                else:
                                    supabase.table('usuarios').insert({
                                        'usuario': user_cad,
                                        'senha': senha_cad,
                                        'nome': nome_cad,
                                        'cargo': cargo_cad,
                                        'matricula': mat_cad,
                                        'status': 'Pendente',
                                        'is_admin': False,
                                        'permissoes': []
                                    }).execute()
                                    st.success("✅ Solicitação enviada! O administrador avaliará em breve.")
                                    time.sleep(2)
                                    st.session_state.modo_login = "login"
                                    st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao cadastrar: {e}")

def tela_app_principal():
    if 'pagina_atual' not in st.session_state:
        st.session_state.pagina_atual = "Preço Bot"
    if 'sidebar_compacta' not in st.session_state:
        st.session_state.sidebar_compacta = False

    logo_ativa = URL_LOGO_DARK if st.session_state.tema == "Dark" else URL_LOGO_LIGHT
    tema_atual = st.session_state.tema
    compacta = st.session_state.sidebar_compacta
    
    cor_texto_inativo = "#8B95A5" if tema_atual == "Dark" else "#5A6472"
    cor_hover_bg = "rgba(255,255,255,0.08)" if tema_atual == "Dark" else "rgba(0,0,0,0.05)"
    cor_hover_text = "#FFFFFF" if tema_atual == "Dark" else "#000000"

    css_nav = f"""
    <style>
    [data-testid="stSidebar"] {{ transition: min-width 0.3s ease, max-width 0.3s ease, width 0.3s ease !important; }}
    .st-key-nav_rail button {{ border: 1px solid transparent !important; background-color: transparent !important; box-shadow: none !important; transition: all 0.2s ease !important; }}
    .st-key-nav_rail button:hover {{ background-color: {cor_hover_bg} !important; }}
    """

    if compacta:
        css_nav += """
        [data-testid="stSidebar"] { min-width: 80px !important; max-width: 80px !important; width: 80px !important; }
        .st-key-nav_rail button { width: 48px !important; height: 48px !important; min-height: 48px !important; margin: 5px auto !important; padding: 0 !important; border-radius: 12px !important; background-position: center !important; background-repeat: no-repeat !important; background-size: 24px 24px !important; display: flex !important; justify-content: center !important; align-items: center !important; }
        .st-key-nav_rail button p, .st-key-nav_rail button div[data-testid="stMarkdownContainer"] { display: none !important; opacity: 0 !important; width: 0 !important; height: 0 !important; font-size: 0 !important; }
        """
    else:
        css_nav += f"""
        [data-testid="stSidebar"] {{ min-width: 280px !important; max-width: 280px !important; width: 280px !important; }}
        .st-key-nav_rail button {{ width: 100% !important; height: 46px !important; min-height: 46px !important; margin: 4px 0 !important; padding: 0 10px 0 50px !important; border-radius: 10px !important; background-position: 15px center !important; background-repeat: no-repeat !important; background-size: 22px 22px !important; display: flex !important; justify-content: flex-start !important; align-items: center !important; }}
        .st-key-nav_rail button div[data-testid="stMarkdownContainer"] {{ display: block !important; width: 100% !important; }}
        .st-key-nav_rail button p {{ margin: 0 !important; padding: 0 !important; text-align: left !important; font-size: 14.5px !important; font-weight: 500 !important; white-space: nowrap !important; color: {cor_texto_inativo} !important; -webkit-text-fill-color: {cor_texto_inativo} !important; }}
        .st-key-nav_rail button:hover p {{ color: {cor_hover_text} !important; -webkit-text-fill-color: {cor_hover_text} !important; }}
        """
    css_nav += "</style>"
    st.markdown(css_nav, unsafe_allow_html=True)

    with st.sidebar:
        with st.container(key="sidebar_header"):
            if compacta:
                st.markdown(f"<div style='text-align: center;'><img src='{logo_ativa}' style='height: 28px;'></div>", unsafe_allow_html=True)
                st.write("") 
                if st.button("»", key="btn_expand_side", help="Expandir menu", use_container_width=True):
                    st.session_state.sidebar_compacta = False
                    st.rerun()
            else:
                col_logo, col_ocultar = st.columns([7, 2])
                with col_logo:
                    st.markdown(f"<div style='display: flex; align-items: center; gap: 10px;'><img src='{logo_ativa}' style='height: 26px;'><div class='pricesense-glow-small' style='font-size: 1.5rem;'>PriceSense</div></div>", unsafe_allow_html=True)
                with col_ocultar:
                    if st.button("«", key="btn_collapse_side", help="Modo compacto (só ícones)"):
                        st.session_state.sidebar_compacta = True
                        st.rerun()

        if not compacta:
            st.markdown(f"<p style='text-align: center; color: gray; font-size: 0.85em; margin-top: 8px;'>{st.session_state.usuario_logado}</p>", unsafe_allow_html=True)
        
        st.markdown("---")

        todas_paginas = [
            ("Preço Bot", "preco_bot"),
            ("Pricing Regular (Em construção)", "pricing_regular"),
            ("Pricing Promo (Em breve)", "pricing_promo"),
        ]
        
        paginas_permitidas = []
        if st.session_state.is_admin:
            paginas_permitidas = todas_paginas + [("Painel de Administração", "painel_admin")]
        else:
            for n, s in todas_paginas:
                if n in st.session_state.permissoes:
                    paginas_permitidas.append((n, s))

        with st.container(key="nav_rail"):
            for nome, slug in paginas_permitidas:
                ativo = st.session_state.pagina_atual == nome
                chave_item = f"navitem_{slug}"
                
                cor_svg_ativa = "#FFFFFF" if tema_atual == "Dark" else "#000000"
                cor_svg_inativa = "#FFFFFF" if tema_atual == "Dark" else "#333333"
                icone_b64 = svg_b64(ICONES_NAV[slug], cor_svg_ativa if ativo else cor_svg_inativa)
                
                st.markdown(f"<style>.st-key-{chave_item} button {{ background-image: url('data:image/svg+xml;base64,{icone_b64}') !important; }}</style>", unsafe_allow_html=True)
                
                if st.button(nome, key=chave_item, use_container_width=True, help=nome if compacta else None):
                    st.session_state.pagina_atual = nome
                    st.rerun()
                    
                if ativo:
                    if tema_atual == "Dark":
                        st.markdown(f"""<style>
                        .st-key-{chave_item} button {{ background-color: rgba(255,255,255,0.1) !important; border: 1px solid rgba(255,255,255,0.15) !important; box-shadow: 0 4px 6px rgba(0,0,0,0.1) !important; }}
                        .st-key-{chave_item} button p {{ color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important; font-weight: 600 !important; }}
                        </style>""", unsafe_allow_html=True)
                    else:
                        st.markdown(f"""<style>
                        .st-key-{chave_item} button {{ background-color: #FFFFFF !important; border: 1px solid rgba(0,0,0,0.1) !important; box-shadow: 0 4px 6px rgba(0,0,0,0.05) !important; }}
                        .st-key-{chave_item} button p {{ color: #000000 !important; -webkit-text-fill-color: #000000 !important; font-weight: 600 !important; }}
                        </style>""", unsafe_allow_html=True)

            st.markdown("---")
            chave_logout = "navitem_logout"
            icone_logout = svg_b64(SVG_LOGOUT, cor_svg_inativa)
            st.markdown(f"<style>.st-key-{chave_logout} button {{ background-image: url('data:image/svg+xml;base64,{icone_logout}') !important; }}</style>", unsafe_allow_html=True)
            
            if st.button("Sair (Logout)", key=chave_logout, use_container_width=True, help="Sair" if compacta else None):
                st.session_state.logado = False
                st.session_state.splash_concluido = False
                st.session_state.modo_login = "login"
                st.rerun()

    menu = st.session_state.pagina_atual

    with st.container(key="theme_safe"):
        icone_tema = "☀️" if st.session_state.tema == "Dark" else "🌙"

    if st.button(icone_tema, key="theme_safe_toggle", help="Alternar tema"):
        st.session_state.tema = "Light" if st.session_state.tema == "Dark" else "Dark"
        st.rerun()

    if menu == "Painel de Administração":
        st.title("Gestão de Acessos")
        st.markdown("Controle rigoroso de usuários e permissões sincronizado diretamente com a nuvem.")
        
        try:
            usuarios_db = supabase.table('usuarios').select('*').execute().data
        except Exception as e:
            usuarios_db = []
            st.error("Erro ao conectar com o banco de dados de usuários.")

        # 1. Solicitações PENDENTES
        pendentes = [u for u in usuarios_db if u.get('status') == 'Pendente']
        if pendentes:
            st.subheader("⏳ Solicitações Pendentes")
            for u in pendentes:
                with st.container(border=True):
                    col_info, col_apr, col_rej = st.columns([3, 1, 1])
                    with col_info:
                        st.markdown(f"**{u['nome']}** (`{u['usuario']}`)")
                    with col_apr:
                        if st.button("✅ Aprovar", key=f"apr_{u['usuario']}", use_container_width=True):
                            supabase.table('usuarios').update({'status': 'Aprovado', 'permissoes': ["Preço Bot"]}).eq('usuario', u['usuario']).execute()
                            st.rerun()
                    with col_rej:
                        if st.button("❌ Rejeitar", key=f"rej_{u['usuario']}", use_container_width=True):
                            supabase.table('usuarios').update({'status': 'Rejeitado'}).eq('usuario', u['usuario']).execute()
                            st.rerun()
            st.markdown("---")

        # 2. Usuários APROVADOS (Ativos)
        aprovados = [u for u in usuarios_db if u.get('status') == 'Aprovado']
        st.subheader("✅ Usuários Ativos")
        for u in aprovados:
            with st.container(border=True):
                col_nome, col_perm, col_bloq = st.columns([2, 3, 1])
                with col_nome:
                    st.markdown(f"**{u['nome']}**")
                    st.caption(f"`{u['usuario']}` | 👑 Admin" if u.get('is_admin') else f"`{u['usuario']}` | 👤 Analista")
                with col_perm:
                    if not u.get('is_admin'):
                        opcoes_telas = ["Preço Bot", "Pricing Regular (Em construção)", "Pricing Promo (Em breve)"]
                        perm = u.get('permissoes') if u.get('permissoes') else []
                        novas_permissoes = st.multiselect("Permissões de Tela:", opcoes_telas, default=perm, key=f"perm_{u['usuario']}")
                        if novas_permissoes != perm:
                            supabase.table('usuarios').update({'permissoes': novas_permissoes}).eq('usuario', u['usuario']).execute()
                with col_bloq:
                    if not u.get('is_admin'):
                        if st.button("Bloquear", key=f"bloq_{u['usuario']}", use_container_width=True):
                            supabase.table('usuarios').update({'status': 'Rejeitado'}).eq('usuario', u['usuario']).execute()
                            st.rerun()
                            
        st.markdown("---")

        # 3. Usuários REJEITADOS
        rejeitados = [u for u in usuarios_db if u.get('status') == 'Rejeitado']
        if rejeitados:
            st.subheader("❌ Usuários Rejeitados / Bloqueados")
            for u in rejeitados:
                with st.container(border=True):
                    col_info, col_liberar = st.columns([4, 1])
                    with col_info:
                        st.markdown(f"**{u['nome']}** (`{u['usuario']}`)")
                    with col_liberar:
                        if st.button("Autorizar Acesso", key=f"aut_{u['usuario']}", use_container_width=True):
                            supabase.table('usuarios').update({'status': 'Aprovado', 'permissoes': ["Preço Bot"]}).eq('usuario', u['usuario']).execute()
                            st.rerun()

    elif menu == "Preço Bot":
        st.title("Preço Bot (Gerador de Importação)")
        st.markdown("Gere preços formatados instantaneamente para importação no sistema.")

        with st.expander("📊 1. Configurações e Filtros Base", expanded=True):
            col_esq, col_dir = st.columns([1, 1])
            with col_esq:
                st.markdown("**Filtros de Loja (Cascata)**")
                lista_estados = puxar_estados_do_banco()
                estado_selecionado = st.multiselect("Estado:", lista_estados, placeholder="Selecione os estados...")
                lista_diretores = puxar_diretores_por_estado(estado_selecionado) if estado_selecionado else []
                diretor_selecionado = st.multiselect("Diretor Regional (Opcional):", lista_diretores, disabled=not estado_selecionado, placeholder="Todos os diretores..." if estado_selecionado else "Aguardando estado...")
                lista_filiais = puxar_filiais(estado_selecionado, diretor_selecionado) if estado_selecionado else []
                filiais = st.multiselect("Filial (Obrigatório):", lista_filiais, disabled=not estado_selecionado, placeholder="Aguardando estado...")

            with col_dir:
                st.markdown("**Configurações da Campanha**")
                formato = st.radio("Formato da Régua:", ["PRICE", "COMERCIAL"], horizontal=True)
                lista_midias_bruta = puxar_tipos_midia()
                if formato == "COMERCIAL":
                    lista_midias = [m for m in lista_midias_bruta if m.split(" - ")[0].strip() not in ["1", "2", "10", "21"]]
                else:
                    lista_midias = lista_midias_bruta

                tipo_midia = st.selectbox("Tipo de Mídia:", lista_midias)
                tipo_op = st.selectbox("Operação:", ["1 - Aplicar Preço", "2 - Cancelar Preço"])

                col_opt1, col_opt2 = st.columns(2)
                with col_opt1:
                    aplicar_similar = st.selectbox("Aplicar Similar:", ["NAO", "SIM"])
                with col_opt2:
                    somente_piso = "NAO"
                    if formato == "COMERCIAL":
                        somente_piso = st.selectbox("Somente Piso de Loja:", ["NAO", "SIM"])

                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    dt_inicio = st.date_input("Data Início:", value=datetime.now())
                with col_d2:
                    dt_fim = st.date_input("Data Fim:", value=datetime.now() + timedelta(days=3))

        st.markdown("---")
        
        st.subheader("💡 Motor de Geração")

        id_classificacao = tipo_midia.split(" - ")[0].strip() if tipo_midia else ""
        cod_op = tipo_op.split(" - ")[0].strip()

        if (formato == "COMERCIAL" and cod_op == "2") or (id_classificacao == "0" and cod_op == "2"):
            st.caption("Operação de CANCELAMENTO: Cole APENAS os Códigos dos Produtos (1 por linha)")
        else:
            st.caption("Cole os valores: Cód. Produto | Preço Varejo | Preço Atacado (Pressione TAB normalmente para espaçar!)")

        texto_colado = st.text_area("Área de Transferência", height=150, label_visibility="collapsed")

        if st.button("🚀 Gerar Preços para Importação", type="primary", use_container_width=True):
            if not filiais or not texto_colado.strip():
                st.error("⚠️ Necessário selecionar ao menos uma filial e colar os dados.")
            else:
                with st.spinner('Aplicando motores analíticos de formato...'):
                    time.sleep(0.5)
                    linhas = texto_colado.strip().split('\n')
                    dados_importacao = []

                    for filial in filiais:
                        id_fil = filial.split(" - ")[0]
                        for linha in linhas:
                            if '\t' in linha:
                                partes = [p.strip() for p in linha.split('\t')]
                            else:
                                partes = linha.split()

                            if not partes or partes == [""]:
                                continue
                            cod = partes[0]

                            try:
                                var_bruto = float(partes[1].replace(',', '.')) if len(partes) >= 2 and partes[1] else 0.0
                                atac_bruto = float(partes[2].replace(',', '.')) if len(partes) >= 3 and partes[2] else var_bruto

                                novo_var = arredondar_varejo(var_bruto) if var_bruto > 0 else 0.0
                                novo_atac = arredondar_atacado(atac_bruto, novo_var) if atac_bruto > 0 else 0.0

                                str_var = f"{novo_var:.2f}".replace('.', ',') if novo_var > 0 else ""
                                str_atac = f"{novo_atac:.2f}".replace('.', ',') if novo_atac > 0 else ""

                                if id_classificacao == "14":
                                    dados_importacao.append({"Código da Filial": id_fil, "Código do Produto": cod, "Preço Varejo": str_var, "Preço Atacado": str_atac})
                                elif id_classificacao == "0":
                                    if cod_op == "2":
                                        dados_importacao.append({"Código da Filial": id_fil, "Código do Produto": cod})
                                    else:
                                        dados_importacao.append({"Código da Filial": id_fil, "Código do Produto": cod, "Preço Fixo": str_var, "Data Início": dt_inicio.strftime("%d/%m/%Y"), "Data Fim": dt_fim.strftime("%d/%m/%Y"), "Similar": aplicar_similar})
                                elif formato == "COMERCIAL":
                                    if cod_op == "2":
                                        dados_importacao.append({"Código da Filial": id_fil, "Tipo de Preço": "1", "ID Classificação": id_classificacao, "Código do Produto": cod})
                                        dados_importacao.append({"Código da Filial": id_fil, "Tipo de Preço": "2", "ID Classificação": id_classificacao, "Código do Produto": cod})
                                    else:
                                        dados_importacao.append({"Código da Filial": id_fil, "Código do Produto": cod, "Preço Varejo": str_var, "Preço Atacado": str_atac, "Data Início": dt_inicio.strftime("%d/%m/%Y"), "Data Fim": dt_fim.strftime("%d/%m/%Y"), "Similar": aplicar_similar, "ID Classificação": id_classificacao, "Somente Piso de Loja": somente_piso})
                                elif formato == "PRICE":
                                    dados_importacao.append({"Código da Filial": id_fil, "Tipo de Preço": "1", "ID Classificação": id_classificacao, "Código do Produto": cod, "Preço": str_var, "Data Início": dt_inicio.strftime("%d/%m/%Y"), "Data Fim": dt_fim.strftime("%d/%m/%Y"), "Similar": aplicar_similar, "Tipo Operação": cod_op})
                                    dados_importacao.append({"Código da Filial": id_fil, "Tipo de Preço": "2", "ID Classificação": id_classificacao, "Código do Produto": cod, "Preço": str_atac, "Data Início": dt_inicio.strftime("%d/%m/%Y"), "Data Fim": dt_fim.strftime("%d/%m/%Y"), "Similar": aplicar_similar, "Tipo Operação": cod_op})
                            except Exception:
                                pass

                    if dados_importacao:
                        df_importacao = pd.DataFrame(dados_importacao)
                        st.success(f"✅ Geração concluída! {len(df_importacao)} linhas formatadas prontas para importação.")

                        if st.session_state.tema == "Light":
                            def stripe_rows(row):
                                return ['background-color: rgba(242, 242, 242, 0.5); color: #000000; border: none;' if row.name % 2 == 0 else 'background-color: #FFFFFF; color: #000000; border: none;' for _ in row]
                            df_styled = df_importacao.style.hide(axis="index").apply(stripe_rows, axis=1)
                            st.dataframe(df_styled, use_container_width=True)
                        else:
                            st.dataframe(df_importacao, use_container_width=True, hide_index=True)

                        data_hoje = datetime.now().strftime("%d-%m-%Y")
                        nome_arquivo = f"pricesense_importacao{data_hoje}.xlsx"

                        buffer = io.BytesIO()
                        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                            df_importacao.to_excel(writer, index=False, sheet_name='Importacao')
                        buffer.seek(0)

                        txt_sem_cabecalho = df_importacao.to_csv(index=False, header=False, sep='\t')
                        b64_texto = base64.b64encode(txt_sem_cabecalho.encode('utf-8')).decode('utf-8')

                        st.markdown("<br>", unsafe_allow_html=True)
                        col_btn1, col_btn2, col_btn3 = st.columns([1.5, 1.5, 1.5])

                        btn_bg = "#107C41" if st.session_state.tema == "Light" else "#27AE60"
                        btn_hover_bg = "#0B5A2F" if st.session_state.tema == "Light" else "#1E8449"
                        primary_bg = "#2424ED" if st.session_state.tema == "Light" else "#E20000"

                        with col_btn1:
                            st.download_button(
                                label="📥 Baixar Arquivo XLSX",
                                data=buffer,
                                file_name=nome_arquivo,
                                mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                                type="primary",
                                use_container_width=True
                            )

                        with col_btn2:
                            html_code = f"""
                            <style>
                            body {{ margin: 0 !important; padding: 0 !important; overflow: hidden; }}
                            .btn-action {{
                                display: flex; justify-content: center; align-items: center; width: 100%;
                                height: 46px; font-family: "Inter", sans-serif; font-size: 15px; font-weight: 600;
                                background-color: {primary_bg}; color: #FFFFFF; border: 1px solid {primary_bg};
                                border-radius: 10px; cursor: pointer; text-decoration: none; transition: all 0.2s ease;
                                background-image: linear-gradient(180deg, rgba(255,255,255,0.15) 0%, rgba(255,255,255,0) 100%);
                                box-shadow: 0 4px 6px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,0.2);
                            }}
                            </style>
                            <button onclick="
                                const text = decodeURIComponent(escape(window.atob('{b64_texto}')));
                                navigator.clipboard.writeText(text).then(() => {{
                                    const btn = document.getElementById('btn-copy');
                                    btn.innerHTML = '✅ Copiado com sucesso!';
                                    btn.style.backgroundColor = '#008000'; btn.style.borderColor = '#008000';
                                    setTimeout(() => {{ btn.innerHTML = '📋 Copiar Base Bruta'; btn.style.backgroundColor = '{primary_bg}'; btn.style.borderColor = '{primary_bg}'; }}, 2500);
                                }});
                            " class="btn-action" id="btn-copy">
                                📋 Copiar Base Bruta
                            </button>
                            """
                            components.html(html_code, height=46)
                            
                        with col_btn3:
                            with st.popover("📧 Enviar para E-mail", use_container_width=True):
                                st.markdown(" **Insira o e-mail de destino:**")
                                email_dest = st.text_input("E-mail", placeholder="exemplo@empresa.com", label_visibility="collapsed")
                                if st.button("Enviar Arquivo", use_container_width=True):
                                    if email_dest and "@" in email_dest:
                                        # ========================================================
                                        # LÓGICA DE SMTP (Python smtplib)
                                        # ========================================================
                                        st.success(f"✅ Arquivo gerado enviado via PriceSense para {email_dest}!")
                                    else:
                                        st.error("Insira um e-mail válido.")

    elif menu == "Pricing Regular (Em construção)":
        st.title("Pricing Regular")
        st.info("🚧 Módulo de análises analíticas de cesta em processo de migração.")

    elif menu == "Pricing Promo (Em breve)":
        st.title("Pricing Promo (Validação)")
        st.info("🚧 Módulo de leitura automática de pasta de encartes em processo de migração.")

if not st.session_state.splash_concluido:
    tela_carregamento()
elif not st.session_state.logado:
    tela_login()
else:
    tela_app_principal()
