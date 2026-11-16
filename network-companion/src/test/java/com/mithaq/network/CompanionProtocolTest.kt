package com.mithaq.network

import org.junit.Assert.assertEquals
import org.junit.Test

class CompanionProtocolTest {
    @Test
    fun companionProtocolVersionIsStableAtOne() {
        assertEquals(1, CompanionProtocolVersion.VALUE)
    }
}

