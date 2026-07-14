package com.despertarme.spike.alarm

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.media.AudioAttributes
import android.net.Uri
import android.provider.Settings
import androidx.core.content.ContextCompat
import com.facebook.react.bridge.Promise
import com.facebook.react.bridge.ReactApplicationContext
import com.facebook.react.bridge.ReactContextBaseJavaModule
import com.facebook.react.bridge.ReactMethod

class AlarmModule(private val ctx: ReactApplicationContext) :
    ReactContextBaseJavaModule(ctx) {

    override fun getName() = "AlarmModule"

    companion object {
        const val CHANNEL_ID = "despertarme.alarm"
        const val ACTION_START = "despertarme.spike.action.START_ALARM"
    }

    private fun ensureChannel() {
        val nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        if (nm.getNotificationChannel(CHANNEL_ID) != null) return
        val channel = NotificationChannel(
            CHANNEL_ID,
            "DespertarME Alarm",
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

    @ReactMethod
    fun startAlarm(promise: Promise) {
        try {
            if (!hasPolicyAccess()) {
                promptPolicyAccess()
            }
            ensureChannel()
            val intent = Intent(ctx, AlarmService::class.java).apply { action = ACTION_START }
            ContextCompat.startForegroundService(ctx, intent)
            promise.resolve(null)
        } catch (e: Exception) {
            promise.reject("start_alarm_failed", e.message ?: "unknown", e)
        }
    }

    @ReactMethod
    fun stopAlarm(promise: Promise) {
        try {
            val intent = Intent(ctx, AlarmService::class.java)
            ctx.stopService(intent)
            promise.resolve(null)
        } catch (e: Exception) {
            promise.reject("stop_alarm_failed", e.message ?: "unknown", e)
        }
    }

    private fun hasPolicyAccess(): Boolean {
        val nm = ctx.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        return nm.isNotificationPolicyAccessGranted
    }

    private fun promptPolicyAccess() {
        val intent = Intent(Settings.ACTION_NOTIFICATION_POLICY_ACCESS_SETTINGS).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK
        }
        ctx.startActivity(intent)
    }
}