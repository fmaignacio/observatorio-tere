"""Observatório Teresópolis — V2 Eleitoral (votação por seção do TSE)."""
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Eleitoral · Observatório Teresópolis", page_icon="🗳️", layout="wide")

DATA = Path(__file__).resolve().parents[1] / "data" / "app"
CARGOS = {3: "Governador", 5: "Senador", 6: "Deputado Federal", 7: "Deputado Estadual",
          11: "Prefeito", 13: "Vereador"}
LOCAL = ["zona", "nr_local"]
VALIDOS = ["nominal", "legenda"]
CENTRO = {"lat": -22.41, "lon": -42.97}


@st.cache_data
def carregar():
    return {n: pd.read_parquet(DATA / f"{n}.parquet")
            for n in ["resultados", "locais", "perfil_local", "transicoes", "clusters", "reconciliacao"]}


if not (DATA / "resultados.parquet").exists():
    st.error("Dados não encontrados em data/app/. Rode `python -m eleitoral.export_app`.")
    st.stop()

D = carregar()
R, L = D["resultados"], D["locais"]


def rotulo_eleicao(ano, cargo):
    return f"{CARGOS[cargo]} {ano}"


def eleicao(ano, cargo):
    return R[(R.ano == ano) & (R.cd_cargo == cargo) & (R.turno == 1)]


def votos_por_eleitor(ano, cargo):
    t = R[(R.ano == ano) & (R.turno == 1)].groupby("cd_cargo").votos.sum()
    return int(round(t[cargo] / t.min()))


def locais_ano(ano):
    return L[L.ano == ano].set_index(LOCAL)


def participacao(ano, cargo, por):
    v = eleicao(ano, cargo)
    v = v[v.tipo_voto.isin(VALIDOS)]
    g = v.groupby([*LOCAL, por], as_index=False).votos.sum()
    g["pct"] = 100 * g.votos / g.groupby(LOCAL).votos.transform("sum")
    return g


def mapa(df, cor, titulo, escala="Blues", meio=None, hover=None, discreto=False):
    kw = dict(lat="latitude", lon="longitude", color=cor, hover_name="local_votacao",
              hover_data=hover or {}, zoom=10.3, center=CENTRO, height=560, map_style="carto-positron")
    if discreto:
        fig = px.scatter_map(df, size="eleitores_aptos", size_max=22, **kw)
    else:
        kw["color_continuous_scale"] = escala
        if meio is not None:
            lim = max(abs(df[cor].min()), abs(df[cor].max()))
            kw["range_color"] = (-lim, lim)
        fig = px.scatter_map(df, size="eleitores_aptos", size_max=22, **kw)
    fig.update_layout(margin=dict(l=0, r=0, t=30, b=0), title=titulo)
    return fig


# ── Cabeçalho e filtros ─────────────────────────────────────────────────────
st.title("🗳️ Eleições em Teresópolis")
st.caption("Votação por seção do TSE (2022, 2024 e 2026), agregada por local de votação. "
           "Os totais batem com o resultado oficial do TSE (veja a aba Confiabilidade).")

with st.sidebar:
    st.header("Eleição")
    ano = st.selectbox("Ano", sorted(map(int, R.ano.unique()), reverse=True))
    cargos_ano = [c for c in CARGOS if c in set(R[R.ano == ano].cd_cargo)]
    cargo = st.selectbox("Cargo", cargos_ano, format_func=CARGOS.get, key=f"cargo_{ano}")
    por = st.radio("Agrupar por", ["candidato", "partido"], horizontal=True)

v = eleicao(ano, cargo)
k = votos_por_eleitor(ano, cargo)
aptos = int(locais_ano(ano).eleitores_aptos.sum())
comparec = int(v.votos.sum() / k)
brancos = int(v[v.tipo_voto == "branco"].votos.sum())
nulos = int(v[v.tipo_voto.isin(["nulo", "nulo_tecnico"])].votos.sum())
validos = int(v[v.tipo_voto.isin(VALIDOS)].votos.sum())

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Eleitorado apto", f"{aptos:,}".replace(",", "."))
c2.metric("Comparecimento", f"{comparec:,}".replace(",", "."), f"{100 * comparec / aptos:.1f}% do eleitorado",
          delta_color="off")
