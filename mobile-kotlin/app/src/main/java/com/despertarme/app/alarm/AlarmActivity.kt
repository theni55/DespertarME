package com.despertarme.app.alarm

import android.content.Intent
import android.app.ActivityManager
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
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
import com.despertarme.app.ui.theme.BackgroundDark
import com.despertarme.app.ui.theme.BlueCorner
import com.despertarme.app.ui.theme.FootballGreen
import com.despertarme.app.ui.theme.NbaBlue
import com.despertarme.app.ui.theme.RedCorner
import com.despertarme.app.ui.theme.TextSecondary
import com.despertarme.app.ui.theme.UfcRed

class AlarmActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setShowWhenLocked(true)
        setTurnScreenOn(true)
        @Suppress("DEPRECATION")
        window.addFlags(
            WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or
                WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON or
                WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON,
        )

        // Safety net: si el AlarmReceiver no pudo arrancar el servicio
        // (ej. restricción de background en Android 14+), lo arrancamos
        // aquí directamente para que el sonido suene.
        if (!isAlarmServiceRunning()) {
            val serviceIntent = Intent(this, AlarmService::class.java).apply {
                action = AlarmService.ACTION_START
            }
            startForegroundService(serviceIntent)
        }

        val fighterRed = intent.getStringExtra("fighter_red") ?: "TBD"
        val fighterBlue = intent.getStringExtra("fighter_blue") ?: "TBD"
        val leadMinutes = intent.getIntExtra("lead_minutes", 15)
        val eventName = intent.getStringExtra("event_name") ?: ""
        val headshotRed = intent.getStringExtra("headshot_red")
        val headshotBlue = intent.getStringExtra("headshot_blue")
        val sport = intent.getStringExtra("sport") ?: "mma"

        setContent {
            AlarmFullScreen(
                fighterRed = fighterRed,
                fighterBlue = fighterBlue,
                eventName = eventName,
                leadMinutes = leadMinutes,
                headshotRed = headshotRed,
                headshotBlue = headshotBlue,
                sport = sport,
                onDismiss = {
                    stopService(Intent(this, AlarmService::class.java).apply {
                        action = AlarmService.ACTION_STOP
                    })
                    finish()
                },
                onOpenApp = {
                    stopService(Intent(this, AlarmService::class.java).apply {
                        action = AlarmService.ACTION_STOP
                    })
                    val intent = Intent(this, com.despertarme.app.MainActivity::class.java).apply {
                        addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
                    }
                    startActivity(intent)
                    finish()
                },
            )
        }
    }
}

@Composable
private fun AlarmFullScreen(
    fighterRed: String,
    fighterBlue: String,
    eventName: String,
    leadMinutes: Int,
    headshotRed: String?,
    headshotBlue: String?,
    sport: String,
    onDismiss: () -> Unit,
    onOpenApp: () -> Unit,
) {
    val accentColor = when (sport) {
        "tennis" -> com.despertarme.app.ui.theme.AccentGreen
        "nba" -> NbaBlue
        "football" -> FootballGreen
        else -> UfcRed
    }
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundDark)
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = "DespertarME",
            color = accentColor,
            fontSize = 14.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 2.sp,
        )
        Spacer(modifier = Modifier.height(8.dp))
        if (eventName.isNotBlank()) {
            Text(
                text = eventName,
                color = Color.White.copy(alpha = 0.85f),
                fontSize = 16.sp,
                fontWeight = FontWeight.SemiBold,
                textAlign = TextAlign.Center,
            )
        }
        Spacer(modifier = Modifier.height(32.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            AthleteColumn(fighterRed, headshotRed, RedCorner)
            Text(
                text = "VS",
                color = Color.White.copy(alpha = 0.7f),
                fontWeight = FontWeight.Bold,
                fontSize = 18.sp,
                modifier = Modifier.padding(horizontal = 16.dp),
            )
            AthleteColumn(fighterBlue, headshotBlue, BlueCorner)
        }
        Spacer(modifier = Modifier.height(24.dp))
        Text(
            text = if (leadMinutes > 0) "Empieza en ~$leadMinutes min" else "Empieza ahora",
            color = Color.White.copy(alpha = 0.8f),
            fontSize = 16.sp,
            fontWeight = FontWeight.SemiBold,
        )
        Spacer(modifier = Modifier.height(40.dp))
        Button(
            onClick = onDismiss,
            modifier = Modifier.fillMaxWidth().height(52.dp),
            shape = RoundedCornerShape(50),
            colors = ButtonDefaults.buttonColors(containerColor = accentColor),
        ) {
            Text(
                text = "DETENER",
                fontWeight = FontWeight.Black,
                fontSize = 18.sp,
                letterSpacing = 2.sp,
                modifier = Modifier.padding(vertical = 2.dp),
            )
        }
        Spacer(modifier = Modifier.height(14.dp))
        OutlinedButton(
            onClick = onOpenApp,
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(50),
        ) {
            Text(
                text = "Abrir app",
                fontWeight = FontWeight.Medium,
                fontSize = 14.sp,
            )
        }
    }
}

@Composable
private fun AthleteColumn(name: String, headshotUrl: String?, cornerColor: Color) {
    Column(
        modifier = Modifier.width(120.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier = Modifier
                .size(72.dp)
                .clip(CircleShape)
                .background(cornerColor.copy(alpha = 0.40f)),
            contentAlignment = Alignment.Center,
        ) {
            if (headshotUrl != null) {
                AsyncImage(
                    model = ImageRequest.Builder(LocalContext.current)
                        .data(headshotUrl)
                        .crossfade(true)
                        .build(),
                    contentDescription = name,
                    contentScale = ContentScale.Crop,
                    modifier = Modifier.fillMaxSize(),
                )
            } else {
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
                        modifier = Modifier.size(32.dp),
            )
        }
    }

    private fun isAlarmServiceRunning(): Boolean {
        val manager = getSystemService(ACTIVITY_SERVICE) as ActivityManager
        return manager.getRunningServices(Int.MAX_VALUE)
            .any { it.service.className == AlarmService::class.java.name }
    }
}
        Spacer(modifier = Modifier.height(6.dp))
        Text(
            text = name,
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
        first.toString().uppercase()
    }
    return initial.uppercase()
}
