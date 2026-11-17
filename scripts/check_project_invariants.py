#!/usr/bin/env python3
"""Phase-0 project, SDK, CI and host-only testing invariants."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]


def fail(message: str) -> None:
    print(f"PROJECT CHECK FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)

root_build = (ROOT / "build.gradle.kts").read_text()
workflow = (ROOT / ".github/workflows/ci.yml").read_text()
gradle_props = (ROOT / "gradle.properties").read_text()
settings = (ROOT / "settings.gradle.kts").read_text()

for expected in (
    'id("com.android.application") version "9.3.1"',
    'id("com.android.library") version "9.3.1"',
    'id("org.jetbrains.kotlin.android") version "2.4.21"',
    'id("org.jetbrains.kotlin.plugin.compose") version "2.4.21"',
    'id("org.jetbrains.kotlin.jvm") version "2.4.21"',
):
    if expected not in root_build:
        fail(f"Expected pinned build plugin missing: {expected}")

expected_modules = {'":app"', '":network-contract"', '":network-companion"', '":integration-tests"'}
if not all(module in settings for module in expected_modules):
    fail(f"settings.gradle.kts must include modules: {sorted(expected_modules)}")
if '"unauthorized-probe"' in settings:
    fail("Retired unauthorized-probe APK module must not remain included")

cleanup_script = ROOT / "scripts/cleanup_retired_emulator_assets.py"
if not cleanup_script.is_file():
    fail("Allowlisted legacy emulator-asset cleanup script is required")
if workflow.count("scripts/cleanup_retired_emulator_assets.py") != 2:
    fail("Both CI jobs must purge legacy ZIP-overlay emulator assets before building")
if workflow.count("scripts/test_cleanup_retired_emulator_assets.py") != 2:
    fail("Both CI jobs must run host-side cleanup safety tests")
cleanup_refs = [i for i in range(len(workflow)) if workflow.startswith("scripts/cleanup_retired_emulator_assets.py", i)]
if len(cleanup_refs) != 2 or cleanup_refs[0] > workflow.index("name: Run manifest and project audits") or cleanup_refs[1] > workflow.index("name: Build signed APKs and Android App Bundles"):
    fail("Legacy-asset cleanup must run before build-test audits and release builds")
if not (ROOT / "scripts/test_cleanup_retired_emulator_assets.py").is_file():
    fail("Host-side legacy cleanup safety tests are required")
if workflow.count("gradle-version: '9.7.0'") != 2:
    fail("Both CI build jobs must install the pinned Gradle 9.7.0 toolchain")
if workflow.count('sdkmanager --channel=3 "platforms;android-37.0"') != 2:
    fail("Both CI build jobs must install the exact Android 37.0 compile platform")
if workflow.count('sdkmanager --channel=0 "build-tools;36.0.0"') != 2:
    fail("Both CI build jobs must install Build Tools 36.0.0")
if 'platforms;android-37"' in workflow:
    fail("The nonexistent integer-only API 37 package must not be requested")
for obsolete in ("platform-tools", '"platforms;android-36"', "android-emulator-runner"):
    if obsolete in workflow:
        fail(f"Emulator-only SDK/action dependency must be removed from CI: {obsolete}")

for key, value in (("android.builtInKotlin", "false"), ("android.newDsl", "false")):
    if f"{key}={value}" not in gradle_props:
        fail(f"Expected explicit AGP/Kotlin migration setting missing: {key}={value}")

for module, application_id in (("app", "com.mithaq.app"), ("network-companion", "com.mithaq.network")):
    build = (ROOT / module / "build.gradle.kts").read_text()
    if f'applicationId = "{application_id}"' not in build:
        fail(f"Unexpected applicationId for {module}")
    if "minSdk = 35" not in build or "targetSdk = 36" not in build:
        fail(f"SDK matrix drift in {module}")
    if 'implementation(project(":network-contract"))' not in build:
        fail(f"{module} must depend on the shared network-contract module")

for module in ("app", "network-companion", "network-contract"):
    build = (ROOT / module / "build.gradle.kts").read_text()
    if "version = release(37)" not in build or "minorApiLevel = 0" not in build:
        fail(f"{module} must compile against explicit Android API 37.0")

main_manifest = (ROOT / "app/src/main/AndroidManifest.xml").read_text()
if '<queries>' not in main_manifest or 'com.mithaq.network.debug' not in main_manifest or 'com.mithaq.network"' not in main_manifest:
    fail("Main app must declare narrow package visibility for release/debug companion IDs")
if 'android:name="android.permission.QUERY_ALL_PACKAGES"' in main_manifest:
    fail("Main app must not request broad QUERY_ALL_PACKAGES visibility")

# User-directed CI policy: JVM unit + host-side integration checks only.
for path in (
    ROOT / "app/src/androidTest",
    ROOT / "unauthorized-probe",
    ROOT / "scripts/run_emulator_boundary_tests.sh",
    ROOT / "scripts/test_emulator_boundary_runner.py",
):
    if path.exists():
        fail(f"Retired emulator/E2E test asset must be removed: {path.relative_to(ROOT)}")
for obsolete in (
    "ReactiveCircus/android-emulator-runner",
    "connectedDebugAndroidTest",
    "assembleDebugAndroidTest",
    "androidTest",
    "unauthorized-probe",
    "scripts/run_emulator_boundary_tests.sh",
    "test_emulator_boundary_runner.py",
):
    if obsolete in workflow:
        fail(f"CI must not include emulator/E2E testing: {obsolete}")
if ":integration-tests:test" not in workflow:
    fail("CI must execute the host-JVM integration test module")
if ":app:testDebugUnitTest" not in workflow or ":network-companion:testDebugUnitTest" not in workflow:
    fail("CI must execute Android module JVM unit tests")
if "instrumented-boundary-tests" in workflow:
    fail("Separate emulator instrumentation job must be removed entirely")
if "needs: build-test" not in workflow:
    fail("Release build must depend on the single test/build job only")

app_build = (ROOT / "app/build.gradle.kts").read_text()
if "testInstrumentationRunner" in app_build or "androidTestImplementation" in app_build:
    fail("App Gradle configuration must not retain Android instrumentation dependencies")
if (ROOT / "integration-tests/build.gradle.kts").is_file() is False:
    fail("Host-side integration-tests Gradle module is required")

all_docs = "\n".join(p.read_text(errors="ignore") for p in (ROOT / "docs").rglob("*.md"))
if "English only" not in all_docs:
    fail("Docs must state English-only v0 language policy")
if "Arabic" not in all_docs or "French is excluded" not in all_docs:
    fail("Docs must preserve future Arabic and explicit French exclusion")

print("Project invariants: PASS")
print("- Mithaq package identities, SDK matrix and pinned toolchain are consistent")
print("- Main and companion share the narrow AIDL contract")
print("- CI executes JVM unit tests, host integration tests, lint and APK builds")
print("- No emulator runner, Android instrumentation, E2E stage or attacker test APK remains")
print("- Release workflow depends on the tested build job")
print("- English-only v0 / future Arabic / no French policy is preserved")
