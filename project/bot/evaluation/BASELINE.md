# Evaluation baseline

The canonical per-ID specification was unavailable in the checkout and conversation
attachments. `baseline_cases.json` is a provisional 120-case mapping derived from
the requested group sizes, previous regression requirements, and repository contracts.
Reconcile it with the canonical specification before treating the IDs as canonical.

## Run

```powershell
.\project\bot\.venv\Scripts\python.exe -m project.bot.scripts.run_baseline --legacy
.\project\bot\.venv\Scripts\python.exe -m project.bot.scripts.run_baseline --split development --output project/bot/evaluation/reports-development
.\project\bot\.venv\Scripts\python.exe -m project.bot.scripts.run_baseline --split holdout --output project/bot/evaluation/reports-holdout
```

Run from the repository root with pytest, the persistent index, and the cached
embedding model. An unavailable index or model is a retrieval failure in this
suite. Pytest runs P0 before P1 and P2. The runner returns pytest's exit code.
Use `--live` with configured Gemini credentials to enable GG-13–15. These cases
send synthetic queries and fixture venue descriptions. Default runs do not call
Gemini. Reports omit raw exception messages, HTTP headers, and environment values.

## Audit and labels

The API adapter exposes chat, place lists, district and category lists, index
health, session creation/deletion, and an unavailable-weather response. Chat
passes validated requests into the orchestrator, which routes turns and reads
session state before retrieving and ranking candidates. The adapter builds cards
from server-side place records. Evaluation traces observe those components
without changing production code.

The current JSON contains 1,691 rows. Place IDs and district names are available.
Category codes can be normalized by the loader, price text can be ambiguous, and
coordinates do not establish verified distances. The JSON has no dedicated menus,
verified reviews, or live weather. The existing index is evaluated as supplied.

For named-venue RT cases, source ID, name, district, and category are transcribed in
`ground_truth_review.json`. A complete label here means one exact venue is the
target of that query. The resulting P@5, R@5 and NDCG@5 describe named-target
search, including padding of short lists in P@5. Open-ended relevance and
ambiguous branches require manual candidate judging. Review each candidate
against the query and source evidence, grade relevance 0–3, and record whether
the set is exhaustive before using Recall@K. RT-20 is a synthetic no-match
request. CR fixtures have controlled evidence and expected eligible IDs.

For GG-13–15, record a run reference and an `annotations` object in the review
file after inspecting the saved reply against its evidence. Label `total_claims`,
`supported_claims` and `unsupported_claims` as counts. Score `relevance` and
`naturalness` from 0 to 1. Scores remain null until reviewed. Mock GG cases
measure validation, response source, and card consistency. A holdout case is
reserved for regression verification and may share venue targets with development
paraphrases. This is a visible repository holdout, so it cannot measure blind
generalization.

## Repair priority

1. **P0 — Specific food constraints and no-match.** The checked-out menu
   recognizer matches a closed vocabulary that omits porridge and unknown dishes.
   QU-05, CR-01, CR-02, and CR-05 expose how this becomes a category-only search.
   Trace CM-04 to the same missing subtype when changing dishes. RT-20 exercises
   the end-to-end no-match failure with the real index.
2. **P0 — Weather and setting.** The checked-out request schema and processor
   have no dedicated weather or setting fields. CM-05 and QU-11–15 exercise
   weather extraction, indoor/outdoor intent, and persistence; CR-15 combines
   weather with a specific dish. Explicit intent should be retained across turns.
3. **P1 — Exact named venue retrieval.** Check the real top-five misses using
   the source IDs and ranked outputs in the report. Inspect aliases and duplicate
   branches before changing embeddings or weights. The loader assigns Văn Miếu
   to `tam-linh`; its RT cases use this normalized filter to measure retrieval.
4. **P2 — Review coverage.** Review open-ended retrieval labels and live answer
   quality. Include evidence for claims and check whether comparison or follow-up
   was useful to the user.

The report describes the checkout before production fixes. Preserve the baseline
output and run to a separate output directory after each authorized fix.
