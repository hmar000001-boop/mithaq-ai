#!/usr/bin/env bash
# Installs prebuilt APKs and runs Phase-0 instrumentation without invoking Gradle
# while the emulator is running. This keeps Gradle's memory/CPU demand away from
# Android's system_server and Package Manager during APK installation.
set -Eeuo pipefail

if [[ "$#" -ne 5 ]]; then
  echo "Usage: $0 <main.apk> <companion.apk> <attacker.apk> <androidTest.apk> <diagnostics-dir>" >&2
  exit 64
fi

MAIN_APK="$1"
COMPANION_APK="$2"
ATTACKER_APK="$3"
ANDROID_TEST_APK="$4"
DIAGNOSTICS_DIR="$5"
mkdir -p "$DIAGNOSTICS_DIR"

capture_diagnostics() {
  local suffix="${1:-failure}"
  mkdir -p "$DIAGNOSTICS_DIR"
  adb logcat -d -b all -v threadtime > "$DIAGNOSTICS_DIR/logcat-${suffix}.txt" 2>&1 || true
  adb shell getprop > "$DIAGNOSTICS_DIR/getprop-${suffix}.txt" 2>&1 || true
  adb shell dumpsys package > "$DIAGNOSTICS_DIR/package-${suffix}.txt" 2>&1 || true
  adb shell dumpsys activity services > "$DIAGNOSTICS_DIR/services-${suffix}.txt" 2>&1 || true
  adb shell dumpsys meminfo > "$DIAGNOSTICS_DIR/meminfo-${suffix}.txt" 2>&1 || true
  adb shell pm list packages -3 > "$DIAGNOSTICS_DIR/third-party-packages-${suffix}.txt" 2>&1 || true
  adb shell pm list instrumentation > "$DIAGNOSTICS_DIR/instrumentation-${suffix}.txt" 2>&1 || true
}

on_exit() {
  local status=$?
  if [[ "$status" -ne 0 ]]; then
    echo "Boundary test runner failed (exit=$status); collecting emulator diagnostics." >&2
    capture_diagnostics final-failure
  fi
  exit "$status"
}
trap on_exit EXIT

wait_for_boot() {
  echo "Waiting for Android boot completion..."
  adb wait-for-device
  for attempt in $(seq 1 180); do
    local boot_completed
    boot_completed="$(adb shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)"
    if [[ "$boot_completed" == "1" ]]; then
      echo "Android reports sys.boot_completed=1."
      return 0
    fi
    sleep 2
  done
  echo "Timed out waiting for sys.boot_completed=1." >&2
  return 1
}

package_manager_healthy() {
  local response
  response="$(adb shell cmd package list packages 2>&1 | tr -d '\r' || true)"
  [[ "$response" == *"package:"* ]] &&
    ! grep -Eqi 'Failure calling service package|Broken pipe|Exception' <<< "$response"
}

wait_for_package_manager() {
  echo "Waiting for Package Manager Binder service..."
  for attempt in $(seq 1 45); do
    if package_manager_healthy; then
      echo "Package Manager is responsive."
      return 0
    fi
    sleep 2
  done
  echo "Package Manager did not become responsive after boot." >&2
  return 1
}

recover_emulator_once() {
  if [[ "${MITHAQ_EMULATOR_REBOOTED:-0}" == "1" ]]; then
    echo "Emulator reboot recovery already used; refusing an unbounded retry." >&2
    return 1
  fi
  export MITHAQ_EMULATOR_REBOOTED=1
  echo "Rebooting emulator once because Package Manager is unavailable..." >&2
  capture_diagnostics before-reboot
  adb reboot || true
  wait_for_boot
  wait_for_package_manager
}

install_apk() {
  local label="$1"
  local apk="$2"
  local test_only="$3"
  local attempt
  local output
  local -a install_args=(--no-streaming)
  if [[ "$test_only" == "true" ]]; then
    install_args+=(-t)
  fi

  if [[ ! -s "$apk" ]]; then
    echo "Missing or empty $label APK: $apk" >&2
    return 1
  fi

  for attempt in 1 2 3; do
    output="$DIAGNOSTICS_DIR/install-${label}-attempt-${attempt}.txt"
    echo "Installing $label APK (attempt $attempt/3): $apk"
    if adb install "${install_args[@]}" "$apk" > "$output" 2>&1; then
      cat "$output"
      return 0
    fi
    cat "$output" >&2

    if grep -Eqi 'Broken pipe|Failure calling service package|device offline|device not found' "$output"; then
      if ! package_manager_healthy; then
        recover_emulator_once || return 1
      else
        # A transient shell/Package Manager binder interruption can clear without
        # reboot. Retry only this recognized transport/service failure.
        sleep 4
      fi
      continue
    fi

    echo "Non-transient APK installation failure for $label; not retrying." >&2
    return 1
  done

  echo "Could not install $label APK after bounded retries." >&2
  return 1
}

