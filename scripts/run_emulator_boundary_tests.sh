#!/usr/bin/env bash
# Installs prebuilt APKs and runs Phase-0 instrumentation in isolated invocations.
# Each instrumentation case gets a fresh process and dedicated crash diagnostics.
set -Eeuo pipefail

if [[ "$#" -eq 0 ]]; then
  MAIN_APK="${MITHAQ_MAIN_APK:-app/build/outputs/apk/debug/app-debug.apk}"
  COMPANION_APK="${MITHAQ_COMPANION_APK:-network-companion/build/outputs/apk/debug/network-companion-debug.apk}"
  ATTACKER_APK="${MITHAQ_ATTACKER_APK:-unauthorized-probe/build/outputs/apk/debug/unauthorized-probe-debug.apk}"
  ANDROID_TEST_APK="${MITHAQ_ANDROID_TEST_APK:-app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk}"
  DIAGNOSTICS_DIR="${MITHAQ_DIAGNOSTICS_DIR:-${RUNNER_TEMP:-${TMPDIR:-/tmp}}/mithaq-emulator-diagnostics}"
elif [[ "$#" -eq 5 ]]; then
  MAIN_APK="$1"
  COMPANION_APK="$2"
  ATTACKER_APK="$3"
  ANDROID_TEST_APK="$4"
  DIAGNOSTICS_DIR="$5"
else
  echo "Usage: $0 [<main.apk> <companion.apk> <attacker.apk> <androidTest.apk> <diagnostics-dir>]" >&2
  exit 64
fi
mkdir -p "$DIAGNOSTICS_DIR"

MAIN_PACKAGE="com.mithaq.app.debug"
TEST_PACKAGE="com.mithaq.app.debug.test"
COMPANION_PACKAGE="com.mithaq.network.debug"
ATTACKER_PACKAGE="com.mithaq.attackerprobe.debug"
INSTRUMENTATION_CLASS="androidx.test.runner.AndroidJUnitRunner"

capture_diagnostics() {
  local suffix="${1:-failure}"
  mkdir -p "$DIAGNOSTICS_DIR"
  adb logcat -d -b all -v threadtime > "$DIAGNOSTICS_DIR/logcat-${suffix}.txt" 2>&1 || true
  adb logcat -d -b crash -v threadtime > "$DIAGNOSTICS_DIR/crash-buffer-${suffix}.txt" 2>&1 || true
  adb shell getprop > "$DIAGNOSTICS_DIR/getprop-${suffix}.txt" 2>&1 || true
  adb shell dumpsys package "$MAIN_PACKAGE" > "$DIAGNOSTICS_DIR/package-main-${suffix}.txt" 2>&1 || true
  adb shell dumpsys package "$TEST_PACKAGE" > "$DIAGNOSTICS_DIR/package-test-${suffix}.txt" 2>&1 || true
  adb shell dumpsys package "$COMPANION_PACKAGE" > "$DIAGNOSTICS_DIR/package-companion-${suffix}.txt" 2>&1 || true
  adb shell dumpsys activity services > "$DIAGNOSTICS_DIR/services-${suffix}.txt" 2>&1 || true
  adb shell dumpsys activity processes > "$DIAGNOSTICS_DIR/processes-${suffix}.txt" 2>&1 || true
  adb shell dumpsys activity exit-info "$MAIN_PACKAGE" > "$DIAGNOSTICS_DIR/exit-info-main-${suffix}.txt" 2>&1 || true
  adb shell dumpsys activity exit-info "$TEST_PACKAGE" > "$DIAGNOSTICS_DIR/exit-info-test-${suffix}.txt" 2>&1 || true
  adb shell dumpsys meminfo > "$DIAGNOSTICS_DIR/meminfo-${suffix}.txt" 2>&1 || true
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
  local label="$1" apk="$2" test_only="$3" attempt output
  local -a install_args=(--no-streaming)
  [[ "$test_only" == "true" ]] && install_args+=(-t)
  [[ -s "$apk" ]] || { echo "Missing or empty $label APK: $apk" >&2; return 1; }

  for attempt in 1 2 3; do
    output="$DIAGNOSTICS_DIR/install-${label}-attempt-${attempt}.txt"
    echo "Installing $label APK (attempt $attempt/3): $apk"
    if adb install "${install_args[@]}" "$apk" > "$output" 2>&1; then
      cat "$output"
      return 0
    fi
    cat "$output" >&2
    if grep -Eqi 'Broken pipe|Failure calling service package|device offline|device not found' "$output"; then
      if ! package_manager_healthy; then recover_emulator_once || return 1; else sleep 4; fi
      continue
    fi
    echo "Non-transient APK installation failure for $label; not retrying." >&2
    return 1
  done
  echo "Could not install $label APK after bounded retries." >&2
  return 1
}

for apk in "$MAIN_APK" "$COMPANION_APK" "$ATTACKER_APK" "$ANDROID_TEST_APK"; do
  [[ -s "$apk" ]] || { echo "Required emulator APK missing or empty: $apk" >&2; exit 1; }
