# ADR-0002 — v0 Language Policy

- **Status:** Accepted
- **Decision date:** 16 November 2026

## Decision

Mithaq v0 ships in English only, with English as the default UI and assistant language. French is excluded. Arabic is planned for a later release, but must not be represented as supported in v0.

## Future Arabic compatibility

Keep locale identifiers, content-language metadata, prompt construction and layout direction locale-aware. Later Arabic qualification must cover MSA and dialect variation, RTL and bidirectional text, embedding retrieval, model answer quality, classifier recall/false-positive rate and source attribution. No database migration should be required solely to add Arabic.
