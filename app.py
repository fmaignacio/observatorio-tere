
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import numpy as np

# --- Configuração da Página ---
st.set_page_config(
    page_title="Observatório Teresópolis",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS Customizado ---
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f4788;
        text-align: center;
        margin-bottom: 1rem;
        font-weight: bold;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 24px;
        background-color: #f0f2f6;
        border-radius: 10px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #1f4788;
        color: white;
    }
    .timeline-container {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# --- Cabeçalho Principal ---
st.markdown('<h1 class="main-header">🏛️ Observatório Legislativo de Teresópolis</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Sistema de Monitoramento de Projetos de Lei - Câmara Municipal</p>', unsafe_allow_html=True)

# --- Função para carregar dados ---
@st.cache_data
def carregar_dados():
    try:
        # Tenta carregar o arquivo com ementas primeiro (versão mais completa)
        df = pd.read_csv('csv/base_observatorio_teresopolis_COM_EMENTAS.csv')
    except:
        try:
            # Fallback para o arquivo completo
            df = pd.read_csv('base_observatorio_teresopolis_COMPLETA.csv')
        except:
            try:
                # Último fallback para o arquivo básico
                df = pd.read_csv('base_observatorio_teresopolis.csv')
            except FileNotFoundError:
                return None

    # Garante que a coluna de data seja tratada como data
    df['Data Sessão'] = pd.to_datetime(df['Data Sessão'], errors='coerce')

    # Limpa dados
    df['PL'] = df['PL'].astype(str).str.strip()
    df['Autor'] = df['Autor'].astype(str).str.strip()
    df['Status'] = df['Status'].astype(str).str.strip()

    # Garante que as novas colunas existam
    if 'Ementa' not in df.columns:
        df['Ementa'] = 'Não disponível'
    else:
        df['Ementa'] = df['Ementa'].fillna('Não disponível').astype(str).str.strip()

    if 'Link YouTube' not in df.columns:
        df['Link YouTube'] = ''
    else:
        df['Link YouTube'] = df['Link YouTube'].fillna('').astype(str).str.strip()

    # Remove registros com datas inválidas ou muito antigas
    df = df[df['Data Sessão'].notna()]
    df = df[df['Data Sessão'] >= '2024-01-01']

    # Adiciona colunas auxiliares
    df['Ano'] = df['Data Sessão'].dt.year
    df['Mês'] = df['Data Sessão'].dt.month
    df['Mês_Nome'] = df['Data Sessão'].dt.strftime('%B')
    df['Trimestre'] = df['Data Sessão'].dt.quarter

    return df

# --- Carregamento dos Dados ---
df = carregar_dados()

if df is None:
    st.error("⚠️ Arquivo de dados não encontrado!")
    st.info("Por favor, certifique-se de que o arquivo CSV está na mesma pasta que este script.")
    st.stop()

# --- Sidebar com Filtros ---
with st.sidebar:
    st.header('🔍 Filtros de Pesquisa')

    # Filtro de período com slider
    st.subheader('📅 Período')
    data_min = df['Data Sessão'].min().date()
    data_max = df['Data Sessão'].max().date()

    # Opção de seleção rápida
    periodo_rapido = st.selectbox(
        'Seleção rápida:',
        ['Personalizado', 'Últimos 30 dias', 'Últimos 3 meses', 'Últimos 6 meses', 'Todo o período']
    )

    if periodo_rapido == 'Últimos 30 dias':
        data_inicio = data_max - timedelta(days=30)
        data_fim = data_max
    elif periodo_rapido == 'Últimos 3 meses':
        data_inicio = data_max - timedelta(days=90)
        data_fim = data_max
    elif periodo_rapido == 'Últimos 6 meses':
        data_inicio = data_max - timedelta(days=180)
        data_fim = data_max
    elif periodo_rapido == 'Todo o período':
        data_inicio = data_min
        data_fim = data_max
    else:  # Personalizado
        data_inicio, data_fim = st.date_input(
            'Selecione o período:',
            value=(data_min, data_max),
            min_value=data_min,
            max_value=data_max,
            format="DD/MM/YYYY"
        )

    # Aplicar filtro de data
    df_filtrado = df[(df['Data Sessão'].dt.date >= data_inicio) &
                     (df['Data Sessão'].dt.date <= data_fim)]

    # Filtro de autores com busca
    st.subheader('👤 Autores')
    busca_autor = st.text_input('Buscar autor:', '')
    autores = sorted(df_filtrado['Autor'].unique())

    if busca_autor:
        autores = [a for a in autores if busca_autor.lower() in a.lower()]

    autor_selecionado = st.multiselect(
        'Selecione o(s) Autor(es):',
        options=autores,
        default=[]
    )

    # Filtro de status
    st.subheader('📊 Status')
    status_disponiveis = sorted(df_filtrado['Status'].unique())
    status_selecionado = st.multiselect(
        'Selecione o(s) Status:',
        options=status_disponiveis,
        default=[]
    )

    # Filtro de PL específico
    st.subheader('📋 Projeto de Lei')
    pl_especifico = st.text_input('Digite o número do PL (ex: 123/2025):', '')

    # Aplicação dos filtros
    if autor_selecionado:
        df_filtrado = df_filtrado[df_filtrado['Autor'].isin(autor_selecionado)]
    if status_selecionado:
        df_filtrado = df_filtrado[df_filtrado['Status'].isin(status_selecionado)]
    if pl_especifico:
        df_filtrado = df_filtrado[df_filtrado['PL'].str.contains(pl_especifico, case=False, na=False)]

    # Botão de reset
    if st.button('🔄 Limpar Filtros'):
        st.rerun()

# --- Métricas Principais (KPIs) ---
st.header('📊 Indicadores Principais')

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    total_eventos = len(df_filtrado)
    st.metric(
        label="📝 Total de Eventos",
        value=f"{total_eventos:,}",
        delta=f"{total_eventos - len(df)} registros filtrados" if total_eventos < len(df) else None
    )

with col2:
    pls_unicos = df_filtrado['PL'].nunique()
    st.metric(
        label="📋 PLs Únicos",
        value=f"{pls_unicos:,}"
    )

with col3:
    if not df_filtrado.empty:
        vereador_mais_ativo = df_filtrado['Autor'].value_counts().index[0]
        qtd_projetos = df_filtrado['Autor'].value_counts().values[0]
        st.metric(
            label="🏆 Mais Ativo",
            value=vereador_mais_ativo.split()[0] if len(vereador_mais_ativo.split()) > 0 else vereador_mais_ativo,
            delta=f"{qtd_projetos} PLs"
        )
    else:
        st.metric(label="🏆 Mais Ativo", value="N/A")

with col4:
    aprovados = df_filtrado[df_filtrado['Status'].str.contains('Aprovado', case=False, na=False)]
    taxa_aprovacao = (len(aprovados) / len(df_filtrado) * 100) if len(df_filtrado) > 0 else 0
    st.metric(
        label="✅ Taxa de Aprovação",
        value=f"{taxa_aprovacao:.1f}%",
        delta=f"{len(aprovados)} aprovados"
    )

with col5:
    sessoes_unicas = df_filtrado['Data Sessão'].dt.date.nunique()
    st.metric(
        label="📅 Sessões",
        value=f"{sessoes_unicas}",
        delta="no período"
    )

# --- Separador ---
st.divider()

# --- Abas principais ---
tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Dashboard", "📋 Dados Detalhados", "📜 Ementas",
    "👥 Análise por Vereador", "📈 Linha do Tempo", "🔍 Busca de PL", "📊 Estatísticas Avançadas"
])

