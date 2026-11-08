# Observatório Teresópolis — Projeto Integrado

## 1. Objetivo

Reunir em uma única plataforma as informações sobre a atuação política em
Teresópolis: o que a Câmara faz (V1), como a cidade vota (V2) e as evidências
documentais que sustentam as análises (V3). Assim, é possível cruzar a produção
legislativa de cada vereador com sua base eleitoral por seção e território.

## 2. Verticais

### V1 — Legislativo (existente)
- **Fontes:** transcrições das sessões no YouTube, Diário Oficial (PDFs em `diario_oficial/`).
- **Produto:** base de PLs com autor, status, votos e presentes (`csv/base_observatorio_teresopolis_COM_EMENTAS.csv`), além do dashboard Streamlit (`app.py`).
- **Pendências:** padronizar nomes de vereadores para que possam ser ligados a `dim_candidato` da V2.

### V2 — Eleitoral (a implementar)
- **Fonte:** Portal de Dados Abertos do TSE.

| Ano | Arquivo | Linhas de Teresópolis | Seções | Cargos |
|---|---|---|---|---|
| 2022 | `votacao_secao_2022_RJ.zip` | 65.347 | 374 | Gov., Senador, Dep. Fed./Est. |
| 2024 | `votacao_secao_2024_RJ.zip` | 43.248 | 400 | Prefeito, Vereador |
| 2026 | `votacao_secao_2026_RJ.zip` | 69.849 | 422 | Gov., Senador (2 vagas), Dep. Fed./Est. |

Cabeçalho idêntico nos três anos (validado em 2026-11-07). Ingestão implementada em `eleitoral/ingest/tse.py`.

- **Pipeline:** `ingest` (download + validação de cabeçalho + filtro Teresópolis + rename) → `transform` (dimensões e fatos) → `analysis`.
- **Análises previstas:**
  - *Swing:* variação de votos por seção/local entre eleições.
  - *Transição:* matriz de transição de votos 2024 × 2026.
  - *Clusters:* agrupamento de seções por comportamento eleitoral e perfil do eleitorado.

### V3 — Evidências (protótipo)
- **Objetivo:** catalogar relatos de perseguição, intimidação, assédio ou coação política contra pessoas de esquerda e eleitores do Lula em Teresópolis, sempre com fonte verificável.
- **Coleta** (`python -m evidencias.coletar`): Google Notícias, GDELT, Bluesky e YouTube, com termos que combinam o município e um tipo de ocorrência.
- **Fila privada de revisão:** SQLite fora do Git. Uma pessoa classifica cada item como caso confirmado, notícia de contexto ou descarte, com tipo de caso e nota.
- **Catálogo** (`evidencias/catalogo.csv`): só itens revisados. Posts de rede social saem sem texto nem perfil.
- **Primeira coleta (2026-11-07):** 70 itens. Entre os relevantes estão o boicote a comércios após a eleição de 2026, as notas de repúdio da OAB, da Prefeitura, do Sincomércio e do PT, e a operação da PF sobre ameaças à deputada Talíria Petrone.
- **Próximos passos:** formulário de denúncia, extração do texto completo das matérias, ligação com discursos na Câmara (V1) e acesso ao Meta Content Library via parceria acadêmica.

## 3. Modelo de dados

```
dim_local_votacao ─┐
dim_secao ─────────┼── fact_votos ── dim_candidato ── (V1) vereadores/PLs
                   └── fact_perfil_secao
```

| Tabela | Grão | Chave |
|---|---|---|
| `dim_local_votacao` | local de votação por ano | `(ano, zona, nr_local)` |
| `dim_secao` | seção por ano | `(ano, zona, secao)` |
| `dim_candidato` | candidato por ano/cargo | `(ano, cargo, numero_candidato)` |
| `fact_votos` | seção × votável × turno × cargo | composta |
| `fact_perfil_secao` | seção × categoria de perfil | composta |

## 4. Plano de ingestão (V2)

```
python -m eleitoral.ingest.tse --year 2022 [--download] [--filter-only]
```

1. **Download** (opcional): baixa o ZIP do CDN do TSE para `data/raw/` e extrai o CSV do RJ.
2. **Validação de cabeçalho:** compara a primeira linha com `COLUMN_MAPS[ano]` e falha se houver colunas faltando ou novas.
3. **Filtro:** mantém só Teresópolis (por `CD_MUNICIPIO`, conferindo `NM_MUNICIPIO`).
4. **Rename:** aplica o mapeamento explícito do ano.
5. **Reconciliação:** soma os votos por candidato/cargo/turno e compara com o resultado oficial. Qualquer discrepância é registrada no log e faz o processo falhar.
6. **Saída:** `data/processed/fact_votos_<ano>.parquet`, com os tipos validados.

### Resultado da reconciliação (2026-11-07)

Bate exatamente nos três anos: votos por candidato, comparecimento, brancos e nulos técnicos por cargo.

| Ano | Candidatos que batem | Inaptos (nulos técnicos) | Comparecimento |
|---|---|---|---|
| 2022 | 2603/2603 | 29 | 99.860 |
| 2024 | 374/374 | 1 | 98.777 |
| 2026 | 1923/1923 | 5 | 103.188 |

### Tabelas geradas

| Tabela | Linhas (22/24/26) |
|---|---|
| `dim_local_votacao` | 80 / 79 / 80 |
| `dim_secao` | 414 / 432 / 442 |
| `dim_candidato` | 1623 / 374 / 1189 (só candidatos com voto em Teresópolis) |
| `fact_votos` | 65.347 / 43.248 / 69.849 |
| `fact_perfil_secao` | eleitorado: 129.040 / 132.969 / 133.424 |

## 5. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Formato muda entre anos (já ocorreu em `perfil_eleitor_secao` e `eleitorado_local_votacao` em 2026) | Mapeamento explícito por ano; o leitor falha se faltar coluna |
| Encoding latin-1 × utf-8 | Leitura sempre com `encoding='latin-1'` |
| Arquivos muito grandes (até 2 GB descompactados) | Leitura em chunks direto do ZIP, com filtro de município |
| Download truncado sem erro | Retomada com HTTP Range e validação do ZIP |
| Discrepância com o oficial | Reconciliação obrigatória; o pipeline aborta |
| Inferência ecológica pouco identificada | Resultado tratado como indicativo; unidades = locais comuns |
| Nomes de vereadores divergentes entre V1 e V2 | Tabela de de-para revisada manualmente |

## 6. Próximos passos

1. ~~Baixar os dados e validar os cabeçalhos~~ (feito).
2. ~~Ingestão e reconciliação com o resultado oficial~~ (feito: bate 100%).
3. ~~Dimensões, fatos e análises (swing, transição, clusters)~~ (feito).
4. Ligar os vereadores da V1 a `dim_candidato` (de-para de nomes).
5. Integrar a V2 ao dashboard Streamlit (mapa por local, swing, transição, clusters).
