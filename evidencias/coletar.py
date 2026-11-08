"""Coleta relatos de perseguição política em Teresópolis e põe na fila de revisão.

Uso:
    python -m evidencias.coletar [--fontes google_news gdelt bluesky youtube]

YouTube só roda com YOUTUBE_API_KEY no ambiente. Uma fonte que falha é
registrada e não interrompe as outras.
"""
from __future__ import annotations

import argparse
import sys

from evidencias import fila, termos
from evidencias.fontes import bluesky, gdelt, google_news, youtube
from evidencias.termos import menciona_municipio

FONTES = ("google_news", "gdelt", "bluesky", "youtube")


def coletar(fontes=FONTES) -> dict[str, str]:
    con = fila.conectar()
    rel = {}
    for f in fontes:
        try:
            if f == "google_news":
                ach = google_news.buscar(termos.consultas())
            elif f == "gdelt":
                ach, puladas = gdelt.buscar(termos.consultas())
                if puladas:
                    rel[f + "_aviso"] = f"{len(puladas)}/{len(termos.consultas())} consultas recusadas pelo limite do GDELT"
            elif f == "bluesky":
                ach = bluesky.buscar(termos.consultas_simples())
            elif f == "youtube":
                if not youtube.disponivel():
                    rel[f] = "pulado (defina YOUTUBE_API_KEY)"
                    continue
                ach = [a for a in youtube.buscar(termos.consultas_simples())
                       if menciona_municipio(a.titulo + " " + a.trecho)]
            else:
                raise ValueError(f)
            novos = fila.inserir(con, ach)
            rel[f] = f"{len(ach)} encontrados, {novos} novos"
        except Exception as e:  # uma fonte não derruba as outras
            rel[f] = f"ERRO: {type(e).__name__}: {e}"[:200]
    tot = dict(con.execute("SELECT status, COUNT(*) FROM achados GROUP BY status").fetchall())
    rel["fila"] = ", ".join(f"{k}: {v}" for k, v in sorted(tot.items())) or "vazia"
    return rel


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--fontes", nargs="+", choices=FONTES, default=list(FONTES))
    a = p.parse_args(argv)
    rel = coletar(a.fontes)
    for k, v in rel.items():
        print(f"{k:>16}: {v}")
    return 1 if any(v.startswith("ERRO") for v in rel.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
