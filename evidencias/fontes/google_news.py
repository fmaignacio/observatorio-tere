"""Google Notícias via RSS de busca.

Os termos do feed restringem o uso a leitura pessoal e não comercial. Serve
para pesquisa e triagem; não republique o feed.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from urllib.parse import quote_plus

from evidencias.base import Achado, Http

URL = "https://news.google.com/rss/search?q={q}&hl=pt-BR&gl=BR&ceid=BR:pt-419"


def parse(xml_text: str, consulta: str) -> list[Achado]:
    root = ET.fromstring(xml_text)
    out = []
    for item in root.iter("item"):
        titulo = (item.findtext("title") or "").strip()
        src = item.find("source")
        veiculo = (src.text or "").strip() if src is not None else ""
        if veiculo and titulo.endswith(" - " + veiculo):
            titulo = titulo[: -len(veiculo) - 3]
        data = item.findtext("pubDate") or ""
        try:
            data = parsedate_to_datetime(data).isoformat()
        except (TypeError, ValueError):
            pass
        out.append(Achado(fonte="google_news", url=(item.findtext("link") or "").strip(), titulo=titulo,
                          publicado_em=data, veiculo=veiculo, consulta=consulta))
    return out


def buscar(consultas: list[str], http: Http | None = None) -> list[Achado]:
    http = http or Http(intervalo=1.0)
    achados = []
    for q in consultas:
        r = http.get(URL.format(q=quote_plus(q)))
        r.raise_for_status()
        achados += parse(r.text, q)
    return achados
