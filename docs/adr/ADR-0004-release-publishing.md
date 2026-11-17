# ADR-0004 — GitHub Actions Build and Release Publishing

- **Status:** Accepted
- **Decision date:** 16 November 2026

## Decision

Every manual source ZIP upload by the owner is followed by GitHub Actions CI. CI runs manifest/invariant scripts, JVM unit tests, host-JVM integration tests, lint, debug APK builds and packaged permission audits. No emulator or instrumentation stage is used. A version tag matching `v*.*.*` triggers a signed release build only after that single build/test job passes.

The release job uploads main and companion APKs, Android App Bundles and SHA-256 checksums to a GitHub Release. It uses one owner-provided release keystore for both packages because Binder permission relies on matching signatures. Signing material is stored only in GitHub Actions secrets.

## Release security

- No signing key/password is committed or included in ZIP artifacts.
- Missing signing secrets fail the release job.
- `contents: write` is scoped to the release job.
- CI debug APKs are for testing only and must not be distributed as production releases.
- All third-party GitHub Actions are pinned to reviewed immutable full commit SHAs; Dependabot monitors pinned Actions and Gradle dependencies.
- The GitHub release workflow's single-keystore setup is a Phase-0 bootstrap. Before production, review app-signing versus AAB upload-key separation.
- The Play-distributed main and companion APKs must share the same Play app-signing certificate for the companion's signature-level Binder permission. This must be configured and tested in Play Console before either listing is rolled out to open testing or production. See `docs/RELEASE_SIGNING.md`.
