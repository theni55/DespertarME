package com.despertarme.app

import com.despertarme.app.alarm.AlarmTriggerPolicy
import org.junit.Assert.assertEquals
import org.junit.Test

class AlarmTriggerPolicyTest {
    private val now = 1_000_000L

    @Test
    fun leadFiveSchedulesEstimateMinusLeadPlusCushion() {
        val estimate = now + 20 * 60_000L

        val trigger = AlarmTriggerPolicy.calculate(now, estimate, leadMinutes = 5)

        assertEquals(now + 16 * 60_000L, trigger)
    }

    @Test
    fun leadThirtyCanBeRecalculatedFromLatestEstimate() {
        val estimate = now + 45 * 60_000L

        val trigger = AlarmTriggerPolicy.calculate(now, estimate, leadMinutes = 30)

        assertEquals(now + 16 * 60_000L, trigger)
    }

    @Test
    fun leadZeroSchedulesOneMinuteBeforeEstimate() {
        val estimate = now + 10 * 60_000L

        val trigger = AlarmTriggerPolicy.calculate(now, estimate, leadMinutes = 0)

        assertEquals(now + 9 * 60_000L, trigger)
    }

    @Test
    fun lateUpdateKeepsOneMinuteSchedulingFloor() {
        val estimate = now - 5 * 60_000L

        val trigger = AlarmTriggerPolicy.calculate(now, estimate, leadMinutes = 5)

        assertEquals(now + 60_000L, trigger)
    }
}
