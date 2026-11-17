# ADR-0001 — Separate Network Companion Package

- **Status:** Accepted for Phase 0
- **Decision date:** 16 November 2026

## Context

Android permissions are app/UID scoped, not independently assigned to each ordinary process inside one package. A service declared in the main package cannot provide a trustworthy per-process Internet permission boundary merely by using `android:process`.

## Decision

Ship a separately installed Network Companion Android package, signed by the same publisher certificate but assigned a different application UID. The main package does not declare `INTERNET` or `ACCESS_NETWORK_STATE`. The companion owns those permissions and exports one narrow Binder service guarded by a signature-level permission.

## Consequences

- The companion has a separate Play Store listing and its own installation/update lifecycle.
- Main app must detect companion availability, signature/protocol compatibility and degrade safely when it is absent.
- The companion is still inside the trusted computing base: it can transmit any data explicitly sent to it. Main app must minimize and authorize each request.
- The signature-level permission is declared in the source manifest and is checked by static/host-side integration tests. Runtime denial of a differently signed caller is not proven by this CI suite; do not describe that property as empirically verified until separate device qualification is performed.
- No generic HTTP proxy or arbitrary URL method may be added.
