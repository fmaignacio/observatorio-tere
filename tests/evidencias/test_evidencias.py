import csv

from evidencias import fila, revisar
from evidencias.base import Achado
from evidencias.fontes import bluesky, gdelt, google_news, youtube

RSS = """<?xml version="1.0"?><rss><channel>
<item><title>Boicote a comércio em Teresópolis - Jornal X</title><link>https://news.example/a</link>
<pubDate>Tue, 28 Oct 2026 12:00:00 GMT</pubDate><source url="https://x">Jornal X</source></item>
</channel></rss>"""


def test_google_news_parse():
    (a,) = google_news.parse(RSS, "q")
    assert a.titulo == "Boicote a comércio em Teresópolis"
    assert a.veiculo == "Jornal X"
    assert a.publicado_em.startswith("2026-10-28T12:00:00")
    assert a.tipo_fonte == "imprensa"


def test_gdelt_parse():
    (a,) = gdelt.parse({"articles": [{"url": "https://n/1", "title": "T", "seendate": "20261028T120000Z",
                                      "domain": "n.com"}]}, "q")
    assert a.publicado_em == "2026-10-28T12:00:00+00:00" and a.veiculo == "n.com"


def test_bluesky_filtra_municipio_e_monta_url():
    payload = {"posts": [
        {"uri": "at://did:plc:x/app.bsky.feed.post/abc", "author": {"handle": "fulano.bsky.social"},
         "record": {"text": "Ameaça em Teresópolis", "createdAt": "2026-11-01T00:00:00Z"}},
        {"uri": "at://did:plc:y/app.bsky.feed.post/def", "author": {"handle": "b"},
         "record": {"text": "Outro assunto"}},
    ]}
    (a,) = bluesky.parse(payload, "q")
    assert a.url == "https://bsky.app/profile/fulano.bsky.social/post/abc"
    assert a.tipo_fonte == "rede_social"


def test_youtube_parse_ignora_nao_video():
    payload = {"items": [{"id": {"videoId": "v1"}, "snippet": {"title": "T", "channelTitle": "C"}},
                         {"id": {"channelId": "c1"}, "snippet": {}}]}
    (a,) = youtube.parse(payload, "q")
    assert a.url.endswith("v1")


def test_fila_deduplica_e_exporta_sem_dados_pessoais(tmp_path):
    con = fila.conectar(tmp_path / "f.sqlite")
    imp = Achado(fonte="google_news", url="https://n/1", titulo="Notícia")
    rede = Achado(fonte="bluesky", url="https://bsky.app/profile/fulano/post/1", titulo="texto pessoal",
                  trecho="texto pessoal", veiculo="fulano", tipo_fonte="rede_social")
    rede2 = Achado(fonte="bluesky", url="https://bsky.app/profile/beltrano/post/2", titulo="t", veiculo="beltrano",
                   tipo_fonte="rede_social")
    assert fila.inserir(con, [imp, rede, rede2]) == 3
    assert fila.inserir(con, [imp]) == 0
    fila.marcar(con, imp.id, "noticia")
    fila.marcar(con, rede.id, "confirmado", tipo_caso="ameaca")
    fila.marcar(con, rede2.id, "noticia")  # rede social como "noticia" não é exportada
    out = tmp_path / "c.csv"
    assert revisar.exportar(con, out) == 2
    rows = list(csv.DictReader(open(out, encoding="utf-8")))
    social = next(r for r in rows if r["fonte"] == "bluesky")
    assert social["veiculo"] == "bluesky" and "pessoal" not in social["titulo"] and "fulano" not in social["veiculo"]
    assert "beltrano" not in open(out, encoding="utf-8").read()
