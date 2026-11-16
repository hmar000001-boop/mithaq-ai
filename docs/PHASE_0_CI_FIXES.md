# Phase 0 CI Fixes — Checkpoint 0.1.1

**Date:** 16 November 2026
**Reported failing run:** 2026-11-16T20:20:46Z
**Affected step:** Install Android SDK packages

## Root cause

The workflow requested `platforms;android-37` in a default-channel `sdkmanager` invocation. Android 17 / API 37 is currently distributed as a preview SDK package. The SDK Manager only includes stable packages unless a channel is requested. Therefore `sdkmanager` could install API 36 but did not discover API 37 and exited with status 1. Gradle was never started in this run.

The `yes: standard output: Broken pipe` diagnostic came from the license-acceptance pipe closing after `sdkmanager` had consumed its input. It is not the build failure. Its stderr is suppressed to remove noise; the `sdkmanager --licenses` command's exit status is still checked.

## Correction

All three SDK installation blocks (main build/test job, emulator job and release job) now run:

```bash
yes 2>/dev/null | sdkmanager --licenses >/dev/null
sdkmanager --channel=0 "platform-tools" "platforms;android-36" "build-tools;36.0.0"
sdkmanager --channel=3 "platforms;android-37"
```

Rationale:

- API 36 is installed from the stable channel and remains the target/emulator API.
- API 37 is installed explicitly from the preview channel for `compileSdk = 37`.
- `targetSdk = 36` is unchanged; compile SDK and target SDK have different roles.
- The Compose BOM selected for this project requires compile SDK 37, so lowering compile SDK to 36 would introduce a separate compatibility issue.

## Regression protection

`scripts/check_project_invariants.py` now requires the stable API 36 and preview API 37 installation commands in all three jobs and rejects the original single-channel request pattern.

## Verification status

- Source-level workflow correction: applied.
- Regression invariant: added; local execution pending.
- Python script syntax: to be run before packaging.
- Hosted Gradle build, unit tests, APK assembly and emulator instrumentation: pending the owner's next GitHub Actions run.
