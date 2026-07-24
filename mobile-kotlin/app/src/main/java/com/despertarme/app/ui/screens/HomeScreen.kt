package com.despertarme.app.ui.screens

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
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
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.Alarm
import androidx.compose.material.icons.filled.NotificationsActive
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import coil.request.ImageRequest
import com.despertarme.app.data.remote.BoutAthleteOut
import com.despertarme.app.ui.theme.BackgroundDark
import com.despertarme.app.ui.theme.BlueCorner
import com.despertarme.app.ui.theme.ErrorRed
import com.despertarme.app.ui.theme.PosterSurface
import com.despertarme.app.ui.theme.RedCorner
import com.despertarme.app.ui.theme.SurfaceDark
import com.despertarme.app.ui.theme.TextSecondary
import com.despertarme.app.ui.theme.UfcRed
import com.despertarme.app.ui.theme.UfcRedDeep
import com.despertarme.app.ui.viewmodel.HomeEventUi
import com.despertarme.app.ui.viewmodel.HomeState
import java.time.LocalDate
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * Home rediseñado estilo Winamax (Sesión 23, D46): lista de N próximos eventos
 * como cards destacadas con CTA "Avísame" propio. Sin botón global ni hero
 * estático — el póster de cada card se compone con los headshots reales del
 * main event (D47) sobre un backdrop dibujado (glows rojo/azul del octágono).
 */
@Composable
fun HomeScreen(
    state: HomeState,
    onEventClick: (String) -> Unit,
    onRetry: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundDark),
    ) {
        BrandHeader()
        Box(modifier = Modifier.fillMaxSize()) {
            when {
                state.isLoading -> CircularProgressIndicator(
                    color = UfcRed,
                    modifier = Modifier.align(Alignment.Center),
                )
                state.error != null -> Column(
                    modifier = Modifier.align(Alignment.Center).padding(24.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text(
                        text = state.error,
                        color = ErrorRed,
                        textAlign = TextAlign.Center,
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                    OutlinedButton(onClick = onRetry, shape = RoundedCornerShape(50)) {
                        Text(text = "Reintentar")
                    }
                }
                state.events.isEmpty() -> Text(
                    text = "No hay eventos próximos ahora mismo.",
                    color = TextSecondary,
                    modifier = Modifier.align(Alignment.Center).padding(24.dp),
                    textAlign = TextAlign.Center,
                )
                else -> LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 4.dp),
                    verticalArrangement = Arrangement.spacedBy(16.dp),
                ) {
                    item {
                        Text(
                            text = "Próximos eventos",
                            color = Color.White,
                            fontSize = 22.sp,
                            fontWeight = FontWeight.Black,
                        )
                    }
                    items(state.events, key = { it.event.id }) { ui ->
                        HomeEventCard(ui = ui, onClick = { onEventClick(ui.event.id) })
                    }
                    item { Spacer(modifier = Modifier.height(8.dp)) }
                }
            }
        }
    }
}

@Composable
private fun BrandHeader() {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(
            imageVector = Icons.Filled.Alarm,
            contentDescription = null,
            tint = UfcRed,
            modifier = Modifier.size(22.dp),
        )
        Spacer(modifier = Modifier.width(8.dp))
        Text(
            text = "DESPERTARME",
            color = Color.White,
            fontSize = 16.sp,
            fontWeight = FontWeight.Black,
            letterSpacing = 3.sp,
        )
    }
}

