package com.despertarme.app.alarm

import android.app.Notification
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.media.AudioAttributes
import android.media.Ringtone
import android.media.RingtoneManager
import android.net.Uri
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat

class AlarmService : Service() {

    companion object {
        const val NOTIFICATION_ID = 1
        const val CHANNEL_ID = "despertarme.alarm"
        const val ACTION_START = "com.despertarme.app.action.START_ALARM"
        const val ACTION_STOP = "com.despertarme.app.action.STOP_ALARM"
        private const val WAKE_TAG = "despertarme:alarm"
    }

    private var ringtone: Ringtone? = null
    private var wakeLock: PowerManager.WakeLock? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopForeground(STOP_FOREGROUND_REMOVE)
            stopSelf()
            return START_NOT_STICKY
        }
        if (intent?.action != ACTION_START) {
            stopSelf()
            return START_NOT_STICKY
        }
        startForeground(
            NOTIFICATION_ID,
            buildNotification(),
            ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK,
        )
        playAlarmLoop()
        return START_STICKY
    }

    private fun playAlarmLoop() {
        val uri: Uri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM)
            ?: RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE)
            ?: return
        val rt: Ringtone = RingtoneManager.getRingtone(this, uri) ?: return
        rt.audioAttributes = AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_ALARM)
            .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
            .build()
        if (Build.VERSION.SDK_INT >= 28) {
            rt.isLooping = true
        }
        rt.play()
        ringtone = rt
        val pm = getSystemService(POWER_SERVICE) as PowerManager
        wakeLock = pm.newWakeLock(PowerManager.PARTIAL_WAKE_LOCK, WAKE_TAG).apply {
            acquire(10 * 60 * 1000L)
        }
    }

    private fun buildNotification(): Notification =
        NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("DespertarME")
            .setContentText(getString(com.despertarme.app.R.string.alarm_notification_text))
            .setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setOngoing(true)
            .setSilent(true)
            .build()

    override fun onDestroy() {
        ringtone?.stop()
        ringtone = null
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null
}