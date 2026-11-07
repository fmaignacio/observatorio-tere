"""Swing: variação da participação de cada partido/candidato por local de votação.

Uso:
    python -m eleitoral.analysis.swing --de 2022:3 --para 2026:3 [--por partido] [--top 10]

``ano:cd_cargo``. Cargos: 3 Governador, 5 Senador, 6 Dep. Federal,
7 Dep. Estadual, 11 Prefeito, 13 Vereador.

A participação é calculada sobre os votos válidos (nominais + legenda) do local.
Os locais são casados por (zona, nr_local); só entram os que existem nos dois anos.
"""
from __future__ import annotations

import argparse

import pandas as pd

from eleitoral.analysis.common import LOCAL, PROCESSED_DIR, VALIDOS, load, rotulo, votos_eleicao


def participacao(ano: int, cd_cargo: int, por: str = "partido", turno: int = 1) -> pd.DataFrame:
    v = votos_eleicao(ano, cd_cargo, turno)
    v = v[v.tipo_voto.isin(VALIDOS)].assign(grupo=lambda d: rotulo(d, por))
    g = v.groupby([*LOCAL, "grupo"], as_index=False).votos.sum()
    g["share"] = g.votos / g.groupby(LOCAL).votos.transform("sum")
    return g


def swing(de: tuple[int, int], para: tuple[int, int], por: str = "partido") -> pd.DataFrame:
    a = participacao(*de, por=por).rename(columns={"votos": "votos_de", "share": "share_de"})
    b = participacao(*para, por=por).rename(columns={"votos": "votos_para", "share": "share_para"})
    comuns = a[LOCAL].drop_duplicates().merge(b[LOCAL].drop_duplicates())
    m = (a.merge(b, on=[*LOCAL, "grupo"], how="outer").merge(comuns, on=LOCAL))
    m[["votos_de", "votos_para", "share_de", "share_para"]] = \
        m[["votos_de", "votos_para", "share_de", "share_para"]].fillna(0)
    m["swing_pp"] = 100 * (m.share_para - m.share_de)
    loc = load("dim_local_votacao")
    nomes = loc[loc.ano == para[0]][[*LOCAL, "local_votacao", "bairro"]]
    return m.merge(nomes, on=LOCAL, how="left")


def resumo_municipio(sw: pd.DataFrame) -> pd.DataFrame:
    t = sw.groupby("grupo")[["votos_de", "votos_para"]].sum()
    t["share_de"] = 100 * t.votos_de / t.votos_de.sum()
    t["share_para"] = 100 * t.votos_para / t.votos_para.sum()
    t["swing_pp"] = t.share_para - t.share_de
    return t.assign(_o=t[["votos_de", "votos_para"]].max(axis=1)).sort_values("_o", ascending=False).drop(columns="_o")


def _par(s: str) -> tuple[int, int]:
    a, c = s.split(":")
    return int(a), int(c)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--de", type=_par, default=(2022, 3))
    p.add_argument("--para", type=_par, default=(2026, 3))
    p.add_argument("--por", choices=["partido", "candidato"], default="partido")
    p.add_argument("--top", type=int, default=8)
    a = p.parse_args(argv)
    sw = swing(a.de, a.para, a.por)
    out = PROCESSED_DIR / f"analysis_swing_{a.de[0]}c{a.de[1]}_{a.para[0]}c{a.para[1]}_{a.por}.parquet"
    sw.to_parquet(out, index=False)
    r = resumo_municipio(sw)
    print(f"== Município ({sw[LOCAL].drop_duplicates().shape[0]} locais comuns) — % dos válidos")
    print(r.head(a.top).round(1).to_string())
    for g in r.head(3).index:
        s = sw[sw.grupo == g].sort_values("swing_pp")
        print(f"\n== {g}: locais com maior queda / maior alta (pp)")
        print(pd.concat([s.head(3), s.tail(3)])[["local_votacao", "bairro", "share_de", "share_para", "swing_pp"]]
              .assign(share_de=lambda d: (100 * d.share_de).round(1), share_para=lambda d: (100 * d.share_para).round(1),
                      swing_pp=lambda d: d.swing_pp.round(1)).to_string(index=False))
    print(f"\nSalvo em {out}")


if __name__ == "__main__":
    main()
