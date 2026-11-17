# Mithaq Phase 0 — Checkpoint 0.1.8

**Date:** 16 November 2026  
**Baseline:** Product specification r1.6  
**Checkpoint type:** Retire emulator E2E testing; move CI to JVM unit and host integration tests  
**Status:** Source/workflow changes prepared; hosted GitHub Actions run pending

## 1. Product decisions retained

- Brand: **Mithaq**.
- Native Android application, Kotlin-first and Jetpack Compose.
- v0 language: English only and default. Arabic is planned for a later qualified release; French is excluded.
- Main app and Network Companion remain separate APKs/packages/UIDs.
- Main app has no `INTERNET` or `ACCESS_NETWORK_STATE` permission.
- Companion has only `INTERNET` and `ACCESS_NETWORK_STATE` for its future bounded role.
- Companion Binder endpoint is exported only with a signature-level permission.
- Android min API 35, target API 36, compile API 37.0.
- JDK 17, AGP 9.3.1, Gradle 9.7.0, Kotlin 2.4.21.
- Manual repository ZIP upload remains the delivery process. CI builds APKs; version tags build and publish signed APK/AAB release assets.

## 2. Decision: remove emulator testing entirely

The owner explicitly requested that automated CI use only JVM unit tests and host-side integration tests, with no E2E tests on an Android emulator. The emulator stage is therefore removed completely, not merely disabled.

Removed from the project:

- `instrumented-boundary-tests` GitHub Actions job and `ReactiveCircus/android-emulator-runner` action.
- `app/src/androidTest`, instrumentation manifest, AndroidJUnitRunner configuration and AndroidX test-runner dependencies.
- Diagnostic-only isolated inference probe service and its test-only AIDL interface from the main APK.
- `unauthorized-probe` test APK module and ephemeral attacker signing workflow.
- Emulator ADB runner and mock-ADB regression scripts.
- Emulator boot, platform-tools and API 36 system-image setup from CI.

No Android runtime behavior is inferred as passed from these removed tests.

## 3. Active automated test strategy

| Layer | What runs | Purpose |
|---|---|---|
| JVM unit tests | `:app:testDebugUnitTest`, `:network-contract:testDebugUnitTest`, `:network-companion:testDebugUnitTest` | Test deterministic Kotlin logic without an emulator |
| Host-JVM integration tests | `:integration-tests:test` | Verify main/companion manifest privilege separation, signature-protected Binder declaration, package visibility and alignment between AIDL methods and service implementation |
| Static security audits | Manifest boundary, project invariant and action-pin scripts | Detect permission/configuration drift and ensure no emulator E2E stage is reintroduced |
| Packaged-artifact integration check | AAPT permission audit after APK assembly | Verify the actual debug APK permission sets, not only source manifests |
| Build/lint | Assemble both debug APKs and run Android lint | Verify both Android applications compile and package |

The host integration suite is deliberately honest about its scope: it does not start Android services or emulate Binder. It cannot prove real cross-UID authorization, process UID separation, private-file denial, `isolatedProcess`, Keystore, SAF or device lifecycle behavior.

## 4. Implemented foundation

| Area | Status | Evidence |
|---|---|---|
| Main Android Compose app | Present | `app/` |
| Separate Network Companion app | Present | `network-companion/` |
| Shared AIDL contract | Present | `network-contract/` |
| Signature-level permission declaration | Present in source | Companion manifest + static/host integration checks |
| Main app least privilege | Present in source and packaged audit | Main manifest + AAPT permission audit |
| Network Companion least privilege | Present in source and packaged audit | Companion manifest + AAPT permission audit |
| JVM unit tests | Configured | Android module `src/test` suites |
| Host-JVM integration tests | Added in this checkpoint | `integration-tests/` |
| APK CI artifacts | Configured | `.github/workflows/ci.yml` |
| Tag release workflow | Configured | `release-build` + `publish-release` jobs |

## 5. Explicitly unverified runtime properties

The removed emulator tests had not completed successfully. Therefore the following are **not verified** by this checkpoint:

- successful real Binder round-trip between the installed packages;
- runtime enforcement of the companion signature permission against a differently signed caller;
- runtime UID separation and service lifecycle;
- an isolated inference process being unable to read host-private files or obtain network permissions.

The main app no longer ships the former diagnostic `IsolatedInferenceProbeService`; it was test scaffolding, not the production inference worker. Actual Gemma/embedding/guard worker isolation must be proved as part of the relevant inference implementation gate. Static checks and host tests must not be described as substitutes for that runtime evidence.

## 6. Deliberately not implemented

1. Gemma 4 E4B runtime or model artifact.
2. Descriptor-based LiteRT-LM JNI bridge.
3. EmbeddingGemma 2 model integration or vector persistence.
4. PromptGuard ONNX export, exact tokenizer adapter or score parity.
5. Search provider client, HTTP client or restricted page-fetch implementation.
6. DNS pinning, SSRF enforcement or HTML extraction.
7. SQLCipher, Keystore vault, durable memory or RAG schema.
8. Image inference.
9. Release signing key; repository owner must create and store it as GitHub Actions secrets.

## 7. CI pipeline after this checkpoint

One normal `build-test` job:

1. Install JDK 17, Gradle 9.7.0, API 37.0 compile platform and Build Tools 36.0.0.
2. Run source manifest, project invariant and GitHub Action SHA-pin audits.
3. Run all Android module JVM unit tests and `:integration-tests:test`.
4. Run Android lint on main and companion apps.
5. Assemble both debug APKs.
6. Audit packaged APK permissions with AAPT.
7. Upload debug APKs and test/lint reports.

For a `v*.*.*` tag, the signed release job depends only on the successful `build-test` job. The separate publish job creates the GitHub Release and uploads APK, AAB and SHA-256 assets.

## 8. Phase 0 exit criteria

- Hosted GitHub Actions run passes all JVM unit tests and host-JVM integration tests.
- Both Android applications pass lint and produce debug APKs.
- Main/companion packaged permission sets pass the strict AAPT audit.
- Third-party workflow actions remain pinned to full commit SHAs.
- Release signing and tag-based publishing are configured and pass when the owner adds secrets.
- Model/runtime, classifier, restricted-fetch, image and device-resource proofs remain separate technical gates; they are not replaced by the host test strategy.

## 9. Verification status for checkpoint 0.1.8

The source ZIP has been updated and static checks are being run in the authoring environment. No claim is made that the new Gradle/JVM integration module has compiled or that GitHub-hosted CI has passed. Hosted verification is required after the owner uploads this checkpoint.
