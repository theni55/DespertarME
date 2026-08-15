package com.despertarme.app.data

import android.content.Context
import android.util.Log
import com.despertarme.app.alarm.AlarmScheduler
import com.despertarme.app.data.remote.DespertarApi
import com.despertarme.app.data.remote.DeviceCreate
import com.despertarme.app.data.remote.DeviceIdInterceptor
import com.google.android.gms.tasks.Tasks
import com.google.firebase.messaging.FirebaseMessaging
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import retrofit2.Retrofit
import retrofit2.converter.kotlinx.serialization.asConverterFactory
import java.util.concurrent.TimeUnit

class AppContainer(context: Context) {

    private val appContext = context.applicationContext
    private val storage = DeviceStorage(context)

    // FCM is wired end-to-end since Sesión 18, but the token may not be available
    // yet (e.g. before FirebaseInitProvider fires onNewToken). The placeholder
    // "no-fcm-yet-{id}" keeps registration non-blocking; the real token replaces
    // it when registerFcmToken() is called from the FCM service.
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
            .baseUrl("https://despertarme-production.up.railway.app/")
            .client(http)
            .addConverterFactory(json.asConverterFactory(contentType))
            .build()
            .create(DespertarApi::class.java)
    }

    suspend fun ensureRegistered(): String {
        val id = ensureDeviceIdLocal()
        registerWithBackend()
        return id
    }

    /**
     * A3: resuelve el device_id local (DataStore) y limpia alarmas viejas.
     * Rápido y sin red: seguro de ejecutar de forma síncrona en el arranque
     * para dejar el `deviceIdFlow` listo antes de la primera composición.
     */
    suspend fun ensureDeviceIdLocal(): String {
        val id = storage.ensureDeviceId()
        deviceIdFlow.value = id
        // Limpiar alarmas viejas del DataStore que puedan sobrevivir
        // a reinstalaciones (allowBackup). Si el trigger ya pasó o
        // la alarma ya sonó, cancelarla para evitar fantasmas.
        AlarmScheduler.cleanupStale(appContext)
        return id
    }

    /**
     * A3: registra el device (y su token FCM) con el backend en segundo plano.
     * Es la parte con red (timeouts 10/20s) que NO debe bloquear el main thread.
     */
    suspend fun registerWithBackend() {
        val id = storage.ensureDeviceId()
        deviceIdFlow.value = id
        val token = freshFcmToken() ?: storage.fcmToken() ?: "no-fcm-yet-$id"
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
            Log.e("DespertarMe", "registerWithBackend failed", t)
        }
    }

    suspend fun registerFcmToken(token: String) {
        val id = storage.ensureDeviceId()
        deviceIdFlow.value = id
        // Guardar en DataStore como fallback, pero usar el token que nos
        // pasan directamente (ya es el fresco de Firebase via onNewToken).
        storage.setFcmToken(token)
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
            Log.i("DespertarMe", "FCM token registrado con el backend")
        } catch (t: Throwable) {
            Log.e("DespertarMe", "registerFcmToken failed", t)
        }
    }

    /**
     * Obtiene el token FCM directamente de Firebase en vez de DataStore.
     * DataStore puede conservar un token viejo tras reinstalar la app
     * (allowBackup), provocando NotRegistered en todos los pushes.
     */
    private fun freshFcmToken(): String? {
        return try {
            val task = FirebaseMessaging.getInstance().token
            Tasks.await(task, 3, java.util.concurrent.TimeUnit.SECONDS)
        } catch (_: Exception) {
            null
        }
    }
}