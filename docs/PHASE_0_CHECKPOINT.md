# Mithaq Phase 0 — Checkpoint 0.1.3

**Date:** 16 November 2026  
**Baseline:** Product specification r1.5, amended for the selected brand name Mithaq  
**Checkpoint type:** Repository and security-boundary foundation; packaged permission audit correction  
**Status:** Source prepared; hosted Gradle/APK/emulator validation pending

## 1. Product decisions frozen for this checkpoint

- Brand: **Mithaq**.
- Native Android application, Kotlin-first and Jetpack Compose.
- v0 language: English only and default. Arabic is planned for a later qualified release; French is excluded.
- Main app and Network Companion are separate APKs/packages/UIDs.
- Main app has no `INTERNET` or `ACCESS_NETWORK_STATE` permission.
- Companion has only the bounded network permissions required for its future role.
- Companion Binder endpoint is exported only with a signature-level permission.
- Android min API 35, target API 36, compile API 37.0.
- JDK 17, AGP 9.3.1, Gradle 9.7.0, Kotlin 2.4.21.
- Release uploads are manual repository push plus GitHub Actions CI; version tags produce signed APK/AAB assets.

## 2. Implemented in this checkpoint

| Area | Implemented | Evidence in repository |
|---|---|---|
| Main Android application | Minimal Compose shell and launcher activity | `app/` |
| Network companion application | Separate Android application, launcher and service | `network-companion/` |
| Shared IPC contract | Minimal AIDL protocol interface | `network-contract/` |
| Signature-level Binder protection | Exported companion service requires `com.mithaq.network.permission.BIND_COMPANION` with `protectionLevel=signature` | Companion manifest |
| Main app least privilege | Requests only the companion signature permission; no network or unused AndroidX legacy receiver permission | Main manifest merger rules + source/APK audits |
| Isolated process probe | `isolatedProcess=true`, non-exported service | Main manifest + probe service |
| Positive Binder test | Main app binds companion, round-trips challenge, checks distinct UIDs | `BoundaryInstrumentedTest` |
| Negative Binder test | Separate probe APK signed with an ephemeral, unrelated CI certificate attempts to bind and must be denied | `unauthorized-probe/` + emulator workflow (hosted run pending) |
| Isolation test | Checks isolated UID differs, cannot read host-private marker, lacks Internet permission | `BoundaryInstrumentedTest` |
| Build checks | Python manifest and product invariants, including explicit removal of AndroidX Core's API<33 receiver-permission fallback | `scripts/` |
| CI | Unit tests, lint, both debug APKs, emulator tests, artifact uploads | `.github/workflows/ci.yml` |
| Release publishing | Signed APK/AAB and checksums uploaded to GitHub Release on `v*.*.*` tags | `publish-release` job |

## 3. Deliberately not implemented

1. Gemma 4 E4B runtime or model artifact.
2. Descriptor-based LiteRT-LM JNI bridge.
3. EmbeddingGemma 2 model integration or vector persistence.
4. PromptGuard ONNX model export, tokenizer adapter, or score parity.
5. Search provider client, HTTP client or page-fetch implementation.
6. DNS pinning, SSRF enforcement or HTML extraction.
7. SQLCipher, Keystore vault, durable memory or RAG schema.
8. Image inference. Image input remains conditional on the model/runtime/device gate.
9. Release signing key. It must be created and stored by the repository owner as GitHub Actions secrets.

The companion AIDL interface is deliberately narrow; it is not a generic HTTP proxy. Future network operations must be added as explicit typed operations with policy and consent contracts.

## 4. Build-tooling notes

The build pins AGP 9.3.1, Gradle 9.7.0 and Kotlin 2.4.21. AGP 9.3 supports up to compile SDK 37, requires Gradle 9.5.0 or higher and JDK 17. The selected KGP 2.4.21 compatibility table supports AGP through 9.3.1 and Gradle through 9.7.0; both pins are within that fully-supported range. Google Play submissions for new apps and updates must target API 36 or higher from 31 August 2026. [R1–R3]

AGP 9 enables built-in Kotlin by default. This checkpoint opts out with `android.builtInKotlin=false` and `android.newDsl=false` so that Kotlin Gradle Plugin 2.4.21 and the matching Compose compiler plugin are explicitly pinned. This is transitional: the opt-out must be revisited before upgrading to AGP 10, where it is removed. [R4]

A Gradle Wrapper JAR could not be retrieved in this build environment. No fake or incomplete wrapper script is included. GitHub Actions provisions Gradle 9.7.0 directly using `gradle/actions/setup-gradle`; README documents how to generate and commit a standard wrapper after installing Gradle locally.

## 5. Verification status

<badge>Pending hosted CI</badge>

| Check | Status | Notes |
|---|---|---|
| XML parse | PASS | All three application manifests parsed successfully |
| Python manifest audit | PASS | `scripts/check_manifest_boundaries.py` |
| Python product invariant audit | PASS | `scripts/check_project_invariants.py` |
| Python workflow pin audit | PASS | `scripts/check_workflow_pins.py`; all third-party action refs use full commit SHAs |
| Python syntax compile | PASS | All repository Python scripts compile with `py_compile` |
| CI YAML syntax and structural scan | PASS | Parsed locally; GitHub-hosted execution remains pending |
| SDK package invariant | PASS | All three workflow jobs request the exact `platforms;android-37.0` package and verify its `android.jar`; all Android modules pin minor API 0 |
| Gradle configuration/build | Not yet reached by hosted CI | The first run failed in SDK provisioning before Gradle; this checkpoint fixes that step. The authoring runtime also has no Gradle/Android SDK |
| Unit tests | Not run | Requires Gradle/Android SDK resolution |
| APK builds | Not run | Requires Android SDK/Gradle |
| Binder emulator test | Not run | Requires API 36 emulator |
| Release signing/upload | Not run | Requires owner-created GitHub secrets and tag |

