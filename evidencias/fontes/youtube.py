"""YouTube Data API v3 (search.list). Precisa de YOUTUBE_API_KEY no ambiente.

Cota gratuita: 10.000 unidades/dia; cada busca custa 100.
Como gerar a chave: console.cloud.google.com → criar projeto → "APIs e
serviços" → ativar "YouTube Data API v3" → Credenciais → Criar chave de API.
"""
from __future__ import annotations

import os

from evidencias.base import Achado, Http

URL = "https://www.googleapis.com/youtube/v3/search"


def parse(payload: dict, consulta: str) -> list[Achado]:
    out = []
    for it in payload.get("items", []):
        vid = (it.get("id") or {}).get("videoId")
        sn = it.get("snippet") or {}
        if not vid:
            continue
        out.append(Achado(fonte="youtube", url=f"https://www.youtube.com/watch?v={vid}", titulo=sn.get("title", ""),
                          trecho=sn.get("description", ""), publicado_em=sn.get("publishedAt", ""),
                          veiculo=sn.get("channelTitle", ""), consulta=consulta, tipo_fonte="rede_social"))
    return out


def disponivel() -> bool:
    return bool(os.environ.get("YOUTUBE_API_KEY"))


def buscar(consultas: list[str], http: Http | None = None) -> list[Achado]:
    key = os.environ["YOUTUBE_API_KEY"]
    http = http or Http()
    achados = []
    for q in consultas:
        r = http.get(URL, params={"part": "snippet", "q": q, "type": "video", "maxResults": 50,
                                  "regionCode": "BR", "relevanceLanguage": "pt", "order": "date", "key": key})
        r.raise_for_status()
        achados += parse(r.json(), q)
    return achados
