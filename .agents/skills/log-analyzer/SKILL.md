# Log Analyzer Skill

## Descripción

Analiza logs de la aplicación para identificar errores, patrones y métricas. Útil para debugging y monitoring de producción.

## Activación

```
Analiza logs
Busca errores en logs
```

## Análisis de Logs

### Errores críticos

```bash
# Buscar errores en logs
grep -E "ERROR|CRITICAL|Exception" logs/app.log | tail -50

# Errores por tipo
cat logs/app.log | jq -r 'select(.level=="ERROR") | .message' | sort | uniq -c | sort -rn
```

### Patrones de errores

```python
#!/usr/bin/env python3
"""log-analyzer.py"""

import json
import sys
from collections import Counter, defaultdict
from datetime import datetime

def analyze_logs(log_file: str):
    """Analyze application logs."""
    
    errors = []
    warnings = []
    by_module = Counter()
    by_hour = defaultdict(int)
    
    with open(log_file) as f:
        for line in f:
            try:
                entry = json.loads(line)
                
                level = entry.get("level", "")
                module = entry.get("module", "unknown")
                timestamp = entry.get("timestamp", "")
                
                if level == "ERROR":
                    errors.append(entry)
                elif level == "WARNING":
                    warnings.append(entry)
                
                by_module[module] += 1
                
                if timestamp:
                    hour = timestamp[11:13]  # Extract hour
                    by_hour[hour] += 1
                    
            except json.JSONDecodeError:
                continue
    
    # Report
    print("\n=== Log Analysis Report ===\n")
    
    print(f"Total Errors: {len(errors)}")
    print(f"Total Warnings: {len(warnings)}\n")
    
    print("Top 10 Modules by Activity:")
    for module, count in by_module.most_common(10):
        print(f"  {module}: {count}")
    
    print("\nTop 10 Errors:")
    error_messages = Counter(e.get("message", "") for e in errors)
    for msg, count in error_messages.most_common(10):
        print(f"  [{count}] {msg[:80]}")
    
    print("\nErrors by Hour:")
    for hour in sorted(by_hour.keys()):
        print(f"  {hour}:00 - {by_hour[hour]} entries")

if __name__ == "__main__":
    log_file = sys.argv[1] if len(sys.argv) > 1 else "logs/app.log"
    analyze_logs(log_file)
```

### Metrics extraction

```bash
# Extraer métricas de logs
cat logs/app.log | jq -r 'select(.metric) | "\(.metric) \(.value)"' | \
    awk '{sum[$1]++; if(min[$1]=="" || $2<min[$1]) min[$1]=$2; if(max[$1]=="" || $2>max[$1]) max[$1]=$2} END {for (m in sum) print m": count="sum[m]", min="min[m]", max="max[m]}'
```

## Uso

```
Analiza logs de la última hora
Busca: errores, warnings, performance issues
```

---

**Versión**: 1.0.0  
**Última actualización**: 2026-03-19
