# Phase 0 CI Fixes — Checkpoint 0.1.2

**Date:** 16 November 2026  
**Reported failing run:** 2026-11-16T20:28:56Z  
**Affected step:** Install Android SDK packages

## Root cause

Checkpoint 0.1.1 correctly added a preview-inclusive SDK channel, but it still requested the wrong package identifier: `platforms;android-37`. Android 37 uses a major/minor SDK package name. The published package is `platforms;android-37.0`; the integer-only package does not exist. This is a package-name mismatch, not a failure to select a sufficiently broad SDK channel.

A further compatibility issue can arise because tools may resolve integer API 37 as `android-37`, while the installed directory is `android-37.0`. AGP's expanded `compileSdk` DSL supports explicit minor API selection. Each Android module now sets `release(37) { minorApiLevel = 0 }`, matching the SDK package. This is preferable to creating a filesystem alias that can mask a mismatch.

## Correction

All three SDK installation blocks (main build/test job, emulator job and release job) now run:

```bash
yes 2>/dev/null | sdkmanager --licenses >/dev/null
sdkmanager --channel=0 "platform-tools" "platforms;android-36" "build-tools;36.0.0"
sdkmanager --channel=3 "platforms;android-37.0"
test -s "$ANDROID_HOME/platforms/android-37.0/android.jar"
cat "$ANDROID_HOME/platforms/android-37.0/source.properties"
```

Every Android module uses:

```kotlin
compileSdk {
    version = release(37) {
        minorApiLevel = 0
    }
}
```

`targetSdk = 36`, emulator API 36, and Build Tools 36.0.0 remain unchanged. API 37.0 is used for compilation only at this stage.

## Regression protection

`scripts/check_project_invariants.py` now requires the exact `android-37.0` package identifier and a post-install `android.jar` existence check in all three CI jobs. It rejects the old `platforms;android-37` request and verifies every Android module explicitly declares minor API level 0.

## Verification status

- Source-level workflow and build-file correction: applied.
- Static project, manifest, workflow-pin, XML and YAML checks: rerun locally before packaging.
- Hosted Gradle build, unit tests, APK assembly and emulator instrumentation: pending the next GitHub Actions run.


# Checkpoint 0.1.3 — Packaged permission audit correction

**Reported failing run:** 2026-11-16T20:44:41Z  
**Affected step:** Audit packaged APK permissions

## Root cause

The main APK requested the required `com.mithaq.network.permission.BIND_COMPANION`, plus `${applicationId}.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION`. The latter is merged from AndroidX Core's library manifest. It is a signature-protected compatibility permission used by `ContextCompat.registerReceiver(..., RECEIVER_NOT_EXPORTED)` only on platform versions below API 33. The AndroidX implementation delegates to the native platform overload on API 33 and newer; Mithaq's minimum SDK is API 35. The compatibility permission is therefore unnecessary for every supported device.

The companion uses the same AndroidX Activity/Compose dependency path and can receive the same merged declaration, so both packages must be checked.

## Correction

Both `app/src/main/AndroidManifest.xml` and `network-companion/src/main/AndroidManifest.xml` now use `tools:node="remove"` for both the library `<permission>` and `<uses-permission>` nodes keyed by `${applicationId}.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION`. The legitimate main-app request for `com.mithaq.network.permission.BIND_COMPANION` remains unchanged. Companion `INTERNET` and `ACCESS_NETWORK_STATE` remain unchanged.

The source manifest audit now verifies these two removal directives are present in both app manifests and ignores those directives when computing active source permissions. The packaged APK audit stays strict: the main APK must contain exactly the companion signature permission; the companion APK must contain exactly `INTERNET` and `ACCESS_NETWORK_STATE`. It does not whitelist or silently accept the AndroidX compatibility permission.

## Verification status

- XML parsing and Python source audits: to be rerun for checkpoint 0.1.3.
- Android manifest merge, Gradle build, packaged AAPT audit and emulator tests: require the next GitHub Actions run.
- The permission checker was not weakened.


# Checkpoint 0.1.4 — Binder service connection timeouts

**Reported run:** 2026-11-16T20:44Z  
**Affected task:** `:app:connectedDebugAndroidTest`

## Reported symptoms

- Build, APK packaging and packaged permission checks progressed successfully.
- `isolatedWorkerHasSeparateUidAndCannotReadHostPrivateFile` timed out waiting for the isolated worker connection.
- `companionBinderIsReachableOnlyThroughTheSignedCompanionContract` timed out waiting for the separate companion connection.
- A `/sdcard/Android/media/.../additional_test_output` cleanup command was denied, but the test runner continued and reported JUnit test failures. It is not assumed to be the Binder root cause.

