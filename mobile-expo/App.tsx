import { StatusBar } from "expo-status-bar";
import { NativeModules, Pressable, StyleSheet, Text, View } from "react-native";
import { useEffect, useState } from "react";

const { AlarmModule } = NativeModules as { AlarmModule?: AlarmModuleType };

type AlarmModuleType = {
  startAlarm: () => Promise<void>;
  stopAlarm: () => Promise<void>;
};

export default function App() {
  const [available, setAvailable] = useState(true);
  const [running, setRunning] = useState(false);
  const [message, setMessage] = useState<string>("Listo.");

  useEffect(() => {
    setAvailable(Boolean(AlarmModule));
    if (!AlarmModule) setMessage("Native module no encontrado. ¿Build sin prebuild?");
  }, []);

  async function start() {
    if (!AlarmModule) return;
    try {
      await AlarmModule.startAlarm();
      setRunning(true);
      setMessage("AlarmService arrancado. Pon el móvil en DnD y mira si suena.");
    } catch (e) {
      setMessage(`startAlarm error: ${String(e)}`);
    }
  }

  async function stop() {
    if (!AlarmModule) return;
    try {
      await AlarmModule.stopAlarm();
      setRunning(false);
      setMessage("AlarmService detenido.");
    } catch (e) {
      setMessage(`stopAlarm error: ${String(e)}`);
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>DespertarME · Spike bypass-silent</Text>
      <Text style={styles.subtitle}>Solo valida: ¿suena TYPE_ALARM en modo DnD?</Text>
      <Text style={styles.status}>Modulo nativo: {available ? "OK" : "NO"}</Text>
      <Text style={styles.status}>Service: {running ? "RUNNING" : "stopped"}</Text>
      <Pressable
        style={[styles.btn, styles.btnStart, !available && styles.btnDisabled]}
        onPress={start}
        disabled={!available || running}
      >
        <Text style={styles.btnText}>Probar alarma</Text>
      </Pressable>
      <Pressable
        style={[styles.btn, styles.btnStop, (!available || !running) && styles.btnDisabled]}
        onPress={stop}
        disabled={!available || !running}
      >
        <Text style={styles.btnText}>Parar</Text>
      </Pressable>
      <Text style={styles.message}>{message}</Text>
      <StatusBar style="light" />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: "#0A0A0A",
    alignItems: "center",
    justifyContent: "center",
    padding: 24,
    gap: 12,
  },
  title: { color: "#fff", fontSize: 20, fontWeight: "700", textAlign: "center" },
  subtitle: { color: "#E50914", fontSize: 13, textAlign: "center", marginBottom: 24 },
  status: { color: "#bdbdbd", fontSize: 13 },
  btn: { paddingVertical: 16, paddingHorizontal: 32, borderRadius: 12, minWidth: 220, alignItems: "center" },
  btnStart: { backgroundColor: "#E50914" },
  btnStop: { backgroundColor: "#333" },
  btnDisabled: { opacity: 0.4 },
  btnText: { color: "#fff", fontSize: 16, fontWeight: "600" },
  message: { color: "#9e9e9e", fontSize: 12, textAlign: "center", marginTop: 16, minHeight: 40 },
});