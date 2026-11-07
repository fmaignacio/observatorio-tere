"""Fila de revisão em SQLite, PRIVADA (evidencias/privado/, fora do Git).

Status: pendente → confirmado | noticia | descartado.
- confirmado: caso de perseguição com fonte verificável;
- noticia: matéria relevante que não é um caso em si (contexto, análise);
- descartado: fora do tema.
"""
from __future__ import annotations

import sqlite3
from dataclasses import asdict
from pathlib import Path

from evidencias.base import Achado

DB = Path(__file__).resolve().parent / "privado" / "fila.sqlite"
STATUS = ("pendente", "confirmado", "noticia", "descartado")
TIPOS_CASO = ("ameaca", "assedio_eleitoral", "demissao_exoneracao", "agressao", "processo", "discurso_autoridade", "outro")

SCHEMA = """
CREATE TABLE IF NOT EXISTS achados (
  id TEXT PRIMARY KEY, fonte TEXT, tipo_fonte TEXT, url TEXT, titulo TEXT, trecho TEXT,
  publicado_em TEXT, veiculo TEXT, consulta TEXT, coletado_em TEXT,
  status TEXT DEFAULT 'pendente', tipo_caso TEXT, nota TEXT, revisado_em TEXT
);
CREATE INDEX IF NOT EXISTS ix_status ON achados(status);
"""


def conectar(db: Path = DB) -> sqlite3.Connection:
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def inserir(con: sqlite3.Connection, achados: list[Achado]) -> int:
    """Insere só o que é novo (por URL). Retorna quantos entraram."""
    antes = con.total_changes
    con.executemany(
        """INSERT OR IGNORE INTO achados (id, fonte, tipo_fonte, url, titulo, trecho, publicado_em, veiculo,
           consulta, coletado_em) VALUES (:id, :fonte, :tipo_fonte, :url, :titulo, :trecho, :publicado_em,
           :veiculo, :consulta, :coletado_em)""",
        [{**asdict(a), "id": a.id} for a in achados if a.url],
    )
    con.commit()
    return con.total_changes - antes


def marcar(con: sqlite3.Connection, id_: str, status: str, tipo_caso: str | None = None, nota: str | None = None) -> bool:
    if status not in STATUS:
        raise ValueError(f"status deve ser um de {STATUS}")
    if tipo_caso and tipo_caso not in TIPOS_CASO:
        raise ValueError(f"tipo_caso deve ser um de {TIPOS_CASO}")
    cur = con.execute(
        "UPDATE achados SET status=?, tipo_caso=COALESCE(?, tipo_caso), nota=COALESCE(?, nota), "
        "revisado_em=datetime('now') WHERE id LIKE ?",
        (status, tipo_caso, nota, id_ + "%"),
    )
    con.commit()
    return cur.rowcount == 1
