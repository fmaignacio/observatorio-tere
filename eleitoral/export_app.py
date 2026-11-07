"""Exporta um pacote pequeno de dados para o dashboard (data/app/, versionado).

Uso:
    python -m eleitoral.export_app

O dashboard publicado não tem acesso a data/processed (gitignored, ~GB de
fontes). Este pacote é agregado por local de votação e traz as análises já
calculadas, para que o app não precise de scipy/sklearn.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from eleitoral.analysis import clusters, swing, transition
from eleitoral.analysis.common import LOCAL, load
from eleitoral.ingest import reconcile

APP_DIR = Path(__file__).resolve().parents[1] / "data" / "app"

TRANSICOES = [((2024, 11), (2026, 3)), ((2022, 3), (2026, 3)), ((2022, 5), (2026, 5))]
CLUSTERS = [(2026, 3), (2024, 11), (2022, 3)]


def resultados() -> pd.DataFrame:
    fv = load("fact_votos")
    cand = load("dim_candidato")[["ano", "sq_candidato", "nome_urna", "eleito"]]
    v = fv.merge(cand, on=["ano", "sq_candidato"], how="left")
    leg = v.tipo_voto.eq("legenda")
    sig = (v.dropna(subset=["partido"]).drop_duplicates(["ano", "nr_partido"])
             .set_index(["ano", "nr_partido"]).partido)
    v.loc[leg, "partido"] = pd.MultiIndex.from_frame(v.loc[leg, ["ano", "nr_partido"]]).map(sig)
    v["partido"] = v.partido.fillna(v.numero_votavel.astype(str)).where(v.tipo_voto.isin(["nominal", "legenda"]))
    v["candidato"] = v.nome_urna.fillna(v.nome_votavel)
    v.loc[leg, "candidato"] = "Legenda " + v.loc[leg, "partido"].astype(str)
    v["eleito"] = v.eleito.fillna(False).astype(bool)
    keys = ["ano", "turno", "cd_cargo", "cargo", *LOCAL, "tipo_voto", "partido", "candidato", "numero_votavel", "eleito"]
    return v.groupby(keys, dropna=False, as_index=False).votos.sum()


def main():
    APP_DIR.mkdir(parents=True, exist_ok=True)
    out = {}
    out["resultados"] = resultados()

    loc = load("dim_local_votacao")
    out["locais"] = loc

    pf = load("fact_perfil_secao")
    out["perfil_local"] = pd.concat([clusters.perfil_local(a).assign(ano=a) for a in sorted(pf.ano.unique())]).reset_index()

    tr = []
    for de, para in TRANSICOES:
        T = transition.transicao(de, para, top=4)
        m = T.stack().rename("fracao").reset_index()
        m.columns = ["origem", "destino", "fracao"]
        A = transition.opcoes(*de, top=4)
        peso = (A.drop(columns="_peso").mul(A._peso, axis=0)).sum()
        m["eleitores_origem"] = m.origem.map(peso).round()
        tr.append(m.assign(de_ano=de[0], de_cargo=de[1], para_ano=para[0], para_cargo=para[1]))
    out["transicoes"] = pd.concat(tr, ignore_index=True)

    cl = []
    for ano, cargo in CLUSTERS:
        X, _, k, sil = clusters.agrupar(ano, cargo)
        cl.append(X.assign(ano=ano, cd_cargo=cargo, k=k, silhueta=sil))
    out["clusters"] = pd.concat(cl, ignore_index=True)

    rec = []
    for y in (2022, 2024, 2026):
        r = reconcile.reconcile(y)
        c = r["candidatos"]
        car = r["cargos"].assign(ano=y,
                                 candidatos_ok=int((~c.fora_lista_oficial).sum() - len(r["candidatos_erro"])),
                                 candidatos_total=int((~c.fora_lista_oficial).sum()))
        rec.append(car)
    out["reconciliacao"] = pd.concat(rec, ignore_index=True)

    for name, df in out.items():
        df.to_parquet(APP_DIR / f"{name}.parquet", index=False)
        print(f"{name}: {len(df)} linhas, {(APP_DIR / f'{name}.parquet').stat().st_size / 1024:.0f} KB")


if __name__ == "__main__":
    main()
