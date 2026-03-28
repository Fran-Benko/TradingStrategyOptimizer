# Code Review Workflow

## Descripción

Workflow estructurado para realizar code reviews efectivos y constructivos.

## Proceso

### 1. Preparación

```
@CodeReviewer prepara review para [branch]
Incluye: files cambiados, diff summary
```

**Checklist del autor:**
- [ ] Tests passing locally
- [ ] Self-review completado
- [ ] Descripción del PR clara
- [ ] Documentación actualizada
- [ ] Breaking changes identificadas

### 2. Revisión Automática

```bash
# Linting
black --check src/
isort --check-only src/
flake8 src/

# Type checking
mypy src/

# Security
bandit -r src/
```

### 3. Revisión Manual

**Áreas de revisión:**

1. **Correctitud**
   - Lógica correcta
   - Edge cases manejados
   - Error handling apropiado

2. **Diseño**
   - API bien diseñada
   - Separación de concerns
   - Reutilización de código

3. **Legibilidad**
   - Código claro
   - Nombres descriptivos
   - Comentarios donde necesario

4. **Testing**
   - Coverage suficiente
   - Casos de prueba completos
   - Mocks apropiados

5. **Seguridad**
   - No hardcoded secrets
   - Input validation
   - SQL injection prevention

### 4. Feedback

**Template de comentarios:**

```markdown
## Comment

**[component/file.py:line]**

**Issue:** Descripción del problema
**Severity:** [Blocking/Warning/Suggestion]
**Suggestion:** Alternativa sugerida

```python
# Código sugerido
```
```

### 5. Aprobación

**Criterios de aprobación:**
- [ ] Todos los comments blocking resueltos
- [ ] Al menos 1 aprobación
- [ ] CI passing
- [ ] Coverage no disminuido
- [ ] No breaking changes sin documentación

## Integración con Agentes

| Etapa | Agente |
|-------|--------|
| Preparación | @CoderAgent |
| Auto-review | @CodeReviewer |
| Security | @SecurityAuditor |
| Performance | @PerformanceTester |
| Aprobación | @CodeReviewer |

---

**Última actualización**: 2026-03-19
