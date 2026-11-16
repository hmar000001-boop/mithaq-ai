package com.mithaq.network

import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.os.Process
import com.mithaq.contract.INetworkCompanion

/**
 * Phase-0 companion endpoint. Future methods must be typed, capability-specific
 * operations; do not add a generic URL/HTTP proxy to this Binder interface.
 */
class NetworkCompanionService : Service() {
    private val binder = object : INetworkCompanion.Stub() {
        override fun getProtocolVersion(): Int = PROTOCOL_VERSION

        override fun getServiceUid(): Int = Process.myUid()

        override fun echoChallenge(challenge: String): String = challenge
    }

    override fun onBind(intent: Intent?): IBinder = binder

    private companion object {
        const val PROTOCOL_VERSION = CompanionProtocolVersion.VALUE
    }
}