# --- Tab 1: Dashboard ---
with tab1:
    col1, col2 = st.columns(2)

    with col1:
        # Gráfico de PLs por Status
        st.subheader('📊 Distribuição por Status')
        if not df_filtrado.empty:
            fig_status = px.pie(
                df_filtrado['Status'].value_counts().reset_index(),
                values='count',
                names='Status',
                title='Distribuição de PLs por Status',
                color_discrete_map={
                    'Aprovado (Votação Simbólica)': '#2ecc71',
                    'Em Discussão': '#f39c12',
                    'Não identificado': '#95a5a6',
                    'Encaminhado para Comissão': '#3498db',
                    'Rejeitado': '#e74c3c'
                }
            )
            fig_status.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_status, use_container_width=True)

    with col2:
        # Gráfico de PLs por Mês
        st.subheader('📅 Evolução Temporal')
        if not df_filtrado.empty:
            df_mes = df_filtrado.groupby(df_filtrado['Data Sessão'].dt.to_period('M')).size()
            df_mes.index = df_mes.index.to_timestamp()

            fig_temporal = px.line(
                x=df_mes.index,
                y=df_mes.values,
                title='PLs por Mês',
                labels={'x': 'Mês', 'y': 'Quantidade de PLs'}
            )
            fig_temporal.update_traces(mode='lines+markers')
            fig_temporal.update_layout(showlegend=False)
            st.plotly_chart(fig_temporal, use_container_width=True)

    # Top 10 Vereadores
    st.subheader('🏆 Top 10 Vereadores Mais Ativos')
    if not df_filtrado.empty:
        top_vereadores = df_filtrado['Autor'].value_counts().head(10)

        fig_bar = px.bar(
            x=top_vereadores.values,
            y=top_vereadores.index,
            orientation='h',
            title='Projetos de Lei por Vereador',
            labels={'x': 'Quantidade de PLs', 'y': 'Vereador'},
            color=top_vereadores.values,
            color_continuous_scale='viridis'
        )
        fig_bar.update_layout(showlegend=False, height=400)
        st.plotly_chart(fig_bar, use_container_width=True)

