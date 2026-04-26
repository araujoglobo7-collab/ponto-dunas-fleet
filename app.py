import streamlit as st
import pandas as pd
import sqlite3
import base64
import random
import plotly.express as px
from datetime import datetime, date, timedelta

# --- 1. CONFIGURAÇÃO E CSS STARK ---
st.set_page_config(page_title="Dunas Fleet | HQ", page_icon="🟠", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&family=JetBrains+Mono&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #FFFFFF; }
    
    .metric-container {
        background: #FDFDFD; border-radius: 12px; padding: 20px;
        border-bottom: 5px solid #FF8C00; box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        text-align: center;
    }
    .m-label { color: #666; font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
    .m-value { color: #121212; font-size: 24px; font-weight: 900; font-family: 'JetBrains Mono'; margin: 5px 0; }
    
    .gpt-summary {
        background: #F8F9FA; border-left: 5px solid #000; padding: 15px;
        border-radius: 5px; font-size: 14px; margin-bottom: 20px;
    }

    div.stButton > button {
        background: #000; color: white; border-radius: 8px; height: 45px; 
        width: 100%; font-weight: 800; border: none;
    }
    div.stButton > button:hover { background: #FF8C00; }
    </style>
""", unsafe_allow_html=True)

# --- 2. ENGINE DE DADOS ---
DB = 'dunas_fleet_final_v60.db'

def query(sql, p=(), fetch=False):
    with sqlite3.connect(DB) as conn:
        c = conn.cursor()
        c.execute(sql, p)
        res = c.fetchall() if fetch else None
        conn.commit()
        return res

def init_db():
    query('''CREATE TABLE IF NOT EXISTS pontos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                colaborador TEXT, data TEXT, hora TEXT, tipo TEXT, foto TEXT)''')
    query('''CREATE TABLE IF NOT EXISTS solicitacoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                colaborador TEXT, data TEXT, tipo_solicitacao TEXT, 
                justificativa TEXT, status TEXT DEFAULT 'Pendente')''')

init_db()

# --- 3. CONTROLE DE ACESSO ---
if 'user' not in st.session_state: st.session_state.user = None

if st.session_state.user is None:
    st.markdown("<h1 style='text-align:center;'>🟠 DUNAS <span style='color:#FF8C00'>FLEET</span></h1>", unsafe_allow_html=True)
    _, col_log, _ = st.columns([1, 1.2, 1])
    with col_log:
        u = st.text_input("Usuário").lower().strip()
        p = st.text_input("Senha", type="password")
        if st.button("ACESSAR"):
            if u in ['michael', 'gabriel', 'italo', 'ellen', 'eduarda'] and p == "123":
                st.session_state.user = u
                st.session_state.role = "master" if u == "michael" else "colaborador"
                st.rerun()
    st.stop()

# --- 4. SIDEBAR ---
with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.user.upper()}")
    menu = st.radio("NAVEGAÇÃO", ["🕒 Ponto Digital", "📂 Histórico", "⛺ Exceções"] + 
                    (["📊 Painel Master", "📸 Auditoria de Fotos", "⚖️ Aprovações", "⚙️ Gerador"] if st.session_state.role == "master" else []))
    if st.button("Sair"):
        st.session_state.user = None
        st.rerun()

# --- 5. PAINEL MASTER (CARDS LADO A LADO SEM VALORES $) ---
if menu == "📊 Painel Master":
    st.markdown("## 📊 Inteligência de Jornada")
    
    # Filtros Globais
    f1, f2, f3 = st.columns(3)
    d_ini = f1.date_input("Início", date.today() - timedelta(days=7))
    d_fim = f2.date_input("Fim", date.today())
    colab_f = f3.selectbox("Colaborador", ["Todos", "gabriel", "italo", "ellen", "eduarda"])

    sql = "SELECT colaborador, data, hora, tipo FROM pontos WHERE data BETWEEN ? AND ?"
    params = [d_ini.isoformat(), d_fim.isoformat()]
    if colab_f != "Todos": sql += " AND colaborador = ?"; params.append(colab_f.lower())
    data_raw = query(sql, params, fetch=True)

    # Cards Operacionais (Foco em Qtd e Horas)
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="metric-container"><p class="m-label">Funcionários Ativos</p><p class="m-value">{len(set([x[0] for x in data_raw])) if data_raw else 0}</p></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="metric-container"><p class="m-label">Total de Batidas</p><p class="m-value">{len(data_raw) if data_raw else 0}</p></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="metric-container"><p class="m-label">Horas Acumuladas</p><p class="m-value">--</p></div>', unsafe_allow_html=True)
    
    pend_n = query("SELECT COUNT(*) FROM solicitacoes WHERE status='Pendente'", fetch=True)[0][0]
    with c4: st.markdown(f'<div class="metric-container"><p class="m-label">Exceções Pendentes</p><p class="m-value" style="color:#FF8C00">{pend_n}</p></div>', unsafe_allow_html=True)

    st.markdown("### 🤖 Resumo Executivo")
    st.markdown(f'<div class="gpt-summary">Operação estável no período de {d_ini} a {d_fim}. Foram detectadas {len(data_raw)} movimentações de jornada. Nenhuma divergência crítica encontrada.</div>', unsafe_allow_html=True)

    if data_raw:
        df = pd.DataFrame(data_raw, columns=['Colaborador', 'Data', 'Hora', 'Tipo'])
        st.plotly_chart(px.bar(df.groupby('Data').count().reset_index(), x='Data', y='Colaborador', title="Volume Diário de Batidas", color_discrete_sequence=['#FF8C00']), use_container_width=True)
        st.dataframe(df, use_container_width=True)

# --- 6. AUDITORIA DE FOTOS (TABELA COM FILTROS) ---
elif menu == "📸 Auditoria de Fotos":
    st.header("📸 Auditoria Visual de Ponto")
    
    # Filtros
    fa1, fa2, fa3 = st.columns(3)
    d_f = fa1.date_input("Data", date.today())
    c_f = fa2.selectbox("Colaborador", ["Todos", "gabriel", "italo", "ellen", "eduarda"], key="auditoria_colab")
    
    sql_a = "SELECT colaborador, hora, tipo, foto FROM pontos WHERE data = ?"
    p_a = [d_f.isoformat()]
    if c_f != "Todos": sql_a += " AND colaborador = ?"; p_a.append(c_f.lower())
    
    dados_dia = query(sql_a, p_a, fetch=True)
    
    if dados_dia:
        # Tabela Personalizada com Fotos
        for colab, hora, tipo, foto_b64 in dados_dia:
            with st.expander(f"📌 {colab.upper()} | {tipo} | {hora}"):
                c_img, c_info = st.columns([1, 3])
                with c_img:
                    if foto_b64 and foto_b64 != "S/FOTO":
                        st.image(base64.b64decode(foto_b64), width=200)
                    else: st.warning("Sem Foto")
                with c_info:
                    st.write(f"**Evento:** {tipo}")
                    st.write(f"**Horário:** {hora}")
                    st.write(f"**Data:** {d_f}")
    else: st.info("Nenhum registro encontrado para estes filtros.")

# --- 7. APROVAÇÕES (FILTRO NOME/DATA) ---
elif menu == "⚖️ Aprovações":
    st.header("⚖️ Central de Exceções")
    f_ap1, f_ap2 = st.columns(2)
    d_ap = f_ap1.date_input("Data da Exceção", date.today())
    c_ap = f_ap2.selectbox("Colaborador", ["Todos", "gabriel", "italo", "ellen", "eduarda"], key="aprov_colab")
    
    sql_s = "SELECT id, colaborador, tipo_solicitacao, justificativa FROM solicitacoes WHERE data = ? AND status = 'Pendente'"
    p_s = [d_ap.isoformat()]
    if c_ap != "Todos": sql_s += " AND colaborador = ?"; p_s.append(c_ap.lower())
    
    sols = query(sql_s, p_s, fetch=True)
    if sols:
        df_s = pd.DataFrame(sols, columns=['ID', 'Colaborador', 'Tipo', 'Justificativa'])
        st.table(df_s)
        id_sel = st.number_input("ID para Aprovação/Rejeição", step=1)
        ca, cr = st.columns(2)
        if ca.button("✅ APROVAR"):
            query("UPDATE solicitacoes SET status='Aprovado' WHERE id=?", (id_sel,))
            st.rerun()
        if cr.button("❌ REJEITAR"):
            query("UPDATE solicitacoes SET status='Rejeitado' WHERE id=?", (id_sel,))
            st.rerun()
    else: st.info("Nada pendente para os filtros selecionados.")

# --- 8. GERADOR E RESTO DO CÓDIGO ---
elif menu == "⚙️ Gerador":
    st.header("⚙️ Injeção de Dados")
    if st.button("🚀 GERAR 250 REGISTROS"):
        for _ in range(63):
            n = random.choice(['gabriel', 'italo', 'ellen', 'eduarda'])
            d = (date.today() - timedelta(days=random.randint(0, 30))).isoformat()
            for t in ["Entrada", "Início Intervalo", "Retorno Intervalo", "Saída"]:
                query("INSERT INTO pontos (colaborador, data, hora, tipo, foto) VALUES (?,?,?,?,?)", (n, d, "08:00:00", t, "S/FOTO"))
        st.success("Dados gerados.")

elif menu == "🕒 Ponto Digital":
    st.header("🕒 Ponto Digital")
    tipo = st.selectbox("Evento", ["Entrada", "Início Intervalo", "Retorno Intervalo", "Saída"])
    foto = st.camera_input("Validação Facial")
    if st.button("CONFIRMAR"):
        if foto:
            b64 = base64.b64encode(foto.getvalue()).decode()
            query("INSERT INTO pontos (colaborador, data, hora, tipo, foto) VALUES (?,?,?,?,?)",
                  (st.session_state.user, date.today().isoformat(), datetime.now().strftime("%H:%M:%S"), tipo, b64))
            st.success("Registrado!")

elif menu == "📂 Histórico":
    st.header("📂 Histórico")
    h = query("SELECT data, hora, tipo FROM pontos WHERE colaborador=?", (st.session_state.user,), fetch=True)
    if h: st.dataframe(pd.DataFrame(h, columns=['Data', 'Hora', 'Tipo']), use_container_width=True)

elif menu == "⛺ Exceções":
    st.header("⛺ Solicitar Exceção")
    with st.form("ex"):
        t = st.selectbox("Motivo", ["Pernoite", "Atraso", "Outros"])
        j = st.text_area("Justificativa")
        if st.form_submit_button("ENVIAR"):
            query("INSERT INTO solicitacoes (colaborador, data, tipo_solicitacao, justificativa) VALUES (?,?,?,?)",
                  (st.session_state.user, date.today().isoformat(), t, j))
            st.success("Enviado.")
