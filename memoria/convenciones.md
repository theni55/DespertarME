# Convenciones del proyecto

> Reglas de código, commits, testing y estilo que todo continuador debe respetar.

- **Idioma**: código e identificadores en inglés; comentarios y docs en español.
- **Commits**: conventional commits (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`).
- **No subir secrets**: `.env` nunca se commitea; solo `.env.example`.
- **Testing**: todo provider/notifier/engine tiene tests; la web admin se puede
  cubrir más adelante.
- **Async-first**: todas las I/O (httpx, BD, redis) deben ser async.
- **Type hints**: obligatorios en todo el código nuevo.
- **Lint**: ruff + black. CI debe pasar antes de mergear.
- **No comentarios** en código salvo que expliquen "por qué" no-trivial.

## Antes de cada commit

```powershell
ruff check src tests
black --check src tests
pytest
```

## Rama y PR

- Ramas de trabajo salen de `main` con prefijo (`feature/`, `fix/`, `docs/`).
- Rama activa de integración: `dev`.
- Colaboración vía PR sobre `theni55/DespertarME` (repo compartido, no fork).
