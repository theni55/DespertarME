package com.despertarme.app.ui.screens

import android.Manifest
import android.app.AlarmManager
import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Cancel
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.despertarme.app.ui.theme.BackgroundDark
import com.despertarme.app.ui.theme.SurfaceDark
import com.despertarme.app.ui.theme.TextSecondary
import java.util.TimeZone

@Composable
fun SettingsScreen(
    deviceId: String?,
    onTestAlarm: () -> Unit,
    onStopAlarm: () -> Unit,
) {
    val context = LocalContext.current
    var testPlaying by remember { mutableStateOf(false) }
    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(BackgroundDark)
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        Text(
            text = "AJUSTES",
            color = Color.White,
            fontSize = 20.sp,
            fontWeight = FontWeight.Black,
            letterSpacing = 1.sp,
        )
        SettingsCard(title = "Dispositivo") {
            LabelValue(label = "Device ID", value = deviceId ?: "sin registrar")
            Spacer(modifier = Modifier.height(8.dp))
            LabelValue(label = "Zona horaria", value = TimeZone.getDefault().id)
        }
        SettingsCard(title = "Permisos") {
            PermissionRow(
                label = "Notificaciones",
                granted = hasNotificationsPermission(context),
            )
            Spacer(modifier = Modifier.height(8.dp))
            PermissionRow(
                label = "Alarmas exactas",
                granted = canScheduleExactAlarms(context),
            )
        }
        SettingsCard(title = "Diagnóstico") {
            Text(
                text = "Comprueba que el sonido de alarma funciona aunque el móvil esté en silencio o No Molestar.",
                color = TextSecondary,
                fontSize = 13.sp,
            )
            Spacer(modifier = Modifier.height(12.dp))
            OutlinedButton(
                onClick = {
                    if (testPlaying) onStopAlarm() else onTestAlarm()
                    testPlaying = !testPlaying
                },
                shape = RoundedCornerShape(50),
                modifier = Modifier.fillMaxWidth(),
            ) {
                Text(
                    text = if (testPlaying) "Parar alarma" else "Probar alarma",
                    fontWeight = FontWeight.Bold,
                )
            }
        }
    }
}

@Composable
private fun SettingsCard(
    title: String,
    content: @Composable () -> Unit,
) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = SurfaceDark),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = title,
                color = TextSecondary,
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
                letterSpacing = 1.sp,
            )
            Spacer(modifier = Modifier.height(10.dp))
            content()
        }
    }
}

@Composable
private fun LabelValue(label: String, value: String) {
    Column {
        Text(text = label, color = TextSecondary, fontSize = 12.sp)
        Text(
            text = value,
            color = Color.White,
            fontSize = 13.sp,
            fontFamily = FontFamily.Monospace,
        )
    }
}

@Composable
private fun PermissionRow(label: String, granted: Boolean) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Icon(
            imageVector = if (granted) Icons.Filled.CheckCircle else Icons.Filled.Cancel,
            contentDescription = null,
            tint = if (granted) Color(0xFF4ADE80) else Color(0xFFCF6679),
            modifier = Modifier.size(18.dp),
        )
        Spacer(modifier = Modifier.width(8.dp))
        Text(text = label, color = Color.White, fontSize = 14.sp)
        Spacer(modifier = Modifier.weight(1f))
        Text(
            text = if (granted) "concedido" else "denegado",
            color = TextSecondary,
            fontSize = 12.sp,
        )
    }
}

private fun hasNotificationsPermission(context: Context): Boolean =
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
        context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) ==
            PackageManager.PERMISSION_GRANTED
    } else {
        true
    }

private fun canScheduleExactAlarms(context: Context): Boolean =
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
        (context.getSystemService(Context.ALARM_SERVICE) as AlarmManager).canScheduleExactAlarms()
    } else {
        true
    }
