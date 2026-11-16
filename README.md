# Mithaq — Android Project (Phase 0)

Mithaq is a native Kotlin Android personal AI workspace. This repository is the first Phase-0 implementation checkpoint, not a feature-complete product release.

## Product baseline

- **Product name:** Mithaq
- **v0 language:** English only; English is the default.
- **Future language:** Arabic is planned, but it is not a supported v0 language.
- **French:** explicitly excluded.
- **Android:** min API 35 (Android 15), target API 36, compile API 37.0.
- **ABI target:** `arm64-v8a` for production model/runtime qualification. The Phase-0 APK also builds for emulator testing.
- **Device qualification target:** 8 GB RAM minimum test target; 12 GB recommended. No device is declared supported until the full runtime and thermal matrix passes.
- **Build:** AGP 9.3.1, Gradle 9.7.0, Kotlin 2.4.21, JDK 17, Compose BOM 2026.09.00.

The main app is `com.mithaq.app`. The separately listed network companion is `com.mithaq.network`. These package IDs are the initial project identity and must be finalized before the first Play Console registration; do not change them after publishing.

## Repository layout

```text
app/                         Main Mithaq application; no INTERNET permission
network-contract/            Small AIDL contract shared by both APKs
network-companion/            Separate app/UID owning future bounded network operations
unauthorized-probe/           Test-only app signed differently to verify Binder denial
docs/                         Product baseline, Phase-0 report, ADRs and test matrix
scripts/                      Manifest/APK audits, invariants and emulator boundary-test runner
.github/workflows/ci.yml      Unit tests, lint, APK builds, emulator boundary tests, tag releases
```

## Phase-0 behavior

The main app and network companion are separate Android packages and therefore have separate application UIDs. The companion exposes only a narrow AIDL Binder contract and protects its exported service with a signature-level permission. The main app declares package visibility only for the release and debug companion package IDs so Android 11+ package filtering does not block cross-package service discovery/binding; it does not request `QUERY_ALL_PACKAGES`, `INTERNET` or `ACCESS_NETWORK_STATE`. Both app manifests remove AndroidX Core's legacy `DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION` merge entries: that compatibility permission is only needed below API 33, while Mithaq's minSdk is 35. The packaged-APK audit remains exact and does not permit unexpected library permissions.

The main app also includes a diagnostic-only service declared with `android:isolatedProcess="true"`. Instrumentation tests bind through `Context.bindIsolatedService()` using a unique instance name, verify the service metadata before binding, then verify that it runs under a distinct isolated UID, cannot read a marker file in the host app's private storage, and has no Internet permission. Binder tests report `onNullBinding`/`onBindingDied` instead of collapsing all connection failures into an opaque timeout. This is a boundary probe only; it is not the Gemma inference worker.

A test-only `unauthorized-probe/` application is signed during CI with a newly generated, unrelated certificate. It attempts to bind the companion and the emulator job must observe an Android permission denial. This negative test is essential: the same-signer positive test alone would not prove that untrusted applications are excluded.

No actual model is bundled or downloaded. No search, page fetch or HTTP proxy has been implemented. The first Phase-0 checkpoint is intended to validate the Android package/process boundary and establish build/release automation.

## Build locally

The project currently uses a pinned Gradle installation provisioned by GitHub Actions. A Gradle Wrapper binary could not be included in this authoring environment, so this checkpoint intentionally does not include a broken `gradlew` script or a placeholder wrapper JAR.

Install JDK 17 and Gradle 9.7.0. Install stable Android 16 / API 36 and Build Tools 36.0.0, then install the Android 17 API 37.0 platform package. Note the required `.0` suffix: `platforms;android-37` does not exist.

```bash
sdkmanager --channel=0 "platform-tools" "platforms;android-36" "build-tools;36.0.0"
sdkmanager --channel=3 "platforms;android-37.0"
test -s "$ANDROID_HOME/platforms/android-37.0/android.jar"
```

The Android modules declare `compileSdk` with `release(37) { minorApiLevel = 0 }`, matching the installed `android-37.0` package. The earlier CI correction fixed the channel but still used the nonexistent integer-only package identifier; checkpoint 0.1.2 fixes the actual package name and makes the minor API explicit. `targetSdk` remains 36. Then run from the repository root:

```bash
gradle --version
gradle clean testDebugUnitTest lintDebug assembleDebug
```

Build both APKs:

```bash
gradle :app:assembleDebug :network-companion:assembleDebug
```

Build all emulator APKs before starting the emulator, including the instrumentation APK:

```bash
gradle --no-daemon --max-workers=2 \
  :app:assembleDebug \
  :app:assembleDebugAndroidTest \
  :network-companion:assembleDebug \
  :unauthorized-probe:assembleDebug
```

With an API 36 emulator running and Package Manager ready, invoke the same boundary-test helper used by CI:

```bash
bash scripts/run_emulator_boundary_tests.sh \
  app/build/outputs/apk/debug/app-debug.apk \
  network-companion/build/outputs/apk/debug/network-companion-debug.apk \
  unauthorized-probe/build/outputs/apk/debug/unauthorized-probe-debug.apk \
  app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk \
  ./emulator-diagnostics
```

If you prefer the standard Gradle Wrapper locally, once Gradle 9.7.0 is installed run:

```bash
gradle wrapper --gradle-version 9.7.0 --distribution-type bin
```

Review the generated wrapper files and commit them to the repository. The GitHub Actions pipeline does not depend on a wrapper because it provisions the exact Gradle version directly.

## GitHub upload workflow (manual repository setup)

