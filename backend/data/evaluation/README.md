# Drafting RAG Evaluation Dataset

`drafting_rag_v1.jsonl` contains masked matter-intake scenarios for evaluating
LegalDocs drafting, not standalone legal research answers. Each row asks whether
the system can retrieve Kenyan legal context and produce a usable draft packet
grounded in that context.

The v1 file is seeded from the local `backend/legal_docs.db` Kenya Law ELC
corpus and the bundled Civil Procedure Act and Rules PDF in `backend/data/sources`.
The expected authority titles are intentionally limited to case titles already
present in the local corpus so retrieval metrics can be computed without
external network access.

## Row Contract

Each JSONL row includes:

- `jurisdiction`, `subcategory`, and `pleading_type`
- `masked_facts` with anonymized parties and land references
- `retrieval_queries` for retriever-only evaluation
- `expected_authority_titles` for context recall, precision, MRR, and MAP
- `expected_statutory_materials` for drafting checks that depend on legislation
- `draft_checklist` for document-type, section, grounding, and fact-fidelity
  review
- `should_draft`; negative controls set this to `false` and require
  `insufficiency_reason`

Load and validate rows with:

```python
from src.evaluation.drafting_dataset import load_drafting_dataset

rows = load_drafting_dataset()
```

## v1 Coverage

- 8 temporary injunction matters
- 6 adverse possession matters
- 4 trespass/eviction matters
- 4 boundary/title dispute matters
- 3 procedural application matters
- 2 negative-control matters

Generator scoring should check faithfulness, answer relevance, drafting
completeness, citation support, and masked-fact fidelity.

