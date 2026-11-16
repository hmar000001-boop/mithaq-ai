package com.mithaq.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            MithaqTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background,
                ) {
                    PhaseZeroHome()
                }
            }
        }
    }
}

@Composable
private fun MithaqTheme(content: @Composable () -> Unit) {
    MaterialTheme(content = content)
}

@Composable
private fun PhaseZeroHome() {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text("Mithaq", style = MaterialTheme.typography.headlineLarge)
        Spacer(Modifier.height(8.dp))
        Text("Private intelligence, under your control.", style = MaterialTheme.typography.titleMedium)
        Spacer(Modifier.height(24.dp))
        Text("Phase 0 · Android foundation", style = MaterialTheme.typography.titleSmall)
        Spacer(Modifier.height(8.dp))
        Text("The main application has no Internet permission. Network capabilities are isolated in the separately installed companion.")
        Spacer(Modifier.height(8.dp))
        Text("English is the v0 language. Arabic is planned for a later qualified release. French is not supported.")
        Spacer(Modifier.height(24.dp))
        Text("This checkpoint proves package and process boundaries; it does not yet include model inference or network operations.", style = MaterialTheme.typography.bodySmall)
    }
}
