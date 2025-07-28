import streamlit as st
import pandas as pd
from supabase import create_client, Client
import os

st.set_page_config(layout="wide")

# --- Configurações --- #
# Usar variáveis de ambiente para credenciais do Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://kmnrrqwgawojqntixfsf.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImttbnJycXdnYXdvanFudGl4ZnNmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDI1MDc5OTAsImV4cCI6MjA1ODA4Mzk5MH0.u8wxqBqJ1QI6zvSA74uvoQhxJBRoAOPeDLy_PqGgpuA")

# Inicializa o cliente Supabase
@st.cache_resource
def init_supabase_client():
    try:
        return create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        st.error(f"Erro ao conectar ao Supabase: {e}")
        st.stop()

supabase: Client = init_supabase_client()

# Usuários definidos no código (idealmente, isso viria de um banco de dados ou serviço de autenticação)
USUARIOS = {
    "master": {"senha": "admin123", "area": "master"},
    "centro": {"senha": "senha1", "area": "CENTRO"},
    "regional2": {"senha": "senha2", "area": "CONTINENTE"},
}

# --- Funções de Autenticação --- #
def login():
    st.title("Sistema de Redistribuição de Metas")
    st.header("Login")

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if usuario not in USUARIOS or USUARIOS[usuario]["senha"] != senha:
            st.error("Usuário ou senha inválidos.")
        else:
            st.session_state["usuario_logado"] = usuario
            st.session_state["area_usuario"] = USUARIOS[usuario]["area"]
            st.rerun()

def logout():
    st.session_state.pop("usuario_logado", None)
    st.session_state.pop("area_usuario", None)
    st.rerun()

# --- Funções de Dados --- #
@st.cache_data(ttl=600) # Cache por 10 minutos
def get_metas_data():
    try:
        resposta = supabase.table("Metas").select("*").execute()
        return resposta.data
    except Exception as e:
        st.error(f"Erro ao buscar metas do Supabase: {e}")
        return None

def save_distribuicao(df_filtrado):
    saldo_restante = df_filtrado["valor_atrib"].sum() - df_filtrado["valor_ajustado"].sum()
    if saldo_restante != 0:
        st.error("A redistribuição está incorreta! Ajuste para zerar o saldo restante.")
        return False
    else:
        try:
            # Preparar dados para inserção, removendo colunas desnecessárias ou ajustando nomes
            registros_para_salvar = df_filtrado[[
                "Loja", "venda_ma", "venda_aa", "valor_atrib", "valor_ajustado", "area", "regional"
            ]].astype({
                "venda_ma": float, "venda_aa": float, "valor_atrib": float, "valor_ajustado": float
            }).to_dict(orient="records")

            # Inserir no Supabase
            for registro in registros_para_salvar:
                # O Supabase pode precisar de um ID único ou de uma estratégia de upsert
                supabase.table("Metas").upsert(registro, on_conflict="Loja").execute()
            st.success("Distribuição salva no Supabase!")
            return True
        except Exception as e:
            st.error(f"Erro ao salvar distribuição no Supabase: {e}")
            if hasattr(e, 'message'):
                st.error(f"Detalhes do erro do Supabase: {e.message}")
            elif hasattr(e, 'json'):
                st.error(f"Detalhes do erro do Supabase (JSON): {e.json()}")
            return False

# --- Funções de UI/Renderização --- #
def format_currency(value):
    return f"R$ {value:,.0f}".replace(",", ".")

def calculate_growth(current, previous):
    if previous == 0:
        return 0
    return (current / previous - 1)

def render_kpis(total_meta, total_ajustado):
    saldo_restante = total_meta - total_ajustado
    st.divider()
    col_kpi1, col_kpi2 = st.columns(2)
    col_kpi1.metric("Alvo Total R$", format_currency(total_meta))
    col_kpi2.metric("Saldo Restante", format_currency(saldo_restante))
    st.divider()

def render_table_header():
    colunas = st.columns([3, 5, 5, 5, 5, 4, 4])
    titulos = [
        "Loja", "Venda Mês Ant(R$)", "Venda Ano Ant(R$)",
        "Meta Sugerida (R$)", "Valor Ajustado (R$)",
        "% Cresc. Mês Ant", "% Cresc. Ano Ant"
    ]

    for col, titulo in zip(colunas, titulos):
        col.markdown(f"""
            <div style=\'background-color:#003366; color:white; font-weight:bold; text-align:center; display:flex; justify-content:center; align-items:center; height:60px; border-radius:4px;\'>
            {titulo}</div>
        """, unsafe_allow_html=True)

def format_currency(value):
    try:
        if pd.isna(value):
            return "R$ 0"
        return f"R$ {float(value):,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return "R$ 0"

