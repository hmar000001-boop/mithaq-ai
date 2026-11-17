# Mithaq — Android Project (Phase 0)

Mithaq is a native Kotlin Android personal AI workspace. This repository is the Phase-0 implementation foundation, not a feature-complete product release.

## Product baseline

- **Product name:** Mithaq
- **v0 language:** English only; English is the default.
- **Future language:** Arabic is planned, but is not a supported v0 language.
- **French:** explicitly excluded.
- **Android:** min API 35 (Android 15), target API 36, compile API 37.0.
- **Device qualification target:** 8 GB RAM minimum qualification target; 12 GB recommended. No device is declared supported until model/runtime and thermal qualification passes.
- **Build:** AGP 9.3.1, Gradle 9.7.0, Kotlin 2.4.21, JDK 17, Compose BOM 2026.09.00.

The main app is `com.mithaq.app`. The separately listed Network Companion is `com.mithaq.network`. These package IDs must be finalized before the first Play Console registration and must not change after publishing.

## Repository layout

```text
app/                         Main Mithaq Android application; no INTERNET permission
network-contract/            Narrow AIDL contract shared by both Android packages
network-companion/           Separate app/UID for future bounded network operations
integration-tests/           Host-JVM integration checks for manifests, AIDL and CI policy
docs/                         Product baseline, Phase-0 checkpoint, ADRs and test matrix
scripts/                      Manifest/APK audits, project invariants and action-pin checks
.github/workflows/ci.yml      JVM unit/integration tests, lint, APK builds and tag releases
```

## Implemented Phase-0 foundation

The main app and Network Companion are separate Android packages and therefore have separate application UIDs. The companion exposes a narrow AIDL Binder contract and protects its exported service with a signature-level permission. The main app declares package visibility only for the release and debug companion package IDs; it does not request `QUERY_ALL_PACKAGES`, `INTERNET` or `ACCESS_NETWORK_STATE`. Both application manifests remove AndroidX Core's legacy `DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION` merge entries because Mithaq's minimum SDK is 35 and that compatibility permission is not required on the supported platform range. Source and packaged-APK permission audits remain strict.

The repository intentionally contains **no Android instrumentation tests, no emulator test job, no E2E-on-emulator stage and no test-only attacker APK or isolated-process probe service**. The repeated emulator failures were consuming the Phase-0 cycle without providing reliable signal. Those assets and their workflow stage have been removed rather than left disabled or optional.

CI now runs:

1. JVM unit tests from the `app`, `network-contract` and `network-companion` modules.
2. Host-JVM integration tests from `integration-tests`, which verify the main/companion manifest permission split, signature-protected companion service declaration, shared AIDL/service method contract, package visibility and the absence of emulator/instrumentation stages.
3. Static manifest, project-invariant and GitHub Actions pin audits.
4. Android lint, debug APK builds and an AAPT inspection of the packaged APK permission sets.

These host-side tests do **not** simulate Android's Binder kernel, real cross-UID authorization, `isolatedProcess`, Keystore, SAF or runtime service lifecycle. No such runtime behavior is claimed as proven by the CI suite. Platform-specific security properties remain explicitly unverified until a separate device-qualification activity is commissioned; they are not a reason to reintroduce emulator E2E into CI.

No model is bundled or downloaded yet. Search, page fetching, general HTTP proxying, encrypted persistence and production inference are not implemented in this Phase-0 foundation.

## Build locally

The project uses a pinned Gradle installation provisioned by GitHub Actions. A Gradle Wrapper binary is not included because a verified wrapper JAR was unavailable in the authoring environment; no placeholder wrapper is provided.

Install JDK 17 and Gradle 9.7.0. Install Android Build Tools 36.0.0 and the Android 17 API 37.0 compile platform. The API 37 package identifier includes the `.0` suffix.

```bash
sdkmanager --channel=0 "build-tools;36.0.0"
sdkmanager --channel=3 "platforms;android-37.0"
test -s "$ANDROID_HOME/platforms/android-37.0/android.jar"
```

Then run from the repository root:

```bash
gradle --version
gradle --no-daemon clean \
  :app:testDebugUnitTest \
  :network-contract:testDebugUnitTest \
  :network-companion:testDebugUnitTest \
  :integration-tests:test \
  :app:lintDebug \
  :network-companion:lintDebug \
  :app:assembleDebug \
  :network-companion:assembleDebug
```

Both debug APKs are produced at:

- `app/build/outputs/apk/debug/app-debug.apk`
- `network-companion/build/outputs/apk/debug/network-companion-debug.apk`

The CI job runs the APK permission audit after assembly. No emulator, Android platform-tools or instrumentation APK is required.

If you prefer the standard Gradle Wrapper locally, after installing Gradle 9.7.0 run:

```bash
gradle wrapper --gradle-version 9.7.0 --distribution-type bin
```

Review and commit the generated wrapper files. GitHub Actions provisions the exact Gradle version directly and does not depend on a wrapper.

## Updating an existing GitHub repository with a project ZIP

