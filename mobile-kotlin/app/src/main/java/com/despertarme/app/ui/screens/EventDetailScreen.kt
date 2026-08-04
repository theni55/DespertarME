package com.despertarme.app.ui.screens

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
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
import androidx.compose.foundation.lazy.itemsIndexed
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
import coil.compose.AsyncImagePainter
import coil.compose.rememberAsyncImagePainter
import coil.request.ImageRequest
import com.despertarme.app.data.remote.BoutOut
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.Locale
import com.despertarme.app.ui.theme.TennisClay
import com.despertarme.app.ui.theme.BackgroundDark
import com.despertarme.app.ui.theme.BlueCorner
import com.despertarme.app.ui.theme.FootballGreen
import com.despertarme.app.ui.theme.NbaBlue
import com.despertarme.app.ui.theme.NflBlue
import com.despertarme.app.ui.theme.RedCorner
import com.despertarme.app.ui.theme.SurfaceDark
import com.despertarme.app.ui.theme.TextSecondary
import com.despertarme.app.ui.theme.UfcRed

private val LEAD_OPTIONS = listOf(5, 10, 15, 30)
private val NBA_QUARTER_LEAD_OPTIONS = listOf(0)

private fun leadOptionsFor(bout: BoutOut): List<Pair<Int, String>> {
    if (bout.sport == "nba" && bout.matchNumber in 2..4) {
        return NBA_QUARTER_LEAD_OPTIONS.map { it to "Cuando empieza" }
    }
    if (bout.sport == "nfl" && bout.matchNumber in 2..4) {
        return NBA_QUARTER_LEAD_OPTIONS.map { it to "Cuando empieza" }
    }
    return LEAD_OPTIONS.map { it to "$it" }
}

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
                    val bouts = state.event.bouts
                    val isNba = bouts.firstOrNull()?.sport == "nba"
                    val isNfl = bouts.firstOrNull()?.sport == "nfl"
                    if (isNba) {
                        val games = bouts
                            .groupBy { it.id.substringBefore("_q") }
                            .values
                            .toList()
                        itemsIndexed(games, key = { _, g -> g.first().id.substringBefore("_q") }) { index, gameBouts ->
                            NbaGameCard(
                                bouts = gameBouts.sortedBy { it.matchNumber },
                                subscribedBouts = state.subscribedBouts,
                                onSubscribe = onSubscribe,
                            )
                            if ((index + 1) % 4 == 0 && index < games.lastIndex) {
                                Spacer(modifier = Modifier.height(12.dp))
                                AdSlot()
                            }
                        }
                    } else if (isNfl) {
                        val games = bouts
                            .groupBy { it.id.substringBefore("_q") }
                            .values
                            .toList()
                        itemsIndexed(games, key = { _, g -> g.first().id.substringBefore("_q") }) { index, gameBouts ->
                            NflGameCard(
                                bouts = gameBouts.sortedBy { it.matchNumber },
                                subscribedBouts = state.subscribedBouts,
                                onSubscribe = onSubscribe,
                            )
                            if ((index + 1) % 4 == 0 && index < games.lastIndex) {
                                Spacer(modifier = Modifier.height(12.dp))
                                AdSlot()
                            }
                        }
                    } else {
                        itemsIndexed(bouts, key = { _, bout -> bout.id }) { index, bout ->
                            BoutCard(
                                bout = bout,
                                // El backend lista los combates en orden cronologico:
                                // el primero es el proximo en suceder (evento futuro).
                                isNext = bout.id == bouts.firstOrNull()?.id,
                                subscribed = state.subscribedBouts.contains(bout.id),
                                onSubscribe = { lead -> onSubscribe(bout, lead) },
                            )
                            if ((index + 1) % 4 == 0 && index < bouts.lastIndex) {
                                Spacer(modifier = Modifier.height(12.dp))
                                AdSlot()
                            }
                        }
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
                if (bout.sport == "tennis") {
                    if (bout.court != null) {
                        TennisCourtBadge(court = bout.court)
                        Spacer(modifier = Modifier.width(8.dp))
                    }
                    if (bout.roundDescription != null) {
                        Text(
                            text = bout.roundDescription,
                            color = TextSecondary,
                            fontSize = 12.sp,
                        )
                        Spacer(modifier = Modifier.width(8.dp))
                    }
                    Text(
                        text = "${bout.periods} sets",
                        color = TextSecondary,
                        fontSize = 12.sp,
                    )
                } else if (bout.sport == "nba") {
                    val quarterLabel = when (bout.matchNumber) {
                        1 -> "Inicio del partido"
                        2 -> "2º cuarto"
                        3 -> "3º cuarto"
                        4 -> "4º cuarto"
                        else -> "Q${bout.matchNumber}"
                    }
                    Text(
                        text = quarterLabel,
                        color = NbaBlue,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.SemiBold,
                    )
                } else if (bout.sport == "nfl") {
                    val quarterLabel = when (bout.matchNumber) {
                        1 -> "Inicio del partido"
                        2 -> "2º cuarto"
                        3 -> "3º cuarto"
                        4 -> "4º cuarto"
                        else -> "Q${bout.matchNumber}"
                    }
                    Text(
                        text = quarterLabel,
                        color = NflBlue,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "12 min",
                        color = TextSecondary,
                        fontSize = 12.sp,
                    )
                } else if (bout.sport == "football") {
                    Text(
                        text = "Partido",
                        color = FootballGreen,
                        fontSize = 12.sp,
                        fontWeight = FontWeight.Bold,
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text(
                        text = "90 min",
                        color = TextSecondary,
                        fontSize = 12.sp,
                    )
                } else {
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
            }
            Spacer(modifier = Modifier.height(12.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                AthleteColumn(bout.red?.name, bout.red?.headshotUrl, RedCorner)
                Text(
                    text = if (bout.sport == "tennis") formatBoutTime(bout.date) else "VS",
                    color = Color.White.copy(alpha = 0.7f),
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(horizontal = 12.dp),
                )
                AthleteColumn(bout.blue?.name, bout.blue?.headshotUrl, BlueCorner)
            }
            if (!subscribed) {
                Spacer(modifier = Modifier.height(12.dp))
                val options = leadOptionsFor(bout)
                FlowRow(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(4.dp),
                ) {
                    options.forEach { (mins, label) ->
                        FilterChip(
                            selected = selectedLead == mins,
                            onClick = { selectedLead = mins },
                            label = { Text(label) },
                        )
                    }
                }
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = if ((bout.sport == "nba" || bout.sport == "nfl") && bout.matchNumber in 2..4) "" else "min antes",
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

/**
 * Card única por partido NBA: cabecera con equipos + hora, y dentro los avisos
 * de los 4 cuartos agrupados. Q1 con selector de lead (5/10/15/30 min antes),
 * Q2-Q4 solo "Cuando empieza". Solo presentación — los bouts/ids del backend
 * no cambian.
 */
@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun NbaGameCard(
    bouts: List<BoutOut>,
    subscribedBouts: Set<String>,
    onSubscribe: (BoutOut, Int) -> Unit,
) {
    val q1 = bouts.firstOrNull { it.matchNumber == 1 } ?: bouts.first()
    var selectedLead by remember { mutableStateOf(15) }
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceDark),
        border = BorderStroke(1.dp, NbaBlue.copy(alpha = 0.5f)),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = "NBA",
                    color = NbaBlue,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.sp,
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = formatDate(q1.date),
                    color = TextSecondary,
                    fontSize = 12.sp,
                )
            }
            Spacer(modifier = Modifier.height(12.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                AthleteColumn(q1.red?.name, q1.red?.headshotUrl, RedCorner)
                Text(
                    text = "VS",
                    color = Color.White.copy(alpha = 0.7f),
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(horizontal = 12.dp),
                )
                AthleteColumn(q1.blue?.name, q1.blue?.headshotUrl, BlueCorner)
            }
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = "AVISOS",
                color = TextSecondary,
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 1.sp,
            )
            Spacer(modifier = Modifier.height(8.dp))
            bouts.forEach { bout ->
                val quarterLabel = when (bout.matchNumber) {
                    1 -> "Inicio del partido"
                    2 -> "2º cuarto"
                    3 -> "3º cuarto"
                    4 -> "4º cuarto"
                    else -> "Q${bout.matchNumber}"
                }
                val isQ1 = bout.matchNumber == 1
                val subscribed = subscribedBouts.contains(bout.id)
                Row(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = quarterLabel,
                            color = Color.White,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.SemiBold,
                        )
                        if (isQ1 && !subscribed) {
                            Spacer(modifier = Modifier.height(4.dp))
                            FlowRow(
                                horizontalArrangement = Arrangement.spacedBy(6.dp),
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
                            Text(
                                text = "min antes",
                                color = TextSecondary,
                                fontSize = 11.sp,
                            )
                        } else if (!isQ1 && !subscribed) {
                            Text(
                                text = "Cuando empieza",
                                color = TextSecondary,
                                fontSize = 11.sp,
                            )
                        }
                    }
                    if (subscribed) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(8.dp)
                                    .clip(CircleShape)
                                    .background(Color(0xFF4ADE80)),
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = "Avisando ✓",
                                color = Color(0xFF4ADE80),
                                fontSize = 12.sp,
                                fontWeight = FontWeight.SemiBold,
                            )
                        }
                    } else {
                        OutlinedButton(
                            onClick = { onSubscribe(bout, if (isQ1) selectedLead else 0) },
                        ) {
                            Text(text = "Avisarme", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }
    }
}

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun NflGameCard(
    bouts: List<BoutOut>,
    subscribedBouts: Set<String>,
    onSubscribe: (BoutOut, Int) -> Unit,
) {
    val q1 = bouts.firstOrNull { it.matchNumber == 1 } ?: bouts.first()
    var selectedLead by remember { mutableStateOf(15) }
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceDark),
        border = BorderStroke(1.dp, NflBlue.copy(alpha = 0.5f)),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text(
                    text = "NFL",
                    color = NflBlue,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 1.sp,
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = formatDate(q1.date),
                    color = TextSecondary,
                    fontSize = 12.sp,
                )
            }
            Spacer(modifier = Modifier.height(12.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                AthleteColumn(q1.red?.name, q1.red?.headshotUrl, RedCorner)
                Text(
                    text = "VS",
                    color = Color.White.copy(alpha = 0.7f),
                    fontWeight = FontWeight.Bold,
                    modifier = Modifier.padding(horizontal = 12.dp),
                )
                AthleteColumn(q1.blue?.name, q1.blue?.headshotUrl, BlueCorner)
            }
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = "AVISOS",
                color = TextSecondary,
                fontSize = 11.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 1.sp,
            )
            Spacer(modifier = Modifier.height(8.dp))
            bouts.forEach { bout ->
                val quarterLabel = when (bout.matchNumber) {
                    1 -> "Inicio del partido"
                    2 -> "2º cuarto"
                    3 -> "3º cuarto"
                    4 -> "4º cuarto"
                    else -> "Q${bout.matchNumber}"
                }
                val isQ1 = bout.matchNumber == 1
                val subscribed = subscribedBouts.contains(bout.id)
                Row(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Column(modifier = Modifier.weight(1f)) {
                        Text(
                            text = quarterLabel,
                            color = Color.White,
                            fontSize = 13.sp,
                            fontWeight = FontWeight.SemiBold,
                        )
                        if (isQ1 && !subscribed) {
                            Spacer(modifier = Modifier.height(4.dp))
                            FlowRow(
                                horizontalArrangement = Arrangement.spacedBy(6.dp),
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
                            Text(
                                text = "min antes",
                                color = TextSecondary,
                                fontSize = 11.sp,
                            )
                        } else if (!isQ1 && !subscribed) {
                            Text(
                                text = "Cuando empieza",
                                color = TextSecondary,
                                fontSize = 11.sp,
                            )
                        }
                    }
                    if (subscribed) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Box(
                                modifier = Modifier
                                    .size(8.dp)
                                    .clip(CircleShape)
                                    .background(Color(0xFF4ADE80)),
                            )
                            Spacer(modifier = Modifier.width(6.dp))
                            Text(
                                text = "Avisando ✓",
                                color = Color(0xFF4ADE80),
                                fontSize = 12.sp,
                                fontWeight = FontWeight.SemiBold,
                            )
                        }
                    } else {
                        OutlinedButton(
                            onClick = { onSubscribe(bout, if (isQ1) selectedLead else 0) },
                        ) {
                            Text(text = "Avisarme", fontSize = 12.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun TennisCourtBadge(court: String) {
    Text(
        text = court.uppercase(),
        color = TennisClay,
        fontSize = 11.sp,
        fontWeight = FontWeight.SemiBold,
        modifier = Modifier
            .clip(RoundedCornerShape(4.dp))
            .background(TennisClay.copy(alpha = 0.18f))
            .padding(horizontal = 6.dp, vertical = 2.dp),
    )
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
                val painter = rememberAsyncImagePainter(
                    model = ImageRequest.Builder(LocalContext.current)
                        .data(display)
                        .crossfade(true)
                        .build(),
                )
                if (painter.state is AsyncImagePainter.State.Error) {
                    // Imagen rota o 404: degradar al avatar de iniciales.
                    AthleteAvatar(name, cornerColor)
                } else {
                    Image(
                        painter = painter,
                        contentDescription = name,
                        contentScale = ContentScale.Crop,
                        modifier = Modifier.fillMaxSize(),
                    )
                }
            } else {
                AthleteAvatar(name, cornerColor)
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

@Composable
private fun AthleteAvatar(name: String?, cornerColor: Color) {
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

private fun formatDate(iso: String): String = runCatching {
    val zoned = OffsetDateTime.parse(iso).atZoneSameInstant(ZoneId.systemDefault())
    val locale = Locale("es", "ES")
    zoned.format(DateTimeFormatter.ofPattern("d MMM \u00b7 HH:mm", locale))
}.getOrDefault(iso)

private fun formatBoutTime(iso: String): String = runCatching {
    OffsetDateTime.parse(iso).atZoneSameInstant(ZoneId.systemDefault())
        .format(DateTimeFormatter.ofPattern("HH:mm"))
}.getOrDefault("--:--")

@Composable
private fun AdSlot() {
    Card(
        modifier = Modifier.fillMaxWidth().height(160.dp),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceDark),
    ) {
        Box(
            modifier = Modifier.fillMaxSize(),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                text = "BILLETES",
                color = TextSecondary,
                fontSize = 14.sp,
            )
        }
    }
}