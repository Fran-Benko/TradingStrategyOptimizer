# Container Builder Skill

## Descripción

Automatiza la construcción y gestión de contenedores Docker/Podman para el sistema de trading. Genera Dockerfiles optimizados y scripts de build.

## Activación

```
Construye container
Optimiza imagen
```

## Uso

### Build de imagen

```bash
# Build con Podman
podman build -t trading-system:latest -f deployment/Containerfile .

# Build con tags
podman build -t trading-system:latest \
             -t trading-system:1.0.0 \
             -t trading-system:v1.0.0-$(git rev-parse --short HEAD) \
             -f deployment/Containerfile .

# Build sin cache
podman build --no-cache -t trading-system:latest -f deployment/Containerfile .
```

### Multi-platform build

```bash
# Build para múltiples plataformas
podman build --platform linux/amd64,linux/arm64 \
    -t trading-system:latest \
    -f deployment/Containerfile .
```

### Script de build automation

```bash
#!/bin/bash
# scripts/build-container.sh

set -e

VERSION=${1:-latest}
REGISTRY=${2:-ghcr.io/trading-team}

echo "Building trading-system:${VERSION}"

# Build
podman build \
    --layers \
    -t trading-system:${VERSION} \
    -t ${REGISTRY}/trading-system:${VERSION} \
    -f deployment/Containerfile \
    .

# Scan for vulnerabilities
podman scan trading-system:${VERSION} || echo "Scan skipped"

# Push to registry
podman push ${REGISTRY}/trading-system:${VERSION}

echo "Build complete: ${REGISTRY}/trading-system:${VERSION}"
```

### Validación post-build

```bash
# Test container runs
podman run --rm trading-system:latest python -c "import trading_system; print('OK')"

# Test health endpoint
podman run -d --name test trading-system:latest
sleep 5
curl http://localhost:8000/health
podman stop test
```

## Optimización

### Multi-stage build

```dockerfile
# Builder stage
FROM python:3.11-slim as builder
WORKDIR /build
RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim
COPY --from=builder /root/.local /opt/venv
COPY src/ ./src/
CMD ["python", "-m", "trading_system"]
```

### Best practices

- [ ] Usar usuario no-root
- [ ] Multi-stage builds
- [ ] Minimize layers
- [ ] No secrets en imagen
- [ ] Health check
- [ ] .dockerignore para archivos innecesarios

---

**Versión**: 1.0.0  
**Última actualización**: 2026-03-19
