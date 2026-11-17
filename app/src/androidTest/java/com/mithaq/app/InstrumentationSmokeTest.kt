package com.mithaq.app

import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test
import org.junit.runner.RunWith

/** Minimal runner diagnostic, executed separately before security-boundary tests. */
@RunWith(AndroidJUnit4::class)
class InstrumentationSmokeTest {
    @Test
    fun runnerStartsAndTargetContextIsAvailable() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        assertNotNull("Instrumentation context must be available", instrumentation.context)
        assertEquals("com.mithaq.app.debug", instrumentation.targetContext.packageName)
    }
}
