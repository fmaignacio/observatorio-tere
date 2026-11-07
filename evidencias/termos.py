"""Termos de busca da V3.

O foco são RELATOS de perseguição, intimidação ou coação política em
Teresópolis, não o monitoramento do que pessoas comuns postam. Cada consulta
combina o município com um termo de ocorrência.
"""

MUNICIPIO = "Teresópolis"

# Termos de ocorrência (o que caracteriza um relato).
OCORRENCIAS = [
    "perseguição política",
    "assédio eleitoral",
    "coação eleitoral",
    "violência política",
    "ameaça eleitor",
    "demitido por votar",
    "intimidação política",
    "perseguição servidor",
    "exoneração perseguição",
    "agressão militante",
]

# Usados para dar contexto (esquerda / eleitores do Lula). Entram combinados
# com o município e um termo de ocorrência genérico.
CONTEXTO = ["Lula", "PT", "esquerda", "petista"]


def consultas() -> list[str]:
    qs = [f'"{MUNICIPIO}" {o}' for o in OCORRENCIAS]
    qs += [f'"{MUNICIPIO}" {c} (perseguição OR ameaça OR agressão OR demissão)' for c in CONTEXTO]
    return qs


def consultas_simples() -> list[str]:
    """Para APIs sem operadores booleanos (Bluesky, YouTube)."""
    return [f"{MUNICIPIO} {o}" for o in OCORRENCIAS] + [f"{MUNICIPIO} {c} perseguição" for c in CONTEXTO]


def menciona_municipio(texto: str) -> bool:
    t = (texto or "").lower()
    return "teresópolis" in t or "teresopolis" in t
