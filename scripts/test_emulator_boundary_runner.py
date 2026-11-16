#!/usr/bin/env python3
"""Exercise the emulator runner shell helper against a deterministic mock adb."""
from pathlib import Path
import os
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_emulator_boundary_tests.sh"

MOCK_ADB = r'''#!/usr/bin/env python3
import os
from pathlib import Path
import sys

args = sys.argv[1:]
joined = " ".join(args)
state = Path(os.environ["MITHAQ_MOCK_ADB_STATE"])

if args == ["wait-for-device"]:
    raise SystemExit(0)
if args[:3] == ["shell", "getprop", "sys.boot_completed"]:
    print("1")
    raise SystemExit(0)
if args[:4] == ["shell", "cmd", "package", "list"]:
    print("package:com.android.settings")
    raise SystemExit(0)
if args and args[0] == "install":
    count = int(state.read_text()) + 1
    state.write_text(str(count))
    if os.environ.get("MITHAQ_MOCK_FAIL_FIRST_INSTALL") == "1" and count == 1:
        print("cmd: Failure calling service package: Broken pipe (32)", file=sys.stderr)
        raise SystemExit(1)
    print("Success")
    raise SystemExit(0)
if args[:3] == ["shell", "pm", "path"]:
    print("package:/data/app/mock/base.apk")
    raise SystemExit(0)
if args[:3] == ["shell", "pm", "list"] and len(args) >= 4 and args[3] == "instrumentation":
    print("instrumentation:com.mithaq.app.debug.test/androidx.test.runner.AndroidJUnitRunner (target=com.mithaq.app.debug)")
    raise SystemExit(0)
if args[:3] == ["shell", "am", "instrument"]:
    print("INSTRUMENTATION_RESULT: stream=")
    print("Time: 0.12")
    print("OK (2 tests)")
    print("INSTRUMENTATION_CODE: -1")
    raise SystemExit(0)
if args[:2] == ["logcat", "-c"]:
    raise SystemExit(0)
if args[:4] == ["shell", "am", "start", "-W"]:
    print("Status: ok")
    raise SystemExit(0)
if args[:4] == ["logcat", "-d", "-s", "MithaqPermissionProbe:I"]:
    print("I/MithaqPermissionProbe: MITHAQ_PERMISSION_PROBE_DENIED")
    raise SystemExit(0)
if args[:2] == ["logcat", "-d"] or args[:2] == ["shell", "dumpsys"] or args[:2] == ["shell", "getprop"] or args[:3] == ["shell", "pm", "list"]:
    raise SystemExit(0)
print("MOCK ADB UNHANDLED: " + joined, file=sys.stderr)
raise SystemExit(2)
'''


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="mithaq-emulator-runner-test-") as temp:
        temp_path = Path(temp)
        bin_dir = temp_path / "bin"
        apk_dir = temp_path / "apks"
        diagnostics = temp_path / "diagnostics"
        bin_dir.mkdir()
        apk_dir.mkdir()
        adb = bin_dir / "adb"
        adb.write_text(MOCK_ADB)
        adb.chmod(0o755)
        sleep = bin_dir / "sleep"
        sleep.write_text("#!/usr/bin/env sh\nexit 0\n")
        sleep.chmod(0o755)

        apks = []
        for name in ("main.apk", "companion.apk", "attacker.apk", "androidTest.apk"):
            path = apk_dir / name
            path.write_bytes(b"mock-apk-content")
            apks.append(str(path))

        state = temp_path / "install-count"
        state.write_text("0")
        env = os.environ.copy()
        env.update(
            {
                "PATH": f"{bin_dir}:{env.get('PATH', '')}",
                "MITHAQ_MOCK_ADB_STATE": str(state),
                "MITHAQ_MOCK_FAIL_FIRST_INSTALL": "1",
            }
        )
        result = subprocess.run(
            ["bash", str(RUNNER), *apks, str(diagnostics)],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )
        if result.returncode != 0:
            print(result.stdout, file=sys.stderr)
            print(result.stderr, file=sys.stderr)
            return 1
        if "Mithaq Phase-0 emulator boundary checks: PASS" not in result.stdout:
            print("Mock emulator run omitted success marker", file=sys.stderr)
            print(result.stdout, file=sys.stderr)
            return 1
        if not (diagnostics / "install-companion-attempt-2.txt").is_file():
            print("Mock run did not exercise the bounded Broken pipe retry", file=sys.stderr)
            return 1
        if not (diagnostics / "summary.txt").is_file():
            print("Mock run did not create boundary summary", file=sys.stderr)
            return 1

    print("Emulator boundary runner mock test: PASS (including bounded Broken pipe retry)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
