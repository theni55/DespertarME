# Handoff

> Punto de entrada de cada sesión: estado actual, último avance y próximo paso. Actualízalo al final de cada sesión.

## ⚠️ Tarea pendiente al iniciar la próxima sesión: crear skill `ship-polished-ui`

**Contexto:** en la sesión anterior el owner pidió leer el artículo
["The 10 rules to ship truly polished UI with Claude"](https://x.com/kvnkld/status/2066863634949779464)
de Kevin (@kvnkld) y convertirlo en una skill de OpenCode. Se leyó el
artículo completo (vía mirror, ya que x.com requiere JS) y se acordó el
plan con el owner mediante preguntas de clarificación. **No se llegó a
crear el archivo** — la sesión terminó en modo plan justo antes de
ejecutarlo. Esta es la primera tarea de la próxima sesión.

**Decisiones ya confirmadas por el owner:**
- Nombre de la skill: **`ship-polished-ui`**
- Idioma del contenido: **inglés** (consistente con las demás skills del repo)
- Incluir subcarpeta `references/` con `motion-library.md` (patrón ya usado
  por `frontend-ui-engineering`)

**Archivos a crear:**

```
.opencode/skills/ship-polished-ui/
├─ SKILL.md
└─ references/
   └─ motion-library.md
```

### `SKILL.md` — contenido a incluir

Frontmatter:
```yaml
---
name: ship-polished-ui
description: Adds premium polish and micro-interactions to UIs. Use when animations feel stiff or generic, when building interactive components (sliders, drag, expand/collapse), or when UI needs to look hand-crafted rather than AI-generated. Complements frontend-ui-engineering.
---
```

Secciones:
- **Overview** — la meta-regla que subyace a las 10: cambiar adjetivos por
  números ("smooth" no es un valor; `cubic-bezier(...)` a 280ms sí).
- **When to Use** — al añadir animación/motion, micro-interacciones,
  componentes interactivos, o cuando algo "se siente AI".
- **The house easing set** — bloque CSS con las 4 variables:
  ```css
  :root {
    --ease-smooth: cubic-bezier(0.22, 1, 0.36, 1);    /* default */
    --ease-out:    cubic-bezier(0.17, 1, 0.32, 1);    /* entradas decorativas */
    --ease-spring: cubic-bezier(0.35, 1.55, 0.65, 1); /* badges, pops, overshoot */
    --ease-in-out: cubic-bezier(0.66, 0, 0.34, 1);    /* movimientos simétricos */
  }
  ```
- **The 10 rules**, cada una con su snippet:
  1. Easing propio, nunca defaults nativos (`ease`, `ease-in-out`).
  2. Definir design tokens antes de construir ("usa solo estos tokens, sin
     valores one-off").
  3. Draggables con física real: momentum, fricción, resistencia; overscroll
     que estira y rebota en vez de parar en seco.
  4. Snap points magnéticos: dos zonas (pull-in estrecha + release amplia) +
     flash del label al enganchar.
  5. Entradas con blur, nunca solo fade: `opacity 0→1` + `translateY 6px→0`
     + `blur(2px)→0`, ~280ms sobre `--ease-smooth`.
  6. Sombras en capas, no una sola: hairline ring of light en vez de borde;
     opacidad por capa 2–8%; varios blurs apilados de distinto tamaño.
  7. Press response en todo clickable: encoger a **98%** (no 95%, que se
     lee como "colapso" en vez de "presión firme").
  8. Expand/collapse con `grid-template-rows: 0fr → 1fr` (nunca el hack
     `max-height: 9999px`, que da saltos).
  9. Respetar `prefers-reduced-motion`: colapsar a instantáneo, parar loops
     decorativos.
  10. Un componente es un **set de estados**, no una imagen: idle / hover /
      pressed / loading / disabled / success — se descubren usándolo, no
      se especifican completos en Figma de antemano.
- **Prompting patterns** — describir el *feeling*, no la jerga técnica;
  entregar el bloque de tokens primero ("mata el 80% del look AI-slop").
- **Red Flags** — fades planos sin blur, sombra única, press al 95%,
  `max-height:9999px`, curvas de easing nativas del navegador, valores
  fuera de la escala de tokens.
- **Verification checklist** — easing tokenizado y no nativo, entradas con
  blur, press feedback en clickables, `prefers-reduced-motion` honrado,
  estados completos del componente (no solo idle/hover).
- **Cierre** — "el prompt te da el 90%; el 10% final (el taste, las
  micro-decisiones de 2px/98%) es tuyo". Atribución al artículo original y
  link al tweet.

### `references/motion-library.md` — contenido a incluir
- Catálogo de curvas de easing con su intención de uso (default / entradas
  decorativas / overshoot / simétrico) — las mismas 4 del bloque CSS de
  arriba, con explicación ampliada.
- Duraciones sugeridas por intención (press ~120ms, entrada ~280ms, drag
  release variable según velocidad).
- Reglas de asimetría enter/exit (las entradas suelen ser más lentas que
  las salidas).
- Snippets copy-paste: hover lift, staggered reveal, modal entry, shimmer
  loading.
- Bloque completo de `@media (prefers-reduced-motion: reduce)` con el
  patrón de fallback a instantáneo.

**Fuente original completa del artículo** (para no tener que volver a
buscarla): mirror legible en
`https://gu-log.vercel.app/en/posts/en-sp-233-20260617-polished-ui-rules`
(x.com/i/article/... requiere JavaScript y no es fetcheable directamente).

**Próximo paso inmediato:** crear ambos ficheros tal cual el plan de
arriba, luego verificar que OpenCode reconoce la skill nueva (puede
requerir reiniciar OpenCode, ver nota en "Notas de entorno" sobre
`.opencode/skills/` no siendo hot-reload).

---

## Última sesión

**Fecha:** 2026-07-09 · **Sesión 6 (cont.) — Landing rediseñada a pantalla única (D36)**

**Contexto:** tras la Sesión 6 (rediseño visual + landing multi-sección,
D35), el owner pidió cambiar la landing recién creada: **una única pantalla
sin scroll**, con la imagen del cartel de UFC 329 (`imagen landing.jpeg`,
hallazgo pendiente de la sesión anterior) como fondo, **un solo botón
"Avísame"** hacia el registro, y dinamismo visual con partículas/movimiento
de fondo. Se resolvieron 4 decisiones de diseño con el owner antes de tocar
código (ver `decisiones.md` → D36): acceso de usuarios existentes (enlace
"Entrar" discreto), técnica de partículas (**tsparticles vía CDN**, no
CSS-only ni canvas propio), tratamiento de la imagen (fondo full-bleed +
overlay) y optimización (WebP+JPG generados con `ffmpeg`, no el 1MB
original).

**Qué se hizo:**
- **Imágenes**: `ffmpeg` generó `static/img/hero.webp` (161KB) y
  `static/img/hero.jpg` (202KB, fallback) a 1600px desde el JPEG original.
  El fichero suelto `imagen landing.jpeg` de la raíz **se eliminó** (cierra
  el hallazgo pendiente de la sesión anterior).
- **`landing.html` reescrita por completo**: `.hero-screen` a `100svh` con
  `<picture>` de fondo (webp/jpg), overlay degradado + glow rojo, capa
  `#tsparticles`, nav superior mínima (marca + "Entrar" → `/app/login`) y
  contenido central (kicker + h1 + lead + botón `.btn-wake` "Avísame" →
  `/app/register`, con animación de brillo pulsante). Se eliminan las
  secciones de marketing de la landing anterior (cómo funciona, deportes,
  CTA final, footer).
- **tsparticles 2.12.0** por CDN (versión pinneada), init guardado tras
  `prefers-reduced-motion`; partículas tipo chispas rojo/dorado con
  movimiento ascendente y repulsión al hover. Progressive enhancement: sin
  JS o con reduced-motion, la landing es 100% funcional.
- **CSS**: sustituido íntegramente el bloque de landing de D35 por los
  estilos de pantalla única, con salvaguarda `@media (max-height: 560px)`
  que reactiva scroll en móviles apaisados muy bajos.
- **Limpieza**: `reveal.js` y `data-reveal`/`reveal-init` eliminados (dead
  code, solo los usaba la landing anterior).
- **Cerrados los 2 tests rojos heredados** de la sesión anterior:
  `test_root_redirects_to_app` (esperaba 302) reescrito como
  `test_root_serves_landing` (200 + contiene "Avísame") en
  `tests/test_health.py` y `tests/test_api.py`. Se verificó que la
  cobertura de `/app` sin cookie → redirige a `/app/login` sigue intacta.

**Verificación de esta sesión:** `ruff` ✅ · `black` ✅ · `mypy` ✅ ·
`pytest` → **72/72 verdes** (0 rojos, primera vez limpio desde que empezó
la Fase 6) · smoke HTTP manual sobre el `uvicorn --reload` ya corriendo:
`/` 200 con "Avísame" y script de tsparticles, `hero.webp`/`hero.jpg`
sirven con el tamaño esperado, `/app` sin cookie → 303 a `/app/login` (200).

**Pendiente aún (no bloqueante, no se tocó esta sesión):**
- Backend HTMX real en `create_alert`/`delete_alert` (`src/app/web/user.py`)
  — el partial `_alert_cell.html` ya tiene los `hx-*` escritos pero el
  backend no detecta `HX-Request` todavía.
- **Smoke visual real en navegador**: responsive 320/768/1024/1440,
  contraste del texto sobre la imagen, foco de teclado en "Entrar"/"Avísame",
  comportamiento de las partículas en pantallas pequeñas/gama baja.
- Si el cartel destacado cambia de evento en el futuro, regenerar
  `static/img/hero.webp`/`hero.jpg` con el póster nuevo (comandos `ffmpeg`
  documentados en `bitacora.md` → Sesión 6 cont.).

**Detalle completo**: `memoria/fases.md` → "Fase 6 — Rediseño visual +
landing dinámica". Decisiones: `D35`/`D36` en `memoria/decisiones.md`.
Narrativa: `memoria/bitacora.md` → "Sesión 6 (cont.)".

**Servidor:** sigue corriendo un `uvicorn --reload` en local en el puerto
8000 (PID 740, ver `Get-NetTCPConnection -LocalPort 8000`) desde la sesión
anterior, usado para el smoke test de esta sesión. Puede matarse sin
problema al empezar la siguiente.

---

## Estado global

| Fase | Estado |
|------|--------|
| Fase 0 — Providers ESPN + tests | **Completada** ✅ |
| Fase 1 — Scaffold | **Completada** ✅ |
| Fase 2a — EstimatorEngine puro | **Completada** ✅ |
| Fase 2b — Poller + idempotencia | **Completada** ✅ |
| Fase 3 — Multiusuario + admin web | **Completada** ✅ |
| Fase MVP-launch — fotos + Twilio + scheduler + Railway | **Código listo** ✅ (deploy pendiente) |
| Fase 4 — Boxeo/Tenis reales | Pendiente (fuera del MVP) |
| Fase 5 — VoiceNotifier real (Twilio) | **Completada** ✅ (falta cuenta Twilio para llamada real) |
| Fase 6 — Rediseño visual + landing dinámica (D35/D36) | 🔶 **En curso** — landing de pantalla única lista y verificada (tests + smoke HTTP); falta HTMX real, smoke visual en navegador |

Detalle de checkboxes en `fases.md`.

---

## Próximos pasos

**Inmediato (cerrar Fase 6):**

1. **Completar HTMX real**: en `src/app/web/user.py`, los endpoints
   `create_alert` y `delete_alert` deben detectar `request.headers.get("HX-Request")`
   y devolver `partials/_alert_cell.html` en vez del `RedirectResponse` 303,
   para que crear/cancelar una alerta no recargue la página.
2. **Smoke visual en navegador real**: abrir `http://localhost:8000/` y
   recorrer landing (pantalla única, sin scroll salvo pantallas muy bajas) →
   registro → dashboard → evento con fotos. Revisar responsive en
   320/768/1024/1440, contraste de color del texto sobre la imagen,
   navegación por teclado (Tab en "Entrar"/"Avísame"), y que las partículas
   no sobrecarguen dispositivos de gama baja.
3. Actualizar `memoria/handoff.md` de nuevo al cerrar esta fase.

**Después de cerrar Fase 6:**

4. **Deploy en Railway** (requiere cuenta del owner) — ver checklist detallado
   más abajo, sin cambios respecto a la Sesión 5.
5. **Cuenta Twilio**: set env-vars cuando el owner la tenga.
6. **Seguridad**: rotar el token GitHub embebido en el remote del clon local.
7. (Opcional) Cadencia adaptativa D15 en el scheduler; CI GitHub Actions.
8. Si el cartel destacado cambia de evento, regenerar `static/img/hero.*`.

---

## Cómo levantar la web en local

```powershell
.\.venv\Scripts\Activate.ps1
# .env: DATABASE_URL=sqlite+aiosqlite:///./avisador.db (append tras copiar .env.example)
alembic upgrade head          # crea las tablas en avisador.db
uvicorn app.main:app --reload
```

**Landing pública (D35/D36, pantalla única):**
- `http://localhost:8000/` → landing de pantalla única (imagen del cartel de
  fondo + partículas + botón "Avísame"). Ya no redirige a `/app`; se muestra
  siempre, incluso con sesión activa.

**Usuario (vista funcional):**
- `http://localhost:8000/app/login` / `/app/register` → auth de usuario
- `http://localhost:8000/app` → dashboard (requiere cookie de sesión)
- `http://localhost:8000/app/events/{event_id}` → tarjeta con fotos y nombres + crear alerta

**Admin:**
- `http://localhost:8000/admin/login` (seed: `python scripts/seed_admin.py`)
- `http://localhost:8000/admin/users/{id}` → detalle de usuario
- `http://localhost:8000/docs` → Swagger UI

---

## Notas de entorno

- **Python**: el `python` del PATH es 3.11; usar `py -3.12`. venv en `.venv`.
- **Redis local**: no es necesario para la web (la caché de atletas degrada a
  memoria); sí para idempotencia del Poller en producción.
- **Scheduler**: arranca con la app; en local sin Redis el poll loguea errores
  benignos si hay suscripciones activas. `SCHEDULER_ENABLED=false` para apagarlo.
- **Tip (PowerShell)**: usar `python -m pip` en vez de `pip`.
- **Hooks git**: activar una vez con `pwsh scripts/setup-hooks.ps1`.
- **Assets estáticos**: `src/app/web/static/{css,fonts,img}/`, montados en
  `/static` vía `StaticFiles`. Sin build step — CSS puro, sin bundler ni
  `package.json`. `fonts/inter-var-latin.woff2` es la tipografía Inter
  Variable auto-hospedada (D35); `img/hero.webp`+`hero.jpg` son el póster de
  fondo de la landing (regenerar con `ffmpeg` si cambia el evento destacado).
- **tsparticles**: única dependencia por CDN del proyecto (versión pinneada
  `2.12.0` en jsdelivr) — rompe puntualmente el principio "sin CDN" de D35
  (que solo cubría fuentes), aceptado como progressive enhancement (D36).
- **Skills de agente**: `.opencode/skills/` contiene el subset frontend de
  `addyosmani/agent-skills`. Si esta sesión no las ve activas, reinicia
  OpenCode (el config no es hot-reload).

---

## Comandos quick-start

```powershell
.\.venv\Scripts\Activate.ps1        # activar venv
alembic upgrade head                # aplicar migraciones (SQLite)
uvicorn app.main:app --reload        # servidor dev (API + web + scheduler)
pytest -v                            # tests (72/72 verdes)
python scripts/probe_espn.py          # smoke ESPN en vivo
ruff check src tests                  # lint
black --check src tests scripts       # formato
mypy src/app                          # type check
python scripts/gen_memoria_index.py   # regenerar índice en AGENTS.md
```

