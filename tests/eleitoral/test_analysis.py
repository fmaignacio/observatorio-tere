import numpy as np

from eleitoral.analysis.clusters import _faixa
from eleitoral.analysis.transition import estimar


def test_estimar_recupera_matriz_conhecida():
    rng = np.random.default_rng(0)
    T = np.array([[0.8, 0.1, 0.1], [0.2, 0.7, 0.1], [0.1, 0.1, 0.8]])
    X = rng.dirichlet([2, 2, 2], size=200)
    Y = X @ T
    est = estimar(X, Y, np.ones(len(X)))
    assert np.allclose(est, T, atol=1e-3)
    assert np.allclose(est.sum(axis=1), 1)
    assert (est >= -1e-9).all()


def test_faixa_etaria():
    assert _faixa("16 anos") == "idade_16_24"
    assert _faixa("21 a 24 anos") == "idade_16_24"
    assert _faixa("45 a 49 anos") == "idade_45_59"
    assert _faixa("100 anos ou mais") == "idade_60_mais"
    assert _faixa("Inválido") is None
