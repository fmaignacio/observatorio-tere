"""Constrói as dimensões da V2 a partir dos arquivos brutos do TSE.

Uso:
    python -m eleitoral.transform.build_dims [--years 2022 2024 2026]

Saídas em data/processed/:
    dim_local_votacao.parquet  (ano, zona, nr_local)
    dim_secao.parquet          (ano, zona, secao)
    dim_candidato.parquet      (ano, cd_cargo, sq_candidato), só quem teve voto em Teresópolis
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from eleitoral.ingest.column_mappings import CD_MUNICIPIO_TERESOPOLIS, DATASET_MAPS
from eleitoral.ingest.download import RAW_DIR, zip_name
from eleitoral.ingest.reader import SchemaError, read_filtered
from eleitoral.ingest.reconcile import oficial_candidatos

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
YEARS = (2022, 2024, 2026)
MUN = {"CD_MUNICIPIO": str(CD_MUNICIPIO_TERESOPOLIS)}


def _read(dataset: str, year: int, filters: dict | None = None) -> pd.DataFrame:
    m = DATASET_MAPS[dataset][year]
    return read_filtered(RAW_DIR / zip_name(year, dataset=dataset), m["member"], m["rename"], filters=filters)


def _unique_by(df: pd.DataFrame, key: list[str], name: str) -> pd.DataFrame:
    dup = df.duplicated(key, keep=False)
    if dup.any():
        raise SchemaError(f"{name}: chave {key} não é única ({dup.sum()} linhas)")
    return df


def locais_e_secoes(year: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = _read("eleitorado_local_votacao", year, MUN)
    df = df[df.turno == "1"].drop(columns=["turno", "cd_municipio"])  # cadastro igual nos dois turnos
    ints = ["ano", "zona", "secao", "secao_principal", "nr_local", "eleitores_aptos"]
    df[ints] = df[ints].astype(int)
    # Coordenadas vêm com ponto ou vírgula decimal, dependendo do ano; -1 = sem coordenada.
    for c in ("latitude", "longitude"):
        df[c] = df[c].str.replace(",", ".", regex=False).astype(float)
    df[["latitude", "longitude"]] = df[["latitude", "longitude"]].where(lambda x: x != -1)
    df["agregada"] = df.tipo_secao.eq("Agregada")
    # Seção agregada: os votos são apurados na seção principal.
    df["secao_apuracao"] = df.secao.where(~df.agregada, df.secao_principal)

    locais = (df.groupby(["ano", "zona", "nr_local"], as_index=False)
                .agg(local_votacao=("local_votacao", "first"), tipo_local=("tipo_local", "first"),
                     endereco=("endereco", "first"), bairro=("bairro", "first"), cep=("cep", "first"),
                     latitude=("latitude", "first"), longitude=("longitude", "first"),
                     secoes=("secao", "nunique"), eleitores_aptos=("eleitores_aptos", "sum")))
    secoes = df[["ano", "zona", "secao", "nr_local", "agregada", "secao_principal", "secao_apuracao",
                 "eleitores_aptos", "situacao_secao"]]
    return (_unique_by(locais, ["ano", "zona", "nr_local"], "dim_local_votacao"),
            _unique_by(secoes, ["ano", "zona", "secao"], "dim_secao"))


def candidatos(year: int, sq_com_voto: set[int]) -> pd.DataFrame:
    """Candidatos com voto em Teresópolis.

    ``apto`` = consta de votacao_candidato_munzona. Os votos dos inaptos viram
    nulo técnico. O campo DS_SITUACAO_CANDIDATURA não serve para isso: vem
    "#NE" para todos em 2024 e 2026.
    """
    oficiais = set(oficial_candidatos(year).sq_candidato)
    df = _read("consulta_cand", year)
    df["sq_candidato"] = df.sq_candidato.astype("int64")
    df = df[df.sq_candidato.isin(sq_com_voto)].copy()
    # Em 2º turno o candidato aparece duas vezes; fica uma linha com o resultado final.
    df = df.sort_values("turno").groupby(["sq_candidato"], as_index=False).last()
    df[["ano", "cd_cargo", "numero_candidato", "nr_partido"]] = \
        df[["ano", "cd_cargo", "numero_candidato", "nr_partido"]].astype(int)
    df["eleito"] = df.resultado.str.startswith("ELEITO")
    df["apto"] = df.sq_candidato.isin(oficiais)
    faltando = sq_com_voto - set(df.sq_candidato)
    if faltando:
        raise SchemaError(f"{year}: {len(faltando)} candidatos com voto ausentes do consulta_cand")
    df = df.drop(columns=["turno"])
    return _unique_by(df, ["ano", "cd_cargo", "sq_candidato"], "dim_candidato")


def build(years=YEARS) -> dict[str, pd.DataFrame]:
    locs, secs, cands = [], [], []
    for y in years:
        loc, sec = locais_e_secoes(y)
        fv = pd.read_parquet(PROCESSED_DIR / f"fact_votos_{y}.parquet", columns=["zona", "secao", "sq_candidato"])
        apur = set(zip(sec.zona, sec.secao_apuracao))
        fora = set(zip(fv.zona, fv.secao)) - apur
        if fora:
            raise SchemaError(f"{y}: seções com voto fora do cadastro: {sorted(fora)[:10]}")
        locs.append(loc)
        secs.append(sec)
        cands.append(candidatos(y, set(fv.sq_candidato[fv.sq_candidato > 0])))
    out = {
        "dim_local_votacao": pd.concat(locs, ignore_index=True),
        "dim_secao": pd.concat(secs, ignore_index=True),
        "dim_candidato": pd.concat(cands, ignore_index=True),
    }
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in out.items():
        df.to_parquet(PROCESSED_DIR / f"{name}.parquet", index=False)
    return out


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--years", type=int, nargs="+", default=list(YEARS))
    a = p.parse_args(argv)
    for name, df in build(a.years).items():
        print(f"{name}: {len(df)} linhas | por ano: {df.groupby('ano').size().to_dict()}")


if __name__ == "__main__":
    main()
