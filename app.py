import streamlit as st
import pandas as pd

# --- Configuração da Página ---
st.set_page_config(layout="wide")

# --- Título e Cabeçalho ---
st.title('Observatório de Teresópolis 🏛️')
st.write('Análise de Projetos de Lei da Câmara de Vereadores - 2025')

# --- Carregamento dos Dados ---
@st.cache_data
def carregar_dados():
    try:
        df = pd.read_csv('base_observatorio_teresopolis.csv')
        # Garante que a coluna de data seja tratada como data
        df['Data Sessão'] = pd.to_datetime(df['Data Sessão'])
        return df
    except FileNotFoundError:
        return None

df = carregar_dados()

if df is None:
    st.error("ERRO: Ficheiro 'base_observatorio_teresopolis.csv' não encontrado.")
    st.info("Por favor, certifique-se de que o ficheiro CSV está na mesma pasta que este script `app.py`.")
else:
    # --- Barra Lateral de Filtros ---
    st.sidebar.header('Filtros Interativos')

    autores = sorted(df['Autor'].unique())
    autor_selecionado = st.sidebar.multiselect('Selecione o(s) Autor(es):', options=autores, default=[])

    status_disponiveis = sorted(df['Status'].unique())
    status_selecionado = st.sidebar.multiselect('Selecione o(s) Status:', options=status_disponiveis, default=[])

    # --- Aplicação dos Filtros ---
    df_filtrado = df
    if autor_selecionado:
        df_filtrado = df_filtrado[df_filtrado['Autor'].isin(autor_selecionado)]
    if status_selecionado:
        df_filtrado = df_filtrado[df_filtrado['Status'].isin(status_selecionado)]

    # --- Indicadores Principais (KPIs) ---
    st.header('Resumo Geral (com base nos filtros)')
    col1, col2, col3 = st.columns(3)
    col1.metric("Total de Eventos de PLs", len(df_filtrado))
    if not df_filtrado.empty:
        col2.metric("Vereador Mais Ativo", df_filtrado['Autor'].value_counts().idxmax())
    else:
        col2.metric("Vereador Mais Ativo", "N/A")
    col3.metric("Total de PLs Únicos", df_filtrado['PL'].nunique())

    # --- Tabela de Dados Principal ---
    st.header('Eventos Registados nas Sessões')
    st.dataframe(df_filtrado)

    # --- NOVIDADE: Linha do Tempo do Projeto de Lei ---
    st.header('Linha do Tempo de um Projeto de Lei')

    # Menu para selecionar um PL específico de toda a base de dados
    lista_pls_unicos = sorted(df['PL'].unique())
    pl_selecionado = st.selectbox('Selecione um PL para ver seu histórico completo:', options=lista_pls_unicos)

    if pl_selecionado:
        # Filtra a base de dados ORIGINAL para encontrar todos os eventos desse PL
        historico_pl = df[df['PL'] == pl_selecionado].sort_values(by='Data Sessão')

        # Encontra o status mais recente
        status_atual = historico_pl.iloc[-1]['Status']
        autor_pl = historico_pl.iloc[-1]['Autor']

        st.subheader(f"Histórico do PL {pl_selecionado}")
        st.write(f"**Autor:** {autor_pl}")
        st.write(f"**Status Mais Recente:** {status_atual}")

        # Mostra a tabela do histórico, apenas com as colunas relevantes
        st.table(historico_pl[['Data Sessão', 'Status', 'Fonte']])

    # --- Visualizações Gráficas ---
    # (O restante do código para gráficos permanece o mesmo)
    st.header('Visualizações Gráficas')
    if not df_filtrado.empty:
        st.subheader('Contagem de Eventos de PLs por Autor')
        contagem_autoria = df_filtrado['Autor'].value_counts()
        st.bar_chart(contagem_autoria)

        st.subheader('Distribuição de Eventos por Status')
        contagem_status = df_filtrado['Status'].value_counts()
        st.bar_chart(contagem_status)
    else:
        st.warning("Nenhum dado encontrado para os filtros selecionados.")