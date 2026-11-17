package com.mithaq.integration

import java.io.File
import javax.xml.parsers.DocumentBuilderFactory
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import org.w3c.dom.Element
import org.w3c.dom.Node

/**
 * Host-JVM integration checks for the source-level contract shared by the two
 * Android packages. These deliberately do not emulate Android Binder, UIDs,
 * services, Keystore or process isolation.
 */
class HostIntegrationContractTest {
    private val root: File by lazy {
        File(requireNotNull(System.getProperty("mithaq.projectRoot")) {
            "mithaq.projectRoot must be set by the Gradle integration-tests task"
        })
    }

    @Test
    fun mainAndCompanionRetainStrictlySeparatedPermissions() {
        val main = parse("app/src/main/AndroidManifest.xml")
        val companion = parse("network-companion/src/main/AndroidManifest.xml")

        assertEquals(
            setOf(COMPANION_PERMISSION),
            directChildren(main, "uses-permission")
                .filterNot { attr(it, TOOLS_NS, "node") == "remove" }
                .map { attr(it, ANDROID_NS, "name") }
                .toSet(),
        )
        assertEquals(
            setOf("android.permission.INTERNET", "android.permission.ACCESS_NETWORK_STATE"),
            directChildren(companion, "uses-permission")
                .filterNot { attr(it, TOOLS_NS, "node") == "remove" }
                .map { attr(it, ANDROID_NS, "name") }
                .toSet(),
        )
        assertFalse(
            directChildren(main, "uses-permission").any {
                attr(it, ANDROID_NS, "name") == "android.permission.INTERNET"
            },
        )
    }

    @Test
    fun companionBinderServiceIsExportedOnlyBehindSignaturePermission() {
        val companion = parse("network-companion/src/main/AndroidManifest.xml")
        val app = directChildren(companion, "application").single()
        val services = directChildren(app, "service")
        assertEquals(1, services.size)

        val service = services.single()
        assertEquals(".NetworkCompanionService", attr(service, ANDROID_NS, "name"))
        assertEquals("true", attr(service, ANDROID_NS, "exported"))
        assertEquals(COMPANION_PERMISSION, attr(service, ANDROID_NS, "permission"))

        val permission = directChildren(companion, "permission").single {
            attr(it, ANDROID_NS, "name") == COMPANION_PERMISSION
        }
        assertEquals("signature", attr(permission, ANDROID_NS, "protectionLevel"))
    }

    @Test
    fun bothAndroidPackagesCompileAgainstTheSameNarrowAidlContract() {
        val appGradle = read("app/build.gradle.kts")
        val companionGradle = read("network-companion/build.gradle.kts")
        assertTrue(appGradle.contains("implementation(project(\":network-contract\"))"))
        assertTrue(companionGradle.contains("implementation(project(\":network-contract\"))"))

        val aidl = read("network-contract/src/main/aidl/com/mithaq/contract/INetworkCompanion.aidl")
        val methods = Regex("\\b(?:int|String)\\s+(\\w+)\\s*\\(")
            .findAll(aidl)
            .map { it.groupValues[1] }
            .toSet()
        assertEquals(setOf("getProtocolVersion", "getServiceUid", "echoChallenge"), methods)

        val service = read("network-companion/src/main/java/com/mithaq/network/NetworkCompanionService.kt")
        assertTrue(service.contains("INetworkCompanion.Stub()"))
        val implemented = Regex("override fun (\\w+)\\s*\\(")
            .findAll(service)
            .map { it.groupValues[1] }
            .toSet()
        assertTrue(implemented.containsAll(methods))
        assertTrue(service.contains("CompanionProtocolVersion.VALUE"))
        assertTrue(read("network-companion/src/main/java/com/mithaq/network/CompanionProtocolVersion.kt").contains("const val VALUE = 1"))
    }

    @Test
    fun mainAppOnlyQueriesTheKnownCompanionPackages() {
        val main = parse("app/src/main/AndroidManifest.xml")
        val queries = directChildren(main, "queries").single()
        val packages = directChildren(queries, "package")
            .map { attr(it, ANDROID_NS, "name") }
            .toSet()
        assertEquals(setOf("com.mithaq.network", "com.mithaq.network.debug"), packages)
    }

    @Test
    fun ciUsesOnlyHostJvmUnitAndIntegrationTestsWithoutAnEmulatorStage() {
        val workflow = read(".github/workflows/ci.yml")
        listOf(
            "ReactiveCircus/android-emulator-runner",
            "connectedDebugAndroidTest",
            "assembleDebugAndroidTest",
            "androidTest",
            "unauthorized-probe",
            "scripts/run_emulator_boundary_tests.sh",
        ).forEach { forbidden ->
            assertFalse("CI must not contain emulator/E2E stage marker: $forbidden", workflow.contains(forbidden))
        }
        assertTrue(workflow.contains(":integration-tests:test"))
        assertTrue(workflow.contains(":app:testDebugUnitTest"))
        assertTrue(workflow.contains(":network-companion:testDebugUnitTest"))
        assertTrue(workflow.contains("needs: build-test"))
        assertEquals(2, Regex("scripts/cleanup_retired_emulator_assets\\.py").findAll(workflow).count())
        assertEquals(2, Regex("scripts/test_cleanup_retired_emulator_assets\\.py").findAll(workflow).count())
        val cleanup = read("scripts/cleanup_retired_emulator_assets.py")
        val cleanupTests = read("scripts/test_cleanup_retired_emulator_assets.py")
        assertTrue(cleanupTests.contains("test_refuses_to_follow_a_symlinked_parent"))
        assertTrue(cleanupTests.contains("test_unlinks_a_final_component_symlink_without_deleting_its_target"))
        listOf(
            "app/src/androidTest",
            "unauthorized-probe",
            "scripts/run_emulator_boundary_tests.sh",
            "scripts/test_emulator_boundary_runner.py",
        ).forEach { assertTrue("Legacy cleanup allowlist missing $it", cleanup.contains(it)) }
        assertFalse(File(root, "app/src/androidTest").exists())
        assertFalse(File(root, "unauthorized-probe").exists())
    }

    private fun parse(relativePath: String): Element {
        val factory = DocumentBuilderFactory.newInstance().apply {
            isNamespaceAware = true
            setFeature("http://apache.org/xml/features/disallow-doctype-decl", true)
            setFeature("http://xml.org/sax/features/external-general-entities", false)
            setFeature("http://xml.org/sax/features/external-parameter-entities", false)
        }
        return factory.newDocumentBuilder().parse(File(root, relativePath)).documentElement
    }

    private fun read(relativePath: String): String = File(root, relativePath).readText()

    private fun directChildren(parent: Node, localName: String): List<Element> {
        val result = mutableListOf<Element>()
        val nodes = parent.childNodes
        for (index in 0 until nodes.length) {
            val node = nodes.item(index)
            if (node is Element && node.localName == localName) result += node
        }
        return result
    }

    private fun attr(element: Element, namespace: String, localName: String): String =
        element.getAttributeNS(namespace, localName)

    private companion object {
        const val ANDROID_NS = "http://schemas.android.com/apk/res/android"
        const val TOOLS_NS = "http://schemas.android.com/tools"
        const val COMPANION_PERMISSION = "com.mithaq.network.permission.BIND_COMPANION"
    }
}