c3.metric("Abstenção", f"{100 * (1 - comparec / aptos):.1f}%")
c4.metric("Brancos", f"{100 * brancos / v.votos.sum():.1f}%")
c5.metric("Nulos", f"{100 * nulos / v.votos.sum():.1f}%")
if k > 1:
    st.info(f"Em {ano}, o eleitor votou em {k} candidatos a {CARGOS[cargo]} (duas vagas). Os percentuais "
            "são sobre o total de votos.")

tab_res, tab_mapa, tab_swing, tab_trans, tab_cl, tab_conf = st.tabs([
    "📊 Resultado", "🗺️ Mapa por local", "↕️ Variação entre eleições", "🔀 Migração de votos",
    "🏘️ Perfis de bairro", "✅ Confiabilidade"])

# ── Resultado ───────────────────────────────────────────────────────────────
with tab_res:
    val = v[v.tipo_voto.isin(VALIDOS)]
    agg = (val.groupby(por, as_index=False)
              .agg(votos=("votos", "sum"), eleito=("eleito", "max"), partido=("partido", "first"))
              .sort_values("votos", ascending=False))
    agg["% válidos"] = 100 * agg.votos / validos
    n = (st.slider("Quantos mostrar", 5, min(60, len(agg)), min(15, len(agg)), key="n_res")
         if len(agg) > 5 else len(agg))
    top = agg.head(n).iloc[::-1]
    if por == "candidato":
        top = top.assign(situacao=top.eleito.map({True: "Eleito", False: "Não eleito"}))
        fig = px.bar(top, x="votos", y="candidato", orientation="h", color="situacao",
                     color_discrete_map={"Eleito": "#1f4788", "Não eleito": "#a9b8d6"},
                     hover_data={"partido": True, "% válidos": ":.1f"}, height=max(380, 26 * n))
    else:
        fig = px.bar(top, x="votos", y="partido", orientation="h", hover_data={"% válidos": ":.1f"},
                     color_discrete_sequence=["#1f4788"], height=max(380, 26 * n))
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), yaxis_title=None, legend_title=None)
    st.plotly_chart(fig, width="stretch")
    with st.expander("Tabela completa"):
        st.dataframe(agg.assign(**{"% válidos": agg["% válidos"].round(2)}), hide_index=True, width="stretch")

# ── Mapa ────────────────────────────────────────────────────────────────────
with tab_mapa:
    p = participacao(ano, cargo, por)
    opcoes = p.groupby(por).votos.sum().sort_values(ascending=False).index.tolist()
    alvo = st.selectbox(f"Escolha o {por}", opcoes, key=f"alvo_mapa_{ano}_{cargo}_{por}")
    m = (locais_ano(ano).join(p[p[por] == alvo].set_index(LOCAL)[["votos", "pct"]]).fillna({"votos": 0, "pct": 0})
         .reset_index())
    st.plotly_chart(mapa(m, "pct", f"{alvo}: % dos votos válidos por local", "Blues",
                         hover={"bairro": True, "votos": True, "pct": ":.1f", "eleitores_aptos": True}),
                    width="stretch")
    st.caption("Cada círculo é um local de votação; o tamanho é o eleitorado.")
    b = m.groupby("bairro").agg(votos=("votos", "sum")).join(
        p.merge(L[L.ano == ano][[*LOCAL, "bairro"]], on=LOCAL).groupby("bairro").votos.sum().rename("validos"))
    b["%"] = (100 * b.votos / b.validos).round(1)
    st.dataframe(b.sort_values("%", ascending=False).reset_index(), hide_index=True, width="stretch")