**Important: extracting a ZIP over an existing repository does not delete files that are absent from the new ZIP.** This was the cause of the follow-up failure after checkpoint 0.1.8: the 0.1.8 archive did not contain `app/src/androidTest`, but that directory was still tracked in the existing GitHub repository, so it remained in the next checkout and the invariant checker correctly rejected it.

Checkpoint 0.1.9 includes an allowlisted migration script. Both CI jobs execute `scripts/cleanup_retired_emulator_assets.py` immediately after checkout and before audits/builds, then run its four host-side safety tests. It removes only `app/src/androidTest`, `unauthorized-probe`, `scripts/run_emulator_boundary_tests.sh` and `scripts/test_emulator_boundary_runner.py`. This keeps the build checkout free of retired emulator assets even when ZIP updates are overlaid onto an older repository. The project invariant still checks that those paths are absent after cleanup.

To permanently remove the old tracked files from your repository (recommended), extract the ZIP into your local clone and run once:

```bash
python3 scripts/cleanup_retired_emulator_assets.py
git add -A
git status --short
git commit -m "Remove retired emulator test assets"
git push
```

Review `git status --short` and confirm that it shows deletions only for the retired emulator assets before committing. You can also delete the same four paths directly in the GitHub web interface. The CI cleanup remains as a safe compatibility measure for future ZIP-overlay updates.

## GitHub upload and CI workflow

1. Create an empty GitHub repository for Mithaq (recommended name: `mithaq-android`).
2. Extract the project ZIP so `README.md`, `settings.gradle.kts`, `app/`, `network-companion/`, `integration-tests/` and `.github/` are at the repository root.
3. Commit and push the extracted contents to `main`.
4. Open **Actions**. `Mithaq Android CI` runs on pushes and pull requests.
5. The single CI validation/build job runs source audits, JVM unit tests, host-JVM integration tests, lint, both debug APK builds and the packaged permission audit. It uploads APKs and test/lint reports as workflow artifacts.
6. Download the main and companion debug APKs from the workflow artifacts. Debug builds are for development only.

There is no emulator creation, emulator boot, `adb install`, `connectedAndroidTest`, `AndroidJUnitRunner`, instrumentation APK, or E2E device stage in this workflow.

## Publishing APKs to GitHub Releases

The release workflow runs only for strict semantic-version tags such as `v0.1.0`, and only after the unit/integration/build job passes. The signed-build job has read-only repository permission and exposes signing secrets only to its Gradle build step. A separate publish job receives `contents: write`, downloads the prepared assets and creates the GitHub Release; it never receives the signing key. Before upload, CI checks packaged permissions and verifies that the main and companion APKs have the same signing-certificate SHA-256 digest. It uploads:

- `Mithaq-<version>.apk`
- `Mithaq-Network-Companion-<version>.apk`
- corresponding `.aab` files for future Play Console submission
- `SHA256SUMS.txt`

### Required GitHub repository secrets

Create a dedicated Android release keystore. Use the **same keystore and signing certificate for both APKs** because the companion's Binder permission is signature-protected. Keep the key outside the repository; no key material is included in project ZIPs.

Example command (run locally; keep the keystore outside the repository):

```bash
keytool -genkeypair -v \
  -keystore mithaq-release.jks \
  -alias mithaq-release \
  -keyalg RSA -keysize 4096 -validity 10000
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

The certificate that signs an AAB upload is not necessarily the certificate on the APK that Google Play installs. Play signs generated distribution APKs with the Play app-signing key. Since Mithaq's cross-package Binder permission is signature-protected, the installed main and companion APKs must have the same Play app-signing certificate. Before either separate Play listing is rolled out to testing or production, configure both listings to use the same app-signing key. Verify the fingerprints of Play-generated APKs as part of distribution qualification. See [`docs/RELEASE_SIGNING.md`](docs/RELEASE_SIGNING.md).

After a successful CI push on `main`, create and push a version tag:

```bash
git tag v0.1.0
git push origin v0.1.0
```

The Release job uses the tag as `versionName` and the workflow run number as the monotonically increasing Android `versionCode`. Do not reuse a published version code for a different binary.

## Current status and limitations

Read [`docs/PHASE_0_CHECKPOINT.md`](docs/PHASE_0_CHECKPOINT.md), [`docs/PHASE_0_TEST_MATRIX.md`](docs/PHASE_0_TEST_MATRIX.md) and the ADRs before extending the architecture. Checkpoint 0.1.8 removed the unstable emulator E2E stage, its instrumentation suite, attacker-probe APK, isolated-process test probe and emulator orchestration scripts. Checkpoint 0.1.9 fixes stale tracked files left behind by ZIP-overlay uploads. CI is now deliberately limited to JVM unit tests, host-side integration checks, static audits, lint, APK assembly and packaged permission inspection. The previous hosted runs did reach successful APK assembly and all four APK installations before AndroidJUnitRunner crashed; that runtime test stage is retired, not reported as passed.

Phase 0 still requires the normal hosted GitHub Actions run to pass the new host-only pipeline. LiteRT-LM descriptor loading, EmbeddingGemma Android integration, PromptGuard ONNX parity, strict SSRF fetching, image inference, actual runtime process-isolation qualification, 8 GB device qualification and release signing remain separate engineering gates.
