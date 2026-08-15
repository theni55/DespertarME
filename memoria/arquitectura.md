# Arquitectura

> Snapshot del diseño: diagrama de componentes, flujo de alerta, entidades y stack.

Snapshot rápido para entender el diseño sin releer todos los módulos. El detalle
de decisiones vive en `decisiones.md`; las fuentes de datos en `fuentes-datos.md`.

---

## Diagrama de componentes

```
 +-----------------------------+
 |   App Android (Kotlin)      |
 |  Compose + AlarmManager +   |
 |  FirebaseMessaging (FCM)    |
 +-------------+---------------+
               |  HTTPS (REST) + FCM data-only
 +-------------v---------------+
 |        FastAPI app          |
 |  (REST /api + scheduler)    |
 +-------------+---------------+
               |
 +-------------+-----------------------------+
 |                                           |
 +--------v---------+              +---------v----------+
 |   Providers       |              |   EstimatorEngine   |
 | - ESPN UFC/Tenis  |              | - recálculo por     |
 |   (ATP/WTA)/NBA/  |              |   deporte/buffer    |
 |   NFL/Fútbol      |              |   (D15/D18/D57/D72) |
 +--------+---------+              +---------+----------+
          |                                    |
          +-----------------+------------------+
                            |
                  +---------v---------+
                  | Poller (APScheduler)|
                  | push on-change (D40)|
                  +---------+---------+
                            |
                  +---------v---------+
                  | Notifier FCM       |
                  | update/started/    |
                  | cancelled/fire     |
                  +-------------------+
```

- **Fuente de la hora de alarma**: una **alarma local exacta** en el dispositivo
  (`AlarmManager.setAlarmClock`), programada al recibir el push FCM `update`.
  El backend solo **mantiene fresca la estimación** (D40/D45).

---

## Flujo de una alerta

1. El usuario se suscribe a un combate/partido en la app (con lead 5/10/15/30, o
   0 para "cuando empieza" en cuartos NBA/NFL).
2. El **Poller** consulta cada 60 s el estado del combate previo vía el provider
   ESPN del deporte/liga de la suscripción.
3. El **EstimatorEngine** recalcula `start_estimado` según la transición del
   combate previo:
   - `pre` → no hay info real; no se pushea (D45).
   - `in` → `now + (duración_media − transcurrido) + buffer`.
   - `post` → `observed_at + buffer` (anclado a la primera observación, E2).
4. Si la estimación se mueve >60 s desde el último push → **push FCM `update`**
   con `estimated_start_at` (epoch millis), `bout_id`, `fighters`, `lead_minutes`.
5. La app Android recibe el push y (re)programa la **alarma local** a
   `estimated_start_at − lead` con un cushion de +1 min (D45). Al disparar,
   suena `TYPE_ALARM` (bypass DnD) + full-screen intent + marca `fired` (ring-once).
6. `started`/`cancelled` informan si el combate empezó/canceló; `alert_log`
   audita cada push en BD.

### Cadencia de polling (D15)

| Estado combate previo | Intervalo | Justificación |
|-----------------------|-----------|---------------|
| `pre` / sin previo | 60 s | Reposo |
| `in` avanzado | 10 s | Equilibrio precisión/coste |
| `post` | 5 s | Máxima precisión, buffer pequeño |

### Idempotencia y resiliencia

- **Idempotencia** (D16/E6/A10): Redis `alert:{sub}:{bout}:{status}` + partial
  unique index `(subscription_id, bout_id, message_type)` en `alert_log` solo
  para `started`/`cancelled`; las filas `update` son audit puro.
- **FCM permanente** (A8): error `NotRegistered`/`InvalidArgument` invalida
  `device.fcm_token` (pausa las subs del device hasta re-registro).
- **404 de evento** (A11): las suscripciones a eventos inexistentes se marcan
  `fired` para no reintentar cada ciclo.
- **Resiliencia ESPN** (D20/D24): backoff exponencial con jitter vía `tenacity` +
  circuit breaker manual (5 fallos consecutivos → 60 s open).

---

## Entidades clave

| Entidad | Campos principales |
|---------|-------------------|
| `devices` | id (UUID), fcm_token, platform, timezone, locale, is_active, last_seen_at |
| `bout_subscriptions` | id, device_id, event_id, bout_id, target_match_number, lead_minutes, sport, league, status |
| `alert_log` | id, subscription_id, device_id, bout_id, message_type, fired_at, fired_at_epoch_hour, payload, status |

