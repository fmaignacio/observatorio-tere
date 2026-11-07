"""Bluesky: busca pública de posts (app.bsky.feed.searchPosts, sem login).

Posts de pessoas são dados pessoais. Só ficam os que citam Teresópolis, e
vão para a fila privada. Nada de rede social é exportado sem revisão humana.
"""
from __future__ import annotations

from evidencias.base import Achado, Http
from evidencias.termos import menciona_municipio

URL = "https://api.bsky.app/xrpc/app.bsky.feed.searchPosts"


def parse(payload: dict, consulta: str) -> list[Achado]:
    out = []
    for p in payload.get("posts", []):
        rec = p.get("record", {}) or {}
        texto = rec.get("text", "")
        if not menciona_municipio(texto):
            continue
        handle = (p.get("author") or {}).get("handle", "")
        rkey = p.get("uri", "").rsplit("/", 1)[-1]
        out.append(Achado(fonte="bluesky", url=f"https://bsky.app/profile/{handle}/post/{rkey}",
                          titulo=texto[:120], trecho=texto, publicado_em=rec.get("createdAt", ""),
                          veiculo=handle, consulta=consulta, tipo_fonte="rede_social"))
    return out


def buscar(consultas: list[str], http: Http | None = None) -> list[Achado]:
    http = http or Http(intervalo=1.0)
    achados = []
    for q in consultas:
        r = http.get(URL, params={"q": q, "limit": 100, "lang": "pt", "sort": "latest"})
        r.raise_for_status()
        achados += parse(r.json(), q)
    return achados
