package com.despertarme.app.ui.screens

import androidx.compose.foundation.BorderStroke
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
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Person
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
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import coil.request.ImageRequest
import com.despertarme.app.data.remote.BoutOut
import com.despertarme.app.ui.theme.BlueCorner
import com.despertarme.app.ui.theme.RedCorner
import com.despertarme.app.ui.theme.SurfaceDark
import com.despertarme.app.ui.theme.TextSecondary
import com.despertarme.app.ui.theme.UfcRed

private val LEAD_OPTIONS = listOf(5, 10, 15, 30)

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
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Volver")
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
                            // El backend lista los combates en orden cronologico:
                            // el primero es el proximo en suceder (evento futuro).
                            isNext = bout.id == state.event.bouts.firstOrNull()?.id,
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
    isNext: Boolean,
    subscribed: Boolean,
    onSubscribe: (Int) -> Unit,
) {
    var selectedLead by remember { mutableStateOf(15) }
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceDark),
        border = if (isNext) BorderStroke(1.dp, UfcRed) else null,
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                if (isNext) {
                    Text(
                        text = "PRÓXIMO",
                        color = Color.White,
                        fontSize = 11.sp,
                        fontWeight = FontWeight.Bold,
                        letterSpacing = 1.sp,
                        modifier = Modifier
                            .clip(RoundedCornerShape(4.dp))
                            .background(UfcRed)
                            .padding(horizontal = 6.dp, vertical = 2.dp),
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                }
                Text(
                    text = "#${bout.matchNumber}",
                    color = TextSecondary,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(modifier = Modifier.width(8.dp))
                if (bout.cardSegment != null) {
                    SegmentBadge(segment = bout.cardSegment)
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
private fun SegmentBadge(segment: String) {
    // "main" en rojo de marca, prelims en azul apagado — antes gris plano.
    val isMain = segment.startsWith("main", ignoreCase = true)
    val bg = if (isMain) UfcRed.copy(alpha = 0.22f) else BlueCorner.copy(alpha = 0.18f)
    val fg = if (isMain) UfcRed else BlueCorner
    Text(
        text = segment.uppercase(),
        color = fg,
        fontSize = 11.sp,
        fontWeight = FontWeight.SemiBold,
        modifier = Modifier
            .clip(RoundedCornerShape(4.dp))
            .background(bg)
            .padding(horizontal = 6.dp, vertical = 2.dp),
    )
}

@Composable
private fun AthleteColumn(name: String?, headshotUrl: String?, cornerColor: Color) {
    Column(
        modifier = Modifier.width(140.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier = Modifier
                .size(80.dp)
                .clip(CircleShape)
                .background(cornerColor.copy(alpha = 0.40f)),
            contentAlignment = Alignment.Center,
        ) {
            val display = headshotUrl
            if (display != null) {
                AsyncImage(
                    model = ImageRequest.Builder(LocalContext.current)
                        .data(display)
                        .crossfade(true)
                        .build(),
                    contentDescription = name,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize(),
                )
            } else {
                // ESPN no resuelve headshot para todos los atletas (debutantes,
                // prelims). Mostrem avatar amb les inicials sobre el color de la
                // cantonada — mateix patro que el placeholder SVG de la web (S5).
                val initials = initialsOf(name)
                if (initials != null) {
                    Text(
                        text = initials,
                        color = Color.White,
                        fontWeight = FontWeight.Bold,
                        fontSize = 20.sp,
                    )
                } else {
                    Icon(
                        imageVector = Icons.Filled.Person,
                        contentDescription = null,
                        tint = Color.White.copy(alpha = 0.7f),
                        modifier = Modifier.size(36.dp),
                    )
                }
            }
        }
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

private fun initialsOf(name: String?): String? {
    if (name.isNullOrBlank()) return null
    val parts = name.trim().split(' ').filter { it.isNotEmpty() }
    if (parts.isEmpty()) return null
    val first = parts.first().firstOrNull() ?: return null
    val initial = if (parts.size >= 2) {
        val last = parts.last().firstOrNull() ?: first
        "$first$last"
    } else {
        if (first.toString().length >= 2) {
            name.take(2)
        } else {
            first.toString()
        }
    }
    return initial.uppercase()
}

private fun formatDate(iso: String): String {
    return runCatching {
        if (iso.length >= 16) "${iso.substring(0, 10)} ${iso.substring(11, 16)} UTC" else iso
    }.getOrDefault(iso)
}