---

## Stack tecnológico

| Capa | Tecnología | Versión |
|------|-----------|---------|
| Backend | Python + FastAPI (async) | 3.12+ / última |
| Scheduler | APScheduler in-process en lifespan (D31) | 3.x |
| ORM | SQLAlchemy 2.x async + Alembic | 2.x |
| BD | PostgreSQL 16 (prod) / SQLite+aiosqlite (dev, D26) | — |
| Cache/state | Redis 7 (prod) / fakeredis (dev/tests, D27/D55) | — |
| HTTP client | httpx (async) | última |
| Push | firebase-admin (FCM data-only high-priority) | 6.x |
| App Android | Kotlin + Jetpack Compose (D43) | Kotlin 2.0 / AGP 8.7 |
| App Android deps | Retrofit + kotlinx-serialization, Coil, DataStore, Navigation Compose, Material3, firebase-messaging | — |
| Alarma | `AlarmManager.setAlarmClock` + `TYPE_ALARM` + full-screen intent | — |
| Deploy | Railway (always-on, PG+Redis add-ons, D33) | — |
| Tests | pytest + pytest-asyncio + respx + freezegun + fakeredis; JUnit Android | — |
| Lint/format | ruff + black + mypy | — |

---

## Estructura de módulos

```
src/app/
├─ main.py              # FastAPI app + routers + lifespan (scheduler D31)
├─ config.py            # pydantic-settings (+ normalización DATABASE_URL PaaS, D33)
├─ scheduler.py         # PollerScheduler: providers multi-sport + buffer_for (D57/D72/A9)
├─ db/
│  ├─ session.py        # engine async SQLAlchemy
│  └─ models/           # Device, BoutSubscription, AlertLog
├─ providers/           # ESPN: UFC, tenis (ATP/WTA), NBA, NFL, fútbol
│  ├─ base.py           # ABC Provider
│  ├─ _base_provider.py # CB + tenacity + HTTP compartidos
│  ├─ _visibility.py    # filtro universal de bouts (D78)
│  ├─ models.py         # DTOs pydantic (parsing ESPN)
│  ├─ athletes.py       # AthleteResolver (caché Redis+memoria, D32/D74)
│  ├─ teams.py          # TeamResolver (NBA/NFL/fútbol, D58)
│  └─ espn_*.py         # EspnUfc/Tennis/Nba/Nfl/FootballProvider
├─ domain/
│  └─ entities.py       # dataclasses frozen (Bout, Card, EstimatedStart...) (D25)
├─ engine/
│  ├─ estimator.py      # EstimatorEngine (recálculo puro, D15/D18/D57)
│  ├─ state.py          # AlertState (Redis idempotencia/anclaje, D16/E2)
│  └─ poller.py         # Poller (push on-change D40, multi-sport, A2/A7/A8/A11)
├─ notifiers/
│  ├─ __init__.py       # build_notifier(): FCM gated por config
│  ├─ base.py           # PushNotifier + AlertPayload/PushResult
│  ├─ dummy.py          # DummyNotifier (log-only)
│  └─ fcm.py            # FcmNotifier (firebase-admin data-only)
└─ api/
   ├─ schemas.py        # DTOs (device/subscription/events/alert_log; allowlist A11)
   └─ routes/           # devices, subscriptions, events, alert_log

mobile-kotlin/app/src/main/java/com/despertarme/app/
├─ MainActivity.kt      # single-activity Compose + nav + onboarding permisos
├─ fcm/DespertarMeFirebaseService.kt  # handleUpdate/Started/Cancelled/Fire (D45)
├─ alarm/               # AlarmScheduler, AlarmTriggerPolicy, AlarmService,
│                       # AlarmReceiver, AlarmActivity, PendingAlarm, BootReceiver
├─ data/                # AppContainer, DeviceStorage, Retrofit (DespertarApi, Models)
└─ ui/                  # theme, screens (Home/EventList/Competitions/EventDetail/
                        # Subscriptions/Settings), viewmodels
```

---

## Ver también

- **Proveedores de datos** (ESPN por deporte) → `fuentes-datos.md`
- **Decisiones de diseño D1–D92** → `decisiones.md`
- **Roadmap por fases** → `fases.md`
