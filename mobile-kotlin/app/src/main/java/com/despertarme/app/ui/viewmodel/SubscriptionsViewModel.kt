package com.despertarme.app.ui.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import com.despertarme.app.data.AppContainer
import com.despertarme.app.data.remote.AlertLogOut
import com.despertarme.app.data.remote.BoutSubscriptionOut
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class SubscriptionUi(
    val sub: BoutSubscriptionOut,
    val fightLabel: String,
    val eventName: String?,
)

data class SubscriptionsState(
    val isLoading: Boolean = true,
    val subscriptions: List<SubscriptionUi> = emptyList(),
    val alerts: List<AlertLogOut> = emptyList(),
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

    fun load() {
        _state.value = _state.value.copy(isLoading = true, error = null)
        viewModelScope.launch {
            try {
                val subs = container.api.listSubscriptions()
                val alerts = runCatching { container.api.listAlerts() }.getOrDefault(emptyList())
                val uiSubs = resolveLabels(subs)
                _state.value = SubscriptionsState(
                    isLoading = false,
                    subscriptions = uiSubs,
                    alerts = alerts,
                )
            } catch (t: Throwable) {
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
            } catch (t: Throwable) {
                _snack.value = "No se pudo cancelar: ${t.message ?: "error"}"
            }
        }
    }

    // El backend solo devuelve ids en la suscripcion; resolvemos nombres de
    // peleadores con una fetch por evento unico (normalmente 1) y cache local.
    private suspend fun resolveLabels(subs: List<BoutSubscriptionOut>): List<SubscriptionUi> {
        val cards = subs.map { it.eventId }.distinct().associateWith { eventId ->
            runCatching { container.api.getEvent(eventId) }.getOrNull()
        }
        return subs.map { sub ->
            val card = cards[sub.eventId]
            val bout = card?.bouts?.firstOrNull { it.id == sub.boutId }
            val label = if (bout != null) {
                "${bout.red?.name ?: "TBD"} vs ${bout.blue?.name ?: "TBD"}"
            } else {
                "Combate #${sub.targetMatchNumber}"
            }
            SubscriptionUi(sub = sub, fightLabel = label, eventName = card?.name)
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
