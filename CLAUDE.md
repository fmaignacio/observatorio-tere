# Observatório Teresópolis — Regras do Projeto

Plataforma de dados públicos sobre a política de Teresópolis (RJ). Ela é
organizada em **verticais**, que compartilham convenções e um modelo de dados
comum. A especificação completa está em `docs/projeto-integrado.md`.

## Verticais

| Vertical | Tema | Situação | Onde fica |
|---|---|---|---|
| **V1 — Legislativo** | Sessões da Câmara, PLs, autores, votações e presença (transcrições + Diário Oficial) | Em produção (Streamlit) | `app.py`, `*.ipynb`, `csv/`, `diario_oficial/` |
| **V2 — Eleitoral** | Votação por seção do TSE (2022, 2024, 2026) para Teresópolis | Planejada | `eleitoral/` |
| **V3 — Evidências** | Documentos e evidências que dão suporte às análises | Planejada | `evidencias/` |

## Regras gerais

- **Idioma:** código, nomes de colunas e docs em português. Colunas em `snake_case`, sem acento.
- **Reprodutibilidade:** todo dado processado precisa ser gerado por script/CLI versionado. Nada de editar CSV/Parquet à mão.
- **Dados brutos não vão para o Git** (`data/raw/`, ZIPs do TSE, evidências privadas). Veja `.gitignore`.
- **Validar antes de transformar:** cabeçalhos e tipos são checados explicitamente. Quando o schema não bate, o script deve falhar com uma mensagem clara.
- **Reconciliação obrigatória:** totais agregados da V2 têm de bater com o resultado oficial do TSE para o município.
- **Encoding:** CSVs do TSE são lidos com `sep=';'` e `encoding='latin-1'`.
- **Saída padrão:** Parquet em `data/processed/` (pyarrow).

## Modelo de dados (V2)

Esquema estrela, com granularidade de **seção eleitoral × candidato × turno × cargo**.

**Dimensões**
- `dim_local_votacao`: zona, local de votação, endereço, bairro, coordenadas
- `dim_secao`: zona, seção, local de votação, eleitorado apto
- `dim_candidato`: ano, cargo, número, nome de urna, partido, coligação

**Fatos**
- `fact_votos`: ano, turno, cargo, zona, seção, número do votável, votos
- `fact_perfil_secao`: perfil do eleitorado por seção (gênero, faixa etária, escolaridade)

Chaves naturais: `(ano, zona, secao)` para seção e `(ano, cargo, numero_candidato)` para candidato.

## Estrutura da V2

```
eleitoral/
├── pipeline.py  # roda tudo: download → ingestão → reconciliação → dims → fatos
├── ingest/      # download.py, reader.py, column_mappings.py, tse.py, reconcile.py
├── transform/   # build_dims.py, build_facts.py
└── analysis/    # common.py, swing.py, transition.py, clusters.py
data/raw/        # gitignored (~2,7 GB de ZIPs do TSE)
data/processed/  # parquets (gitignored, regeneráveis)
tests/eleitoral/
```

Conjuntos do TSE usados: `votacao_secao` (fato), `votacao_candidato_munzona` e
`detalhe_votacao_munzona` (reconciliação), `consulta_cand` (candidatos),
`eleitorado_local_votacao` (locais/seções), `perfil_eleitor_secao` (perfil).

### Regras de negócio que não são óbvias

- **A reconciliação precisa bater exatamente** (`eleitoral.ingest.reconcile`): votos por candidato, comparecimento, brancos e nulos técnicos por cargo. Se não bater, o pipeline aborta.
- **Nulo técnico:** votos em candidato inapto (ausente de `votacao_candidato_munzona`) ou em legenda de partido sem candidato no cargo **e fora de federação com candidatos**. Em federação, a legenda de um partido sem candidato vale para a federação.
- **Apto:** use a presença em `votacao_candidato_munzona`. O campo `DS_SITUACAO_CANDIDATURA` do `consulta_cand` vem `#NE` para todos em 2024 e 2026.
- **Seções agregadas** não têm voto próprio: os votos aparecem na `secao_principal` (`dim_secao.secao_apuracao`).
- **Comparação entre anos é feita por local** (`zona`, `nr_local`). A numeração das seções muda, e o nome do local muda de grafia ("E.E." → "E.M."), mas o código é estável (79 de 81 locais existem nos três anos).
- **PII:** CPF, e-mail e título de eleitor dos candidatos são descartados na leitura.
- A matriz de transição é **inferência ecológica**: serve como indicativo, não como comportamento individual.

## Pontos de atenção do TSE

- Fonte: `https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_<ano>_RJ.zip`, que contém um CSV e o `leiame.pdf`.
- **Validado em 2026-11-07:** 2022, 2024 e 2026 têm o mesmo cabeçalho de 26 colunas (o candidato vem em `NR_VOTAVEL`). Mesmo assim, o mapeamento fica explícito por ano em `column_mappings.py`, e qualquer divergência ou ano sem mapeamento faz o script falhar.
- Teresópolis tem `CD_MUNICIPIO = 59153` (código TSE, não IBGE). O filtro é feito por esse código, e o nome serve apenas como checagem.
- O arquivo estadual não traz Presidente. Votos brancos e nulos aparecem como `NR_VOTAVEL` 95 e 96.
- Em 2026, o Senador soma o dobro de votos dos outros cargos, porque foram 2 vagas.
- Os downloads grandes podem chegar truncados sem erro. O `download.py` retoma o download e valida o ZIP.
- Os formatos que mudam entre anos (por isso o mapeamento é explícito por ano):
  - `perfil_eleitor_secao` 2026: `ANO_ELEICAO` → `AA_ELEICAO`, `QT_ELEITORES_PERFIL` → `QT_ELEITORES`;
  - `eleitorado_local_votacao` 2026: passou a ter um CSV por UF dentro do ZIP;
  - as coordenadas vêm com vírgula decimal em alguns anos.

## Comandos

- App V1: `streamlit run app.py`
- Dependências das análises e dos testes: `pip install -r requirements-dev.txt`
- Pipeline V2 completo: `python -m eleitoral.pipeline`
- Reconciliação de um ano: `python -m eleitoral.ingest.reconcile --year 2026`
- Análises:
  - `python -m eleitoral.analysis.swing --de 2022:3 --para 2026:3` (`ano:cd_cargo`)
  - `python -m eleitoral.analysis.transition --de 2024:11 --para 2026:3`
  - `python -m eleitoral.analysis.clusters --ano 2026 --cargo 3`
- Códigos de cargo: 3 Governador, 5 Senador, 6 Dep. Federal, 7 Dep. Estadual, 11 Prefeito, 13 Vereador.
- Testes: `pytest tests/`
