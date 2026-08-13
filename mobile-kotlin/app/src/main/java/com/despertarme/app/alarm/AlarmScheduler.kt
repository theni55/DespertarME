package com.despertarme.app.alarm

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.os.Build
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock

object AlarmScheduler {

    const val ALARM_ACTION = "com.despertarme.app.action.ALARM_FIRE"
    private const val FIRED_TOMBSTONE_TTL_MILLIS = 24 * 60 * 60 * 1000L
    private val transitionMutex = Mutex()

    suspend fun schedule(context: Context, alarm: PendingAlarm): AlarmScheduleResult =
        transitionMutex.withLock {
            cancelScheduled(context, alarm.boutId)
            if (!PendingAlarmStorage.putIfNotFired(context.applicationContext, alarm)) {
                return@withLock AlarmScheduleResult.SUPPRESSED
            }
            val am = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && !am.canScheduleExactAlarms()) {
                return@withLock AlarmScheduleResult.EXACT_PERMISSION_REQUIRED
            }
            val intent = Intent(context, AlarmReceiver::class.java).apply {
                action = ALARM_ACTION
                putExtra("bout_id", alarm.boutId)
                putExtra("event_id", alarm.eventId)
                putExtra("fighter_red", alarm.fighterRed ?: "TBD")
                putExtra("fighter_blue", alarm.fighterBlue ?: "TBD")
                putExtra("lead_minutes", alarm.leadMinutes)
                putExtra("event_name", alarm.eventName ?: "")
                alarm.headshotRed?.let { putExtra("headshot_red", it) }
                alarm.headshotBlue?.let { putExtra("headshot_blue", it) }
                alarm.sport?.let { putExtra("sport", it) }
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
            return@withLock try {
                am.setAlarmClock(info, pendingIntent)
                AlarmScheduleResult.SCHEDULED
            } catch (_: SecurityException) {
                AlarmScheduleResult.EXACT_PERMISSION_REQUIRED
            } catch (_: RuntimeException) {
                AlarmScheduleResult.FAILED
            }
        }

    suspend fun cancel(context: Context, boutId: String) {
        transitionMutex.withLock {
            cancelScheduled(context, boutId)
            PendingAlarmStorage.remove(context.applicationContext, boutId)
        }
    }

    fun cancelScheduled(context: Context, boutId: String) {
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
    }

    suspend fun suppress(context: Context, boutId: String): Boolean =
        transitionMutex.withLock {
            cancelScheduled(context, boutId)
            val existing = PendingAlarmStorage.get(context.applicationContext, boutId)
                ?: return@withLock false
            PendingAlarmStorage.put(
                context.applicationContext,
                existing.copy(triggerAtMillis = System.currentTimeMillis(), fired = true),
            )
            existing.fired
        }

    suspend fun markFired(context: Context, boutId: String) {
        suppress(context, boutId)
    }

    suspend fun reschedule(context: Context, boutId: String, newTriggerAtMillis: Long) {
        val existing = PendingAlarmStorage.get(context.applicationContext, boutId) ?: return
        schedule(context, existing.copy(triggerAtMillis = newTriggerAtMillis))
    }

    suspend fun restorePending(context: Context): Pair<Int, Int> {
        val now = System.currentTimeMillis()
        val alarms = PendingAlarmStorage.all(context.applicationContext)
        val valid = alarms.filter { it.triggerAtMillis > now && !it.fired }
        val restored = valid.count { schedule(context, it) == AlarmScheduleResult.SCHEDULED }
        return restored to valid.size
    }

    /**
     * Cancela alarmas pendientes cuyo trigger ya pasó. Los tombstones fired
     * se conservan 24 h para que un update/started tardío no vuelva a sonar.
     */
    suspend fun cleanupStale(context: Context) {
        val now = System.currentTimeMillis()
        val all = PendingAlarmStorage.all(context.applicationContext)
        for (alarm in all) {
            val expiredPending = !alarm.fired && alarm.triggerAtMillis > 0L && alarm.triggerAtMillis < now
            val expiredTombstone = alarm.fired &&
                alarm.triggerAtMillis > 0L &&
                alarm.triggerAtMillis < now - FIRED_TOMBSTONE_TTL_MILLIS
            if (expiredPending || expiredTombstone) {
                cancel(context, alarm.boutId)
            }
        }
    }
}

enum class AlarmScheduleResult {
    SCHEDULED,
    SUPPRESSED,
    EXACT_PERMISSION_REQUIRED,
    FAILED,
}
