package com.despertarme.app.data.remote

import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface DespertarApi {

    @GET("/api/events")
    suspend fun listEvents(
        @Query("sport") sport: String = "mma",
        @Query("league") league: String = "",
    ): List<EventSummaryOut>

    @GET("/api/events/{id}")
    suspend fun getEvent(
        @Path("id") id: String,
        @Query("sport") sport: String = "mma",
        @Query("league") league: String = "",
    ): EventCardOut

    @POST("/api/devices")
    suspend fun registerDevice(@Body body: DeviceCreate): DeviceOut

    @POST("/api/subscriptions")
    suspend fun createSubscription(@Body body: BoutSubscriptionCreate): BoutSubscriptionOut

    @GET("/api/subscriptions")
    suspend fun listSubscriptions(): List<BoutSubscriptionOut>

    @DELETE("/api/subscriptions/{id}")
    suspend fun deleteSubscription(@Path("id") id: String)

    @GET("/api/alerts")
    suspend fun listAlerts(@Query("limit") limit: Int = 50): List<AlertLogOut>
}
