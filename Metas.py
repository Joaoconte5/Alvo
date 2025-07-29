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
    "regional1": {"senha": "senha1", "regional": "REGIONAL 1"},
    "centro": {"senha": "senha1", "area": "CENTRO"},
    "extremosul": {"senha": "senha1", "area": "EXTREMO SUL"},
    "caxias": {"senha": "senha1", "area": "CAXIAS"},
    "regional2": {"senha": "senha2", "area": "CONTINENTE"},
}

# --- Funções de Autenticação --- #
# --- Funções de Autenticação --- #
def login():
    st.title("Revisão de alvos - Áreas de coordenação")
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
# Removendo o cache para get_metas_data para garantir que os dados sejam sempre atualizados
# Alternativamente, poderíamos usar st.cache_data(ttl=algum_tempo) e adicionar um botão para invalidar o cache
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
            # Preencher quaisquer NaN com 0 antes de converter para dicionário
            # Isso é crucial para evitar o erro "Out of range float values are not JSON compliant: nan"
            df_para_salvar = df_filtrado[[
                "Loja", "venda_ma", "venda_aa", "valor_atrib", "valor_ajustado", "area", "regional"
            ]].astype({
                "venda_ma": float, "venda_aa": float, "valor_atrib": float, "valor_ajustado": float
            }).fillna(0) # Preenche NaN com 0

            registros_para_salvar = df_para_salvar.to_dict(orient="records")

            # Inserir no Supabase
            for registro in registros_para_salvar:
                # O Supabase pode precisar de um ID único ou de uma estratégia de upsert
                supabase.table("Metas").upsert(registro, on_conflict="Loja").execute()
            st.success("Distribuição salva no Supabase!")
            # Invalida o cache de dados após salvar para garantir que a próxima busca seja atualizada
            # get_metas_data.clear()
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
    saldo_restante =  total_ajustado - total_meta
    st.divider()
    col_kpi1, col_kpi2 = st.columns(2)
    col_kpi1.metric("Alvo Total R$", format_currency(total_meta))

    # Estilização condicional para o Saldo Restante
    color = "green" if saldo_restante >= 0 else "red"
    col_kpi2.markdown(f"""
        <div style='text-align: center;'>
            <div style='font-size: 14px; color: grey;'>Saldo Restante</div>
            <div style='font-size: 36px; font-weight: bold; color: {color};'>
                {format_currency(saldo_restante)}
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.divider()

def render_table_header():
    colunas = st.columns([3, 5, 5, 5, 5, 4, 4])
    titulos = [
        "Loja",  "Venda Ano Ant(R$)", "Venda Projetado Julho(R$)",
        "Meta Sugerida (R$)", "Valor Ajustado (R$)",
        "% Cresc. Mês Ant", "% Evol. Ano Ant"
    ]

    for col, titulo in zip(colunas, titulos):
        col.markdown(f"""
            <div style=\'background-color:#003366; color:white; font-weight:bold; text-align:center; display:flex; justify-content:center; align-items:center; height:60px; border-radius:4px;\'>
            {titulo}</div>
        """, unsafe_allow_html=True)

def render_table_rows(df_filtrado):
    # Criar uma cópia do DataFrame para armazenar os valores ajustados da sessão
    df_para_renderizar = df_filtrado.copy()

    for index, row in df_para_renderizar.iterrows():
        c1, c2, c3, c4, c5, c6, c7 = st.columns([3, 5, 5, 5, 5, 4, 4])

        c1.markdown(f"<div style=\'text-align:center; padding:10px 0;\'>{row['Loja']}</div>", unsafe_allow_html=True)
        c2.markdown(f"<div style=\'text-align:center; padding:10px 0;\'>{format_currency(row['venda_aa'])}</div>", unsafe_allow_html=True)
        c3.markdown(f"<div style=\'text-align:center; padding:10px 0;\'>{format_currency(row['venda_ma'])}</div>", unsafe_allow_html=True)
        c4.markdown(f"<div style=\'text-align:center; padding:10px 0;\'>{format_currency(row['valor_atrib'])}</div>", unsafe_allow_html=True)

        key_loja = "input_" + str(row["Loja"])
        # O valor inicial do number_input deve vir do st.session_state para persistência
        # Se não estiver no session_state, usa o valor inicial do DataFrame
        current_valor_ajustado = st.session_state.get(key_loja, int(row["valor_atrib"]))

        valor_ajustado = c5.number_input(
            label="",
            min_value=0,
            value=current_valor_ajustado,
            step=1,
            key=key_loja # Usando a chave única para persistência
        )
        # Atualiza o valor ajustado no DataFrame de renderização para cálculos subsequentes
        df_para_renderizar.at[index, "valor_ajustado"] = valor_ajustado

        crescimento_mes = calculate_growth(valor_ajustado, row['venda_ma'])
        crescimento_ano = calculate_growth(valor_ajustado, row['venda_aa'])

        c6.markdown(f"<div style=\'text-align:center; padding:10px 0;\'>{crescimento_mes:.2%}</div>", unsafe_allow_html=True)
        c7.markdown(f"<div style=\'text-align:center; padding:10px 0;\'>{crescimento_ano:.2%}</div>", unsafe_allow_html=True)

        st.markdown("<div style=\'border-top: 1px solid #CCC; margin:8px 0;\'></div>", unsafe_allow_html=True)

    return df_para_renderizar # Retorna o DataFrame atualizado com os valores da sessão

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

    st.title("Revisão de alvos - Áreas de coordenação")
    st.success(f"Bem-vindo, Área: {area_usuario.upper()}!")

    if st.button("Logout"):
        logout()

    # Adicionando um botão para recarregar os dados manualmente
    if st.button("Recarregar Dados do Supabase"):
        # Limpa o cache de dados, se houver
        # st.cache_data.clear()
        st.rerun() # Força uma nova execução do script para recarregar os dados

    dados_iniciais = get_metas_data()

    if not dados_iniciais:
        st.warning("Nenhuma meta encontrada ou erro ao carregar dados.")
        st.stop()

    df = pd.DataFrame(dados_iniciais)
    # Inicializa 'valor_ajustado' com 'valor_atrib' ou com o valor salvo na sessão
    # Isso garante que os valores ajustados persistam entre as reruns
    df['valor_ajustado'] = df.apply(lambda row: st.session_state.get(f"input_{row['Loja']}", row['valor_atrib']), axis=1)

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
    # O total_ajustado agora é calculado a partir do df_filtrado que já contém os valores da sessão
    total_ajustado = df_filtrado["valor_ajustado"].sum()

    render_kpis(total_meta, total_ajustado)
    render_table_header()
    # render_table_rows não precisa mais retornar o df_filtrado, pois as alterações já estão no session_state
    render_table_rows(df_filtrado) 

    st.divider()

    export_csv_button(df_filtrado)

    if st.button("Salvar Distribuição"):
        save_distribuicao(df_filtrado)

# --- Fluxo Principal da Aplicação --- #

if "usuario_logado" not in st.session_state:
    login()
else:
    main_app()
