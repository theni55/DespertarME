package com.despertarme.app.alarm

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build

object AlarmScheduler {

    const val ALARM_ACTION = "com.despertarme.app.action.ALARM_FIRE"

    suspend fun schedule(context: Context, alarm: PendingAlarm) {
        cancel(context, alarm.boutId)
        val intent = Intent(context, AlarmReceiver::class.java).apply {
            action = ALARM_ACTION
            putExtra("bout_id", alarm.boutId)
            putExtra("event_id", alarm.eventId)
            putExtra("fighter_red", alarm.fighterRed ?: "TBD")
            putExtra("fighter_blue", alarm.fighterBlue ?: "TBD")
            putExtra("lead_minutes", alarm.leadMinutes)
            putExtra("event_name", alarm.eventName ?: "")
        }
        val flags = if (Build.VERSION.SDK_INT >= 31) {
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        } else {
            PendingIntent.FLAG_UPDATE_CURRENT
        }
        val pendingIntent = PendingIntent.getBroadcast(
            context, alarm.boutId.hashCode(), intent, flags,
        )
        val info = AlarmManager.AlarmClockInfo(alarm.triggerAtMillis, pendingIntent)
        val am = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        am.setAlarmClock(info, pendingIntent)
        PendingAlarmStorage.put(context.applicationContext, alarm)
    }

    suspend fun cancel(context: Context, boutId: String) {
        val intent = Intent(context, AlarmReceiver::class.java).apply {
            action = ALARM_ACTION
        }
        val flags = if (Build.VERSION.SDK_INT >= 31) {
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        } else {
            PendingIntent.FLAG_UPDATE_CURRENT
        }
        val pendingIntent = PendingIntent.getBroadcast(
            context, boutId.hashCode(), intent, flags,
        )
        val am = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        am.cancel(pendingIntent)
        PendingAlarmStorage.remove(context.applicationContext, boutId)
    }

    suspend fun reschedule(context: Context, boutId: String, newTriggerAtMillis: Long) {
        val existing = PendingAlarmStorage.get(context.applicationContext, boutId) ?: return
        schedule(context, existing.copy(triggerAtMillis = newTriggerAtMillis))
    }
}
