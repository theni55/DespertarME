package com.despertarme.app.alarm

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.first
import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

private val Context.alarmDataStore by preferencesDataStore(name = "alarm_store")

private val PENDING_ALARMS_KEY = stringPreferencesKey("pending_alarms")

@Serializable
data class PendingAlarm(
    val boutId: String,
    val eventId: String,
    val triggerAtMillis: Long,
    val leadMinutes: Int,
    val fighterRed: String?,
    val fighterBlue: String?,
    val eventName: String?,
    val boutMatchNumber: Int,
    val fired: Boolean = false,
    val headshotRed: String? = null,
    val headshotBlue: String? = null,
    val sport: String? = null,
)

@Serializable
private data class PendingAlarmsMap(val alarms: Map<String, PendingAlarm> = emptyMap())

object PendingAlarmStorage {

    private val json = Json { ignoreUnknownKeys = true }

    suspend fun put(context: Context, alarm: PendingAlarm) {
        context.alarmDataStore.edit { prefs ->
            val all = decode(prefs[PENDING_ALARMS_KEY]).toMutableMap()
            all[alarm.boutId] = alarm
            prefs[PENDING_ALARMS_KEY] = json.encodeToString(PendingAlarmsMap(all))
        }
    }

    suspend fun putIfNotFired(context: Context, alarm: PendingAlarm): Boolean {
        var stored = false
        context.alarmDataStore.edit { prefs ->
            val all = decode(prefs[PENDING_ALARMS_KEY]).toMutableMap()
            if (all[alarm.boutId]?.fired == true) return@edit
            all[alarm.boutId] = alarm
            prefs[PENDING_ALARMS_KEY] = json.encodeToString(PendingAlarmsMap(all))
            stored = true
        }
        return stored
    }

    suspend fun remove(context: Context, boutId: String) {
        context.alarmDataStore.edit { prefs ->
            val all = decode(prefs[PENDING_ALARMS_KEY]).toMutableMap()
            all.remove(boutId)
            prefs[PENDING_ALARMS_KEY] = json.encodeToString(PendingAlarmsMap(all))
        }
    }

    suspend fun get(context: Context, boutId: String): PendingAlarm? =
        readAll(context)[boutId]

    suspend fun all(context: Context): List<PendingAlarm> =
        readAll(context).values.toList()

    private suspend fun readAll(context: Context): Map<String, PendingAlarm> {
        val raw = context.alarmDataStore.data.first()[PENDING_ALARMS_KEY]
        return decode(raw)
    }

    private fun decode(raw: String?): Map<String, PendingAlarm> {
        if (raw == null) return emptyMap()
        return runCatching {
            json.decodeFromString<PendingAlarmsMap>(raw).alarms
        }.getOrDefault(emptyMap())
    }
}
