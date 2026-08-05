package com.despertarme.app.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.despertarme.app.DespertarMeApp
import com.despertarme.app.alarm.AlarmScheduler
import com.despertarme.app.data.AppContainer
import com.despertarme.app.data.remote.BoutSubscriptionOut
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class SubscriptionUi(
    val sub: BoutSubscriptionOut,
    val fightLabel: String,
    val eventName: String?,
    val sport: String = "mma",
)

data class AlertUi(
    val id: String,
    val fightLabel: String,
    val firedAt: String,
    val status: String,
)

data class SubscriptionsState(
    val isLoading: Boolean = true,
    val subscriptions: List<SubscriptionUi> = emptyList(),
    val alerts: List<AlertUi> = emptyList(),
    val error: String? = null,
)

class SubscriptionsViewModel(
    private val container: AppContainer,
) : ViewModel() {

    private val _state = MutableStateFlow(SubscriptionsState())
    val state: StateFlow<SubscriptionsState> = _state.asStateFlow()

    private val _snack = MutableStateFlow<String?>(null)
    val snackMessage: StateFlow<String?> = _snack.asStateFlow()

    fun clearSnack() { _snack.value = null }

    fun prepareForLoad() {
        _state.value = SubscriptionsState(isLoading = true, error = null)
    }

    fun load() {
        _state.value = _state.value.copy(isLoading = true, error = null)
        viewModelScope.launch {
            try {
                val subs = container.api.listSubscriptions()
                val alertsRaw = runCatching { container.api.listAlerts() }.getOrDefault(emptyList())
                val uiSubs = resolveLabels(subs)
                // Enriquecer historial con fightLabel cruzando con suscripciones.
                val subByBout = subs.associateBy { it.boutId }
                val enrichedAlerts = alertsRaw.map { alert ->
                    val sub = subByBout[alert.boutId]
                    val fightLabel = if (sub != null) {
                        uiSubs.firstOrNull { it.sub.id == sub.id }?.fightLabel ?: "Combate"
                    } else {
                        "Combate"
                    }
                    AlertUi(
                        id = alert.id,
                        fightLabel = fightLabel,
                        firedAt = alert.firedAt,
                        status = alert.status,
                    )
                }
                _state.value = SubscriptionsState(
                    isLoading = false,
                    subscriptions = uiSubs,
                    alerts = enrichedAlerts,
                )
            } catch (t: Exception) {
                _state.value = _state.value.copy(
                    isLoading = false,
                    error = "No se pudieron cargar las alertas: ${t.message ?: "desconocido"}",
                )
            }
        }
    }

    fun cancel(subId: String) {
        viewModelScope.launch {
            try {
                container.api.deleteSubscription(subId)
                _state.value = _state.value.copy(
                    subscriptions = _state.value.subscriptions.filterNot { it.sub.id == subId },
                )
                _snack.value = "Alerta cancelada"

                val current = _state.value.subscriptions.firstOrNull { it.sub.id == subId }?.sub
                if (current != null) {
                    AlarmScheduler.cancel(DespertarMeApp.instance, current.boutId)
                }
            } catch (t: Exception) {
                _snack.value = "No se pudo cancelar: ${t.message ?: "error"}"
            }
        }
    }

    // El backend solo devuelve ids en la suscripcion; resolvemos nombres de
    // peleadores con una fetch por evento unico (normalmente 1) y cache local.
    // La key del mapa incluye league porque el backend necesita sport+league
    // para encontrar el provider correcto (ej: atp vs wta para tenis).
    private suspend fun resolveLabels(subs: List<BoutSubscriptionOut>): List<SubscriptionUi> {
        val cards = subs.map { Triple(it.eventId, it.sport, it.league) }.distinct()
            .associateWith { (eventId, sport, league) ->
            runCatching { container.api.getEvent(eventId, sport, league) }.getOrNull()?.also { card ->
                // Si la card se obtuvo pero el bout no esta (bout_id cambiado por ESPN),
                // el fallback de abajo lo manejara sin numero (#0).
            } ?: run {
                android.util.Log.w(
                    "SubscriptionsViewModel",
                    "getEvent($eventId, $sport, $league) fallo — usando label fallback",
                )
                null
            }
        }
        return subs.map { sub ->
            val card = cards[Triple(sub.eventId, sub.sport, sub.league)]
            val bout = card?.bouts?.firstOrNull { it.id == sub.boutId }
            val label = if (bout != null) {
                "${bout.red?.name ?: "TBD"} vs ${bout.blue?.name ?: "TBD"}"
            } else {
                android.util.Log.w(
                    "SubscriptionsViewModel",
                    "bout ${sub.boutId} no encontrado en card del evento ${sub.eventId}",
                )
                when (sub.sport) {
                    "tennis" -> "Partido"
                    "nba" -> if (sub.targetMatchNumber == 1) "Inicio" else "Cuarto #${sub.targetMatchNumber}"
                    "nfl" -> if (sub.targetMatchNumber == 1) "Inicio" else "Cuarto #${sub.targetMatchNumber}"
                    "football" -> "Partido"
                    else -> "Combate"
                }
            }
            SubscriptionUi(
                sub = sub,
                fightLabel = label,
                eventName = card?.name,
                sport = sub.sport,
            )
        }
    }
}

class SubscriptionsViewModelFactory(
    private val container: AppContainer,
) : ViewModelProvider.Factory {
    @Suppress("UNCHECKED_CAST")
    override fun <T : ViewModel> create(modelClass: Class<T>): T =
        SubscriptionsViewModel(container) as T
}
