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
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.SportsMma
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
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
import com.despertarme.app.data.remote.EventSummaryOut
import com.despertarme.app.ui.theme.BackgroundDark
import com.despertarme.app.ui.theme.SurfaceDark
import com.despertarme.app.ui.theme.TextSecondary
import com.despertarme.app.ui.theme.UfcRed
import com.despertarme.app.ui.viewmodel.EventListState

@Composable
fun EventListScreen(
    state: EventListState,
    onEventClick: (EventSummaryOut) -> Unit,
) {
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
            state.events.isEmpty() -> Text(
                text = "No hay eventos próximos ahora mismo.",
                color = TextSecondary,
                modifier = Modifier.align(Alignment.Center).padding(24.dp),
                textAlign = TextAlign.Center,
            )
            else -> LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(horizontal = 16.dp, vertical = 16.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) {
                item {
                    Text(
                        text = "PRÓXIMOS EVENTOS",
                        color = Color.White,
                        fontSize = 20.sp,
                        fontWeight = FontWeight.Black,
                        letterSpacing = 1.sp,
                        modifier = Modifier.padding(bottom = 4.dp),
                    )
                }
                items(state.events, key = { it.id }) { event ->
                    EventCard(event = event, onClick = { onEventClick(event) })
                }
            }
        }
    }
}

@Composable
private fun EventCard(
    event: EventSummaryOut,
    onClick: () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceDark),
    ) {
        // ESPN no sirve image_url todavia (D42) — franja degradada roja como
        // sustituto visual de la foto a toda anchura de la referencia Winamax.
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(72.dp)
                .background(
                    Brush.horizontalGradient(
                        listOf(UfcRed.copy(alpha = 0.55f), SurfaceDark),
                    ),
                ),
            contentAlignment = Alignment.CenterStart,
        ) {
            Icon(
                imageVector = Icons.Filled.SportsMma,
                contentDescription = null,
                tint = Color.White.copy(alpha = 0.9f),
                modifier = Modifier.padding(start = 20.dp).size(36.dp),
            )
        }
        Row(
            modifier = Modifier.fillMaxWidth().padding(16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = event.name,
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
                            .background(UfcRed),
                    )
                    Spacer(modifier = Modifier.width(6.dp))
                    Text(
                        text = formatEventDate(event.date),
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

private fun formatEventDate(iso: String): String = runCatching {
    if (iso.length >= 16) "${iso.substring(0, 10)} · ${iso.substring(11, 16)} UTC" else iso
}.getOrDefault(iso)