1. Create an empty GitHub repository for Mithaq (recommended name: `mithaq-android`).
2. Extract the ZIP so that `README.md`, `settings.gradle.kts`, `app/`, `network-companion/`, and `.github/` are at the repository root. Do not upload the outer ZIP folder as an extra nested directory.
3. Commit and push the extracted contents to the `main` branch.
4. Open **Actions**. The `Mithaq Android CI` workflow runs on push and pull request.
5. The build job runs Python source-manifest/project audits plus a fake-ADB regression test for the emulator helper, Kotlin unit tests, Android lint, builds both debug APKs, and audits permissions in the packaged APKs. A second job first builds all four required APKs (main, companion, separately signed attacker probe and instrumentation APK) before starting an API 36 emulator. The emulator helper waits for both Android boot completion and Package Manager responsiveness, installs the prebuilt APKs with `adb install --no-streaming`, discovers and runs AndroidJUnitRunner directly with `adb shell am instrument`, and then runs the separately signed unauthorized-caller test. It does not run Gradle while the emulator is active. On failure it uploads logcat, system properties, Package Manager, ActivityManager, memory, installed-package and instrumentation diagnostics.
6. Download debug APKs from the workflow's artifacts. The main and companion debug packages are signed using the runner's debug certificate and are for testing only.

## Publishing APKs to GitHub Releases

The release workflow runs only for strict semantic-version tags such as `v0.1.0`, and only after the CI build and emulator tests pass. The signed-build job has read-only repository permission and exposes signing secrets only to its Gradle build step. A separate publish job receives `contents: write`, downloads the prepared assets, and creates the release; it never receives the signing key. Before upload, CI checks packaged permissions and verifies that the main and companion APKs have the same signing-certificate SHA-256 digest. It uploads:

- `Mithaq-<version>.apk`
- `Mithaq-Network-Companion-<version>.apk`
- corresponding `.aab` files for future Play Console submission
- `SHA256SUMS.txt`

### Required GitHub repository secrets

Create a dedicated Android release keystore. Use the **same keystore and signing certificate for both APKs** because the companion's Binder permission is signature-protected. Keep the key outside the repository and include no key material in the ZIP.

Example command (run locally; keep the keystore outside the repository):

```bash
keytool -genkeypair -v \
  -keystore mithaq-release.jks \
  -alias mithaq-release \
  -keyalg RSA -keysize 4096 -validity 10000
```

Base64-encode the resulting file (Linux):

```bash
base64 -w 0 mithaq-release.jks
```

Add these repository secrets under **Settings → Secrets and variables → Actions**:

| Secret | Value |
|---|---|
| `MITHAQ_KEYSTORE_BASE64` | Base64 output of the release keystore |
| `MITHAQ_KEYSTORE_PASSWORD` | Keystore password |
| `MITHAQ_KEY_ALIAS` | `mithaq-release` or the alias you chose |
| `MITHAQ_KEY_PASSWORD` | Private-key password |

Never commit the keystore, passwords, signing properties or decoded keystore. The signed-build job fails closed if any signing secret is missing. Configure Actions to allow the workflow's `GITHUB_TOKEN` to create releases; only the isolated release-publish job requests `contents: write`.

### Mandatory Google Play signing configuration

The certificate that signs an AAB upload is **not necessarily** the certificate on the APK that Google Play installs. Play signs generated distribution APKs with the Play app-signing key. Since Mithaq's cross-package Binder permission is signature-protected, the installed main and companion APKs must have the same Play app-signing certificate. Before either separate Play listing is rolled out to open testing or production, configure both listings to use the same app-signing key (Google documents “Use the same key as another app in this developer account” or providing a copy of the key). Verify the fingerprints of Play-generated APKs and rerun the Binder test on a device. See [`docs/RELEASE_SIGNING.md`](docs/RELEASE_SIGNING.md). The current one-key GitHub workflow is a Phase-0 bootstrap; review upload-key/app-signing-key separation before production.

After a successful CI push on `main`, create and push a version tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The Release job uses the tag as `versionName` and the workflow run number as the monotonically increasing Android `versionCode`. Re-run the release tag only after correcting a failed workflow; do not reuse a published version code for a different binary.

## Current status and limitations

Read [`docs/PHASE_0_CHECKPOINT.md`](docs/PHASE_0_CHECKPOINT.md) and the ADRs before extending the architecture. The authoring environment does not have the Android SDK or Gradle, so all build claims are based on hosted GitHub Actions. Checkpoint 0.1.1 corrected the Android 17 SDK channel; checkpoint 0.1.2 corrected the exact `platforms;android-37.0` package name and explicit API minor level. Checkpoint 0.1.3 removed AndroidX Core's unused API<33 dynamic-receiver compatibility permission from both APK manifests while keeping the packaged permission audit strict. Checkpoint 0.1.4 added package-visibility declarations and improved Binder test diagnostics. The 16 November 2026 hosted run reached `BUILD SUCCESSFUL` for debug APK assembly, and the emulator job's `build-test` prerequisite passed, but the emulator failed before instrumentation at `adb install` with `Failure calling service package: Broken pipe (32)`. Checkpoint 0.1.5 moves all four emulator APK builds before emulator startup, avoids Gradle execution while the emulator is active, checks Package Manager readiness, uses `adb install --no-streaming`, and runs the same AndroidJUnitRunner suite directly with `adb shell am instrument`. The next hosted run must confirm whether this resolves the emulator install failure; the Binder boundary tests remain pending.

Phase 0 is not complete until GitHub CI and the emulator boundary tests pass. LiteRT-LM descriptor loading, EmbeddingGemma Android integration, PromptGuard ONNX parity, strict SSRF fetching, image inference, 8 GB device qualification and release signing remain open engineering gates.
