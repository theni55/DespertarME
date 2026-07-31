package com.despertarme.app.alarm

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class AlarmReceiver : BroadcastReceiver() {

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

        // D45 — Ring-once: marcar fired=true ANTES de que suene para que cualquier
        // push `update` que llegue en el rato entre ahora y el sonido sea ignorado.
        CoroutineScope(Dispatchers.IO).launch {
            PendingAlarmStorage.put(
                ctx,
                (PendingAlarmStorage.get(ctx, boutId) ?: return@launch).copy(fired = true),
            )
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

        // Abrir pantalla a pantalla completa sobre lockscreen.
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
        ctx.startActivity(activityIntent)

        Log.i("AlarmReceiver", "Alarma disparada y fired=true marcado para bout=$boutId")
    }
}
