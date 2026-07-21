package com.despertarme.app

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.despertarme.app.alarm.AlarmService
import com.despertarme.app.data.AppContainer
import com.despertarme.app.ui.screens.EventDetailScreen
import com.despertarme.app.ui.screens.EventListScreen
import com.despertarme.app.ui.screens.HomeScreen
import com.despertarme.app.ui.screens.SettingsScreen
import com.despertarme.app.ui.screens.SubscriptionsScreen
import com.despertarme.app.ui.theme.BackgroundDark
import com.despertarme.app.ui.theme.DespertarTheme
import com.despertarme.app.ui.theme.TextSecondary
import com.despertarme.app.ui.theme.UfcRed
import com.despertarme.app.ui.viewmodel.EventDetailViewModel
import com.despertarme.app.ui.viewmodel.EventDetailViewModelFactory
import com.despertarme.app.ui.viewmodel.EventListViewModel
import com.despertarme.app.ui.viewmodel.EventListViewModelFactory
import com.despertarme.app.ui.viewmodel.HomeViewModel
import com.despertarme.app.ui.viewmodel.HomeViewModelFactory
import com.despertarme.app.ui.viewmodel.SubscriptionsViewModel
import com.despertarme.app.ui.viewmodel.SubscriptionsViewModelFactory
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {

    private lateinit var container: AppContainer

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        // Usar el AppContainer singleton del Application (lo comparten receivers/services).
        val app = application as DespertarMeApp
        container = app.container

        // Registrar el device best-effort antes de que la UI rinda.
        runCatching {
            kotlinx.coroutines.runBlocking { withContext(Dispatchers.IO) { container.ensureRegistered() } }
        }
        setContent {
            DespertarTheme {
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    AppGraph(
                        container = container,
                        onTestAlarm = ::startTestAlarm,
                        onStopAlarm = ::stopTestAlarm,
                    )
                }
            }
        }
    }

    private fun startTestAlarm() {
        val intent = Intent(this, AlarmService::class.java).apply { action = AlarmService.ACTION_START }
        startForegroundService(intent)
    }

    private fun stopTestAlarm() {
        val intent = Intent(this, AlarmService::class.java).apply { action = AlarmService.ACTION_STOP }
        startService(intent)
    }
}

private data class TopLevelDestination(
    val route: String,
    val label: String,
    val icon: ImageVector,
)

// D46: nav reducida a 3 destinos (Buscar/Home/Alertas). Ajustes sale de la nav
// y se alcanza vía icono ⚙️ en el header de "Mis alertas".
private val TOP_LEVEL_DESTINATIONS = listOf(
    TopLevelDestination("events", "Buscar", Icons.Filled.Search),
    TopLevelDestination("home", "Home", Icons.Filled.Home),
    TopLevelDestination("subscriptions", "Alertas", Icons.Filled.Notifications),
)

@Composable
private fun AppGraph(
    container: AppContainer,
    onTestAlarm: () -> Unit,
    onStopAlarm: () -> Unit,
) {
    val navController = rememberNavController()
    val detailVm: EventDetailViewModel = viewModel(factory = EventDetailViewModelFactory(container))
    val eventsVm: EventListViewModel = viewModel(factory = EventListViewModelFactory(container))
    val subsVm: SubscriptionsViewModel = viewModel(factory = SubscriptionsViewModelFactory(container))
    val homeVm: HomeViewModel = viewModel(factory = HomeViewModelFactory(container))

    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route

    Scaffold(
        bottomBar = {
            NavigationBar(containerColor = BackgroundDark) {
                TOP_LEVEL_DESTINATIONS.forEach { destination ->
                    NavigationBarItem(
                        selected = currentRoute == destination.route,
                        onClick = { navController.navigateTopLevel(destination.route) },
                        icon = { Icon(destination.icon, contentDescription = destination.label) },
                        label = { Text(destination.label) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = UfcRed,
                            selectedTextColor = UfcRed,
                            unselectedIconColor = TextSecondary,
                            unselectedTextColor = TextSecondary,
                            indicatorColor = UfcRed.copy(alpha = 0.12f),
                        ),
                    )
                }
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = "home",
            modifier = Modifier.padding(padding),
        ) {
            composable("home") {
                val state by homeVm.state.collectAsState()
                LaunchedEffect(Unit) { homeVm.load() }
                HomeScreen(
                    state = state,
                    onEventClick = { eventId ->
                        detailVm.clearSnack()
                        navController.navigate("event/$eventId")
                    },
                    onRetry = { homeVm.load(force = true) },
                )
            }
            composable("events") {
                val state by eventsVm.state.collectAsState()
                LaunchedEffect(Unit) { eventsVm.load() }
                EventListScreen(
                    state = state,
                    onEventClick = { event ->
                        detailVm.clearSnack()
                        navController.navigate("event/${event.id}")
                    },
                )
            }
            composable("subscriptions") {
                val state by subsVm.state.collectAsState()
                val snack by subsVm.snackMessage.collectAsState()
                LaunchedEffect(Unit) { subsVm.load() }
                SubscriptionsScreen(
                    state = state,
                    snackbarMessage = snack,
                    onDismissSnack = { subsVm.clearSnack() },
                    onCancel = { subId -> subsVm.cancel(subId) },
                    onOpenSettings = { navController.navigate("settings") },
                )
            }
            composable("settings") {
                val deviceId by container.deviceId.collectAsState()
                SettingsScreen(
                    deviceId = deviceId,
                    onTestAlarm = onTestAlarm,
                    onStopAlarm = onStopAlarm,
                    onBack = { navController.popBackStack() },
                )
            }
            composable("event/{eventId}") { entry ->
                val eventId = entry.arguments?.getString("eventId") ?: "none"
                LaunchedEffect(eventId) { detailVm.load(eventId) }
                val state by detailVm.state.collectAsState()
                val snack by detailVm.snackMessage.collectAsState()
                EventDetailScreen(
                    state = state,
                    snackbarMessage = snack,
                    onDismissSnack = { detailVm.clearSnack() },
                    onBack = { navController.popBackStack() },
                    onSubscribe = { bout, lead ->
                        val eventIdForSub = state.event?.id ?: eventId
                        val red = bout.red?.name ?: "TBD"
                        val blue = bout.blue?.name ?: "TBD"
                        detailVm.subscribe(
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
}

private fun NavHostController.navigateTopLevel(route: String) {
    navigate(route) {
        popUpTo(graph.findStartDestination().id) { saveState = true }
        launchSingleTop = true
        restoreState = true
    }
}
