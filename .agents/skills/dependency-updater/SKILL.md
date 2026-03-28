# Dependency Updater Skill

## Descripción

Gestiona la actualización de dependencias del proyecto. Verifica vulnerabilidades, testa compatibilidad, y automatiza el proceso de actualización de packages.

## Activación

```
Actualiza dependencias
Verifica seguridad de packages
```

## Comandos

### Check de actualizaciones

```bash
# Listar actualizaciones disponibles
pip list --outdated

# Verificar con pip-tools
pip-compile --dry-run requirements.in
```

### Actualización segura

```bash
# 1. Crear branch
git checkout -b chore/update-dependencies

# 2. Actualizar pip
pip install --upgrade pip

# 3. Actualizar requirements.in
# Agregar nueva dependencia o versión

# 4. Recompilar lock file
pip-compile requirements.in

# 5. Instalar y testar
pip install -r requirements.txt
pytest

# 6. Commit y push
git add requirements.txt requirements.in
git commit -m "chore: update dependencies"
```

### Actualización de paquete específico

```bash
# Ver versión actual
pip show pandas
pip install pandas==2.0.0 --dry-run  # Preview
pip install pandas==2.0.0            # Actualizar

# Verificar que todo funciona
pytest
```

## Gestión de requirements.in

```text
# requirements.in

# Core dependencies
pandas>=2.0.0,<3.0.0
numpy>=1.24.0,<2.0.0
pydantic>=2.0.0,<3.0.0
pydantic-settings>=2.0.0,<3.0.0

# Trading libraries
backtrader>=1.9.0,<2.0.0
ta-lib>=0.4.0

# Data fetching
yfinance>=0.2.0,<1.0.0
alpaca-trade-api>=0.50.0,<1.0.0
requests>=2.28.0,<3.0.0

# Testing
pytest>=7.0.0,<8.0.0
pytest-cov>=4.0.0,<5.0.0
pytest-mock>=3.10.0,<4.0.0
pytest-asyncio>=0.21.0,<1.0.0
hypothesis>=6.0.0,<7.0.0

# Development
black>=23.0.0,<24.0.0
isort>=5.12.0,<6.0.0
flake8>=6.0.0,<7.0.0
mypy>=1.0.0,<2.0.0
pylint>=2.17.0,<3.0.0

# DevOps
bandit>=1.7.0,<2.0.0
safety>=2.3.0,<3.0.0
```

## Verificación de Seguridad

```bash
# Scan de vulnerabilidades
safety check

# Con output JSON
safety check --json > security-report.json

# Actualizar si hay vulnerabilidades
safety check --auto-remediation
```

## Política de Actualizaciones

| Tipo | Frecuencia | Requiere |
|------|------------|----------|
| Patch de seguridad | Inmediato | CI passing |
| Minor | Mensual | Tests + Review |
| Major | Trimestral | Tests + Review + Changelog |

## Checklist de Actualización

- [ ] Verificar vulnerabilidades con `safety check`
- [ ] Revisar changelog del paquete
- [ ] Ejecutar tests completos
- [ ] Verificar type hints si cambió API
- [ ] Actualizar documentación si es necesario
- [ ] Crear PR con descripción de cambios
- [ ] Monitorear CI/CD

## Automatización

```yaml
# .github/workflows/dependency-check.yml
name: Dependency Check

on:
  schedule:
    - cron: '0 0 * * 0'  # Weekly
  workflow_dispatch:

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Check for outdated
        run: pip list --outdated
      
      - name: Security scan
        run: safety check || true
      
      - name: Create issue if vulnerable
        if: failure()
        uses: actions/create-issue@v1
        with:
          title: "Dependency Security Alert"
          body: "Security vulnerabilities found in dependencies"
```

## Uso

### Verificar estado de dependencias

```
dependency-updater check-status
Muestra: outdated, vulnerable, breaking changes
```

### Actualizar un paquete

```
dependency-updater update pandas
Con: tests, security check, PR
```

### Generar reporte

```
dependency-updater generate-report
Formato: markdown con changelog
```

---

**Versión**: 1.0.0  
**Última actualización**: 2026-03-19
