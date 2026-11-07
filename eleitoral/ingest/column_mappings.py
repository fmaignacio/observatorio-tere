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


# ── Demais conjuntos do TSE ─────────────────────────────────────────────────
# Para cada conjunto e ano: o arquivo dentro do ZIP (regex) e as colunas
# mantidas -> nome padronizado. O leitor falha se alguma coluna não existir.
# Validado em 2026-11-07 contra os arquivos reais.

_CAND = {
    "ANO_ELEICAO": "ano", "NR_TURNO": "turno", "SG_UE": "sg_ue", "CD_CARGO": "cd_cargo",
    "DS_CARGO": "cargo", "SQ_CANDIDATO": "sq_candidato", "NR_CANDIDATO": "numero_candidato",
    "NM_CANDIDATO": "nome", "NM_URNA_CANDIDATO": "nome_urna",
    "DS_SITUACAO_CANDIDATURA": "situacao_candidatura", "NR_PARTIDO": "nr_partido",
    "SG_PARTIDO": "partido", "NM_FEDERACAO": "federacao", "DS_COMPOSICAO_FEDERACAO": "composicao_federacao",
    "NM_COLIGACAO": "coligacao", "DS_COMPOSICAO_COLIGACAO": "composicao_coligacao",
    "DS_GENERO": "genero", "DS_GRAU_INSTRUCAO": "grau_instrucao", "DS_COR_RACA": "cor_raca",
    "DS_OCUPACAO": "ocupacao", "DT_NASCIMENTO": "dt_nascimento", "DS_SIT_TOT_TURNO": "resultado",
}  # CPF, e-mail e título de eleitor são descartados de propósito.

_LOCAL = {
    "AA_ELEICAO": "ano", "NR_TURNO": "turno", "CD_MUNICIPIO": "cd_municipio", "NR_ZONA": "zona",
    "NR_SECAO": "secao", "DS_TIPO_SECAO_AGREGADA": "tipo_secao", "NR_SECAO_PRINCIPAL": "secao_principal",
    "NR_LOCAL_VOTACAO": "nr_local", "NM_LOCAL_VOTACAO": "local_votacao", "DS_TIPO_LOCAL": "tipo_local",
    "DS_ENDERECO": "endereco", "NM_BAIRRO": "bairro", "NR_CEP": "cep",
    "NR_LATITUDE": "latitude", "NR_LONGITUDE": "longitude", "QT_ELEITOR_SECAO": "eleitores_aptos",
    "DS_SITU_SECAO": "situacao_secao",
}

_PERFIL_2022 = {
    "ANO_ELEICAO": "ano", "CD_MUNICIPIO": "cd_municipio", "NR_ZONA": "zona", "NR_SECAO": "secao",
    "NR_LOCAL_VOTACAO": "nr_local", "DS_GENERO": "genero", "DS_ESTADO_CIVIL": "estado_civil",
    "DS_FAIXA_ETARIA": "faixa_etaria", "DS_GRAU_ESCOLARIDADE": "escolaridade", "DS_RACA_COR": "raca_cor",
    "QT_ELEITORES_PERFIL": "eleitores",
}
# 2026: ANO_ELEICAO -> AA_ELEICAO, QT_ELEITORES_PERFIL -> QT_ELEITORES
_PERFIL_2026 = {("AA_ELEICAO" if k == "ANO_ELEICAO" else "QT_ELEITORES" if k == "QT_ELEITORES_PERFIL" else k): v
                for k, v in _PERFIL_2022.items()}

DATASET_MAPS: dict[str, dict[int, dict]] = {
    "consulta_cand": {y: {"member": rf"consulta_cand_{y}_RJ\.csv$", "rename": _CAND} for y in (2022, 2024, 2026)},
    "eleitorado_local_votacao": {
        2022: {"member": r"eleitorado_local_votacao_2022\.csv$", "rename": _LOCAL},
        2024: {"member": r"eleitorado_local_votacao_2024\.csv$", "rename": _LOCAL},
        2026: {"member": r"eleitorado_local_votacao_2026_RJ\.csv$", "rename": _LOCAL},  # passou a ser por UF
    },
    "perfil_eleitor_secao": {
        2022: {"member": r"perfil_eleitor_secao_2022_RJ\.csv$", "rename": _PERFIL_2022},
        2024: {"member": r"perfil_eleitor_secao_2024_RJ\.csv$", "rename": _PERFIL_2022},
        2026: {"member": r"perfil_eleitor_secao_2026_RJ\.csv$", "rename": _PERFIL_2026},
    },
}
