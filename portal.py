import streamlit as st
import streamlit.components.v1 as components
from streamlit import config as st_config
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time
import io
import base64
from PIL import Image
from supabase import create_client, Client
import plotly.graph_objects as go

# ================= 1. GERENCIAMENTO DE ESTADO ABSOLUTO =================
if 'tema' not in st.session_state: st.session_state.tema = "Light"
if 'modo_login' not in st.session_state: st.session_state.modo_login = "login"
if 'permissoes' not in st.session_state: st.session_state.permissoes = []
if 'pagina_atual' not in st.session_state: st.session_state.pagina_atual = "Preço Bot"
if 'splash_concluido' not in st.session_state: st.session_state.splash_concluido = False
if 'logado' not in st.session_state: st.session_state.logado = False
if 'usuario_logado' not in st.session_state: st.session_state.usuario_logado = ""
if 'usuario_login' not in st.session_state: st.session_state.usuario_login = ""
if 'foto_perfil' not in st.session_state: st.session_state.foto_perfil = ""
if 'is_admin' not in st.session_state: st.session_state.is_admin = False
if 'reset_key' not in st.session_state: st.session_state.reset_key = 0

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
st.set_page_config(page_title="PriceSense Web", layout="wide", initial_sidebar_state="collapsed")

# ================= CONEXÃO COM BANCO DE DADOS =================
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
except Exception:
    SUPABASE_URL = "https://jawdoxmvnvidqkmfohsn.supabase.co"
    SUPABASE_KEY = "sb_publishable_qbnZplDdvwJL9Ph5IEvo8Q_4korwizq"

@st.cache_resource
def iniciar_supabase():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = iniciar_supabase()

