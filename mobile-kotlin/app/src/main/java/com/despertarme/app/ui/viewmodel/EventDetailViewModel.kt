package com.despertarme.app.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.despertarme.app.data.AppContainer
import com.despertarme.app.data.remote.EventSummaryOut
import com.despertarme.app.ui.screens.EventDetailState
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class EventDetailViewModel(
    private val container: AppContainer,
) : ViewModel() {

    private val _state = MutableStateFlow(EventDetailState())
    val state: StateFlow<EventDetailState> = _state.asStateFlow()

    private val _snack = MutableStateFlow<String?>(null)
    val snackMessage: StateFlow<String?> = _snack.asStateFlow()

    fun clearSnack() { _snack.value = null }

    fun load(eventId: String) {
        if (eventId == "none") {
            resolveNextEvent()
            return
        }
        if (_state.value.event?.id == eventId && _state.value.error == null) return
        _state.value = EventDetailState(isLoading = true)
        viewModelScope.launch {
            try {
                val card = container.api.getEvent(eventId)
                _state.value = EventDetailState(isLoading = false, event = card)
            } catch (t: Throwable) {
                _state.value = EventDetailState(
                    isLoading = false,
                    error = "No se pudo cargar el evento: ${t.message ?: "desconocido"}",
                )
            }
        }
    }

    private fun resolveNextEvent() {
        _state.value = EventDetailState(isLoading = true)
        viewModelScope.launch {
            try {
                val next = container.api.listEvents().firstOrNull()
                if (next == null) {
                    _state.value = EventDetailState(
                        isLoading = false,
                        error = "No hay eventos próximos ahora mismo.",
                    )
                    return@launch
                }
                val card = container.api.getEvent(next.id)
                _state.value = EventDetailState(isLoading = false, event = card)
            } catch (t: Throwable) {
                _state.value = EventDetailState(
                    isLoading = false,
                    error = "No se pudo cargar el evento: ${t.message ?: "desconocido"}",
                )
            }
        }
    }

    fun subscribe(
        boutId: String,
        eventId: String,
        matchNumber: Int,
        leadMinutes: Int,
        fighterNames: Pair<String, String>,
    ) {
        viewModelScope.launch {
            try {
                val sub = container.api.createSubscription(
                    com.despertarme.app.data.remote.BoutSubscriptionCreate(
                        eventId = eventId,
                        boutId = boutId,
                        targetMatchNumber = matchNumber,
                        leadMinutes = leadMinutes,
                    ),
                )
                _state.value = _state.value.copy(
                    subscribedBouts = _state.value.subscribedBouts + sub.boutId,
                )
                _snack.value = "Alerta creada: ${fighterNames.first} vs ${fighterNames.second} — $leadMinutes min"
            } catch (t: Throwable) {
                _snack.value = "No se pudo crear la alerta: ${t.message ?: "error"}"
            }
        }
    }
}

class EventListLoader(
    private val container: AppContainer,
) {
    suspend fun nextEvent(): EventSummaryOut? = runCatching {
        container.api.listEvents().firstOrNull()
    }.getOrNull()
}

class EventDetailViewModelFactory(
    private val container: AppContainer,
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T =
        EventDetailViewModel(container) as T
}