# --- Tab 2: Dados Detalhados ---
with tab2:
    st.subheader('📋 Tabela Completa de Projetos de Lei')

    # Opções de visualização
    col1, col2, col3 = st.columns([1, 1, 2])
    with col1:
        ordenar_por = st.selectbox(
            'Ordenar por:',
            ['Data Sessão', 'PL', 'Autor', 'Status']
        )
    with col2:
        ordem = st.selectbox(
            'Ordem:',
            ['Decrescente', 'Crescente']
        )
    with col3:
        mostrar_ementa = st.checkbox('Mostrar Ementa', value=True)

    # Aplicar ordenação
    df_ordenado = df_filtrado.sort_values(
        ordenar_por,
        ascending=(ordem == 'Crescente')
    )

    # Colunas a exibir
    colunas_exibir = ['Data Sessão', 'PL', 'Autor', 'Status']
    if mostrar_ementa:
        colunas_exibir.insert(3, 'Ementa')

    # Exibir dados
    st.dataframe(
        df_ordenado[colunas_exibir],
        use_container_width=True,
        height=500,
        column_config={
            "Data Sessão": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
            "Ementa": st.column_config.TextColumn("Ementa", width="large"),
        }
    )

    # Links do YouTube disponíveis
    df_com_youtube = df_ordenado[df_ordenado['Link YouTube'].str.len() > 0]
    if not df_com_youtube.empty:
        with st.expander(f"🎬 {len(df_com_youtube)} sessões com vídeo disponível no YouTube"):
            for idx, row in df_com_youtube.drop_duplicates(subset=['Link YouTube']).head(20).iterrows():
                st.markdown(f"- [{row['Data Sessão'].strftime('%d/%m/%Y')} - Sessão]({row['Link YouTube']})")

    # Opção de download
    csv = df_ordenado.to_csv(index=False)
    st.download_button(
        label="📥 Baixar dados em CSV",
        data=csv,
        file_name=f'observatorio_teresopolis_{datetime.now().strftime("%Y%m%d")}.csv',
        mime='text/csv'
    )

# --- Tab 3: Ementas ---
with tab3:
    st.subheader('📜 Consulta de Ementas dos Projetos de Lei')

    # Campo de busca por ementa
    busca_ementa = st.text_input(
        '🔍 Buscar por conteúdo da ementa:',
        placeholder='Ex: saúde, educação, IPTU, zoneamento...',
        key='busca_ementa'
    )

    # Filtrar por ementa
    if busca_ementa:
        df_ementas = df_filtrado[
            df_filtrado['Ementa'].str.contains(busca_ementa, case=False, na=False)
        ]
    else:
        df_ementas = df_filtrado.copy()

    # Estatísticas de ementas
    col1, col2, col3 = st.columns(3)
    with col1:
        total_ementas = len(df_ementas[df_ementas['Ementa'] != 'Não disponível'])
        st.metric("📜 PLs com Ementa", total_ementas)
    with col2:
        pls_sem_ementa = len(df_ementas[df_ementas['Ementa'] == 'Não disponível'])
        st.metric("❓ PLs sem Ementa", pls_sem_ementa)
    with col3:
        if busca_ementa:
            st.metric("🔍 Resultados da Busca", len(df_ementas))

    st.divider()

    # Agrupar por PL único e mostrar ementas
    pls_unicos = df_ementas.drop_duplicates(subset=['PL']).sort_values('Data Sessão', ascending=False)

    if not pls_unicos.empty:
        st.markdown(f"**Mostrando {len(pls_unicos)} projetos de lei únicos**")

        for idx, row in pls_unicos.head(50).iterrows():
            with st.container():
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.markdown(f"### PL {row['PL']}")
                    st.markdown(f"**Autor:** {row['Autor']}")
                    st.markdown(f"**Status:** {row['Status']}")

                    # Exibir ementa com destaque
                    ementa_texto = row['Ementa'] if row['Ementa'] != 'Não disponível' else '*Ementa não disponível*'
                    st.info(f"📄 **Ementa:** {ementa_texto}")

                with col2:
                    st.markdown(f"**Data:** {row['Data Sessão'].strftime('%d/%m/%Y')}")

                    # Link do YouTube se disponível
                    if row['Link YouTube'] and len(row['Link YouTube']) > 0:
                        st.markdown(f"[🎬 Assistir Sessão]({row['Link YouTube']})")

                st.divider()
    else:
        st.warning("Nenhum projeto de lei encontrado com os filtros aplicados.")

