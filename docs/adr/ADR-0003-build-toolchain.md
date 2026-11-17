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
| Compile SDK | 37.0 | Maximum supported by AGP 9.3; explicit minor API level 0 |
| Target SDK | 36 | Google Play new-app/update target requirement from 31 August 2026 |
| Min SDK | 35 | Agreed Android 15+ product baseline |

## Compatibility reasoning

The Kotlin Gradle Plugin 2.4.21 compatibility table documents full support through Gradle 9.7.0 and AGP 9.3.1. AGP 9.3 requires Gradle 9.5.0 or later, JDK 17, and supports compile API 37. The selected pair is therefore inside both published compatibility ranges. We intentionally do not use AGP 9.5.1 with KGP 2.4.21: that combination is outside Kotlin's documented fully-supported AGP range.

AGP 9 enables built-in Kotlin. This project explicitly opts out during Phase 0 so that KGP 2.4.21 and the matching Compose compiler plugin are explicitly pinned. `android.builtInKotlin=false` and `android.newDsl=false` are transitional settings; their compatibility must be rechecked before upgrades.

## Wrapper caveat

The project ZIP does not include a fake or incomplete Gradle Wrapper JAR. CI installs Gradle 9.7.0 using `gradle/actions/setup-gradle`. A standard wrapper can be generated with Gradle 9.7.0 and committed when the owner has a local Gradle installation.


## SDK package identity and minor API policy

Android 37 is published using a major/minor SDK package identity. The exact SDK package is `platforms;android-37.0`; `platforms;android-37` does not exist. The earlier Phase 0.1.1 workflow corrected the preview channel but retained the wrong package identifier, which explains the second failed run on 16 November 2026.

All Android modules therefore use the expanded AGP DSL and pin the minor API explicitly:

```kotlin
compileSdk {
    version = release(37) {
        minorApiLevel = 0
    }
}
```

CI installs the package from a channel that includes preview packages and verifies the platform payload before Gradle starts:

```bash
sdkmanager --channel=3 "platforms;android-37.0"
test -s "$ANDROID_HOME/platforms/android-37.0/android.jar"
```

This avoids confusing the API level number with the SDK package identifier and ensures local builds and CI compile against the same API 37.0 surface. API 36 remains the target SDK baseline for Phase 0; CI does not create an emulator or require platform-tools. Record the installed `source.properties` revision in CI logs and rerun the build/test matrix if the selected platform package changes.
