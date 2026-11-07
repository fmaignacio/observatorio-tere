"""Leitura genérica de CSVs do TSE dentro de ZIPs, com filtro e validação."""
from __future__ import annotations

import csv
import io
import re
import zipfile
from pathlib import Path

import pandas as pd

ENCODING = "latin-1"
SEP = ";"


class SchemaError(ValueError):
    pass


def find_member(zf: zipfile.ZipFile, pattern: str) -> str:
    """Retorna o único CSV do ZIP cujo nome casa com ``pattern`` (regex)."""
    hits = [n for n in zf.namelist() if re.search(pattern, n, re.I)]
    if len(hits) != 1:
        raise SchemaError(f"Esperado 1 arquivo casando {pattern!r}, encontrados: {hits}")
    return hits[0]


def read_filtered(
    zip_path: Path,
    member_pattern: str,
    rename: dict[str, str],
    filters: dict[str, str] | None = None,
    expected_header: list[str] | None = None,
    chunksize: int = 500_000,
) -> pd.DataFrame:
    """Lê um CSV do ZIP em chunks, valida o cabeçalho e filtra as linhas.

    - ``rename``: colunas a manter, já com o nome padronizado. Todas precisam existir.
    - ``filters``: {coluna_original: valor_em_texto} (igualdade).
    - ``expected_header``: se passado, exige o cabeçalho idêntico, inclusive na ordem.
    """
    filters = filters or {}
    with zipfile.ZipFile(zip_path) as zf:
        member = find_member(zf, member_pattern)
        with zf.open(member) as raw:
            text = io.TextIOWrapper(raw, encoding=ENCODING, newline="")
            header = next(csv.reader(text, delimiter=SEP))
            if expected_header is not None and header != expected_header:
                missing = [c for c in expected_header if c not in header]
                extra = [c for c in header if c not in expected_header]
                raise SchemaError(f"{member}: cabeçalho divergente. Faltando: {missing}; novas: {extra}")
            needed = list(dict.fromkeys([*rename, *filters]))
            missing = [c for c in needed if c not in header]
            if missing:
                raise SchemaError(f"{member}: colunas ausentes {missing}")
            reader = pd.read_csv(text, sep=SEP, names=header, header=None, usecols=needed,
                                 dtype=str, chunksize=chunksize)
            parts = []
            for chunk in reader:
                mask = pd.Series(True, index=chunk.index)
                for col, val in filters.items():
                    mask &= chunk[col] == str(val)
                parts.append(chunk[mask])
    df = pd.concat(parts, ignore_index=True)
    return df[list(rename)].rename(columns=rename)
