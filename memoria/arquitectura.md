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
- **Resiliencia ESPN** (D20): backoff exponencial con jitter (1→60 s cap) + circuit breaker (5 fallos/min → 60 s open).

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
| Scheduler | APScheduler | 3.x |
| ORM | SQLAlchemy 2.x async + Alembic | 2.x |
| BD | PostgreSQL 16 (docker-compose) | 16 |
| Cache/state | Redis 7 (docker-compose) | 7 |
| HTTP client | httpx (async) | última |
| Web admin | Jinja2 + HTMX (D21) | — |
| Proveedor SIM | Twilio (D23, Fase 5) | — |
| Tests | pytest + pytest-asyncio + respx + freezegun | — |
| Lint/format | ruff + black + mypy | — |

---

## Ver también

- **Proveedores de datos** (ESPN, TheSportsDB, scraping) → `fuentes-datos.md`
- **Decisiones de diseño D1–D23** → `decisiones.md`
- **Roadmap por fases** → `fases.md`
