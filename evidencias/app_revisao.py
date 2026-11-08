"""Tela de revisão da fila da V3. Roda só localmente (a fila é privada).

Uso:
    streamlit run evidencias/app_revisao.py

Fica fora de pages/ de propósito, para não ir para o dashboard publicado.
A variável EVIDENCIAS_DB troca o arquivo da fila (usada nos testes).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

import streamlit as st  # noqa: E402

from evidencias import fila, revisar  # noqa: E402

DB = Path(os.environ.get("EVIDENCIAS_DB", fila.DB))
POR_PAGINA = 15
ROTULO_TIPO = {
    "ameaca": "Ameaça", "assedio_eleitoral": "Assédio eleitoral", "demissao_exoneracao": "Demissão/exoneração",
    "agressao": "Agressão", "processo": "Processo", "discurso_autoridade": "Discurso de autoridade", "outro": "Outro",
}

st.set_page_config(page_title="Revisão de evidências", layout="wide")
con = fila.conectar(DB)


def _marcar(id_: str, status: str) -> None:
    tipo = st.session_state.get(f"tipo_{id_}") if status == "confirmado" else None
    nota = (st.session_state.get(f"nota_{id_}") or "").strip() or None
    fila.marcar(con, id_, status, tipo, nota)
    st.session_state["aviso"] = f"Item {id_[:8]} marcado como {status}."


# --- barra lateral --------------------------------------------------------
contagem = dict(con.execute("SELECT status, COUNT(*) FROM achados GROUP BY status").fetchall())
st.sidebar.title("Revisão")
for s in fila.STATUS:
    st.sidebar.write(f"**{s}**: {contagem.get(s, 0)}")

status = st.sidebar.selectbox("Mostrar", fila.STATUS, key="f_status")
fontes = [r[0] for r in con.execute("SELECT DISTINCT fonte FROM achados ORDER BY fonte")]
fonte = st.sidebar.selectbox("Fonte", ["todas", *fontes], key="f_fonte")
busca = st.sidebar.text_input("Buscar no título", key="f_busca").strip()

st.sidebar.divider()
if st.sidebar.button("Exportar catálogo", type="primary", key="exportar"):
    n = revisar.exportar(con)
    st.sidebar.success(f"{n} itens em evidencias/catalogo.csv")
st.sidebar.caption("O catálogo leva imprensa (confirmado/noticia) e só o link dos posts confirmados, "
                   "sem texto nem perfil.")

# --- lista ----------------------------------------------------------------
q = "SELECT * FROM achados WHERE status=?"
args: list = [status]
if fonte != "todas":
    q += " AND fonte=?"
    args.append(fonte)
if busca:
    q += " AND (titulo LIKE ? OR trecho LIKE ?)"
    args += [f"%{busca}%"] * 2
rows = con.execute(q + " ORDER BY publicado_em DESC", args).fetchall()

st.title("Revisão de evidências — V3")
if aviso := st.session_state.pop("aviso", None):
    st.toast(aviso)

if not rows:
    st.info(f"Nenhum item com status '{status}'" + (" para esse filtro." if fonte != "todas" or busca else "."))
    st.stop()

paginas = (len(rows) - 1) // POR_PAGINA + 1
pagina = st.number_input(f"Página (de {paginas})", 1, paginas, 1, key=f"pag_{status}_{fonte}_{busca}") \
    if paginas > 1 else 1
st.caption(f"{len(rows)} itens · mostrando {POR_PAGINA * (pagina - 1) + 1}–{min(len(rows), POR_PAGINA * pagina)}")

for r in rows[POR_PAGINA * (pagina - 1): POR_PAGINA * pagina]:
    id_ = r["id"]
    with st.container(border=True):
        st.markdown(f"**{r['titulo'] or '(sem título)'}**")
        st.caption(f"{(r['publicado_em'] or '')[:10]} · {r['fonte']} · {r['veiculo']} · `{id_[:8]}`")
        if r["trecho"] and r["trecho"] != r["titulo"]:
            st.write(r["trecho"][:600])
        st.markdown(f"[Abrir fonte ↗]({r['url']})")
        if r["tipo_caso"] or r["nota"]:
            st.caption(f"Atual: {ROTULO_TIPO.get(r['tipo_caso'], '—')} · {r['nota'] or ''}")

        c1, c2 = st.columns([1, 2])
        tipos = list(ROTULO_TIPO)
        c1.selectbox("Tipo (para confirmar)", tipos, format_func=ROTULO_TIPO.get, key=f"tipo_{id_}",
                     index=tipos.index(r["tipo_caso"]) if r["tipo_caso"] in tipos else 0)
        c2.text_input("Nota (o que você conferiu)", value=r["nota"] or "", key=f"nota_{id_}")

        b = st.columns(4)
        acoes = [("confirmado", "Confirmar caso"), ("noticia", "Notícia/contexto"),
                 ("descartado", "Descartar"), ("pendente", "Voltar p/ pendente")]
        for col, (s, rot) in zip(b, acoes):
            if s != r["status"]:
                col.button(rot, key=f"{s}_{id_}", on_click=_marcar, args=(id_, s),
                           type="primary" if s == "confirmado" else "secondary")
