# Phase 1: Baseline RAG Pipeline Report

## 1. Ingestion Summary
- **Source API**: Crossref REST API
- **Query**: `agentic retrieval augmented generation large language model`
- **Max Results**: 24
- **Ingested Records**: 24

## 2. Evaluation Metrics
- **Total Evaluation Samples**: 24
- **Retrieval Hit Rate**: 100.00%
- **Mean Token F1**: 55.07%
- **Judge Accuracy**: 50.00%
- **Mean Judge Score**: 3.00 / 5.0

### Ragas Sub-metrics
```json
{
  "skipped": "Set RUN_RAGAS=1 to enable the slower Ragas pass."
}
```

## 3. Data Quality & Freshness
- **Quality Check Success**: `True`
- **Total Rows**: 23
- **Null/Empty Paper IDs**: 0
- **Null/Empty Titles**: 0
- **Short Summaries**: 0
- **Stale Count**: 0
- **Latest Published Date**: 2026-06-02
- **Oldest Published Date**: 2025-12-19
- **Freshness Status**: `Fresh`