# ── Variação ────────────────────────────────────────────────────────────────
with tab_swing:
    st.markdown("Compara a participação (% dos válidos) de um partido ou candidato entre duas eleições, "
                "local por local. Os locais são casados pelo código do TSE, que é estável entre os anos.")
    eleicoes = [(int(a), c) for a in sorted(R.ano.unique()) for c in CARGOS if c in set(R[R.ano == a].cd_cargo)]
    c1, c2, c3 = st.columns(3)
    de = c1.selectbox("De", eleicoes, index=eleicoes.index((2022, 3)) if (2022, 3) in eleicoes else 0,
                      format_func=lambda e: rotulo_eleicao(*e))
    para = c2.selectbox("Para", eleicoes, index=eleicoes.index((2026, 3)) if (2026, 3) in eleicoes else 0,
                        format_func=lambda e: rotulo_eleicao(*e))
    por_sw = c3.radio("Comparar", ["partido", "candidato"], horizontal=True, key="por_sw")
    a = participacao(*de, por_sw).rename(columns={"votos": "votos_de", "pct": "pct_de"})
    b = participacao(*para, por_sw).rename(columns={"votos": "votos_para", "pct": "pct_para"})
    comuns = a[LOCAL].drop_duplicates().merge(b[LOCAL].drop_duplicates())
    sw = a.merge(b, on=[*LOCAL, por_sw], how="outer").merge(comuns).fillna(0)
    sw["variacao_pp"] = sw.pct_para - sw.pct_de
    tot = sw.groupby(por_sw)[["votos_de", "votos_para"]].sum()
    tot["% de"] = 100 * tot.votos_de / tot.votos_de.sum()
    tot["% para"] = 100 * tot.votos_para / tot.votos_para.sum()
    tot["variação (pp)"] = tot["% para"] - tot["% de"]
    tot = tot.assign(_o=tot[["votos_de", "votos_para"]].max(axis=1)).sort_values("_o", ascending=False).drop(columns="_o")
    g = st.selectbox(f"{por_sw.capitalize()} para o mapa", tot.index.tolist(), key=f"g_sw_{de}_{para}_{por_sw}")
    ms = (locais_ano(para[0]).join(sw[sw[por_sw] == g].set_index(LOCAL)[["pct_de", "pct_para", "variacao_pp"]],
                                   how="inner").reset_index())
    c1, c2 = st.columns([3, 2])
    c1.plotly_chart(mapa(ms, "variacao_pp", f"{g}: variação em pontos percentuais", "RdBu", meio=0,
                         hover={"bairro": True, "pct_de": ":.1f", "pct_para": ":.1f", "variacao_pp": ":.1f"}),
                    width="stretch")
    c2.markdown("**Município (locais comuns)**")
    c2.dataframe(tot.round(1).reset_index(), hide_index=True, width="stretch", height=520)
    st.caption("Azul = cresceu; vermelho = caiu. Comparações entre cargos diferentes (ex.: prefeito × governador) "
               "mostram afinidade territorial, não transferência de voto.")

# ── Migração ────────────────────────────────────────────────────────────────
with tab_trans:
    T = D["transicoes"]
    pares = T[["de_ano", "de_cargo", "para_ano", "para_cargo"]].drop_duplicates().itertuples(index=False)
    pares = [tuple(map(int, x)) for x in pares]
    par = st.selectbox("Comparação", pares,
                       format_func=lambda x: f"{rotulo_eleicao(x[0], x[1])} → {rotulo_eleicao(x[2], x[3])}")
    t = T[(T.de_ano == par[0]) & (T.de_cargo == par[1]) & (T.para_ano == par[2]) & (T.para_cargo == par[3])]
    ordem_o = t.drop_duplicates("origem").origem.tolist()
    ordem_d = t.drop_duplicates("destino").destino.tolist()
    mat = t.pivot(index="origem", columns="destino", values="fracao").loc[ordem_o, ordem_d] * 100
    fig = px.imshow(mat.round(0), text_auto=".0f", color_continuous_scale="Blues", aspect="auto",
                    labels=dict(x=f"Voto em {par[2]}", y=f"Voto em {par[0]}", color="%"), height=480)
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0))
    st.plotly_chart(fig, width="stretch")
    st.warning("Estimativa por inferência ecológica (regressão de Goodman com restrições sobre os locais de "
               "votação). Cada linha mostra para onde foram, em média, os eleitores daquela opção. "
               "Serve como indicativo de tendência, não de comportamento individual. Linhas com poucos "
               "eleitores ('Outros') são pouco confiáveis.")