for apk in "$MAIN_APK" "$COMPANION_APK" "$ATTACKER_APK" "$ANDROID_TEST_APK"; do
  if [[ ! -s "$apk" ]]; then
    echo "Required emulator APK missing or empty: $apk" >&2
    exit 1
  fi
done

wait_for_boot
if ! wait_for_package_manager; then
  recover_emulator_once
fi

# Companion and main app are signed by the same CI debug identity. The attacker
# APK uses the distinct ephemeral key created earlier in the workflow.
install_apk companion "$COMPANION_APK" false
install_apk main "$MAIN_APK" false
install_apk attacker "$ATTACKER_APK" false
install_apk instrumentation "$ANDROID_TEST_APK" true

for package_name in \
  com.mithaq.app.debug \
  com.mithaq.network.debug \
  com.mithaq.attackerprobe.debug; do
  if ! adb shell pm path "$package_name" | grep -q '^package:'; then
    echo "Package Manager does not report expected installed package: $package_name" >&2
    exit 1
  fi
done

instrumentation_listing="$DIAGNOSTICS_DIR/available-instrumentation.txt"
adb shell pm list instrumentation | tr -d '\r' > "$instrumentation_listing"
instrumentation_component="$(awk '/target=com\.mithaq\.app\.debug\)/ { sub(/^instrumentation:/, "", $1); print $1; exit }' "$instrumentation_listing")"
if [[ -z "$instrumentation_component" ]]; then
  echo "Could not discover instrumentation runner targeting com.mithaq.app.debug." >&2
  cat "$instrumentation_listing" >&2
  exit 1
fi

echo "Running Phase-0 AndroidJUnitRunner: $instrumentation_component"
instrumentation_output="$DIAGNOSTICS_DIR/instrumentation-output.txt"
if ! adb shell am instrument -w -r \
    -e class com.mithaq.app.BoundaryInstrumentedTest \
    "$instrumentation_component" > "$instrumentation_output" 2>&1; then
  cat "$instrumentation_output" >&2
  exit 1
fi
cat "$instrumentation_output"
if ! grep -Eq 'OK \([0-9]+ tests?\)' "$instrumentation_output" || \
   grep -Eq 'FAILURES!!!|INSTRUMENTATION_FAILED|MITHAQ_' "$instrumentation_output"; then
  echo "Instrumentation output does not contain a clean JUnit success summary." >&2
  exit 1
fi

# The separately signed app must not obtain the signature permission. A thrown
# SecurityException is the expected, positive denial signal; missing services
# and a false bind result are not accepted as evidence of protection.
adb logcat -c
adb shell am start -W -n \
  com.mithaq.attackerprobe.debug/com.mithaq.attackerprobe.AttackerProbeActivity
probe_log="$DIAGNOSTICS_DIR/attacker-probe-log.txt"
denied=0
for attempt in $(seq 1 15); do
  adb logcat -d -s MithaqPermissionProbe:I > "$probe_log" 2>&1 || true
  if grep -q 'MITHAQ_PERMISSION_PROBE_DENIED' "$probe_log"; then
    denied=1
    break
  fi
  if grep -Eq 'MITHAQ_PERMISSION_PROBE_FAILED|MITHAQ_PERMISSION_PROBE_INVALID' "$probe_log"; then
    cat "$probe_log" >&2
    exit 1
  fi
  sleep 1
done
if [[ "$denied" -ne 1 ]]; then
  cat "$probe_log" >&2
  echo "Differently signed app was not explicitly denied by the companion signature permission." >&2
  exit 1
fi

echo "Mithaq Phase-0 emulator boundary checks: PASS" | tee "$DIAGNOSTICS_DIR/summary.txt"
echo "- API 36 emulator boot and Package Manager health: PASS" | tee -a "$DIAGNOSTICS_DIR/summary.txt"
echo "- Companion and main debug APK installation: PASS" | tee -a "$DIAGNOSTICS_DIR/summary.txt"
echo "- Isolated-process and companion Binder instrumentation: PASS" | tee -a "$DIAGNOSTICS_DIR/summary.txt"
echo "- Differently signed attacker denied by signature permission: PASS" | tee -a "$DIAGNOSTICS_DIR/summary.txt"
