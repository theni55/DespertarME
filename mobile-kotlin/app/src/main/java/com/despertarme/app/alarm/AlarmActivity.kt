package com.despertarme.app.alarm

import android.content.Intent
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
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

        val fighterRed = intent.getStringExtra("fighter_red") ?: "TBD"
        val fighterBlue = intent.getStringExtra("fighter_blue") ?: "TBD"
        val leadMinutes = intent.getIntExtra("lead_minutes", 15)
        val eventName = intent.getStringExtra("event_name") ?: ""

        setContent {
            AlarmFullScreen(
                fighterRed = fighterRed,
                fighterBlue = fighterBlue,
                eventName = eventName,
                leadMinutes = leadMinutes,
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
    onDismiss: () -> Unit,
    onOpenApp: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(Color(0xFF0A0A0A))
            .padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(
            text = "DespertarME",
            color = UfcRed,
            fontSize = 14.sp,
            fontWeight = FontWeight.Bold,
            letterSpacing = 2.sp,
        )
        Spacer(modifier = Modifier.height(16.dp))
        Text(
            text = "$fighterRed  VS  $fighterBlue",
            color = Color.White,
            fontSize = 28.sp,
            fontWeight = FontWeight.Black,
            textAlign = TextAlign.Center,
        )
        if (eventName.isNotBlank()) {
            Spacer(modifier = Modifier.height(8.dp))
            Text(
                text = eventName,
                color = Color.White.copy(alpha = 0.7f),
                fontSize = 14.sp,
                textAlign = TextAlign.Center,
            )
        }
        Spacer(modifier = Modifier.height(24.dp))
        Text(
            text = "Empieza en ~$leadMinutes min",
            color = Color.White.copy(alpha = 0.8f),
            fontSize = 18.sp,
            fontWeight = FontWeight.SemiBold,
        )
        Spacer(modifier = Modifier.height(48.dp))
        Button(
            onClick = onDismiss,
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(50),
            colors = ButtonDefaults.buttonColors(containerColor = UfcRed),
        ) {
            Text(
                text = "Descartar",
                fontWeight = FontWeight.Bold,
                fontSize = 16.sp,
                modifier = Modifier.padding(vertical = 4.dp),
            )
        }
        Spacer(modifier = Modifier.height(12.dp))
        Button(
            onClick = onOpenApp,
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(50),
            colors = ButtonDefaults.buttonColors(
                containerColor = Color.White.copy(alpha = 0.15f),
            ),
        ) {
            Text(
                text = "Abrir app",
                fontWeight = FontWeight.Medium,
                fontSize = 16.sp,
                modifier = Modifier.padding(vertical = 4.dp),
            )
        }
    }
}
