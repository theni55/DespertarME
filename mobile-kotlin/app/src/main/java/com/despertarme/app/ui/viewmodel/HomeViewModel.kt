package com.despertarme.app.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.despertarme.app.data.AppContainer
import com.despertarme.app.data.remote.BoutAthleteOut
import com.despertarme.app.data.remote.EventCardOut
import com.despertarme.app.data.remote.EventSummaryOut
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.time.Instant
import java.time.OffsetDateTime

data class HomeEventUi(
    val event: EventSummaryOut,
    val sport: String = "mma",
    val league: String = "",
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
            val allSummaries = try {
                coroutineScope {
                    val mmaDeferred = async {
                        runCatching { container.api.listEvents("mma", "") }
                            .getOrDefault(emptyList())
                            .map { Triple(it, "mma", "") }
                    }
                    val atpDeferred = async {
                        runCatching { container.api.listEvents("tennis", "atp") }
                            .getOrDefault(emptyList())
                            .map { Triple(it, "tennis", "atp") }
                    }
                    val wtaDeferred = async {
                        runCatching { container.api.listEvents("tennis", "wta") }
                            .getOrDefault(emptyList())
                            .map { Triple(it, "tennis", "wta") }
                    }
                    (mmaDeferred.await() + atpDeferred.await() + wtaDeferred.await())
                        .sortedBy { (event, _, _) -> parseDateEpoch(event.date) }
                        .take(MAX_FEATURED)
                }
            } catch (t: Throwable) {
                _state.value = HomeState(
                    isLoading = false,
                    error = "No se pudieron cargar los eventos: ${t.message ?: "desconocido"}",
                )
                return@launch
            }
            _state.value = HomeState(
                isLoading = false,
                events = allSummaries.map { (event, sport, league) ->
                    HomeEventUi(event, sport = sport, league = league)
                },
            )

            val enriched = coroutineScope {
                allSummaries.map { (summary, sport, league) ->
                    async {
                        val card = runCatching {
                            container.api.getEvent(summary.id, sport, league)
                        }.getOrNull()
                        val main = if (sport == "tennis") {
                            mainBoutTennis(card)
                        } else {
                            card?.bouts?.firstOrNull { it.matchNumber == 1 }
                        }
                        HomeEventUi(
                            event = summary,
                            sport = sport,
                            league = league,
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
        const val MAX_FEATURED = 4

        private fun parseDateEpoch(iso: String): Long = runCatching {
            OffsetDateTime.parse(iso).toEpochSecond()
        }.getOrDefault(Long.MAX_VALUE)

        private fun mainBoutTennis(card: EventCardOut?) = runCatching {
            val bouts = card?.bouts ?: return@runCatching null
            if (bouts.isEmpty()) return@runCatching null
            val nowEpoch = Instant.now().epochSecond
            bouts.minByOrNull { bout ->
                val boutEpoch = runCatching {
                    OffsetDateTime.parse(bout.date).toEpochSecond()
                }.getOrDefault(Long.MAX_VALUE)
                kotlin.math.abs(boutEpoch - nowEpoch)
            }
        }.getOrNull()
    }
}

class HomeViewModelFactory(
    private val container: AppContainer,
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T =
        HomeViewModel(container) as T
}