# ── Perfis ──────────────────────────────────────────────────────────────────
with tab_cl:
    C = D["clusters"]
    opc = C[["ano", "cd_cargo"]].drop_duplicates().itertuples(index=False)
    opc = [tuple(map(int, x)) for x in opc]
    sel = st.selectbox("Base do agrupamento", opc, format_func=lambda x: rotulo_eleicao(*x))
    c = C[(C.ano == sel[0]) & (C.cd_cargo == sel[1])].copy()
    c["grupo"] = "Grupo " + (c.cluster + 1).astype(str)
    st.markdown(f"Os locais de votação foram agrupados (k-means, **{int(c.k.iloc[0])} grupos**) pelo perfil do "
                "eleitorado (idade, escolaridade, gênero) e pelo voto. Locais do mesmo grupo se parecem nos dois "
                "aspectos.")
    c1, c2 = st.columns([3, 2])
    c1.plotly_chart(mapa(c.sort_values("grupo"), "grupo", "Grupos de locais", discreto=True,
                         hover={"bairro": True, "eleitores_aptos": True}), width="stretch")
    cols = [x for x in c.columns if x.startswith(("idade_", "esc_", "voto_")) or x in ("mulheres", "abstencao")]
    res = c.groupby("grupo").agg(locais=("local_votacao", "size"), eleitores=("eleitores_aptos", "sum"),
                                 **{x: (x, "mean") for x in cols})
    res[cols] = (100 * res[cols]).round(0)
    nomes = {"mulheres": "% mulheres", "idade_16_24": "% 16–24 anos", "idade_25_44": "% 25–44",
             "idade_45_59": "% 45–59", "idade_60_mais": "% 60+", "esc_baixa": "% escolaridade baixa",
             "esc_media": "% escolaridade média", "esc_superior": "% superior",
             "voto_branco_nulo": "% branco/nulo", "abstencao": "% abstenção"}
    res = res.rename(columns=lambda x: nomes.get(x, x.replace("voto_", "% ")))
    c2.dataframe(res.T, width="stretch", height=560)
    with st.expander("Bairros de cada grupo"):
        for gname, gg in c.groupby("grupo"):
            st.markdown(f"**{gname}:** " + ", ".join(sorted(gg.bairro.dropna().unique())))

# ── Confiabilidade ──────────────────────────────────────────────────────────
with tab_conf:
    st.markdown("Os dados por seção foram conferidos contra o resultado oficial do TSE para o município. "
                "Divergência zero é exigida; se houver qualquer diferença, o pipeline para.")
    rc = D["reconciliacao"]
    show = rc[["ano", "cargo", "comparecimento", "votos_por_eleitor", "dif_total", "brancos", "dif_brancos",
               "nulos_tecnicos", "dif_tecnicos", "candidatos_ok", "candidatos_total"]].rename(columns={
        "comparecimento": "comparecimento oficial", "votos_por_eleitor": "votos/eleitor",
        "dif_total": "dif. total", "dif_brancos": "dif. brancos", "nulos_tecnicos": "nulos técnicos",
        "dif_tecnicos": "dif. nulos técnicos", "candidatos_ok": "candidatos que batem",
        "candidatos_total": "candidatos"})
    st.dataframe(show, hide_index=True, width="stretch")
    st.caption("Nulo técnico = voto em candidato inapto ou em legenda de partido sem candidato fora de federação. "
               "Fonte: TSE, Portal de Dados Abertos (votacao_secao, votacao_candidato_munzona, "
               "detalhe_votacao_munzona, consulta_cand, eleitorado_local_votacao, perfil_eleitor_secao).")
