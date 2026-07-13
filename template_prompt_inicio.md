# Prompt inicial — Setup de proyecto con memoria viva + hooks

> Plantilla reutilizable para arrancar cualquier proyecto nuevo con la
> metodología de "memoria viva modular" (continuidad entre sesiones y entre
> LLMs distintos). Copia el bloque de código de abajo, rellena el Bloque 1
> con los datos del proyecto concreto, y pásalo como primer mensaje a tu LLM.

---

## Uso

1. Copia el bloque de código de más abajo (el que está entre las vallas ```` ``` ````).
2. Rellena el **BLOQUE 1 — DATOS DEL PROYECTO** con la información concreta.
3. Pásalo como **primer mensaje** a tu LLM (Claude, GPT, etc.) en el directorio
   vacío del proyecto nuevo (o en uno ya inicializado con `git init`).
4. El LLM montará `memoria/`, `AGENTS.md`, hooks y scripts **antes** de tocar
   código de la aplicación.
5. Al finalizar el setup, pasa `pwsh scripts/setup-hooks.ps1` (Win) o
   `bash scripts/setup-hooks.sh` (Unix) para activar los hooks, haz un commit
   de prueba y arranca la Fase 1 (scaffold del stack).

## Adaptabilidad

- El script `gen_memoria_index.py` es Python stdlib (sin deps) y funciona en
  cualquier proyecto, aunque la app no sea Python. Si prefieres, reescríbelo en
  Node/Bash según el stack.
- Solo se indexa `memoria/*.md` (no `README.md`, ni código).
- Si el proyecto no usa git puedes omitir los hooks, pero pierdes la defensa
  automática de "no commitear código sin actualizar handoff".

---

## Prompt para Copiar

```
Vas a inicializar un proyecto de software nuevo siguiendo una metodología de
"memoria viva modular" pensada para continuidad entre sesiones y entre LLMs
distintos. Ejecuta los pasos en orden. NO escribas código de la aplicación
todavía: primero monta la documentación, los hooks y la estructura base.

====================================================================
BLOQUE 1 — DATOS DEL PROYECTO (rellenar antes de pasar el prompt)
====================================================================

- Nombre del proyecto: <NOMBRE>
- Qué resuelve / caso de uso: <2-4 frases>
- Stack previsto: <lenguaje, framework, BD, etc.>
- Alcance MVP: <bullet list corto>
- Fuera del MVP: <bullet list corto>
- Decisiones de diseño ya tomadas (D1, D2...): <lista o "ninguna">
- Fuentes de datos / APIs previstas: <lista o "a investigar">

====================================================================
BLOQUE 2 — ENTREGABLES OBLIGATORIOS
====================================================================

Crea EXACTAMENTE esta estructura (fiel a la metodología, adaptable al stack):

.
├─ README.md                      # solo el QUÉ y el POR QUÉ (máx ~50 líneas)
├─ AGENTS.md                      # chuleta ejecutable: comandos + índice de memoria/
├─ memoria/
│  ├─ handoff.md                  # punto de entrada de cada sesión
│  ├─ contexto.md                 # visión del producto y alcance
│  ├─ arquitectura.md             # snapshot del diseño (componentes, flujo, entidades, stack)
│  ├─ decisiones.md               # registro histórico D1..Dn + pendientes
│  ├─ fases.md                    # roadmap con checkboxes
│  ├─ convenciones.md             # reglas de código, commits, testing, estilo
│  ├─ bitacora.md                 # registro cronológico de sesiones
│  └─ <extras>                    # ej. fuentes-datos.md si aplica
├─ scripts/
│  └─ gen_memoria_index.py        # regenera el índice de memoria/ en AGENTS.md
├─ .githooks/
│  └─ pre-commit                  # regenera índice + avisa si cambiaste src sin tocar handoff
└─ scripts/setup-hooks.(ps1|sh)   # activa los hooks (una vez por clon)

REGLAS DE CADA FICHERO:

- memoria/*.md empieza con `# Título` + línea `> descripción` (la usa el generador).
- handoff.md: "Última sesión", "Estado global" (tabla fases), "Próximo paso",
  "Notas de entorno", "Comandos quick-start". Actualízalo al final de CADA sesión.
- decisiones.md: tabla histórico (D#, Decisión, Fecha, Justificación). NO editar
  las históricas; para cambiar una, añade D{n+1} con justificación que la sustituye.
- fases.md: roadmap con checkboxes `- [ ]`. Marca sub-items al completarlos.
- bitacora.md: entrada por sesión (fecha, qué se hizo, qué quedó pendiente).
- AGENTS.md: prerequisitos, setup inicial, tabla de comandos frecuentes, endpoints,
  estructura de carpetas, y un bloque <!-- MEMORIA-INDEX:START -->...<!-- ...END -->
  que el script rellenará automáticamente con la tabla de documentos de memoria/.

====================================================================
BLOQUE 3 — GENERADOR DE ÍNDICE (scripts/gen_memoria_index.py)
====================================================================

Script Python estándar (sin deps externas, stdlib solo) que:
1. Lee todos los memoria/*.md.
2. Extrae el `# Título` y la línea `> descripción` de cada uno.
3. Genera una tabla markdown y la inyecta en AGENTS.md entre los marcadores
   <!-- MEMORIA-INDEX:START --> y <!-- MEMORIA-INDEX:END -->.
4. Soporta flag `--check` (exit ≠ 0 si el índice está desactualizado) para CI/hooks.

====================================================================
BLOQUE 4 — HOOK pre-commit (.githooks/pre-commit)
====================================================================

Hook git que al commitear:
1. Regenera el índice de memoria/ en AGENTS.md con scripts/gen_memoria_index.py.
2. Re-stagea AGENTS.md si cambió.
3. Si detecta cambios significativos en <carpetas claves: src/, app/, alembic/,
   pyproject.toml, package.json, docker-compose.yml...> SIN que memoria/handoff.md
   se haya tocado en el mismo commit → ABORTA el commit con un aviso explicativo.
4. Se salta el aviso puntualmente con `git commit --no-verify`.

====================================================================
BLOQUE 5 — REGLAS DE TRABAJO PARA EL LLM / CONTINUADOR
====================================================================

Al empezar cada sesión, leer en este orden:
1. memoria/handoff.md  → saber dónde se quedó y qué sigue.
2. README.md           → contexto (qué + por qué).
3. memoria/ módulos relevantes según la tarea.

Durante el trabajo:
- No modifiques decisiones de decisiones.md (D1..Dn).
- Marca checkboxes en fases.md al completar sub-items.
- Añade entrada en bitacora.md al final de la sesión.
- Actualiza handoff.md con el nuevo estado.
- Código en inglés; docs y comentarios en español (o idioma del proyecto).
- Type hints obligatorios (si el lenguaje lo soporta).
- Antes de commitear pasa lint + format + tests.
- Si requisitos externos faltan (red, BD, API), pregunta antes de inventar.

====================================================================
BLOQUE 6 — VERIFICACIÓN FINAL DEL SETUP
====================================================================

Antes de dar el setup por terminado, verifica:
- `python scripts/gen_memoria_index.py` corre sin error y el índice cuadra.
- `python scripts/gen_memoria_index.py --check` sale 0.
- Hook activado: `pwsh scripts/setup-hooks.ps1` (Win) o
  `bash scripts/setup-hooks.sh` (Unix), o `git config core.hooksPath .githooks`.
- Haz un commit de prueba (ej. "chore: inicializa memoria viva + hooks") y
  confirma que el hook regenera el índice sin abortar.

Al finalizar el setup, devuelve: árbol de archivos creados, comandos para
verificar y el siguiente paso sugerido (normalmente Fase 1: scaffold del stack).
```