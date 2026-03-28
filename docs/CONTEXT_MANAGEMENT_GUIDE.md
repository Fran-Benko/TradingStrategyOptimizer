# Guía de Gestión de Contexto con OpenCode

Esta guía explica cómo usar el sistema de gestión de contexto de OpenCode para mantener el conocimiento del proyecto actualizado y accesible.

## 📚 ¿Qué es el Sistema de Contexto?

El sistema de contexto de OpenCode permite:
- **Extraer conocimiento** de sesiones de desarrollo
- **Organizar información** por función (concepts, examples, guides, lookup, errors)
- **Mantener archivos pequeños** (<200 líneas - MVI: Minimal Viable Information)
- **Actualizar automáticamente** cuando cambian APIs o frameworks

## 🎯 Principios Clave

### 1. MVI (Minimal Viable Information)
- **Core concept**: 1-3 oraciones
- **Key points**: 3-5 bullets
- **Minimal example**: <10 líneas
- **Reference link**: a documentación completa
- **File size**: <200 líneas

### 2. Organización Function-Based
```
.opencode/context/{category}/
├── navigation.md       # Índice de navegación
├── concepts/          # Qué es (definiciones, conceptos)
├── examples/          # Código funcional
├── guides/            # Cómo hacer (paso a paso)
├── lookup/            # Referencia rápida (comandos, APIs)
├── errors/            # Problemas comunes y soluciones
└── standards/         # Estándares y patrones
```

## 🔄 Operaciones de Contexto

### `/context harvest` - Cosechar Conocimiento

**Cuándo usar**: Después de cada sesión de desarrollo

**Qué hace**:
1. Escanea archivos temporales (OVERVIEW.md, SESSION-*.md, SUMMARY.md)
2. Extrae conocimiento valioso
3. Categoriza por función
4. Muestra preview para aprobación
5. Guarda en contexto permanente
6. Limpia archivos temporales

**Ejemplo**:
```bash
# Escanear todo el workspace
/context harvest

# Escanear directorio específico
/context harvest .tmp/

# Escanear archivo específico
/context harvest SESSION-2026-03-19.md
```

**Output esperado**:
```
Found 2 summary documents:

### SESSION-auth-work.md (1.8 KB)

✓ [A] Error: JWT token expiration not handled
    → Would add to: development/errors/auth-errors.md
    Preview: "Symptom: 401 after 1 hour. Cause: No refresh flow..."

✓ [B] Example: JWT refresh token implementation
    → Would create: development/examples/jwt-refresh.md
    Preview: "Store refresh token → Check expiry → Request new..."

Select items (A B or 'all'): all

✅ Harvested 2 items into permanent context
🗑️ Archived: SESSION-auth-work.md
```

### `/context extract` - Extraer desde Documentación

**Cuándo usar**: Al integrar nueva librería o framework

**Qué hace**:
1. Lee documentación externa (URLs, archivos)
2. Extrae información relevante
3. Aplica MVI para minimizar
4. Categoriza por función
5. Crea archivos de contexto

**Ejemplo**:
```bash
# Extraer desde URL
/context extract from https://www.backtrader.com/docu/

# Extraer desde archivo local
/context extract from docs/api.md

# Extraer desde directorio
/context extract from docs/architecture/
```

**Uso en el proyecto**:
```bash
# Extraer docs de backtrader
/context extract from https://www.backtrader.com/docu/

# Extraer docs de yfinance
/context extract from https://pypi.org/project/yfinance/

# Extraer docs de alpaca-py
/context extract from https://alpaca.markets/docs/python-sdk/
```

### `/context update` - Actualizar Contexto

**Cuándo usar**: Cuando cambian APIs, frameworks o librerías

**Qué hace**:
1. Identifica archivos afectados
2. Muestra diff de cambios propuestos
3. Solicita aprobación
4. Actualiza referencias
5. Agrega notas de migración

**Ejemplo**:
```bash
# Actualizar para nueva versión
/context update for backtrader 2.0

# Actualizar para cambios de API
/context update for Alpaca API v2024

# Actualizar framework
/context update for Python 3.12
```

**Output esperado**:
```
Found 5 files referencing backtrader:

Proposed updates:

━━━ concepts/backtesting.md ━━━
Line 15:
  - Backtrader 1.9 uses Strategy class
  + Backtrader 2.0 introduces AsyncStrategy class

Approve changes? (yes/no/edit): yes

✅ Updated 5 files
📝 Added migration notes to errors/backtrader-migration.md
```

### `/context organize` - Reorganizar Contexto

**Cuándo usar**: Cuando el contexto está desorganizado

**Qué hace**:
1. Analiza estructura actual
2. Identifica archivos mal ubicados
3. Propone reorganización
4. Mueve archivos a ubicaciones correctas
5. Actualiza referencias

**Ejemplo**:
```bash
# Organizar categoría específica
/context organize trading/

# Dry run (ver qué haría sin ejecutar)
/context organize trading/ --dry-run
```

