---
name: data-pipeline
description: Workflow for fetching, validating, and caching market data
triggers:
  - New data source integration
  - Data quality issues
  - Cache management
  - Backtest data preparation
required_skills:
  - verification-before-completion
---

# Data Pipeline Workflow

## Descripción

Workflow completo para obtener, validar, cachear y gestionar datos de mercado.

## Pasos

### 1. Selección de Fuente de Datos

**Skill requerido:** `brainstorming` (para evaluación de fuentes)

**Fuentes disponibles:**
- Yahoo Finance (gratuito, delayed)
- Alpaca (real-time, requiere API key)
- Google Finance (alternativo)

```
@DataEngineer evalúa fuente de datos
Criterios: disponibilidad, latencia, costo, confiabilidad
```

**Checklist de selección:**
- [ ] Verificar disponibilidad del símbolo
- [ ] Evaluar costos de API
- [ ] Confirmar límites de rate (ver `src/trading_system/data/storage/rate_limiter.py`)
- [ ] Documentar latency expectations

### 2. Fetching de Datos

```
@DataEngineer obtiene datos de [fuente]
Incluye: OHLCV, symbols válidos, date range
```

**Patrón de fetching:**

```python
from trading_system.data.fetchers import YahooFetcher  # o según fuente

# Con Rate Limiter
from trading_system.data.storage.rate_limiter import RateLimiter

limiter = RateLimiter(max_requests=2000, window_seconds=60)
fetcher = YahooFetcher(rate_limiter=limiter)

# Fetch datos
data = fetcher.fetch(
    symbol="AAPL",
    start_date="2023-01-01",
    end_date="2024-01-01",
    interval="1d"
)
```

**Parámetros de fetching:**
| Intervalo | Uso |
|-----------|-----|
| 1m, 5m, 15m, 1h | Day trading / Scalping |
| 1d | Swing trading / Positional |
| 1wk, 1mo | Long-term analysis |

**Rate limits por fuente:**
- Yahoo Finance: 2000 requests/hora (sin auth)
- Alpaca: 240 requests/minuto (con API key)

### 3. Validación de Datos

```
@DataEngineer valida datos
Herramienta: src/trading_system/data/validators/data_validator.py
```

**Validaciones obligatorias:**

```python
from trading_system.data.validators.data_validator import (
    DataValidator,
    DataValidationError
)

validator = DataValidator(
    min_data_points=2,
    quality_threshold=70.0
)

# Validar estructura OHLCV
try:
    validator.validate_ohlcv(data)
    print("✓ OHLCV structure valid")
except DataValidationError as e:
    print(f"✗ Validation errors: {e.errors}")

# Verificar calidad
report = validator.check_data_quality(data)
print(f"Quality Score: {report.quality_score}")

if not report.is_acceptable:
    print(f"⚠ Data quality below threshold: {report.issues}")
```

**Checklist de validación:**
- [ ] Estructura OHLCV correcta
- [ ] Sin missing values críticos
- [ ] Sin duplicados de timestamps
- [ ] OHLC consistency (high ≥ low, etc.)
- [ ] Sin outliers extremos (z-score < 5)
- [ ] Quality score ≥ 70

**Criterios de rechazo:**
- Missing rows > 10%
- Price anomalies > 5%
- Quality score < 70

### 4. Caching

```
@DataEngineer configura cache
Herramienta: src/trading_system/data/storage/cache.py
```

**Configuración de cache:**

```python
from trading_system.data.storage.cache import CacheManager

# Cache manager con persistencia
cache = CacheManager(
    ttl=3600,              # 1 hora TTL
    max_size=1000,         # 1000 entradas
    persist_path="./data/cache"
)

# Generar clave de cache
cache_key = f"yahoo_{symbol}_{interval}_{start}_{end}"

# Intentar obtener de cache
cached_data = cache.get(cache_key)
if cached_data is not None:
    print("✓ Data loaded from cache")
    data = cached_data
else:
    # Fetch y guardar
    data = fetcher.fetch(symbol, start, end, interval)
    cache.set(cache_key, data)
    print("✓ Data cached")
```

