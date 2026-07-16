package com.despertarme.app

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.despertarme.app.alarm.AlarmService
import com.despertarme.app.data.AppContainer
import com.despertarme.app.data.remote.EventSummaryOut
import com.despertarme.app.ui.screens.EventDetailScreen
import com.despertarme.app.ui.screens.HomeScreen
import com.despertarme.app.ui.theme.DespertarTheme
import com.despertarme.app.ui.viewmodel.EventDetailViewModel
import com.despertarme.app.ui.viewmodel.EventListLoader
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {

    private lateinit var container: AppContainer

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        container = AppContainer(applicationContext)
        // Register the device best-effort before UI renders; fast (SQLite-side on backend).
        runCatching {
            kotlinx.coroutines.runBlocking { withContext(Dispatchers.IO) { container.ensureRegistered() } }
        }
        setContent {
            DespertarTheme {
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    AppGraph(container = container, onTestAlarm = ::startTestAlarm)
                }
            }
        }
    }

    private fun startTestAlarm() {
        val intent = Intent(this, AlarmService::class.java).apply { action = AlarmService.ACTION_START }
        startForegroundService(intent)
    }
}

@Composable
private fun AppGraph(
    container: AppContainer,
    onTestAlarm: () -> Unit,
) {
    val navController = rememberNavController()
    val vm: EventDetailViewModel = viewModel(factory = com.despertarme.app.ui.viewmodel.EventDetailViewModelFactory(container))

    // Resolve the next event ahead of time so Home's "Avísame" can navigate
    // straight into EventDetail without blocking the UI.
    var nextEvent by remember { mutableStateOf<EventSummaryOut?>(null) }
    var resolvingNext by remember { mutableStateOf(true) }
    LaunchedEffect(Unit) {
        kotlinx.coroutines.withContext(Dispatchers.IO) {
            nextEvent = EventListLoader(container).nextEvent()
            resolvingNext = false
        }
    }

    NavHost(navController = navController, startDestination = "home") {
        composable("home") {
            HomeScreen(
                isLoading = resolvingNext && nextEvent == null,
                onNextEvent = {
                    val event = nextEvent
                    if (event != null) {
                        vm.clearSnack()
                        navController.navigate("event/${event.id}")
                    }
                },
                onTestAlarm = onTestAlarm,
            )
        }
        composable("event/{eventId}") { backStackEntry ->
            val eventId = backStackEntry.arguments?.getString("eventId") ?: "none"
            LaunchedEffect(eventId) { vm.load(eventId) }
            val state by vm.state.collectAsState()
            val snack by vm.snackMessage.collectAsState()
            EventDetailScreen(
                state = state,
                snackbarMessage = snack,
                onDismissSnack = { vm.clearSnack() },
                onBack = { navController.popBackStack() },
                onSubscribe = { bout, lead ->
                    val eventIdForSub = state.event?.id ?: eventId
                    val red = bout.red?.name ?: "TBD"
                    val blue = bout.blue?.name ?: "TBD"
                    vm.subscribe(
                        boutId = bout.id,
                        eventId = eventIdForSub,
                        matchNumber = bout.matchNumber,
                        leadMinutes = lead,
                        fighterNames = red to blue,
                    )
                },
            )
        }
    }
}