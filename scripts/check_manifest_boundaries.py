#!/usr/bin/env python3
"""Static security audit for the production main-app/Network-Companion manifests."""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ANDROID = "{http://schemas.android.com/apk/res/android}"
TOOLS = "{http://schemas.android.com/tools}"
DYNAMIC_RECEIVER_PERMISSION = "${applicationId}.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION"
COMPANION_PERMISSION = "com.mithaq.network.permission.BIND_COMPANION"


def fail(message: str) -> None:
    print(f"BOUNDARY CHECK FAILED: {message}", file=sys.stderr)
    raise SystemExit(1)


def load(relative: str):
    path = ROOT / relative
    if not path.is_file():
        fail(f"Missing manifest: {relative}")
    try:
        return ET.parse(path).getroot()
    except ET.ParseError as exc:
        fail(f"Invalid XML in {relative}: {exc}")


def attr(node, name, default=None):
    return node.attrib.get(ANDROID + name, default)


def active_permissions(manifest):
    return {
        node.attrib.get(ANDROID + "name")
        for node in manifest.findall("uses-permission")
        if node.attrib.get(TOOLS + "node") != "remove"
    }


def has_merger_removal(manifest, tag: str, permission_name: str) -> bool:
    return any(
        node.attrib.get(ANDROID + "name") == permission_name
        and node.attrib.get(TOOLS + "node") == "remove"
        for node in manifest.findall(tag)
    )


main = load("app/src/main/AndroidManifest.xml")
companion = load("network-companion/src/main/AndroidManifest.xml")
main_app = main.find("application")
companion_app = companion.find("application")
if main_app is None or companion_app is None:
    fail("Both production manifests must contain an application element")

main_permissions = active_permissions(main)
companion_permissions = active_permissions(companion)
if main_permissions != {COMPANION_PERMISSION}:
    fail(f"Main app permissions must be exactly the companion signature permission; found {main_permissions}")
expected_companion_permissions = {
    "android.permission.INTERNET",
    "android.permission.ACCESS_NETWORK_STATE",
}
if companion_permissions != expected_companion_permissions:
    fail(f"Companion permissions must be exactly {expected_companion_permissions}; found {companion_permissions}")

visible_packages = {
    node.attrib.get(ANDROID + "name")
    for node in main.findall("queries/package")
}
expected_visible_packages = {"com.mithaq.network", "com.mithaq.network.debug"}
if visible_packages != expected_visible_packages:
    fail(f"Main app package visibility must be exactly {expected_visible_packages}; found {visible_packages}")
if any("QUERY_ALL_PACKAGES" in value for value in main_permissions):
    fail("Main app must not use QUERY_ALL_PACKAGES")

for label, manifest in (("main", main), ("companion", companion)):
    for tag in ("permission", "uses-permission"):
        if not has_merger_removal(manifest, tag, DYNAMIC_RECEIVER_PERMISSION):
            fail(f"{label} manifest must remove AndroidX Core's unused API<33 dynamic-receiver {tag} entry")

for label, manifest in (("main", main), ("companion", companion)):
    app = manifest.find("application")
    if attr(app, "allowBackup") != "false":
        fail(f"{label} application must set allowBackup=false")
    if attr(app, "usesCleartextTraffic") != "false":
        fail(f"{label} application must set usesCleartextTraffic=false")
    if attr(manifest, "sharedUserId"):
        fail(f"{label} manifest must not declare sharedUserId")

# The only exported service is the production companion endpoint, guarded by
# a signature permission. The main application currently exports no services.
main_services = main_app.findall("service")
if main_services:
    fail(f"Main app must not contain a diagnostic/test service: {[attr(s, 'name') for s in main_services]}")
companion_services = companion_app.findall("service")
if len(companion_services) != 1:
    fail(f"Companion must declare exactly one Binder service; found {len(companion_services)}")
service = companion_services[0]
if attr(service, "name") != ".NetworkCompanionService":
    fail(f"Unexpected companion service: {attr(service, 'name')}")
if attr(service, "exported") != "true" or attr(service, "permission") != COMPANION_PERMISSION:
    fail("Companion Binder service must be exported only behind the signature-level permission")

permission_nodes = {
    attr(permission, "name"): permission
    for permission in companion.findall("permission")
}
permission = permission_nodes.get(COMPANION_PERMISSION)
if permission is None or attr(permission, "protectionLevel") != "signature":
    fail("Companion Binder permission must be declared with protectionLevel=signature")

print("Manifest boundary audit: PASS")
print("- Main app: no network permissions; only the companion signature permission")
print("- Companion: only INTERNET and ACCESS_NETWORK_STATE")
print("- Cross-package Binder service: exported only behind signature protection")
print("- Package visibility: release/debug companion IDs only; no QUERY_ALL_PACKAGES")
print("- No test-only isolated process or attacker-probe components are shipped")
