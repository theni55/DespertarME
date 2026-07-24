package com.despertarme.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.despertarme.app.ui.theme.AccentGreen
import com.despertarme.app.ui.theme.BackgroundDark
import com.despertarme.app.ui.theme.SurfaceDark
import com.despertarme.app.ui.theme.TextSecondary
import com.despertarme.app.ui.theme.UfcRed
import com.despertarme.app.ui.viewmodel.CompetitionUi
import com.despertarme.app.ui.viewmodel.CompetitionsState

@Composable
fun CompetitionsScreen(
    state: CompetitionsState,
    sport: String,
    onEventClick: (eventId: String, sport: String, league: String) -> Unit,
    onBack: () -> Unit,
) {
    Column(modifier = Modifier.fillMaxSize().background(BackgroundDark)) {
        val sportLabel = when (sport) {
            "tennis" -> "Tenis"
            else -> "MMA"
        }
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 4.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            IconButton(onClick = onBack) {
                Icon(
                    Icons.AutoMirrored.Filled.ArrowBack,
                    contentDescription = "Volver",
                    tint = Color.White,
                )
            }
            Text(
                text = sportLabel,
                color = Color.White,
                fontSize = 20.sp,
                fontWeight = FontWeight.Black,
                letterSpacing = 1.sp,
            )
        }
        Box(modifier = Modifier.fillMaxSize()) {
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
                state.tournaments.isEmpty() -> Text(
                    text = "No hay competiciones próximas ahora mismo.",
                    color = TextSecondary,
                    modifier = Modifier.align(Alignment.Center).padding(24.dp),
                    textAlign = TextAlign.Center,
                )
                else -> {
                    val atpList = state.tournaments.filter { it.league == "atp" }
                    val wtaList = state.tournaments.filter { it.league == "wta" }
                    val mmaList = state.tournaments.filter { it.sport == "mma" }
                    LazyColumn(
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                    ) {
                        if (atpList.isNotEmpty()) {
                            item {
                                SectionHeader(title = "ATP")
                            }
                            items(atpList, key = { "atp-${it.event.id}" }) { comp ->
                                CompetitionCard(
                                    comp = comp,
                                    onClick = {
                                        onEventClick(comp.event.id, comp.sport, comp.league)
                                    },
                                )
                            }
                        }
                        if (wtaList.isNotEmpty()) {
                            item {
                                SectionHeader(title = "WTA")
                            }
                            items(wtaList, key = { "wta-${it.event.id}" }) { comp ->
                                CompetitionCard(
                                    comp = comp,
                                    onClick = {
                                        onEventClick(comp.event.id, comp.sport, comp.league)
                                    },
                                )
                            }
                        }
                        if (mmaList.isNotEmpty()) {
                            items(mmaList, key = { "mma-${it.event.id}" }) { comp ->
                                CompetitionCard(
                                    comp = comp,
                                    onClick = {
                                        onEventClick(comp.event.id, comp.sport, comp.league)
                                    },
                                )
                            }
                        }
                        item { Spacer(modifier = Modifier.height(24.dp)) }
                    }
                }
            }
        }
    }
}

@Composable
private fun SectionHeader(title: String) {
    Text(
        text = title,
        color = Color.White.copy(alpha = 0.7f),
        fontSize = 14.sp,
        fontWeight = FontWeight.Bold,
        letterSpacing = 1.sp,
        modifier = Modifier.padding(top = 4.dp, bottom = 2.dp),
    )
}

@Composable
private fun CompetitionCard(
    comp: CompetitionUi,
    onClick: () -> Unit,
) {
    val leagueLabel = when (comp.league) {
        "atp" -> "ATP"
        "wta" -> "WTA"
        else -> null
    }
    val stripColor = when (comp.sport) {
        "tennis" -> AccentGreen
        else -> UfcRed
    }
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceDark),
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(72.dp)
                .background(
                    Brush.horizontalGradient(
                        listOf(stripColor.copy(alpha = 0.55f), SurfaceDark),
                    ),
                ),
            contentAlignment = Alignment.CenterStart,
        ) {
            if (leagueLabel != null) {
                Text(
                    text = leagueLabel,
                    color = Color.White,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Black,
                    letterSpacing = 2.sp,
                    modifier = Modifier.padding(start = 20.dp),
                )
            }
        }
        Row(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = comp.event.name,
                    color = Color.White,
                    fontSize = 17.sp,
                    fontWeight = FontWeight.Bold,
                    lineHeight = 22.sp,
                )
                Spacer(modifier = Modifier.height(4.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Box(
                        modifier = Modifier
                            .size(6.dp)
                            .clip(RoundedCornerShape(50))
                            .background(stripColor),
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = formatCompetitionDate(comp.event.date),
                        color = TextSecondary,
                        fontSize = 13.sp,
                    )
                }
            }
            Icon(
                imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = TextSecondary,
            )
        }
    }
}

private fun formatCompetitionDate(iso: String): String = runCatching {
    if (iso.length >= 16) "${iso.substring(0, 10)} · ${iso.substring(11, 16)} UTC" else iso
}.getOrDefault(iso)
