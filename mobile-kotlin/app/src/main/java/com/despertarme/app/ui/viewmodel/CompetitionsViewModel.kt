package com.despertarme.app.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.despertarme.app.data.AppContainer
import com.despertarme.app.data.remote.EventSummaryOut
import kotlinx.coroutines.Job
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class CompetitionUi(
    val event: EventSummaryOut,
    val sport: String,
    val league: String,
)

data class CompetitionsState(
    val isLoading: Boolean = true,
    val tournaments: List<CompetitionUi> = emptyList(),
    val error: String? = null,
)

class CompetitionsViewModel(
    private val container: AppContainer,
) : ViewModel() {

    private val _state = MutableStateFlow(CompetitionsState())
    val state: StateFlow<CompetitionsState> = _state.asStateFlow()

    private var loadJob: Job? = null

    fun load(sport: String) {
        loadJob?.cancel()
        _state.value = CompetitionsState(isLoading = true)
        loadJob = viewModelScope.launch {
            try {
                val tournaments = when (sport) {
                    "tennis" -> {
                        val (atp, wta) = coroutineScope {
                            val atpDeferred = async {
                                runCatching { container.api.listEvents("tennis", "atp") }.getOrDefault(emptyList())
                            }
                            val wtaDeferred = async {
                                runCatching { container.api.listEvents("tennis", "wta") }.getOrDefault(emptyList())
                            }
                            atpDeferred.await() to wtaDeferred.await()
                        }
                        atp.map { CompetitionUi(it, "tennis", "atp") } +
                            wta.map { CompetitionUi(it, "tennis", "wta") }
                    }
                    "nba" -> {
                        val events = container.api.listEvents("nba", "")
                        events.map { CompetitionUi(it, "nba", "") }
                    }
                    "football" -> {
                        val leagues = listOf(
                            "esp.1", "eng.1", "ita.1", "ger.1", "fra.1",
                            "uefa.champions", "uefa.europa",
                        )
                        val results = coroutineScope {
                            leagues.map { slug ->
                                async {
                                    runCatching { container.api.listEvents("football", slug) }
                                        .getOrDefault(emptyList())
                                        .map { CompetitionUi(it, "football", slug) }
                                }
                            }.awaitAll()
                        }
                        results.flatten()
                    }
                    else -> {
                        val events = container.api.listEvents("mma", "")
                        events.map { CompetitionUi(it, "mma", "") }
                    }
                }
                _state.value = CompetitionsState(isLoading = false, tournaments = tournaments)
            } catch (t: Exception) {
                _state.value = CompetitionsState(
                    isLoading = false,
                    error = "No se pudieron cargar las competiciones: ${t.message ?: "desconocido"}",
                )
            }
        }
    }
}

class CompetitionsViewModelFactory(
    private val container: AppContainer,
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T =
        CompetitionsViewModel(container) as T
}
