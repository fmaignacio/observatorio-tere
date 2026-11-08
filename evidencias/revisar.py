"""Revisão humana da fila e exportação do catálogo.

Uso:
    python -m evidencias.revisar listar [--status pendente] [--fonte bluesky] [--limite 30]
    python -m evidencias.revisar marcar <id> confirmado --tipo ameaca --nota "BO nº ..., confirmado pela vítima"
    python -m evidencias.revisar marcar <id> descartado
    python -m evidencias.revisar exportar

O <id> pode ser abreviado (os primeiros caracteres bastam se forem únicos).

`exportar` gera evidencias/catalogo.csv (versionável) só com itens revisados:
- da imprensa: status confirmado ou noticia;
- de rede social: só status confirmado, e sem o texto do post nem o perfil,
  porque são dados pessoais. Fica só o link, para quem revisar conferir.
"""
from __future__ import annotations

import argparse
import csv
import sys
import textwrap
from pathlib import Path

from evidencias import fila

CATALOGO = Path(__file__).resolve().parent / "catalogo.csv"
COLS = ["id", "status", "tipo_caso", "publicado_em", "fonte", "veiculo", "titulo", "url", "nota", "revisado_em"]


def listar(con, status="pendente", fonte=None, limite=30):
    q = "SELECT * FROM achados WHERE status=?" + (" AND fonte=?" if fonte else "") + \
        " ORDER BY publicado_em DESC LIMIT ?"
    args = [status, *([fonte] if fonte else []), limite]
    rows = con.execute(q, args).fetchall()
    for r in rows:
        print(f"[{r['id'][:8]}] {r['publicado_em'][:10]}  {r['fonte']:<11} {r['veiculo'][:30]}")
        print(textwrap.indent(textwrap.fill(r["titulo"], 100), "    "))
        if r["trecho"] and r["trecho"] != r["titulo"]:
            print(textwrap.indent(textwrap.shorten(r["trecho"], 240), "    > "))
        print(f"    {r['url']}\n")
    print(f"{len(rows)} itens com status '{status}'" + (f" de {fonte}" if fonte else ""))


def exportar(con, destino: Path = CATALOGO) -> int:
    rows = con.execute(
        "SELECT * FROM achados WHERE (tipo_fonte='imprensa' AND status IN ('confirmado','noticia')) "
        "OR (tipo_fonte='rede_social' AND status='confirmado') ORDER BY publicado_em DESC"
    ).fetchall()
    with open(destino, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            d = {c: r[c] for c in COLS}
            if r["tipo_fonte"] == "rede_social":
                d["veiculo"] = r["fonte"]       # sem o perfil da pessoa
                d["titulo"] = "(post em rede social)"
            w.writerow(d)
    return len(rows)


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    l = sub.add_parser("listar")
    l.add_argument("--status", default="pendente", choices=fila.STATUS)
    l.add_argument("--fonte")
    l.add_argument("--limite", type=int, default=30)
    m = sub.add_parser("marcar")
    m.add_argument("id")
    m.add_argument("status", choices=fila.STATUS)
    m.add_argument("--tipo", choices=fila.TIPOS_CASO)
    m.add_argument("--nota")
    sub.add_parser("exportar")
    a = p.parse_args(argv)
    con = fila.conectar()
    if a.cmd == "listar":
        listar(con, a.status, a.fonte, a.limite)
    elif a.cmd == "marcar":
        if not fila.marcar(con, a.id, a.status, a.tipo, a.nota):
            print("id não encontrado ou ambíguo; use mais caracteres")
            return 1
        print("ok")
    else:
        print(f"{exportar(con)} itens exportados para {CATALOGO}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
