package com.mithaq.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

/** v0 is English-only. Arabic is planned but is not a v0 supported locale. */
class LaunchLanguagePolicyTest {
    @Test
    fun englishIsTheOnlySupportedV0Locale() {
        val supportedLocales = setOf("en")
        val defaultLocale = "en"

        assertEquals("en", defaultLocale)
        assertEquals(setOf("en"), supportedLocales)
        assertFalse("fr" in supportedLocales)
        assertFalse("ar" in supportedLocales)
    }
}
