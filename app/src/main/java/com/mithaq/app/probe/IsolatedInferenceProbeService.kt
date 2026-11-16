package com.mithaq.app.probe

import android.Manifest
import android.app.Service
import android.content.Intent
import android.content.pm.PackageManager
import android.os.IBinder
import android.os.Process
import android.util.Log
import java.io.File

/**
 * Diagnostic-only service used to test the Android isolated-process boundary.
 * It is intentionally not connected to LiteRT-LM and accepts no model files.
 */
class IsolatedInferenceProbeService : Service() {
    override fun onCreate() {
        super.onCreate()
        Log.i(TAG, "ISOLATED_PROBE_CREATED uid=${Process.myUid()} pid=${Process.myPid()}")
    }

    private val binder = object : IIsolatedInferenceProbe.Stub() {
        override fun getWorkerUid(): Int = Process.myUid()

        override fun canReadPath(path: String): Boolean {
            if (path.isBlank()) return false
            return runCatching { File(path).canRead() }.getOrDefault(false)
        }

        override fun checkInternetPermission(): Int =
            if (checkSelfPermission(Manifest.permission.INTERNET) == PackageManager.PERMISSION_GRANTED) 0 else -1
    }

    override fun onBind(intent: Intent?): IBinder {
        Log.i(TAG, "ISOLATED_PROBE_BOUND uid=${Process.myUid()} pid=${Process.myPid()}")
        return binder
    }

    private companion object {
        const val TAG = "MithaqIsolatedProbe"
    }
}
