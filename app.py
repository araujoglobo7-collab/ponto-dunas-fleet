import streamlit as st
import pandas as pd
import sqlite3
import base64
import plotly.express as px
from datetime import datetime, date, timedelta

# --- CONFIGURAÇÃO DUNAS FLEET ---
st.set_page_config(page_title="Dunas Fleet | Intelligence", page_icon="🟠", layout="wide")

# --- CSS PREMIUM CLEAN & TOTAL RESPONSIVO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #FFFFFF; }
    
    /* Ajuste da Câmera: Menor e centralizada para Mobile */
    [data-testid="stCameraInput"] { 
        max-width: 400px !important; 
        margin: 0 auto; 
    }
    
    /* Cards de Indicadores */
    .metric-card {
        background: #F8F9FA; padding: 15px; border-radius: 12px;
        border: 1px solid #E9ECEF; text-align: center; margin-bottom: 10px;
    }
    
    /* Painel de Insight IA */
    .insight-card {
        background: #FFF3E0; padding: 20px; border-radius: 15px;
        border-left: 8px solid #FF8C00; margin-bottom: 20px;
    }
    
    /* Botão Estilo Dunas */
    div.stButton > button {
        background-color: #000; color: white; border-radius: 10px;
        height: 48px; font-weight: 600; border: none; width: 100%;
        transition: 0.3s;
    }
    div.stButton > button:hover { background-color: #FF8C00; }
    
    /* Ajustes para telas pequenas (Celulares) */
    @media (max-width: 640px) {
        .main-title { font-size: 1.8rem !important; }
        [data-testid="stCameraInput"] { width: 100% !important; }
        .stMetric { margin-bottom: 10px; }
    }
    </style>
""", unsafe_allow_html=True)

# --- ENGINE DE DADOS ---
def db_query(query, params=(), fetch=False):
    with sqlite3.connect('dunas_fleet_v8.db') as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetch: return cursor.fetchall()
        conn.commit()

def init_db():
    db_query('''CREATE TABLE IF NOT EXISTS registros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                colaborador TEXT, data TEXT, hora TEXT, tipo TEXT, foto TEXT)''')
init_db()

# --- SISTEMA DE LOGIN ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    st.markdown("<h1 class='main-title' style='text-align:center; color:#000;'>🟠 DUNAS <span style='color:#FF8C00'>FLEET</span></h1>", unsafe_allow_html=True)
    _, col_login, _ = st.columns([1, 1.2, 1])
    with col_login:
        u = st.text_input("Usuário").lower().strip()
        p = st.text_input("Senha", type="password")
        if st.button("ACESSAR DASHBOARD"):
            if u == "michael" and p == "123":
                st.session_state.user, st.session_state.role = u, "master"
                st.rerun()
            elif u in ['gabriel', 'italo', 'ellen', 'eduarda'] and p == "123":
                st.session_state.user, st.session_state.role = u, "colaborador"
                st.rerun()
            else: st.error("Acesso negado. Verifique credenciais.")
    st.stop()

is_master = st.session_state.role == "master"

# --- SIDEBAR NAV ---
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user.upper()}")
    st.caption(f"Perfil: {'Gestor Master' if is_master else 'Colaborador'}")
    menu_options = ["🕒 Ponto Digital", "📂 Histórico"]
    if is_master:
        menu_options += ["📊 Gestão Master", "✍️ Lançar Manual", "🤖 IA Intelligence"]
    menu = st.radio("NAVEGAÇÃO", menu_options)
    st.markdown("---")
    if st.button("Encerrar Sessão"):
        st.session_state.user = None
        st.rerun()

# --- MÓDULO: PONTO DIGITAL ---
if menu == "🕒 Ponto Digital":
    st.header("Registro de Ponto")
    tipo = st.segmented_control("Tipo de Batida", ["Entrada", "Saída"], default="Entrada")
    foto = st.camera_input("Validação Facial")
    if st.button("CONFIRMAR REGISTRO"):
        if foto:
            b64 = base64.b64encode(foto.getvalue()).decode()
            db_query("INSERT INTO registros (colaborador, data, hora, tipo, foto) VALUES (?,?,?,?,?)",
                     (st.session_state.user, date.today().isoformat(), datetime.now().strftime("%H:%M:%S"), tipo, b64))
            st.success("✅ Ponto registrado com sucesso!")
            st.balloons()
        else: st.warning("⚠️ Foto obrigatória para validar o ponto.")

# --- MÓDULO: MEU HISTÓRICO ---
elif menu == "📂 Histórico":
    st.header("Meus Lançamentos")
    dados = db_query("SELECT data, hora, tipo FROM registros WHERE colaborador=? ORDER BY data DESC", (st.session_state.user,), True)
    if dados:
        st.dataframe(pd.DataFrame(dados, columns=['Data', 'Hora', 'Tipo']), use_container_width=True)
    else: st.info("Você ainda não possui registros.")

# --- MÓDULO: GESTÃO MASTER ---
elif menu == "📊 Gestão Master" and is_master:
    st.header("Controle de Operações")
    df = pd.DataFrame(db_query("SELECT id, colaborador, data, hora, tipo FROM registros ORDER BY id DESC", fetch=True), 
                      columns=['ID', 'Colaborador', 'Data', 'Hora', 'Tipo'])
    st.dataframe(df, use_container_width=True)
    
    with st.expander("🗑️ Excluir Registro"):
        id_del = st.number_input("Informe o ID", step=1, min_value=0)
        if st.button("EXCLUIR PERMANENTEMENTE"):
            db_query("DELETE FROM registros WHERE id=?", (id_del,))
            st.rerun()

# --- MÓDULO: LANÇAMENTO MANUAL (NOVO) ---
elif menu == "✍️ Lançar Manual" and is_master:
    st.header("Ajuste Manual Administrativo")
    with st.form("form_manual"):
        col1, col2 = st.columns(2)
        m_colab = col1.selectbox("Colaborador", ['michael', 'gabriel', 'italo', 'ellen', 'eduarda'])
        m_data = col2.date_input("Data")
        m_hora = col1.time_input("Hora")
        m_tipo = col2.selectbox("Tipo", ["Entrada", "Saída"])
        if st.form_submit_button("EFETUAR LANÇAMENTO"):
            db_query("INSERT INTO registros (colaborador, data, hora, tipo, foto) VALUES (?,?,?,?,?)",
                     (m_colab, m_data.isoformat(), m_hora.strftime("%H:%M:%S"), m_tipo, ""))
            st.success("Lançamento inserido no banco.")

# --- MÓDULO: IA INTELLIGENCE ---
elif menu == "🤖 IA Intelligence" and is_master:
    st.header("Executive Intelligence Report")
    
    # Cards de Decisão
    c1, c2, c3 = st.columns(3)
    c1.markdown('<div class="metric-card"><h4>Horas Extras</h4><h2 style="color:#FF8C00;">42.5h</h2></div>', unsafe_allow_html=True)
    c2.markdown('<div class="metric-card"><h4>Atrasos Críticos</h4><h2 style="color:#d32f2f;">08</h2></div>', unsafe_allow_html=True)
    c3.markdown('<div class="metric-card"><h4>Eficácia OTIF</h4><h2 style="color:#2e7d32;">98%</h2></div>', unsafe_allow_html=True)

    st.markdown('<div class="insight-card">', unsafe_allow_html=True)
    st.subheader("💡 Insights Dunas Fleet")
    st.markdown("""
    * **ALERTA FINANCEIRO:** Italo Costa excedeu o limite de HE em 15%. Recomenda-se compensação de horas.
    * **PONTUALIDADE:** Gabriel Silva mantém o score mais alto de conformidade matinal (08:00).
    * **DECISÃO:** Escalar Ellen Souza para os Sprints de encerramento de faturamento, onde há maior gargalo de saída.
    """)
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Gráfico de Atividade
    df_vol = pd.DataFrame(db_query("SELECT data, count(*) as total FROM registros GROUP BY data", fetch=True), columns=['data', 'total'])
    if not df_vol.empty:
        st.plotly_chart(px.bar(df_vol, x='data', y='total', title="Volume de Atividade da Equipe", color_discrete_sequence=['#FF8C00']), use_container_width=True)