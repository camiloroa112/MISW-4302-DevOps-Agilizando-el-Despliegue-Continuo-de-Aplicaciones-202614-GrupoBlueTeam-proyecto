# CD FAIL — Ruta A: hook de validación de CodeDeploy (Lambda).
#
# CodeDeploy invoca esta función en el evento de ciclo de vida configurado en el AppSpec
# (AfterAllowTestTraffic). La función reporta deliberadamente "Failed" para provocar un fallo
# REAL del despliegue antes de mover tráfico de producción, dejando el task set estable intacto.
#
# Permisos mínimos del rol de la Lambda:
#   - codedeploy:PutLifecycleEventHookExecutionStatus
#   - logs:CreateLogGroup, logs:CreateLogStream, logs:PutLogEvents (logs básicos)
#
# Despliegue sugerido (runtime python3.12, handler = validation_hook.handler).
# Este archivo es un parche del escenario CD FAIL y NO forma parte del runtime del servicio.

# 1st Party Imports
import boto3

# Cliente de CodeDeploy reutilizado entre invocaciones
codedeploy = boto3.client("codedeploy")


# Punto de entrada que CodeDeploy invoca durante el lifecycle hook
def handler(event: dict, context) -> dict:
    """
    Introduction:
        - This Lambda reports a deliberate "Failed" validation status to CodeDeploy so the
          deployment fails before shifting production traffic (CD FAIL scenario, route A)
    Returns:
        - dict: A minimal response payload
    """

    # CodeDeploy entrega el ID del despliegue y el ID de ejecución del hook en el evento
    deployment_id = event["DeploymentId"]

    # El ID de ejecución del hook identifica esta validación concreta
    lifecycle_event_hook_execution_id = event["LifecycleEventHookExecutionId"]

    # Reportar "Failed" a propósito: esto hace que el despliegue termine en fallo real
    codedeploy.put_lifecycle_event_hook_execution_status(
        deploymentId = deployment_id,
        lifecycleEventHookExecutionId = lifecycle_event_hook_execution_id,
        status = "Failed",
    )

    # Devolver una respuesta mínima (CodeDeploy ya recibió el estado por la llamada anterior)
    return {"status": "Failed", "deploymentId": deployment_id}
