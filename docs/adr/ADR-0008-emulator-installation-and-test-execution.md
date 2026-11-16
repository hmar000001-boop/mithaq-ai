# ADR-0008 — Prebuild emulator APKs and run boundary instrumentation without Gradle on-device

**Status:** Accepted for Phase 0 CI reliability  
**Date:** 16 November 2026

## Context

Checkpoint 0.1.4 reached successful Gradle compilation and APK assembly. The emulator action then failed at the first `adb install` with:

```text
adb: failed to install network-companion-debug.apk:
cmd: Failure calling service package: Broken pipe (32)
```

The prior workflow ran Gradle APK assembly and the connected instrumentation task inside the emulator action's script. That meant Gradle's JVM, workers and dependency/build operations ran concurrently with the emulator's `system_server` and Package Manager while APK installation and Binder tests were being prepared. The exact low-level emulator failure is not yet proven, but this unnecessary resource contention is avoidable and is a plausible contributor to the Package Manager transport interruption.

The emulator-runner action waits for `sys.boot_completed=1`; it does not establish that the Package Manager Binder service is responsive. Therefore the test harness needs its own readiness check and diagnostics.

## Decision

1. Build the main debug APK, companion debug APK, attacker-probe APK and Android instrumentation APK in a normal workflow step **before** starting the emulator.
2. Do not run Gradle compilation or `connectedDebugAndroidTest` while the emulator is running.
3. Use a dedicated Bash helper to wait for Android boot completion and independently poll `cmd package list packages` until Package Manager is responsive.
4. Install prebuilt APKs using `adb install --no-streaming`; pass `-t` for the instrumentation APK.
5. Retry only recognized ADB transport / Package Manager interruption errors. If Package Manager remains unavailable, permit exactly one controlled emulator reboot, then fail with diagnostics if recovery does not succeed. Do not retry deterministic package/signature/manifest installation errors.
6. Discover the instrumentation runner from `pm list instrumentation` for target package `com.mithaq.app.debug`, then run `BoundaryInstrumentedTest` using `adb shell am instrument -w -r`.
7. Keep the separately signed attacker-app denial test after instrumentation. A missing service, false bind result or unavailable package is not accepted as proof of signature-permission enforcement.
8. On every failure, capture all-buffer logcat, properties, Package Manager state, ActivityManager services, memory summary, installed packages and instrumentation registrations.
9. Upload the raw instrumentation output and emulator diagnostics as GitHub Actions artifacts.
10. Run a fake-ADB regression test in the normal build job; it injects one transient Package Manager transport failure and verifies the retry path and successful instrumentation/attacker flow.

## Consequences

- Emulator runtime no longer overlaps with full Gradle assembly, reducing host memory and CPU contention.
- Package Manager readiness is explicitly verified rather than inferred from `sys.boot_completed` alone.
- Instrumentation runs independently of Gradle's connected-device orchestration, while retaining the same AndroidJUnitRunner tests and assertions.
- Test output is preserved as a raw artifact. Gradle's generated connected-test HTML report is no longer expected for this manually invoked instrumentation path.
- A transient Package Manager outage has one bounded recovery path; persistent failures remain visible and fail CI.

## Acceptance criteria

- The prebuild step produces all four required APKs before emulator launch.
- Package Manager readiness check succeeds before install.
- Companion, main, attacker and instrumentation APKs install and their expected package identities are confirmed.
- Both `BoundaryInstrumentedTest` methods report a clean JUnit success summary.
- The differently signed attacker app emits `MITHAQ_PERMISSION_PROBE_DENIED` and no failure marker.
- Failure diagnostics are uploaded even when installation or instrumentation fails.
- The fake-ADB regression test passes in the non-emulator CI job.

## References

- Android Debug Bridge command reference documents `adb install --no-streaming` as pushing the APK to the device and invoking Package Manager as a separate step: https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/main/docs/user/adb.1.md
- ReactiveCircus Android Emulator Runner waits for `sys.boot_completed=1` before running its custom script: https://github.com/ReactiveCircus/android-emulator-runner/blob/main/src/emulator-manager.ts
