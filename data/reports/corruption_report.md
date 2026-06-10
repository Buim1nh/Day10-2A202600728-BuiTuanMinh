# Data Corruption & Pipeline Repair Comparison Report

This report compares the performance and data quality metrics across three phases of the RAG pipeline:
1. **Baseline**: Clean, fresh dataset fetched directly from the source.
2. **Corrupted**: Simulated data quality issues (deleted rows, blank/noisy fields, backdated timestamps, duplicate rows).
3. **Repaired**: Re-fetched and re-cleaned dataset using the ingestion logic.

## 1. RAG Performance Comparison

| Metric | Baseline | Corrupted | Repaired | Impact (Corrupted vs Baseline) |
| :--- | :---: | :---: | :---: | :---: |
| **Total Samples** | 24 | 24 | 24 | - |
| **Retrieval Hit Rate** | 100.00% | 16.67% | 100.00% | -83.33% |
| **Mean Token F1** | 55.07% | 8.85% | 55.07% | -46.22% |
| **Judge Accuracy** | 50.00% | 8.33% | 50.00% | -41.67% |
| **Mean Judge Score** | 3.00 | 1.33 | 3.00 | -1.67 |

## 2. Data Quality & Freshness Comparison

| Metric | Baseline | Corrupted | Repaired |
| :--- | :---: | :---: | :---: |
| **Row Count** | 6 | 20 | 23 |
| **Quality Check Status** | `True` | `False` | `True` |
| **Stale Count (Age Check)** | 0 | 2 | 0 |
| **Short Summary Count** | 0 | 2 | 0 |
| **Null/Empty Titles** | 0 | 0 | 0 |
| **Freshness Status** | `Fresh` | `Stale` | `Fresh` |

## 3. Analysis and Impact Discussion

### Impact of Data Corruption on RAG Performance
- **Loss of Context**: Deleting the latest papers directly impacts retrieval hit rate because the agent cannot retrieve papers that no longer exist in the vector store.
- **Degraded Semantic Search**: Blank summaries, title truncations, and noise injection corrupt the semantic embeddings, leading to incorrect top-k retrieval matches.
- **Erroneous QA Output**: When the retrieved context contains noise or is missing critical info (e.g. blank summaries), the LLM agent fails to answer correctly, dropping the Mean Token F1 and Judge Score.
- **Staleness**: Backdating publication dates violates freshness constraints and causes the freshness monitor to trigger alerts.

### Repair Strategy & Recovery
- **Re-ingestion & Re-cleaning**: Fetching a clean snapshot from the Crossref raw data snapshot (or API) and running the cleaning pipeline successfully restored all missing, corrupted, and stale fields.
- **Index Reconstruction**: Rebuilding the ChromaDB index using the repaired dataset restores retrieval and generation metrics to their baseline levels.
