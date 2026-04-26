import streamlit as st
import pandas as pd
import sqlite3
import base64
from datetime import datetime, date, timedelta
from streamlit_js_eval import streamlit_js_eval

# --- CONFIGURAÇÃO DUNAS FLEET ---
st.set_page_config(page_title="Dunas Fleet | Intelligence", page_icon="🟠", layout="wide")

# --- CSS PREMIUM ESTILO BRUXO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #FFFFFF; }
    .cost-card {
        background: #F8F9FA; padding: 20px; border-radius: 12px;
        border-top: 5px solid #FF8C00; text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .he-value { color: #D32F2F; font-size: 26px; font-weight: 700; }
    .insight-card {
        background: #FFF3E0; padding: 25px; border-radius: 15px;
        border-left: 8px solid #FF8C00; margin-bottom: 20px;
    }
    div.stButton > button {
        background-color: #000; color: white; border-radius: 10px; height: 50px; width: 100%;
    }
    div.stButton > button:hover { background-color: #FF8C00; }
    </style>
""", unsafe_allow_html=True)

# --- ENGINE DE DADOS ---
def db_query(query, params=(), fetch=False):
    with sqlite3.connect('dunas_fleet_v18.db') as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetch: return cursor.fetchall()
        conn.commit()

def init_db():
    db_query('''CREATE TABLE IF NOT EXISTS registros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                colaborador TEXT, data TEXT, hora TEXT, tipo TEXT, foto TEXT, 
                local_manual TEXT, gps_coords TEXT)''')
    db_query('''CREATE TABLE IF NOT EXISTS excecoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                colaborador TEXT, data TEXT, hora TEXT, local TEXT, tipo_excecao TEXT, 
                justificativa TEXT, gps TEXT, status TEXT)''')
init_db()

# --- LOGIN ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    st.markdown("<h1 style='text-align:center; color:#000;'>🟠 DUNAS <span style='color:#FF8C00'>FLEET</span></h1>", unsafe_allow_html=True)
    _, col_log, _ = st.columns([1, 1.5, 1])
    with col_log:
        u = st.text_input("Usuário").lower().strip()
        p = st.text_input("Senha", type="password")
        if st.button("ACESSAR"):
            if u in ['michael', 'gabriel', 'italo', 'ellen', 'eduarda'] and p == "123":
                st.session_state.user = u
                st.session_state.role = "master" if u == "michael" else "colaborador"
                st.rerun()
    st.stop()

# --- GPS ---
loc_gps = streamlit_js_eval(js_expressions="navigator.geolocation.getCurrentPosition(pos => { window.eth = pos.coords.latitude + ',' + pos.coords.longitude; }); window.eth", key="gps_v18")

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user.upper()}")
    menu = st.radio("NAVEGAÇÃO", ["🕒 Ponto Digital", "⛺ Pernoite/Exceção", "📂 Histórico"] + (["📊 Auditoria Master", "🤖 Resumo de Custos"] if st.session_state.role == "master" else []))
    if st.button("Sair"):
        st.session_state.user = None
        st.rerun()

# --- MÓDULO: PONTO DIGITAL ---
if menu == "🕒 Ponto Digital":
    st.header("Registro de Jornada")
    tipo = st.selectbox("Evento", ["Entrada", "Início Intervalo", "Retorno Intervalo", "Saída Final"])
    local = st.text_input("📍 Local Informado")
    foto = st.camera_input("Validação")
    if st.button("CONFIRMAR BATIDA"):
        if foto and local and loc_gps:
            b64 = base64.b64encode(foto.getvalue()).decode()
            db_query("INSERT INTO registros (colaborador, data, hora, tipo, foto, local_manual, gps_coords) VALUES (?,?,?,?,?,?,?)",
                     (st.session_state.user, date.today().isoformat(), datetime.now().strftime("%H:%M:%S"), tipo, b64, local, loc_gps))
            st.success("✅ Registrado.")
        else: st.warning("⚠️ GPS/Foto/Local obrigatórios.")

# --- MÓDULO: PERNOITE ---
elif menu == "⛺ Pernoite/Exceção":
    st.header("Registro de Exceção")
    with st.form("ex_form"):
        t_ex = st.selectbox("Tipo", ["Pernoite", "Refeição em Rota", "Desvio de Percurso"])
        l_ex = st.text_input("📍 Local da Parada")
        j_ex = st.text_area("Justificativa")
        if st.form_submit_button("ENVIAR"):
            if l_ex and loc_gps:
                db_query("INSERT INTO excecoes (colaborador, data, hora, local, tipo_excecao, justificativa, gps, status) VALUES (?,?,?,?,?,?,?,?)",
                         (st.session_state.user, date.today().isoformat(), datetime.now().strftime("%H:%M:%S"), l_ex, t_ex, j_ex, loc_gps, "Pendente"))
                st.success("✅ Enviado.")

# --- MÓDULO: IA & CUSTOS (BASEADO NOS DADOS REAIS) ---
elif menu == "🤖 Resumo de Custos" and st.session_state.role == "master":
    st.header("Análise de Custo Operacional")
    
    # Busca dados reais para o cálculo
    hoje = date.today().isoformat()
    registros_hoje = db_query("SELECT hora, colaborador FROM registros WHERE data=? AND tipo='Saída Final'", (hoje,), True)
    pernoites_hoje = db_query("SELECT id FROM excecoes WHERE data=?", (hoje,), True)
    
    # Lógica de Hora Extra Real (Baseada em Saída > 18:00)
    total_he_minutos = 0
    for r in registros_hoje:
        h_saida = datetime.strptime(r[0], "%H:%M:%S")
        h_limite = datetime.strptime("18:00:00", "%H:%M:%S")
        if h_saida > h_limite:
            diff = (h_saida - h_limite).seconds / 60
            total_he_minutos += diff
    
    total_he_formatado = f"{int(total_he_minutos // 60)}h {int(total_he_minutos % 60)}m"
    
    c1, c2, c3 = st.columns(3)
    c1.markdown(f'<div class="cost-card"><h4>Horas Extras (Hoje)</h4><span class="he-value">{total_he_formatado}</span></div>', unsafe_allow_html=True)
    c2.markdown(f'<div class="cost-card"><h4>Exceções Registradas</h4><span class="he-value" style="color:#000;">{len(pernoites_hoje)}</span></div>', unsafe_allow_html=True)
    c3.markdown(f'<div class="cost-card"><h4>Custo Estimado HE</h4><span class="he-value" style="color:#FF8C00;">R$ {round((total_he_minutos/60)*45, 2)}</span></div>', unsafe_allow_html=True)

    st.markdown('<div class="insight-card">', unsafe_allow_html=True)
    st.subheader("🤖 IA Strategic Insight")
    
    if total_he_minutos > 0:
        st.markdown(f"**Alerta de Jornada:** Identificamos um excedente de **{total_he_formatado}** em horas extras registradas no sistema hoje.")
        # Pega o local mais frequente dos dados reais
        locais = db_query("SELECT local_manual FROM registros WHERE data=?", (hoje,), True)
        if locais:
            top_local = max(set(locais), key=locais.count)[0]
            st.markdown(f"**Gargalo Operacional:** A maior parte das atividades está concentrada em **{top_local}**.")
    else:
        st.markdown("✅ **Operação dentro do horário:** Não foram detectados desvios de custo por hora extra até o momento.")
    
    st.markdown(f"**Integridade:** {len(db_query('SELECT id FROM registros WHERE data=?', (hoje,), True))} batidas validadas via GPS.")
    st.markdown('</div>', unsafe_allow_html=True)

# --- AUDITORIA ---
elif menu == "📊 Auditoria Master" and st.session_state.role == "master":
    st.header("Painel Michael")
    df_reg = pd.DataFrame(db_query("SELECT colaborador, hora, tipo, local_manual, gps_coords FROM registros ORDER BY id DESC", fetch=True), 
                          columns=['Colaborador', 'Hora', 'Tipo', 'Local', 'GPS'])
    st.dataframe(df_reg, use_container_width=True)