@Composable
private fun HomeEventCard(
    ui: HomeEventUi,
    onClick: () -> Unit,
) {
    val dateParts = eventDateParts(ui.event.date)
    Card(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceDark),
    ) {
        // Strip superior con la liga — patrón header de card Winamax.
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .background(Brush.horizontalGradient(listOf(UfcRed, UfcRedDeep)))
                .padding(horizontal = 14.dp, vertical = 9.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                text = "UFC",
                color = Color.White,
                fontSize = 13.sp,
                fontWeight = FontWeight.Black,
                letterSpacing = 1.sp,
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(
                text = buildString {
                    append("MMA")
                    val n = ui.boutCount
                    if (n != null && n > 0) append(" · $n combates")
                },
                color = Color.White.copy(alpha = 0.85f),
                fontSize = 12.sp,
            )
            Spacer(modifier = Modifier.weight(1f))
            Icon(
                imageVector = Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = Color.White.copy(alpha = 0.9f),
                modifier = Modifier.size(18.dp),
            )
        }
        // Área de póster: backdrop dibujado (D47) + headshots del main event
        // anclados abajo + fecha/hora centradas (patrón "equipo | hora | equipo").
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .height(180.dp)
                .drawBehind {
                    drawRect(color = PosterSurface)
                    val radius = size.width * 0.55f
                    drawCircle(
                        brush = Brush.radialGradient(
                            colors = listOf(RedCorner.copy(alpha = 0.35f), Color.Transparent),
                            center = Offset(0f, size.height),
                            radius = radius,
                        ),
                        center = Offset(0f, size.height),
                        radius = radius,
                    )
                    drawCircle(
                        brush = Brush.radialGradient(
                            colors = listOf(BlueCorner.copy(alpha = 0.30f), Color.Transparent),
                            center = Offset(size.width, size.height),
                            radius = radius,
                        ),
                        center = Offset(size.width, size.height),
                        radius = radius,
                    )
                },
        ) {
            Row(
                modifier = Modifier.fillMaxSize(),
                verticalAlignment = Alignment.Bottom,
            ) {
                Box(
                    modifier = Modifier.weight(1f).fillMaxHeight(),
                    contentAlignment = Alignment.BottomCenter,
                ) {
                    FighterFigure(athlete = ui.mainRed, cornerColor = RedCorner)
                }
                Spacer(modifier = Modifier.width(96.dp))
                Box(
                    modifier = Modifier.weight(1f).fillMaxHeight(),
                    contentAlignment = Alignment.BottomCenter,
                ) {
                    FighterFigure(athlete = ui.mainBlue, cornerColor = BlueCorner)
                }
            }
            Column(
                modifier = Modifier.align(Alignment.Center),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text(
                    text = dateParts.dayLabel,
                    color = TextSecondary,
                    fontSize = 12.sp,
                    fontWeight = FontWeight.SemiBold,
                    letterSpacing = 1.sp,
                )
                Text(
                    text = dateParts.timeLabel,
                    color = Color.White,
                    fontSize = 28.sp,
                    fontWeight = FontWeight.Black,
                )
            }
        }
        // Pie: nombre del evento + main event + CTA propio de la card.
        Column(modifier = Modifier.fillMaxWidth().padding(16.dp)) {
            Text(
                text = ui.event.name,
                color = Color.White,
                fontSize = 17.sp,
                fontWeight = FontWeight.Bold,
                lineHeight = 22.sp,
            )
            val red = ui.mainRed?.name
            val blue = ui.mainBlue?.name
            if (red != null || blue != null) {
                Spacer(modifier = Modifier.height(3.dp))
                Text(
                    text = "Main event: ${red ?: "TBD"} vs ${blue ?: "TBD"}",
                    color = TextSecondary,
                    fontSize = 13.sp,
                )
            }
            Spacer(modifier = Modifier.height(14.dp))
            Button(
                onClick = onClick,
                shape = RoundedCornerShape(50),
                colors = ButtonDefaults.buttonColors(containerColor = UfcRed),
                modifier = Modifier.fillMaxWidth().height(48.dp),
            ) {
                Icon(
                    imageVector = Icons.Filled.NotificationsActive,
                    contentDescription = null,
                    modifier = Modifier.size(20.dp),
                )
                Spacer(modifier = Modifier.width(8.dp))
                Text(
                    text = "Avísame",
                    fontSize = 16.sp,
                    fontWeight = FontWeight.Bold,
                )
            }
        }
    }
}

@Composable
private fun FighterFigure(athlete: BoutAthleteOut?, cornerColor: Color) {
    val url = athlete?.headshotUrl
    if (url != null) {
        AsyncImage(
            model = ImageRequest.Builder(LocalContext.current)
                .data(url)
                .crossfade(true)
                .build(),
            contentDescription = athlete.name,
            contentScale = ContentScale.Fit,
            modifier = Modifier.fillMaxHeight().padding(top = 12.dp),
        )
    } else {
        // Sin headshot (TBD, debutante o carga en curso): avatar de iniciales
        // sobre el color de la esquina — mismo patrón que EventDetail.
        Box(
            modifier = Modifier
                .padding(bottom = 40.dp)
                .size(72.dp)
                .clip(CircleShape)
                .background(cornerColor.copy(alpha = 0.35f)),
            contentAlignment = Alignment.Center,
        ) {
            Text(
                text = figureInitials(athlete?.name),
                color = Color.White,
                fontWeight = FontWeight.Bold,
                fontSize = 18.sp,
            )
        }
    }
}

private fun figureInitials(name: String?): String {
    if (name.isNullOrBlank()) return "?"
    val parts = name.trim().split(' ').filter { it.isNotEmpty() }
    val first = parts.firstOrNull()?.firstOrNull() ?: return "?"
    val last = if (parts.size >= 2) parts.last().firstOrNull() else null
    return listOfNotNull(first, last).joinToString("").uppercase(Locale.getDefault())
}

/** Fecha/hora de la card en zona horaria del dispositivo, estilo Winamax ("HOY · 21:00"). */
private data class EventDateParts(val dayLabel: String, val timeLabel: String)

private fun eventDateParts(iso: String): EventDateParts {
    val zoned = parseToDeviceZone(iso)
        ?: return EventDateParts(dayLabel = iso, timeLabel = "")
    val today = LocalDate.now(zoned.zone)
    val locale = Locale("es", "ES")
    val dayLabel = when (zoned.toLocalDate()) {
        today -> "HOY"
        today.plusDays(1) -> "MAÑANA"
        else -> zoned.format(DateTimeFormatter.ofPattern("EEE d MMM", locale))
            .replace(".", "")
            .uppercase(locale)
    }
    return EventDateParts(
        dayLabel = dayLabel,
        timeLabel = zoned.format(DateTimeFormatter.ofPattern("HH:mm", locale)),
    )
}

private fun parseToDeviceZone(iso: String): ZonedDateTime? = runCatching {
    OffsetDateTime.parse(iso).atZoneSameInstant(ZoneId.systemDefault())
}.getOrNull()