done

wait_for_boot
if ! wait_for_package_manager; then recover_emulator_once; fi
install_apk companion "$COMPANION_APK" false
install_apk main "$MAIN_APK" false
install_apk attacker "$ATTACKER_APK" false
install_apk instrumentation "$ANDROID_TEST_APK" true

for package_name in "$MAIN_PACKAGE" "$COMPANION_PACKAGE" "$ATTACKER_PACKAGE" "$TEST_PACKAGE"; do
  if ! adb shell pm path "$package_name" | grep -q '^package:'; then
    echo "Package Manager does not report expected installed package: $package_name" >&2
    exit 1
  fi
done

instrumentation_listing="$DIAGNOSTICS_DIR/available-instrumentation.txt"
adb shell pm list instrumentation | tr -d '\r' > "$instrumentation_listing"
instrumentation_component="$(awk -v target="$MAIN_PACKAGE" -v runner="$INSTRUMENTATION_CLASS" \
  'index($0, "target=" target ")") && index($0, "/" runner) { sub(/^instrumentation:/, "", $1); print $1; exit }' \
  "$instrumentation_listing")"
if [[ -z "$instrumentation_component" ]]; then
  echo "Could not discover AndroidJUnitRunner targeting $MAIN_PACKAGE." >&2
  cat "$instrumentation_listing" >&2
  exit 1
fi

run_instrumentation_case() {
  local label="$1" class_spec="$2" expected_summary="$3"
  local output="$DIAGNOSTICS_DIR/instrumentation-${label}.txt"
  local crash_log="$DIAGNOSTICS_DIR/instrumentation-${label}-crash-buffer.txt"
  local full_log="$DIAGNOSTICS_DIR/instrumentation-${label}-logcat.txt"
  local exit_info="$DIAGNOSTICS_DIR/instrumentation-${label}-exit-info.txt"
  local command_status=0

  echo "Running instrumentation case '$label': $class_spec"
  adb logcat -c || true
  set +e
  adb shell am instrument -w -r -e class "$class_spec" "$instrumentation_component" > "$output" 2>&1
  command_status=$?
  set -e

  # Capture the crash buffer immediately; it is much more useful than the shell
  # command's generic 'Process crashed' line and must be saved before next case.
  adb logcat -d -b crash -v threadtime > "$crash_log" 2>&1 || true
  adb logcat -d -b all -v threadtime > "$full_log" 2>&1 || true
  adb shell dumpsys activity exit-info "$MAIN_PACKAGE" > "$exit_info" 2>&1 || true
  cat "$output"

  if [[ "$command_status" -ne 0 ]] || grep -Eqi 'shortMsg=Process crashed|INSTRUMENTATION_FAILED|FAILURES!!!|INSTRUMENTATION_STATUS_CODE: -2' "$output"; then
    echo "Instrumentation process failed in case '$label' (adb exit=$command_status)." >&2
    echo "Relevant crash diagnostics:" >&2
    grep -E -A 12 -B 4 'FATAL EXCEPTION|Fatal signal|am_crash|Process:|Caused by:|AndroidRuntime|Instrumentation.*crash' \
      "$crash_log" "$full_log" >&2 || true
    cat "$exit_info" >&2 || true
    return 1
  fi
  if ! grep -Fq "$expected_summary" "$output" || ! grep -Eq 'INSTRUMENTATION_CODE: -1' "$output"; then
    echo "Instrumentation case '$label' did not produce expected success summary '$expected_summary'." >&2
    cat "$output" >&2
    return 1
  fi
  echo "Instrumentation case '$label': PASS"
}

run_instrumentation_case smoke \
  "com.mithaq.app.InstrumentationSmokeTest" "OK (1 test)"
run_instrumentation_case isolated \
  "com.mithaq.app.BoundaryInstrumentedTest#isolatedWorkerHasSeparateUidAndCannotReadHostPrivateFile" "OK (1 test)"
run_instrumentation_case companion \
  "com.mithaq.app.BoundaryInstrumentedTest#companionBinderIsReachableOnlyThroughTheSignedCompanionContract" "OK (1 test)"

# The separately signed app must not obtain the signature permission.
adb logcat -c
adb shell am start -W -n \
  "$ATTACKER_PACKAGE/com.mithaq.attackerprobe.AttackerProbeActivity"
probe_log="$DIAGNOSTICS_DIR/attacker-probe-log.txt"
denied=0
for attempt in $(seq 1 15); do
  adb logcat -d -s MithaqPermissionProbe:I > "$probe_log" 2>&1 || true
  if grep -q 'MITHAQ_PERMISSION_PROBE_DENIED' "$probe_log"; then denied=1; break; fi
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
echo "- Instrumentation smoke, isolated-worker and companion Binder tests: PASS" | tee -a "$DIAGNOSTICS_DIR/summary.txt"
echo "- Differently signed attacker denied by signature permission: PASS" | tee -a "$DIAGNOSTICS_DIR/summary.txt"
