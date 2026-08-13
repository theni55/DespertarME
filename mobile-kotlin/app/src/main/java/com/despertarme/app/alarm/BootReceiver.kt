package com.despertarme.app.alarm

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log
import com.despertarme.app.DespertarMeApp
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class BootReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return

        val app = context.applicationContext as DespertarMeApp
        val pendingResult = goAsync()
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val (restored, total) = AlarmScheduler.restorePending(app)
                Log.i(
                    "BootReceiver",
                    "Reprogramadas $restored/$total alarmas pendientes tras reinicio",
                )
            } finally {
                pendingResult.finish()
            }
        }
    }
}
