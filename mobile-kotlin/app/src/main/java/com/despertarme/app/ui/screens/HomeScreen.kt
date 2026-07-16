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
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.layout.WindowInsets
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
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.despertarme.app.R
import com.despertarme.app.ui.theme.BackgroundDark
import com.despertarme.app.ui.theme.UfcRed

@Composable
fun HomeScreen(
    isLoading: Boolean,
    onNextEvent: () -> Unit,
    onTestAlarm: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundDark)
            .windowInsetsPadding(WindowInsets.safeDrawing),
    ) {
        // Top zone: hero poster scaled to fit (no crop) — both fighters visible.
        // The webp has the McGregor vs Holloway 2 UFC 329 carte l; Fit keeps
        // the whole poster visible regardless of device aspect ratio.
        Image(
            painter = painterResource(R.drawable.hero),
            contentDescription = null,
            contentScale = ContentScale.Fit,
            modifier = Modifier.fillMaxWidth().weight(1f),
        )
        // Bottom zone: fixed-height area on solid dark background so the CTA
        // is always visible above the gesture nav bar.
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .background(BackgroundDark)
                .padding(horizontal = 24.dp, vertical = 16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(
                text = "DESPERTARME",
                color = Color.White,
                fontSize = 14.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 6.sp,
            )
            Spacer(modifier = Modifier.height(6.dp))
            Text(
                text = "No te pierdas el combate.",
                color = Color.White,
                fontSize = 22.sp,
                fontWeight = FontWeight.Bold,
            )
            Spacer(modifier = Modifier.height(2.dp))
            Text(
                text = "Te avisamos antes de que empiece.",
                color = Color.White.copy(alpha = 0.85f),
                fontSize = 14.sp,
            )
            Spacer(modifier = Modifier.height(16.dp))
            if (isLoading) {
                CircularProgressIndicator(
                    color = UfcRed,
                    strokeWidth = 2.dp,
                    modifier = Modifier.size(20.dp),
                )
                Spacer(modifier = Modifier.height(8.dp))
            } else {
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
                Spacer(modifier = Modifier.height(10.dp))
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