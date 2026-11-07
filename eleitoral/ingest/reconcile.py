"""Reconciliação de fact_votos_<ano> com os totais oficiais do TSE.

Uso:
    python -m eleitoral.ingest.reconcile --year 2022

Checagens (todas precisam bater exatamente):
1. Por candidato: soma de votos nas seções == QT_VOTOS_NOMINAIS oficial
   (votacao_candidato_munzona). Usa os nominais *totais*, não os válidos, porque
   a urna conta normalmente votos de candidatos que depois foram anulados.
2. Por cargo/turno: soma de todos os votos nas seções == QT_COMPARECIMENTO
   × votos por eleitor (2 no Senador quando há duas vagas).
3. Por cargo/turno: brancos (NR_VOTAVEL 95) == QT_VOTOS_BRANCOS.
4. Por cargo/turno: votos dados a votáveis ausentes da lista oficial (candidatos
   inaptos e legendas de partidos sem candidato no cargo) == QT_VOTOS_NULOS_TECNICOS.
   O TSE conta esses votos como nulos técnicos, então eles não aparecem em
   votacao_candidato_munzona e não são divergência.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from eleitoral.ingest.column_mappings import CD_MUNICIPIO_TERESOPOLIS, VOTO_BRANCO
from eleitoral.ingest.download import RAW_DIR, download_zip, zip_name
from eleitoral.ingest.reader import read_filtered

PROCESSED_DIR = Path(__file__).resolve().parents[2] / "data" / "processed"
MUN = {"CD_MUNICIPIO": str(CD_MUNICIPIO_TERESOPOLIS)}


def _zip(dataset: str, year: int, download: bool) -> Path:
    return download_zip(year, dataset=dataset) if download else RAW_DIR / zip_name(year, dataset=dataset)


def oficial_candidatos(year: int, download: bool = False) -> pd.DataFrame:
    df = read_filtered(
        _zip("votacao_candidato_munzona", year, download), rf"_{year}_RJ\.csv$",
        {"NR_TURNO": "turno", "CD_CARGO": "cd_cargo", "SQ_CANDIDATO": "sq_candidato",
         "NR_CANDIDATO": "numero_votavel", "DS_COMPOSICAO_FEDERACAO": "federacao",
         "QT_VOTOS_NOMINAIS": "votos_oficial"},
        filters=MUN,
    )
    df = df.astype({"turno": int, "cd_cargo": int, "sq_candidato": "int64",
                    "numero_votavel": int, "votos_oficial": int})
    keys = ["turno", "cd_cargo", "sq_candidato", "numero_votavel", "federacao"]
    return df.groupby(keys, as_index=False).votos_oficial.sum()


def _norm_sigla(s: str) -> str:
    return "".join(s.split()).upper()


def numeros_partidos(year: int, download: bool = False) -> dict[str, int]:
    """Sigla normalizada -> número do partido, a partir de todos os candidatos do RJ."""
    df = read_filtered(_zip("consulta_cand", year, download), rf"_{year}_RJ\.csv$",
                       {"SG_PARTIDO": "sigla", "NR_PARTIDO": "numero"}).drop_duplicates()
    return {_norm_sigla(s): int(n) for s, n in zip(df.sigla, df.numero)}


def oficial_cargos(year: int, download: bool = False) -> pd.DataFrame:
    df = read_filtered(
        _zip("detalhe_votacao_munzona", year, download), rf"_{year}_RJ\.csv$",
        {"NR_TURNO": "turno", "CD_CARGO": "cd_cargo", "DS_CARGO": "cargo",
         "QT_COMPARECIMENTO": "comparecimento", "QT_VOTOS_BRANCOS": "brancos_oficial",
         "QT_TOTAL_VOTOS_NULOS": "nulos_oficial", "QT_VOTOS_NULOS_TECNICOS": "nulos_tecnicos_oficial"},
        filters=MUN,
    )
    num = ["turno", "cd_cargo", "comparecimento", "brancos_oficial", "nulos_oficial", "nulos_tecnicos_oficial"]
    df[num] = df[num].astype(int)
    return df.groupby(["turno", "cd_cargo", "cargo"], as_index=False)[num[2:]].sum()


def tecnicos_por_cargo(fv: pd.DataFrame, oficial: pd.DataFrame,
                       partidos: dict[str, int] | None = None) -> pd.DataFrame:
    """Soma, por turno/cargo, os votos em votáveis que não estão na lista oficial.

    - candidato (sq_candidato > 0) ausente de votacao_candidato_munzona;
    - voto de legenda (2 dígitos, exceto 95/96) num partido sem nenhum candidato
      oficial naquele cargo e fora de qualquer federação que tenha candidatos.
      Numa federação, o voto de legenda em um partido sem candidato vale para a
      federação. Só vale para cargos proporcionais, em que o candidato tem mais
      de 2 dígitos; nos majoritários, o número do candidato tem 2 dígitos.
    """
    partidos = partidos or {}
    oficiais = set(oficial.sq_candidato)
    out = []
    for (turno, cargo), g in fv.groupby(["turno", "cd_cargo"]):
        sel = oficial[(oficial.turno == turno) & (oficial.cd_cargo == cargo)]
        nums = sel.numero_votavel
        prefixos = {str(n)[:2] for n in nums}
        for comp in sel.federacao.unique():
            for sigla in str(comp).split("/"):
                n = partidos.get(_norm_sigla(sigla))
                if n is not None:
                    prefixos.add(str(n))
        proporcional = bool(len(nums)) and nums.astype(str).str.len().min() > 2
        cand_fora = (g.sq_candidato > 0) & ~g.sq_candidato.isin(oficiais)
        leg = (g.sq_candidato <= 0) & (g.numero_votavel < 95)
        leg_fora = leg & ~g.numero_votavel.astype(str).isin(prefixos) if proporcional else False
        out.append({"turno": turno, "cd_cargo": cargo, "nulos_tecnicos": int(g.loc[cand_fora | leg_fora, "votos"].sum())})
    return pd.DataFrame(out)


def reconcile(year: int, download: bool = False) -> dict[str, pd.DataFrame]:
    fv = pd.read_parquet(PROCESSED_DIR / f"fact_votos_{year}.parquet")

    # 1. Por candidato
    sec = fv[fv.sq_candidato > 0].groupby(["turno", "cd_cargo", "sq_candidato"], as_index=False).votos.sum()
    of = oficial_candidatos(year, download)
    cand = of.merge(sec, on=["turno", "cd_cargo", "sq_candidato"], how="outer")
    cand[["votos", "votos_oficial"]] = cand[["votos", "votos_oficial"]].fillna(0).astype(int)
    cand["dif"] = cand.votos - cand.votos_oficial
    cand["fora_lista_oficial"] = ~cand.sq_candidato.isin(of.sq_candidato)
    cand_err = cand[(cand.dif != 0) & ~cand.fora_lista_oficial]

    # Votos em votáveis fora da lista oficial -> nulos técnicos
    tecnicos = tecnicos_por_cargo(fv, of, numeros_partidos(year, download))

    # 2 e 3. Por cargo
    tot = fv.groupby(["turno", "cd_cargo"], as_index=False).agg(
        votos=("votos", "sum"),
        brancos=("votos", lambda s: s[fv.loc[s.index, "numero_votavel"] == VOTO_BRANCO].sum()),
    )
    car = (oficial_cargos(year, download).merge(tot, on=["turno", "cd_cargo"], how="outer")
           .merge(tecnicos, on=["turno", "cd_cargo"], how="left").fillna({"nulos_tecnicos": 0}))
    car["nulos_tecnicos"] = car.nulos_tecnicos.astype(int)
    car["votos_por_eleitor"] = (car.votos / car.comparecimento).round().astype(int)
    car["dif_total"] = car.votos - car.comparecimento * car.votos_por_eleitor
    car["dif_brancos"] = car.brancos - car.brancos_oficial
    car["dif_tecnicos"] = car.nulos_tecnicos - car.nulos_tecnicos_oficial
    car_err = car[(car.dif_total != 0) | (car.dif_brancos != 0) | (car.dif_tecnicos != 0)
                  | ~car.votos_por_eleitor.isin([1, 2])]
    return {"candidatos": cand, "candidatos_erro": cand_err, "cargos": car, "cargos_erro": car_err}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--year", type=int, required=True)
    p.add_argument("--download", action="store_true")
    a = p.parse_args(argv)
    r = reconcile(a.year, a.download)
    print(f"== {a.year} por cargo")
    print(r["cargos"][["turno", "cargo", "comparecimento", "votos_por_eleitor", "votos", "dif_total",
                       "brancos", "brancos_oficial", "dif_brancos",
                       "nulos_tecnicos", "nulos_tecnicos_oficial", "dif_tecnicos"]].to_string(index=False))
    c = r["candidatos"]
    n = int((~c.fora_lista_oficial).sum())
    print(f"== {a.year} por candidato: {n - len(r['candidatos_erro'])}/{n} batem "
          f"(+{int(c.fora_lista_oficial.sum())} fora da lista oficial, contados como nulos técnicos)")
    if len(r["candidatos_erro"]) or len(r["cargos_erro"]):
        print("DIVERGÊNCIAS:")
        print(r["candidatos_erro"].to_string(index=False))
        print(r["cargos_erro"].to_string(index=False))
        return 1
    print("OK: reconciliação sem divergências")
    return 0


if __name__ == "__main__":
    sys.exit(main())
