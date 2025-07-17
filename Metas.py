import streamlit as st
import pandas as pd
from supabase import create_client, Client

# Configurações do Supabase
SUPABASE_URL = 'https://kmnrrqwgawojqntixfsf.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImttbnJycXdnYXdvanFudGl4ZnNmIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDI1MDc5OTAsImV4cCI6MjA1ODA4Mzk5MH0.u8wxqBqJ1QI6zvSA74uvoQhxJBRoAOPeDLy_PqGgpuA'
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Usuários definidos no código
usuarios = {
    "master": {"senha": "admin123", "area": "master"},
    "centro": {"senha": "senha1", "area": "CENTRO"},
    "regional2": {"senha": "senha2", "area": "CONTINENTE"},
}

st.set_page_config(layout="wide")

def login():
    st.title("Sistema de Redistribuição de Metas")
    st.header("Login")

    usuario = st.text_input("Usuário")
    senha = st.text_input("Senha", type="password")

    if st.button("Entrar"):
        if usuario not in usuarios or usuarios[usuario]["senha"] != senha:
            st.error("Usuário ou senha inválidos.")
        else:
            # Salva info no session_state
            st.session_state["usuario_logado"] = usuario
            st.session_state["area_usuario"] = usuarios[usuario]["area"]
            st.rerun()  # Força reload para mostrar app principal

