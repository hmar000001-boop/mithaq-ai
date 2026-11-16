# ADR-0009 — Keep the Android emulator action script input to one physical line

**Status:** Accepted for Phase 0 CI
**Date:** 16 November 2026

## Context

Checkpoint 0.1.5 invoked the emulator helper with a YAML multiline script and Bash backslash continuations. The hosted run launched the emulator and then exited 64 with the helper's usage text, before running any ADB operation.

The exact `ReactiveCircus/android-emulator-runner` revision pinned by `.github/workflows/ci.yml` imports `parseScript()`. At the pinned commit, `parseScript()` trims the input, splits it on physical newline characters, trims each line and returns each nonempty line as a separate script command. The action executes each returned script independently through `sh -c`. Bash line continuation is therefore not preserved across the action's script parser boundary.

## Decision

1. The action's `script:` input must be exactly one physical command: `bash scripts/run_emulator_boundary_tests.sh`.
2. The helper supports zero-argument CI mode and derives APK paths from the repository root and the diagnostics directory from `RUNNER_TEMP`.
3. Five-argument mode remains available for local debugging and manual use.
4. The fake-ADB regression test exercises the zero-argument CI path.
5. The project invariant checker rejects multiline action script input for this step.

## Consequences

- No shell continuation or multi-line conditional syntax is passed through the action's line parser.
- All emulator orchestration remains in a version-controlled Bash file, where normal Bash syntax works.
- Future changes to the emulator runner invocation must preserve the one-line contract unless a separate script-file handoff is used.
- This fixes the observed exit-64 invocation error, but does not establish emulator or Binder success.

## References

- Exact pinned action parser: https://raw.githubusercontent.com/ReactiveCircus/android-emulator-runner/a421e43855164a8197daf9d8d40fe71c6996bb0d/src/script-parser.ts
- Action runner executing each parsed script separately: https://github.com/ReactiveCircus/android-emulator-runner/blob/main/src/main.ts
