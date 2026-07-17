package com.despertarme.app.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.despertarme.app.data.AppContainer
import com.despertarme.app.data.remote.EventSummaryOut
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class EventListState(
    val isLoading: Boolean = true,
    val events: List<EventSummaryOut> = emptyList(),
    val error: String? = null,
)

class EventListViewModel(
    private val container: AppContainer,
) : ViewModel() {

    private val _state = MutableStateFlow(EventListState())
    val state: StateFlow<EventListState> = _state.asStateFlow()

    fun load(force: Boolean = false) {
        if (!force && !_state.value.isLoading && _state.value.error == null) return
        _state.value = EventListState(isLoading = true)
        viewModelScope.launch {
            try {
                val events = container.api.listEvents()
                _state.value = EventListState(isLoading = false, events = events)
            } catch (t: Throwable) {
                _state.value = EventListState(
                    isLoading = false,
                    error = "No se pudieron cargar los eventos: ${t.message ?: "desconocido"}",
                )
            }
        }
    }
}

class EventListViewModelFactory(
    private val container: AppContainer,
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T =
        EventListViewModel(container) as T
}
