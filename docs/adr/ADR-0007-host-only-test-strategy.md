# ADR-0007 — Use JVM unit and host-side integration tests; remove emulator E2E from CI

- **Status:** Accepted
- **Decision date:** 16 November 2026
- **Supersedes:** Emulator/instrumentation CI decisions recorded in former ADR-0007 through ADR-0010

## Context

Phase-0 CI repeatedly failed in the Android emulator stage for several different reasons: Binder connection timeouts, Package Manager transport failure during APK installation, incorrect action-script parsing, and AndroidJUnitRunner process crashes. The latest run successfully booted the emulator, installed all test APKs and started AndroidJUnitRunner, but the instrumentation process crashed before producing a JUnit result.

The test APKs and diagnostic-only service existed solely to exercise runtime behavior in this emulator job. Repeated adjustments to emulator startup, ADB retries, instrumentation invocation and crash collection were not producing a stable, maintainable validation signal. The owner has explicitly directed that CI use JVM unit tests and host-side integration tests only, with no E2E tests on an emulator.

## Decision

1. Remove the complete `instrumented-boundary-tests` GitHub Actions job and the pinned Android emulator runner action.
2. Remove Android instrumentation source sets, runner dependencies, test manifests and `connectedDebugAndroidTest`/`assembleDebugAndroidTest` tasks.
3. Remove the test-only isolated inference probe service and its AIDL interface from the production app. It was not the production Gemma worker and must not be shipped as diagnostic runtime code.
4. Remove the separately signed `unauthorized-probe` application module and its ephemeral test-signing workflow.
5. Remove emulator orchestration and mock-ADB test scripts.
6. Run JVM unit tests in the Android modules and a dedicated host-JVM `integration-tests` module. The host integration suite verifies source-level manifest privilege separation, signature-protected service declaration, package visibility, shared AIDL/service method alignment and absence of emulator CI stages.
7. Continue to inspect the actual built debug and release APK manifests with AAPT. This is a packaged-artifact integration check, not a runtime Binder test.
8. Make the release-build job depend only on the single successful test/build job.
9. Do not describe host tests as proof of Android Binder authorization, distinct runtime UIDs, isolated-process behavior, private-file denial, Keystore behavior or service lifecycle. Those runtime properties remain unverified until separately qualified on actual devices if the project later requires that evidence.

## Consequences

- CI no longer creates, boots, installs packages on or runs tests against an Android emulator.
- Build time and CI failure surface are reduced; JVM test results are repeatable and do not depend on Android system_server/Package Manager startup.
- Static/host tests verify configuration and contracts but cannot prove kernel-enforced cross-UID IPC or Android runtime isolation. Production security claims must remain bounded to the evidence actually collected.
- Future Android-only behavior should be designed behind testable interfaces and covered with JVM unit/host integration tests wherever possible. Any future request to reintroduce device automation requires a new explicit owner decision and ADR.
