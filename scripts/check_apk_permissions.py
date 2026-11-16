#!/usr/bin/env python3
"""Inspect packaged APK permission manifests using Android build-tools aapt."""
from pathlib import Path
import os
import re
import subprocess
import sys

ANDROID_SDK_ROOT = Path(os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME", ""))
BUILD_TOOLS_VERSION = "36.0.0"
AAPT = ANDROID_SDK_ROOT / "build-tools" / BUILD_TOOLS_VERSION / "aapt"


def fail(message: str) -> None:
    print(f"APK PERMISSION CHECK FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)


def package_permissions(apk: Path) -> tuple[str, set[str]]:
    if not apk.is_file():
        fail(f"APK not found: {apk}")
    if not AAPT.is_file():
        fail(f"aapt not found at {AAPT}; install Android Build Tools {BUILD_TOOLS_VERSION}")
    result = subprocess.run(
        [str(AAPT), "dump", "permissions", str(apk)],
        check=False,
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        fail(f"aapt failed for {apk}: {result.stderr.strip()}")

    package_match = re.search(r"^package:\s+([^\s]+)", result.stdout, re.MULTILINE)
    if not package_match:
        fail(f"Could not parse package name from aapt output for {apk}")
    permissions = set(re.findall(r"uses-permission(?:-sdk-\d+)?:\s+name='([^']+)'", result.stdout))
    return package_match.group(1), permissions


if len(sys.argv) != 4 or sys.argv[3] not in {"debug", "release"}:
    fail("Usage: check_apk_permissions.py <main.apk> <companion.apk> <debug|release>")

variant = sys.argv[3]
main_package_expected = "com.mithaq.app.debug" if variant == "debug" else "com.mithaq.app"
companion_package_expected = "com.mithaq.network.debug" if variant == "debug" else "com.mithaq.network"

main_package, main_permissions = package_permissions(Path(sys.argv[1]))
companion_package, companion_permissions = package_permissions(Path(sys.argv[2]))

if main_package != main_package_expected:
    fail(f"Unexpected main {variant} package id: {main_package}")
if companion_package != companion_package_expected:
    fail(f"Unexpected companion {variant} package id: {companion_package}")
if main_permissions != {"com.mithaq.network.permission.BIND_COMPANION"}:
    fail(f"Main APK permissions are not least-privilege: {main_permissions}")
if companion_permissions != {
    "android.permission.INTERNET",
    "android.permission.ACCESS_NETWORK_STATE",
}:
    fail(f"Companion APK permissions are not least-privilege: {companion_permissions}")

print(f"Packaged {variant} APK permission audit: PASS")
print(f"- {main_package}: {sorted(main_permissions)}")
print(f"- {companion_package}: {sorted(companion_permissions)}")