## 📋 Workflow Recomendado

### Durante el Desarrollo

1. **Trabaja normalmente** con los agentes
2. Los agentes crean archivos temporales (SUMMARY.md, etc.)
3. **Al final de la sesión**, ejecuta:
   ```bash
   /context harvest
   ```

### Al Integrar Nueva Librería

1. **Extrae documentación**:
   ```bash
   /context extract from https://library-docs.com
   ```

2. **Revisa y aprueba** el contexto extraído

3. **Los agentes ahora tienen acceso** a esta información

### Cuando Actualizas Dependencias

1. **Actualiza el contexto**:
   ```bash
   /context update for library-name 2.0
   ```

2. **Revisa cambios** propuestos

3. **Aprueba** actualizaciones

## 🎯 Casos de Uso Específicos

### Caso 1: Nueva Estrategia de Trading

```bash
# 1. Trabajas con StrategyDesigner
@StrategyDesigner crea estrategia RSI Momentum

# 2. Al final, cosechas conocimiento
/context harvest

# 3. El conocimiento se guarda en:
# - trading/examples/rsi-momentum-example.md
# - trading/guides/creating-rsi-strategy.md
```

### Caso 2: Integrar Nueva Fuente de Datos

```bash
# 1. Extraes docs de la API
/context extract from https://new-data-api.com/docs

# 2. DataEngineer implementa
@DataEngineer implementa fetcher para NewDataAPI

# 3. Cosechas conocimiento
/context harvest

# 4. Resultado:
# - trading/standards/market-data-integration.md (actualizado)
# - trading/examples/new-data-api-example.md (nuevo)
```

### Caso 3: Actualizar Backtrader

```bash
# 1. Actualizas requirements.txt
backtrader==2.0.0

# 2. Actualizas contexto
/context update for backtrader 2.0

# 3. Revisas cambios
# 4. Los agentes ahora usan la nueva versión
```

## 🔍 Navegación de Contexto

### Encontrar Contexto Relevante

Cada categoría tiene un `navigation.md`:

```bash
# Ver índice de trading
cat .opencode/context/trading/navigation.md

# Ver índice de development
cat .opencode/context/development/navigation.md
```

### Estructura de Navigation.md

```markdown
## Quick Access

### Standards (Critical - Load First)
| File | Purpose | When to Load |
|------|---------|--------------|
| trading-patterns.md | Strategy patterns | Designing strategies |
| risk-management.md | Risk principles | All trading tasks |

### Concepts
| File | Purpose |
|------|---------|
| strategy-types.md | Types of strategies |

### Examples
| File | Purpose |
|------|---------|
| momentum-example.md | Momentum strategy |
```

## 🎓 Best Practices

### ✅ DO

- **Harvest después de cada sesión** importante
- **Extract al integrar** nuevas librerías
- **Update cuando cambien** APIs
- **Mantener archivos <200 líneas**
- **Usar categorías correctas**
- **Aprobar cambios** antes de aplicar

### ❌ DON'T

- No dejar archivos temporales sin cosechar
- No crear archivos de contexto manualmente (usa `/context`)
- No ignorar warnings de tamaño de archivo
- No mezclar conceptos en un solo archivo
- No duplicar información entre archivos

## 📊 Monitoreo de Contexto

### Ver Estado del Contexto

```bash
# Ver estructura
/context map

# Ver estructura de categoría específica
/context map trading/

# Validar integridad
/context validate
```

### Métricas de Calidad

El sistema verifica:
- ✅ Archivos <200 líneas
- ✅ Estructura function-based
- ✅ Referencias válidas
- ✅ No duplicación
- ✅ Navegación actualizada

## 🔧 Troubleshooting

### Problema: Archivo muy grande

```bash
# Error: File exceeds 200 lines

# Solución: Dividir en múltiples archivos
/context organize {category}/
```

### Problema: Contexto desactualizado

```bash
# Solución: Actualizar
/context update for {topic}
```

### Problema: No encuentro contexto

```bash
# Solución: Ver navegación
cat .opencode/context/{category}/navigation.md

# O buscar
grep -r "keyword" .opencode/context/
```

## 📚 Recursos

- **Sistema de contexto**: `.opencode/context/core/context-system/`
- **Operaciones**: `.opencode/context/core/context-system/operations/`
- **Estándares**: `.opencode/context/core/context-system/standards/`
- **Guías**: `.opencode/context/core/context-system/guides/`

## 🎯 Próximos Pasos

1. **Familiarízate** con `/context harvest`
2. **Practica** extrayendo docs externas
3. **Mantén** el contexto actualizado
4. **Revisa** navigation.md regularmente
5. **Comparte** conocimiento con el equipo

---

**Recuerda**: El contexto es el "cerebro" del sistema. Mantenlo actualizado y los agentes trabajarán mejor.

**Versión**: 1.0.0  
**Última actualización**: 2026-03-19