def render_table_rows(df_filtrado):
    # Força as colunas a serem numéricas
    df_filtrado['venda_ma'] = pd.to_numeric(df_filtrado['venda_ma'], errors='coerce')
    df_filtrado['venda_aa'] = pd.to_numeric(df_filtrado['venda_aa'], errors='coerce')
    df_filtrado['valor_atrib'] = pd.to_numeric(df_filtrado['valor_atrib'], errors='coerce')

    for index, row in df_filtrado.iterrows():
        c1, c2, c3, c4, c5, c6, c7 = st.columns([3, 5, 5, 5, 5, 4, 4])

        c1.markdown(f"<div style='text-align:center; padding:10px 0;'>{row.get('Loja', '')}</div>", unsafe_allow_html=True)
        c2.markdown(f"<div style='text-align:center; padding:10px 0;'>{format_currency(row.get('venda_ma'))}</div>", unsafe_allow_html=True)
        c3.markdown(f"<div style='text-align:center; padding:10px 0;'>{format_currency(row.get('venda_aa'))}</div>", unsafe_allow_html=True)
        c4.markdown(f"<div style='text-align:center; padding:10px 0;'>{format_currency(row.get('valor_atrib'))}</div>", unsafe_allow_html=True)


        # Garante que o valor inicial do number_input seja um inteiro
        # O valor do number_input deve vir do st.session_state para persistência
        # Se não estiver no session_state, usa o valor inicial do DataFrame
        key_loja = "input_" + str(row["Loja"])
        current_valor_ajustado = st.session_state.get(key_loja, int(row["valor_ajustado"]))
        valor_ajustado = c5.number_input(
            label="",
            min_value=0,
            value=current_valor_ajustado,
            step=1,
            key=key_loja # Usando a chave única para persistência
        )
        # Atualiza o valor ajustado no DataFrame para cálculos subsequentes
        df_filtrado.at[index, "valor_ajustado"] = valor_ajustado
        crescimento_mes = calculate_growth(valor_ajustado, row['venda_ma'])
        crescimento_ano = calculate_growth(valor_ajustado, row['venda_aa'])

        c6.markdown(f"<div style=\'text-align:center; padding:10px 0;\'>{crescimento_mes:.2%}</div>", unsafe_allow_html=True)
        c7.markdown(f"<div style=\'text-align:center; padding:10px 0;\'>{crescimento_ano:.2%}</div>", unsafe_allow_html=True)

        st.markdown("<div style=\'border-top: 1px solid #CCC; margin:8px 0;\'></div>", unsafe_allow_html=True)

    return df_filtrado # Retorna o DataFrame atualizado

def export_csv_button(df_filtrado):
    df_exportar = df_filtrado.copy()
    df_exportar["% Cresc. Mês Anterior"] = df_exportar.apply(
        lambda row: calculate_growth(row["valor_ajustado"], row["venda_ma"]),
        axis=1
    )
    df_exportar["% Cresc. Ano Anterior"] = df_exportar.apply(
        lambda row: calculate_growth(row["valor_ajustado"], row["venda_aa"]),
        axis=1
    )

    df_exportar_final = df_exportar[[
        "Loja", "venda_ma", "venda_aa", "valor_atrib", "valor_ajustado",
        "% Cresc. Mês Anterior", "% Cresc. Ano Anterior"
    ]].rename(columns={
        "Loja": "Loja",
        "venda_ma": "Mês Anterior (R$)",
        "venda_aa": "Ano Anterior (R$)",
        "valor_atrib": "Meta Sugerida (R$)",
        "valor_ajustado": "Valor Ajustado (R$)"
    })

    csv = df_exportar_final.to_csv(index=False, sep=";", decimal=",").encode("utf-8")

    st.download_button(
        label="📥 Baixar Tabela como CSV",
        data=csv,
        file_name="metas_distribuidas.csv",
        mime="text/csv"
    )

def main_app():
    usuario_logado = st.session_state.get("usuario_logado")
    area_usuario = st.session_state.get("area_usuario")

    st.title("Sistema de Redistribuição de Metas")
    st.success(f"Bem-vindo, Área: {area_usuario.upper()}!")

    if st.button("Logout"):
        logout()

    dados_iniciais = get_metas_data()

    if not dados_iniciais:
        st.warning("Nenhuma meta encontrada ou erro ao carregar dados.")
        st.stop()

    df = pd.DataFrame(dados_iniciais)
    df["valor_ajustado"] = df["valor_atrib"]

    if area_usuario != "master":
        df = df[df["area"] == area_usuario]
        areas_disponiveis = [area_usuario]
    else:
        areas_disponiveis = sorted(df["area"].unique())

    regionais_disponiveis = sorted(df["regional"].unique())

    col_filtros = st.columns(2)
    filtro_area = col_filtros[0].selectbox("Filtrar por Área:", options=["Todas"] + areas_disponiveis)
    filtro_regional = col_filtros[1].selectbox("Filtrar por Regional:", options=["Todas"] + regionais_disponiveis)

    df_filtrado = df.copy()
    if filtro_area != "Todas":
        df_filtrado = df_filtrado[df_filtrado["area"] == filtro_area]
    if filtro_regional != "Todas":
        df_filtrado = df_filtrado[df_filtrado["regional"] == filtro_regional]

    if df_filtrado.empty:
        st.warning("Nenhuma loja encontrada para os filtros selecionados.")
        st.stop()



    total_meta = df_filtrado["valor_atrib"].sum()
    total_ajustado = df_filtrado["valor_ajustado"].sum()

    render_kpis(total_meta, total_ajustado)
    render_table_header()
    df_filtrado = render_table_rows(df_filtrado) # Passa e recebe o DataFrame atualizado

    st.divider()

    export_csv_button(df_filtrado)

    if st.button("Salvar Distribuição"):
        save_distribuicao(df_filtrado)

# --- Fluxo Principal da Aplicação --- #

if "usuario_logado" not in st.session_state:
    login()
else:
    main_app()
