package com.despertarme.app.fcm

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.util.Log
import androidx.core.app.NotificationCompat
import com.despertarme.app.DespertarMeApp
import com.despertarme.app.MainActivity
import com.despertarme.app.R
import com.despertarme.app.alarm.AlarmActivity
import com.despertarme.app.alarm.AlarmScheduler
import com.despertarme.app.alarm.AlarmService
import com.despertarme.app.alarm.PendingAlarmStorage
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class DespertarMeFirebaseService : FirebaseMessagingService() {

    companion object {
        private const val TAG = "FcmMessaging"
        private const val INFO_CHANNEL_ID = "despertarme.info"
        private const val INFO_NOTIFICATION_ID = 100
    }

    override fun onCreate() {
        super.onCreate()
        ensureInfoChannel()
    }

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Log.i(TAG, "Nuevo FCM token: $token")

        // El token puede llegar antes de que AppContainer esté inicializado
        // (FirebaseInitProvider arranca antes que Application.onCreate).
        // Persistimos en DataStore directamente y el backend lo recoge luego
        // en `ensureRegistered()` via DeviceStorage.
        val storage = com.despertarme.app.data.DeviceStorage(applicationContext)
        CoroutineScope(Dispatchers.IO).launch {
            storage.setFcmToken(token)
        }

        // Si el AppContainer ya está listo, registramos el token con el backend.
        val app = application as DespertarMeApp
        if (app.isContainerReady) {
            CoroutineScope(Dispatchers.IO).launch {
                try {
                    app.container.registerFcmToken(token)
                } catch (t: Throwable) {
                    Log.e(TAG, "Error al registrar FCM token con el backend", t)
                }
            }
        }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val data = message.data
        val type = data["type"] ?: return
        Log.i(TAG, "FCM message type=$type")

        when (type) {
            "update" -> handleUpdate(data)
            "started" -> handleStarted(data)
            "cancelled" -> handleCancelled(data)
            "fire" -> handleFire(data)
            else -> Log.w(TAG, "FCM type desconocido: $type")
        }
    }

    private fun handleUpdate(data: Map<String, String>) {
        val boutId = data["bout_id"] ?: return
        val estimatedStartRaw = data["estimated_start_at"] ?: return
        val estimatedStartMs = estimatedStartRaw.toLongOrNull() ?: return

        val app = application as DespertarMeApp
        CoroutineScope(Dispatchers.IO).launch {
            val existing = PendingAlarmStorage.get(app, boutId) ?: run {
                Log.w(TAG, "Update ignorado — no hay PendingAlarm para bout=$boutId")
                return@launch
            }

            // D45 ring-once: si ya sonó la alarma para este combate, ignorar.
            if (existing.fired) {
                Log.i(TAG, "Update ignorado — alarma ya sonó para bout=$boutId")
                return@launch
            }

            // D45 lead>=30: programa la alarma solo en el PRIMER push (cuando el
            // prev transiciona pre→in). Pushes subsiguientes durante `in` no repro.
            if (existing.leadMinutes >= 30 && existing.triggerAtMillis > 0L) {
                Log.i(TAG, "Update ignorado — alarma ya programada (lead>=30) para bout=$boutId")
                return@launch
            }

            val now = System.currentTimeMillis()
            val trigger: Long = if (existing.leadMinutes >= 30) {
                // lead>=30: suena al recibir primer push + cushion 1 min
                // ("cuando empieza el combate previo" tras cushion).
                now + 60_000L
            } else {
                // lead<30: trigger = est-lead + cushion. Si el cálculo sale
                // pasado, cushion floor de 1 min (max(now+1min, ...)).
                maxOf(now + 60_000L, estimatedStartMs - existing.leadMinutes * 60_000L + 60_000L)
            }

            AlarmScheduler.schedule(app, existing.copy(triggerAtMillis = trigger))
            Log.i(
                TAG,
                "Alarma programada: bout=$boutId trigger=$trigger (sonará en ${(trigger - now) / 1000}s)",
            )
        }
    }

    private fun handleStarted(data: Map<String, String>) {
        val boutId = data["bout_id"] ?: return
        val fighters = data["fighters"] ?: "Combate"
        cancelAlarmAndNotify(boutId, "\u2694 $fighters — El combate ha empezado")
    }

    private fun handleCancelled(data: Map<String, String>) {
        val boutId = data["bout_id"] ?: return
        val fighters = data["fighters"] ?: "Combate"
        cancelAlarmAndNotify(boutId, "\u274c Alerta cancelada: $fighters")
    }

    private fun handleFire(_data: Map<String, String>) {
        val intent = Intent(this, AlarmService::class.java).apply {
            action = AlarmService.ACTION_START
        }
        startForegroundService(intent)

        val activityIntent = Intent(this, AlarmActivity::class.java).apply {
            putExtra("bout_id", "test")
            putExtra("event_id", "test")
            putExtra("fighter_red", "Test")
            putExtra("fighter_blue", "Alarm")
            putExtra("lead_minutes", 0)
            putExtra("event_name", "DespertarME — Test de alarma")
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        }
        startActivity(activityIntent)
    }

    private fun cancelAlarmAndNotify(boutId: String, message: String) {
        val app = application as DespertarMeApp
        CoroutineScope(Dispatchers.IO).launch {
            val existing = PendingAlarmStorage.get(app, boutId)
            if (existing != null && !existing.fired) {
                PendingAlarmStorage.put(app, existing.copy(fired = true))
            }
            AlarmScheduler.cancel(app, boutId)
        }
        showInfoNotification(message)
    }

    private fun showInfoNotification(message: String) {
        val intent = Intent(this, MainActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
        }
        val flags = if (android.os.Build.VERSION.SDK_INT >= 31) {
            PendingIntent.FLAG_IMMUTABLE
        } else {
            0
        }
        val pendingIntent = PendingIntent.getActivity(this, 0, intent, flags)

        val notification = NotificationCompat.Builder(this, INFO_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
            .setContentTitle("DespertarME")
            .setContentText(message)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .build()

        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        nm.notify(INFO_NOTIFICATION_ID, notification)
    }

    private fun ensureInfoChannel() {
        if (android.os.Build.VERSION.SDK_INT < 26) return
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (nm.getNotificationChannel(INFO_CHANNEL_ID) != null) return
        val channel = NotificationChannel(
            INFO_CHANNEL_ID,
            "Información de alertas",
            NotificationManager.IMPORTANCE_HIGH,
        ).apply {
            description = "Notificaciones informativas sobre el estado de tus alertas"
        }
        nm.createNotificationChannel(channel)
    }
}
