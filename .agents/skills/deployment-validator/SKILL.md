# Deployment Validator Skill

## Descripción

Valida despliegues verificando health checks, logs y funcionalidad después de deploy. Automatiza la verificación post-deployment.

## Activación

```
Valida deployment
Check post-deploy
```

## Validaciones

### Health check

```bash
# Endpoint de salud
curl -f http://localhost:8000/health

# Respuesta esperada
{
  "status": "healthy",
  "version": "1.0.0",
  "checks": {
    "database": true,
    "cache": true
  }
}
```

### Smoke tests

```python
#!/usr/bin/env python3
"""deployment-validator.py"""

import requests
import sys
import time

def validate_deployment(base_url: str, expected_version: str) -> bool:
    """Run deployment validations."""
    checks = []
    
    # 1. Health check
    try:
        resp = requests.get(f"{base_url}/health", timeout=5)
        checks.append(("Health endpoint", resp.status_code == 200))
    except Exception as e:
        checks.append(("Health endpoint", False))
    
    # 2. Version check
    try:
        resp = requests.get(f"{base_url}/version", timeout=5)
        data = resp.json()
        checks.append(("Version match", data.get("version") == expected_version))
    except Exception as e:
        checks.append(("Version match", False))
    
    # 3. API functionality
    try:
        resp = requests.get(f"{base_url}/api/v1/symbols", timeout=5)
        checks.append(("API functional", resp.status_code == 200))
    except Exception as e:
        checks.append(("API functional", False))
    
    # Report
    print("\n=== Deployment Validation ===")
    all_passed = True
    for name, passed in checks:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status}: {name}")
        if not passed:
            all_passed = False
    
    return all_passed

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    version = sys.argv[2] if len(sys.argv) > 2 else "latest"
    
    success = validate_deployment(url, version)
    sys.exit(0 if success else 1)
```

## Rollback

```bash
#!/bin/bash
# rollback.sh

set -e

echo "Rolling back deployment..."

# Get previous image
PREVIOUS_IMAGE=$(git rev-parse HEAD~1)

# Stop current
podman stop trading-system || true
podman rm trading-system || true

# Start with previous image
podman run -d \
    --name trading-system \
    --env-file .env \
    trading-system:$PREVIOUS_IMAGE

# Validate
sleep 10
if curl -f http://localhost:8000/health; then
    echo "Rollback successful"
else
    echo "Rollback failed - manual intervention required"
    exit 1
fi
```

## Uso

```
Validates deployment en staging
Con: health check, API test, logs review
```

---

**Versión**: 1.0.0  
**Última actualización**: 2026-03-19
