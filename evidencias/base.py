"""Tipos e utilitários comuns aos coletores."""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import requests

USER_AGENT = "observatorio-tere/0.1 (pesquisa sobre violência política em Teresópolis)"


@dataclass
class Achado:
    fonte: str             # google_news | gdelt | bluesky | youtube
    url: str
    titulo: str
    trecho: str = ""
    publicado_em: str = ""  # ISO 8601, quando a fonte informa
    veiculo: str = ""      # nome do site/canal/perfil
    consulta: str = ""
    tipo_fonte: str = "imprensa"  # imprensa | rede_social
    coletado_em: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(timespec="seconds"))

    @property
    def id(self) -> str:
        return hashlib.sha1(self.url.strip().encode()).hexdigest()[:16]


class Http:
    """requests com User-Agent, timeout e intervalo mínimo entre chamadas."""

    def __init__(self, intervalo: float = 0.0):
        self.s = requests.Session()
        self.s.headers["User-Agent"] = USER_AGENT
        self.intervalo = intervalo
        self._ultimo = 0.0

    def get(self, url: str, **kw) -> requests.Response:
        espera = self.intervalo - (time.monotonic() - self._ultimo)
        if espera > 0:
            time.sleep(espera)
        try:
            return self.s.get(url, timeout=kw.pop("timeout", 30), **kw)
        finally:
            self._ultimo = time.monotonic()
