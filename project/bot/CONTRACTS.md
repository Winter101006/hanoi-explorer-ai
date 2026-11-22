# PR0 — Shared contracts

PR0 uses Python standard-library dataclasses and unittest. Run from repository root:

```powershell
python -B -m unittest discover -s project/bot/tests -p "test_contracts.py" -v
```

## Architecture Separation

The core pipeline isolates domain contracts from web delivery and external ML dependencies:
- **Core Data, NLU & Retrieval:** `schemas.py`, `config.py`, `data_loader.py`, `embedding.py`, `chroma_manager.py`, `query_processor.py`, `retriever.py`, and `recommender.py`.
- **Orchestration, LLM & Web Delivery:** `memory.py`, `gemini_client.py`, `prompts.py`, `chatbot.py`, `src/web`, API adapters, and the evaluation runner.
All components adhere to the strict contract interfaces below so tests can swap collaborators with deterministic mocks without requiring runtime ML dependencies.

## Module interfaces for subsequent workstreams

| Module | Signature |
|---|---|
| data_loader | load(path: Path) -> list[Place] |
| embedding | encode(texts: list[str]) -> list[list[float]] |
| query_processor | process(message: str, state: ConversationState, explicit_filters: dict) -> QueryUnderstanding |
| retriever | retrieve(request: SearchRequest) -> list[RetrievalResult] |
| recommender | rank(request: SearchRequest, candidates: list[RetrievalResult], limit: int) -> list[Recommendation] |
| memory | get(session_id: str) -> ConversationState; save(session_id: str, state: ConversationState) -> None; clear(session_id: str) -> None |
| gemini_client | extract_query(prompt: str) -> dict; generate_answer(prompt: str) -> dict |
| chatbot | respond(request: ChatRequest) -> ChatbotResponse |

Implementations accept their collaborators in constructors so tests can supply mocks.
The query processor receives a state snapshot. The orchestrator persists the new
state. Retrieval owns embedding calls, while the recommender consumes candidates.

## Context and validation

QueryUpdate.values contains only explicitly changed fields. Missing fields retain
their previous values. clear_fields restores field defaults. reset starts a new
topic. Preferences are a complete replacement tuple after the query processor has
resolved additions/removals. JSON arrays must be converted to tuples by the boundary
adapter. Gemini JSON must be checked for allowed keys and expected types before
constructing dataclasses; type annotations alone do not validate arbitrary JSON.

The current message overrides inherited constraints. An explicit UI filter that
conflicts with the message requires clarification. The UI value `all` means no
additional UI restriction, not an instruction to clear conversation constraints.
Ambiguous HUS references produce clarification before retrieval.

## Source and normalization

RawPlace preserves input fields. Place.normalized_category_code is derived.
Quán ăn with a spiritual code is flagged and normalized to an-uong by the loader.
Quán nước requires the agreed beverage mapping; unresolved cases retain an unknown
normalized code. Category words appearing in street names are not category evidence.
Generic district addresses are district_only. Numeric coordinate validity does not
set coordinates_verified. Distance ranking remains disabled until evidence supports it.
PriceInfo retains unknown values and conditions. The raw price lives in source.price_range.
Duplicate names are kept under their source IDs and reported for review.

## Ranking and output

Use normalized embeddings and cosine distance. Semantic score is
clamp(1 - cosine_distance, 0, 1), not a probability. Default ranking weights are
semantic .40, preference .25, location .20, budget .15. Inactive user criteria are
excluded and remaining weights renormalized. Missing evidence for an active hard
constraint cannot pass that constraint. Unknown soft criteria receive no positive
match credit and are disclosed in limitations.

ChatbotResponse.validate_ids checks unique recommendation IDs against retrieved
IDs. The API adapter obtains all card metadata from server-side Place objects.
The existing status/reply/places/total_results/itinerary/location_info fields remain
supported. answer maps to reply. New fields are additive. Legacy history IDs are
resolved against the current dataset. Requests without session IDs use request
history, never one shared session for all clients.

## Configuration and index compatibility

load_settings reads a supplied mapping or process environment explicitly. Relative
paths resolve from bot/. .env.example documents variables; PR0 does not automatically
load .env. Set GEMINI_MODEL and GEMINI_API_KEY when implementing Gemini integration.
Embedding normalization is enabled by the embedding implementation contract.
Index metadata must record model, vector dimension, normalization, document version
and dataset fingerprint. Model/document incompatibility requires a separate collection.
Dataset updates are explicit offline indexing operations; startup never rebuilds it.

## Fixture and verification scope

tests/fixtures/contracts.json includes source conflicts, incomplete metadata,
conditional free pricing, invalid generation IDs and a four-turn context sequence.
Tests cover the contracts and the current source schema. Semantic retrieval, live
Gemini, session storage and Flask migration are implemented and verified in WS1–WS4.
The existing web package will move once into src/web during WS4.