# ================= CSS GLOBAL (GLASSMORPHISM) =================
def aplicar_css_tema():
    tema = st.session_state.tema
    primary = "#E20000" if tema == "Dark" else "#2424ED"
    primary_hover = "#CC0000" if tema == "Dark" else "#09096D"
    bg_color = "#0E1117" if tema == "Dark" else "#F4F5F7"
    text_color = "#FFFFFF" if tema == "Dark" else "#1D1D1D"
    
    glass_bg = "rgba(25, 25, 30, 0.4)" if tema == "Dark" else "rgba(255, 255, 255, 0.55)"
    glass_border = "rgba(255, 255, 255, 0.08)" if tema == "Dark" else "rgba(255, 255, 255, 0.8)"
    input_bg = "rgba(20, 20, 25, 0.3)" if tema == "Dark" else "rgba(255, 255, 255, 0.6)"
    input_border = "rgba(255, 255, 255, 0.1)" if tema == "Dark" else "rgba(0, 0, 0, 0.06)"
    hover_bg = "rgba(255, 255, 255, 0.08)" if tema == "Dark" else "rgba(0, 0, 0, 0.04)"
    
    animacao_pulse = "pulse-white" if tema == "Dark" else "pulse-blue-new"

    css = f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    
    html, body, p, div, li, a, button, input, label, table, td, th {{ font-family: 'Inter', sans-serif; }}
    h1 {{ font-size: 1.6rem !important; font-weight: 700 !important; letter-spacing: -0.04em !important; margin-bottom: 0.2rem !important; margin-top: -1rem !important; }}
    h2 {{ font-size: 1.2rem !important; font-weight: 600 !important; letter-spacing: -0.02em !important; margin-bottom: 0.8rem !important; }}
    h3 {{ font-size: 0.85rem !important; font-weight: 700 !important; letter-spacing: 0.05em !important; text-transform: uppercase !important; color: #888888 !important; margin-bottom: 0.5rem !important; margin-top: 1rem !important; }}

    [data-testid="stSidebar"], [data-testid="collapsedControl"], [data-testid="stSidebarCollapseButton"], [data-testid="stToolbar"] {{ display: none !important; }}
    header[data-testid="stHeader"] {{ display: none !important; height: 0px !important; min-height: 0px !important; }}

    .block-container {{ padding: 1.5rem 3rem 5rem 3rem !important; max-width: 1500px !important; margin-top: 0 !important; }}
    @media (max-width: 767px) {{ .block-container {{ padding: 1.5rem 1rem 5rem 1rem !important; }} }}
    .stApp {{ background-color: {bg_color} !important; color: {text_color} !important; }}

    @keyframes pulse-white {{ 0% {{ text-shadow: 0 0 10px rgba(255,255,255,0.4); transform: scale(0.99); }} 50% {{ text-shadow: 0 0 20px rgba(255,255,255,0.8); transform: scale(1.01); }} 100% {{ text-shadow: 0 0 10px rgba(255,255,255,0.4); transform: scale(0.99); }} }}
    @keyframes pulse-blue-new {{ 0% {{ text-shadow: 0 0 10px rgba(36, 36, 237, 0.3); transform: scale(0.99); }} 50% {{ text-shadow: 0 0 20px rgba(36, 36, 237, 0.6); transform: scale(1.01); }} 100% {{ text-shadow: 0 0 10px rgba(36, 36, 237, 0.3); transform: scale(0.99); }} }}
    
    .pricesense-glow {{ color: {primary}; font-weight: 900; letter-spacing: -2px; margin:0; line-height: 1; animation: {animacao_pulse} 2.5s infinite ease-in-out; }}
    .pricesense-glow-header {{ color: {primary}; font-size: 2.0rem; font-weight: 900; letter-spacing: -1.5px; margin:0; line-height: 1; animation: {animacao_pulse} 2.5s infinite ease-in-out; }}

    div[data-testid="stVerticalBlockBorderWrapper"], [data-testid="stExpander"] {{
        background: {glass_bg} !important; backdrop-filter: blur(16px) !important; -webkit-backdrop-filter: blur(16px) !important;
        border: 1px solid {glass_border} !important; border-radius: 14px !important; box-shadow: 0 8px 32px rgba(0,0,0,0.03) !important;
    }}
    
    [data-testid="stPopoverBody"] {{
        background: { "rgba(25, 25, 30, 0.85)" if tema == "Dark" else "rgba(255, 255, 255, 0.9)" } !important;
        backdrop-filter: blur(24px) !important; -webkit-backdrop-filter: blur(24px) !important;
        border: 1px solid {glass_border} !important; border-radius: 16px !important; box-shadow: 0 10px 40px rgba(0,0,0,0.1) !important; padding: 10px !important;
    }}

    .stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] {{ 
        background-color: {primary} !important; background-image: linear-gradient(180deg, rgba(255,255,255,0.12) 0%, rgba(255,255,255,0) 100%) !important;
        border: 1px solid {primary} !important; color: #FFFFFF !important; font-weight: 600; border-radius: 10px !important; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,0.2) !important; transition: all 0.2s ease !important;
        height: 42px !important; min-height: 42px !important; width: 100% !important;
    }}
    .stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover {{ background-color: {primary_hover} !important; border-color: {primary_hover} !important; box-shadow: 0 6px 12px rgba(0,0,0,0.15) !important; transform: translateY(-1px) !important; }}

    .stButton > button[kind="secondary"] {{
        background-color: {input_bg} !important; border: 1px solid {input_border} !important; color: {text_color} !important; 
        font-weight: 500 !important; border-radius: 10px !important; height: 42px !important; min-height: 42px !important; 
        transition: all 0.2s ease !important; width: 100% !important; backdrop-filter: blur(8px) !important; -webkit-backdrop-filter: blur(8px) !important;
    }}
    .stButton > button[kind="secondary"]:hover {{ background-color: {hover_bg} !important; border-color: {primary} !important; transform: translateY(-1px) !important; }}

    div[data-testid="stPopover"] > button {{
        background-color: transparent !important; border: 1px solid transparent !important; color: {text_color} !important; 
        font-weight: 600 !important; font-size: 15px !important; height: 42px !important; min-height: 42px !important; 
        padding: 0 10px !important; box-shadow: none !important; display: flex; justify-content: flex-start; align-items: center; transition: all 0.2s ease !important;
    }}
    div[data-testid="stPopover"] > button:hover {{ background-color: {hover_bg} !important; color: {primary} !important; border-radius: 8px !important; }}

    .stTextInput > div > div, .stTextInput input, .stDateInput > div > div, .stDateInput input, div[data-baseweb="select"] > div {{ 
        background-color: {input_bg} !important; border: 1px solid {input_border} !important; border-radius: 10px !important; color: {text_color} !important; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02) !important;
    }}
    div[data-baseweb="select"] > div:focus-within, .stTextInput > div > div:focus-within, .stDateInput > div > div:focus-within {{ border-color: {primary} !important; box-shadow: none !important; }}
    
    [data-testid="stMultiSelect"] div[data-baseweb="select"] > div:first-child {{ flex-wrap: wrap !important; padding-top: 4px !important; padding-bottom: 4px !important; }}
    span[data-baseweb="tag"] {{ margin-bottom: 4px !important; margin-top: 4px !important; }}
    
    .stTextArea textarea {{ background-color: {input_bg} !important; color: {text_color} !important; border: 1px solid {input_border} !important; border-radius: 10px !important; tab-size: 8 !important; -moz-tab-size: 8 !important; font-family: 'Courier New', monospace !important; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02) !important; }}
    .stTextArea textarea:focus {{ border-color: {primary} !important; box-shadow: none !important; }}
    
    [data-testid="stDataFrame"] {{ background-color: transparent !important; }}
    [data-testid="stMultiSelect"] [data-baseweb="tag"], [data-testid="stMultiSelect"] [data-baseweb="tag"] *, [data-testid="stExpander"] [data-baseweb="tag"], [data-testid="stExpander"] [data-baseweb="tag"] * {{ background-color: {primary} !important; color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important; border-radius: 4px !important; }}
    
    /* CAIXAS DE KPI DA PESQUISA DE MERCADO */
    .kpi-card {{
        background: {glass_bg}; backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
        border: 1px solid {glass_border}; border-radius: 12px; padding: 15px; text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
    }}
    .kpi-title {{ font-size: 0.9rem; color: #888888; font-weight: 600; text-transform: uppercase; margin-bottom: 5px; }}
    .kpi-value {{ font-size: 2.2rem; font-weight: 800; color: {text_color}; line-height: 1; }}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)

aplicar_css_tema()

# ================= MODAL: PERFIL DO USUÁRIO =================
@st.dialog("Editar Perfil de Acesso")
def dialog_perfil():
    st.write("Atualize suas informações pessoais.")
    novo_nome = st.text_input("Nome de Exibição", value=st.session_state.get('usuario_logado', ''))
    nova_senha = st.text_input("Nova Senha (deixe em branco para manter a atual)", type="password")
    st.markdown("---")
    foto = st.file_uploader("Foto de Perfil", type=['png', 'jpg', 'jpeg'])
    
    if st.button("Salvar Alterações", type="primary", use_container_width=True):
        updates = {}
        if novo_nome and novo_nome != st.session_state.usuario_logado: updates['nome'] = novo_nome
        if nova_senha: updates['senha'] = nova_senha
            
        if foto:
            try:
                img = Image.open(foto)
                img = img.convert("RGB")
                img.thumbnail((150, 150))
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG", quality=85)
                b64_foto = base64.b64encode(buffered.getvalue()).decode('utf-8')
                updates['foto_perfil'] = b64_foto
            except Exception as e:
                st.error(f"Erro ao processar imagem: {e}")
            
        if updates:
            try:
                supabase.table('usuarios').update(updates).eq('usuario', st.session_state.usuario_login).execute()
                st.session_state.usuario_logado = novo_nome
                if 'foto_perfil' in updates: st.session_state.foto_perfil = updates['foto_perfil']
                st.success("Perfil atualizado!")
                time.sleep(1)
                st.rerun()
            except Exception as e: st.error(f"Erro no banco. {e}")
        else:
            st.rerun()

# ================= SCRIPT PARA O TAB NA CAIXA DE TEXTO =================
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

# ================= FUNÇÕES DE APOIO =================
def obter_logo_svg(cor, tamanho="36px"):
    return f"<svg width='{tamanho}' height='{tamanho}' viewBox='-2 0 28 24' fill='none' stroke='{cor}' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round' style='margin-right: 8px;'><path d='M11 2a7 7 0 0 1 7 7c0 2.5.5 3.5 1.5 4.5.5.5.5 1.5 0 2s-1.5.5-1.5 1V18a2 2 0 0 1-2 2h-5c-1.5 0-2.5-1-2.5-2.5v-2c0-1.5-1.5-2-3-2.5'/><circle cx='12' cy='10' r='2.5'/><path d='M12 6.5V7.5'/><path d='M12 12.5V13.5'/><path d='M8.5 10H9.5'/><path d='M14.5 10H15.5'/><path d='M9.5 7.5L10.2 8.2'/><path d='M13.8 11.8L14.5 12.5'/><path d='M9.5 12.5L10.2 11.8'/><path d='M13.8 8.2L14.5 7.5'/><path d='M8.5 10H3'/><circle cx='2' cy='10' r='1'/><path d='M10 6H4'/><circle cx='3' cy='6' r='1'/><path d='M10 14H5'/><circle cx='4' cy='14' r='1'/></svg>"

def extrair_nome_empresa(nome_filial):
    partes = str(nome_filial).split('-')
    if len(partes) > 1: return partes[1].strip()
    return str(nome_filial).strip()

def arredondar_varejo(preco):
    if preco <= 0: return 0.0
    preco_arred = round(preco, 2); base_inteira = int(np.floor(preco_arred)); validos = []
    faixa = 'A' if preco_arred <= 10.99 else ('B' if preco_arred <= 19.99 else ('C' if preco_arred <= 40.00 else 'D'))
    for c in range(100):
        p = c // 10; u = c % 10; is_valid = False
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
    varejo_finalizado = round(varejo_finalizado, 2); preco_arred = round(preco_atacado, 2)
    ultimo_digito_varejo = int(round(varejo_finalizado * 100)) % 10
    faixa = 'A' if preco_arred <= 10.99 else ('B' if preco_arred <= 19.99 else ('C' if preco_arred <= 40.00 else 'D'))
    base_inteira = int(np.floor(preco_arred)); validos = []
    for c in range(100):
        p = c // 10; u = c % 10
        if u == ultimo_digito_varejo:
            is_valid = False
            if faixa == 'A': is_valid = True
            elif faixa == 'B': is_valid = (1 <= p <= 9)
            elif faixa in ['C', 'D'] and (3 <= p <= 9): is_valid = True if u != 0 else (p in [5, 9])
            if is_valid: validos.append(c / 100.0)
    candidatos = [round((base_inteira - 1) + v, 2) for v in validos] + [round(base_inteira + v, 2) for v in validos] + [round((base_inteira + 1) + v, 2) for v in validos]
    proximo = round(preco_arred, 2) if round(preco_arred, 2) in candidatos else (round(sorted(candidatos, key=lambda x: abs(x - preco_arred))[0], 2) if candidatos else round(preco_arred, 2))
    return round(varejo_finalizado if proximo >= varejo_finalizado else proximo, 2)

@st.cache_data(ttl=3600)
def puxar_estados_do_banco():
    try: return sorted(list(set([linha['estado'] for linha in supabase.table('lojas').select('estado').execute().data])))
    except Exception: return []

@st.cache_data(ttl=3600)
def puxar_diretores_por_estado(estados_selecionados):
    if not estados_selecionados: return []
    try: return sorted(list(set([linha['diretor'] for linha in supabase.table('lojas').select('diretor').in_('estado', estados_selecionados).execute().data])))
    except Exception: return []

@st.cache_data(ttl=3600)
def puxar_filiais(estados, diretores):
    if not estados: return []
    try:
        query = supabase.table('lojas').select('filial').in_('estado', estados)
        if diretores: query = query.in_('diretor', diretores)
        return sorted(list(set([linha['filial'] for linha in query.execute().data])))
    except Exception: return []

@st.cache_data(ttl=3600)
def puxar_tipos_midia():
    try: return sorted(list(set([linha['tipo_preço'] for linha in supabase.table('tipo_ofertas').select('tipo_preço').execute().data if linha['tipo_preço']])))
    except Exception: return ["ERRO AO CARREGAR"]

@st.cache_data(ttl=3600)
def carregar_dim_produto():
    try: return pd.DataFrame(supabase.table('dim_produto').select('*').execute().data)
    except: return pd.DataFrame()

@st.cache_data(ttl=3600)
def carregar_dim_fornecedor():
    try: return pd.DataFrame(supabase.table('dim_fornecedor_macro').select('*').execute().data)
    except: return pd.DataFrame()

@st.cache_data(ttl=3600)
def carregar_dim_empresa_conc():
    try: return pd.DataFrame(supabase.table('dim_empresa_concorrente').select('*').execute().data)
    except: return pd.DataFrame()

# ================= TELAS =================
def tela_carregamento():
    st.write("<br>"*3, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        primary = "#E20000" if st.session_state.tema == "Dark" else "#2424ED"
        st.markdown(f"<div style='display: flex; justify-content: center; align-items: center;'>{obter_logo_svg(primary, '60px')}<div class='pricesense-glow' style='font-size: 3.5rem;'>PriceSense</div></div>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #888; font-style: italic; margin-top: 10px;'>Inicializando motores de inteligência...</p>", unsafe_allow_html=True)
        bp = st.progress(0)
        for i in range(101): time.sleep(0.01); bp.progress(i)
        time.sleep(0.3)
        st.session_state.splash_concluido = True
        st.rerun()

def tela_login():
    st.write("<br>"*3, unsafe_allow_html=True)
    col_vazia1, col_centro, col_vazia2 = st.columns([1, 1.2, 1])
    with col_centro:
        primary = "#E20000" if st.session_state.tema == "Dark" else "#2424ED"
        st.markdown(f"<div style='display: flex; justify-content: center; align-items: center;'>{obter_logo_svg(primary, '54px')}<div class='pricesense-glow' style='font-size: 3rem;'>PriceSense</div></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<br>", unsafe_allow_html=True)
            if st.session_state.modo_login == "login":
                usuario_input = st.text_input("Usuário", placeholder="Login")
                senha_input = st.text_input("Senha", type="password", placeholder="••••••••")
                st.markdown("<br>", unsafe_allow_html=True)

                if st.button("Acessar Plataforma", type="primary", use_container_width=True):
                    try:
                        res = supabase.table('usuarios').select('*').eq('usuario', usuario_input).execute()
                        if res.data and res.data[0]['senha'] == senha_input:
                            if res.data[0]['status'] == 'Aprovado':
                                st.session_state.logado = True
                                st.session_state.usuario_logado = res.data[0]['nome']
                                st.session_state.usuario_login = res.data[0]['usuario']
                                st.session_state.foto_perfil = res.data[0].get('foto_perfil', '')
                                st.session_state.is_admin = res.data[0].get('is_admin', False)
                                
                                raw_perms = res.data[0].get('permissoes', [])
                                clean_perms = []
                                for p in raw_perms:
                                    if "Bot" in p: clean_perms.append("Preço Bot")
                                    elif "Regular" in p: clean_perms.append("Pricing Regular")
                                    elif "Promo" in p: clean_perms.append("Pricing Promo")
                                    elif "Pesquisa" in p: clean_perms.append("Pesquisa de Mercado")
                                st.session_state.permissoes = clean_perms
                                st.rerun()
                            elif res.data[0]['status'] == 'Pendente': st.error("Acesso em análise.")
                            else: st.error("Acesso negado.")
                        else: st.error("Credenciais inválidas.")
                    except Exception: st.error("Erro de servidor.")
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("Solicitar Credencial", use_container_width=True): 
                    st.session_state.modo_login = "cadastro"
                    st.rerun()
            else:
                st.markdown("<h4 style='text-align: center;'>Solicitação de Acesso</h4>", unsafe_allow_html=True)
                nome_cad = st.text_input("Nome")
                user_cad = st.text_input("Usuário")
                mat_cad = st.text_input("Matrícula")
                cargo_cad = st.text_input("Cargo")
                senha_cad = st.text_input("Senha", type="password")
                senha2_cad = st.text_input("Confirmar Senha", type="password")
                st.markdown("<br>", unsafe_allow_html=True)
                col_voltar, col_enviar = st.columns(2)
                with col_voltar:
                    if st.button("Voltar", use_container_width=True): st.session_state.modo_login = "login"; st.rerun()
                with col_enviar:
                    if st.button("Enviar Solicitação", type="primary", use_container_width=True):
                        if not nome_cad or not user_cad or not senha_cad: st.error("Preencha tudo.")
                        elif senha_cad != senha2_cad: st.error("Senhas divergem.")
                        else:
                            try:
                                if supabase.table('usuarios').select('usuario').eq('usuario', user_cad).execute().data: st.error("Usuário existe.")
                                else:
                                    supabase.table('usuarios').insert({'usuario': user_cad, 'senha': senha_cad, 'nome': nome_cad, 'cargo': cargo_cad, 'matricula': mat_cad, 'status': 'Pendente', 'is_admin': False, 'permissoes': []}).execute()
                                    st.success("Enviado."); time.sleep(1); st.session_state.modo_login = "login"; st.rerun()
                            except Exception: st.error("Erro.")

def tela_app_principal():
    # ================= NAVEGAÇÃO SUPERIOR PREMIUM =================
    todas_paginas = ["Preço Bot", "Pricing Regular", "Pricing Promo", "Pesquisa de Mercado"]
    paginas_permitidas = todas_paginas + ["Administração"] if st.session_state.is_admin else [p for p in todas_paginas if p in st.session_state.permissoes]

    if st.session_state.pagina_atual not in paginas_permitidas:
        st.session_state.pagina_atual = paginas_permitidas[0] if paginas_permitidas else "Preço Bot"

    col_logo, col_nav, col_theme, col_profile = st.columns([2.5, 6.0, 0.5, 2.0], vertical_alignment="center")
    primary = "#E20000" if st.session_state.tema == "Dark" else "#2424ED"

    with col_logo:
        st.markdown(f"<div style='display: flex; align-items: center; height: 42px; gap: 8px;'>{obter_logo_svg(primary, '36px')}<div class='pricesense-glow-header'>PriceSense</div></div>", unsafe_allow_html=True)
                
    with col_nav:
        with st.container(border=True):
            nav_cols = st.columns(len(paginas_permitidas))
            for i, p in enumerate(paginas_permitidas):
                ativo = (p == st.session_state.pagina_atual)
                with nav_cols[i]:
                    if st.button(p, type="primary" if ativo else "secondary", use_container_width=True, key=f"nav_{p}"):
                        st.session_state.pagina_atual = p
                        st.rerun()
                        
    with col_theme:
        icone_tema = "🌙" if st.session_state.tema == "Light" else "☀️"
        if st.button(icone_tema, type="secondary", use_container_width=True, help="Alternar Modo"):
            st.session_state.tema = "Dark" if st.session_state.tema == "Light" else "Light"
            st.rerun()

    with col_profile:
        c_foto, c_nome = st.columns([1, 2.5], gap="small", vertical_alignment="center")
        with c_foto:
            foto_b64 = st.session_state.get('foto_perfil', '')
            if foto_b64:
                st.markdown(f'<div style="display: flex; height: 42px; align-items: center; justify-content: center;"><img src="data:image/jpeg;base64,{foto_b64}" style="width: 46px; height: 46px; border-radius: 50%; object-fit: cover; border: 2px solid {primary}; box-shadow: 0 4px 12px rgba(0,0,0,0.15);"></div>', unsafe_allow_html=True)
            else:
                nome_inicial = st.session_state.usuario_logado[0].upper() if st.session_state.usuario_logado else "U"
                st.markdown(f'<div style="display: flex; height: 42px; align-items: center; justify-content: center;"><div style="width: 46px; height: 46px; border-radius: 50%; background-color: {primary}; color: white; display: flex; align-items: center; justify-content: center; font-size: 20px; font-weight: bold; border: 2px solid {primary}; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">{nome_inicial}</div></div>', unsafe_allow_html=True)
                
        with c_nome:
            nome_exibicao = st.session_state.usuario_logado.split()[0] if st.session_state.usuario_logado else "Usuário"
            with st.popover(f"{nome_exibicao} ▾", use_container_width=True):
                if st.button("⚙️ Editar Perfil", use_container_width=True): dialog_perfil()
                if st.button("🚪 Sair", use_container_width=True):
                    st.session_state.logado = False
                    st.session_state.modo_login = "login"
                    st.rerun()

    st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
    menu = st.session_state.pagina_atual

    # ================= MÓDULOS DE APLICAÇÃO =================
    if menu == "Administração":
        st.markdown("<h1>Gestão de Acessos</h1>", unsafe_allow_html=True)
        st.markdown("Controle de usuários e permissões.")
        
        try: usuarios_db = supabase.table('usuarios').select('*').execute().data
        except Exception: usuarios_db = []; st.error("Erro banco.")

        pendentes = [u for u in usuarios_db if u.get('status') == 'Pendente']
        if pendentes:
            st.subheader("Solicitações Pendentes")
            for u in pendentes:
                with st.container(border=True):
                    c_i, c_a, c_r = st.columns([3, 1, 1], vertical_alignment="center")
                    with c_i: st.markdown(f"**{u['nome']}** (`{u['usuario']}`)")
                    with c_a:
                        if st.button("Aprovar", key=f"apr_{u['usuario']}", use_container_width=True, type="primary"):
                            supabase.table('usuarios').update({'status': 'Aprovado', 'permissoes': ["Preço Bot"]}).eq('usuario', u['usuario']).execute(); st.rerun()
                    with c_r:
                        if st.button("Rejeitar", key=f"rej_{u['usuario']}", use_container_width=True):
                            supabase.table('usuarios').update({'status': 'Rejeitado'}).eq('usuario', u['usuario']).execute(); st.rerun()

        aprovados = [u for u in usuarios_db if u.get('status') == 'Aprovado']
        st.subheader("Usuários Ativos")
        opcoes_telas_limpas = ["Preço Bot", "Pricing Regular", "Pricing Promo", "Pesquisa de Mercado"]
        for u in aprovados:
            with st.container(border=True):
                c_n, c_p, c_b = st.columns([2, 3, 1], vertical_alignment="center")
                with c_n: st.markdown(f"**{u['nome']}**<br><small>{u['usuario']}</small>", unsafe_allow_html=True)
                with c_p:
                    if not u.get('is_admin'):
                        perm_brutas = u.get('permissoes', [])
                        perm_validas = []
                        for p in perm_brutas:
                            if "Bot" in p: perm_validas.append("Preço Bot")
                            elif "Regular" in p: perm_validas.append("Pricing Regular")
                            elif "Promo" in p: perm_validas.append("Pricing Promo")
                            elif "Pesquisa" in p: perm_validas.append("Pesquisa de Mercado")
                        novas_perms = st.multiselect("Permissões:", opcoes_telas_limpas, default=perm_validas, key=f"perm_{u['usuario']}")
                        if novas_perms != perm_validas: supabase.table('usuarios').update({'permissoes': novas_perms}).eq('usuario', u['usuario']).execute()
                with c_b:
                    if not u.get('is_admin'):
                        if st.button("Bloquear", key=f"bloq_{u['usuario']}", use_container_width=True):
                            supabase.table('usuarios').update({'status': 'Rejeitado'}).eq('usuario', u['usuario']).execute(); st.rerun()

    elif menu == "Preço Bot":
        st.markdown("<h1>Preço Bot</h1>", unsafe_allow_html=True)
        st.markdown("Gerador de formatação e aplicação para importação de preços no ERP.")

        with st.expander("Configurações e Filtros Base", expanded=True):
            col_esq, col_dir = st.columns([1, 1])
            with col_esq:
                st.markdown("**Filtros de Loja (Cascata)**")
                lista_estados = puxar_estados_do_banco()
                estado_selecionado = st.multiselect("Estado:", lista_estados, placeholder="Selecione os estados...", wrap=True)
                
                lista_diretores = puxar_diretores_por_estado(estado_selecionado) if estado_selecionado else []
                diretor_selecionado = st.multiselect("Diretor Regional (Opcional):", lista_diretores, disabled=not estado_selecionado, placeholder="Todos os diretores..." if estado_selecionado else "Aguardando estado...", wrap=True)
                
                lista_filiais = puxar_filiais(estado_selecionado, diretor_selecionado) if estado_selecionado else []
                filiais = st.multiselect("Filial (Obrigatório):", lista_filiais, disabled=not estado_selecionado, placeholder="Aguardando estado...", wrap=True)

            with col_dir:
                st.markdown("**Configurações da Campanha**")
                formato = st.radio("Formato da Régua:", ["PRICE", "COMERCIAL"], horizontal=True)
                lista_midias_bruta = puxar_tipos_midia()
                lista_midias = [m for m in lista_midias_bruta if m.split(" - ")[0].strip() not in ["1", "2", "10", "21"]] if formato == "COMERCIAL" else lista_midias_bruta
                tipo_midia = st.selectbox("Tipo de Mídia:", lista_midias)
                tipo_op = st.selectbox("Operação:", ["1 - Aplicar Preço", "2 - Cancelar Preço"])

                c_o1, c_o2 = st.columns(2)
                with c_o1: aplicar_similar = st.selectbox("Aplicar Similar:", ["NAO", "SIM"])
                with c_o2: somente_piso = st.selectbox("Somente Piso de Loja:", ["NAO", "SIM"]) if formato == "COMERCIAL" else "NAO"

                c_d1, c_d2 = st.columns(2)
                with c_d1: dt_inicio = st.date_input("Data Início:", value=datetime.now())
                with c_d2: dt_fim = st.date_input("Data Fim:", value=datetime.now() + timedelta(days=3))

        st.markdown("<h2>Motor de Geração</h2>", unsafe_allow_html=True)
        id_classificacao = tipo_midia.split(" - ")[0].strip() if tipo_midia else ""
        cod_op = tipo_op.split(" - ")[0].strip()

        if (formato == "COMERCIAL" and cod_op == "2") or (id_classificacao == "0" and cod_op == "2"):
            st.caption("Operação de Cancelamento: Cole apenas os Códigos dos Produtos (1 por linha)")
        else: st.caption("Insira os valores: Cód. Produto | Preço Varejo | Preço Atacado (Pressione TAB para separar)")

        texto_colado = st.text_area("Área de Transferência", height=150, label_visibility="collapsed")

        tem_erro_atacado = False; tem_alerta_margem = False; itens_com_erro = []
        if texto_colado.strip() and not ((formato == "COMERCIAL" and cod_op == "2") or (id_classificacao == "0" and cod_op == "2")):
            for linha in texto_colado.strip().split('\n'):
                partes = [p.strip() for p in linha.split('\t')] if '\t' in linha else linha.split()
                if not partes or partes == [""]: continue
                try:
                    cod = partes[0]
                    v_val = float(partes[1].replace(',', '.')) if len(partes) >= 2 and partes[1] else 0.0
                    a_val = float(partes[2].replace(',', '.')) if len(partes) >= 3 and partes[2] else v_val
                    if a_val > v_val: tem_erro_atacado = True; itens_com_erro.append(cod) if len(itens_com_erro) < 5 else None
                    elif v_val > 0 and abs(v_val - a_val) / v_val >= 0.10: tem_alerta_margem = True
                except: pass
                
        if tem_erro_atacado: st.error(f"Bloqueio: Atacado MAIOR que Varejo! (Ex: {', '.join(itens_com_erro)}). Corrija para gerar.")
        confirmar_margem = False
        if tem_alerta_margem and not tem_erro_atacado:
            st.warning("Alerta de Negócio: Diferença de 10% ou mais entre Varejo e Atacado.")
            confirmar_margem = st.checkbox("Confirmo as margens agressivas.")

        if st.button("Gerar Preços", type="primary", use_container_width=True, disabled=tem_erro_atacado):
            if tem_alerta_margem and not confirmar_margem: st.error("Confirme a ciência da margem.")
            elif not filiais or not texto_colado.strip(): st.error("Selecione filial e insira dados.")
            else:
                with st.spinner('Aplicando regras...'):
                    time.sleep(0.5); linhas = texto_colado.strip().split('\n'); dados_importacao = []
                    for filial in filiais:
                        id_fil = filial.split(" - ")[0]
                        for linha in linhas:
                            partes = [p.strip() for p in linha.split('\t')] if '\t' in linha else linha.split()
                            if not partes or partes == [""]: continue
                            cod = partes[0]
                            try:
                                var_bruto = float(partes[1].replace(',', '.')) if len(partes) >= 2 and partes[1] else 0.0
                                atac_bruto = float(partes[2].replace(',', '.')) if len(partes) >= 3 and partes[2] else var_bruto
                                novo_var = arredondar_varejo(var_bruto) if var_bruto > 0 else 0.0
                                novo_atac = arredondar_atacado(atac_bruto, novo_var) if atac_bruto > 0 else 0.0
                                str_var = f"{novo_var:.2f}".replace('.', ',') if novo_var > 0 else ""
                                str_atac = f"{novo_atac:.2f}".replace('.', ',') if novo_atac > 0 else ""

                                if id_classificacao == "14": dados_importacao.append({"Código da Filial": id_fil, "Código do Produto": cod, "Preço Varejo": str_var, "Preço Atacado": str_atac})
                                elif id_classificacao == "0":
                                    if cod_op == "2": dados_importacao.append({"Código da Filial": id_fil, "Código do Produto": cod})
                                    else: dados_importacao.append({"Código da Filial": id_fil, "Código do Produto": cod, "Preço Fixo": str_var, "Data Início": dt_inicio.strftime("%d/%m/%Y"), "Data Fim": dt_fim.strftime("%d/%m/%Y"), "Similar": aplicar_similar})
                                elif formato == "COMERCIAL":
                                    if cod_op == "2":
                                        dados_importacao.append({"Código da Filial": id_fil, "Tipo de Preço": "1", "ID Classificação": id_classificacao, "Código do Produto": cod})
                                        dados_importacao.append({"Código da Filial": id_fil, "Tipo de Preço": "2", "ID Classificação": id_classificacao, "Código do Produto": cod})
                                    else: dados_importacao.append({"Código da Filial": id_fil, "Código do Produto": cod, "Preço Varejo": str_var, "Preço Atacado": str_atac, "Data Início": dt_inicio.strftime("%d/%m/%Y"), "Data Fim": dt_fim.strftime("%d/%m/%Y"), "Similar": aplicar_similar, "ID Classificação": id_classificacao, "Somente Piso de Loja": somente_piso})
                                elif formato == "PRICE":
                                    dados_importacao.append({"Código da Filial": id_fil, "Tipo de Preço": "1", "ID Classificação": id_classificacao, "Código do Produto": cod, "Preço": str_var, "Data Início": dt_inicio.strftime("%d/%m/%Y"), "Data Fim": dt_fim.strftime("%d/%m/%Y"), "Similar": aplicar_similar, "Tipo Operação": cod_op})
                                    dados_importacao.append({"Código da Filial": id_fil, "Tipo de Preço": "2", "ID Classificação": id_classificacao, "Código do Produto": cod, "Preço": str_atac, "Data Início": dt_inicio.strftime("%d/%m/%Y"), "Data Fim": dt_fim.strftime("%d/%m/%Y"), "Similar": aplicar_similar, "Tipo Operação": cod_op})
                            except: pass

                    if dados_importacao:
                        df_importacao = pd.DataFrame(dados_importacao); st.success("Sucesso!")
                        st.dataframe(df_importacao, use_container_width=True, hide_index=True)

                        buffer = io.BytesIO(); df_importacao.to_excel(buffer, index=False, sheet_name='Importacao'); buffer.seek(0)
                        txt_sem_cabecalho = df_importacao.to_csv(index=False, header=False, sep='\t')
                        b64_texto = base64.b64encode(txt_sem_cabecalho.encode('utf-8')).decode('utf-8')

                        st.markdown("<br>", unsafe_allow_html=True)
                        c_b1, c_b2 = st.columns([1, 1])
                        primary_bg = "#2424ED" if st.session_state.tema == "Light" else "#E20000"
                        primary_hover_bg = "#09096D" if st.session_state.tema == "Light" else "#CC0000"

                        with c_b1: st.download_button("Baixar Arquivo XLSX", data=buffer, file_name=f"pricesense_importacao{datetime.now().strftime('%d-%m-%Y')}.xlsx", mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', type="primary", use_container_width=True)
                        with c_b2:
                            components.html(f"""
                            <style>body {{ margin: 0; }} .btn-action {{ display: flex; justify-content: center; align-items: center; width: 100%; height: 42px; font-family: "Inter", sans-serif; font-size: 15px; font-weight: 600; background-color: {primary_bg}; color: #FFFFFF; border: 1px solid {primary_bg}; border-radius: 8px; cursor: pointer; transition: all 0.2s; }} .btn-action:hover {{ background-color: {primary_hover_bg}; }}</style>
                            <button onclick="const t = decodeURIComponent(escape(window.atob('{b64_texto}'))); navigator.clipboard.writeText(t).then(() => {{ this.innerHTML = 'Copiado!'; this.style.backgroundColor = '#008000'; setTimeout(() => {{ this.innerHTML = 'Copiar Base Bruta'; this.style.backgroundColor = '{primary_bg}'; }}, 2500); }});" class="btn-action">Copiar Base Bruta</button>
                            """, height=42)

    elif menu == "Pricing Regular":
        st.markdown("<h1>Pricing Regular</h1>", unsafe_allow_html=True)
        st.info("Módulo de análises competitivas em migração.")

    # ================= MÓDULO 4: PRICING PROMO =================
    elif menu == "Pricing Promo":
        import plotly.express as px
        
        st.markdown("<h1>Pricing Promo</h1>", unsafe_allow_html=True)
        st.markdown("Validação inteligente de encartes, explosão de clusters e auditoria base.")

        @st.cache_data(ttl=600)
        def carregar_de_para_clusters():
            try:
                resp = supabase.table('filial-cluster').select('*').execute()
                if resp.data: 
                    return pd.DataFrame(resp.data)
            except Exception: 
                pass
            return pd.DataFrame(columns=['CLUSTER', 'ID FILIAL'])

        @st.cache_data(ttl=600)
        def carregar_mapa_lojas():
            try:
                resp = supabase.table('lojas').select('filial').execute()
                mapa = {}
                if resp.data:
                    for r in resp.data:
                        f_id = str(r['filial']).split('-')[0].strip()
                        mapa[f_id] = str(r['filial'])
                return mapa
            except Exception: 
                return {}

        df_clusters = carregar_de_para_clusters()
        mapa_lojas = carregar_mapa_lojas()

        if 'linhas_alteradas' not in st.session_state: 
            st.session_state.linhas_alteradas = set()

        st.markdown("<h2>Upload das Bases</h2>", unsafe_allow_html=True)
        arquivos_upload = st.file_uploader("Arraste planilhas", accept_multiple_files=True, type=['xlsx', 'xls', 'csv'], label_visibility="collapsed")

        if arquivos_upload:
            nomes_arquivos = sorted([f.name for f in arquivos_upload])
            
            if 'promo_arquivos' not in st.session_state or st.session_state.promo_arquivos != nomes_arquivos:
                with st.spinner("Estruturando matriz analítica e explodindo clusters..."):
                    dfs = []
                    for arq in arquivos_upload:
                        try:
                            df_temp = pd.read_csv(arq, sep=';', encoding='latin1') if arq.name.endswith('.csv') else pd.read_excel(arq)
                            df_temp['ARQUIVO ORIGEM'] = arq.name.replace('.xlsx', '').replace('.csv', '')
                            dfs.append(df_temp)
                        except Exception: 
                            pass
                    
                    if dfs:
                        df_bruto = pd.concat(dfs, ignore_index=True)
                        df_bruto.rename(columns=lambda x: str(x).strip().upper(), inplace=True)

                        for col_data in ['INICIO', 'FIM']:
                            if col_data in df_bruto.columns: 
                                df_bruto[col_data] = pd.to_datetime(df_bruto[col_data].astype(str).str[:10], errors='coerce').dt.strftime('%d/%m/%Y')
                        
                        def limpar_preco(p):
                            try: 
                                return float(str(p).upper().replace('R$', '').replace(' ', '').replace(',', '.'))
                            except Exception: 
                                return 0.0
                            
                        if 'PRECO_PROMOCIONAL' in df_bruto.columns:
                            df_bruto['PRECO_NUM'] = df_bruto['PRECO_PROMOCIONAL'].apply(limpar_preco)
                        elif 'PRECO' in df_bruto.columns:
                            df_bruto['PRECO_NUM'] = df_bruto['PRECO'].apply(limpar_preco)
                        else:
                            df_bruto['PRECO_NUM'] = 0.0

                        if 'CLUSTER/LOJA' in df_bruto.columns and not df_clusters.empty:
                            df_explodido = df_bruto.merge(df_clusters, left_on='CLUSTER/LOJA', right_on='CLUSTER', how='left')
                            df_explodido['ID FILIAL'] = df_explodido['ID FILIAL'].fillna(df_explodido['CLUSTER/LOJA'])
                            
                            st.session_state.clusters_desconhecidos = df_explodido[df_explodido['ID FILIAL'] == df_explodido['CLUSTER/LOJA']]['CLUSTER/LOJA'].unique().tolist()
                        else:
                            df_explodido = df_bruto.copy()
                            df_explodido['ID FILIAL'] = df_explodido.get('CLUSTER/LOJA', 'DESCONHECIDO')
                            st.session_state.clusters_desconhecidos = []

                        df_explodido['FILIAL ABREV'] = df_explodido['ID FILIAL'].astype(str).map(mapa_lojas).fillna(df_explodido['ID FILIAL'].astype(str))

                        if 'SEQPRODUTO' in df_explodido.columns:
                            df_limpo = df_explodido.drop_duplicates(subset=['ID FILIAL', 'SEQPRODUTO', 'PRECO_NUM']).copy()
                            df_limpo['Status Sistema'] = df_limpo.groupby(['ID FILIAL', 'SEQPRODUTO'])['PRECO_NUM'].transform('nunique').apply(lambda x: "CRÍTICO" if x > 1 else "VÁLIDO")
                        else:
                            df_limpo = df_explodido.copy()
                            df_limpo['Status Sistema'] = "VÁLIDO"
                        
                        df_limpo['ALTERADO_MANUAL'] = 'NÃO'
                        
                        d_inicio = pd.to_datetime(df_limpo['INICIO'], format='%d/%m/%Y', errors='coerce')
                        d_fim = pd.to_datetime(df_limpo['FIM'], format='%d/%m/%Y', errors='coerce')
                        df_limpo['MIDIA'] = np.where((d_fim - d_inicio).dt.days < 4, 1, 2)

                        st.session_state.df_promo_processado = df_limpo
                        st.session_state.promo_arquivos = nomes_arquivos
                        st.session_state.linhas_alteradas = set()
                        
                        hoje_comp = pd.Timestamp.today().normalize()
                        vencidas = df_limpo[pd.to_datetime(df_limpo['FIM'], format='%d/%m/%Y', errors='coerce').dt.date < hoje_comp.date()]['ARQUIVO ORIGEM'].unique().tolist()
                        st.session_state.campanhas_vencidas = vencidas
                        st.session_state.alerta_vencido_exibido = False

        if 'df_promo_processado' in st.session_state and not st.session_state.df_promo_processado.empty:
            df = st.session_state.df_promo_processado.copy()
            st.markdown("---")
            
            vencidas = st.session_state.get('campanhas_vencidas', [])
            if vencidas:
                if not st.session_state.get('alerta_vencido_exibido', False):
                    st.toast("Atenção: Campanhas com vigência vencida detectadas.")
                    st.session_state.alerta_vencido_exibido = True
                st.warning(f"Aviso de Vigência: Há campanhas anexadas com Data Fim no passado: {', '.join(vencidas)}.")

            clusters_out = st.session_state.get('clusters_desconhecidos', [])
            if clusters_out:
                st.error(f"{len(clusters_out)} Cluster(s) não estão mapeados na arquitetura do banco de dados.")
                with st.expander("Vincular Novo Cluster (Requer Admin)", expanded=False):
                    with st.form("form_novo_cluster_promo"):
                        col_c1, col_c2 = st.columns(2)
                        novo_clust = col_c1.selectbox("Cluster Não Mapeado:", clusters_out)
                        nova_filial = col_c2.text_input("ID da Filial correspondente (Ex: 544)")
                        if st.form_submit_button("Enviar para Mapeamento", type="primary"):
                            if nova_filial.strip():
                                try:
                                    supabase.table('solicitacoes_cluster').insert({
                                        'cluster': novo_clust, 
                                        'id_filial': nova_filial, 
                                        'status': 'Pendente', 
                                        'solicitante': st.session_state.usuario_logado
                                    }).execute()
                                    st.success("Solicitação de mapeamento enviada ao Administrador.")
                                except Exception: 
                                    st.warning("Tabela 'solicitacoes_cluster' ainda não configurada no Supabase.")
                            else: 
                                st.error("O ID da Filial é obrigatório.")

            datas_ini_disp = ["Todas"] + sorted(df['INICIO'].dropna().unique().tolist())
            datas_fim_disp = ["Todas"] + sorted(df['FIM'].dropna().unique().tolist())
            campanhas_disp = ["Todas"] + sorted(df['ARQUIVO ORIGEM'].unique().tolist())
            filiais_disp = ["Todas"] + sorted(df['FILIAL ABREV'].unique().astype(str))

            col_filt, col_edit = st.columns([1.5, 1])
            with col_filt:
                st.markdown("<h2>Filtros Dinâmicos</h2>", unsafe_allow_html=True)
                f_c1, f_c2 = st.columns(2)
                f_filial = f_c1.multiselect("Filial:", filiais_disp[1:], wrap=True)
                f_prod = f_c2.text_input("Produto (Cód):", placeholder="Código Exato")
                
                f_c3, f_c4, f_c5 = st.columns([1, 1, 1])
                f_ini = f_c3.selectbox("Data Início:", datas_ini_disp)
                f_fim = f_c4.selectbox("Data Fim:", datas_fim_disp)
                f_status = f_c5.multiselect("Status:", ["VÁLIDO", "CRÍTICO"], default=["VÁLIDO", "CRÍTICO"])

            with col_edit:
                st.markdown("<h2>Alteração em Lote</h2>", unsafe_allow_html=True)
                e_c1, e_c2 = st.columns(2)
                e_camp = e_c1.selectbox("Campanha p/ Alterar:", campanhas_disp)
                e_filial = e_c2.selectbox("Filial p/ Alterar:", filiais_disp)
                
                e_c3, e_c4 = st.columns(2)
                novo_ini = e_c3.selectbox("Novo Início:", datas_ini_disp[1:]) 
                novo_fim = e_c4.selectbox("Novo Fim:", datas_fim_disp[1:])
                
                st.write("")
                if st.button("Aplicar Alteração", type="primary", use_container_width=True):
                    mask = pd.Series(True, index=df.index)
                    if e_camp != "Todas": 
                        mask &= (df['ARQUIVO ORIGEM'] == e_camp)
                    if e_filial != "Todas": 
                        mask &= (df['FILIAL ABREV'] == e_filial)
                        
                    if mask.any():
                        df.loc[mask, 'INICIO'] = novo_ini
                        df.loc[mask, 'FIM'] = novo_fim
                        
                        dt_i = pd.to_datetime(novo_ini, format='%d/%m/%Y')
                        dt_f = pd.to_datetime(novo_fim, format='%d/%m/%Y')
                        df.loc[mask, 'MIDIA'] = 1 if (dt_f - dt_i).days < 4 else 2
                        
                        st.session_state.linhas_alteradas.update(df[mask].index.tolist())
                        st.session_state.df_promo_processado = df
                        st.rerun()

            df_filtrado = df.copy()
            if f_filial: 
                df_filtrado = df_filtrado[df_filtrado['FILIAL ABREV'].isin(f_filial)]
            if f_prod: 
                df_filtrado = df_filtrado[df_filtrado['SEQPRODUTO'].astype(str).str.contains(f_prod.strip())]
            if f_ini != "Todas": 
                df_filtrado = df_filtrado[df_filtrado['INICIO'] == f_ini]
            if f_fim != "Todas": 
                df_filtrado = df_filtrado[df_filtrado['FIM'] == f_fim]
            if f_status: 
                df_filtrado = df_filtrado[df_filtrado['Status Sistema'].isin(f_status)]

            st.markdown("<br>", unsafe_allow_html=True)
            col_kpis, col_grafico = st.columns([2, 1.2])
            total_linhas = len(df_filtrado)
            críticos = df_filtrado['Status Sistema'].str.contains('CRÍTICO').sum()
            validos = total_linhas - críticos
            
            with col_kpis:
                c1, c2, c3 = st.columns(3)
                with c1.container(border=True): 
                    st.metric("Linhas Selecionadas", f"{total_linhas}")
                with c2.container(border=True): 
                    st.metric("Itens Válidos", f"{validos}")
                with c3.container(border=True): 
                    st.metric("Alertas Críticos", f"{críticos}")
            
            with col_grafico:
                if total_linhas > 0:
                    fig = px.pie(
                        pd.DataFrame({"Status": ["VÁLIDO", "CRÍTICO"], "Qtd": [validos, críticos]}), 
                        values='Qtd', names='Status', hole=0.6, color='Status', 
                        color_discrete_map={"VÁLIDO": "#27AE60", "CRÍTICO": "#E20000"}
                    )
                    fig.update_layout(margin=dict(t=10, b=10, l=10, r=10), showlegend=True, height=140, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

            st.markdown("---")
            st.markdown("<h2>Edição Direta na Grade</h2>", unsafe_allow_html=True)
            
            cols_exibicao = ['ARQUIVO ORIGEM', 'FILIAL ABREV', 'SEQPRODUTO', 'PRECO_NUM', 'INICIO', 'FIM', 'ALTERADO_MANUAL', 'Status Sistema']
            mapa_colunas = {
                'ARQUIVO ORIGEM': 'Campanha', 
                'FILIAL ABREV': 'Filial Abrev', 
                'SEQPRODUTO': 'ID Produto', 
                'PRECO_NUM': 'Preço_Temp', 
                'INICIO': 'Data Início', 
                'FIM': 'Data Fim', 
                'ALTERADO_MANUAL': 'Modificado', 
                'Status Sistema': 'Status'
            }
            
            df_vis = df_filtrado[cols_exibicao].copy().rename(columns=mapa_colunas)
            
            def estilizar_tabela(row):
                if 'CRÍTICO' in str(row.get('Status', '')): 
                    return ['background-color: #F5B7B1; color: #900C3F; font-weight: bold;'] * len(row)
                if row.get('Modificado', '') == 'SIM': 
                    return ['background-color: #FEF9E7; color: #7D6608; font-weight: bold;'] * len(row)
                return [''] * len(row)

            edited_df = st.data_editor(
                df_vis.style.apply(estilizar_tabela, axis=1), 
                column_config={
                    "Preço_Temp": st.column_config.NumberColumn("Preço (R$)", format="R$ %.2f", min_value=0.0, step=0.01), 
                    "Campanha": st.column_config.TextColumn(disabled=True), 
                    "Filial Abrev": st.column_config.TextColumn(disabled=True), 
                    "ID Produto": st.column_config.TextColumn(disabled=True), 
                    "Data Início": st.column_config.TextColumn(disabled=True), 
                    "Data Fim": st.column_config.TextColumn(disabled=True), 
                    "Modificado": st.column_config.TextColumn(disabled=True), 
                    "Status": st.column_config.TextColumn(disabled=True)
                }, 
                use_container_width=True, 
                hide_index=True, 
                height=350
            )

            if not edited_df['Preço_Temp'].equals(df_vis['Preço_Temp']):
                diff = edited_df['Preço_Temp'] != df_vis['Preço_Temp']
                df_memoria = st.session_state.df_promo_processado
                
                for idx in diff[diff].index:
                    df_memoria.loc[idx, 'PRECO_NUM'] = edited_df.loc[idx, 'Preço_Temp']
                    df_memoria.loc[idx, 'ALTERADO_MANUAL'] = 'SIM'
                    
                df_memoria['Status Sistema'] = df_memoria.groupby(['ID FILIAL', 'SEQPRODUTO'])['PRECO_NUM'].transform('nunique').apply(lambda x: "CRÍTICO" if x > 1 else "VÁLIDO")
                st.session_state.df_promo_processado = df_memoria
                st.rerun()

            st.markdown("<br>", unsafe_allow_html=True)
            tipo_operacao = st.selectbox("Selecione a Operação de Exportação:", ["1 - Aplicar Preço", "2 - Cancelar Preço"])
            oper_val = "1" if "1" in tipo_operacao else "2"
            
            col_exp1, col_exp2 = st.columns([1, 1])
            primary_bg = "#2424ED" if st.session_state.tema == "Light" else "#E20000"
            primary_hover_bg = "#09096D" if st.session_state.tema == "Light" else "#CC0000"
            
            with col_exp1:
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer: 
                    df_vis.drop(columns=['Preço_Temp']).to_excel(writer, index=False)
                buffer.seek(0)
                st.download_button(
                    "Baixar Excel da Tela", 
                    data=buffer, 
                    file_name=f"Auditoria_{datetime.now().strftime('%d-%m-%Y')}.xlsx", 
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
                    type="primary", 
                    use_container_width=True
                )
                
            with col_exp2:
                if críticos > 0: 
                    st.error("A Cópia está bloqueada. Filtre para 'VÁLIDO' ou corrija os itens críticos.")
                else:
                    df_export = df_filtrado.drop_duplicates(subset=['ID FILIAL', 'SEQPRODUTO', 'PRECO_NUM']).copy()
                    
                    df_varejo = pd.DataFrame({
                        'ID Filial': df_export['ID FILIAL'], 
                        'Tipo Preço': "1", 
                        'Midia Preço': df_export['MIDIA'], 
                        'ID Produto': df_export['SEQPRODUTO'], 
                        'Preço': df_export['PRECO_NUM'].apply(lambda x: f"{x:.2f}".replace('.', ',')), 
                        'Data Início': df_export['INICIO'], 
                        'Data Fim': df_export['FIM'], 
                        'Similar': 'NAO', 
                        'Tipo Oper.': "1" if "1" in tipo_operacao else "2"
                    })
                    
                    df_atacado = df_varejo.copy()
                    df_atacado['Tipo Preço'] = "2"
                    
                    df_import_final = pd.concat([df_varejo, df_atacado]).sort_values(by=['ID Filial', 'ID Produto', 'Tipo Preço'])
                    txt_copy = df_import_final.to_csv(sep='\t', index=False, header=False)
                    b64_copy = base64.b64encode(txt_copy.encode('utf-8')).decode('utf-8')
                    
                    components.html(f"""
                    <style>
                    body{{margin:0;overflow:hidden;background:transparent;}}
                    .b{{display:flex;justify-content:center;align-items:center;width:100%;height:42px;font-family:"Inter",sans-serif;font-size:15px;font-weight:600;background-color:{primary_bg};color:#FFFFFF;border:1px solid {primary_bg};border-radius:8px;cursor:pointer;text-decoration:none;transition:all 0.2s;}}
                    .b:hover{{background-color:{primary_hover_bg};border-color:{primary_hover_bg};}}
                    </style>
                    <button onclick="
                        const t = decodeURIComponent(escape(window.atob('{b64_copy}'))); 
                        navigator.clipboard.writeText(t).then(() => {{ 
                            this.innerHTML = 'Copiado Base Limpa'; 
                            this.style.backgroundColor = '#008000'; 
                            setTimeout(() => {{ 
                                this.innerHTML = 'Copiar Padrão Importação'; 
                                this.style.backgroundColor = '{primary_bg}'; 
                                this.style.borderColor = '{primary_bg}'; 
                            }}, 2500); 
                        }});
                    " class="b">Copiar Padrão Importação</button>
                    """, height=42)

    # ================= MÓDULO NOVO: PESQUISA DE MERCADO =================
    elif menu == "Pesquisa de Mercado":
        st.markdown("<h1>Pesquisa de Mercado (BI)</h1>", unsafe_allow_html=True)
        st.markdown("Análise histórica de preços e concorrência.")

        arquivo_pesquisa = st.file_uploader("Arraste ou selecione a base de pesquisa (CSV separado por '|')", type=['csv'])

        if arquivo_pesquisa:
            with st.spinner("Limpando, Mesclando Dimensões e Processando Inteligência..."):
                try:
                    df_pesq = pd.read_csv(arquivo_pesquisa, sep='|', encoding='latin1', dtype=str)
                    df_pesq.columns = df_pesq.columns.str.strip()
                    
                    def converter_para_float(val):
                        try:
                            if pd.isna(val) or str(val).strip() == '': return 0.0
                            v_str = str(val).upper().replace('R$', '').replace(' ', '').replace(',', '.')
                            return float(v_str)
                        except Exception:
                            return 0.0

                    cols_financeiras = ['CustoMedio', 'Vlr. Varejo PDV', 'Vlr. Atacado PDV', 'Vlr.Vare.Conc', 'Vlr.Atac.Conc.', 'QtdEstoque']
                    for col in cols_financeiras:
                        if col in df_pesq.columns:
                            df_pesq[col] = df_pesq[col].apply(converter_para_float)

                    if 'PESQUISADATA' in df_pesq.columns:
                        df_pesq['PESQUISADATA_DT'] = pd.to_datetime(df_pesq['PESQUISADATA'], format='%d/%m/%Y', errors='coerce')
                    
                    if 'Vlr.Atac.Conc.' in df_pesq.columns and 'Vlr.Vare.Conc' in df_pesq.columns:
                        df_pesq['Vlr.Atac.Conc.'] = np.where(df_pesq['Vlr.Atac.Conc.'] <= 0.09, df_pesq['Vlr.Vare.Conc'], df_pesq['Vlr.Atac.Conc.'])

                    if 'Vlr.Vare.Conc' in df_pesq.columns and 'CustoMedio' in df_pesq.columns:
                        df_pesq['MargemConc'] = np.where(df_pesq['Vlr.Vare.Conc'] > 0, (df_pesq['Vlr.Vare.Conc'] - df_pesq['CustoMedio']) / df_pesq['Vlr.Vare.Conc'], 0.0)

                    # --- INTEGRAÇÃO COM TABELAS DIMENSÃO ---
                    df_dim_prod = carregar_dim_produto()
                    df_dim_forn = carregar_dim_fornecedor()
                    df_dim_emp = carregar_dim_empresa_conc()

                    # 1. Empresa Concorrente
                    if not df_dim_emp.empty and 'filial_concorrente' in df_dim_emp.columns and 'empresa' in df_dim_emp.columns:
                        map_empresa = dict(zip(df_dim_emp['filial_concorrente'].astype(str).str.strip(), df_dim_emp['empresa'].astype(str).str.strip()))
                        df_pesq['EMPRESA_CONC'] = df_pesq['FILIALCONCORRENTE'].map(map_empresa).fillna(df_pesq['FILIALCONCORRENTE'].apply(extrair_nome_empresa))
                    else:
                        df_pesq['EMPRESA_CONC'] = df_pesq['FILIALCONCORRENTE'].apply(extrair_nome_empresa)

                    # 2. Produto -> Categoria e Fornecedor
                    if 'PRODUTO' in df_pesq.columns:
                        df_pesq['COD_PROD'] = df_pesq['PRODUTO'].str.split('-').str[0].str.strip()
                        if not df_dim_prod.empty:
                            col_p_id = 'id' if 'id' in df_dim_prod.columns else ('produto' if 'produto' in df_dim_prod.columns else df_dim_prod.columns[0])
                            map_cat = dict(zip(df_dim_prod[col_p_id].astype(str).str.strip(), df_dim_prod.get('categoria_comercial', '')))
                            map_forn = dict(zip(df_dim_prod[col_p_id].astype(str).str.strip(), df_dim_prod.get('id_fornecedor', '')))
                            
                            df_pesq['CATEGORIA_COMERCIAL'] = df_pesq['COD_PROD'].map(map_cat).fillna('SEM CLASSIFICAÇÃO')
                            df_pesq['ID_FORN'] = df_pesq['COD_PROD'].map(map_forn)
                        else:
                            df_pesq['CATEGORIA_COMERCIAL'] = 'SEM CLASSIFICAÇÃO'
                            df_pesq['ID_FORN'] = None

                    # 3. Fornecedor -> Grupo Empresarial
                    if 'ID_FORN' in df_pesq.columns and not df_dim_forn.empty:
                        col_f_id = 'id' if 'id' in df_dim_forn.columns else df_dim_forn.columns[0]
                        map_grupo = dict(zip(df_dim_forn[col_f_id].astype(str).str.strip(), df_dim_forn.get('grupo_empresarial', '')))
                        df_pesq['GRUPO_EMPRESARIAL'] = df_pesq['ID_FORN'].astype(str).map(map_grupo).fillna('SEM CLASSIFICAÇÃO')
                    else:
                        df_pesq['GRUPO_EMPRESARIAL'] = 'SEM CLASSIFICAÇÃO'

                    st.session_state.df_pesq_master = df_pesq
                except Exception as e:
                    st.error(f"Erro ao processar a base. Verifique as colunas. Erro: {e}")

        if 'df_pesq_master' in st.session_state and not st.session_state.df_pesq_master.empty:
            df_m = st.session_state.df_pesq_master.copy()
            
            st.markdown("---")
            # LINHA 1 DE FILTROS
            c_f1, c_f2, c_f3, c_f4 = st.columns(4)
            produtos_lista = ["Todos"] + sorted(df_m['PRODUTO'].dropna().unique().tolist()) if 'PRODUTO' in df_m.columns else ["Todos"]
            filial_pdv_lista = ["Todas"] + sorted(df_m['FILIAL'].dropna().unique().tolist()) if 'FILIAL' in df_m.columns else ["Todas"]
            cat_lista = ["Todas"] + sorted(df_m['CATEGORIA_COMERCIAL'].dropna().unique().tolist()) if 'CATEGORIA_COMERCIAL' in df_m.columns else ["Todas"]
            grupo_lista = ["Todos"] + sorted(df_m['GRUPO_EMPRESARIAL'].dropna().unique().tolist()) if 'GRUPO_EMPRESARIAL' in df_m.columns else ["Todos"]

            f_prod = c_f1.selectbox("PRODUTO", produtos_lista, key=f"prod_{st.session_state.reset_key}")
            f_filial = c_f2.selectbox("FILIAL (PDV)", filial_pdv_lista, key=f"filial_{st.session_state.reset_key}")
            f_cat = c_f3.selectbox("CATEGORIA COMERCIAL", cat_lista, key=f"cat_{st.session_state.reset_key}")
            f_grupo = c_f4.selectbox("GRUPO EMPRESARIAL", grupo_lista, key=f"grupo_{st.session_state.reset_key}")

            # LINHA 2 DE FILTROS
            c_f5, c_f6, c_f7, c_f_btn = st.columns([1.5, 1.5, 1.5, 0.8], vertical_alignment="bottom")
            
            if f_filial != "Todas" and 'FILIAL' in df_m.columns: df_conc_opts = df_m[df_m['FILIAL'] == f_filial]
            else: df_conc_opts = df_m
                
            filial_conc_lista = sorted(df_conc_opts['FILIALCONCORRENTE'].dropna().unique().tolist()) if 'FILIALCONCORRENTE' in df_m.columns else []
            tipo_lista = sorted(df_m['Tipo'].dropna().unique().tolist()) if 'Tipo' in df_m.columns else []
            min_data = df_m['PESQUISADATA_DT'].min().date() if not df_m['PESQUISADATA_DT'].dropna().empty else datetime.now().date()
            max_data = df_m['PESQUISADATA_DT'].max().date() if not df_m['PESQUISADATA_DT'].dropna().empty else datetime.now().date()

            f_conc = c_f5.multiselect("FILIAL CONCORRENTE", filial_conc_lista, placeholder="Filtre concorrentes...", key=f"conc_{st.session_state.reset_key}")
            f_tipo = c_f6.multiselect("TIPO PREÇO", tipo_lista, placeholder="Todos os tipos...", key=f"tipo_{st.session_state.reset_key}")
            f_periodo = c_f7.date_input("PERÍODO", [min_data, max_data], min_value=min_data, max_value=max_data, key=f"per_{st.session_state.reset_key}")
            
            with c_f_btn:
                if st.button("🧹 Limpar", use_container_width=True, help="Limpar todos os filtros"):
                    st.session_state.reset_key += 1; st.rerun()

            # APLICAÇÃO GERAL DOS FILTROS DO USUÁRIO
            df_filt = df_m.copy()
            
            # REGRA GLOBAL ABSOLUTA: Eliminar qualquer pesquisa <= 0.09
            if 'Vlr.Vare.Conc' in df_filt.columns:
                df_filt = df_filt[df_filt['Vlr.Vare.Conc'] > 0.09]

            if f_prod != "Todos" and 'PRODUTO' in df_filt.columns: df_filt = df_filt[df_filt['PRODUTO'] == f_prod]
            if f_filial != "Todas" and 'FILIAL' in df_filt.columns: df_filt = df_filt[df_filt['FILIAL'] == f_filial]
            if f_cat != "Todas" and 'CATEGORIA_COMERCIAL' in df_filt.columns: df_filt = df_filt[df_filt['CATEGORIA_COMERCIAL'] == f_cat]
            if f_grupo != "Todos" and 'GRUPO_EMPRESARIAL' in df_filt.columns: df_filt = df_filt[df_filt['GRUPO_EMPRESARIAL'] == f_grupo]
            if f_conc and 'FILIALCONCORRENTE' in df_filt.columns: df_filt = df_filt[df_filt['FILIALCONCORRENTE'].isin(f_conc)]
            if f_tipo and 'Tipo' in df_filt.columns: df_filt = df_filt[df_filt['Tipo'].isin(f_tipo)]
            if len(f_periodo) == 2:
                df_filt = df_filt[(df_filt['PESQUISADATA_DT'].dt.date >= f_periodo[0]) & (df_filt['PESQUISADATA_DT'].dt.date <= f_periodo[1])]

            # CÁLCULO DOS KPIs
            df_moda = df_filt.copy()
            if 'Tipo' in df_moda.columns:
                mask_tipo = df_moda['Tipo'].astype(str).str.upper().str.contains('REGULAR|PROMOCAO|PROMOÇÃO|PONTO EXTRA', regex=True, na=False)
                df_moda = df_moda[mask_tipo]

            if 'CustoMedio' in df_moda.columns and 'MargemConc' in df_moda.columns:
                mask_margem = (df_moda['CustoMedio'] <= 0.09) | ((df_moda['MargemConc'] >= -0.30) & (df_moda['MargemConc'] <= 0.60))
                df_moda = df_moda[mask_margem]

            v_moda_var = df_moda['Vlr.Vare.Conc'].mode()[0] if not df_moda.empty and 'Vlr.Vare.Conc' in df_moda.columns and len(df_moda['Vlr.Vare.Conc'].mode()) > 0 else 0.0
            v_moda_atac = df_moda['Vlr.Atac.Conc.'].mode()[0] if not df_moda.empty and 'Vlr.Atac.Conc.' in df_moda.columns and len(df_moda['Vlr.Atac.Conc.'].mode()) > 0 else 0.0
            
            qtd_total = len(df_filt)
            min_varejo = df_filt['Vlr.Vare.Conc'].min() if not df_filt.empty and 'Vlr.Vare.Conc' in df_filt.columns else 0.0
            max_varejo = df_filt['Vlr.Vare.Conc'].max() if not df_filt.empty and 'Vlr.Vare.Conc' in df_filt.columns else 0.0

            # DESENHO DOS MÓDULOS (KPIs + Tabela Miniatura)
            st.markdown("<br>", unsafe_allow_html=True)
            col_kpis, col_tabela = st.columns([6, 4])
            
            borda_glass = "rgba(255, 255, 255, 0.1)" if st.session_state.tema == "Dark" else "rgba(0, 0, 0, 0.08)"
            texto_glass = "#FFFFFF" if st.session_state.tema == "Dark" else "#1D1D1D"
            kpi_style = f"border: 1px solid {borda_glass}; border-radius: 10px; padding: 12px; text-align: center; box-shadow: 0 2px 8px rgba(0,0,0,0.02); height: 100%; display: flex; flex-direction: column; justify-content: center;"
            kpi_t_style = "font-size: 0.70rem; color: #888888; font-weight: 700; text-transform: uppercase; margin-bottom: 2px;"
            kpi_v_style = f"font-size: 1.7rem; font-weight: 800; color: {texto_glass}; line-height: 1;"

            with col_kpis:
                k_c1, k_c2, k_c3 = st.columns(3)
                with k_c1: st.markdown(f"<div style='{kpi_style}'><div style='{kpi_t_style}'>MODA VAREJO</div><div style='{kpi_v_style}'>{v_moda_var:,.2f}</div></div>", unsafe_allow_html=True)
                with k_c2: st.markdown(f"<div style='{kpi_style}'><div style='{kpi_t_style}'>MODA ATACADO</div><div style='{kpi_v_style}'>{v_moda_atac:,.2f}</div></div>", unsafe_allow_html=True)
                with k_c3: st.markdown(f"<div style='{kpi_style}'><div style='{kpi_t_style}'>QTD. COLETAS</div><div style='{kpi_v_style}'>{qtd_total}</div></div>", unsafe_allow_html=True)
                st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
                k_c4, k_c5 = st.columns(2)
                with k_c4: st.markdown(f"<div style='{kpi_style}'><div style='{kpi_t_style}'>MENOR PREÇO VAREJO</div><div style='{kpi_v_style}'>{min_varejo:,.2f}</div></div>", unsafe_allow_html=True)
                with k_c5: st.markdown(f"<div style='{kpi_style}'><div style='{kpi_t_style}'>MAIOR PREÇO VAREJO</div><div style='{kpi_v_style}'>{max_varejo:,.2f}</div></div>", unsafe_allow_html=True)

            with col_tabela:
                if not df_filt.empty and 'EMPRESA_CONC' in df_filt.columns:
                    st.markdown(f"<div style='font-size: 0.80rem; color: #888888; font-weight: 700; text-transform: uppercase; margin-bottom: 5px; text-align: center;'>Preço Médio por Empresa</div>", unsafe_allow_html=True)
                    df_resumo = df_filt.groupby('EMPRESA_CONC')[['Vlr.Vare.Conc', 'Vlr.Atac.Conc.']].mean().reset_index()
                    df_resumo.rename(columns={'EMPRESA_CONC': 'Concorrentes', 'Vlr.Vare.Conc': 'Varejo', 'Vlr.Atac.Conc.': 'Atacado'}, inplace=True)
                    st.dataframe(
                        df_resumo,
                        column_config={
                            "Concorrentes": st.column_config.TextColumn("Concorrentes"),
                            "Varejo": st.column_config.NumberColumn("Preço Varejo", format="R$ %.2f"),
                            "Atacado": st.column_config.NumberColumn("Preço Atacado", format="R$ %.2f")
                        },
                        hide_index=True, use_container_width=True, height=160
                    )

            # =======================================================
            # GRÁFICOS HISTÓRICOS (PLOTLY)
            # =======================================================
            st.markdown("<br>", unsafe_allow_html=True)
            
            if not df_filt.empty and 'PESQUISADATA_DT' in df_filt.columns:
                cols_agg = [c for c in ['Vlr. Varejo PDV', 'Vlr. Atacado PDV', 'Vlr.Vare.Conc', 'Vlr.Atac.Conc.'] if c in df_filt.columns]

                if cols_agg:
                    df_plot = df_filt.groupby('PESQUISADATA_DT')[cols_agg].mean().reset_index()
                    df_plot = df_plot.sort_values('PESQUISADATA_DT')
                    df_plot['DATA_STR'] = df_plot['PESQUISADATA_DT'].dt.strftime('%d/%m/%Y')
                    
                    if 'FILIALCONCORRENTE' in df_filt.columns and 'Vlr.Vare.Conc' in df_filt.columns:
                        df_hov = df_filt.groupby(['PESQUISADATA_DT', 'FILIALCONCORRENTE'])['Vlr.Vare.Conc'].mean().reset_index()
                        df_hov['conc_str'] = df_hov['FILIALCONCORRENTE'].str[:30] + ": <b>R$ " + df_hov['Vlr.Vare.Conc'].apply(lambda x: f"{x:,.2f}".replace('.', ',')) + "</b>"
                        df_hov_str = df_hov.groupby('PESQUISADATA_DT')['conc_str'].apply(lambda x: '<br>'.join(x)).reset_index(name='HOVER_CONC')
                        df_plot = pd.merge(df_plot, df_hov_str, on='PESQUISADATA_DT', how='left')

                    cor_varejo = "#2424ED" if st.session_state.tema == "Light" else "#4A90E2"
                    cor_atacado = "#E20000" if st.session_state.tema == "Light" else "#FF4B4B"
                    
                    hover_bg_color = "rgba(20, 20, 25, 0.85)" if st.session_state.tema == "Dark" else "rgba(255, 255, 255, 0.92)"
                    hover_border_color = "rgba(255, 255, 255, 0.2)" if st.session_state.tema == "Dark" else "rgba(0, 0, 0, 0.1)"
                    hover_font_color = "#FFFFFF" if st.session_state.tema == "Dark" else "#1D1D1D"

                    def desenhar_traco_e_flag(fig, df, coluna, nome_label, cor, orientacao_flag, exibe_detalhes=False):
                        if coluna in df.columns and not df[coluna].isnull().all():
                            custom_data = df['HOVER_CONC'] if exibe_detalhes and 'HOVER_CONC' in df.columns else [''] * len(df)
                            hover_temp = f"R$ %{{y:,.2f}}<br><br><span style='font-size:12px;color:#888;'>Detalhes Média Concorrentes:</span><br><span style='font-size:14px; font-weight: 500;'>%{{customdata}}</span><extra></extra>" if exibe_detalhes else f"R$ %{{y:,.2f}}<extra></extra>"
                            
                            fig.add_trace(go.Scatter(
                                x=df['DATA_STR'], y=df[coluna], mode='lines+markers+text',
                                name=nome_label, line=dict(color=cor, width=2.5, shape='spline', smoothing=0.8),
                                marker=dict(size=6, color='white', line=dict(width=2, color=cor)),
                                text=[f"{val:,.2f}".replace('.', ',') for val in df[coluna]],
                                textposition="top center" if orientacao_flag < 0 else "bottom center",
                                textfont=dict(color=cor, size=11, weight="bold"),
                                customdata=custom_data, hovertemplate=hover_temp
                            ))
                            
                            min_val = df[coluna].min()
                            data_min = df[df[coluna] == min_val].iloc[0]['DATA_STR']
                            fig.add_annotation(
                                x=data_min, y=min_val, text=f"Mín: R$ {min_val:,.2f}",
                                showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=2, arrowcolor=cor,
                                ax=0, ay=orientacao_flag, font=dict(color="white", size=10, family="Inter"),
                                bgcolor=cor, borderpad=3, borderwidth=1, opacity=0.95, bordercolor='white'
                            )

                    titulo_graf = f"Evolução de Preços - {f_prod}" if f_prod != "Todos" else "Evolução Média de Preços (Visão Geral)"
                    texto_titulo = "#1D1D1D" if st.session_state.tema == "Light" else "#FFFFFF"
                    grid_color = "rgba(150,150,150,0.15)"

                    if 'Vlr.Vare.Conc' in cols_agg or 'Vlr.Atac.Conc.' in cols_agg:
                        fig_conc = go.Figure()
                        desenhar_traco_e_flag(fig_conc, df_plot, 'Vlr.Vare.Conc', 'Varejo Concorrente', cor_varejo, orientacao_flag=-35, exibe_detalhes=True)
                        desenhar_traco_e_flag(fig_conc, df_plot, 'Vlr.Atac.Conc.', 'Atacado Concorrente', cor_atacado, orientacao_flag=35, exibe_detalhes=False)
                        
                        fig_conc.update_layout(
                            height=320,
                            title=f"<b>{titulo_graf} - CONCORRENTE</b>", title_font=dict(size=16, family="Inter", color=texto_titulo),
                            margin=dict(l=10, r=10, t=50, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            hovermode="x unified",
                            hoverlabel=dict(bgcolor=hover_bg_color, font_size=15, font_family="Inter", bordercolor=hover_border_color, font_color=hover_font_color),
                            xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(color="#888888", size=10)),
                            yaxis=dict(showgrid=True, gridcolor=grid_color, zeroline=False, tickprefix="R$ ", tickfont=dict(color="#888888", size=10)),
                            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1)
                        )
                        with st.container(border=True): st.plotly_chart(fig_conc, use_container_width=True, config={'displayModeBar': False})

                    if 'Vlr. Varejo PDV' in cols_agg or 'Vlr. Atacado PDV' in cols_agg:
                        st.markdown("<br>", unsafe_allow_html=True)
                        fig_pdv = go.Figure()
                        desenhar_traco_e_flag(fig_pdv, df_plot, 'Vlr. Varejo PDV', 'Varejo PDV', cor_varejo, orientacao_flag=-35)
                        desenhar_traco_e_flag(fig_pdv, df_plot, 'Vlr. Atacado PDV', 'Atacado PDV', cor_atacado, orientacao_flag=35)

                        fig_pdv.update_layout(
                            height=320,
                            title=f"<b>{titulo_graf} - NOSSO PDV</b>", title_font=dict(size=16, family="Inter", color=texto_titulo),
                            margin=dict(l=10, r=10, t=50, b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            hovermode="x unified",
                            hoverlabel=dict(bgcolor=hover_bg_color, font_size=15, font_family="Inter", bordercolor=hover_border_color, font_color=hover_font_color),
                            xaxis=dict(showgrid=False, zeroline=False, tickfont=dict(color="#888888", size=10)),
                            yaxis=dict(showgrid=True, gridcolor=grid_color, zeroline=False, tickprefix="R$ ", tickfont=dict(color="#888888", size=10)),
                            legend=dict(orientation="h", yanchor="bottom", y=1.05, xanchor="right", x=1)
                        )
                        with st.container(border=True): st.plotly_chart(fig_pdv, use_container_width=True, config={'displayModeBar': False})

            # =======================================================
            # MÓDULOS EXECUTIVOS DE EXTRAÇÃO (SEM EMOJIS)
            # =======================================================
            st.markdown("<br><hr>", unsafe_allow_html=True)
            st.markdown("<h2>Geração de Inteligência Competitiva</h2>", unsafe_allow_html=True)
            st.markdown("<p style='color: #888;'>Selecione abaixo o modelo analítico que deseja processar sobre a base filtrada.</p>", unsafe_allow_html=True)
            
            c_btn1, c_btn2, c_btn3, c_btn4 = st.columns(4)
            
            # --- MODELO 1: MODA DE MERCADO ---
            with c_btn1:
                if st.button("Extrair Preço Moda", type="primary", use_container_width=True, key="btn_ext_moda"):
                    with st.spinner("Processando inteligência de Moda de Mercado..."):
                        time.sleep(0.5)
                        df_analise = df_filt.copy()
                        
                        if 'Tipo' in df_analise.columns:
                            m_tipo = df_analise['Tipo'].astype(str).str.upper().str.contains('REGULAR|PROMOCAO|PROMOÇÃO|PONTO EXTRA', regex=True, na=False)
                            df_analise = df_analise[m_tipo]

                        if 'CustoMedio' in df_analise.columns and 'MargemConc' in df_analise.columns:
                            m_margem = (df_analise['CustoMedio'] <= 0.09) | ((df_analise['MargemConc'] >= -0.30) & (df_analise['MargemConc'] <= 0.60))
                            df_analise = df_analise[m_margem]

                        if df_analise.empty:
                            st.warning("Nenhum dado válido após aplicar os filtros de Tipo e Margem (-30% a +60%).")
                        elif not {'FILIAL', 'PRODUTO', 'FILIALCONCORRENTE', 'Vlr.Vare.Conc', 'Vlr.Atac.Conc.'}.issubset(df_analise.columns):
                            st.error("A base não contém as colunas necessárias para este cálculo.")
                        else:
                            def calc_modas(g):
                                counts = g['Vlr.Vare.Conc'].value_counts()
                                if counts.empty: return pd.Series({'Moda Varejo': 0.0, 'Moda Atacado': 0.0, 'Frequência Máxima': 0})
                                m_var = counts.index[0]
                                freq = counts.iloc[0]
                                m_atac_serie = g[g['Vlr.Vare.Conc'] == m_var]['Vlr.Atac.Conc.'].mode()
                                m_atac = m_atac_serie.iloc[0] if not m_atac_serie.empty else 0.0
                                return pd.Series({'Moda Varejo': m_var, 'Moda Atacado': m_atac, 'Frequência Máxima': freq})

                            df_modas_conc = df_analise.groupby(['FILIAL', 'PRODUTO', 'FILIALCONCORRENTE']).apply(calc_modas).reset_index()
                            idx_max = df_modas_conc.groupby(['FILIAL', 'PRODUTO'])['Frequência Máxima'].idxmax()
                            df_final = df_modas_conc.loc[idx_max].reset_index(drop=True)
                            
                            df_final.rename(columns={'FILIAL': 'Filial', 'PRODUTO': 'Produto', 'FILIALCONCORRENTE': 'Concorrente Moda'}, inplace=True)
                            df_final = df_final[['Filial', 'Produto', 'Moda Varejo', 'Moda Atacado', 'Frequência Máxima', 'Concorrente Moda']].sort_values(by=['Filial', 'Produto'])

                            st.success("Moda de Mercado gerada com sucesso!")
                            st.dataframe(df_final, use_container_width=True, hide_index=True)

                            buf_resumo = io.BytesIO()
                            with pd.ExcelWriter(buf_resumo, engine='openpyxl') as w: df_final.to_excel(w, index=False)
                            buf_resumo.seek(0)
                            
                            st.download_button("Baixar Resumo Moda (Excel)", data=buf_resumo, file_name=f"PriceSense_ModaMercado_{datetime.now().strftime('%d-%m-%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="secondary", use_container_width=True)

            # --- MODELO 2: MENOR PREÇO (RECENTE) ---
            with c_btn2:
                if st.button("Extrair Menor Preço", type="primary", use_container_width=True, key="btn_ext_min"):
                    with st.spinner("Processando inteligência de Menor Preço Recente..."):
                        time.sleep(0.5)
                        df_menor = df_filt.copy()
                        
                        if 'Tipo' in df_menor.columns:
                            df_menor = df_menor[~df_menor['Tipo'].astype(str).str.upper().str.contains('VALIDADE', na=False)]

                        if df_menor.empty:
                            st.warning("Nenhum dado válido após aplicar os filtros (Removido Tipo 'VALIDADE').")
                        elif not {'FILIAL', 'PRODUTO', 'FILIALCONCORRENTE', 'Vlr.Vare.Conc', 'Vlr.Atac.Conc.', 'CustoMedio', 'PESQUISADATA_DT'}.issubset(df_menor.columns):
                            st.error("A base não contém as colunas necessárias para este cálculo.")
                        else:
                            df_menor = df_menor.sort_values(by='PESQUISADATA_DT', ascending=False)
                            df_recentes = df_menor.drop_duplicates(subset=['FILIAL', 'PRODUTO', 'FILIALCONCORRENTE'], keep='first')
                            
                            df_recentes = df_recentes.sort_values(by='Vlr.Vare.Conc', ascending=True)
                            df_final_menor = df_recentes.drop_duplicates(subset=['FILIAL', 'PRODUTO'], keep='first')
                            
                            map_cols_menor = {
                                'FILIAL': 'Filial',
                                'PRODUTO': 'Produto',
                                'CustoMedio': 'Custo Médio',
                                'Vlr.Vare.Conc': 'Menor Varejo',
                                'Vlr.Atac.Conc.': 'Menor Atacado',
                                'MargemConc': 'Margem Mercado (Menor)',
                                'Tipo': 'Tipo',
                                'PESQUISADATA': 'Data Pesquisa',
                                'FILIALCONCORRENTE': 'Concorrente Menor'
                            }
                            
                            df_final_menor = df_final_menor.rename(columns=map_cols_menor)[list(map_cols_menor.values())]
                            df_final_menor['Margem Mercado (Menor)'] = df_final_menor['Margem Mercado (Menor)'].apply(lambda x: round(x * 100, 2) if pd.notnull(x) else 0.0)
                            df_final_menor = df_final_menor.sort_values(by=['Filial', 'Produto'])

                            st.success("Menor Preço gerado com sucesso!")
                            st.dataframe(df_final_menor, use_container_width=True, hide_index=True)

                            buf_menor = io.BytesIO()
                            with pd.ExcelWriter(buf_menor, engine='openpyxl') as w: df_final_menor.to_excel(w, index=False)
                            buf_menor.seek(0)
                            
                            st.download_button("Baixar Resumo Mínimo (Excel)", data=buf_menor, file_name=f"PriceSense_MenorPreco_{datetime.now().strftime('%d-%m-%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="secondary", use_container_width=True)

            # --- MODELO 3: MENOR PREÇO HISTÓRICO ---
            with c_btn3:
                if st.button("Extrair Menor Histórico", type="primary", use_container_width=True, key="btn_ext_hist"):
                    with st.spinner("Processando inteligência de Menor Preço Histórico..."):
                        time.sleep(0.5)
                        df_hist = df_filt.copy()
                        
                        if 'Tipo' in df_hist.columns:
                            df_hist = df_hist[~df_hist['Tipo'].astype(str).str.upper().str.contains('VALIDADE', na=False)]

                        if 'CustoMedio' in df_hist.columns and 'MargemConc' in df_hist.columns:
                            m_margem_hist = (df_hist['CustoMedio'] <= 0.09) | ((df_hist['MargemConc'] >= -0.50) & (df_hist['MargemConc'] <= 0.60))
                            df_hist = df_hist[m_margem_hist]

                        if df_hist.empty:
                            st.warning("Nenhum dado válido após aplicar os filtros (Tipo 'VALIDADE' removido e Margem -50% a +60%).")
                        elif not {'FILIAL', 'PRODUTO', 'FILIALCONCORRENTE', 'Vlr.Vare.Conc', 'Vlr.Atac.Conc.', 'CustoMedio', 'Vlr. Varejo PDV', 'Vlr. Atacado PDV', 'Tipo', 'PESQUISADATA'}.issubset(df_hist.columns):
                            st.error("A base não contém as colunas necessárias para este cálculo.")
                        else:
                            df_hist = df_hist.sort_values(by='Vlr.Vare.Conc', ascending=True)
                            df_final_hist = df_hist.drop_duplicates(subset=['FILIAL', 'PRODUTO'], keep='first')
                            
                            map_cols_hist = {
                                'FILIAL': 'Filial',
                                'PRODUTO': 'Produto',
                                'CustoMedio': 'Custo Médio',
                                'Vlr. Varejo PDV': 'Vlr. Varejo PDV',
                                'Vlr. Atacado PDV': 'Vlr. Atacado PDV',
                                'Vlr.Vare.Conc': 'Menor Varejo Conc.',
                                'Vlr.Atac.Conc.': 'Menor Atacado Conc.',
                                'Tipo': 'Tipo',
                                'PESQUISADATA': 'Data',
                                'FILIALCONCORRENTE': 'Menor Concorrente'
                            }
                            
                            df_final_hist = df_final_hist.rename(columns=map_cols_hist)[list(map_cols_hist.values())]
                            df_final_hist = df_final_hist.sort_values(by=['Filial', 'Produto'])

                            st.success("Menor Preço Histórico gerado com sucesso!")
                            st.dataframe(df_final_hist, use_container_width=True, hide_index=True)

                            buf_hist = io.BytesIO()
                            with pd.ExcelWriter(buf_hist, engine='openpyxl') as w: df_final_hist.to_excel(w, index=False)
                            buf_hist.seek(0)
                            
                            st.download_button("Baixar Histórico (Excel)", data=buf_hist, file_name=f"PriceSense_MenorHistorico_{datetime.now().strftime('%d-%m-%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="secondary", use_container_width=True)

            # --- MODELO 4: MERCADO TOTAL ---
            with c_btn4:
                if st.button("Extrair Mercado Total", type="primary", use_container_width=True, key="btn_ext_total"):
                    with st.spinner("Consolidando Visão Mercado Total..."):
                        time.sleep(0.5)
                        df_base_mt = df_filt.copy()

                        # Corte Global do Mercado Total (-40% a +60%)
                        if 'CustoMedio' in df_base_mt.columns and 'MargemConc' in df_base_mt.columns:
                            m_margem_mt = (df_base_mt['CustoMedio'] <= 0.09) | ((df_base_mt['MargemConc'] >= -0.40) & (df_base_mt['MargemConc'] <= 0.60))
                            df_base_mt = df_base_mt[m_margem_mt]

                        if df_base_mt.empty:
                            st.warning("Nenhum dado válido após aplicar filtro de Margem (-40% a +60%).")
                        elif not {'FILIAL', 'PRODUTO', 'FILIALCONCORRENTE', 'Vlr.Vare.Conc', 'Vlr.Atac.Conc.', 'CustoMedio', 'Tipo', 'PESQUISADATA_DT', 'PESQUISADATA'}.issubset(df_base_mt.columns):
                            st.error("A base não contém as colunas necessárias para o Mercado Total.")
                        else:
                            # 1. VISÃO RECENTE (SEM VALIDADE)
                            df_rec = df_base_mt.copy()
                            df_rec = df_rec[~df_rec['Tipo'].astype(str).str.upper().str.contains('VALIDADE', na=False)]
                            df_rec = df_rec.sort_values(by='PESQUISADATA_DT', ascending=False).drop_duplicates(subset=['FILIAL', 'PRODUTO', 'FILIALCONCORRENTE'], keep='first')
                            df_rec = df_rec.sort_values(by='Vlr.Vare.Conc', ascending=True).drop_duplicates(subset=['FILIAL', 'PRODUTO'], keep='first')
                            df_rec = df_rec[['FILIAL', 'PRODUTO', 'CustoMedio', 'Vlr.Vare.Conc', 'Vlr.Atac.Conc.', 'Tipo', 'PESQUISADATA', 'FILIALCONCORRENTE']]
                            df_rec.rename(columns={
                                'CustoMedio': 'Custo Médio', 'Vlr.Vare.Conc': 'Menor Varejo (Recente)', 'Vlr.Atac.Conc.': 'Menor Atacado (Recente)', 
                                'PESQUISADATA': 'Data Pesquisa', 'FILIALCONCORRENTE': 'Concorrente Menor (Recente)'
                            }, inplace=True)

                            # 2. VISÃO HISTÓRICA (SEM VALIDADE)
                            df_hst = df_base_mt.copy()
                            df_hst = df_hst[~df_hst['Tipo'].astype(str).str.upper().str.contains('VALIDADE', na=False)]
                            df_hst = df_hst.sort_values(by='Vlr.Vare.Conc', ascending=True).drop_duplicates(subset=['FILIAL', 'PRODUTO'], keep='first')
                            df_hst = df_hst[['FILIAL', 'PRODUTO', 'Vlr.Vare.Conc', 'Vlr.Atac.Conc.', 'Tipo', 'FILIALCONCORRENTE']]
                            df_hst.rename(columns={
                                'Vlr.Vare.Conc': 'Menor Varejo (Histórico)', 'Vlr.Atac.Conc.': 'Menor Atacado (Histórico)', 
                                'Tipo': 'Tipo (Histórico)', 'FILIALCONCORRENTE': 'Concorrente Menor (Histórico)'
                            }, inplace=True)

                            # 3. VISÃO MODA (SÓ REGULAR/PROMO/PONTO EXTRA)
                            df_md = df_base_mt.copy()
                            df_md = df_md[df_md['Tipo'].astype(str).str.upper().str.contains('REGULAR|PROMOCAO|PROMOÇÃO|PONTO EXTRA', regex=True, na=False)]
                            if not df_md.empty:
                                def calc_modas_mt(g):
                                    counts = g['Vlr.Vare.Conc'].value_counts()
                                    if counts.empty: return pd.Series({'Moda Varejo': 0.0, 'Moda Atacado': 0.0, 'Frequência': 0})
                                    m_var = counts.index[0]
                                    freq = counts.iloc[0]
                                    m_atac_serie = g[g['Vlr.Vare.Conc'] == m_var]['Vlr.Atac.Conc.'].mode()
                                    m_atac = m_atac_serie.iloc[0] if not m_atac_serie.empty else 0.0
                                    return pd.Series({'Moda Varejo': m_var, 'Moda Atacado': m_atac, 'Frequência': freq})

                                df_modas_conc = df_md.groupby(['FILIAL', 'PRODUTO', 'FILIALCONCORRENTE']).apply(calc_modas_mt).reset_index()
                                idx_max = df_modas_conc.groupby(['FILIAL', 'PRODUTO'])['Frequência'].idxmax()
                                df_md_final = df_modas_conc.loc[idx_max].reset_index(drop=True)
                                df_md_final.rename(columns={'FILIALCONCORRENTE': 'Concorrente Moda'}, inplace=True)
                            else:
                                df_md_final = pd.DataFrame(columns=['FILIAL', 'PRODUTO', 'Moda Varejo', 'Moda Atacado', 'Frequência', 'Concorrente Moda'])

                            # MERGE DE TODOS OS CÁLCULOS
                            df_mt = pd.merge(df_rec, df_hst, on=['FILIAL', 'PRODUTO'], how='outer')
                            df_mt = pd.merge(df_mt, df_md_final, on=['FILIAL', 'PRODUTO'], how='outer')
                            df_mt.rename(columns={'FILIAL': 'Filial', 'PRODUTO': 'Produto'}, inplace=True)
                            
                            # Formatação Final
                            colunas_finais = [
                                'Filial', 'Produto', 'Custo Médio', 
                                'Menor Varejo (Recente)', 'Menor Atacado (Recente)', 'Tipo', 'Data Pesquisa', 'Concorrente Menor (Recente)', 
                                'Menor Varejo (Histórico)', 'Menor Atacado (Histórico)', 'Tipo (Histórico)', 'Concorrente Menor (Histórico)', 
                                'Moda Varejo', 'Moda Atacado', 'Frequência', 'Concorrente Moda'
                            ]
                            df_mt = df_mt[[c for c in colunas_finais if c in df_mt.columns]]
                            df_mt = df_mt.sort_values(by=['Filial', 'Produto'])

                            st.success("Mercado Total consolidado com sucesso!")
                            st.dataframe(df_mt, use_container_width=True, hide_index=True)

                            buf_mt = io.BytesIO()
                            with pd.ExcelWriter(buf_mt, engine='openpyxl') as w: df_mt.to_excel(w, index=False)
                            buf_mt.seek(0)
                            
                            st.download_button("Baixar Mercado Total (Excel)", data=buf_mt, file_name=f"PriceSense_MercadoTotal_{datetime.now().strftime('%d-%m-%Y')}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", type="secondary", use_container_width=True)

# Garantia de margem de escape na parte inferior
st.write("<br><br><br><br>", unsafe_allow_html=True)

if not st.session_state.splash_concluido: 
    tela_carregamento()
elif not st.session_state.logado: 
    tela_login()
else: 
    tela_app_principal()
