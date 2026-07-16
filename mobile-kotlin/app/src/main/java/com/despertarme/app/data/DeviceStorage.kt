package com.despertarme.app.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import java.util.UUID

private val Context.deviceDataStore by preferencesDataStore(name = "device_store")

private val DEVICE_ID_KEY = stringPreferencesKey("device_id")
private val FCM_TOKEN_KEY = stringPreferencesKey("fcm_token")

class DeviceStorage(private val context: Context) {

    val deviceIdFlow: Flow<String?> = context.deviceDataStore.data.map { it[DEVICE_ID_KEY] }

    suspend fun ensureDeviceId(): String {
        val existing = context.deviceDataStore.data.first()[DEVICE_ID_KEY]
        if (existing != null) return existing
        val generated = UUID.randomUUID().toString()
        context.deviceDataStore.edit { it[DEVICE_ID_KEY] = generated }
        return generated
    }

    suspend fun getDeviceId(): String? = context.deviceDataStore.data.first()[DEVICE_ID_KEY]

    suspend fun fcmToken(): String? = context.deviceDataStore.data.first()[FCM_TOKEN_KEY]
}