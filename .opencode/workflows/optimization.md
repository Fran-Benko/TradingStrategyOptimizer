# Optimization Workflow

## Descripción

Workflow para optimizar rendimiento de código, queries y algoritmos.

## Proceso

### 1. Identificación

```
@PerformanceTester identifica bottlenecks
En: [módulo o función]
```

**Métricas a revisar:**
- Tiempo de ejecución
- Uso de memoria
- I/O operations
- Database queries

### 2. Medición Baseline

```bash
# Benchmark baseline
pytest tests/performance/ \
    --benchmark-only \
    --benchmark-json=baseline.json

# Memory profiling
python -m memory_profiler src/optimization/target.py
```

### 3. Análisis

```bash
# CPU profiling
python -m cProfile -o profile.stats -s cumtime src/target.py

# Visualizar con snakeviz
snakeviz profile.stats
```

### 4. Optimización

```
@CodeReviewer optimiza [componente]
Con: profiling data, targets
```

**Técnicas comunes:**

| Técnica | Cuándo usar |
|---------|-------------|
| Caching | Resultados costosos reutilizados |
| Batch processing | Múltiples operaciones similares |
| Vectorization | Loops sobre arrays |
| Lazy evaluation | Resultados no necesarios inmediatamente |
| Connection pooling | Múltiples conexiones a DB/API |

### 5. Verificación

```bash
# Comparar con baseline
pytest tests/performance/ \
    --benchmark-compare=baseline.json

# Validar correctness
pytest tests/unit/ -v
```

### 6. Documentación

```markdown
## Optimización: [Nombre]

### Problema
Descripción del bottleneck original.

### Solución
Técnica aplicada y razón.

### Resultados
| Métrica | Antes | Después | Mejora |
|---------|-------|---------|--------|
| Time | 100ms | 20ms | 5x |
| Memory | 50MB | 30MB | 40% |

### Tags
#performance #optimization
```

## Integración con Agentes

| Etapa | Agente |
|-------|--------|
| Identificación | @PerformanceTester |
| Medición | @PerformanceTester |
| Análisis | @PerformanceTester, @CodeReviewer |
| Optimización | @PythonDeveloper |
| Verificación | @UnitTestEngineer, @BacktestValidator |

---

**Última actualización**: 2026-03-19
