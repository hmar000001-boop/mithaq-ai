# Phase 0 — Test Matrix (host-only CI)

**Policy:** automated CI runs JVM unit tests and host-side integration checks only. There are no Android instrumentation tests, emulator E2E tests, emulator boot/install steps or device-runner jobs. A narrow migration cleanup removes only known retired files that can persist when a new ZIP is extracted over an older tracked checkout.

| ID | Boundary or behavior | Test | Expected result | Current evidence |
|---|---|---|---|---|
| P0-MAN-01 | Main app network privilege | Parse main manifest | No INTERNET / ACCESS_NETWORK_STATE; only companion signature permission | `scripts/check_manifest_boundaries.py` + host integration test |
| P0-MAN-02 | Companion network privilege | Parse companion manifest | INTERNET + ACCESS_NETWORK_STATE only | `scripts/check_manifest_boundaries.py` + host integration test |
| P0-MAN-03 | Companion IPC exposure | Parse exported service and permission declaration | Binder service exported only with `protectionLevel=signature` | Manifest audit + host integration test |
| P0-MAN-04 | Shared UID | Parse production manifests | No `sharedUserId` | Manifest audit |
| P0-MAN-05 | AndroidX legacy receiver permission | Parse source merger directives and inspect APKs | API<33-only permission absent from both APKs because minSdk=35 | Manifest audit + AAPT APK permission audit |
| P0-IPC-01 | Shared Binder contract | Compare AIDL declarations, app/companion Gradle dependencies and companion service implementation | Both Android packages consume the same narrow AIDL module; implementation exposes only declared methods | `:integration-tests:test` |
| P0-IPC-02 | Package visibility | Inspect main manifest `<queries>` | Only release/debug companion package IDs are visible; no `QUERY_ALL_PACKAGES` | Manifest audit + host integration test |
| P0-CI-01 | JVM unit tests | Gradle `testDebugUnitTest` tasks for app, contract and companion | All host-executable unit tests pass | GitHub Actions build job |
| P0-CI-02 | Host-side integration tests | Gradle `:integration-tests:test` | Manifest, AIDL/service and CI-policy contracts pass on the JVM | GitHub Actions build job |
| P0-CI-03 | Android lint | Gradle `lintDebug` for both apps | No lint errors | GitHub Actions build job |
| P0-CI-04 | Debug APK delivery | Assemble main and companion debug variants | Both APKs exist and are uploaded as artifacts | GitHub Actions build job |
| P0-CI-05 | Packaged permission boundary | AAPT inspection of both debug APKs | Main APK has only companion signature permission; companion has only INTERNET + ACCESS_NETWORK_STATE | `scripts/check_apk_permissions.py` |
| P0-CI-06 | Third-party action integrity | Static workflow scan | Every external action uses a full 40-character commit SHA | `scripts/check_workflow_pins.py` |
| P0-CI-07 | SDK provisioning | Inspect SDK install blocks | Build Tools 36.0.0 and API 37.0 compile platform are installed; no emulator/platform-tools setup | `scripts/check_project_invariants.py` |
| P0-CI-08 | Legacy ZIP-overlay cleanup | Run allowlisted cleanup before audits in both CI jobs; execute cleanup safety tests | Four stale paths are removed, unrelated paths survive, and symlink redirection is rejected | `scripts/cleanup_retired_emulator_assets.py`, `scripts/test_cleanup_retired_emulator_assets.py` and host integration test |
| P0-REL-01 | Release package signing | Tag-triggered build | Main and companion APKs signed with the same release certificate | Release CI + `apksigner` |
| P0-REL-02 | Release asset upload | Tag-triggered release | APK, AAB and checksum files attached to GitHub Release | GitHub Release workflow |
| P0-REL-03 | Play-distributed companion authorization | Compare Play-generated APK signing certificates from both listings | Both listings use the same Play app-signing certificate | Separate distribution qualification; not covered by host CI |

## Tests explicitly removed

- No `connectedDebugAndroidTest` or `assembleDebugAndroidTest` tasks.
- No AndroidJUnitRunner or `src/androidTest` test source set.
- No API 36 emulator creation, boot, ADB package installation or runtime execution.
- No test-only isolated-process service/probe in the shipped main application.
- No separately signed attacker-probe APK.
- No emulator orchestration scripts or mock-ADB regression test.

## Runtime properties not proven by host tests

The host integration suite checks source and build contracts. It does **not** prove actual Binder kernel authorization, runtime process UIDs, `android:isolatedProcess`, cross-UID private-file denial, Android Keystore/SQLCipher behavior or system-service lifecycle. Those claims must not be marked verified on the strength of JVM or manifest tests. If runtime evidence becomes a release requirement, it must be obtained through a separately authorized device-qualification activity; emulator E2E is not part of this CI policy.

## CI SDK and build strategy

The normal CI job installs only the API 37.0 compile platform and Build Tools 36.0.0. `platform-tools`, API 36 system images and AVD creation are not required. The release-build job depends on the single successful `build-test` job and therefore cannot bypass unit/integration tests, lint or packaged permission inspection.
