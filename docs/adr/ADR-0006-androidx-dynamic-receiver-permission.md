# ADR-0006 — Exclude AndroidX's pre-API-33 dynamic receiver permission

**Status:** Accepted for Phase 0  
**Date:** 16 November 2026

## Context

AndroidX Core's manifest contributes a package-scoped `DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION` declaration and matching use-permission. `ContextCompat.registerReceiver` needs that custom signature permission only in its compatibility branch for platform versions below API 33. On API 33+, it delegates to the platform `Context.registerReceiver(..., flags)` API.

Mithaq main app and Network Companion both have `minSdk = 35`. No supported runtime can execute the pre-API-33 fallback. Shipping the generated permission is therefore unnecessary privilege and noise in the least-privilege APK audit.

## Decision

Both app manifests use Android manifest-merger `tools:node="remove"` directives for the exact `${applicationId}.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION` `<permission>` and `<uses-permission>` entries. The project does not remove or rename the companion IPC permission.

## Security invariants

- Main APK requests exactly `com.mithaq.network.permission.BIND_COMPANION`; it has no network permission.
- Network Companion requests exactly `android.permission.INTERNET` and `android.permission.ACCESS_NETWORK_STATE`.
- No wildcard permission whitelist is introduced.
- Packaged APK permission audit remains authoritative and fails on any extra permission.
- If minSdk is ever lowered below API 33, this decision must be re-evaluated before release. If pre-33 support is introduced, the AndroidX fallback permission must be restored and protected as `signature`.

## Consequences

The release and debug package audits remain narrow and deterministic. A future minSdk reduction cannot silently inherit an unsupported configuration because the rationale and required review are documented here.

## References

- AndroidX Core `ContextCompat`: API 33+ delegates to the native receiver registration API; below API 33 the not-exported fallback obtains the generated permission: https://android.googlesource.com/platform/frameworks/support/+/4d0b56080497b79e6ac3d1b3b87f1029edf9c3c7/core/core/src/main/java/androidx/core/content/ContextCompat.java
- Android security guide: generated permission is required for the not-exported compatibility fallback when `minSdk < 33`: https://developer.android.com/agents/skills/security/android-intent-security/skill
