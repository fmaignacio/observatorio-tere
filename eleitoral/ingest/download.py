"""Download de arquivos do Portal de Dados Abertos do TSE (CDN odsele)."""
from __future__ import annotations

import time
import zipfile
from pathlib import Path

import requests

RAW_DIR = Path(__file__).resolve().parents[2] / "data" / "raw"
CDN = "https://cdn.tse.jus.br/estatistica/sead/odsele"

# dataset -> (pasta no CDN, padrão do nome; {y}=ano, {uf}=UF)
DATASETS = {
    "votacao_secao": ("votacao_secao", "votacao_secao_{y}_{uf}.zip"),
    "votacao_candidato_munzona": ("votacao_candidato_munzona", "votacao_candidato_munzona_{y}.zip"),
    "detalhe_votacao_munzona": ("detalhe_votacao_munzona", "detalhe_votacao_munzona_{y}.zip"),
    "consulta_cand": ("consulta_cand", "consulta_cand_{y}.zip"),
    "perfil_eleitor_secao": ("perfil_eleitor_secao", "perfil_eleitor_secao_{y}_{uf}.zip"),
    "eleitorado_local_votacao": ("eleitorado_locais_votacao", "eleitorado_local_votacao_{y}.zip"),
}


def zip_name(year: int, uf: str = "RJ", dataset: str = "votacao_secao") -> str:
    return DATASETS[dataset][1].format(y=year, uf=uf)


def zip_url(year: int, uf: str = "RJ", dataset: str = "votacao_secao") -> str:
    folder, _ = DATASETS[dataset]
    return f"{CDN}/{folder}/{zip_name(year, uf, dataset)}"


def _is_valid_zip(path: Path) -> bool:
    try:
        with zipfile.ZipFile(path) as zf:
            return zf.testzip() is None
    except zipfile.BadZipFile:
        return False


def download_zip(year: int, uf: str = "RJ", dest: Path = RAW_DIR, force: bool = False,
                 dataset: str = "votacao_secao", retries: int = 8) -> Path:
    """Baixa o ZIP com retomada (HTTP Range) e valida a integridade.

    O CDN do TSE às vezes corta a conexão no meio sem erro. Por isso a
    validação do ZIP é obrigatória.
    """
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / zip_name(year, uf, dataset)
    if path.exists() and not force and _is_valid_zip(path):
        return path
    part = path.with_suffix(".zip.part")
    if force:
        part.unlink(missing_ok=True)
    url = zip_url(year, uf, dataset)
    for attempt in range(1, retries + 1):
        offset = part.stat().st_size if part.exists() else 0
        headers = {"Range": f"bytes={offset}-"} if offset else {}
        try:
            with requests.get(url, stream=True, timeout=60, headers=headers) as r:
                if r.status_code == 416:  # já completo
                    pass
                else:
                    r.raise_for_status()
                    mode = "ab" if r.status_code == 206 else "wb"
                    with open(part, mode) as f:
                        for chunk in r.iter_content(chunk_size=1 << 20):
                            f.write(chunk)
        except requests.RequestException:
            time.sleep(2 * attempt)
            continue
        if _is_valid_zip(part):
            part.rename(path)
            return path
    raise IOError(f"Falha ao baixar {url} após {retries} tentativas")
