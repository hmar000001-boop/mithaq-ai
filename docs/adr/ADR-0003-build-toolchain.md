# ADR-0003 — Android Build Toolchain

- **Status:** Accepted for Phase 0; revisit AGP built-in Kotlin migration before upgrading
- **Decision date:** 16 November 2026

## Pinned versions

| Component | Version | Reason |
|---|---:|---|
| Android Gradle Plugin | 9.3.1 | Chosen within Kotlin 2.4.21's documented fully-supported AGP range (through 9.3.1); AGP 9.3 supports compile API 37 |
| Gradle | 9.7.0 | At Kotlin 2.4.21's documented maximum fully-supported Gradle version; meets AGP 9.3's 9.5.0 minimum |
| Kotlin Gradle Plugin | 2.4.21 | Stable Kotlin patch release |
| Compose compiler plugin | 2.4.21 | Matched to Kotlin compiler plugin |
| Compose BOM | 2026.09.00 | Stable Compose BOM |
| Activity Compose | 1.13.0 | Stable Activity Compose release |
| JDK | 17 | AGP 9.3 supported minimum/default |
| Compile SDK | 37 | Maximum supported by AGP 9.3 |
| Target SDK | 36 | Google Play new-app/update target requirement from 31 August 2026 |
| Min SDK | 35 | Agreed Android 15+ product baseline |

## Compatibility reasoning

The Kotlin Gradle Plugin 2.4.21 compatibility table documents full support through Gradle 9.7.0 and AGP 9.3.1. AGP 9.3 requires Gradle 9.5.0 or later, JDK 17, and supports compile API 37. The selected pair is therefore inside both published compatibility ranges. We intentionally do not use AGP 9.5.1 with KGP 2.4.21: that combination is outside Kotlin's documented fully-supported AGP range.

AGP 9 enables built-in Kotlin. This project explicitly opts out during Phase 0 so that KGP 2.4.21 and the matching Compose compiler plugin are explicitly pinned. `android.builtInKotlin=false` and `android.newDsl=false` are transitional settings; their compatibility must be rechecked before upgrades.

## Wrapper caveat

The project ZIP does not include a fake or incomplete Gradle Wrapper JAR. CI installs Gradle 9.7.0 using `gradle/actions/setup-gradle`. A standard wrapper can be generated with Gradle 9.7.0 and committed when the owner has a local Gradle installation.


## SDK package channel policy

The project uses `compileSdk = 37` because the selected Compose BOM `2026.09.00` requires API 37. At the time of this checkpoint, Android 17 / API 37 is distributed as a preview SDK package, while API 36 is available on the stable channel. The CI workflow therefore installs the packages in two explicit operations:

```bash
sdkmanager --channel=0 "platform-tools" "platforms;android-36" "build-tools;36.0.0"
sdkmanager --channel=3 "platforms;android-37"
```

Do not request API 37 from the default stable channel. The CI failure reported on 16 November 2026 was caused by doing exactly that; it occurred before Gradle was invoked. API 37 is used only for compilation. `targetSdk` remains 36 pending the next Play target-API requirement and runtime qualification. The preview SDK package may change while Android 17 remains preview; record SDK package revision in CI logs and re-run the full build/test matrix when it changes.
