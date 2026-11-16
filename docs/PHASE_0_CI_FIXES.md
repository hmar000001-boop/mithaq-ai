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
