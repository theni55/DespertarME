package com.despertarme.app.alarm

object AlarmTriggerPolicy {
    private const val SCHEDULING_CUSHION_MILLIS = 60_000L

    fun calculate(
        nowMillis: Long,
        estimatedStartMillis: Long,
        leadMinutes: Int,
    ): Long {
        val requestedTrigger = if (leadMinutes == 0) {
            estimatedStartMillis - SCHEDULING_CUSHION_MILLIS
        } else {
            estimatedStartMillis - leadMinutes * 60_000L + SCHEDULING_CUSHION_MILLIS
        }
        return maxOf(nowMillis + SCHEDULING_CUSHION_MILLIS, requestedTrigger)
    }
}
