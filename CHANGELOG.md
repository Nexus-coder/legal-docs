# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0.0] - 2026-05-26

### Added

- Advocates can now review the recommended filing packet before drafting and include optional documents such as certificates of urgency, draft orders, written submissions, witness statements, and lists of documents.
- Drafting packets now expose backend metadata for required and optional documents so the workspace can show the correct packet for each matter type.
- Drafting runs now persist the selected document types and reject unsupported selections before invoking the legal drafting agent.

### Changed

- The drafting workspace now waits for the advocate to choose optional documents instead of auto-starting generation as soon as masked facts load.
- Generation progress now follows the selected packet dynamically, including optional documents selected for that run.

## [0.2.1.0] - 2026-05-26

### Changed

- Legal drafting now defaults to the configurable `gpt-5.5` drafting model while keeping the existing embedding index unchanged.
- The drafting agent now grounds critique against the original request, matter instructions, and retrieved Kenya Law context.
- Drafting runs now move blocking model and retrieval work off the async event loop.

### Fixed

- Drafting now fails safely with `retrieval_failed` before generating documents when no usable authority context is retrieved.
- Critique now only passes on an exact `PASS` response instead of accepting partial pass text with unresolved issues.
- Draft prompts now mark matter facts and retrieved authorities as untrusted source material to reduce prompt-injection risk.

## [0.2.0.0] - 2026-05-26

### Added

- Drafting packets for adverse possession, trespass/eviction, boundary/title disputes, and procedural applications, with document instructions matched to each pleading type.
- A drafting evaluation dataset and Ragas-compatible runner for measuring retrieval coverage, authority ranking, checklist fit, and negative-control behavior.
- Matter-scoped citation provenance from retrieved Kenya Law authorities, including source URLs, neutral citations, judgment metadata, confidence breakdowns, and inline editor citation anchors.

### Changed

- Drafting requests can now default jurisdiction, subcategory, and pleading type from the matter while still preserving the selected packet on drafting runs.
- Draft generation now uses the Kenya Law ELC vector namespace and fails safely when no authority context is retrieved.
- The drafting workspace now renders filing packet documents from the generated backend documents instead of assuming every matter is a temporary injunction packet.

### Fixed

- Regenerated drafts no longer fail authority grounding because retrieval queried the wrong Pinecone namespace.
- Unsupported drafting categories now return a readable workspace error instead of exposing a raw backend status.

## [0.1.0.0] - 2026-05-25

### Added

- Live drafting runs that stream ordered drafting events for masked matter facts, authority search, document drafting, critique, and completion.
- Persistent drafting run and event records so the workspace can replay progress and preserve safe failure states.
- A realtime drafting workspace with connection status, retry controls, document packet progress, and a skeleton loading surface.
- A persisted Tiptap editor for generated draft documents, including autosave, manual save, dirty/saving/saved states, and citation-aware editor anchors.
- Draft document revision snapshots that preserve the generated baseline and record manual, autosave, and restore edits.
- Draft export endpoints for browser preview and `.docx` download generated from validated editor JSON.
- Backend tests covering drafting run creation, event streaming, failed empty-context runs, cross-user access blocking, editor JSON validation, stale-save handling, citation ownership, and export output.

### Changed

- Draft generation now writes separate Notice of Motion and Supporting Affidavit documents through the drafting run service.
- Authentication can read the JWT from the existing `token` cookie so EventSource requests can use credentialed streaming.
- Draft documents now treat validated Tiptap JSON as the canonical editable state while keeping plain-text content updated for existing matter records and compatibility.
- The drafting workspace now opens generated pleadings in an editable legal-document surface instead of rendering read-only draft text.

### Fixed

- Drafting failures now rollback failed transactions before recording the failed run event.
- The drafting workspace no longer treats an unexpectedly closed event stream as a completed run.
- Citation evidence snippets now strip Kenya Law index metadata and show a usable judgment excerpt.
- Stale editor saves now return a clear `stale_revision` conflict instead of overwriting newer draft edits.
