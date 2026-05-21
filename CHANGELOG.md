# Changelog

All notable changes to this project will be documented in this file.

## [0.1.0.0] - 2026-05-21

### Added

- Live drafting runs that stream ordered drafting events for masked matter facts, authority search, document drafting, critique, and completion.
- Persistent drafting run and event records so the workspace can replay progress and preserve safe failure states.
- A realtime drafting workspace with connection status, retry controls, document packet progress, and a skeleton loading surface.
- Backend tests covering drafting run creation, event streaming, failed empty-context runs, and cross-user access blocking.

### Changed

- Draft generation now writes separate Notice of Motion and Supporting Affidavit documents through the drafting run service.
- Authentication can read the JWT from the existing `token` cookie so EventSource requests can use credentialed streaming.

### Fixed

- Drafting failures now rollback failed transactions before recording the failed run event.
- The drafting workspace no longer treats an unexpectedly closed event stream as a completed run.
