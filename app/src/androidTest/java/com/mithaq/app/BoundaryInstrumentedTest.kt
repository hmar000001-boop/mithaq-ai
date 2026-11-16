package com.mithaq.app

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.os.IBinder
import android.os.Process
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.mithaq.app.probe.IIsolatedInferenceProbe
import com.mithaq.app.probe.IsolatedInferenceProbeService
import com.mithaq.contract.INetworkCompanion
import java.io.File
import java.util.UUID
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class BoundaryInstrumentedTest {
    private val context: Context
        get() = InstrumentationRegistry.getInstrumentation().targetContext

    @Test
    fun isolatedWorkerHasSeparateUidAndCannotReadHostPrivateFile() {
        val marker = File(context.filesDir, "phase0-isolation-${UUID.randomUUID()}.txt")
        marker.writeText("host-private-marker")
        assertTrue("The host app must read its own test marker", marker.canRead())

        val component = ComponentName(context, IsolatedInferenceProbeService::class.java)
        val serviceInfo = context.packageManager.getServiceInfo(
            component,
            PackageManager.ComponentInfoFlags.of(0),
        )
        assertFalse("Inference probe must remain non-exported", serviceInfo.exported)
        assertTrue(
            "Inference probe must be declared isolatedProcess=true (flags=${serviceInfo.flags})",
            serviceInfo.flags and ServiceInfo.FLAG_ISOLATED_PROCESS != 0,
        )
        assertTrue(
            "Inference probe must use a dedicated named process: ${serviceInfo.processName}",
            serviceInfo.processName.endsWith(":inference_probe"),
        )

        val service = AtomicReference<IIsolatedInferenceProbe?>()
        val event = AtomicReference("no ServiceConnection callback")
        val connected = CountDownLatch(1)
        val connection = object : ServiceConnection {
            override fun onServiceConnected(name: ComponentName, binder: IBinder) {
                event.set("onServiceConnected($name)")
                service.set(IIsolatedInferenceProbe.Stub.asInterface(binder))
                connected.countDown()
            }

            override fun onServiceDisconnected(name: ComponentName) {
                event.set("onServiceDisconnected($name)")
                connected.countDown()
            }

            override fun onNullBinding(name: ComponentName) {
                event.set("onNullBinding($name)")
                connected.countDown()
            }

            override fun onBindingDied(name: ComponentName) {
                event.set("onBindingDied($name)")
                connected.countDown()
            }
        }

        val intent = Intent().setComponent(component)
        val bound = context.bindIsolatedService(
            intent,
            Context.BIND_AUTO_CREATE,
            "phase0-isolation-${UUID.randomUUID()}",
            context.mainExecutor,
            connection,
        )
        assertTrue("Could not bind isolated probe service $component", bound)

        try {
            assertTrue(
                "Isolated service did not connect within 30s; event=${event.get()}, " +
                    "callerUid=${Process.myUid()}, targetUid=${context.applicationInfo.uid}, " +
                    "process=${serviceInfo.processName}",
                connected.await(SERVICE_CONNECTION_TIMEOUT_SECONDS, TimeUnit.SECONDS),
            )
            assertTrue("Expected a Binder connection, observed ${event.get()}", service.get() != null)
            val remote = requireNotNull(service.get())

            assertNotEquals("Worker must have its own isolated UID", context.applicationInfo.uid, remote.workerUid)
            assertFalse("Isolated worker must not read the host app's private file", remote.canReadPath(marker.absolutePath))
            assertEquals("Isolated worker must not have Internet permission", -1, remote.checkInternetPermission())
        } finally {
            context.unbindService(connection)
            marker.delete()
        }
    }

    @Test
    fun companionBinderIsReachableOnlyThroughTheSignedCompanionContract() {
        val companionPackage = DEBUG_COMPANION_PACKAGE
        val component = ComponentName(companionPackage, COMPANION_SERVICE_CLASS)
        val packageManager = context.packageManager

        val companionPackageInfo = try {
            packageManager.getPackageInfo(
                companionPackage,
                PackageManager.PackageInfoFlags.of(PackageManager.GET_PERMISSIONS.toLong()),
            )
        } catch (error: PackageManager.NameNotFoundException) {
            throw AssertionError(
                "Debug network companion $companionPackage is not installed or is not query-visible. " +
                    "Install network-companion-debug.apk and keep the package in app <queries>.",
                error,
            )
        }
        assertNotNull("Companion package must expose package metadata", companionPackageInfo.applicationInfo)

        val serviceInfo = packageManager.getServiceInfo(
            component,
            PackageManager.ComponentInfoFlags.of(0),
        )
        assertTrue("Companion Binder service must be enabled", serviceInfo.enabled)
        assertTrue("Companion Binder service must be exported for cross-package IPC", serviceInfo.exported)
        assertEquals("Companion must use the signature-level Binder permission", COMPANION_PERMISSION, serviceInfo.permission)
        assertEquals(
            "Main app must hold the companion signature permission; check APK signing certificates and companion install order",
            PackageManager.PERMISSION_GRANTED,
            context.checkSelfPermission(COMPANION_PERMISSION),
        )
        assertEquals(
            "Main app and companion must have the same signing certificate",
            PackageManager.SIGNATURE_MATCH,
            packageManager.checkSignatures(context.packageName, companionPackage),
        )

        val service = AtomicReference<INetworkCompanion?>()
        val event = AtomicReference("no ServiceConnection callback")
        val connected = CountDownLatch(1)
        val connection = object : ServiceConnection {
            override fun onServiceConnected(name: ComponentName, binder: IBinder) {
                event.set("onServiceConnected($name)")
                service.set(INetworkCompanion.Stub.asInterface(binder))
                connected.countDown()
            }

            override fun onServiceDisconnected(name: ComponentName) {
                event.set("onServiceDisconnected($name)")
                connected.countDown()
            }

            override fun onNullBinding(name: ComponentName) {
                event.set("onNullBinding($name)")
                connected.countDown()
            }

            override fun onBindingDied(name: ComponentName) {
                event.set("onBindingDied($name)")
                connected.countDown()
            }
        }

        val bound = try {
            context.bindService(Intent().setComponent(component), connection, Context.BIND_AUTO_CREATE)
        } catch (error: SecurityException) {
            throw AssertionError(
                "Android denied the main app's bind to $component despite the declared signature permission. " +
                    "Main package=${context.packageName}, companion=$companionPackage, " +
                    "granted=${context.checkSelfPermission(COMPANION_PERMISSION)}",
                error,
            )
        }
        assertTrue("Companion service $component could not be resolved for binding", bound)

        try {
            assertTrue(
                "Companion Binder did not connect within 30s; event=${event.get()}, " +
                    "mainUid=${context.applicationInfo.uid}, companionUid=${serviceInfo.applicationInfo.uid}, " +
                    "permissionGranted=${context.checkSelfPermission(COMPANION_PERMISSION)}",
                connected.await(SERVICE_CONNECTION_TIMEOUT_SECONDS, TimeUnit.SECONDS),
            )
            assertTrue("Expected a Binder connection, observed ${event.get()}", service.get() != null)
            val remote = requireNotNull(service.get())
            val challenge = "mithaq-phase0-${UUID.randomUUID()}"

            assertEquals(1, remote.protocolVersion)
            assertEquals(challenge, remote.echoChallenge(challenge))
            assertNotEquals(context.applicationInfo.uid, remote.serviceUid)
            assertEquals(serviceInfo.applicationInfo.uid, remote.serviceUid)
        } finally {
            context.unbindService(connection)
        }
    }

    private companion object {
        const val COMPANION_PERMISSION = "com.mithaq.network.permission.BIND_COMPANION"
        const val DEBUG_COMPANION_PACKAGE = "com.mithaq.network.debug"
        const val COMPANION_SERVICE_CLASS = "com.mithaq.network.NetworkCompanionService"
        const val SERVICE_CONNECTION_TIMEOUT_SECONDS = 30L
    }
}
