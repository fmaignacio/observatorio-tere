import zipfile

import pytest

from eleitoral.ingest import tse
from eleitoral.ingest.column_mappings import HEADER_V1


def _row(municipio_cd, municipio_nm, secao, votavel, votos):
    vals = {
        "DT_GERACAO": "01/11/2022", "HH_GERACAO": "16:05:25", "ANO_ELEICAO": "2022",
        "CD_TIPO_ELEICAO": "2", "NM_TIPO_ELEICAO": "Eleição Ordinária", "NR_TURNO": "1",
        "CD_ELEICAO": "546", "DS_ELEICAO": "Eleições Gerais Estaduais 2022",
        "DT_ELEICAO": "02/10/2022", "TP_ABRANGENCIA": "E", "SG_UF": "RJ", "SG_UE": "RJ",
        "NM_UE": "RIO DE JANEIRO", "CD_MUNICIPIO": str(municipio_cd),
        "NM_MUNICIPIO": municipio_nm, "NR_ZONA": "195", "NR_SECAO": str(secao),
        "CD_CARGO": "3", "DS_CARGO": "Governador", "NR_VOTAVEL": str(votavel),
        "NM_VOTAVEL": "FULANO", "QT_VOTOS": str(votos), "NR_LOCAL_VOTACAO": "1015",
        "SQ_CANDIDATO": "190001600001", "NM_LOCAL_VOTACAO": "ESCOLA X",
        "DS_LOCAL_VOTACAO_ENDERECO": "RUA Y, 1",
    }
    return ";".join(f'"{vals[c]}"' for c in HEADER_V1)


def _make_zip(tmp_path, rows, header=HEADER_V1):
    content = "\n".join([";".join(f'"{c}"' for c in header), *rows]) + "\n"
    path = tmp_path / "votacao_secao_2022_RJ.zip"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("votacao_secao_2022_RJ.csv", content.encode("latin-1"))
        zf.writestr("leiame.pdf", b"x")
    return path


def test_filtra_teresopolis_e_renomeia(tmp_path):
    z = _make_zip(tmp_path, [
        _row(59153, "TERESÓPOLIS", 1, 22, 10),
        _row(59153, "TERESÓPOLIS", 1, 95, 2),
        _row(58041, "BELFORD ROXO", 1, 22, 99),
    ])
    df = tse.read_teresopolis(z, 2022)
    tse.check(df, 2022)
    assert len(df) == 2
    assert df["votos"].sum() == 12
    assert {"zona", "secao", "numero_votavel", "votos"} <= set(df.columns)
    assert df["municipio"].unique().tolist() == ["TERESÓPOLIS"]


def test_cabecalho_diferente_falha(tmp_path):
    header = [c if c != "NR_VOTAVEL" else "NR_CANDIDATO" for c in HEADER_V1]
    z = _make_zip(tmp_path, [], header=header)
    with pytest.raises(tse.SchemaError, match="NR_VOTAVEL"):
        tse.read_teresopolis(z, 2022)


def test_ano_sem_mapeamento_falha():
    with pytest.raises(tse.SchemaError, match="sem mapeamento"):
        tse.validate_header(HEADER_V1, 2030)


def test_duplicata_falha(tmp_path):
    r = _row(59153, "TERESÓPOLIS", 1, 22, 10)
    df = tse.read_teresopolis(_make_zip(tmp_path, [r, r]), 2022)
    with pytest.raises(tse.SchemaError, match="duplicadas"):
        tse.check(df, 2022)
