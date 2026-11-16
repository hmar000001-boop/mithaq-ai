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
