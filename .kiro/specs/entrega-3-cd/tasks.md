# Tareas — Entrega 3: Entrega Continua (CD)

Planeado para las **semanas 5 y 6** del curso. El baseline manual de Fargate va antes del
despliegue automático. La captura de evidencia se agenda junto a cada ejecución.

Convención de owner: **Kiro** (local, sin stage) o **Owner** (commits/push y acciones AWS).

---

## Semana 5 — Implementación local y baseline

- [ ] 1. Crear el Feature Spec `entrega-3-cd`
  - Crear `requirements.md`, `design.md`, `tasks.md`.
  - _Dependencias:_ ninguna.
  - _Verificación:_ los tres archivos existen y son coherentes con el plan.
  - _Evidencia:_ archivos del spec.
  - _Owner:_ Kiro.
  - _Requisitos:_ todos.

- [ ] 2. Verificar baseline local (pruebas + build de imagen)
  - Confirmar rama `feature/release_3`. Correr `pytest` (23). Construir imagen amd64 y
    verificar `/health` con `docker run`.
  - _Dependencias:_ 1.
  - _Verificación:_ `pytest` 23 passed; `docker build` OK; `/health` → 200.
  - _Evidencia:_ salida de pytest y de docker.
  - _Owner:_ Kiro.
  - _Requisitos:_ R-FARGATE, R-CI-CONFIG.

- [ ] 3. Añadir `buildspec.ecs.yml` (CI → imagen ECR)
  - pytest → (si pasa) login ECR, docker build/push tag=SHA, emitir `imageDetail.json`.
    Conservar `buildspec.yml` EB. Gate con `CODEBUILD_BUILD_SUCCEEDING`.
  - _Dependencias:_ 2.
  - _Verificación:_ YAML válido; gate demostrado localmente; sin secretos en el archivo.
  - _Evidencia:_ `buildspec.ecs.yml`.
  - _Owner:_ Kiro (archivo) / Owner (proyecto CodeBuild en AWS).
  - _Requisitos:_ R-CI-CONFIG, R-CI-TRIGGER.

- [ ] 4. Añadir `deploy/taskdef.json`, `deploy/appspec.yaml` y validador
  - Task definition Fargate parametrizada + appspec con placeholders; validador de coherencia.
  - _Dependencias:_ 2.
  - _Verificación:_ `python scripts/validate_deploy_artifacts.py` OK; JSON/YAML válidos.
  - _Evidencia:_ artefactos de despliegue + salida del validador.
  - _Owner:_ Kiro.
  - _Requisitos:_ R-CI-CONFIG, R-CD-AUTO.

- [ ] 5. Actualizar la colección Postman
  - Variable `baseUrl`; casos health + negocio con datos desechables.
  - _Dependencias:_ 2.
  - _Verificación:_ JSON válido; casos revisados.
  - _Evidencia:_ colección Postman.
  - _Owner:_ Kiro.
  - _Requisitos:_ R-FARGATE, R-CD-AUTO.

- [ ] 6. Procedimiento del baseline manual Fargate
  - `deploy/create-fargate-baseline.md` (ECR bootstrap, cluster, ALB, 2 TG, listener :80,
    servicio CODE_DEPLOY, SG, secrets, egress) con comandos PowerShell y bash + checklist.
  - _Dependencias:_ 3, 4.
  - _Verificación:_ coherencia con taskdef/appspec/puertos.
  - _Evidencia:_ documento runbook.
  - _Owner:_ Kiro (doc) / Owner (ejecución AWS tras aprobación).
  - _Requisitos:_ R-FARGATE.

## Semana 6 — Automatización, escenarios y documento

- [ ] 7. Preparar parches del escenario CD FAIL (reversibles)
  - `deploy/cd-fail/`: ruta A (hook Lambda) y ruta B (override taskdef), fuera del working
    tree normal; nota de selección por permisos.
  - _Dependencias:_ 4, 6.
  - _Verificación:_ artefactos parsean; override determinista; no contaminan el repo normal.
  - _Evidencia:_ parches en `deploy/cd-fail/`.
  - _Owner:_ Kiro (preparación) / Owner (publicación controlada).
  - _Requisitos:_ R-DOC-CD-FAIL.

- [ ] 8. Borrador del documento de evidencias (español)
  - `docs/entrega-3/README.md`: arquitectura, baseline, flujo de trigger/artefactos, una
    sección por run; placeholders PENDIENTE; checklist de capturas para el operador.
  - _Dependencias:_ 3–7.
  - _Verificación:_ estructura completa; no observado = PENDIENTE.
  - _Evidencia:_ borrador del documento.
  - _Owner:_ Kiro (borrador) / Owner+equipo (capturas y PDF final).
  - _Requisitos:_ R-DOC-CI-FAIL, R-DOC-SUCCESS, R-DOC-CD-FAIL.

- [ ] 9. Cableado final + tabla de estado del gate de revisión
  - Coherencia end-to-end (puertos, contenedor, placeholders, rutas/casing). Tabla de estado
    por ID. Dejar todo sin stage.
  - _Dependencias:_ 1–8.
  - _Verificación:_ `pytest` verde; validador verde; diff listo; secuencia AWS enumerada.
  - _Evidencia:_ diff + resultados + tabla de estado.
  - _Owner:_ Kiro.
  - _Requisitos:_ todos.

## Post-aprobación (Owner publica revisiones a CodeCommit `master`)

- [ ] 10. Verificación read-only de AWS (inventario)
  - Cuenta/región/permisos, CodeCommit, CodeBuild/CodePipeline, roles, RDS, VPC/ALB/TG, ECR.
  - _Owner:_ Owner/operador. _Requisitos:_ todos (habilitación).

- [ ] 11. Baseline manual Fargate en AWS + Postman
  - Ejecutar el runbook; capturar ECS/ALB/Postman.
  - _Owner:_ Owner. _Requisitos:_ R-FARGATE.

- [ ] 12. Configurar CI/CD en AWS (CodeCommit source, CodeBuild ECS, ECR, CodeDeploy, pipeline)
  - EventBridge + polling off; CodeDeployToECS con mapeo de artefactos.
  - _Owner:_ Owner. _Requisitos:_ R-CI-CONFIG, R-CI-TRIGGER, R-CD-AUTO.

- [ ] 13. Run CI OK / CD OK + evidencia
  - _Owner:_ Owner. _Requisitos:_ R-DOC-SUCCESS.

- [ ] 14. Run CI FAIL / CD no ejecutado + revert + evidencia
  - _Owner:_ Owner. _Requisitos:_ R-DOC-CI-FAIL.

- [ ] 15. Run CI OK / CD FAIL + revert + evidencia
  - _Owner:_ Owner. _Requisitos:_ R-DOC-CD-FAIL.

- [ ] 16. Ensamblar PDF final `Proyecto 1 entrega 3 – Documento.pdf` + video del equipo
  - _Owner:_ Owner + equipo. _Requisitos:_ todos + R-VIDEO.
