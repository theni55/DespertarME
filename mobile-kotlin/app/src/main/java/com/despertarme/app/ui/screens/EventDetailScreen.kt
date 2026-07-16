package com.despertarme.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
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
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CenterAlignedTopAppBar
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Snackbar
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.despertarme.app.data.remote.BoutOut
import com.despertarme.app.ui.theme.BlueCorner
import com.despertarme.app.ui.theme.RedCorner
import com.despertarme.app.ui.theme.SurfaceDark
import com.despertarme.app.ui.theme.TextSecondary

private val LEAD_OPTIONS = listOf(5, 10, 15, 30, 60)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EventDetailScreen(
    state: EventDetailState,
    snackbarMessage: String?,
    onDismissSnack: () -> Unit,
    onBack: () -> Unit,
    onSubscribe: (BoutOut, Int) -> Unit,
) {
    val snackbarHost = remember { SnackbarHostState() }
    LaunchedEffect(snackbarMessage) {
        if (snackbarMessage != null) {
            snackbarHost.showSnackbar(snackbarMessage)
            onDismissSnack()
        }
    }
    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = { Text(state.event?.name ?: "Evento") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Filled.ArrowBack, contentDescription = "Volver")
                    }
                },
            )
        },
        snackbarHost = { SnackbarHost(hostState = snackbarHost) },
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize().padding(padding).background(Color(0xFF0A0A0A))) {
            when {
                state.isLoading -> CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                state.error != null -> Text(
                    text = state.error,
                    color = Color(0xFFCF6679),
                    modifier = Modifier.align(Alignment.Center).padding(24.dp),
                    textAlign = TextAlign.Center,
                )
                state.event == null -> Text(
                    text = "No hay datos",
                    color = TextSecondary,
                    modifier = Modifier.align(Alignment.Center),
                )
                else -> LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(
                        horizontal = 16.dp,
                        vertical = 8.dp,
                    ),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    item {
                        Text(
                            text = "${state.event.name} · ${formatDate(state.event.date)}",
                            color = TextSecondary,
                            fontSize = 14.sp,
                            modifier = Modifier.padding(horizontal = 4.dp, vertical = 4.dp),
                        )
                    }
                    items(state.event.bouts, key = { it.id }) { bout ->
                        BoutCard(
                            bout = bout,
                            subscribed = state.subscribedBouts.contains(bout.id),
                            onSubscribe = { lead -> onSubscribe(bout, lead) },
                        )
                    }
                    item { Spacer(modifier = Modifier.height(24.dp)) }
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
private fun BoutCard(
    bout: BoutOut,
    subscribed: Boolean,
    onSubscribe: (Int) -> Unit,
) {
    var selectedLead by remember { mutableStateOf(15) }
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceDark),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = "#${bout.matchNumber}",
                    color = TextSecondary,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(modifier = Modifier.width(8.dp))
                if (bout.cardSegment != null) {
                    Text(
                        text = bout.cardSegment,
                        color = TextSecondary,
                        fontSize = 12.sp,
                        modifier = Modifier
                            .clip(RoundedCornerShape(4.dp))
                            .background(Color.White.copy(alpha = 0.08f))
                            .padding(horizontal = 6.dp, vertical = 2.dp),
                    )
                }
                Spacer(modifier = Modifier.width(8.dp))
                if (bout.weightClass != null) {
                    Text(text = bout.weightClass, color = TextSecondary, fontSize = 12.sp)
                }
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "${bout.periods}r",
                    color = TextSecondary,
                    fontSize = 12.sp,
                )
            }
            Spacer(modifier = Modifier.height(12.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                AthleteColumn(bout.red?.name, bout.red?.headshotUrl, RedCorner)
                Text(
                    text = "VS",
                    color = Color.White.copy(alpha = 0.7f),
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(horizontal = 12.dp),
                )
                AthleteColumn(bout.blue?.name, bout.blue?.headshotUrl, BlueCorner)
            }
            if (!subscribed) {
                Spacer(modifier = Modifier.height(12.dp))
                FlowRow(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    LEAD_OPTIONS.forEach { mins ->
                        FilterChip(
                            selected = selectedLead == mins,
                            onClick = { selectedLead = mins },
                            label = { Text("$mins") },
                        )
                    }
                }
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "min antes",
                    color = TextSecondary,
                    fontSize = 12.sp,
                )
                Spacer(modifier = Modifier.height(8.dp))
                OutlinedButton(
                    onClick = { onSubscribe(selectedLead) },
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(text = "Avisarme", fontWeight = FontWeight.Bold)
                }
            } else {
                Spacer(modifier = Modifier.height(12.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(8.dp)
                            .clip(CircleShape)
                            .background(Color(0xFF4ADE80)),
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(text = "Avisando ✓", color = Color(0xFF4ADE80), fontWeight = FontWeight.SemiBold)
                }
            }
        }
    }
}

@Composable
private fun AthleteColumn(name: String?, headshotUrl: String?, cornerColor: Color) {
    Column(
        modifier = Modifier.width(140.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        AsyncImage(
            model = headshotUrl,
            contentDescription = name,
            contentScale = ContentScale.Crop,
            modifier = Modifier
                .size(80.dp)
                .clip(CircleShape)
                .background(cornerColor.copy(alpha = 0.25f)),
        )
        Spacer(modifier = Modifier.height(6.dp))
        Text(
            text = name ?: "TBD",
            color = Color.White,
            fontSize = 13.sp,
            fontWeight = FontWeight.Medium,
            textAlign = TextAlign.Center,
            maxLines = 2,
        )
    }
}

private fun formatDate(iso: String): String {
    return runCatching {
        if (iso.length >= 16) "${iso.substring(0, 10)} ${iso.substring(11, 16)} UTC" else iso
    }.getOrDefault(iso)
}