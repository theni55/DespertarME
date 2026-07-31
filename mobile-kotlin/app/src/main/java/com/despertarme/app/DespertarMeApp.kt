package com.despertarme.app

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.media.AudioAttributes
import com.despertarme.app.alarm.AlarmService
import com.despertarme.app.data.AppContainer

class DespertarMeApp : Application() {

    @Volatile
    var isContainerReady: Boolean = false
        private set

    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        instance = this
        container = AppContainer(this)
        isContainerReady = true
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
        nm.createNotificationChannel(channel)
    }

    companion object {
        lateinit var instance: DespertarMeApp
            private set
    }
}