package com.despertarme.app.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.despertarme.app.data.AppContainer
import com.despertarme.app.data.remote.BoutAthleteOut
import com.despertarme.app.data.remote.EventSummaryOut
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/**
 * Card de evento del Home: summary del listado + datos del main event
 * (headshots reales de ESPN) cargados en segunda fase, best-effort.
 */
data class HomeEventUi(
    val event: EventSummaryOut,
    val mainRed: BoutAthleteOut? = null,
    val mainBlue: BoutAthleteOut? = null,
    val boutCount: Int? = null,
)

data class HomeState(
    val isLoading: Boolean = true,
    val events: List<HomeEventUi> = emptyList(),
    val error: String? = null,
)

class HomeViewModel(
    private val container: AppContainer,
) : ViewModel() {

    private val _state = MutableStateFlow(HomeState())
    val state: StateFlow<HomeState> = _state.asStateFlow()

    fun load(force: Boolean = false) {
        val current = _state.value
        if (!force && !current.isLoading && current.error == null && current.events.isNotEmpty()) return
        _state.value = HomeState(isLoading = true)
        viewModelScope.launch {
            val upcoming = try {
                container.api.listEvents().take(MAX_FEATURED)
            } catch (t: Throwable) {
                _state.value = HomeState(
                    isLoading = false,
                    error = "No se pudieron cargar los próximos eventos: ${t.message ?: "desconocido"}",
                )
                return@launch
            }
            // Fase 1: render inmediato con los summaries (sin headshots todavía).
            _state.value = HomeState(isLoading = false, events = upcoming.map { HomeEventUi(it) })

            // Fase 2: enriquecer cada card con el main event (matchNumber == 1)
            // en paralelo. ESPN no sirve póster por evento (D42); los headshots
            // del main event son la única imagen real disponible por evento (D47).
            val enriched = coroutineScope {
                upcoming.map { summary ->
                    async {
                        val card = runCatching { container.api.getEvent(summary.id) }.getOrNull()
                        val main = card?.bouts?.firstOrNull { it.matchNumber == 1 }
                        HomeEventUi(
                            event = summary,
                            mainRed = main?.red,
                            mainBlue = main?.blue,
                            boutCount = card?.bouts?.size,
                        )
                    }
                }.awaitAll()
            }
            _state.value = HomeState(isLoading = false, events = enriched)
        }
    }

    companion object {
        // Top N eventos destacados en Home (validación de sesión: 3-5).
        const val MAX_FEATURED = 4
    }
}

class HomeViewModelFactory(
    private val container: AppContainer,
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T =
        HomeViewModel(container) as T
}
