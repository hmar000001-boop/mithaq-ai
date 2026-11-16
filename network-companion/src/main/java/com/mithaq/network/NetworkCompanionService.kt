package com.mithaq.network

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.os.Process
import android.util.Log
import com.mithaq.contract.INetworkCompanion

/**
 * Phase-0 companion endpoint. Future methods must be typed, capability-specific
 * operations; do not add a generic URL/HTTP proxy to this Binder interface.
 */
class NetworkCompanionService : Service() {
    override fun onCreate() {
        super.onCreate()
        Log.i(TAG, "COMPANION_SERVICE_CREATED uid=${Process.myUid()} pid=${Process.myPid()}")
    }

    private val binder = object : INetworkCompanion.Stub() {
        override fun getProtocolVersion(): Int = PROTOCOL_VERSION

        override fun getServiceUid(): Int = Process.myUid()

        override fun echoChallenge(challenge: String): String = challenge
    }

    override fun onBind(intent: Intent?): IBinder {
        Log.i(TAG, "COMPANION_SERVICE_BOUND uid=${Process.myUid()} pid=${Process.myPid()}")
        return binder
    }

    private companion object {
        const val TAG = "MithaqCompanionService"
        const val PROTOCOL_VERSION = CompanionProtocolVersion.VALUE
    }
}
