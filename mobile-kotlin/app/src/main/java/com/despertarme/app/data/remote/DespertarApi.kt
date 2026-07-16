package com.despertarme.app.data.remote

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface DespertarApi {

    @GET("/api/events")
    suspend fun listEvents(): List<EventSummaryOut>

    @GET("/api/events/{id}")
    suspend fun getEvent(@Path("id") id: String): EventCardOut

    @POST("/api/devices")
    suspend fun registerDevice(@Body body: DeviceCreate): DeviceOut

    @POST("/api/subscriptions")
    suspend fun createSubscription(@Body body: BoutSubscriptionCreate): BoutSubscriptionOut

    @GET("/api/subscriptions")
    suspend fun listSubscriptions(): List<BoutSubscriptionOut>
}