def main_app():
    usuario_logado = st.session_state["usuario_logado"]
    area_usuario = st.session_state["area_usuario"]

    st.title("Sistema de Redistribuição de Metas")
    st.success(f"Bem-vindo, Área: {usuario_logado.upper()}!")

    # Botão logout
    if st.button("Logout"):
        st.session_state.pop("usuario_logado")
        st.session_state.pop("area_usuario")
        st.rerun()

    # Buscar dados da tabela Metas
    resposta = supabase.table('Metas').select('*').execute()
    dados_iniciais = resposta.data

    if not dados_iniciais:
        st.error("Nenhuma meta encontrada no Supabase.")
        st.stop()

    df = pd.DataFrame(dados_iniciais)
    df["valor_ajustado"] = df["valor_atrib"]

    # Limitar área para usuários não master
    if area_usuario != 'master':
        df = df[df["area"] == area_usuario]
        areas_disponiveis = [area_usuario]
    else:
        areas_disponiveis = sorted(df["area"].unique())

    regionais_disponiveis = sorted(df["regional"].unique())

    # Filtros lado a lado
    col_filtros = st.columns(2)
    filtro_area = col_filtros[0].selectbox("Filtrar por Área:", options=["Todas"] + areas_disponiveis)
    filtro_regional = col_filtros[1].selectbox("Filtrar por Regional:", options=["Todas"] + regionais_disponiveis)

    # Aplicar filtro
    df_filtrado = df.copy()
    if filtro_area != "Todas":
        df_filtrado = df_filtrado[df_filtrado["area"] == filtro_area]
    if filtro_regional != "Todas":
        df_filtrado = df_filtrado[df_filtrado["regional"] == filtro_regional]

    if df_filtrado.empty:
        st.warning("Nenhuma loja encontrada para os filtros selecionados.")
        st.stop()

    
     # Atualiza 'valor_ajustado' no DataFrame com os valores atuais dos widgets number_input
    for index, row in df_filtrado.iterrows():
        valor_ajustado = st.session_state.get(f"input_{index}", int(row["valor_ajustado"]))
        df_filtrado.at[index, "valor_ajustado"] = valor_ajustado

    # Calcula KPIs com os valores atualizados
    total_meta = df_filtrado["valor_atrib"].sum()
    total_ajustado = df_filtrado["valor_ajustado"].sum()
    saldo_restante = total_meta - total_ajustado

    st.divider()
    col_kpi1, col_kpi2 = st.columns(2)
    col_kpi1.metric("Alvo Total R$", f"R$ {total_meta:,.0f}".replace(",", "."))
    col_kpi2.metric("Saldo Restante", f"R$ {saldo_restante:,.0f}".replace(",", "."))
    st.divider()

    # Cabeçalho da Tabela (centralizado)
    colunas = st.columns([3, 5, 5, 5, 5, 4, 4])
    titulos = [
        "Loja", "Venda Mês Ant(R$)", "Venda Ano Ant(R$)",
        "Meta Sugerida (R$)", "Valor Ajustado (R$)",
        "% Cresc. Mês Ant", "% Cresc. Ano Ant"
    ]

    for col, titulo in zip(colunas, titulos):
        col.markdown(f"""
            <div style='
                background-color:#003366;
                color:white;
                font-weight:bold;
                text-align:center;
                display:flex;
                justify-content:center;
                align-items:center;
                height:60px;
                border-radius:4px;
            '>{titulo}</div>
        """, unsafe_allow_html=True)

    # Linhas da Tabela
    for index, row in df_filtrado.iterrows():
        c1, c2, c3, c4, c5, c6, c7 = st.columns([3, 5, 5, 5, 5, 4, 4])

        c1.markdown(f"<div style='text-align:center; padding:10px 0;'>{row['Loja']}</div>", unsafe_allow_html=True)
        c2.markdown(f"<div style='text-align:center; padding:10px 0;'>R$ {row['venda_ma']:,.0f}</div>", unsafe_allow_html=True)
        c3.markdown(f"<div style='text-align:center; padding:10px 0;'>R$ {row['venda_aa']:,.0f}</div>", unsafe_allow_html=True)
        c4.markdown(f"<div style='text-align:center; padding:10px 0;'>R$ {row['valor_atrib']:,.0f}</div>", unsafe_allow_html=True)

        valor_ajustado = c5.number_input(
            label="",
            min_value=0,
            value=int(row["valor_ajustado"]),
            step=1,
            key=f"input_{index}"
        )

        crescimento_mes = (valor_ajustado / row['venda_ma'] - 1) if row['venda_ma'] != 0 else 0
        crescimento_ano = (valor_ajustado / row['venda_aa'] - 1) if row['venda_aa'] != 0 else 0

        c6.markdown(f"<div style='text-align:center; padding:10px 0;'>{crescimento_mes:.2%}</div>", unsafe_allow_html=True)
        c7.markdown(f"<div style='text-align:center; padding:10px 0;'>{crescimento_ano:.2%}</div>", unsafe_allow_html=True)

        st.markdown("<div style='border-top: 1px solid #CCC; margin:8px 0;'></div>", unsafe_allow_html=True)

    # Exportar CSV
    df_exportar = df_filtrado.copy()
    df_exportar["% Cresc. Mês Anterior"] = df_exportar.apply(
        lambda row: (row["valor_ajustado"] / row["venda_ma"] - 1) if row["venda_ma"] != 0 else 0,
        axis=1
    )
    df_exportar["% Cresc. Ano Anterior"] = df_exportar.apply(
        lambda row: (row["valor_ajustado"] / row["venda_aa"] - 1) if row["venda_aa"] != 0 else 0,
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

    csv = df_exportar_final.to_csv(index=False, sep=";", decimal=",")

    st.divider()

    st.download_button(
        label="📥 Baixar Tabela como CSV",
        data=csv,
        file_name='metas_distribuidas.csv',
        mime='text/csv'
    )

    if st.button("Salvar Distribuição"):
        saldo_restante = df_filtrado["valor_atrib"].sum() - df_filtrado["valor_ajustado"].sum()
        if saldo_restante != 0:
            st.error("A redistribuição está incorreta! Ajuste para zerar o saldo restante.")
        else:
            registros = df_filtrado.to_dict(orient="records")
            for registro in registros:
                supabase.table("metas_ajustadas").insert(registro).execute()
            st.success("Distribuição salva no Supabase!")

if "usuario_logado" not in st.session_state:
    login()
else:
    main_app()