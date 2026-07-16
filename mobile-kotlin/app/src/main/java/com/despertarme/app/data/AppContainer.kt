package com.despertarme.app.data

import android.content.Context
import android.util.Log
import com.despertarme.app.data.remote.DespertarApi
import com.despertarme.app.data.remote.DeviceCreate
import com.despertarme.app.data.remote.DeviceIdInterceptor
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit

class AppContainer(context: Context) {

    private val storage = DeviceStorage(context)

    // FCM placeholder until the FCM tramo arrives — backend accepts any string
    // >=10 chars and the poller simply won't push without a real token. Meanwhile
    // the device can still register and create subscriptions.
    private val deviceIdFlow = MutableStateFlow<String?>(null)
    val deviceId: StateFlow<String?> get() = deviceIdFlow

    val api: DespertarApi

    init {
        val json = Json { ignoreUnknownKeys = true; encodeDefaults = true }

        val http = OkHttpClient.Builder()
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(20, TimeUnit.SECONDS)
            .addInterceptor(DeviceIdInterceptor { deviceIdFlow.value })
            .build()

        val contentType = "application/json".toMediaType()
        api = Retrofit.Builder()
            .baseUrl("http://10.0.2.2:8000/")
            .client(http)
            .addConverterFactory(json.asConverterFactory(contentType))
            .build()
            .create(DespertarApi::class.java)
    }

    suspend fun ensureRegistered(): String {
        val id = storage.ensureDeviceId()
        deviceIdFlow.value = id
        val token = storage.fcmToken() ?: "no-fcm-yet-$id"
        try {
            api.registerDevice(
                DeviceCreate(
                    deviceId = id,
                    fcmToken = token,
                    platform = "android",
                    timezone = "Europe/Madrid",
                    locale = "es-ES",
                ),
            )
        } catch (t: Throwable) {
            Log.e("DespertarMe", "ensureRegistered failed", t)
        }
        return id
    }
}