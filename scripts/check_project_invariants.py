#!/usr/bin/env python3
"""Static Phase-0 checks for product identity and pinned build inputs."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]

def fail(message: str) -> None:
    print(f"PROJECT CHECK FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)

root_build = (ROOT / "build.gradle.kts").read_text()
workflow = (ROOT / ".github/workflows/ci.yml").read_text()
gradle_props = (ROOT / "gradle.properties").read_text()
for expected in (
    'id("com.android.application") version "9.3.1"',
    'id("com.android.library") version "9.3.1"',
    'id("org.jetbrains.kotlin.android") version "2.4.21"',
    'id("org.jetbrains.kotlin.plugin.compose") version "2.4.21"',
):
    if expected not in root_build:
        fail(f"Expected pinned build plugin missing: {expected}")

if workflow.count("gradle-version: '9.7.0'") != 3:
    fail("All three CI build jobs must install the pinned Gradle 9.7.0 toolchain")
if workflow.count('sdkmanager --channel=0 "platform-tools" "platforms;android-36" "build-tools;36.0.0"') != 3:
    fail("All CI jobs must install stable API 36 and Build Tools 36.0.0")
if workflow.count('sdkmanager --channel=3 "platforms;android-37.0"') != 3:
    fail("All CI jobs must install the exact Android 37.0 package from a preview-inclusive channel")
if workflow.count('test -s "$ANDROID_HOME/platforms/android-37.0/android.jar"') != 3:
    fail("All CI jobs must verify the Android 37.0 platform payload before Gradle starts")
if 'platforms;android-37"' in workflow:
    fail("The nonexistent integer-only API 37 package must not be requested")

for key, value in (("android.builtInKotlin", "false"), ("android.newDsl", "false")):
    if f"{key}={value}" not in gradle_props:
        fail(f"Expected explicit AGP/Kotlin migration setting missing: {key}={value}")

for module, application_id in (("app", "com.mithaq.app"), ("network-companion", "com.mithaq.network")):
    build = (ROOT / module / "build.gradle.kts").read_text()
    if f'applicationId = "{application_id}"' not in build:
        fail(f"Unexpected applicationId for {module}")
    if "minSdk = 35" not in build or "targetSdk = 36" not in build:
        fail(f"SDK matrix drift in {module}")

for module in ("app", "network-companion", "network-contract", "unauthorized-probe"):
    build = (ROOT / module / "build.gradle.kts").read_text()
    if "version = release(37)" not in build or "minorApiLevel = 0" not in build:
        fail(f"{module} must compile against explicit Android API 37.0")

main_manifest = (ROOT / "app/src/main/AndroidManifest.xml").read_text()
if '<queries>' not in main_manifest or 'com.mithaq.network.debug' not in main_manifest or 'com.mithaq.network"' not in main_manifest:
    fail("Main app must declare narrowly scoped package visibility for release/debug companion IDs")
if 'android:name="android.permission.QUERY_ALL_PACKAGES"' in main_manifest:
    fail("Main app must not request broad QUERY_ALL_PACKAGES visibility")

boundary_test = (ROOT / "app/src/androidTest/java/com/mithaq/app/BoundaryInstrumentedTest.kt").read_text()
if "bindIsolatedService(" not in boundary_test:
    fail("Isolated inference boundary test must use bindIsolatedService with an explicit instance name")
if "onNullBinding" not in boundary_test or "onBindingDied" not in boundary_test:
    fail("Binder boundary tests must report terminal ServiceConnection callbacks, not only time out")
if "SERVICE_CONNECTION_TIMEOUT_SECONDS = 30L" not in boundary_test:
    fail("Binder instrumentation timeout must allow cold-start headroom on hosted emulators")
if 'replace("-", "")' not in boundary_test or 'return "mithaq_phase0_$compactUuid"' not in boundary_test:
    fail("bindIsolatedService instanceName must remove UUID hyphens and use Android's allowed ASCII identifier characters")
if 'instanceName.matches(Regex("[A-Za-z0-9_.]+"))' not in boundary_test:
    fail("Isolated-service test must assert the instanceName character contract before calling Android")
smoke_test = ROOT / "app/src/androidTest/java/com/mithaq/app/InstrumentationSmokeTest.kt"
if not smoke_test.is_file() or "runnerStartsAndTargetContextIsAvailable" not in smoke_test.read_text():
    fail("A minimal AndroidJUnitRunner smoke test must run before the Binder tests")

# Emulator workload must be prebuilt before emulator launch. Gradle compilation
# used to run alongside Android's Package Manager and caused a flaky package
# service transport failure during adb install. The runtime helper installs
# prebuilt APKs and executes AndroidJUnitRunner directly through adb.
prebuild_marker = "name: Prebuild emulator APKs before starting the emulator"
emulator_marker = "uses: ReactiveCircus/android-emulator-runner@"
if prebuild_marker not in workflow or emulator_marker not in workflow:
    fail("Emulator APK prebuild and emulator-runner steps must both exist")
if workflow.index(prebuild_marker) > workflow.index(emulator_marker):
    fail("Emulator APKs must be built before the emulator is launched")
prebuild_section = workflow[workflow.index(prebuild_marker):workflow.index(emulator_marker)]
if ":app:assembleDebugAndroidTest" not in prebuild_section:
    fail("Instrumentation APK must be prebuilt before emulator startup")
# ReactiveCircus/android-emulator-runner@a421e438 parses its script input into
# independent single-line commands. A YAML literal/folded block with Bash\
# continuations is therefore unsafe: only the first line receives the arguments.
script_input = re.search(r"(?m)^\s+script: (.+)$", workflow)
if not script_input or script_input.group(1).strip() != "bash scripts/run_emulator_boundary_tests.sh":
    fail("Emulator action script must be one physical command invoking the helper with its default paths")
emulator_script = (ROOT / "scripts/run_emulator_boundary_tests.sh").read_text()
if 'if [[ "$#" -eq 0 ]]; then' not in emulator_script:
    fail("Emulator helper must support the zero-argument CI invocation")
if "gradle " in emulator_script:
    fail("Emulator runtime helper must not invoke Gradle while the emulator is running")
for required in (
    "wait_for_package_manager",
    "package_manager_healthy",
    "--no-streaming",
    "pm list instrumentation",
    "am instrument -w -r",
    "InstrumentationSmokeTest",
    "-crash-buffer.txt",
    "run_instrumentation_case smoke",
    "run_instrumentation_case isolated",
    "run_instrumentation_case companion",
    "dumpsys activity exit-info",
    "MITHAQ_PERMISSION_PROBE_DENIED",
    "capture_diagnostics final-failure",
):
    if required not in emulator_script:
        fail(f"Emulator boundary runner is missing required behavior: {required}")

all_docs = "\n".join(p.read_text(errors="ignore") for p in (ROOT / "docs").rglob("*.md"))
if "English only" not in all_docs:
    fail("Docs must state English-only v0 language policy")
if "Arabic" not in all_docs or "French is excluded" not in all_docs:
    fail("Docs must preserve future Arabic and explicit French exclusion")

print("Project invariants: PASS")
print("- Mithaq package identities and SDK matrix (API 37.0) are pinned")
print("- AGP 9.3.1 / Gradle 9.7.0 / Kotlin 2.4.21 compatibility pins are explicit")
print("- English-only v0 / future Arabic / no French recorded")
print("- Narrow package visibility and explicit isolated-service binding are enforced")
print("- Isolated-service instance names obey Android's documented ASCII character constraint")
print("- Instrumentation smoke test and per-case crash diagnostics are mandatory")
