# Phase 0 — Test Matrix

| ID | Boundary or behavior | Test | Expected result | Current evidence |
|---|---|---|---|---|
| P0-MAN-01 | Main app network privilege | Parse main manifest | No INTERNET / ACCESS_NETWORK_STATE | Python CI audit |
| P0-MAN-02 | Companion network privilege | Parse companion manifest | INTERNET + ACCESS_NETWORK_STATE present | Python CI audit |
| P0-MAN-03 | Companion IPC exposure | Parse exported service | Service exported only with signature permission | Python CI audit |
| P0-MAN-04 | Shared UID | Parse both manifests | No sharedUserId | Python CI audit |
| P0-IPC-01 | Same-publisher IPC | Bind from main app to companion | Protocol version 1 and challenge echo succeed | Android instrumentation |
| P0-IPC-02 | Package isolation | Query both service UIDs | Main and companion service UIDs differ | Android instrumentation |
| P0-IPC-03 | Unauthorized caller | Build a probe APK with an ephemeral CI-generated, unrelated signing certificate; attempt explicit bind | Android rejects binding to the signature-protected Binder service | Emulator CI negative test |
| P0-INF-01 | Isolated service UID | Bind main to isolated probe | Worker UID differs from host app UID | Android instrumentation |
| P0-INF-02 | Private-file isolation | Worker attempts to read host marker | Access denied | Android instrumentation |
| P0-INF-03 | Permission isolation | Worker checks INTERNET permission | Denied | Android instrumentation |
| P0-CI-01 | Compile and unit test | Gradle CI tasks | All modules compile and tests pass | GitHub Actions |
| P0-CI-02 | APK delivery | Assemble debug variants | Main + companion APK artifacts uploaded | GitHub Actions |
| P0-REL-01 | Release package signing | Tag-triggered build | Both APKs signed by same release certificate | GitHub Actions + `apksigner` follow-up |
| P0-REL-02 | Release asset upload | Tag-triggered release | APK, AAB and checksum attached | GitHub Release |
| P0-CI-03 | Third-party action integrity | Static workflow scan | Every external action uses a full 40-character commit SHA | `scripts/check_workflow_pins.py` |
| P0-CI-04 | Android SDK provisioning | Inspect all SDK install blocks | Stable API 36 from channel 0 and preview API 37 from channel 3 are installed separately | `scripts/check_project_invariants.py` |
| P0-REL-03 | Play-distributed companion authorization | Compare Play-generated APK signing certificates from both listings | Same app-signing certificate for main and companion | Play internal-testing release gate; not run |

## SDK provisioning failure and correction (checkpoint 0.1.1)

The first hosted run failed during `sdkmanager` provisioning with `Failed to find package 'platforms;android-37'`. This is consistent with requesting Android 17 / API 37 from the default stable channel while the Android 17 setup guide places API 37 in the preview channel. The workflow now installs stable API 36 with `--channel=0` and API 37 with `--channel=3`. The Gradle build and emulator jobs have not yet been observed succeeding; rerun CI after uploading checkpoint 0.1.1.

## Negative test coverage and remaining checks

- The distinct-certificate unauthorized probe is implemented as a separate test APK. CI generates a one-run attacker signing identity, installs the probe alongside the companion, verifies the companion service's exported/signature-protected declaration, and asserts that Android throws `SecurityException` on the unauthorized bind. This source-level configuration remains unverified until the first hosted API 36 emulator run passes.
- AAPT-based checks inspect permissions in the packaged debug and release APKs, not only source manifests. They require the main app to have no network permission and the companion to have exactly the two declared network permissions.
- Release CI verifies that the main and companion APK signer SHA-256 certificate digests match.
- Run attacker-app tests against both packages again when additional IPC endpoints are added.
- Prove the companion cannot read main app private files and does not receive arbitrary file descriptors or unrestricted URLs before adding content-bearing IPC methods.
- Run Binder parcel-size and malformed-input tests before adding content-bearing IPC methods.
