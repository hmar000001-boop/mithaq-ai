plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val attackerStoreFile = providers.environmentVariable("MITHAQ_ATTACKER_KEYSTORE_FILE").orNull
val attackerStorePassword = providers.environmentVariable("MITHAQ_ATTACKER_KEYSTORE_PASSWORD").orNull
val attackerKeyAlias = providers.environmentVariable("MITHAQ_ATTACKER_KEY_ALIAS").orNull
val attackerKeyPassword = providers.environmentVariable("MITHAQ_ATTACKER_KEY_PASSWORD").orNull
val hasAttackerSigning = listOf(
    attackerStoreFile,
    attackerStorePassword,
    attackerKeyAlias,
    attackerKeyPassword,
).all { !it.isNullOrBlank() }

android {
    namespace = "com.mithaq.attackerprobe"
    compileSdk = 37
    buildToolsVersion = "36.0.0"

    defaultConfig {
        applicationId = "com.mithaq.attackerprobe"
        minSdk = 35
        targetSdk = 36
        versionCode = 1
        versionName = "0.1.0-test"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    signingConfigs {
        if (hasAttackerSigning) {
            create("attacker") {
                storeFile = file(requireNotNull(attackerStoreFile))
                storePassword = requireNotNull(attackerStorePassword)
                keyAlias = requireNotNull(attackerKeyAlias)
                keyPassword = requireNotNull(attackerKeyPassword)
            }
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    buildTypes {
        debug {
            applicationIdSuffix = ".debug"
            if (hasAttackerSigning) {
                signingConfig = signingConfigs.getByName("attacker")
            }
        }
        release {
            isMinifyEnabled = false
        }
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(org.jetbrains.kotlin.gradle.dsl.JvmTarget.JVM_17)
    }
}

dependencies {
    testImplementation("junit:junit:4.13.2")
}
