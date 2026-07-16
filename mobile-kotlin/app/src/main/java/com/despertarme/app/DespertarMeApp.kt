package com.despertarme.app

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.media.AudioAttributes
import com.despertarme.app.alarm.AlarmService

class DespertarMeApp : Application() {

    override fun onCreate() {
        super.onCreate()
        ensureAlarmChannel()
    }

    private fun ensureAlarmChannel() {
        val nm = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (nm.getNotificationChannel(AlarmService.CHANNEL_ID) != null) return
        val channel = NotificationChannel(
            AlarmService.CHANNEL_ID,
            getString(R.string.notification_channel_alarm),
            NotificationManager.IMPORTANCE_HIGH,
        ).apply {
            description = "Alarm channel that bypasses Do Not Disturb"
            setBypassDnd(true)
            setLockscreenVisibility(android.app.Notification.VISIBILITY_PUBLIC)
            enableVibration(false)
            setSound(null, null)
        }
        // AudioAttributes usage alarm for the channel (pre-26 ignored, safe).
        @Suppress("unused")
        val attrs = AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_ALARM)
            .build()
        nm.createNotificationChannel(channel)
    }
}