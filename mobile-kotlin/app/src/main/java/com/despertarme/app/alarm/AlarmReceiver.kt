package com.despertarme.app.alarm

import android.app.NotificationManager
import android.app.PendingIntent
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.runBlocking

class AlarmReceiver : BroadcastReceiver() {

    companion object {
        const val FULLSCREEN_NOTIFICATION_ID = 2
    }

    override fun onReceive(rawContext: Context, intent: Intent) {
        if (intent.action != AlarmScheduler.ALARM_ACTION) return

        val boutId = intent.getStringExtra("bout_id") ?: return
        val eventId = intent.getStringExtra("event_id") ?: return
        val fighterRed = intent.getStringExtra("fighter_red") ?: "TBD"
        val fighterBlue = intent.getStringExtra("fighter_blue") ?: "TBD"
        val leadMinutes = intent.getIntExtra("lead_minutes", 15)
        val eventName = intent.getStringExtra("event_name") ?: ""
        val headshotRed = intent.getStringExtra("headshot_red")
        val headshotBlue = intent.getStringExtra("headshot_blue")
        val sport = intent.getStringExtra("sport") ?: "mma"

        val ctx = rawContext.applicationContext

        // D45 — Ring-once: marcar fired=true ANTES de que suene.
        // runBlocking garantiza escritura sincrona en DataStore antes de que
        // onReceive retorne. Sin esto, un fire-and-forget async (CoroutineScope)
        // podria perder el write si el proceso muere antes del flush.
        runBlocking(Dispatchers.IO) {
            val existing = PendingAlarmStorage.get(ctx, boutId)
            if (existing != null) {
                PendingAlarmStorage.put(ctx, existing.copy(fired = true))
            }
        }

        // Arrancar el sonido de alarma.
        val serviceIntent = Intent(ctx, AlarmService::class.java).apply {
            action = AlarmService.ACTION_START
        }
        try {
            ctx.startForegroundService(serviceIntent)
        } catch (e: Exception) {
            Log.w("AlarmReceiver", "No se pudo arrancar AlarmService como foreground: ${e.message}")
            try {
                ctx.startService(serviceIntent)
            } catch (e2: Exception) {
                Log.e("AlarmReceiver", "No se pudo arrancar AlarmService: ${e2.message}")
            }
        }

        val activityIntent = Intent(ctx, AlarmActivity::class.java).apply {
            putExtra("bout_id", boutId)
            putExtra("event_id", eventId)
            putExtra("fighter_red", fighterRed)
            putExtra("fighter_blue", fighterBlue)
            putExtra("lead_minutes", leadMinutes)
            putExtra("event_name", eventName)
            headshotRed?.let { putExtra("headshot_red", it) }
            headshotBlue?.let { putExtra("headshot_blue", it) }
            putExtra("sport", sport)
            addFlags(
                Intent.FLAG_ACTIVITY_NEW_TASK or
                    Intent.FLAG_ACTIVITY_CLEAR_TOP or
                    Intent.FLAG_ACTIVITY_NO_USER_ACTION,
            )
        }
        val pendingFlags = if (Build.VERSION.SDK_INT >= 31) {
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        } else {
            PendingIntent.FLAG_UPDATE_CURRENT
        }
        val nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager

        // Full-screen intent si el permiso esta concedido (Android 14+).
        // Si no, fallback a startActivity directo desde el BroadcastReceiver.
        val canFsi = if (Build.VERSION.SDK_INT >= 34) {
            nm.canUseFullScreenIntent()
        } else {
            true
        }

        val stopPendingIntent = PendingIntent.getService(
            ctx, boutId.hashCode() + 1, serviceIntent.apply { action = AlarmService.ACTION_STOP },
            pendingFlags,
        )

        if (canFsi) {
            val activityPendingIntent = PendingIntent.getActivity(
                ctx, boutId.hashCode(), activityIntent, pendingFlags,
            )
            val notification = NotificationCompat.Builder(ctx, AlarmService.CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
                .setContentTitle("DespertarME")
                .setContentText("$fighterRed vs $fighterBlue — $eventName")
                .setCategory(NotificationCompat.CATEGORY_ALARM)
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
                .setFullScreenIntent(activityPendingIntent, true)
                .setOngoing(true)
                .addAction(android.R.drawable.ic_media_pause, "Parar", stopPendingIntent)
                .build()
            nm.cancel(AlarmService.NOTIFICATION_ID)
            nm.notify(FULLSCREEN_NOTIFICATION_ID, notification)
        } else {
            try {
                ctx.startActivity(activityIntent)
            } catch (e: Exception) {
                Log.e("AlarmReceiver", "No se pudo abrir AlarmActivity: ${e.message}")
            }
        }

        Log.i("AlarmReceiver", "Alarma disparada y fired=true marcado para bout=$boutId")

        Log.i("AlarmReceiver", "Alarma disparada y fired=true marcado para bout=$boutId")
    }
}