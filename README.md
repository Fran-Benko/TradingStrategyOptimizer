# Trading System - Agentic Development Environment

Sistema de trading algorítmico desarrollado con OpenCode usando un entorno agéntico completo.

## 🎯 Descripción

Este proyecto implementa un sistema de trading algorítmico con:
- **Optimización de estrategias** (momentum, mean reversion, arbitrage, ML-based)
- **Backtesting** con backtrader
- **Múltiples fuentes de datos** (Yahoo Finance, Alpaca, Google Finance)
- **Métricas avanzadas** (Sharpe ratio, drawdown, win rate, profit factor)
- **Deployment** con Podman
- **Gestión de contexto automática** usando OpenCode

## 📁 Estructura del Proyecto

```
skillsTest/
├── .opencode/                    # OpenCode configuration
│   ├── agent/                    # Agentes especializados
│   │   └── trading/              # Agentes de trading
│   │       ├── trading-architect.md      # Arquitecto principal
│   │       ├── data-engineer.md          # Ingeniero de datos
│   │       ├── strategy-designer.md      # Diseñador de estrategias
│   │       └── metrics-analyst.md        # Analista de métricas
│   ├── context/                  # Contexto de conocimiento
│   │   └── trading/              # Contexto de trading
│   │       ├── navigation.md     # Navegación de contexto
│   │       └── standards/        # Estándares y patrones
│   │           ├── trading-patterns.md
│   │           └── market-data-integration.md
│   └── workflows/                # Workflows de desarrollo
├── .agents/                      # Skills de OpenCode
│   └── skills/
│       └── data-fetcher/         # Skill de obtención de datos
├── src/                          # Código fuente
│   └── trading_system/
│       ├── data/                 # Módulo de datos
│       ├── strategies/           # Estrategias de trading
│       ├── backtesting/          # Motor de backtesting
│       ├── optimization/         # Optimización de parámetros
│       └── utils/                # Utilidades
├── tests/                        # Tests
├── docs/                         # Documentación
├── config/                       # Configuración
└── deployment/                   # Deployment con Podman
```

## 🤖 Agentes Disponibles

### Agentes Core de Trading

#### TradingArchitect
- **Rol**: Arquitecto principal del sistema
- **Responsabilidades**: Diseño de arquitectura, coordinación de agentes, definición de flujos
- **Uso**: `@TradingArchitect diseña la arquitectura para [feature]`

#### DataEngineer
- **Rol**: Ingeniero de datos de mercado
- **Responsabilidades**: Integración de Yahoo Finance, Alpaca, Google Finance
- **Uso**: `@DataEngineer implementa fetcher para [data source]`

#### StrategyDesigner
- **Rol**: Diseñador de estrategias
- **Responsabilidades**: Diseño e implementación de estrategias de trading
- **Uso**: `@StrategyDesigner crea estrategia de [tipo]`

#### MetricsAnalyst
- **Rol**: Analista de métricas
- **Responsabilidades**: Cálculo de métricas, reportes, dashboards
- **Uso**: `@MetricsAnalyst calcula métricas para [strategy]`

## 🛠️ Skills Disponibles

### data-fetcher
Obtiene datos de mercado de múltiples fuentes con fallback automático.

**Uso**:
```
Fetch historical data for AAPL from 2023-01-01 to 2024-01-01
```

**Características**:
- Multi-source (Yahoo, Alpaca, Google)
- Rate limiting automático
- Caching inteligente
- Validación de datos
- Fallback automático

## 🚀 Inicio Rápido

### 1. Configuración de Entorno

```bash
# Clonar repositorio
git clone <repo-url>
cd skillsTest

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

### 2. Configurar API Keys

Crear archivo `.env`:
```bash
# Alpaca
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
ALPACA_BASE_URL=https://paper-api.alpaca.markets

# Google Finance (si es necesario)
GOOGLE_FINANCE_API_KEY=your_key
```

### 3. Usar OpenCode

#### Opción A: Desde Windows (este sistema)
```powershell
# Los agentes ya están configurados en .opencode/
# Usar directamente con OpenCode
```

#### Opción B: Desde WSL Ubuntu
```bash
# Acceder a WSL
wsl

# Navegar al proyecto
cd /mnt/c/Users/FrancoYairBenko/OneDrive\ -\ IBM/Documents/Desarrollo/OpenCodeDev/skillsTest

# Usar OpenCode desde WSL
opencode [comando]
```

## 📚 Uso del Sistema

### Desarrollar una Nueva Estrategia

```
@TradingArchitect necesito crear una estrategia de momentum basada en RSI

