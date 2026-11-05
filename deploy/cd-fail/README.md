# Escenario CD FAIL — parches reversibles (Entrega 3)

Grupo Blue Team · MISW-4302

Objetivo: provocar una **falla real de CodeDeploy** (R-DOC-CD-FAIL) con CI verde e imagen
publicada en ECR, demostrando que CodeDeploy crea un despliegue y reporta un fallo real, y
que la versión estable sigue respondiendo. Después, verificar la recuperación tras el revert.

> **No vale** como evidencia: un artefacto inválido rechazado antes de iniciar CodeDeploy, una
> ejecución cancelada a mano, ni un build fallido. El build **debe** pasar y la imagen **debe**
> publicarse.

Estos archivos son **parches separados y reversibles**, fuera del flujo normal. El owner los
publica de forma controlada en un commit temporal a CodeCommit `master` y luego revierte.

## Selección de ruta (según permisos del lab Academy)

| Ruta | Mecanismo | Requiere | Preferencia |
|---|---|---|---|
| **A** | Hook de validación CodeDeploy (Lambda retorna `Failed`) | Permisos de Lambda + `codedeploy:PutLifecycleEventHookExecutionStatus` | **Preferida** |
| **B** | Override de task definition que hace fallar el health check del task de reemplazo | Solo ECS/CodeDeploy | Alternativa si no hay Lambda |

Verificar primero con el operador si hay permisos de Lambda:

```bash
aws lambda list-functions --query "Functions[].FunctionName" --output text
aws iam get-role --role-name __LAMBDA_ROLE__ 2>/dev/null && echo "lambda role OK"
```

Implementar **solo la ruta aprobada**.

---

## Ruta A — Hook de validación CodeDeploy (preferida)

1. Desplegar la Lambda `validation_hook.py` (ver archivo en esta carpeta) con un rol que tenga
   `codedeploy:PutLifecycleEventHookExecutionStatus` y permisos básicos de logs.
2. En el commit temporal, el AppSpec incluye el bloque `Hooks` que asocia la Lambda al evento
   de ciclo de vida `AfterAllowTestTraffic` (antes de mover tráfico de producción). Usar el
   fragmento de `appspec.hooks-fail.yaml`.
3. CodeDeploy invoca la Lambda; esta llama a `put_lifecycle_event_hook_execution_status` con
   `status="Failed"`, usando `DeploymentId` y `LifecycleEventHookExecutionId` del evento.
4. CodeDeploy marca el despliegue como fallido **antes** de redirigir el tráfico de producción;
   el task set estable (blue) sigue sirviendo.

Evidencia a capturar: build verde + imagen en ECR, acción Deploy fallida en CodePipeline,
deployment ID y motivo (hook `Failed`), log de la Lambda, y Postman respondiendo desde el ALB.

### Reversión
- Revertir el AppSpec a la versión sin `Hooks` (la de `deploy/appspec.yaml`).
- Opcional: eliminar la Lambda y su asociación.

---

## Ruta B — Override de task definition (alternativa)

1. Usar `taskdef.cd-fail.override.json` como override: cambia el health check del contenedor
   para que **siempre falle** (comando apuntando a un puerto/ruta inexistente). Esto hace que
   el task de reemplazo (green) nunca quede healthy.
2. CodeDeploy crea el despliegue, espera a que el nuevo task set pase el health check, el
   health check falla de forma determinista, y el despliegue termina en fallo. El task set
   estable (blue) permanece healthy.
3. Es determinista respecto a la imagen real (el contenedor arranca, pero el health check del
   contenedor falla), y respeta los tiempos de espera del health check y del despliegue.

Evidencia a capturar: build verde + imagen en ECR, acción Deploy fallida, deployment ID y
motivo (tasks no saludables), estado de ECS/ALB (task set estable sano), rollback o task set
estable, y Postman respondiendo desde el ALB.

### Reversión
- Revertir `deploy/taskdef.json` a la versión normal (sin el health check roto) y volver a
  publicar en `master`.

---

## Verificación de recuperación (ambas rutas)

Tras el revert publicado por el owner:
- Nueva ejecución del pipeline en verde.
- Despliegue de CodeDeploy exitoso.
- Revisión en ejecución del servicio coincide con la imagen del build.
- Postman: `/health` 200 y la operación de negocio OK.
- Distinguir en el documento el **despliegue fallido intencional** del **despliegue de recuperación**.