# --- Tab 4: Análise por Vereador ---
with tab4:
    st.subheader('👥 Análise Detalhada por Vereador')

    if not df_filtrado.empty:
        # Seletor de vereador
        vereador_analise = st.selectbox(
            'Selecione um vereador para análise detalhada:',
            sorted(df_filtrado['Autor'].unique())
        )

        # Filtrar dados do vereador
        df_vereador = df_filtrado[df_filtrado['Autor'] == vereador_analise]

        # Métricas do vereador
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total de PLs", len(df_vereador))

        with col2:
            aprovados_vereador = len(df_vereador[df_vereador['Status'].str.contains('Aprovado', case=False, na=False)])
            taxa_aprov_vereador = (aprovados_vereador / len(df_vereador) * 100) if len(df_vereador) > 0 else 0
            st.metric("Taxa de Aprovação", f"{taxa_aprov_vereador:.1f}%")

        with col3:
            primeiro_pl = df_vereador['Data Sessão'].min()
            st.metric("Primeiro PL", primeiro_pl.strftime('%d/%m/%Y') if pd.notna(primeiro_pl) else "N/A")

        with col4:
            ultimo_pl = df_vereador['Data Sessão'].max()
            st.metric("Último PL", ultimo_pl.strftime('%d/%m/%Y') if pd.notna(ultimo_pl) else "N/A")

        # Gráfico de evolução do vereador
        col1, col2 = st.columns(2)

        with col1:
            # Status dos PLs do vereador
            fig_status_vereador = px.pie(
                df_vereador['Status'].value_counts().reset_index(),
                values='count',
                names='Status',
                title=f'Status dos PLs - {vereador_analise}'
            )
            st.plotly_chart(fig_status_vereador, use_container_width=True)

        with col2:
            # Evolução temporal do vereador
            df_vereador_mes = df_vereador.groupby(df_vereador['Data Sessão'].dt.to_period('M')).size()
            if not df_vereador_mes.empty:
                df_vereador_mes.index = df_vereador_mes.index.to_timestamp()

                fig_temporal_vereador = px.bar(
                    x=df_vereador_mes.index,
                    y=df_vereador_mes.values,
                    title=f'PLs por Mês - {vereador_analise}',
                    labels={'x': 'Mês', 'y': 'Quantidade'}
                )
                st.plotly_chart(fig_temporal_vereador, use_container_width=True)

        # Lista de PLs do vereador
        st.subheader(f'📋 Projetos de Lei - {vereador_analise}')
        st.dataframe(
            df_vereador[['Data Sessão', 'PL', 'Ementa', 'Status']].sort_values('Data Sessão', ascending=False),
            use_container_width=True,
            column_config={
                "Data Sessão": st.column_config.DateColumn("Data", format="DD/MM/YYYY"),
                "Ementa": st.column_config.TextColumn("Ementa", width="large"),
            }
        )

        # Links do YouTube para sessões do vereador
        df_vereador_youtube = df_vereador[df_vereador['Link YouTube'].str.len() > 0]
        if not df_vereador_youtube.empty:
            with st.expander(f"🎬 Sessões com vídeo ({len(df_vereador_youtube.drop_duplicates(subset=['Link YouTube']))})"):
                for idx, row in df_vereador_youtube.drop_duplicates(subset=['Link YouTube']).iterrows():
                    st.markdown(f"- [{row['Data Sessão'].strftime('%d/%m/%Y')}]({row['Link YouTube']}) - PL {row['PL']}")