## Source-level causes addressed

The main app had no package visibility declaration for its cross-package network companion. Android 11+ package visibility filters interactions with other installed packages; the Android package visibility guide specifically includes service binding among the use cases for a `<queries><package>` declaration. The main app and instrumentation test manifest now list only the release and debug companion IDs. No `QUERY_ALL_PACKAGES` permission is added.

The isolated-worker test used generic `bindService()` and had only a single timeout assertion. It now calls `bindIsolatedService()` with a unique instance name and validates the service's isolated-process metadata first. Both tests report `onNullBinding`, `onBindingDied` and `onServiceDisconnected`, verify the companion's signature permission and signer match, and wait up to 30 seconds for cold process startup.

## Additional diagnostics

The emulator job now clears logcat before the tests and captures logcat, `dumpsys package` for both application IDs, and ActivityManager service state when instrumentation fails. Those diagnostics are uploaded with the JUnit report.

## Status

This is a **source-level corrective checkpoint**. The next GitHub Actions emulator run must prove the two Binder callbacks actually occur. The isolated-worker boundary and signature-protected companion are not considered validated until the hosted emulator tests pass.


## 16. Checkpoint 0.1.5 — Package Manager `Broken pipe` during emulator APK install

### Hosted symptom

The hosted build completed successfully, including both debug APK assemblies. The emulator action then failed on its first companion installation with:

```text
adb: failed to install network-companion-debug.apk:
cmd: Failure calling service package: Broken pipe (32)
```

This occurs before the instrumentation tests start. The `Unable to strip libandroidx.graphics.path.so` messages are non-fatal native-symbol packaging warnings and are unrelated to the Package Manager failure.

### Change

- Added `scripts/run_emulator_boundary_tests.sh` to wait for boot and Package Manager readiness, install prebuilt APKs without streaming, invoke the AndroidJUnitRunner directly, run the differently signed attacker probe, and collect system diagnostics on failure.
- Added a workflow step to prebuild the main APK, companion APK, attacker APK and instrumentation APK before launching the emulator.
- Removed Gradle assembly and `connectedDebugAndroidTest` from the emulator action's runtime script; no Gradle compilation runs concurrently with emulator APK installation.
- Added bounded retries for recognized Package Manager/ADB transport interruptions and at most one emulator reboot if the Package Manager service remains unavailable. Deterministic install errors fail immediately.
- Added invariants that reject a workflow regression to building APKs after emulator startup or running Gradle from the emulator helper.
- Added `scripts/test_emulator_boundary_runner.py`, which runs the helper against a fake ADB implementation and injects one transient `Broken pipe` response to verify the bounded retry and end-to-end runner flow without pretending to be a real emulator test.
- Added ADR-0008 and updated the checkpoint, test matrix and README.

### Validation boundary

Static script/workflow/manifest/ZIP checks and the fake-ADB control-flow test validate the helper and its bounded retry, but only the next hosted emulator run can establish whether it resolves the actual emulator `Broken pipe` condition. The previous log does not prove the emulator OOMed or that `system_server` crashed; resource contention is treated as a plausible contributing condition, not a confirmed root cause.


## 17. Checkpoint 0.1.6 — Emulator action split the helper invocation into separate lines

### Hosted symptom

The 0.1.5 workflow started the emulator and then immediately printed the helper's usage text, exiting 64. No ADB boot check or APK installation ran.

### Root cause

The exact pinned `ReactiveCircus/android-emulator-runner` source implements `parseScript()` by trimming the `script:` input, splitting it on `\n`/`\r`, trimming each line, and running every nonempty line as its own `sh -c` process. A Bash multiline command using trailing backslashes is therefore not a single command in this action. The first line invoked `bash scripts/run_emulator_boundary_tests.sh` without arguments, and the helper correctly returned usage code 64.

### Change

- Changed the action input to one physical line: `script: bash scripts/run_emulator_boundary_tests.sh`.
- Added zero-argument defaults in the helper for the main, companion, attacker and androidTest APK paths and the `$RUNNER_TEMP` diagnostics directory. Five-argument mode remains supported for local use.
- Changed the fake-ADB regression test to invoke the helper with zero arguments and inject APK/diagnostics paths through environment variables, matching CI behavior.
- Added a project invariant that requires the emulator action's script input to remain a single physical command.
- Added ADR-0009 and updated the Phase 0 checkpoint and README.

### Validation boundary

The source parser behavior is verified against the exact action commit pinned in the workflow. Static checks and the zero-argument fake-ADB regression test validate this correction. The next hosted run must still prove the emulator and Binder boundaries; the current failure occurred before those tests.
