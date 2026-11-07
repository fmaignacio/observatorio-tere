"""Constrói as tabelas fato da V2.

Uso:
    python -m eleitoral.transform.build_facts [--years 2022 2024 2026]

Pré-requisitos: ``eleitoral.ingest.tse`` (fact_votos_<ano>.parquet) e
``eleitoral.transform.build_dims`` (dim_candidato).

Saídas em data/processed/:
    fact_votos.parquet         todos os anos, com tipo_voto e partido
    fact_perfil_secao.parquet  eleitores por seção × perfil
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from eleitoral.ingest.column_mappings import (
    CD_MUNICIPIO_TERESOPOLIS,
    DATASET_MAPS,
    VOTO_BRANCO,
    VOTO_NULO,
)
from eleitoral.ingest.download import RAW_DIR, zip_name
from eleitoral.ingest.reader import read_filtered

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
YEARS = (2022, 2024, 2026)


def tipo_voto(fv: pd.DataFrame, cand: pd.DataFrame) -> pd.Series:
    """nominal | legenda | branco | nulo | nulo_tecnico."""
    t = pd.Series("nominal", index=fv.index)
    t[fv.numero_votavel == VOTO_BRANCO] = "branco"
    t[fv.numero_votavel == VOTO_NULO] = "nulo"
    t[(fv.sq_candidato <= 0) & (fv.numero_votavel < VOTO_BRANCO)] = "legenda"
    validos = set(cand.sq_candidato)
    t[(fv.sq_candidato > 0) & ~fv.sq_candidato.isin(validos)] = "nulo_tecnico"
    return t


def votos(years=YEARS) -> pd.DataFrame:
    cand = pd.read_parquet(PROCESSED_DIR / "dim_candidato.parquet")
    partes = []
    for y in years:
        fv = pd.read_parquet(PROCESSED_DIR / f"fact_votos_{y}.parquet")
        c = cand[cand.ano == y]
        # Votos em candidatos inaptos (fora da lista oficial) = nulo técnico.
        fv["tipo_voto"] = tipo_voto(fv, c[c.apto])
        fv = fv.merge(c[["sq_candidato", "partido", "nr_partido"]], on="sq_candidato", how="left")
        leg = fv.tipo_voto.eq("legenda")
        fv.loc[leg, "nr_partido"] = fv.loc[leg, "numero_votavel"]
        partes.append(fv[["ano", "turno", "cd_cargo", "cargo", "zona", "secao", "nr_local",
                          "numero_votavel", "nome_votavel", "sq_candidato", "tipo_voto",
                          "partido", "nr_partido", "votos"]])
    out = pd.concat(partes, ignore_index=True)
    out["nr_partido"] = out.nr_partido.astype("Int16")
    return out


def perfil(years=YEARS) -> pd.DataFrame:
    partes = []
    for y in years:
        m = DATASET_MAPS["perfil_eleitor_secao"][y]
        df = read_filtered(RAW_DIR / zip_name(y, dataset="perfil_eleitor_secao"), m["member"], m["rename"],
                           filters={k: str(CD_MUNICIPIO_TERESOPOLIS) for k in ["CD_MUNICIPIO"]})
        ints = ["ano", "zona", "secao", "nr_local", "eleitores"]
        df[ints] = df[ints].astype(int)
        partes.append(df.drop(columns="cd_municipio"))
    return pd.concat(partes, ignore_index=True)


def build(years=YEARS) -> dict[str, pd.DataFrame]:
    out = {"fact_votos": votos(years), "fact_perfil_secao": perfil(years)}
    for name, df in out.items():
        df.to_parquet(PROCESSED_DIR / f"{name}.parquet", index=False)
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--years", type=int, nargs="+", default=list(YEARS))
    a = p.parse_args(argv)
    out = build(a.years)
    fv = out["fact_votos"]
    print(fv.groupby(["ano", "tipo_voto"]).votos.sum().unstack(fill_value=0))
    pf = out["fact_perfil_secao"]
    print("perfil: eleitores por ano", pf.groupby("ano").eleitores.sum().to_dict())


if __name__ == "__main__":
    main()
