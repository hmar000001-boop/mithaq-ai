# Phase 0 CI Fixes and Test-Strategy Change Log

## Earlier hosted findings

The initial Phase-0 CI attempts encountered several independent issues:

1. API 37 SDK installation initially used the wrong channel/package identifier. The workflow now requests the published `platforms;android-37.0` package with explicit `minorApiLevel = 0`.
2. The APK permission audit found an AndroidX legacy dynamic-receiver permission. Both app manifests now remove the API<33 compatibility permission while the packaged permission allowlist remains strict.
3. The main app needed narrow `<queries>` package visibility for its separately installed companion. Only release/debug companion IDs are listed; `QUERY_ALL_PACKAGES` is not requested.
4. The emulator stage encountered Binder service timeouts, Package Manager transport failure (`Broken pipe`), action script parsing problems and AndroidJUnitRunner process crashes. Although the later run booted the emulator, confirmed Package Manager health and installed the APKs, instrumentation still failed before producing a JUnit summary.

These events are retained as history, not as active test requirements.

## Owner decision — checkpoint 0.1.8

The owner directed that emulator E2E testing be removed entirely. CI is now limited to:

- JVM unit tests in the Android modules;
- host-JVM integration tests in `integration-tests`;
- source manifest/security configuration audits;
- Android lint;
- main and companion APK assembly;
- AAPT-based packaged APK permission audits;
- artifact upload and tag-based release publishing.

The project removes the emulator job/action, instrumentation source set and dependencies, test-only isolated-process service, separately signed attacker-probe app, emulator helper and fake-ADB test. The release build no longer depends on an emulator job.

## Important security-evidence qualification

The new host suite verifies configuration and shared source contracts. It does not prove runtime Binder authorization, cross-UID behavior, isolated-process restrictions, private-file denial, Keystore or Android system-service behavior. These remain unverified technical properties and must not be represented as passed because unit and host integration tests are green.
