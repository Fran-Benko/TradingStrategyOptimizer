# Testing Pipeline Workflow

## Descripción

Workflow para ejecutar la suite completa de testing antes de merge o deployment.

## Pipeline de Testing

```
┌─────────────┐
│   Lint      │  ← black, isort, flake8, mypy
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Unit      │  ← pytest unit/
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Integration │  ← pytest integration/
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Performance │  ← pytest performance/
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Security   │  ← bandit, safety
└─────────────┘
```

## Ejecución

### Local

```bash
# Full pipeline
make test

# Individual stages
make lint
make test-unit
make test-integration
make test-performance
make security-scan
```

### CI/CD

```bash
# El pipeline se ejecuta automáticamente en:
# - push a main/develop
# - pull requests
# - workflow_dispatch
```

## Comandos de Testing

### Unit Tests

```bash
pytest tests/unit/ \
    --cov=trading_system \
    --cov-report=term-missing \
    --cov-report=html \
    -v \
    --tb=short
```

### Integration Tests

```bash
USE_MOCK_DATA=true pytest tests/integration/ \
    -v \
    --tb=short \
    --maxfail=1
```

### Performance Tests

```bash
pytest tests/performance/ \
    --benchmark-only \
    --benchmark-json=benchmark.json \
    -v
```

### Security Scan

```bash
# Bandit
bandit -r src/ -f json -o bandit-report.json

# Safety
safety check --json > safety-report.json
```

## Métricas de Calidad

| Metric | Target | Blocker |
|--------|--------|--------|
| Coverage | ≥ 80% | No (warning) |
| Tests Passing | 100% | Yes |
| Flaky Tests | 0% | Yes |
| Lint Errors | 0 | Yes |
| Security Issues | 0 (High/Critical) | Yes |

## Integración con Agentes

| Stage | Agente |
|-------|--------|
| Lint | @CIConfigurer |
| Unit | @UnitTestEngineer |
| Integration | @IntegrationTestEngineer |
| Performance | @PerformanceTester |
| Security | @SecurityAuditor |

---

**Última actualización**: 2026-03-19
