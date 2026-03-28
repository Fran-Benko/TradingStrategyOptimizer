# Deployment Workflow

## Descripción

Workflow para deployment seguro a diferentes ambientes.

## Ambientes

| Ambiente | Propósito | Strategy | Approval |
|----------|-----------|----------|----------|
| Development | Testing local | Direct | None |
| Staging | Pre-prod testing | Blue-green | 1 reviewer |
| Production | Live trading | Canary → Rolling | 2 reviewers |

## Proceso de Deployment

### 1. Pre-deployment Checks

```bash
# Validaciones antes de deploy
@DeploymentEngineer pre-deployment-check
Incluye: tests, security, backup
```

**Checklist:**
- [ ] Todos los tests passing
- [ ] Security scan passed
- [ ] Backup completado
- [ ] Rollback plan preparado
- [ ] Monitoring actualizado
- [ ] Team notificado

### 2. Build

```bash
# Build de imagen
podman build \
    -t trading-system:${VERSION} \
    -t trading-system:${GIT_SHA} \
    -f deployment/Containerfile \
    .

# Scan de vulnerabilidades
trivy image trading-system:${VERSION}
```

### 3. Deployment

#### Staging (Blue-Green)

```bash
# Deploy to staging
./scripts/deploy.sh staging ${VERSION}

# Validate
python scripts/deployment-validator.py http://staging:8000 ${VERSION}

# Switch traffic
kubectl rollout status deployment/trading-system-staging
```

#### Production (Canary)

```bash
# 1. Deploy 10% canary
kubectl set image deployment/trading-system trading-system=${VERSION}
kubectl patch deployment trading-system -p '{"spec":{"replicas":3}}'

# 2. Monitor for 1 hour
@MonitoringSetup check-metrics --duration 1h

# 3. If healthy, full rollout
kubectl patch deployment trading-system -p '{"spec":{"replicas":10}}'

# 4. If issues, rollback
kubectl rollout undo deployment/trading-system
```

### 4. Post-deployment

```bash
# Validar deployment
@DeploymentEngineer post-deployment-validation
Incluye: health, smoke tests, metrics
```

### 5. Rollback

```bash
# Rollback rápido
@DeploymentEngineer rollback
Versión: anterior estable

# Rollback manual
kubectl rollout undo deployment/trading-system
```

## Integración con Agentes

| Etapa | Agente |
|-------|--------|
| Pre-check | @DeploymentEngineer, @SecurityAuditor |
| Build | @ContainerSpecialist |
| Deploy | @DeploymentEngineer |
| Validate | @MonitoringSetup |
| Rollback | @DeploymentEngineer |

---

**Última actualización**: 2026-03-19
