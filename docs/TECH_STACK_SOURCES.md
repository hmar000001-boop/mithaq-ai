# Phase-0 Build and Runtime Source Register

Reviewed on 16 November 2026. Pin versions in the repository; re-check these sources before upgrades.

| Component | Source | Phase-0 decision |
|---|---|---|
| Android Gradle Plugin 9.3 | https://developer.android.com/build/releases/agp-9-3-0-release-notes | AGP 9.3.1; Gradle >=9.5.0; JDK 17; maximum compile API 37 |
| Kotlin Gradle Plugin compatibility | https://kotlinlang.org/docs/gradle-configure-project.html | KGP 2.4.21 fully supports Gradle through 9.7.0 and AGP through 9.3.1; selected pair stays within this range |
| Gradle 9.7.0 | https://docs.gradle.org/9.7.0/release-notes.html | Within KGP 2.4.21's documented maximum fully-supported Gradle version |
| Kotlin 2.4.21 | https://kotlinlang.org/docs/releases.html | Pinned stable release |
| Google Play target API | https://support.google.com/googleplay/android-developer/answer/11926878 | API 36 required for new apps and updates from 31 Aug 2026 |
| Android 17 SDK setup | https://developer.android.com/about/versions/17/setup-sdk | Android 17 preview SDK is API 37.0; package ID is `platforms;android-37.0`; project compiles against minor API 0 and targets 36 |
| SDK Manager channel options | https://developer.android.com/tools/sdkmanager | Channel 0 is stable; channel 3 includes canary and earlier channels; CI requests exact package `platforms;android-37.0` and verifies `android.jar` |
| Compose BOM | https://developer.android.com/develop/ui/compose/bom | Stable BOM 2026.09.00 |
| Activity Compose | https://developer.android.com/jetpack/androidx/releases/activity | Stable 1.13.0 |
| LiteRT-LM Android Kotlin guide | https://developers.google.com/edge/litert-lm/android | Public generator guide uses a model path; isolated FD loading remains a proof |
| LiteRT-LM releases | https://github.com/google-ai-edge/LiteRT-LM/releases | v0.19.1 changes the C API to 1.0.0; bridge must match headers and native library |
| Gemma 4 | https://developers.google.com/edge/litert-lm/models/gemma-4 | E2B/E4B support documented; device benchmark remains essential |
| Prompt Guard 2 model card | https://github.com/meta-llama/PurpleLlama/blob/main/Llama-Prompt-Guard-2/86M/MODEL_CARD.md | Published evaluation languages exclude Arabic; qualify English for v0 |
| ONNX Runtime Android | https://onnxruntime.ai/docs/install/ | Android Maven package exists; exact model/tokenizer integration still open |

## GitHub Actions release train reviewed for this checkpoint

Every external action in `.github/workflows/ci.yml` is pinned to a full immutable commit SHA. Dependabot checks these pins weekly.

| Action | Release | Immutable commit SHA | Release/source |
|---|---|---|---|
| `actions/checkout` | v7.0.1 | `3d3c42e5aac5ba805825da76410c181273ba90b1` | https://github.com/actions/checkout/releases/tag/v7.0.1 |
| `actions/setup-java` | v6.3.0 | `d1374f8ac74474200d16ef8ecee22c7ae7a51880` | https://github.com/actions/setup-java/releases/tag/v6.3.0 |
| `android-actions/setup-android` | v4.0.4 | `be39fa834029ff78f1a44aa3bb0819b8fc2bd8fd` | https://github.com/android-actions/setup-android/releases/tag/v4.0.4 |
| `gradle/actions/setup-gradle` | v6.4.1 | `8da46b539cd8fe6ab27ca75128919a18d757604c` | https://github.com/gradle/actions/releases/tag/v6.4.1 |
| `actions/upload-artifact` | v7.0.2 | `cf430e030ddbb5b0abf93d22962f4752f3646cd9` | https://github.com/actions/upload-artifact/releases/tag/v7.0.2 |
| `actions/download-artifact` | v8.0.2 | `9000827ccba6bdab643e8b6fd33ac0654aef8333` | https://github.com/actions/download-artifact/releases/tag/v8.0.2 |
| `ReactiveCircus/android-emulator-runner` | v2.38.0 | `a421e43855164a8197daf9d8d40fe71c6996bb0d` | https://github.com/ReactiveCircus/android-emulator-runner/releases/tag/v2.38.0 |
| `softprops/action-gh-release` | v3.0.3 | `efb35369e0ad2afab669f228072c1b0d510eae64` | https://github.com/softprops/action-gh-release/releases/tag/v3.0.3 |

Gradle setup caching is disabled. The `setup-java` v6.3.0 release makes the Java problem matcher opt-in; CI still fails normally on a non-zero Gradle process exit. The signed build uses read-only repository permissions and scopes the signing secrets to the single Gradle build step. A separate job with `contents: write` downloads the prepared assets and publishes the GitHub Release.

## Play signing reference

- Google Play App Signing: https://support.google.com/googleplay/android-developer/answer/9842756
- Because Mithaq uses a signature-level Binder permission across two separately listed apps, ensure both Play-delivered APKs share the same app-signing certificate. The upload key is not the app-signing key.

- Android Gradle compileSdk minor API syntax: https://developer.android.com/reference/tools/gradle-api/9.3/com/android/build/api/dsl/CompileSdkSpec (expanded `compileSdk` block with `minorApiLevel`).

## Android API 37.0 package details

- GitHub Actions runner-image issue documenting the exact package and directory (`platforms;android-37.0` / `platforms/android-37.0`), not `android-37`: https://github.com/actions/runner-images/issues/13859
- AGP 9.3 `CompileSdkSpec` API documents `compileSdk { version = release(37) { minorApiLevel = 0 } }`; the API was added in AGP 8.13.0: https://developer.android.com/reference/tools/gradle-api/9.3/com/android/build/api/dsl/CompileSdkSpec