**Estrategias de cache:**
| TTL | Uso |
|-----|-----|
| 300 (5 min) | Intraday data |
| 3600 (1 hr) | Daily data |
| 86400 (24 hr) | Historical data |

### 5. Manejo de Errores

**Skill requerido:** `verification-before-completion`

**Tipos de errores y manejo:**

```python
from trading_system.exceptions import (
    DataValidationError,
    DataFetchError,
    RateLimitError
)

def fetch_with_retry(symbol, retries=3, backoff=60):
    """Fetch con reintento exponencial."""
    for attempt in range(retries):
        try:
            data = fetcher.fetch(symbol)
            validator.validate_ohlcv(data)
            return data
        except RateLimitError:
            if attempt < retries - 1:
                sleep(backoff * (2 ** attempt))
            else:
                raise DataFetchError(f"Rate limit exceeded for {symbol}")
        except DataValidationError as e:
            # Intentar fuente alternativa
            data = alt_fetcher.fetch(symbol)
            validator.validate_ohlcv(data)
            return data
```

**Checklist de errores:**
- [ ] Rate limit handling implementado
- [ ] Retry logic con backoff
- [ ] Fallback a fuente alternativa
- [ ] Logging de errores
- [ ] Alertas para errores recurrentes

### 6. Preparación para Backtest

**Ensamblar dataset completo:**

```python
# Combinar múltiples símbolos
symbols = ["AAPL", "MSFT", "GOOGL"]
dataset = {}

for symbol in symbols:
    cache_key = f"yahoo_{symbol}_1d_2020-01-01_2024-01-01"
    data = cache.get(cache_key)
    
    if data is None:
        data = fetcher.fetch(symbol, "2020-01-01", "2024-01-01", "1d")
        cache.set(cache_key, data)
    
    # Validar antes de agregar
    try:
        validator.validate_ohlcv(data)
        dataset[symbol] = data
    except DataValidationError:
        print(f"✗ Skipping {symbol}: validation failed")

# Batch validation
reports = validator.validate_batch(dataset)
for symbol, report in reports.items():
    if report.is_acceptable:
        print(f"✓ {symbol}: quality={report.quality_score}")
    else:
        print(f"✗ {symbol}: issues={report.issues}")
```

**Checklist de preparación:**
- [ ] Todos los símbolos validados
- [ ] Date range consistente
- [ ] Ausencia de survivorship bias
- [ ] Costos de datos documentados

## Integración con Agentes

| Paso | Agente Principal | Agentes de Soporte |
|------|-----------------|-------------------|
| Selección | @DataEngineer | @TradingArchitect |
| Fetching | @DataEngineer | - |
| Validación | @DataEngineer | @MetricsAnalyst |
| Caching | @DataEngineer | - |
| Error Handling | @DataEngineer | @PythonDeveloper |
| Preparación | @DataEngineer | @MetricsAnalyst |

## Módulos de Referencia

- **Rate Limiter:** `src/trading_system/data/storage/rate_limiter.py`
- **Cache Manager:** `src/trading_system/data/storage/cache.py`
- **Validators:** `src/trading_system/data/validators/data_validator.py`
- **Fetchers:** `src/trading_system/data/fetchers/`
- **Exceptions:** `src/trading_system/exceptions.py`

## Comandos Útiles

```bash
# Limpiar cache
python -c "from src.trading_system.data.storage.cache import CacheManager; CacheManager(persist_path='./data/cache').clear()"

# Ver estadísticas de cache
python -c "from src.trading_system.data.storage.cache import CacheManager; print(CacheManager(persist_path='./data/cache').get_stats())"

# Validar dataset
python -c "from src.trading_system.data.validators.data_validator import DataValidator; v = DataValidator(); print(v.validate_ohlcv.__doc__)"
```

---

**Última actualización**: 2026-03-19