Two hosted runs failed before Gradle was invoked. Checkpoint 0.1.1 corrected the channel but not the package ID; checkpoint 0.1.2 fixed that by requesting `platforms;android-37.0` and explicitly setting minor API 0. The next hosted run reached the APK permission audit and found an AndroidX Core compatibility permission in the main APK. Checkpoint 0.1.3 removes that unused API<33 fallback permission from both app manifests because minSdk is 35; the strict APK audit remains unchanged and will verify the packaged result. Gradle, test, APK and emulator status must be confirmed by hosted CI; no source-level change is treated as a successful build.

## 6. Play App Signing constraint

The main and companion services rely on Android's signature-level Binder permission. Therefore, the APKs installed from Google Play must have the same **Play app-signing certificate**. Matching only the AAB upload-key certificates is insufficient because Play signs the distribution APKs with the app-signing key. For two new Play listings, configure the second listing to use the same app-signing key as the first, or provide a copy of the same app-signing key, before either listing is rolled out to open testing or production. Confirm the certificate fingerprints on Play-generated APKs during internal testing. [R5]

The Phase-0 release workflow currently uses one GitHub Actions keystore to sign GitHub APK assets and AABs. This is a bootstrap arrangement, not the final key-custody recommendation. Before production publishing, decide whether to split the direct-APK app-signing key from the AAB upload key and update the release workflow accordingly. Never mistake the upload key for the Play app-signing key.

## 7. Phase 0 exit criteria

Phase 0 remains open until:

- GitHub Actions successfully compiles both APKs and passes unit tests/lint.
- The API 36 emulator confirms the network companion Binder round trip under the signature permission and denies the differently signed attacker probe.
- The isolated service UID differs from the host UID and cannot read the host app's private marker file.
- The isolated service reports no Internet permission.
- Play Console signing configuration is documented before either companion listing is released; both Play-delivered packages use the same app-signing certificate.
- Merged-manifest inspection confirms main app has no network permission and companion has only its expected permissions.
- Gemma FD-loading proof, embedding proof, classifier export/parity, URL-fetch proof and resource benchmarks are delivered as separate technical reports or explicit blockers.

## 8. Next work within Phase 0

1. Upload checkpoint 0.1.3 and rerun GitHub Actions; confirm both packaged APK permission audits pass with the strict expected permission sets.
2. Fix any subsequent Gradle/AGP/AIDL/Compose/manifest/instrumentation failures and issue a full replacement ZIP.
3. Run LiteRT-LM Gemma 4 E4B raw-FD proof on a physical Android 16/API 36 device.
4. Run EmbeddingGemma text-only inference proof, verify exact model artifact/tokenizer/template and output dimensions.
5. Export PromptGuard 2 86M to ONNX, integrate the exact tokenizer and compare Android logits against reference Transformers results.
6. Implement and test the separate-package companion protocol version/signature lifecycle.
7. Prototype secure HTTP fetch with DNS-to-socket pinning and strict redirect enforcement; no live product tool until the gate passes.
8. Produce measured peak-memory/thermal evidence for 8 GB and 12 GB reference devices.

## 9. References

- R1 — Android Gradle Plugin 9.3 release notes: https://developer.android.com/build/releases/agp-9-3-0-release-notes
- R2 — Gradle 9.7.0 release notes: https://docs.gradle.org/9.7.0/release-notes.html
- R6 — Kotlin Gradle Plugin 2.4.21 compatibility matrix: https://kotlinlang.org/docs/gradle-configure-project.html
- R3 — Google Play target API requirements: https://support.google.com/googleplay/android-developer/answer/11926878
- R4 — AGP 9 built-in Kotlin and migration guidance: https://developer.android.com/build/migrate-to-built-in-kotlin
- R5 — Google Play App Signing, including the option to use the same app-signing key for multiple listings before rollout: https://support.google.com/googleplay/android-developer/answer/9842756
- R7 — Set up the Android 17 SDK; documents compileSdk 37 and the Android 17 SDK package: https://developer.android.com/about/versions/17/setup-sdk
- R8 — AGP CompileSdkSpec; documents `release(37) { minorApiLevel = 0 }`: https://developer.android.com/reference/tools/gradle-api/9.3/com/android/build/api/dsl/CompileSdkSpec
- R9 — GitHub Actions runner-image issue confirming API 37.0 package ID and `android-37.0` install path: https://github.com/actions/runner-images/issues/13859
- R10 — AndroidX Core source: its receiver-registration compatibility permission is only checked below API 33; API 33+ delegates to the platform overload: https://android.googlesource.com/platform/frameworks/support/+/4d0b56080497b79e6ac3d1b3b87f1029edf9c3c7/core/core/src/main/java/androidx/core/content/ContextCompat.java
- R11 — Android security guide: the generated receiver permission is required when `minSdk < 33`, not when the supported baseline is API 35: https://developer.android.com/agents/skills/security/android-intent-security/skill
- R8 — SDK Manager channel options (0 stable, 1 beta, 2 dev, 3 canary): https://developer.android.com/tools/sdkmanager
