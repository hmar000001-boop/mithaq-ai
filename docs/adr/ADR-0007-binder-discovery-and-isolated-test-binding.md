# ADR-0007 — Binder discovery and isolated-service test binding

**Status:** Accepted for Phase-0 validation  
**Date:** 16 November 2026

## Context

The first complete Android emulator run compiled both applications and passed the packaged APK permission audit, but timed out waiting for Binder callbacks from both the isolated inference probe and the separately installed network companion.

Android 11+ applies package-visibility filtering to package discovery and interactions with other applications. Android's package-visibility guide specifically recommends declaring a `<queries><package>` entry when interacting with a known companion app, including binding to its service. The main app had no such entry.

The isolated worker already used `android:isolatedProcess="true"` and `android:exported="false"`; its test used the generic `bindService()` call and reported only a timeout, without reporting `onNullBinding` or `onBindingDied`.

## Decision

1. The main app declares `<queries>` entries for exactly `com.mithaq.network` and `com.mithaq.network.debug`, covering the production and debug companion IDs. It does not request `QUERY_ALL_PACKAGES`.
2. The androidTest manifest repeats the narrow package visibility entries so the separately packaged instrumentation APK has deterministic package-query visibility during test setup.
3. The isolated worker test uses `Context.bindIsolatedService()` with `BIND_AUTO_CREATE`, a fresh non-sensitive instance name and the main executor. It verifies `ServiceInfo.FLAG_ISOLATED_PROCESS`, `exported=false`, and the expected process suffix before binding.
4. Both Binder tests record connected, disconnected, null-binding and binding-died callbacks, and use a 30-second timeout to tolerate a cold emulator without hiding terminal callback failures.
5. The companion test verifies package presence, service metadata, signature permission grant and matching signing identity before the Binder round trip.
6. CI captures logcat plus ActivityManager/package diagnostics if instrumentation fails.

## Security impact

The `<queries>` entries disclose only the known companion package identities to PackageManager; they do not grant the companion access to host files, accounts, or databases. They do not add network permission to the main app. `QUERY_ALL_PACKAGES` is explicitly prohibited. The companion service remains exported only behind its signature-level permission. The diagnostic inference service remains non-exported and isolated.

## Validation

Source and manifest audits must pass. The hosted emulator must establish both Binder connections, verify the isolated UID and private-file denial, confirm no Internet permission in the isolated worker, and reject the different-signer attacker. A successful source audit is not a substitute for the emulator proof.

## Reference

Android Developers, “Declare package visibility needs”: https://developer.android.com/training/package-visibility/declaring (accessed 16 November 2026). The guide instructs apps to declare a package entry for known apps they need to interact with, and notes this enables checking installation and interacting by `bindService()`.
