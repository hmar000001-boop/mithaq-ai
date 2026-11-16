package com.mithaq.app

import android.content.ComponentName
import android.content.Context
import android.content.Intent
import android.content.ServiceConnection
import android.os.IBinder
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

        val service = AtomicReference<IIsolatedInferenceProbe?>()
        val connected = CountDownLatch(1)
        val connection = object : ServiceConnection {
            override fun onServiceConnected(name: ComponentName, binder: IBinder) {
                service.set(IIsolatedInferenceProbe.Stub.asInterface(binder))
                connected.countDown()
            }

            override fun onServiceDisconnected(name: ComponentName) {
                service.set(null)
            }
        }

        val bound = context.bindService(
            Intent(context, IsolatedInferenceProbeService::class.java),
            connection,
            Context.BIND_AUTO_CREATE,
        )
        assertTrue("Could not bind isolated probe service", bound)

        try {
            assertTrue("Isolated service connection timed out", connected.await(10, TimeUnit.SECONDS))
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
        val service = AtomicReference<INetworkCompanion?>()
        val connected = CountDownLatch(1)
        val connection = object : ServiceConnection {
            override fun onServiceConnected(name: ComponentName, binder: IBinder) {
                service.set(INetworkCompanion.Stub.asInterface(binder))
                connected.countDown()
            }

            override fun onServiceDisconnected(name: ComponentName) {
                service.set(null)
            }
        }

        val intent = Intent().setComponent(
            ComponentName("com.mithaq.network.debug", "com.mithaq.network.NetworkCompanionService"),
        )
        val bound = context.bindService(intent, connection, Context.BIND_AUTO_CREATE)
        assertTrue("Debug companion must be installed before running this test", bound)

        try {
            assertTrue("Companion Binder connection timed out", connected.await(10, TimeUnit.SECONDS))
            val remote = requireNotNull(service.get())
            val challenge = "mithaq-phase0-${UUID.randomUUID()}"

            assertEquals(1, remote.protocolVersion)
            assertEquals(challenge, remote.echoChallenge(challenge))
            assertNotEquals(context.applicationInfo.uid, remote.serviceUid)
        } finally {
            context.unbindService(connection)
        }
    }
}
