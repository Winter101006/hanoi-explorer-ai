# Hanoi Explorer AI baseline

Executed pytest cases: 187

| Group | Passed | Failed | Skipped |
|---|---:|---:|---:|
| AR | 15 | 0 | 0 |
| CM | 20 | 0 | 0 |
| CR | 25 | 0 | 0 |
| GG | 12 | 0 | 3 |
| QU | 25 | 0 | 0 |
| RT | 19 | 0 | 1 |
| legacy | 67 | 0 | 0 |

## Priority failures

P0: 0, P1: 0, P2: 0

## Metrics

```json
{
  "intent_accuracy": 1.0,
  "entity_accuracy": 1.0,
  "exact_target_search_at_5": {
    "precision": 0.20000000000000004,
    "precision_labelled": 12,
    "recall": 1.0,
    "recall_labelled": 12,
    "ndcg": 0.9692441461309548,
    "ndcg_labelled": 12
  },
  "constraint_violation_rate": 0.0,
  "no_match_correctness": 1.0,
  "generation_human_review": {
    "labelled_answers": 0,
    "labelled_claims": 0,
    "groundedness": null,
    "hallucination_rate": null,
    "answer_relevance": null,
    "naturalness": null
  }
}
```

## Failures and skips

- **GG-13** (P1) skipped · setup · Skipped: Opt-in live Gemini evaluation
- **GG-14** (P1) skipped · setup · Skipped: Opt-in live Gemini evaluation
- **GG-15** (P1) skipped · setup · Skipped: Opt-in live Gemini evaluation
- **RT-19** (P2) skipped · source_label · Skipped: Open-ended relevance judgments awaiting human review

Only named-target retrieval cases with complete target labels contribute to search metrics.
See [audit, dataset limits and repair priorities](../BASELINE.md) and [ground-truth review](../ground_truth_review.json).
