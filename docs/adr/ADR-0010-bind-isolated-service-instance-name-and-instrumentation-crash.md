# ADR-0010 — Correct isolated-service instance names and isolate instrumentation failures

**Status:** Accepted for Phase 0
**Date:** 16 November 2026

## Context

The 0.1.6 hosted run successfully booted the API 36 emulator, confirmed Package Manager responsiveness, installed all four APKs, and discovered the AndroidJUnitRunner. The first direct instrumentation invocation then returned:

```text
INSTRUMENTATION_RESULT: shortMsg=Process crashed.
INSTRUMENTATION_CODE: 0
```

The command's shell exit status was not sufficient to explain the failure. Android's public `Context.bindIsolatedService()` contract specifies that `instanceName` may contain only ASCII letters, digits, underscores, and periods; invalid names throw `IllegalArgumentException`. Android's CTS test explicitly includes `test-three` as an invalid value.

The isolated-worker test previously passed `phase0-isolation-${UUID.randomUUID()}`. Both the fixed prefix and UUID string contain hyphens. This is a deterministic API-contract violation in the test itself. The generic crash line alone does not prove that it is the only runtime issue, so the runner also needs to preserve the first fatal stack trace and distinguish runner startup from each individual boundary case.

## Decision

1. Generate the isolated-service name as `mithaq_phase0_` plus a UUID with all hyphens removed. This yields only permitted ASCII letters, digits and underscores.
2. Add a minimal `InstrumentationSmokeTest` that verifies the AndroidJUnitRunner starts and exposes the expected target package.
3. Run the smoke test first, followed by the isolated-worker test method and companion Binder test method in separate `am instrument` invocations.
4. Require each invocation to return `INSTRUMENTATION_CODE: -1` and exactly one JUnit success (`OK (1 test)`). A zero shell status alone is not success.
5. Clear logcat before each invocation. Immediately after each invocation, save the crash buffer, full logcat and ActivityManager historical exit information for the target package.
6. On failure, print fatal Java/native crash excerpts into the Actions log and upload full diagnostics.
7. Keep the existing Android security assertions unchanged: isolated UID, private-file denial, no INTERNET permission, same-signer companion Binder round trip, and different-signer attacker denial.

## Consequences

- The test no longer violates the Android API's instance-name character contract.
- Runner initialization failures can be distinguished from either individual Binder-boundary case.
- A subsequent failure should include the relevant crash buffer and historical process exit reason rather than only `Process crashed`.
- This correction is source-level evidence. The isolated UID and Binder behavior remain unverified until the hosted emulator suite passes.

## References

- Android `Context.bindIsolatedService()` API: https://developer.android.com/reference/android/content/Context#bindIsolatedService(android.content.Intent,int,java.lang.String,java.util.concurrent.Executor,android.content.ServiceConnection)
- Android CTS invalid-instance-name test: https://android.googlesource.com/platform/cts/+/master/tests/app/src/android/app/cts/ServiceTest.java
- AndroidJUnitRunner instrumentation crash example and need to inspect the crash stack: https://github.com/android/android-test/issues/1834
