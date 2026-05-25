# Changelog

All notable changes to this project will be documented in this file.

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
