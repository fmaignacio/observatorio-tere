"""Ingestão da votação por seção do TSE para Teresópolis.

Uso:
    python -m eleitoral.ingest.tse --year 2022 [--download]
"""
from __future__ import annotations

import argparse
import csv
import io
import logging
import zipfile
from pathlib import Path

import pandas as pd

from eleitoral.ingest.column_mappings import (
    CD_MUNICIPIO_TERESOPOLIS,
    COLUMN_MAPS,
    NM_MUNICIPIO_TERESOPOLIS,
)
from eleitoral.ingest.download import RAW_DIR, download_zip, zip_name
from eleitoral.ingest.reader import SchemaError

log = logging.getLogger("eleitoral.ingest.tse")

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
ENCODING = "latin-1"
SEP = ";"

DTYPES = {
    "ano": "int16",
    "turno": "int8",
    "cd_eleicao": "int32",
    "cd_municipio": "int32",
    "zona": "int16",
    "secao": "int16",
    "cd_cargo": "int16",
    "numero_votavel": "int32",
    "sq_candidato": "int64",
    "votos": "int32",
    "nr_local": "int32",
}


def _csv_member(zf: zipfile.ZipFile) -> str:
    csvs = [n for n in zf.namelist() if n.lower().endswith(".csv")]
    if len(csvs) != 1:
        raise SchemaError(f"Esperado 1 CSV no ZIP, encontrados: {csvs}")
    return csvs[0]


def validate_header(header: list[str], year: int) -> None:
    if year not in COLUMN_MAPS:
        raise SchemaError(f"Ano {year} sem mapeamento em column_mappings.COLUMN_MAPS")
    expected = COLUMN_MAPS[year]["header"]
    if header != expected:
        missing = [c for c in expected if c not in header]
        extra = [c for c in header if c not in expected]
        raise SchemaError(
            f"Cabeçalho {year} diferente do esperado. Faltando: {missing}; novas: {extra}; "
            f"ordem igual: {sorted(header) == sorted(expected)}"
        )


def read_teresopolis(zip_path: Path, year: int, chunksize: int = 500_000) -> pd.DataFrame:
    """Lê o CSV de dentro do ZIP em chunks e mantém só Teresópolis."""
    rename = COLUMN_MAPS[year]["rename"]
    with zipfile.ZipFile(zip_path) as zf:
        member = _csv_member(zf)
        with zf.open(member) as raw:
            text = io.TextIOWrapper(raw, encoding=ENCODING, newline="")
            header = next(csv.reader(text, delimiter=SEP))
            validate_header(header, year)
            reader = pd.read_csv(
                text, sep=SEP, names=header, header=None, usecols=list(rename),
                dtype=str, chunksize=chunksize,
            )
            parts = [c[c["CD_MUNICIPIO"] == str(CD_MUNICIPIO_TERESOPOLIS)] for c in reader]
    df = pd.concat(parts, ignore_index=True).rename(columns=rename)
    if df.empty:
        raise SchemaError(f"Nenhuma linha de Teresópolis (CD_MUNICIPIO={CD_MUNICIPIO_TERESOPOLIS})")
    nomes = set(df["municipio"].unique())
    if nomes != {NM_MUNICIPIO_TERESOPOLIS}:
        raise SchemaError(f"CD_MUNICIPIO bate mas NM_MUNICIPIO diverge: {nomes}")
    return df.astype(DTYPES)


def check(df: pd.DataFrame, year: int) -> None:
    """Checagens internas de consistência."""
    if set(df["ano"].unique()) != {year}:
        raise SchemaError(f"ANO_ELEICAO inesperado: {df['ano'].unique()}")
    if (df["votos"] < 0).any():
        raise SchemaError("Há votos negativos")
    key = ["turno", "cd_cargo", "zona", "secao", "numero_votavel"]
    dup = df.duplicated(key).sum()
    if dup:
        raise SchemaError(f"{dup} linhas duplicadas na chave {key}")


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["turno", "cargo"])
        .agg(secoes=("secao", lambda s: df.loc[s.index, ["zona", "secao"]].drop_duplicates().shape[0]),
             votos=("votos", "sum"))
        .reset_index()
    )


def run(year: int, download: bool = False) -> Path:
    zip_path = download_zip(year) if download else RAW_DIR / zip_name(year)
    if not zip_path.exists():
        raise FileNotFoundError(f"{zip_path} não existe; rode com --download")
    df = read_teresopolis(zip_path, year)
    check(df, year)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = PROCESSED_DIR / f"fact_votos_{year}.parquet"
    df.to_parquet(out, index=False)
    log.info("%s: %d linhas -> %s", year, len(df), out)
    print(summarize(df).to_string(index=False))
    return out


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--year", type=int, required=True, choices=sorted(COLUMN_MAPS))
    p.add_argument("--download", action="store_true", help="baixa o ZIP do TSE se não existir")
    args = p.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    run(args.year, download=args.download)


if __name__ == "__main__":
    main()
