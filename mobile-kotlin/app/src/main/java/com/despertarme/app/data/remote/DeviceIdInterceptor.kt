package com.despertarme.app.data.remote

import okhttp3.Interceptor
import okhttp3.Response

class DeviceIdInterceptor(
    private val deviceIdProvider: () -> String?,
) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        val deviceId = deviceIdProvider()
        val request = if (deviceId != null) {
            chain.request().newBuilder()
                .header("X-Device-Id", deviceId)
                .build()
        } else {
            chain.request()
        }
        return chain.proceed(request)
    }
}