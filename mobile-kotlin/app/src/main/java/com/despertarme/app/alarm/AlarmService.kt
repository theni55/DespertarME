package com.despertarme.app.alarm

import android.app.Notification
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.media.AudioAttributes
import android.media.AudioManager
import android.media.Ringtone
import android.media.RingtoneManager
import android.net.Uri
import android.os.Build
import android.os.IBinder
import android.os.PowerManager
import androidx.core.app.NotificationCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.runBlocking

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
    private var originalAlarmVolume: Int? = null

    private var alarmBoutId: String = ""
    private var alarmEventId: String = ""
    private var alarmFighterRed: String = ""
    private var alarmFighterBlue: String = ""
    private var alarmLeadMinutes: Int = 0
    private var alarmEventName: String = ""
    private var alarmSport: String = "mma"
    private var alarmHeadshotRed: String? = null
    private var alarmHeadshotBlue: String? = null

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (intent?.action == ACTION_STOP) {
            stopPlayback(restoreVolume = true)
            val nm = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
            nm.cancel(AlarmReceiver.FULLSCREEN_NOTIFICATION_ID)
            nm.cancel(NOTIFICATION_ID)
            stopForeground(STOP_FOREGROUND_REMOVE)
            stopSelf()
            return START_NOT_STICKY
        }
        if (intent?.action != ACTION_START) {
            stopSelf()
            return START_NOT_STICKY
        }
        intent?.let {
            alarmBoutId = it.getStringExtra("bout_id") ?: ""
            alarmEventId = it.getStringExtra("event_id") ?: ""
            alarmFighterRed = it.getStringExtra("fighter_red") ?: "TBD"
            alarmFighterBlue = it.getStringExtra("fighter_blue") ?: "TBD"
            alarmLeadMinutes = it.getIntExtra("lead_minutes", 0)
            alarmEventName = it.getStringExtra("event_name") ?: ""
            alarmSport = it.getStringExtra("sport") ?: "mma"
            alarmHeadshotRed = it.getStringExtra("headshot_red")
            alarmHeadshotBlue = it.getStringExtra("headshot_blue")
        }
        startForeground(
            NOTIFICATION_ID,
            buildNotification(),
            ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK,
        )
        val playbackStarted = playAlarmLoop()
        if (playbackStarted && alarmBoutId.isNotEmpty()) {
            runBlocking(Dispatchers.IO) {
                AlarmScheduler.markFired(applicationContext, alarmBoutId)
            }
        }
        if (!playbackStarted) {
            stopPlayback(restoreVolume = true)
            stopForeground(STOP_FOREGROUND_REMOVE)
            stopSelf()
            return START_NOT_STICKY
        }
        return START_STICKY
    }

    private fun playAlarmLoop(): Boolean {
        stopPlayback(restoreVolume = false)
        val uri: Uri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM)
            ?: RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE)
            ?: return false
        val rt: Ringtone = RingtoneManager.getRingtone(this, uri) ?: return false
        val am = getSystemService(AUDIO_SERVICE) as AudioManager
        if (originalAlarmVolume == null) {
            originalAlarmVolume = am.getStreamVolume(AudioManager.STREAM_ALARM)
        }
        val maxVol = am.getStreamMaxVolume(AudioManager.STREAM_ALARM)
        am.setStreamVolume(AudioManager.STREAM_ALARM, maxVol, 0)
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
        return true
    }

    private fun buildNotification(): Notification {
        val stopIntent = Intent(this, AlarmService::class.java).apply {
            action = ACTION_STOP
        }
        val pendingFlags = if (Build.VERSION.SDK_INT >= 31) {
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        } else {
            PendingIntent.FLAG_UPDATE_CURRENT
        }
        val stopPend = PendingIntent.getService(this, 0, stopIntent, pendingFlags)

        val builder = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("DespertarME")
            .setContentText(getString(com.despertarme.app.R.string.alarm_notification_text))
            .setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
            .setCategory(NotificationCompat.CATEGORY_ALARM)
            .setOngoing(true)
            .setSilent(true)
            .addAction(android.R.drawable.ic_media_pause, "Parar", stopPend)

        if (alarmBoutId.isNotEmpty()) {
            val contentIntent = Intent(this, AlarmActivity::class.java).apply {
                putExtra("bout_id", alarmBoutId)
                putExtra("event_id", alarmEventId)
                putExtra("fighter_red", alarmFighterRed)
                putExtra("fighter_blue", alarmFighterBlue)
                putExtra("lead_minutes", alarmLeadMinutes)
                putExtra("event_name", alarmEventName)
                putExtra("sport", alarmSport)
                alarmHeadshotRed?.let { putExtra("headshot_red", it) }
                alarmHeadshotBlue?.let { putExtra("headshot_blue", it) }
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
            }
            builder.setContentIntent(
                PendingIntent.getActivity(this, 1, contentIntent, pendingFlags),
            )
        } else {
            builder.setContentIntent(stopPend)
        }

        return builder.build()
    }

    override fun onDestroy() {
        stopPlayback(restoreVolume = true)
        super.onDestroy()
    }

    private fun stopPlayback(restoreVolume: Boolean) {
        ringtone?.stop()
        ringtone = null
        wakeLock?.let { if (it.isHeld) it.release() }
        wakeLock = null
        if (restoreVolume) {
            originalAlarmVolume?.let { volume ->
                val am = getSystemService(AUDIO_SERVICE) as AudioManager
                am.setStreamVolume(AudioManager.STREAM_ALARM, volume, 0)
            }
            originalAlarmVolume = null
        }
    }

    override fun onBind(intent: Intent?): IBinder? = null
}
