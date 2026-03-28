# Context Harvester Skill

## Descripción

Extrae conocimiento de sesiones de desarrollo y lo convierte en contexto permanente. Captura decisiones arquitectónicas, patrones descubiertos y aprendizajes para futuras sesiones.

## Activación

```
Harvest conocimiento
Extrae contexto de sesión
```

## Uso

### Harvest de sesión actual

```bash
# Usar el comando /context de OpenCode
/context harvest

# Con filtro
/context harvest --pattern "*.py" --since "1 week ago"

# Especificar categoría
/context harvest --category "architecture" --pattern "src/**/*.py"
```

### Extracción de patrones

```bash
# Extraer patrones de código
/context extract-patterns --language python --directory src/

# Output: lista de patrones encontrados
# - Strategy Pattern en strategies/
# - Factory Pattern en data/fetchers/
# - Observer Pattern en events/
```

### Actualización de documentación

```bash
# Actualizar contexto con nueva información
/context update --file docs/trading-patterns.md --from-session 2024-03-19

# Merge con contexto existente
/context merge --source session-notes/ --target .opencode/context/
```

## Templates de Contexto

### Decision Log Entry

```markdown
---
date: 2024-03-19
author: agent
type: architecture-decision
---

## ADR-001: Uso de Protocol para Data Fetchers

### Decisión
Usar `Protocol` de Python para definir interfaces de fetchers en lugar de ABC.

### Contexto
Necesitamos flexibilidad para agregar nuevos sources de datos sin modificar código existente.

### Alternativas consideradas
1. ABC con clases abstractas
2.鸭子类型 simple
3. Protocol (elegida)

### Consecuencias
- Positivas: Flexibilidad, type safety, sin herencia forzada
- Negativas: Requiere Python 3.8+

### Tags
#architecture #data #pattern
```

### Pattern Entry

```markdown
---
date: 2024-03-19
type: code-pattern
tags: [strategy, data-fetching]
---

## Yahoo Finance Data Fetcher Pattern

### Descripción
Patrón para implementar fetchers de datos siguiendo la arquitectura del proyecto.

### Estructura
```python
class BaseDataFetcher:
    def __init__(self, cache=None, rate_limiter=None):
        self.cache = cache
        self.rate_limiter = rate_limiter
    
    def fetch(self, symbol, start, end):
        # Template method
        cache_key = self._get_cache_key(symbol, start, end)
        if cached := self.cache.get(cache_key):
            return cached
        data = self._fetch_from_api(symbol, start, end)
        self.cache.set(cache_key, data)
        return data
    
    @abstractmethod
    def _fetch_from_api(self, symbol, start, end):
        pass
```

### Tags
#data-fetcher #template-method #cache
```

## Automatización

### Git hook para harvest

```bash
#!/bin/bash
# .git/hooks/post-commit

# Harvest después de cada commit
if [ -f .context.harvest ]; then
    /context harvest --output .opencode/context/sessions/$(date +%Y%m%d-%H%M%S).md
fi
```

### Scheduled harvest

```yaml
# .github/workflows/context-harvest.yml
name: Context Harvest

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly
  workflow_dispatch:

jobs:
  harvest:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Harvest context
        run: /context harvest --output context/sessions/
      - name: Create PR
        uses: peter-evans/create-pull-request@v5
        with:
          title: "chore: harvest session context"
          branch: chore/context-harvest
```

## Categorías de Contexto

| Categoría | Descripción | Destino |
|-----------|-------------|---------|
| architecture | Decisiones de arquitectura | `.opencode/context/architecture/` |
| pattern | Patrones de código | `.opencode/context/patterns/` |
| troubleshooting | Problemas y soluciones | `.opencode/context/troubleshooting/` |
| api | Diseño de APIs | `.opencode/context/api/` |
| performance | Optimizaciones | `.opencode/context/performance/` |

---

**Versión**: 1.0.0  
**Última actualización**: 2026-03-19
