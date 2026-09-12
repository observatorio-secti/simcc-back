# Scripts do Módulo MarIA (Busca Semântica e IA)

Esta pasta agrupa todos os scripts operacionais e de testes para o pipeline de dados vetoriais (`pgvector`) da **MarIA**:

---

## 📁 Estrutura de Scripts

| Script | Finalidade | Principais Argumentos |
|---|---|---|
| [`ingest_researchers.py`](file:///home/jaspion/Observatorio/Simcc/simcc-back/scripts/maria/ingest_researchers.py) | Lê pesquisadores e afiliações da base, gera texto consolidado e embeddings via OpenAI, salvando em `search_document_researcher`. | `--batch-size`, `--limit`, `--reindex` |
| [`ingest_productions.py`](file:///home/jaspion/Observatorio/Simcc/simcc-back/scripts/maria/ingest_productions.py) | Lê produções científicas (artigos, livros, capítulos, relatórios, softwares, patentes), gera texto e embeddings via OpenAI, salvando em `search_document_production`. | `--types`, `--batch-size`, `--limit`, `--reindex` |
| [`extract_golden_sample.py`](file:///home/jaspion/Observatorio/Simcc/simcc-back/scripts/maria/extract_golden_sample.py) | Extrai uma amostra equilibrada da base real (30 pesquisadores + 30 de cada tipo de produção) mantendo integridade referencial, gerando JSON/GZ, SHA-256 e catálogo de inspeção. | `--db-url`, `--output-dir` |
| [`seed_golden_sample.py`](file:///home/jaspion/Observatorio/Simcc/simcc-back/scripts/maria/seed_golden_sample.py) | Anexa/popula a amostra assinada em qualquer banco PostgreSQL com pgvector (ex: banco local ou testcontainers nos testes automatizados). | `--db-url`, `--fixture-path` |

---

## 🚀 Como Usar

### 1. Ingestão e Indexação Vetorial da Base (Gera Embeddings)
Popula os documentos vetoriais da MarIA consultando a OpenAI:

```bash
# Indexar pesquisadores (lote de 25, ou limitando para teste)
poetry run python scripts/maria/ingest_researchers.py --limit 50

# Indexar produções de tipos específicos ou todos
poetry run python scripts/maria/ingest_productions.py --types ARTICLE,BOOK --batch-size 25
```

### 2. Extração da Amostra de Testes (Golden Dataset)
Extrai os registros com embeddings já calculados da sua base local para fixtures versionáveis:

```bash
poetry run python scripts/maria/extract_golden_sample.py
```
*Arquivos gerados em `tests/fixtures/golden_dataset/`:*
- `sample_data.json` / `sample_data.json.gz`: Base completa com chaves estrangeiras e vetores.
- `sample_data.sha256`: Hash de integridade.
- `CATALOG.md`: Catálogo human-readable com títulos, autores, instituições e prévias para elaboração de consultas de avaliação.

### 3. Popular/Anexar a Amostra no Banco
Anexa a amostra extraída em qualquer banco de dados de desenvolvimento ou CI:

```bash
# No banco padrão ou fornecendo uma connection string
poetry run python scripts/maria/seed_golden_sample.py --db-url "postgresql+asyncpg://postgres:postgres@localhost:5433/simcc"
```