# --- Tab 5: Linha do Tempo ---
with tab5:
    st.subheader('📈 Linha do Tempo de Projetos de Lei')

    # Seletor de PL para timeline
    if not df_filtrado.empty:
        pl_timeline = st.selectbox(
            'Selecione um PL para ver sua linha do tempo:',
            sorted(df_filtrado['PL'].unique())
        )

        # Filtrar histórico do PL
        df_pl = df[df['PL'] == pl_timeline].sort_values('Data Sessão')

        if not df_pl.empty:
            # Informações do PL
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                st.metric("Autor", df_pl.iloc[0]['Autor'])

            with col2:
                st.metric("Status Atual", df_pl.iloc[-1]['Status'])

            with col3:
                dias_tramitacao = (df_pl.iloc[-1]['Data Sessão'] - df_pl.iloc[0]['Data Sessão']).days
                st.metric("Dias em Tramitação", dias_tramitacao)

            with col4:
                total_mencoes = len(df_pl)
                st.metric("Menções em Sessões", total_mencoes)

            # Ementa do PL
            ementa_pl = df_pl.iloc[0]['Ementa']
            if ementa_pl and ementa_pl != 'Não disponível':
                st.info(f"📄 **Ementa:** {ementa_pl}")

            # Timeline
            st.markdown("### 📅 Histórico do PL")

            for idx, row in df_pl.iterrows():
                with st.container():
                    col1, col2, col3 = st.columns([1, 3, 1])

                    with col1:
                        st.markdown(f"**{row['Data Sessão'].strftime('%d/%m/%Y')}**")

                    with col2:
                        status_emoji = {
                            'Aprovado (Votação Simbólica)': '✅',
                            'Em Discussão': '💬',
                            'Não identificado': '❓',
                            'Encaminhado para Comissão': '📤',
                            'Rejeitado': '❌'
                        }.get(row['Status'], '📋')

                        st.markdown(f"{status_emoji} **{row['Status']}**")
                        st.caption(f"Fonte: {row['Fonte']}")

                    with col3:
                        # Link do YouTube
                        if row['Link YouTube'] and len(row['Link YouTube']) > 0:
                            st.markdown(f"[🎬 Ver Sessão]({row['Link YouTube']})")

                    st.divider()

# --- Tab 6: Busca de PL ---
with tab6:
    st.subheader('🔍 Busca Avançada de Projetos de Lei')

    # Campo de busca
    busca_termo = st.text_input('Digite o número do PL ou termo de busca:', '')

    if busca_termo:
        # Buscar em todos os campos incluindo ementa
        df_busca = df[
            (df['PL'].str.contains(busca_termo, case=False, na=False)) |
            (df['Autor'].str.contains(busca_termo, case=False, na=False)) |
            (df['Status'].str.contains(busca_termo, case=False, na=False)) |
            (df['Ementa'].str.contains(busca_termo, case=False, na=False))
        ]

        if not df_busca.empty:
            st.success(f"Encontrados {len(df_busca)} resultados")

            # Agrupar por PL
            pls_encontrados = df_busca['PL'].unique()

            for pl in sorted(pls_encontrados):
                df_pl_busca = df_busca[df_busca['PL'] == pl]

                with st.expander(f"📋 PL {pl} - {df_pl_busca.iloc[0]['Autor']}"):
                    # Informações do PL
                    col1, col2 = st.columns(2)

                    with col1:
                        st.markdown(f"**Autor:** {df_pl_busca.iloc[0]['Autor']}")
                        st.markdown(f"**Primeira Menção:** {df_pl_busca['Data Sessão'].min().strftime('%d/%m/%Y')}")

                    with col2:
                        st.markdown(f"**Status Atual:** {df_pl_busca.iloc[-1]['Status']}")
                        st.markdown(f"**Última Menção:** {df_pl_busca['Data Sessão'].max().strftime('%d/%m/%Y')}")

                    # Ementa do PL
                    ementa_busca = df_pl_busca.iloc[0]['Ementa']
                    if ementa_busca and ementa_busca != 'Não disponível':
                        st.info(f"📄 **Ementa:** {ementa_busca}")

                    # Link do YouTube
                    youtube_link = df_pl_busca[df_pl_busca['Link YouTube'].str.len() > 0]['Link YouTube']
                    if not youtube_link.empty:
                        st.markdown(f"🎬 [Assistir última sessão no YouTube]({youtube_link.iloc[-1]})")

                    # Histórico
                    st.markdown("**Histórico:**")
                    st.dataframe(
                        df_pl_busca[['Data Sessão', 'Status', 'Fonte']].sort_values('Data Sessão'),
                        use_container_width=True,
                        hide_index=True
                    )
        else:
            st.warning("Nenhum resultado encontrado")

