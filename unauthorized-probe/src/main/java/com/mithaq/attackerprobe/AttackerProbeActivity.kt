package com.mithaq.attackerprobe

import android.app.Activity
import android.content.ComponentName
import android.content.Intent
import android.content.ServiceConnection
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.IBinder
import android.util.Log

/**
 * Test-only application signed with a CI-generated certificate that differs
 * from Mithaq. It asserts that Android rejects an unauthorized Binder caller.
 */
class AttackerProbeActivity : Activity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val targetPackage = "com.mithaq.network.debug"
        val targetClass = "com.mithaq.network.NetworkCompanionService"
        val component = ComponentName(targetPackage, targetClass)

        try {
            val info = packageManager.getServiceInfo(component, PackageManager.ComponentInfoFlags.of(0))
            check(info.exported) { "Companion service must be exported for cross-package IPC" }
            check(info.permission == COMPANION_PERMISSION) {
                "Companion service is not protected by the expected signature permission"
            }
        } catch (error: Exception) {
            Log.e(TAG, "MITHAQ_PERMISSION_PROBE_INVALID_TARGET", error)
            finish()
            return
        }

        val connection = object : ServiceConnection {
            override fun onServiceConnected(name: ComponentName, service: IBinder) {
                Log.e(TAG, "MITHAQ_PERMISSION_PROBE_FAILED_CONNECTED")
                runCatching { unbindService(this) }
                finish()
            }

            override fun onServiceDisconnected(name: ComponentName) = Unit
        }

        try {
            val bound = bindService(Intent().setComponent(component), connection, BIND_AUTO_CREATE)
            if (bound) {
                Log.e(TAG, "MITHAQ_PERMISSION_PROBE_FAILED_BOUND")
            } else {
                // A missing/unresolvable service is not accepted as proof of denial.
                Log.e(TAG, "MITHAQ_PERMISSION_PROBE_FAILED_NOT_BOUND")
            }
        } catch (_: SecurityException) {
            Log.i(TAG, "MITHAQ_PERMISSION_PROBE_DENIED")
        } catch (error: Exception) {
            Log.e(TAG, "MITHAQ_PERMISSION_PROBE_INVALID_BIND", error)
        } finally {
            finish()
        }
    }

    private companion object {
        const val TAG = "MithaqPermissionProbe"
        const val COMPANION_PERMISSION = "com.mithaq.network.permission.BIND_COMPANION"
    }
}
