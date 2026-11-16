# Phase 0 — Test Matrix

| ID | Boundary or behavior | Test | Expected result | Current evidence |
|---|---|---|---|---|
| P0-MAN-01 | Main app network privilege | Parse main manifest | No INTERNET / ACCESS_NETWORK_STATE | Python CI audit |
| P0-MAN-02 | Companion network privilege | Parse companion manifest | INTERNET + ACCESS_NETWORK_STATE present | Python CI audit |
| P0-MAN-03 | Companion IPC exposure | Parse exported service | Service exported only with signature permission | Python CI audit |
| P0-MAN-04 | Shared UID | Parse both manifests | No sharedUserId | Python CI audit |
| P0-MAN-05 | AndroidX legacy receiver permission | Merge both app manifests and inspect packaged APKs | API<33-only `${applicationId}.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION` is removed because minSdk=35; no extra permission appears in either APK | Source merger-directive audit + AAPT APK audit |
| P0-IPC-01 | Same-publisher IPC | Confirm companion is query-visible, verify same signer and signature permission grant, then bind from main app | Protocol version 1 and challenge echo succeed | Android instrumentation + package/service diagnostics |
| P0-IPC-02 | Package isolation | Query both service UIDs | Main and companion service UIDs differ | Android instrumentation |
| P0-IPC-03 | Unauthorized caller | Build a probe APK with an ephemeral CI-generated, unrelated signing certificate; attempt explicit bind | Android rejects binding to the signature-protected Binder service | Emulator CI negative test |
| P0-INF-01 | Isolated service UID | Verify `ServiceInfo.FLAG_ISOLATED_PROCESS`, then use `bindIsolatedService` with a unique instance name | Worker UID differs from host app UID | Android instrumentation + package/service diagnostics |
| P0-INF-02 | Private-file isolation | Worker attempts to read host marker | Access denied | Android instrumentation |
| P0-INF-03 | Permission isolation | Worker checks INTERNET permission | Denied | Android instrumentation |
| P0-CI-01 | Compile and unit test | Gradle CI tasks | All modules compile and tests pass | GitHub Actions |
| P0-CI-02 | APK delivery | Assemble debug variants | Main + companion APK artifacts uploaded | GitHub Actions |
| P0-REL-01 | Release package signing | Tag-triggered build | Both APKs signed by same release certificate | GitHub Actions + `apksigner` follow-up |
| P0-REL-02 | Release asset upload | Tag-triggered release | APK, AAB and checksum attached | GitHub Release |
| P0-CI-03 | Third-party action integrity | Static workflow scan | Every external action uses a full 40-character commit SHA | `scripts/check_workflow_pins.py` |
| P0-CI-04 | Android SDK provisioning | Inspect all SDK install blocks | Stable API 36 and Build Tools 36.0.0 are installed; exact API 37.0 package is installed with `platforms;android-37.0` and its `android.jar` is checked | `scripts/check_project_invariants.py` |
| P0-IPC-04 | Android package visibility | Inspect main/test `<queries>` | Only release/debug companion IDs are visible; no `QUERY_ALL_PACKAGES` | Source manifest audit |
| P0-CI-05 | Instrumentation diagnostics | Force/observe instrumentation failure | Upload logcat and ActivityManager/package dumps with the test report | CI artifact |
| P0-REL-03 | Play-distributed companion authorization | Compare Play-generated APK signing certificates from both listings | Same app-signing certificate for main and companion | Play internal-testing release gate; not run |

## SDK provisioning failure and correction (checkpoint 0.1.2)

Two hosted runs failed during SDK provisioning. The first used an API 37 request without a preview channel; the second added channel 3 but still requested the nonexistent package `platforms;android-37`. API 37 is published as `platforms;android-37.0`. Checkpoint 0.1.2 requests that exact package, declares `minorApiLevel = 0` in every Android module, and verifies the installed `android.jar`. Gradle and emulator results remain pending.

## Negative test coverage and remaining checks

- The distinct-certificate unauthorized probe is implemented as a separate test APK. CI generates a one-run attacker signing identity, installs the probe alongside the companion, verifies the companion service's exported/signature-protected declaration, and asserts that Android throws `SecurityException` on the unauthorized bind. This source-level configuration remains unverified until the first hosted API 36 emulator run passes.
- AAPT-based checks inspect permissions in the packaged debug and release APKs, not only source manifests. They require the main app to have no network permission and the companion to have exactly the two declared network permissions.
- Release CI verifies that the main and companion APK signer SHA-256 certificate digests match.
- Run attacker-app tests against both packages again when additional IPC endpoints are added.
- Prove the companion cannot read main app private files and does not receive arbitrary file descriptors or unrestricted URLs before adding content-bearing IPC methods.
- Run Binder parcel-size and malformed-input tests before adding content-bearing IPC methods.


## Packaged permission audit correction (checkpoint 0.1.3)

AndroidX Core contributes a signature permission used only by its pre-API-33 `ContextCompat.registerReceiver` fallback. Since both Mithaq application modules set minSdk 35, each app manifest explicitly removes the library's `<permission>` and `<uses-permission>` nodes. The AAPT audit still enforces exact packaged permission sets: main APK = the companion signature permission only; companion APK = `INTERNET` and `ACCESS_NETWORK_STATE` only.
