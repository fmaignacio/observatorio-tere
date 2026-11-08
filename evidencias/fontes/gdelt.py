"""GDELT DOC 2.0 (imprensa mundial, gratuita).

Limite: 1 requisição a cada 5 s. Na prática, o GDELT às vezes recusa por IP
mesmo respeitando o intervalo. Nesse caso a consulta é pulada sem erro.
"""
from __future__ import annotations

from datetime import datetime

from evidencias.base import Achado, Http

URL = "https://api.gdeltproject.org/api/v2/doc/doc"


class Limitado(RuntimeError):
    pass


def parse(payload: dict, consulta: str) -> list[Achado]:
    out = []
    for a in payload.get("articles", []):
        data = a.get("seendate", "")
        try:
            data = datetime.strptime(data, "%Y%m%dT%H%M%SZ").isoformat() + "+00:00"
        except ValueError:
            pass
        out.append(Achado(fonte="gdelt", url=a.get("url", ""), titulo=a.get("title", ""),
                          publicado_em=data, veiculo=a.get("domain", ""), consulta=consulta))
    return out


def buscar(consultas: list[str], http: Http | None = None, janela: str = "1y") -> tuple[list[Achado], list[str]]:
    """Retorna (achados, consultas_puladas)."""
    http = http or Http(intervalo=6.0)
    achados, puladas = [], []
    for q in consultas:
        r = http.get(URL, params={"query": f"{q} sourcelang:portuguese", "mode": "artlist", "format": "json",
                                  "maxrecords": 100, "timespan": janela, "sort": "datedesc"})
        if r.status_code == 429 or r.text.lstrip().startswith("Please limit"):
            puladas.append(q)
            continue
        r.raise_for_status()
        try:
            achados += parse(r.json(), q)
        except ValueError:  # resposta vazia ou não-JSON
            puladas.append(q)
    return achados, puladas
