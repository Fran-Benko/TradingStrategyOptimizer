# CI Pipeline Skill

## Descripción

Configura y automatiza pipelines de CI/CD usando GitHub Actions. Genera workflows completos con linting, testing, building y deployment.

## Activación

```
Configura CI
Agrega job al pipeline
```

## Templates

### Pipeline completo

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

env:
  PYTHON_VERSION: '3.11'

jobs:
  lint:
    name: Lint
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'
      - run: pip install black isort flake8 mypy pylint
      - run: |
          black --check src/ tests/
          isort --check-only src/ tests/
          flake8 src/ tests/

  test:
    name: Test (Python ${{ matrix.python-version }})
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.10', '3.11', '3.12']
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'
      - run: pip install -r requirements.txt
      - run: pytest tests/ --cov=trading_system -v

  build:
    name: Build Container
    runs-on: ubuntu-latest
    needs: [test]
    if: github.ref == 'refs/heads/main'
    steps:
      - uses: actions/checkout@v4
      - run: podman build -t trading-system:${{ github.sha }} -f deployment/Containerfile .
      - run: podman save trading-system:${{ github.sha }} -o trading-system.tar
      - uses: actions/upload-artifact@v4
        with:
          name: container
          path: trading-system.tar
```

### Job de security scan

```yaml
security:
  name: Security Scan
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: pip install safety bandit
    - run: safety check || true
    - run: bandit -r src/ -f json -o bandit-report.json || true
    - uses: actions/upload-artifact@v4
      with:
        name: security-report
        path: bandit-report.json
```

## Comandos

### Agregar workflow

```
ci-pipeline add-workflow nombre:performance-tests
Trigger: [push, schedule]
```

### Actualizar cache

```
ci-pipeline update-cache
Dependencias: pip, apt
```

---

**Versión**: 1.0.0  
**Última actualización**: 2026-03-19
