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
├── ingest/      # tse.py (CLI), download.py, column_mappings.py
├── transform/   # build_dims.py, build_facts.py
└── analysis/    # swing.py, transition.py, clusters.py
data/raw/        # gitignored
data/processed/  # parquets
tests/eleitoral/
```

CLI: `python -m eleitoral.ingest.tse --year 2022 [--download] [--filter-only]`

## Pontos de atenção do TSE

- Fonte: `https://cdn.tse.jus.br/estatistica/sead/odsele/votacao_secao/votacao_secao_<ano>_RJ.zip`, que contém um CSV e o `leiame.pdf`.
- **Validado em 2026-11-07:** 2022, 2024 e 2026 têm o mesmo cabeçalho de 26 colunas (o candidato vem em `NR_VOTAVEL`). Mesmo assim, o mapeamento fica explícito por ano em `column_mappings.py`, e qualquer divergência ou ano sem mapeamento faz o script falhar.
- Teresópolis tem `CD_MUNICIPIO = 59153` (código TSE, não IBGE). O filtro é feito por esse código, e o nome serve apenas como checagem.
- O arquivo estadual não traz Presidente. Votos brancos e nulos aparecem como `NR_VOTAVEL` 95 e 96.
- Em 2026, o Senador soma o dobro de votos dos outros cargos, porque foram 2 vagas.
- Os downloads grandes podem chegar truncados: confira com `unzip -t` e retome com `curl -C -`.

## Comandos

- App V1: `streamlit run app.py`
- Testes: `pytest tests/`
