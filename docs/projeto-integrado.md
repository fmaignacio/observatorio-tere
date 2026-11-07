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

| Ano | Recurso | Pasta no ZIP |
|---|---|---|
| 2022 | RJ — Votação por seção eleitoral | `votacao_secao/` |
| 2024 | Detalhe da apuração por seção eleitoral | `detalhe_votacao_secao/` |
| 2026 | A publicar após a eleição | a definir |

- **Pipeline:** `ingest` (download + validação de cabeçalho + filtro Teresópolis + rename) → `transform` (dimensões e fatos) → `analysis`.
- **Análises previstas:**
  - *Swing:* variação de votos por seção/local entre eleições.
  - *Transição:* matriz de transição de votos 2024 × 2026.
  - *Clusters:* agrupamento de seções por comportamento eleitoral e perfil do eleitorado.

### V3 — Evidências (a definir)
- Repositório de documentos, prints e anexos que embasam as análises das V1 e V2.
- Material bruto ou sensível fica fora do Git (`evidencias/raw/`, `evidencias/privado/`). Só metadados e referências são versionados.

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

## 5. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Colunas mudam entre anos | Mapeamento explícito por ano e validação de cabeçalho |
| Encoding latin-1 × utf-8 | Leitura sempre com `encoding='latin-1'` |
| Arquivos muito grandes | Leitura em chunks com filtro de município na leitura |
| 2026 ainda não publicado | Script preparado, com mapeamento pendente |
| Discrepância com o oficial | Teste de reconciliação obrigatório |
| Nomes de vereadores divergentes entre V1 e V2 | Tabela de de-para revisada manualmente |

## 6. Próximos passos

1. Baixar uma amostra de 2022 e de 2024 e comparar os cabeçalhos reais (`head -1`).
2. Preencher `eleitoral/ingest/column_mappings.py` com as colunas validadas.
3. Implementar `tse.py` e o teste de reconciliação para 2022.
4. Construir as dimensões e os fatos e depois as análises.
5. Integrar a V2 ao dashboard Streamlit.
