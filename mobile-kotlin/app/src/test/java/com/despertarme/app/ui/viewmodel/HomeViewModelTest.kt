package com.despertarme.app.ui.viewmodel

import com.despertarme.app.data.remote.EventSummaryOut
import org.junit.Assert.assertEquals
import org.junit.Test

class HomeViewModelTest {

    private fun ev(id: String, date: String) =
        EventSummaryOut(id = id, name = "Evento $id", date = date)

    @Test
    fun selectHomeEvents_agrupa_futbol_en_una_card_y_mantiene_atp_wta_separadas() {
        val all = listOf(
            Triple(ev("mma-1", "2026-08-16T10:00:00Z"), "mma", ""),
            Triple(ev("atp-1", "2026-08-16T12:00:00Z"), "tennis", "atp"),
            Triple(ev("wta-1", "2026-08-16T11:00:00Z"), "tennis", "wta"),
            Triple(ev("nba-1", "2026-08-16T13:00:00Z"), "nba", ""),
            Triple(ev("nfl-1", "2026-08-16T14:00:00Z"), "nfl", ""),
            Triple(ev("foot-esp", "2026-08-16T09:00:00Z"), "football", "esp.1"),
            Triple(ev("foot-eng", "2026-08-16T08:00:00Z"), "football", "eng.1"),
            Triple(ev("foot-ita", "2026-08-16T07:00:00Z"), "football", "ita.1"),
        )

        val result = HomeViewModel.selectHomeEvents(all)

        // Fútbol aporta 1 sola card (su partido mas proximo), no 3.
        assertEquals(1, result.count { it.second == "football" })
        assertEquals("foot-ita", result.first { it.second == "football" }.first.id)

        // Total <= 6 (mma+atp+wta+nba+nfl+futbol).
        assertEquals(6, result.size)

        // ATP y WTA siguen siendo cards separadas.
        assertEquals(1, result.count { it.second == "tennis" && it.third == "atp" })
        assertEquals(1, result.count { it.second == "tennis" && it.third == "wta" })
    }

    @Test
    fun selectHomeEvents_respeta_el_techo_max_featured() {
        // Mas combinaciones sport+league que el techo: debe recortar a 6.
        val all = listOf(
            Triple(ev("mma-1", "2026-08-16T10:00:00Z"), "mma", ""),
            Triple(ev("atp-1", "2026-08-16T12:00:00Z"), "tennis", "atp"),
            Triple(ev("wta-1", "2026-08-16T11:00:00Z"), "tennis", "wta"),
            Triple(ev("nba-1", "2026-08-16T13:00:00Z"), "nba", ""),
            Triple(ev("nfl-1", "2026-08-16T14:00:00Z"), "nfl", ""),
            Triple(ev("foot-esp", "2026-08-16T09:00:00Z"), "football", "esp.1"),
            Triple(ev("foot-eng", "2026-08-16T08:00:00Z"), "football", "eng.1"),
        )
        val result = HomeViewModel.selectHomeEvents(all)
        assertEquals(6, result.size)
    }
}
