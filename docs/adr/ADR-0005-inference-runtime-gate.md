# ADR-0005 — LiteRT-LM Descriptor Loading Is a Release Gate

- **Status:** Proposed / not proven
- **Decision date:** 16 November 2026

## Context

The published LiteRT-LM Android Kotlin guide demonstrates `EngineConfig(modelPath=...)`. Mithaq requires inference in an Android isolated process and does not permit falling back to the main app's ordinary same-UID process while retaining an isolation claim.

LiteRT-LM v0.19.1 includes a breaking C API 1.0.0 change. A custom JNI bridge must use the matching C headers and native libraries.

## Required proof

1. Verify Gemma artifact hash and open read-only FD in the main app.
2. Transfer only the FD to `android:isolatedProcess=true` service through Binder.
3. Duplicate/close descriptor safely in JNI and load Gemma through the selected LiteRT-LM native C API.
4. Verify runtime does not require unrestricted private path access or silently persist model data outside its allowed descriptors.
5. Verify streaming, cancellation, repeated load/unload, lock handling, process death and memory release.
6. Demonstrate worker UID isolation and no network permission on minimum API and reference devices.

## Failure handling

If this proof fails, stop implementation of generation-dependent features. Evaluate a separately installed inference companion package or a runtime with supported descriptor/isolated loading. Do not ship an ordinary-process fallback under an isolation claim.
