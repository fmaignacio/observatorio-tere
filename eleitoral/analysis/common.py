"""Utilitários compartilhados pelas análises da V2."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
LOCAL = ["zona", "nr_local"]  # código estável entre anos (os nomes mudam de grafia)
VALIDOS = ("nominal", "legenda")


@lru_cache(maxsize=None)
def load(name: str) -> pd.DataFrame:
    return pd.read_parquet(PROCESSED_DIR / f"{name}.parquet")


def votos_eleicao(ano: int, cd_cargo: int, turno: int = 1) -> pd.DataFrame:
    fv = load("fact_votos")
    out = fv[(fv.ano == ano) & (fv.cd_cargo == cd_cargo) & (fv.turno == turno)]
    if out.empty:
        raise ValueError(f"Sem votos para ano={ano} cargo={cd_cargo} turno={turno}")
    return out


def rotulo(df: pd.DataFrame, por: str) -> pd.Series:
    """Categoria do voto: 'partido' (sigla, ou número para legenda) ou 'candidato'."""
    if por == "partido":
        sig = df.partido.copy()
        leg = df.tipo_voto.eq("legenda")
        # Legenda: busca a sigla pelo número do partido entre os candidatos do mesmo ano.
        mapa = (df.dropna(subset=["partido"]).drop_duplicates("nr_partido")
                  .set_index("nr_partido").partido)
        sig[leg] = df.loc[leg, "nr_partido"].map(mapa).fillna(df.loc[leg, "numero_votavel"].astype(str))
        return sig
    if por == "candidato":
        return df.nome_votavel
    raise ValueError(por)


def aptos_por_local(ano: int) -> pd.Series:
    sec = load("dim_secao")
    return sec[sec.ano == ano].groupby(LOCAL).eleitores_aptos.sum()
