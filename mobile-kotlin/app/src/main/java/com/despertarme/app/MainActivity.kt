package com.despertarme.app

import android.Manifest
import android.app.AlarmManager
import android.app.AlertDialog
import android.app.NotificationManager
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.provider.Settings
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
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.despertarme.app.alarm.AlarmActivity
import com.despertarme.app.alarm.AlarmService
import com.despertarme.app.data.AppContainer
import com.despertarme.app.ui.screens.CompetitionsScreen
import com.despertarme.app.ui.screens.EventDetailScreen
import com.despertarme.app.ui.screens.EventListScreen
import com.despertarme.app.ui.screens.HomeScreen
import com.despertarme.app.ui.screens.SettingsScreen
import com.despertarme.app.ui.screens.SubscriptionsScreen
import com.despertarme.app.ui.theme.BackgroundDark
import com.despertarme.app.ui.theme.DespertarTheme
import com.despertarme.app.ui.theme.TextSecondary
import com.despertarme.app.ui.theme.UfcRed
import com.despertarme.app.ui.viewmodel.CompetitionsViewModel
import com.despertarme.app.ui.viewmodel.CompetitionsViewModelFactory
import com.despertarme.app.ui.viewmodel.EventDetailViewModel
import com.despertarme.app.ui.viewmodel.EventDetailViewModelFactory
import com.despertarme.app.ui.viewmodel.HomeViewModel
import com.despertarme.app.ui.viewmodel.HomeViewModelFactory
import com.despertarme.app.ui.viewmodel.SubscriptionsViewModel
import com.despertarme.app.ui.viewmodel.SubscriptionsViewModelFactory
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {

    private lateinit var container: AppContainer
    private var permissionStep = 0
    private var waitingForSettingsReturn = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        val app = application as DespertarMeApp
        container = app.container

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

    override fun onResume() {
        super.onResume()
        if (waitingForSettingsReturn) {
            waitingForSettingsReturn = false
            advancePermissionChain()
        } else if (permissionStep == 0) {
            advancePermissionChain()
        }
    }

    private fun advancePermissionChain() {
        if (!hasNotificationsPermission()) {
            showPermissionDialog(
                title = "Notificaciones",
                message = "DespertarME necesita enviarte notificaciones para avisarte cuando empiece tu combate.",
            ) {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                    requestPermissions(
                        arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                        REQUEST_NOTIFICATIONS,
                    )
                }
            }
            return
        }
        permissionStep = 1

        if (Build.VERSION.SDK_INT >= 34 && !canUseFullScreenIntent()) {
            showPermissionDialog(
                title = "Pantalla de bloqueo",
                message = "DespertarME necesita mostrarse sobre la pantalla de bloqueo para que puedas detener la alarma sin desbloquear el movil.",
            ) {
                val intent = Intent(
                    Settings.ACTION_MANAGE_APP_USE_FULL_SCREEN_INTENT,
                    Uri.parse("package:$packageName"),
                )
                startActivity(intent)
                waitingForSettingsReturn = true
            }
            return
        }
        permissionStep = 2

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && !canScheduleExactAlarms()) {
            showPermissionDialog(
                title = "Alarmas exactas",
                message = "DespertarME necesita alarmas exactas para que suene en el momento justo, sin retrasos del sistema.",
            ) {
                val intent = Intent(Settings.ACTION_REQUEST_SCHEDULE_EXACT_ALARM).apply {
                    data = Uri.parse("package:$packageName")
                }
                startActivity(intent)
                waitingForSettingsReturn = true
            }
            return
        }
        permissionStep = 3
    }

    override fun onRequestPermissionsResult(
        requestCode: Int,
        permissions: Array<String>,
        grantResults: IntArray,
    ) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_NOTIFICATIONS) {
            advancePermissionChain()
        }
    }

    private fun showPermissionDialog(title: String, message: String, onAccept: () -> Unit) {
        AlertDialog.Builder(this)
            .setTitle(title)
            .setMessage(message)
            .setPositiveButton("Activar") { _, _ -> onAccept() }
            .setNegativeButton("Ahora no", null)
            .setCancelable(false)
            .show()
    }

    private fun hasNotificationsPermission(): Boolean =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) ==
                PackageManager.PERMISSION_GRANTED
        } else {
            true
        }

    private fun canUseFullScreenIntent(): Boolean =
        if (Build.VERSION.SDK_INT >= 34) {
            (getSystemService(NOTIFICATION_SERVICE) as NotificationManager).canUseFullScreenIntent()
        } else {
            true
        }

    private fun canScheduleExactAlarms(): Boolean =
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            (getSystemService(ALARM_SERVICE) as AlarmManager).canScheduleExactAlarms()
        } else {
            true
        }

    companion object {
        private const val REQUEST_NOTIFICATIONS = 1001
    }

    private fun startTestAlarm() {
        val intent = Intent(this, AlarmService::class.java).apply { action = AlarmService.ACTION_START }
        startForegroundService(intent)
        val activityIntent = Intent(this, AlarmActivity::class.java).apply {
            putExtra("bout_id", "test")
            putExtra("event_id", "test")
            putExtra("fighter_red", "Test")
            putExtra("fighter_blue", "Alarma")
            putExtra("lead_minutes", 0)
            putExtra("event_name", "DespertarME — Alarma de prueba")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        }
        startActivity(activityIntent)
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
    val subsVm: SubscriptionsViewModel = viewModel(factory = SubscriptionsViewModelFactory(container))
    val homeVm: HomeViewModel = viewModel(factory = HomeViewModelFactory(container))
    val competitionsVm: CompetitionsViewModel = viewModel(factory = CompetitionsViewModelFactory(container))

    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route

    Scaffold(
        bottomBar = {
            NavigationBar(containerColor = BackgroundDark) {
                TOP_LEVEL_DESTINATIONS.forEach { destination ->
                    NavigationBarItem(
                        selected = currentRoute == destination.route,
                        onClick = {
                            if (destination.route == "subscriptions") {
                                subsVm.prepareForLoad()
                            }
                            navController.navigateTopLevel(destination.route)
                        },
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
                    onEventClick = { eventId, sport, league ->
                        detailVm.clearSnack()
                        detailVm.prepareForNavigation(sport, league)
                        navController.navigate("event/$eventId")
                    },
                    onRetry = { homeVm.load(force = true) },
                )
            }
            composable("events") {
                EventListScreen(
                    onSportClick = { sport ->
                        competitionsVm.prepareForLoad(sport)
                        navController.navigate("events/$sport")
                    },
                )
            }
            composable("events/{sport}") { entry ->
                val sport = entry.arguments?.getString("sport") ?: "mma"
                LaunchedEffect(sport) { competitionsVm.load(sport) }
                val state by competitionsVm.state.collectAsState()
                CompetitionsScreen(
                    state = state,
                    sport = sport,
                    onEventClick = { eventId, s, league ->
                        detailVm.clearSnack()
                        detailVm.prepareForNavigation(s, league)
                        navController.navigate("event/$eventId")
                    },
                    onBack = { navController.popBackStack() },
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
    if (route == "events") {
        popBackStack("events", inclusive = true)
    }
    navigate(route) {
        popUpTo(graph.findStartDestination().id) { saveState = true }
        launchSingleTop = true
        restoreState = true
    }
}
