# Feature Development Workflow

## Descripción

Workflow completo para desarrollar una nueva feature desde la concepción hasta el merge.

## Pasos

### 1. Planning

```
@TradingArchitect diseña feature de [nombre]
Incluye: arquitectura, dependencias, riesgos
```

**Checklist:**
- [ ] Definir alcance de la feature
- [ ] Identificar componentes necesarios
- [ ] Diseñar interfaz/API
- [ ] Estimar esfuerzo
- [ ] Identificar tests requeridos

### 2. Setup

```bash
# Crear branch
git checkout -b feature/[nombre]

# Instalar dependencias
pip install -r requirements.txt

# Setup pre-commit
pre-commit install
```

### 3. Implementación

```
@StrategyDesigner implementa [componente]
Con: tests, documentation
```

**Patrón de commits:**
```
feat: add RSI momentum strategy
fix: handle missing data in fetcher
refactor: extract base strategy class
test: add unit tests for indicators
docs: update strategy documentation
```

### 4. Testing

```
@UnitTestEngineer genera tests para [módulo]
@IntegrationTestEngineer genera integration tests
@PerformanceTester benchmark [componente]
```

### 5. Code Review

```
@CodeReviewer revisa feature/[nombre]
@SecurityAuditor audita cambios
```

**Checklist de PR:**
- [ ] Tests passing
- [ ] Coverage ≥ 80%
- [ ] Linting passing
- [ ] Documentación actualizada
- [ ] Changelog actualizado

### 6. Merge

```bash
# Rebase on main
git rebase main

# Squash commits si necesario
git rebase -i main

# Push y crear PR
git push origin feature/[nombre]
gh pr create
```

## Integración con Agentes

| Paso | Agente Principal | Agentes de Soporte |
|------|-----------------|-------------------|
| Planning | @TradingArchitect | @StrategyDesigner |
| Setup | @PythonDeveloper | - |
| Implement | @StrategyDesigner | @PythonDeveloper |
| Testing | @UnitTestEngineer | @PerformanceTester |
| Review | @CodeReviewer | @SecurityAuditor |
| Merge | @TradingArchitect | - |

---

**Última actualización**: 2026-03-19
