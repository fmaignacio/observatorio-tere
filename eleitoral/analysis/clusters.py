"""Agrupamento (k-means) de locais de votação por perfil do eleitorado e voto.

Uso:
    python -m eleitoral.analysis.clusters --ano 2026 --cargo 3 [--k 0] [--top 4]

Unidade: local de votação (zona, nr_local). As seções mudam de numeração entre
anos; os locais, não. Variáveis (todas em proporção, padronizadas):
- perfil: % mulheres, faixas etárias (16–24, 25–44, 45–59, 60+),
  escolaridade (baixa, média, superior);
- voto: % dos válidos dos ``top`` partidos no cargo, mais % brancos/nulos e abstenção.

``--k 0`` escolhe k entre 3 e 7 pelo maior coeficiente de silhueta.
"""
from __future__ import annotations

import argparse
import re

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from eleitoral.analysis.common import LOCAL, PROCESSED_DIR, VALIDOS, aptos_por_local, load, rotulo, votos_eleicao

ESCOLARIDADE = {
    "ANALFABETO": "esc_baixa", "LÊ E ESCREVE": "esc_baixa", "ENSINO FUNDAMENTAL INCOMPLETO": "esc_baixa",
    "ENSINO FUNDAMENTAL COMPLETO": "esc_media", "ENSINO MÉDIO INCOMPLETO": "esc_media",
    "ENSINO MÉDIO COMPLETO": "esc_media", "SUPERIOR INCOMPLETO": "esc_superior",
    "SUPERIOR COMPLETO": "esc_superior",
}


def _faixa(desc: str) -> str | None:
    m = re.match(r"\s*(\d+)", str(desc))
    if not m:
        return None
    i = int(m.group(1))
    return "idade_16_24" if i < 25 else "idade_25_44" if i < 45 else "idade_45_59" if i < 60 else "idade_60_mais"


def perfil_local(ano: int) -> pd.DataFrame:
    p = load("fact_perfil_secao")
    p = p[p.ano == ano]
    tot = p.groupby(LOCAL).eleitores.sum()
    fem = p[p.genero == "FEMININO"].groupby(LOCAL).eleitores.sum() / tot
    idade = (p.assign(f=p.faixa_etaria.map(_faixa)).dropna(subset=["f"])
              .pivot_table(index=LOCAL, columns="f", values="eleitores", aggfunc="sum", fill_value=0))
    esc = (p.assign(e=p.escolaridade.map(ESCOLARIDADE)).dropna(subset=["e"])
            .pivot_table(index=LOCAL, columns="e", values="eleitores", aggfunc="sum", fill_value=0))
    return pd.concat([fem.rename("mulheres"), idade.div(idade.sum(axis=1), axis=0),
                      esc.div(esc.sum(axis=1), axis=0)], axis=1).fillna(0)


def voto_local(ano: int, cd_cargo: int, top: int) -> pd.DataFrame:
    v = votos_eleicao(ano, cd_cargo).copy()
    v["grupo"] = rotulo(v, "partido")
    val = v[v.tipo_voto.isin(VALIDOS)]
    principais = val.groupby("grupo").votos.sum().nlargest(top).index
    tab = (val[val.grupo.isin(principais)]
           .pivot_table(index=LOCAL, columns="grupo", values="votos", aggfunc="sum", fill_value=0))
    tab = tab.div(val.groupby(LOCAL).votos.sum(), axis=0).add_prefix("voto_")
    total = v.groupby(LOCAL).votos.sum()
    tab["voto_branco_nulo"] = v[~v.tipo_voto.isin(VALIDOS)].groupby(LOCAL).votos.sum() / total
    fv = load("fact_votos")
    comparec = fv[(fv.ano == ano) & (fv.turno == 1)].groupby(["cd_cargo", *LOCAL]).votos.sum()
    menor = comparec.groupby("cd_cargo").sum().idxmin()  # cargo de 1 voto/eleitor
    tab["abstencao"] = 1 - comparec.loc[menor] / aptos_por_local(ano)
    return tab.fillna(0)


def agrupar(ano: int, cd_cargo: int, k: int = 0, top: int = 4, seed: int = 0):
    X = perfil_local(ano).join(voto_local(ano, cd_cargo, top), how="inner")
    Z = StandardScaler().fit_transform(X)
    if k == 0:
        scores = {kk: silhouette_score(Z, KMeans(kk, n_init=20, random_state=seed).fit_predict(Z))
                  for kk in range(3, 8)}
        k = max(scores, key=scores.get)
    km = KMeans(k, n_init=50, random_state=seed).fit(Z)
    X = X.assign(cluster=km.labels_)
    loc = load("dim_local_votacao")
    loc = loc[loc.ano == ano].set_index(LOCAL)[["local_votacao", "bairro", "latitude", "longitude", "eleitores_aptos"]]
    X = X.join(loc)
    resumo = X.groupby("cluster").agg(
        locais=("local_votacao", "size"), eleitores=("eleitores_aptos", "sum"),
        **{c: (c, "mean") for c in X.columns if c not in loc.columns and c != "cluster"},
    )
    return X.reset_index(), resumo, k, float(silhouette_score(Z, km.labels_))


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ano", type=int, default=2026)
    p.add_argument("--cargo", type=int, default=3)
    p.add_argument("--k", type=int, default=0)
    p.add_argument("--top", type=int, default=4)
    a = p.parse_args(argv)
    X, resumo, k, sil = agrupar(a.ano, a.cargo, a.k, a.top)
    out = PROCESSED_DIR / f"analysis_clusters_{a.ano}c{a.cargo}.parquet"
    X.to_parquet(out, index=False)
    print(f"k={k} (silhueta {sil:.2f})")
    pct = [c for c in resumo.columns if c not in ("locais", "eleitores")]
    r = resumo.copy()
    r[pct] = (100 * r[pct]).round(0).astype(int)
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(r.T.to_string())
    for c, g in X.groupby("cluster"):
        print(f"cluster {c}: {', '.join(g.bairro.value_counts().head(5).index)}")
    print(f"\nSalvo em {out}")


if __name__ == "__main__":
    main()
