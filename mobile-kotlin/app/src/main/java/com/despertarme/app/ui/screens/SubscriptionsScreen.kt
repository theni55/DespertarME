package com.despertarme.app.ui.screens

import androidx.compose.foundation.BorderStroke
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
import androidx.compose.material3.OutlinedButton
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
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.despertarme.app.ui.theme.BackgroundDark
import com.despertarme.app.ui.theme.FootballGreen
import com.despertarme.app.ui.theme.NbaBlue
import com.despertarme.app.ui.theme.NflBlue
import com.despertarme.app.ui.theme.SurfaceDark
import com.despertarme.app.ui.theme.TennisClay
import com.despertarme.app.ui.theme.TextSecondary
import com.despertarme.app.ui.theme.UfcRed
import com.despertarme.app.ui.viewmodel.AlertUi
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
                verticalArrangement = Arrangement.spacedBy(6.dp),
            ) {
                item { SubscriptionHeader(
                    activeCount = state.subscriptions.count { it.sub.status == "active" },
                    onOpenSettings = onOpenSettings,
                ) }
                if (state.subscriptions.isEmpty()) {
                    item { EmptyAlerts() }
                } else {
                    items(state.subscriptions, key = { it.sub.id }) { ui ->
                        SubscriptionCard(ui = ui, onCancel = { onCancel(ui.sub.id) })
                    }
                }
                if (state.alerts.isNotEmpty()) {
                    item { HistorySectionHeader() }
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
private fun SubscriptionHeader(activeCount: Int, onOpenSettings: () -> Unit) {
    Column {
        Row(
            modifier = Modifier.fillMaxWidth(),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = "TUS ALERTAS",
                    color = Color.White,
                    fontSize = 18.sp,
                    fontWeight = FontWeight.Black,
                    letterSpacing = 1.sp,
                )
                if (activeCount > 0) {
                    Text(
                        text = "$activeCount combates pendientes",
                        color = TextSecondary,
                        fontSize = 12.sp,
                    )
                }
            }
            IconButton(onClick = onOpenSettings) {
                Icon(
                    imageVector = Icons.Filled.Settings,
                    contentDescription = "Ajustes",
                    tint = TextSecondary,
                )
            }
        }
        Spacer(modifier = Modifier.height(6.dp))
        Box(
            modifier = Modifier.fillMaxWidth().height(1.dp)
                .background(Color.White.copy(alpha = 0.08f)),
        )
        Spacer(modifier = Modifier.height(6.dp))
    }
}

@Composable
private fun HistorySectionHeader() {
    Column {
        Spacer(modifier = Modifier.height(12.dp))
        Box(
            modifier = Modifier.fillMaxWidth().height(1.dp)
                .background(Color.White.copy(alpha = 0.08f)),
        )
        Spacer(modifier = Modifier.height(8.dp))
        Text(
            text = "HISTORIAL",
            color = TextSecondary,
            fontSize = 13.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 1.sp,
        )
    }
}

@Composable
private fun EmptyAlerts() {
    Column(
        modifier = Modifier.fillMaxWidth().padding(vertical = 48.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Icon(
            imageVector = Icons.Filled.NotificationsNone,
            contentDescription = null,
            tint = TextSecondary,
            modifier = Modifier.size(56.dp),
        )
        Spacer(modifier = Modifier.height(12.dp))
        Text(
            text = "Aún no tienes alertas",
            color = Color.White,
            fontWeight = FontWeight.SemiBold,
            fontSize = 16.sp,
        )
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = "Suscríbete a un combate desde Eventos",
            color = TextSecondary,
            fontSize = 13.sp,
        )
    }
}

@Composable
private fun SubscriptionCard(ui: SubscriptionUi, onCancel: () -> Unit) {
    val sportColor = when (ui.sport) {
        "tennis" -> TennisClay
        "nba" -> NbaBlue
        "nfl" -> NflBlue
        "football" -> FootballGreen
        else -> UfcRed
    }
    val badgeText = when (ui.sport) {
        "tennis" -> "Tenis"
        "nba" -> "NBA"
        "nfl" -> "NFL"
        "football" -> "Futbol"
        else -> "MMA"
    }
    val isActive = ui.sub.status == "active"
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(10.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceDark),
        border = BorderStroke(1.dp, sportColor.copy(alpha = 0.3f)),
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier.size(8.dp).clip(CircleShape)
                    .background(if (isActive) Color(0xFF4ADE80) else TextSecondary),
            )
            Spacer(modifier = Modifier.width(8.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = ui.fightLabel,
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                    fontSize = 14.sp,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Row(verticalAlignment = Alignment.CenterVertically) {
                    if (ui.eventName != null) {
                        Text(
                            text = ui.eventName.take(40),
                            color = TextSecondary,
                            fontSize = 11.sp,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                            modifier = Modifier.weight(1f, fill = false),
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                    }
                    Text(
                        text = "${ui.sub.leadMinutes} min",
                        color = sportColor,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Medium,
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = badgeText,
                        color = sportColor,
                        fontSize = 9.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 0.5.sp,
                        modifier = Modifier.clip(RoundedCornerShape(3.dp))
                            .background(sportColor.copy(alpha = 0.15f))
                            .padding(horizontal = 4.dp, vertical = 1.dp),
                    )
                }
            }
            OutlinedButton(
                onClick = onCancel,
                modifier = Modifier.padding(start = 4.dp),
                contentPadding = PaddingValues(horizontal = 8.dp, vertical = 4.dp),
            ) {
                Icon(
                    imageVector = Icons.Filled.Delete,
                    contentDescription = "Cancelar",
                    tint = Color(0xFFCF6679).copy(alpha = 0.8f),
                    modifier = Modifier.size(16.dp),
                )
            }
        }
    }
}

@Composable
private fun AlertHistoryRow(alert: AlertUi) {
    val statusColor = when (alert.status) {
        "fired" -> Color(0xFF4ADE80)
        "cancelled" -> Color(0xFFCF6679)
        else -> TextSecondary
    }
    Row(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 4.dp, vertical = 3.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier.size(6.dp).clip(CircleShape).background(statusColor),
        )
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            text = alert.fightLabel,
            color = Color.White.copy(alpha = 0.85f),
            fontSize = 13.sp,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f),
        )
        Spacer(modifier = Modifier.width(6.dp))
        Text(
            text = formatFiredAt(alert.firedAt),
            color = TextSecondary,
            fontSize = 11.sp,
        )
    }
}

private fun formatFiredAt(iso: String): String = runCatching {
    if (iso.length >= 16) "${iso.substring(8, 10)}/${iso.substring(5, 7)} ${iso.substring(11, 16)}" else iso
}.getOrDefault(iso)
