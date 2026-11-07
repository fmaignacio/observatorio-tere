import pandas as pd

from eleitoral.ingest.reconcile import tecnicos_por_cargo
from eleitoral.transform.build_facts import tipo_voto


def _fv(rows):
    return pd.DataFrame(rows, columns=["turno", "cd_cargo", "numero_votavel", "sq_candidato", "votos"])


def test_tipo_voto():
    fv = _fv([
        (1, 13, 15015, 10, 5),   # nominal apto
        (1, 13, 15999, 11, 3),   # candidato inapto
        (1, 13, 15, -1, 2),      # legenda
        (1, 13, 95, -3, 1),      # branco
        (1, 13, 96, -3, 1),      # nulo
    ])
    t = tipo_voto(fv, pd.DataFrame({"sq_candidato": [10]}))
    assert t.tolist() == ["nominal", "nulo_tecnico", "legenda", "branco", "nulo"]


def test_tecnicos_considera_federacao():
    oficial = pd.DataFrame({
        "turno": [1, 1], "cd_cargo": [13, 13], "sq_candidato": [10, 20],
        "numero_votavel": [23001, 13001],
        "federacao": ["CIDADANIA / PSDB", "PC do B / PT / PV"],
    })
    partidos = {"CIDADANIA": 23, "PSDB": 45, "PCDOB": 65, "PT": 13, "PV": 43, "PSOL": 50}
    fv = _fv([
        (1, 13, 23001, 10, 100),
        (1, 13, 45, -1, 7),      # PSDB sem candidato, mas na federação -> válido
        (1, 13, 65, -1, 2),      # PCdoB idem
        (1, 13, 50, -1, 4),      # PSOL sem candidato e fora de federação -> técnico
        (1, 13, 99001, 99, 3),   # candidato fora da lista -> técnico
    ])
    r = tecnicos_por_cargo(fv, oficial, partidos)
    assert r.nulos_tecnicos.tolist() == [7]


def test_legenda_nao_conta_em_majoritario():
    oficial = pd.DataFrame({"turno": [1], "cd_cargo": [11], "sq_candidato": [10],
                            "numero_votavel": [22], "federacao": ["#NULO"]})
    fv = _fv([(1, 11, 22, 10, 50)])
    assert tecnicos_por_cargo(fv, oficial).nulos_tecnicos.tolist() == [0]
