#!/usr/bin/env python3
"""Fail CI if the Android package/permission boundary drifts."""
from pathlib import Path
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ANDROID = "{http://schemas.android.com/apk/res/android}"
TOOLS = "{http://schemas.android.com/tools}"
DYNAMIC_RECEIVER_PERMISSION = "${applicationId}.DYNAMIC_RECEIVER_NOT_EXPORTED_PERMISSION"
COMPANION_PERMISSION = "com.mithaq.network.permission.BIND_COMPANION"


def attr(node, name, default=None):
    return node.attrib.get(ANDROID + name, default)


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


main = load("app/src/main/AndroidManifest.xml")
companion = load("network-companion/src/main/AndroidManifest.xml")
attacker = load("unauthorized-probe/src/main/AndroidManifest.xml")


def uses_permissions(manifest):
    # Ignore explicit manifest-merger removal nodes; they remove library entries
    # and do not represent permissions requested by the packaged application.
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


def has_active_node(manifest, tag: str, permission_name: str) -> bool:
    return any(
        node.attrib.get(ANDROID + "name") == permission_name
        and node.attrib.get(TOOLS + "node") != "remove"
        for node in manifest.findall(tag)
    )


main_permissions = uses_permissions(main)
companion_permissions = uses_permissions(companion)
attacker_permissions = uses_permissions(attacker)

visible_packages = {
    node.attrib.get(ANDROID + "name")
    for node in main.findall("queries/package")
}
expected_visible_packages = {"com.mithaq.network", "com.mithaq.network.debug"}
if not expected_visible_packages.issubset(visible_packages):
    fail(
        "Main app must declare package visibility only for the release and debug "
        f"network companion IDs; missing {expected_visible_packages - visible_packages}"
    )
if any("QUERY_ALL_PACKAGES" in value for value in main_permissions):
    fail("Main app must not use QUERY_ALL_PACKAGES")

android_test_manifest = ROOT / "app/src/androidTest/AndroidManifest.xml"
if not android_test_manifest.is_file():
    fail("Missing instrumentation manifest with explicit package-visibility declarations")
test_manifest = load("app/src/androidTest/AndroidManifest.xml")
test_visible_packages = {
    node.attrib.get(ANDROID + "name")
    for node in test_manifest.findall("queries/package")
}
if not expected_visible_packages.issubset(test_visible_packages):
    fail("Instrumentation package must declare visibility for the network companion")

for label, manifest in (("main", main), ("companion", companion)):
    for tag in ("permission", "uses-permission"):
        if not has_merger_removal(manifest, tag, DYNAMIC_RECEIVER_PERMISSION):
            fail(
                f"{label} manifest must remove AndroidX Core's unused API<33 "
                f"dynamic-receiver {tag} entry for minSdk 35"
            )
        if has_active_node(manifest, tag, DYNAMIC_RECEIVER_PERMISSION):
            fail(f"{label} manifest must not keep an active {tag} for the legacy receiver permission")

if main_permissions != {COMPANION_PERMISSION}:
    fail(f"Main app permissions must be exactly the companion signature permission; found {main_permissions}")

expected_companion_permissions = {
    "android.permission.INTERNET",
    "android.permission.ACCESS_NETWORK_STATE",
}
if companion_permissions != expected_companion_permissions:
    fail(f"Companion permissions must be exactly {expected_companion_permissions}; found {companion_permissions}")

if attacker_permissions:
    fail(f"Unauthorized probe must request no permissions; found {attacker_permissions}")

query_names = {
    node.attrib.get(ANDROID + "name")
    for node in attacker.findall("queries/package")
}
if "com.mithaq.network.debug" not in query_names:
    fail("Attacker probe must declare package visibility for the debug companion")

for label, manifest in (("main", main), ("companion", companion), ("attacker", attacker)):
    app = manifest.find("application")
    if app is None:
        fail(f"{label} manifest has no application element")
    if attr(app, "allowBackup") != "false":
        fail(f"{label} application must set allowBackup=false")
    if attr(app, "usesCleartextTraffic") != "false":
        fail(f"{label} application must set usesCleartextTraffic=false")

    if attr(manifest, "sharedUserId"):
        fail(f"{label} manifest must not declare sharedUserId")

# Every exported service must be explicitly protected. Launcher activities are allowed.
for label, manifest in (("main", main), ("companion", companion), ("attacker", attacker)):
    app = manifest.find("application")
    for component in list(app):
        if attr(component, "exported") != "true":
            continue
        tag = component.tag.rsplit("}", 1)[-1]
        if tag == "activity":
            actions = {
                a.attrib.get(ANDROID + "name")
                for f in component.findall("intent-filter")
                for a in f.findall("action")
            }
            categories = {
                c.attrib.get(ANDROID + "name")
                for f in component.findall("intent-filter")
                for c in f.findall("category")
            }
            if "android.intent.action.MAIN" not in actions or "android.intent.category.LAUNCHER" not in categories:
                fail(f"Unexpected exported {label} activity: {attr(component, 'name')}")
        elif tag == "service":
            if attr(component, "permission") != COMPANION_PERMISSION:
                fail(f"Exported {label} service is not signature protected: {attr(component, 'name')}")
        else:
            fail(f"Unexpected exported {label} component: {tag} {attr(component, 'name')}")

isolated = [
    service
    for service in main.find("application").findall("service")
    if attr(service, "name") == ".probe.IsolatedInferenceProbeService"
]
if len(isolated) != 1:
    fail("Exactly one Phase-0 inference isolation probe service must be declared")
if attr(isolated[0], "isolatedProcess") != "true":
    fail("Inference probe must use android:isolatedProcess=true")
if attr(isolated[0], "exported") != "false":
    fail("Inference probe must be non-exported")

permissions = {permission.attrib.get(ANDROID + "name"): permission for permission in companion.findall("permission")}
permission = permissions.get(COMPANION_PERMISSION)
if permission is None or attr(permission, "protectionLevel") != "signature":
    fail("Companion Binder permission must be declared with protectionLevel=signature")

print("Manifest boundary audit: PASS")
print("- Main app: only the companion signature permission; no network or legacy AndroidX receiver permissions")
print("- Companion: only INTERNET and ACCESS_NETWORK_STATE; no legacy AndroidX receiver permission")
print("- Companion Binder: exported only behind the signature permission")
print("- Unauthorized probe: no permissions and no companion signature grant")
print("- Inference probe: isolatedProcess=true, exported=false")
