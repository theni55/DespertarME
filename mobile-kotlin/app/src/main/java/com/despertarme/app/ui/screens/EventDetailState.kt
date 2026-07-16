package com.despertarme.app.ui.screens

import com.despertarme.app.data.remote.EventCardOut

data class EventDetailState(
    val isLoading: Boolean = true,
    val event: EventCardOut? = null,
    val error: String? = null,
    val subscribedBouts: Set<String> = emptySet(),
)