# --- Tab 7: Estatísticas Avançadas ---
with tab7:
    st.subheader('📊 Estatísticas Avançadas')

    if not df_filtrado.empty:
        # Análise por período
        col1, col2 = st.columns(2)

        with col1:
            # Heatmap de atividade
            st.markdown("### 🗓️ Mapa de Calor - Atividade Mensal")

            # Preparar dados para heatmap
            df_heatmap = df_filtrado.copy()
            df_heatmap['Mês'] = df_heatmap['Data Sessão'].dt.month
            df_heatmap['Ano'] = df_heatmap['Data Sessão'].dt.year

            pivot_table = df_heatmap.pivot_table(
                values='PL',
                index='Mês',
                columns='Ano',
                aggfunc='count',
                fill_value=0
            )

            fig_heatmap = px.imshow(
                pivot_table,
                labels=dict(x="Ano", y="Mês", color="PLs"),
                y=['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
                   'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'][:len(pivot_table)],
                color_continuous_scale='YlOrRd'
            )
            st.plotly_chart(fig_heatmap, use_container_width=True)

        with col2:
            # Taxa de aprovação por vereador
            st.markdown("### 📊 Taxa de Aprovação por Vereador")

            taxa_aprovacao_vereadores = []
            for vereador in df_filtrado['Autor'].unique():
                df_v = df_filtrado[df_filtrado['Autor'] == vereador]
                aprovados = len(df_v[df_v['Status'].str.contains('Aprovado', case=False, na=False)])
                total = len(df_v)
                taxa = (aprovados / total * 100) if total > 0 else 0

                if total >= 3:  # Apenas vereadores com pelo menos 3 PLs
                    taxa_aprovacao_vereadores.append({
                        'Vereador': vereador,
                        'Taxa de Aprovação (%)': taxa,
                        'Total PLs': total
                    })

            if taxa_aprovacao_vereadores:
                df_taxa = pd.DataFrame(taxa_aprovacao_vereadores)
                df_taxa = df_taxa.sort_values('Taxa de Aprovação (%)', ascending=False).head(10)

                fig_taxa = px.bar(
                    df_taxa,
                    x='Taxa de Aprovação (%)',
                    y='Vereador',
                    orientation='h',
                    text='Total PLs',
                    color='Taxa de Aprovação (%)',
                    color_continuous_scale='RdYlGn'
                )
                fig_taxa.update_traces(texttemplate='%{text} PLs', textposition='inside')
                st.plotly_chart(fig_taxa, use_container_width=True)

        # Análise de correlação
        st.markdown("### 🔗 Análise de Parcerias")

        # Identificar vereadores que aparecem juntos em sessões
        vereadores_sessoes = []
        for sessao in df_filtrado['Data Sessão'].unique():
            df_sessao = df_filtrado[df_filtrado['Data Sessão'] == sessao]
            vereadores_na_sessao = df_sessao['Autor'].unique()

            if len(vereadores_na_sessao) > 1:
                for i, v1 in enumerate(vereadores_na_sessao):
                    for v2 in vereadores_na_sessao[i+1:]:
                        vereadores_sessoes.append({
                            'Vereador 1': v1,
                            'Vereador 2': v2,
                            'Sessão': sessao
                        })

        if vereadores_sessoes:
            df_parcerias = pd.DataFrame(vereadores_sessoes)

            # Contar parcerias mais frequentes
            parcerias_freq = df_parcerias.groupby(['Vereador 1', 'Vereador 2']).size().reset_index(name='Frequência')
            parcerias_freq = parcerias_freq.sort_values('Frequência', ascending=False).head(10)

            if not parcerias_freq.empty:
                parcerias_freq['Parceria'] = parcerias_freq['Vereador 1'] + ' & ' + parcerias_freq['Vereador 2']

                fig_parcerias = px.bar(
                    parcerias_freq,
                    x='Frequência',
                    y='Parceria',
                    orientation='h',
                    title='Vereadores que Mais Apresentam PLs nas Mesmas Sessões'
                )
                st.plotly_chart(fig_parcerias, use_container_width=True)

# --- Rodapé ---
st.divider()
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>📊 Observatório Legislativo de Teresópolis | Dados atualizados até {}</p>
    <p>Desenvolvido para transparência e acompanhamento da atividade legislativa municipal</p>
</div>
""".format(df['Data Sessão'].max().strftime('%d/%m/%Y')), unsafe_allow_html=True)