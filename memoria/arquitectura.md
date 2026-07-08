# Arquitectura

> Snapshot del diseño: diagrama de componentes, flujo de alerta, entidades y stack.

Snapshot rápido para entender el diseño sin releer todos los módulos. El detalle
de decisiones vive en `decisiones.md`; las fuentes de datos en `fuentes-datos.md`.

---

## Diagrama de componentes

```
                +-----------------------------+
                |        FastAPI app          |
                |  (REST auth + admin web)    |
                +-------------+---------------+
                              |
            +-----------------+-----------------+
            |                                   |
   +--------v---------+              +---------v----------+
   |   Providers       |              |   EstimatorEngine   |
   | - ESPN UFC         |              | - recálculo         |
   | - TheSportsDB     |              |   según combate previo
   | - Scraping Tenis  |              | - regla "X min antes"|
   +--------+---------+              +---------+----------+
            |                                   |
            +-----------------+-----------------+
                              |
                     +--------v--------+
                     | APScheduler poller
                     | (cadencia adaptativa)|
                     +--------+--------+
                              |
                     +--------v--------+
                     | Notifier dispatcher
                     | - VoiceNotifier  |
                     |   (mock → Twilio)|
                     +-----------------+
```

---

## Flujo de una alerta

1. **Poller** (APScheduler) consulta cada N segundos el provider del evento suscrito.
2. **Provider** devuelve la card con estado de cada combate (`scheduled`/`in_progress`/`ended`) y tiempos reales.
3. **EstimatorEngine** detecta transiciones de estado del combate inmediatamente anterior al objetivo y recalcula `start_estimado`:
   - Combate `n-1` en `in_progress` → `start_n ≈ now + (duración_media − ya_transcurrido)`.
   - Combate `n-1` en `ended` → `start_n = now + buffer_intercombate` (D18: 5 min).
4. Si `start_estimado − now ≤ X_min_configurado` y no se ha disparado ya la alerta para esa suscripción → **notifier.call(user, bout_info)**.
5. **alert_log** registra todo en BD (auditable desde admin).

### Cadencia de polling adaptativa (D15)

| Estado combate previo | Intervalo | Justificación |
|-----------------------|-----------|---------------|
| Sin combates próximos | 60 s | Ahorro en reposo |
| Previo `in_progress` avanzado | 10 s | Equilibrio precisión/coste |
| Previo `post` (terminado) | 5 s | Máxima precisión, buffer pequeño |

### Idempotencia y reintentos

- **Idempotencia** (D16): clave Redis `alert:{sub_id}:{bout_id}:{status}` TTL 7200 s + UNIQUE `(subscription_id, bout_id, fired_at_hour)` en `alert_log`.
- **Reintentos de llamada** (D17): 3 intentos con backoff exponencial 1 s / 5 s / 30 s. Si todos fallan → log `error` + marcar `failed`.
- **Resiliencia ESPN** (D20, D24): backoff exponencial con jitter (1→60 s cap) vía `tenacity` + circuit breaker manual (5 fallos consecutivos → 60 s open). El CB acepta un `clock` inyectable para tests.

---

## Entidades clave (draft — concretar en Fase 2)

| Entidad | Campos principales |
|---------|-------------------|
| `users` | id, email, phone_normalized, timezone (default `Europe/Madrid`), role |
| `sports_subscriptions` | user_id, sport |
| `event_subscriptions` | user_id, event_id, lead_minutes |
| `bout_subscriptions` | user_id, bout_id, previous_bout_id, lead_minutes, status |
| `notification_channels` | user_id, type=phone, config_json |
| `alert_log` | subscription_id, bout_id, fired_at, fired_at_hour, payload, notifier_response |

---

## Stack tecnológico

| Capa | Tecnología | Versión |
|------|-----------|---------|
| Lenguaje | Python | 3.12+ |
| Framework | FastAPI (async) | última |
| Scheduler | APScheduler (pendiente integrar, D29) | 3.x |
| ORM | SQLAlchemy 2.x async + Alembic | 2.x |
| BD | PostgreSQL 16 (prod) / SQLite+aiosqlite (dev, D26) | 16 / — |
| Cache/state | Redis 7 (prod) / fakeredis (tests, D27) | 7 / — |
| HTTP client | httpx (async) | última |
| Resiliencia | tenacity (backoff) + circuit breaker manual (D24) | 9.x |
| Auth | passlib[bcrypt] + PyJWT (D28) | — |
| Web admin | Jinja2 + HTMX (D21) | — |
| Proveedor SIM | Twilio (D23, Fase 5) | — |
| Tests | pytest + pytest-asyncio + respx + freezegun + fakeredis | — |
| Lint/format | ruff + black + mypy | — |

---

## Estructura de módulos (Fase 0–3)

```
src/app/
├─ main.py              # FastAPI app + routers
├─ config.py            # pydantic-settings
├─ db/
│  ├─ session.py        # engine async SQLAlchemy
│  └─ models/           # User, SportSubscription, EventSubscription,
│                       # BoutSubscription, AlertLog (UNIQUE D16)
├─ providers/           # Fase 0: ESPN UFC
│  ├─ base.py           # ABC Provider
│  ├─ models.py         # DTOs pydantic (parsing ESPN)
│  └─ espn_ufc.py       # EspnUfcProvider + tenacity + CB (D24)
├─ domain/
│  └─ entities.py       # dataclasses frozen (Bout, Card, EstimatedStart...) (D25)
├─ engine/
│  ├─ estimator.py      # EstimatorEngine (recálculo puro, D15/D18)
│  ├─ state.py          # AlertState (Redis idempotencia, D16)
│  └─ poller.py         # Poller (orquestación + reintentos D17, D29)
├─ notifiers/
│  ├─ base.py           # VoiceNotifier + AlertPayload/CallResult
│  └─ dummy.py          # DummyNotifier (log-only)
├─ auth/                # Fase 3: JWT
│  ├─ security.py       # hash/verify + create/decode token
│  └─ dependencies.py   # get_current_user / require_admin
├─ api/                 # Fase 3: REST
│  ├─ schemas.py        # pydantic request/response DTOs
│  └─ routes/           # auth, users, subscriptions, alert_log
└─ web/                 # Fase 3: admin web
   ├─ admin.py          # router Jinja2 + HTMX
   └─ templates/        # base, login, dashboard, users, alerts
```

---

## Ver también

- **Proveedores de datos** (ESPN, TheSportsDB, scraping) → `fuentes-datos.md`
- **Decisiones de diseño D1–D29** → `decisiones.md`
- **Roadmap por fases** → `fases.md`
