package com.despertarme.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.NotificationsNone
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.despertarme.app.data.remote.AlertLogOut
import com.despertarme.app.ui.theme.BackgroundDark
import com.despertarme.app.ui.theme.SurfaceDark
import com.despertarme.app.ui.theme.TextSecondary
import com.despertarme.app.ui.theme.UfcRed
import com.despertarme.app.ui.viewmodel.SubscriptionUi
import com.despertarme.app.ui.viewmodel.SubscriptionsState

@Composable
fun SubscriptionsScreen(
    state: SubscriptionsState,
    snackbarMessage: String?,
    onDismissSnack: () -> Unit,
    onCancel: (String) -> Unit,
    onOpenSettings: () -> Unit,
) {
    val snackbarHost = remember { SnackbarHostState() }
    LaunchedEffect(snackbarMessage) {
        if (snackbarMessage != null) {
            snackbarHost.showSnackbar(snackbarMessage)
            onDismissSnack()
        }
    }
    Box(modifier = Modifier.fillMaxSize().background(BackgroundDark)) {
        when {
            state.isLoading -> CircularProgressIndicator(
                color = UfcRed,
                modifier = Modifier.align(Alignment.Center),
            )
            state.error != null -> Text(
                text = state.error,
                color = Color(0xFFCF6679),
                modifier = Modifier.align(Alignment.Center).padding(24.dp),
                textAlign = TextAlign.Center,
            )
            else -> LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(horizontal = 16.dp, vertical = 16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                item {
                    // D46: Ajustes sale de la bottom nav; se accede desde aquí.
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            text = "MIS ALERTAS",
                            color = Color.White,
                            fontSize = 20.sp,
                            fontWeight = FontWeight.Black,
                            letterSpacing = 1.sp,
                            modifier = Modifier.weight(1f),
                        )
                        IconButton(onClick = onOpenSettings) {
                            Icon(
                                imageVector = Icons.Filled.Settings,
                                contentDescription = "Ajustes",
                                tint = TextSecondary,
                            )
                        }
                    }
                }
                if (state.subscriptions.isEmpty()) {
                    item { EmptyAlerts() }
                } else {
                    items(state.subscriptions, key = { it.sub.id }) { ui ->
                        SubscriptionCard(ui = ui, onCancel = { onCancel(ui.sub.id) })
                    }
                }
                item {
                    Spacer(modifier = Modifier.height(8.dp))
                    Text(
                        text = "HISTORIAL",
                        color = TextSecondary,
                        fontSize = 14.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 1.sp,
                    )
                }
                if (state.alerts.isEmpty()) {
                    item {
                        Text(
                            text = "Todavía no ha sonado ninguna alerta.",
                            color = TextSecondary,
                            fontSize = 13.sp,
                        )
                    }
                } else {
                    items(state.alerts, key = { it.id }) { alert ->
                        AlertHistoryRow(alert = alert)
                    }
                }
                item { Spacer(modifier = Modifier.height(24.dp)) }
            }
        }
    }
    SnackbarHost(hostState = snackbarHost)
}

@Composable
private fun EmptyAlerts() {
    Column(
        modifier = Modifier.fillMaxWidth().padding(vertical = 32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Icon(
            imageVector = Icons.Filled.NotificationsNone,
            contentDescription = null,
            tint = TextSecondary,
            modifier = Modifier.size(48.dp),
        )
        Spacer(modifier = Modifier.height(12.dp))
        Text(
            text = "No tienes alertas activas.",
            color = Color.White,
            fontWeight = FontWeight.SemiBold,
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = "Suscríbete a un combate desde Eventos.",
            color = TextSecondary,
            fontSize = 13.sp,
        )
    }
}

@Composable
private fun SubscriptionCard(
    ui: SubscriptionUi,
    onCancel: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceDark),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier
                    .size(10.dp)
                    .clip(CircleShape)
                    .background(if (ui.sub.status == "active") Color(0xFF4ADE80) else TextSecondary),
            )
            Spacer(modifier = Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = ui.fightLabel,
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                    fontSize = 15.sp,
                )
                Spacer(modifier = Modifier.height(2.dp))
                Text(
                    text = buildString {
                        if (ui.eventName != null) {
                            append(ui.eventName)
                            append(" · ")
                        }
                        append("${ui.sub.leadMinutes} min antes")
                    },
                    color = TextSecondary,
                    fontSize = 12.sp,
                )
            }
            IconButton(onClick = onCancel) {
                Icon(
                    imageVector = Icons.Filled.Delete,
                    contentDescription = "Cancelar alerta",
                    tint = UfcRed,
                )
            }
        }
    }
}

@Composable
private fun AlertHistoryRow(alert: AlertLogOut) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(modifier = Modifier.weight(1f)) {
            Text(
                text = "Alerta ${alert.status}",
                color = Color.White,
                fontSize = 14.sp,
                fontWeight = FontWeight.Medium,
            )
            Text(
                text = formatFiredAt(alert.firedAt),
                color = TextSecondary,
                fontSize = 12.sp,
            )
        }
        Text(
            text = "x${alert.attempts}",
            color = TextSecondary,
            fontSize = 12.sp,
        )
    }
}

private fun formatFiredAt(iso: String): String = runCatching {
    if (iso.length >= 16) "${iso.substring(0, 10)} ${iso.substring(11, 16)}" else iso
}.getOrDefault(iso)