El arquitecto coordinará:
1. @StrategyDesigner para diseñar la estrategia
2. @DataEngineer para obtener datos históricos
3. @MetricsAnalyst para evaluar performance
```

### Obtener Datos de Mercado

```
Fetch historical data for AAPL, GOOGL, MSFT
Date range: 2023-01-01 to 2024-01-01
Interval: 1 day
```

### Ejecutar Backtest

```
@StrategyDesigner ejecuta backtest de la estrategia RSI Momentum
Símbolos: AAPL, MSFT
Período: 2023-01-01 a 2024-01-01
```

### Calcular Métricas

```
@MetricsAnalyst calcula métricas para el backtest anterior
Incluye: Sharpe ratio, max drawdown, win rate, profit factor
```

## 🔄 Sistema de Gestión de Contexto

El sistema usa OpenCode para mantener el conocimiento actualizado:

### Harvest (Cosechar Conocimiento)
```bash
/context harvest
```
Extrae conocimiento de sesiones de desarrollo → contexto permanente

### Extract (Extraer desde Docs)
```bash
/context extract from https://www.backtrader.com/docu/
```
Extrae conocimiento desde documentación externa

### Update (Actualizar)
```bash
/context update for backtrader 2.0
```
Actualiza contexto cuando cambian APIs/frameworks

## 📊 Fuentes de Datos

### Yahoo Finance
- **Mejor para**: Datos históricos, backtesting
- **Límite**: ~2000 requests/hora
- **Gratis**: Sí

### Alpaca
- **Mejor para**: Datos en tiempo real, paper trading
- **Límite**: 200 requests/minuto (tier gratuito)
- **Gratis**: Sí (con limitaciones)

### Google Finance
- **Mejor para**: Fallback, validación
- **Límite**: Conservador
- **Gratis**: Depende

## 🧪 Testing

```bash
# Tests unitarios
pytest tests/unit/

# Tests de integración
pytest tests/integration/

# Tests end-to-end
pytest tests/e2e/

# Tests de performance
pytest tests/performance/
```

## 📈 Métricas Soportadas

- **Returns**: Total return, annualized return, CAGR
- **Risk-adjusted**: Sharpe ratio, Sortino ratio, Calmar ratio
- **Risk**: Max drawdown, VaR, CVaR, volatility
- **Trade stats**: Win rate, profit factor, avg win/loss
- **Consistency**: Consecutive wins/losses, monthly consistency

## 🐳 Deployment

### Con Podman

```bash
# Build
podman build -t trading-system .

# Run
podman run -d \
  --name trading-system \
  -e ALPACA_API_KEY=$ALPACA_API_KEY \
  -e ALPACA_SECRET_KEY=$ALPACA_SECRET_KEY \
  trading-system
```

## 📖 Documentación

- **Agentes**: `.opencode/agent/trading/`
- **Contexto**: `.opencode/context/trading/`
- **Skills**: `.agents/skills/`
- **Docs técnicas**: `docs/`

## 🔧 Desarrollo

### Agregar Nueva Estrategia

1. Usar `@StrategyDesigner` para diseñar
2. Implementar en `src/trading_system/strategies/`
3. Crear tests en `tests/unit/`
4. Ejecutar backtest
5. Documentar en `docs/`

### Agregar Nueva Fuente de Datos

1. Usar `@DataEngineer` para diseñar
2. Implementar `DataFetcher` protocol
3. Agregar a `src/trading_system/data/fetchers/`
4. Actualizar factory
5. Crear tests

## 🤝 Contribuir

1. Fork el proyecto
2. Crear feature branch
3. Usar agentes de OpenCode para desarrollo
4. Ejecutar tests
5. Crear Pull Request

## 📝 Notas

- **Contexto actualizado**: El sistema usa `/context harvest` para mantener conocimiento
- **Agentes coordinados**: TradingArchitect coordina todos los agentes
- **Best practices**: Todos los agentes siguen estándares en `.opencode/context/`
- **WSL ready**: Sistema preparado para desarrollo en WSL Ubuntu

## 🎓 Próximos Pasos

1. ✅ Estructura de directorios creada
2. ✅ Agentes core de trading implementados
3. ✅ Contextos de estándares creados
4. ✅ Skill data-fetcher implementado
5. ⏳ Implementar código Python usando OpenCode en WSL
6. ⏳ Configurar CI/CD
7. ⏳ Deployment con Podman

## 📞 Soporte

Para preguntas o issues, usar los agentes de OpenCode:
- `@TradingArchitect` para arquitectura
- `@DataEngineer` para datos
- `@StrategyDesigner` para estrategias
- `@MetricsAnalyst` para métricas

---

**Versión**: 1.0.0  
**Última actualización**: 2026-03-19  
**Mantenido por**: Trading Team