"""Download dos arquivos de votação por seção do TSE."""
from __future__ import annotations

from pathlib import Path

import requests

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
BASE_URL = "https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao"


def zip_name(year: int, uf: str = "RJ") -> str:
    return f"votacao_secao_{year}_{uf}.zip"


def zip_url(year: int, uf: str = "RJ") -> str:
    return f"{BASE_URL}/{zip_name(year, uf)}"


def download_zip(year: int, uf: str = "RJ", dest: Path = RAW_DIR, force: bool = False) -> Path:
    """Baixa o ZIP do ano/UF para ``dest``. Não rebaixa se já existir (salvo ``force``)."""
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / zip_name(year, uf)
    if path.exists() and not force:
        return path
    tmp = path.with_suffix(".part")
    with requests.get(zip_url(year, uf), stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    tmp.rename(path)
    return path
