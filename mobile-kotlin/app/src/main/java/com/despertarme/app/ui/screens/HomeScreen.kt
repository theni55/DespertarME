package com.despertarme.app.ui.screens

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.NotificationsActive
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.despertarme.app.R
import com.despertarme.app.ui.theme.UfcRed

/**
 * Home screen (Paso 1-2 of Fase 7b): hero background + single CTA
 * "Avísame" that jumps straight into the next event's EventDetail. Optimistic
 * UX: while there's no next event known yet we show a small loading indicator
 * but still allow tapping the button which will resolve the event on navigation.
 */
@Composable
fun HomeScreen(
    isLoading: Boolean,
    onNextEvent: () -> Unit,
    onTestAlarm: () -> Unit,
) {
    Box(modifier = Modifier.fillMaxSize().background(Color(0xFF0A0A0A))) {
        // Hero: embebido localmente. drawable-nodpi/hero.webp fue volcado desde
        // la rama `web` del backend (cartel UFC 329, D36/D42).
        Image(
            painter = painterResource(R.drawable.hero),
            contentDescription = null,
            contentScale = ContentScale.Crop,
            modifier = Modifier.fillMaxSize(),
        )
        // Veil for legibility (matches landing web D36).
        Box(
            modifier = Modifier
                .fillMaxSize()
                .background(
                    Brush.verticalGradient(
                        0f to Color.Black.copy(alpha = 0.65f),
                        0.6f to Color.Black.copy(alpha = 0.35f),
                        1f to Color.Black.copy(alpha = 0.85f),
                    ),
                ),
        )
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(horizontal = 24.dp, vertical = 32.dp),
            verticalArrangement = Arrangement.SpaceBetween,
        ) {
            Spacer(modifier = Modifier.height(40.dp))
            Column(
                modifier = Modifier.fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                Text(
                    text = "DESPERTARME",
                    color = Color.White,
                    fontSize = 14.sp,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 6.sp,
                )
                Spacer(modifier = Modifier.height(8.dp))
                Text(
                    text = "No te pierdas el combate.",
                    color = Color.White,
                    fontSize = 28.sp,
                    fontWeight = FontWeight.Bold,
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = "Te avisamos antes de que empiece.",
                    color = Color.White.copy(alpha = 0.85f),
                    fontSize = 16.sp,
                )
            }
            Column(
                modifier = Modifier.fillMaxWidth(),
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                if (isLoading) {
                    CircularProgressIndicator(
                        color = UfcRed,
                        strokeWidth = 2.dp,
                        modifier = Modifier.size(20.dp),
                    )
                    Spacer(modifier = Modifier.height(12.dp))
                }
                Button(
                    onClick = onNextEvent,
                    shape = RoundedCornerShape(50),
                    colors = ButtonDefaults.buttonColors(containerColor = UfcRed),
                    modifier = Modifier.fillMaxWidth().height(56.dp),
                ) {
                    Icon(
                        imageVector = Icons.Filled.NotificationsActive,
                        contentDescription = null,
                    )
                    Spacer(modifier = Modifier.size(8.dp))
                    Text(
                        text = "Avísame",
                        fontSize = 18.sp,
                        fontWeight = FontWeight.Bold,
                    )
                }
                Spacer(modifier = Modifier.height(12.dp))
                OutlinedButton(
                    onClick = onTestAlarm,
                    shape = RoundedCornerShape(50),
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    Text(text = "Probar sonido")
                }
            }
        }
    }
}