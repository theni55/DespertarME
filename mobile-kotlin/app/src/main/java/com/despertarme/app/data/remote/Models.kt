package com.despertarme.app.data.remote

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class EventSummaryOut(
    val id: String,
    val name: String,
    val date: String,
    @SerialName("image_url") val imageUrl: String? = null,
)

@Serializable
data class EventCardOut(
    val id: String,
    val name: String,
    val date: String,
    @SerialName("image_url") val imageUrl: String? = null,
    val bouts: List<BoutOut>,
)

@Serializable
data class BoutOut(
    val id: String,
    @SerialName("match_number") val matchNumber: Int,
    val date: String,
    @SerialName("card_segment") val cardSegment: String? = null,
    @SerialName("weight_class") val weightClass: String? = null,
    val periods: Int = 3,
    val red: BoutAthleteOut? = null,
    val blue: BoutAthleteOut? = null,
    @SerialName("previous_bout_id") val previousBoutId: String? = null,
)

@Serializable
data class BoutAthleteOut(
    val id: String,
    val name: String? = null,
    @SerialName("headshot_url") val headshotUrl: String? = null,
)

@Serializable
data class DeviceCreate(
    @SerialName("device_id") val deviceId: String,
    @SerialName("fcm_token") val fcmToken: String,
    val platform: String? = "android",
    val timezone: String = "Europe/Madrid",
    val locale: String? = "es-ES",
)

@Serializable
data class DeviceOut(
    val id: String,
    @SerialName("fcm_token") val fcmToken: String? = null,
    val platform: String? = null,
    val timezone: String,
    val locale: String? = null,
    @SerialName("is_active") val isActive: Boolean,
    @SerialName("last_seen_at") val lastSeenAt: String,
)

@Serializable
data class BoutSubscriptionCreate(
    @SerialName("event_id") val eventId: String,
    @SerialName("bout_id") val boutId: String,
    @SerialName("target_match_number") val targetMatchNumber: Int,
    @SerialName("lead_minutes") val leadMinutes: Int,
)

@Serializable
data class AlertLogOut(
    val id: String,
    @SerialName("subscription_id") val subscriptionId: String,
    @SerialName("device_id") val deviceId: String,
    @SerialName("bout_id") val boutId: String,
    @SerialName("fired_at") val firedAt: String,
    @SerialName("fired_at_epoch_hour") val firedAtEpochHour: Long,
    val status: String,
    val attempts: Int,
    @SerialName("notifier_response") val notifierResponse: String? = null,
    val payload: String? = null,
)

@Serializable
data class BoutSubscriptionOut(
    val id: String,
    @SerialName("device_id") val deviceId: String,
    @SerialName("event_id") val eventId: String,
    @SerialName("bout_id") val boutId: String,
    @SerialName("target_match_number") val targetMatchNumber: Int,
    @SerialName("lead_minutes") val leadMinutes: Int,
    val status: String,
)