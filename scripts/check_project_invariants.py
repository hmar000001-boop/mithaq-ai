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

for key, value in (("android.builtInKotlin", "false"), ("android.newDsl", "false")):
    if f"{key}={value}" not in gradle_props:
        fail(f"Expected explicit AGP/Kotlin migration setting missing: {key}={value}")

for module, application_id in (("app", "com.mithaq.app"), ("network-companion", "com.mithaq.network")):
    build = (ROOT / module / "build.gradle.kts").read_text()
    if f'applicationId = "{application_id}"' not in build:
        fail(f"Unexpected applicationId for {module}")
    if "minSdk = 35" not in build or "targetSdk = 36" not in build or "compileSdk = 37" not in build:
        fail(f"SDK matrix drift in {module}")

all_docs = "\n".join(p.read_text(errors="ignore") for p in (ROOT / "docs").rglob("*.md"))
if "English only" not in all_docs:
    fail("Docs must state English-only v0 language policy")
if "Arabic" not in all_docs or "French is excluded" not in all_docs:
    fail("Docs must preserve future Arabic and explicit French exclusion")

print("Project invariants: PASS")
print("- Mithaq package identities and SDK matrix are pinned")
print("- AGP 9.3.1 / Gradle 9.7.0 / Kotlin 2.4.21 compatibility pins are explicit")
print("- English-only v0 / future Arabic / no French recorded")
