"""Mapeamento de colunas do TSE (votacao_secao_<ano>_<UF>.csv) por ano.

Validado em 2026-11-07 contra os arquivos reais: 2022, 2024 e 2026 têm
exatamente o mesmo cabeçalho (26 colunas, mesma ordem). O mapeamento continua
explícito por ano para que uma mudança futura do TSE quebre a validação em vez
de gerar dados silenciosamente errados.
"""
from __future__ import annotations

# Cabeçalho completo, na ordem em que aparece no CSV.
HEADER_V1 = [
    "DT_GERACAO", "HH_GERACAO", "ANO_ELEICAO", "CD_TIPO_ELEICAO", "NM_TIPO_ELEICAO",
    "NR_TURNO", "CD_ELEICAO", "DS_ELEICAO", "DT_ELEICAO", "TP_ABRANGENCIA",
    "SG_UF", "SG_UE", "NM_UE", "CD_MUNICIPIO", "NM_MUNICIPIO",
    "NR_ZONA", "NR_SECAO", "CD_CARGO", "DS_CARGO", "NR_VOTAVEL",
    "NM_VOTAVEL", "QT_VOTOS", "NR_LOCAL_VOTACAO", "SQ_CANDIDATO", "NM_LOCAL_VOTACAO",
    "DS_LOCAL_VOTACAO_ENDERECO",
]

# Colunas mantidas -> nome padronizado (snake_case, sem acento).
RENAME_V1 = {
    "ANO_ELEICAO": "ano",
    "NR_TURNO": "turno",
    "CD_ELEICAO": "cd_eleicao",
    "DT_ELEICAO": "dt_eleicao",
    "SG_UF": "uf",
    "CD_MUNICIPIO": "cd_municipio",
    "NM_MUNICIPIO": "municipio",
    "NR_ZONA": "zona",
    "NR_SECAO": "secao",
    "CD_CARGO": "cd_cargo",
    "DS_CARGO": "cargo",
    "NR_VOTAVEL": "numero_votavel",
    "NM_VOTAVEL": "nome_votavel",
    "SQ_CANDIDATO": "sq_candidato",
    "QT_VOTOS": "votos",
    "NR_LOCAL_VOTACAO": "nr_local",
    "NM_LOCAL_VOTACAO": "local_votacao",
    "DS_LOCAL_VOTACAO_ENDERECO": "endereco_local",
}

COLUMN_MAPS: dict[int, dict] = {
    2022: {"header": HEADER_V1, "rename": RENAME_V1},
    2024: {"header": HEADER_V1, "rename": RENAME_V1},
    2026: {"header": HEADER_V1, "rename": RENAME_V1},
}

# Código TSE do município (não é o código IBGE).
CD_MUNICIPIO_TERESOPOLIS = 59153
NM_MUNICIPIO_TERESOPOLIS = "TERESÓPOLIS"

# Valores especiais de NR_VOTAVEL no TSE.
VOTO_BRANCO = 95
VOTO_NULO = 96
