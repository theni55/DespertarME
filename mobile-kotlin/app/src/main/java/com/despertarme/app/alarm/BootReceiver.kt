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
        CoroutineScope(Dispatchers.IO).launch {
            val alarms = PendingAlarmStorage.all(app)
            Log.i("BootReceiver", "Reprogramando ${alarms.size} alarmas tras reinicio")
            alarms.forEach { alarm ->
                AlarmScheduler.schedule(app, alarm)
            }
        }
    }
}
