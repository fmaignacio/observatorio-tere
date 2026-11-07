"""Matriz de transição de votos entre duas eleições (inferência ecológica).

Uso:
    python -m eleitoral.analysis.transition --de 2024:11 --para 2026:3 [--top 4]

Estima T[i, j] = fração dos eleitores da opção i na eleição A que escolheram j
na eleição B. As opções incluem candidatos (os ``top`` mais votados), "Outros",
"Branco/Nulo" e "Abstenção". As unidades são os locais de votação comuns.

Método: regressão de Goodman com restrições (T >= 0, cada linha soma 1),
ponderada pelo eleitorado apto. É uma estimativa ecológica: mostra padrões
agregados, não o comportamento individual. Locais com perfil muito parecido
deixam a matriz pouco identificada, então leia como indicativo.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from eleitoral.analysis.common import LOCAL, PROCESSED_DIR, VALIDOS, aptos_por_local, load, rotulo, votos_eleicao


def votos_por_eleitor(ano: int, cd_cargo: int, turno: int = 1) -> int:
    fv = load("fact_votos")
    tot = fv[(fv.ano == ano) & (fv.turno == turno)].groupby("cd_cargo").votos.sum()
    return int(round(tot[cd_cargo] / tot.min()))


def opcoes(ano: int, cd_cargo: int, top: int, por: str = "candidato", turno: int = 1) -> pd.DataFrame:
    """Proporção do eleitorado apto de cada local em cada opção (linhas somam 1)."""
    v = votos_eleicao(ano, cd_cargo, turno).copy()
    v["grupo"] = rotulo(v, por)
    validos = v.tipo_voto.isin(VALIDOS)
    principais = v[validos].groupby("grupo").votos.sum().nlargest(top).index
    v.loc[validos & ~v.grupo.isin(principais), "grupo"] = "Outros"
    v.loc[~validos, "grupo"] = "Branco/Nulo"
    tab = v.pivot_table(index=LOCAL, columns="grupo", values="votos", aggfunc="sum", fill_value=0)
    # Cargos com 2 vagas (Senador em 2026): cada eleitor dá 2 votos. Divide pelo
    # nº de votos por eleitor, usando como base o comparecimento (igual em todos os cargos do ano).
    k = votos_por_eleitor(ano, cd_cargo, turno)
    tab = tab / k
    aptos = aptos_por_local(ano).reindex(tab.index)
    tab["Abstenção"] = (aptos - tab.sum(axis=1)).clip(lower=0)
    ordem = [*principais, "Outros", "Branco/Nulo", "Abstenção"]
    tab = tab[[c for c in ordem if c in tab.columns]]
    return tab.div(tab.sum(axis=1), axis=0).assign(_peso=aptos)


def estimar(X: np.ndarray, Y: np.ndarray, w: np.ndarray) -> np.ndarray:
    p, q = X.shape[1], Y.shape[1]
    sw = np.sqrt(w / w.sum())[:, None]
    Xw, Yw = X * sw, Y * sw

    def f(t):
        r = Xw @ t.reshape(p, q) - Yw
        return (r * r).sum()

    def g(t):
        return (2 * Xw.T @ (Xw @ t.reshape(p, q) - Yw)).ravel()

    cons = [{"type": "eq", "fun": lambda t, i=i: t.reshape(p, q)[i].sum() - 1} for i in range(p)]
    t0 = np.tile(Y.mean(axis=0), (p, 1)).ravel()
    res = minimize(f, t0, jac=g, bounds=[(0, 1)] * (p * q), constraints=cons, method="SLSQP",
                   options={"maxiter": 1000, "ftol": 1e-12})
    if not res.success:
        raise RuntimeError(f"Otimização não convergiu: {res.message}")
    return res.x.reshape(p, q)


def transicao(de: tuple[int, int], para: tuple[int, int], top: int = 4, por: str = "candidato") -> pd.DataFrame:
    A = opcoes(*de, top=top, por=por)
    B = opcoes(*para, top=top, por=por)
    idx = A.index.intersection(B.index)
    A, B = A.loc[idx], B.loc[idx]
    w = ((A.pop("_peso") + B.pop("_peso")) / 2).to_numpy(float)
    T = estimar(A.to_numpy(float), B.to_numpy(float), w)
    return pd.DataFrame(T, index=pd.Index(A.columns, name=f"{de[0]}"), columns=pd.Index(B.columns, name=f"{para[0]}"))


def _par(s: str) -> tuple[int, int]:
    a, c = s.split(":")
    return int(a), int(c)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--de", type=_par, default=(2024, 11))
    p.add_argument("--para", type=_par, default=(2026, 3))
    p.add_argument("--top", type=int, default=4)
    p.add_argument("--por", choices=["partido", "candidato"], default="candidato")
    a = p.parse_args(argv)
    T = transicao(a.de, a.para, a.top, a.por)
    out = PROCESSED_DIR / f"analysis_transicao_{a.de[0]}c{a.de[1]}_{a.para[0]}c{a.para[1]}.parquet"
    T.reset_index().to_parquet(out, index=False)
    with pd.option_context("display.width", 200, "display.max_columns", 20):
        print("Linhas: origem; colunas: destino (% dos eleitores da origem)")
        print((100 * T).round(0).astype(int).to_string())
    print(f"\nSalvo em {out}")


if __name__ == "__main__":
    main()
