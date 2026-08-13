package com.despertarme.app.ui.screens

import android.Manifest
import android.app.AlarmManager
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Cancel
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
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
    onBack: () -> Unit,
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
        // D46: Ajustes ya no está en la bottom nav — header con volver.
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onBack) {
                Icon(
                    imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                    contentDescription = "Volver",
                    tint = Color.White,
                )
            }
            Text(
                text = "AJUSTES",
                color = Color.White,
                fontSize = 20.sp,
                fontWeight = FontWeight.Black,
                letterSpacing = 1.sp,
            )
        }
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
            if (Build.VERSION.SDK_INT >= 34) {
                Spacer(modifier = Modifier.height(8.dp))
                FullScreenIntentRow(context)
            }
            if (isXiaomiDevice()) {
                Spacer(modifier = Modifier.height(12.dp))
                XiaomiPopupPermissionRow(context)
            }
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

private fun isXiaomiDevice(): Boolean =
    Build.MANUFACTURER.equals("Xiaomi", ignoreCase = true) ||
        Build.BRAND.equals("Redmi", ignoreCase = true) ||
        Build.BRAND.equals("POCO", ignoreCase = true)

@Composable
private fun XiaomiPopupPermissionRow(context: Context) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .clickable {
                val miuiIntent = Intent("miui.intent.action.APP_PERM_EDITOR").apply {
                    setClassName(
                        "com.miui.securitycenter",
                        "com.miui.permcenter.permissions.PermissionsEditorActivity",
                    )
                    putExtra("extra_pkgname", context.packageName)
                }
                runCatching { context.startActivity(miuiIntent) }
                    .onFailure {
                        val fallback = Intent(
                            Settings.ACTION_APPLICATION_DETAILS_SETTINGS,
                            Uri.parse("package:${context.packageName}"),
                        )
                        context.startActivity(fallback)
                    }
            }
            .padding(vertical = 4.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                imageVector = Icons.Filled.Cancel,
                contentDescription = null,
                tint = Color(0xFFFFB74D),
                modifier = Modifier.size(18.dp),
            )
            Spacer(modifier = Modifier.width(8.dp))
            Text(text = "Ventana emergente Xiaomi", color = Color.White, fontSize = 14.sp)
            Spacer(modifier = Modifier.weight(1f))
            Text(
                text = "CONFIGURAR",
                color = com.despertarme.app.ui.theme.UfcRed,
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
            )
        }
        Spacer(modifier = Modifier.height(6.dp))
        Text(
            text = "En Otros permisos activa Mostrar ventanas emergentes en segundo plano para ver la alarma sobre el bloqueo de MIUI.",
            color = TextSecondary,
            fontSize = 12.sp,
        )
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

@Composable
private fun FullScreenIntentRow(context: Context) {
    val nm = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
    val granted = nm.canUseFullScreenIntent()
    Row(
        verticalAlignment = Alignment.CenterVertically,
        modifier = if (!granted) Modifier.clickable {
            val intent = Intent(
                Settings.ACTION_MANAGE_APP_USE_FULL_SCREEN_INTENT,
                Uri.parse("package:${context.packageName}"),
            )
            context.startActivity(intent)
        } else Modifier,
    ) {
        Icon(
            imageVector = if (granted) Icons.Filled.CheckCircle else Icons.Filled.Cancel,
            contentDescription = null,
            tint = if (granted) Color(0xFF4ADE80) else Color(0xFFCF6679),
            modifier = Modifier.size(18.dp),
        )
        Spacer(modifier = Modifier.width(8.dp))
        Text(text = "Pantalla bloqueo", color = Color.White, fontSize = 14.sp)
        Spacer(modifier = Modifier.weight(1f))
        if (!granted) {
            Text(
                text = "CONFIGURAR",
                color = com.despertarme.app.ui.theme.UfcRed,
                fontSize = 12.sp,
                fontWeight = FontWeight.Bold,
            )
        } else {
            Text(
                text = "concedido",
                color = TextSecondary,
                fontSize = 12.sp,
            )
        }
    }
}
