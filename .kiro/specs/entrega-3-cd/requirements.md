# Requisitos — Entrega 3: Entrega Continua (CD)

Microservicio de lista negra de emails · Grupo Blue Team
Curso MISW-4302 DevOps · Universidad de los Andes

## Introducción

La Entrega 3 añade **Entrega Continua (CD)** al microservicio Flask existente, extendiendo
la CI de la Entrega 2. El objetivo es que cada commit publicado por el owner en la rama
`master` de **AWS CodeCommit** dispare automáticamente **AWS CodePipeline**, que
AWS CodeBuild ejecute la suite de pruebas unitarias existente y, solo si pasa, construya
y publique la imagen del contenedor en **Amazon ECR**, y que **AWS CodeDeploy** despliegue
esa imagen al servicio **ECS Fargate** mediante una estrategia blue/green, sin aprobación
manual en el camino normal. Un build fallido impide el despliegue de esa ejecución.

Antes del despliegue automático se establece un **baseline manual** en Fargate y se verifica
la API viva con Postman. Después de la revisión del owner se documentan tres ejecuciones
reales: CI OK/CD OK, CI FAIL/CD no ejecutado, y CI OK/CD FAIL.

El trabajo local se realiza en la rama `feature/release_3`. GitHub `main` sigue siendo la
rama de integración del equipo; CodeCommit `master` es la fuente del pipeline de la Entrega 3.

## Glosario

- **CI**: Integración Continua (pruebas + construcción/publicación de imagen).
- **CD**: Entrega Continua (despliegue automático a ECS Fargate vía CodeDeploy).
- **Baseline**: primer despliegue manual del servicio en Fargate, previo al CD automático.
- **Blue/green**: dos conjuntos de tareas (actual y reemplazo) con dos target groups.

## Requisitos

### R-FARGATE — Despliegue manual previo a AWS Fargate (20%)

**Historia:** Como equipo, queremos desplegar manualmente el microservicio en ECS Fargate
antes de automatizar, para tener un baseline verificado y comparable.

#### Criterios de aceptación

1. CUANDO se construye la primera imagen y se publica en ECR, ENTONCES existe una imagen
   con tag trazable (SHA del commit) consumible por la task definition de Fargate.
2. CUANDO se crea el servicio ECS en Fargate, ENTONCES usa red `awsvpc`, arquitectura
   x86_64, tamaño compatible con Fargate, contenedor en el puerto 8000 y logs a CloudWatch.
3. CUANDO el servicio está activo, ENTONCES la task se reporta RUNNING y el target activo
   queda healthy detrás del ALB en el listener de producción (:80).
4. CUANDO se prueba con Postman contra el endpoint del ALB, ENTONCES `/health` responde
   `200 {"status":"ok"}` y al menos una operación de negocio responde el estado y cuerpo
   esperados (usando datos de prueba desechables en escrituras).
5. CUANDO se captura el baseline, ENTONCES se conservan capturas de ECS (task RUNNING),
   salud del target en el ALB y respuestas de Postman, antes de la primera entrega automática.
6. CUANDO el servicio necesita la base de datos, ENTONCES PostgreSQL permanece privado y las
   credenciales se inyectan por referencias de secreto de ECS (nunca en código ni en la imagen).

### R-CI-CONFIG — Configuración de CodeDeploy y pruebas en CodeBuild (10%)

**Historia:** Como equipo, queremos que la configuración de despliegue viva en el repositorio
y que CodeBuild falle cuando una prueba falle.

#### Criterios de aceptación

1. CUANDO el owner publica la revisión aprobada en CodeCommit `master`, ENTONCES el
   repositorio contiene la configuración requerida por CodeDeploy (`appspec.yaml` y
   `taskdef.json`).
2. CUANDO CodeBuild ejecuta la fase de pruebas, ENTONCES corre la suite pytest existente de
   la Entrega 2 sin alterar el contrato del API.
3. CUANDO una prueba unitaria falla, ENTONCES CodeBuild termina en estado fallido.
4. CUANDO el build falla, ENTONCES no se publica imagen ni se produce un artefacto
   desplegable para esa ejecución.
5. CUANDO corren las pruebas en CodeBuild, ENTONCES la salida queda en CloudWatch y el
   reporte JUnit se publica en la pestaña Informes.

### R-CI-TRIGGER — Disparo automático y publicación de imagen (10%)

**Historia:** Como equipo, queremos que un push a `master` en CodeCommit inicie el pipeline
automáticamente y publique la imagen en ECR cuando la CI tenga éxito.

#### Criterios de aceptación

1. CUANDO el owner hace push a `master` en CodeCommit, ENTONCES CodePipeline inicia
   automáticamente mediante una regla de EventBridge.
2. CUANDO EventBridge está configurado, ENTONCES el polling de la acción Source queda
   desactivado para evitar ejecuciones duplicadas.
3. CUANDO la CI tiene éxito, ENTONCES CodeBuild construye la imagen (arquitectura
   compatible con Fargate) y la publica en ECR con tag derivado del commit resuelto,
   registrando el digest y evitando `latest` como entrada de despliegue.
4. CUANDO se produce el artefacto de build, ENTONCES contiene `imageDetail.json` con el
   `ImageURI` de la imagen recién publicada.
5. CUANDO se registra cada ejecución, ENTONCES se anota el commit exacto que la inició.

### R-CD-AUTO — Despliegue automático a ECS Fargate por CodeDeploy (40%)

**Historia:** Como equipo, queremos que una etapa CI exitosa despliegue automáticamente la
imagen al servicio ECS Fargate mediante CodeDeploy, sin aprobación manual.

#### Criterios de aceptación

1. CUANDO la etapa CI termina con éxito, ENTONCES CodePipeline ejecuta una acción Deploy
   con proveedor `CodeDeployToECS` sin aprobación manual en el camino normal.
2. CUANDO se configura la acción Deploy, ENTONCES mapea explícitamente los artefactos de
   AppSpec, task definition e imagen; el placeholder `<IMAGE1_NAME>` del taskdef coincide
   con `Image1ContainerName = IMAGE1_NAME`, y el AppSpec declara `TaskDefinition: <TASK_DEFINITION>`.
3. CUANDO se despliega, ENTONCES el nombre de contenedor y el puerto del AppSpec coinciden
   con la task definition y con el servicio ECS.
4. CUANDO el servicio ECS usa CodeDeploy, ENTONCES su controlador de despliegue es
   `CODE_DEPLOY` y el grupo de despliegue apunta al servicio, listeners y target groups
   correctos, con rollback en caso de fallo cuando esté permitido.
5. CUANDO una ejecución tiene CI exitosa, ENTONCES la revisión en ejecución del servicio ECS
   coincide con la imagen del build y Postman sigue respondiendo correctamente.
6. CUANDO un build falla, ENTONCES no se ejecuta la acción Deploy para esa ejecución y el
   servicio existente permanece sano.

### R-DOC-CI-FAIL — Evidencia CI fallida (4%)

#### Criterios de aceptación

1. CUANDO el owner publica un cambio con una aserción fallida real, ENTONCES se documenta
   la ejecución con CI fallida, el SHA, el execution ID, el log de CloudWatch con la prueba
   que falló, la ausencia de la acción Deploy y el servicio existente aún sano.
2. CUANDO el owner publica el revert, ENTONCES se verifica la recuperación.

### R-DOC-SUCCESS — Evidencia CI OK / CD OK (8%)

#### Criterios de aceptación

1. CUANDO el owner publica un cambio seguro con pruebas que pasan, ENTONCES se documenta la
   ejecución exitosa con execution ID y SHA, salida de pruebas de CodeBuild, tag/digest de
   la imagen en ECR, éxito de CodeDeploy con su deployment ID, revisión Fargate en ejecución
   con target healthy, y respuesta Postman exitosa.

### R-DOC-CD-FAIL — Evidencia CI OK / CD FAIL (8%)

#### Criterios de aceptación

1. CUANDO el owner publica un cambio de despliegue que hace que CodeDeploy falle realmente
   (hook de validación que retorna `Failed`, o override de task definition que hace fallar el
   health check del task de reemplazo), ENTONCES se documenta: build verde con su imagen
   publicada, acción Deploy fallida en CodePipeline, deployment ID y motivo de fallo de
   CodeDeploy, evidencia de ECS/ALB o del hook, rollback o task set estable, y una respuesta
   Postman que prueba disponibilidad del servicio.
2. CUANDO el owner publica el revert, ENTONCES se verifica la recuperación.
3. UN artefacto inválido rechazado antes de iniciar CodeDeploy, una ejecución cancelada
   manualmente o un build fallido NO son evidencia suficiente para este escenario.

### R-VIDEO — Sustentación en video (obligatorio)

#### Criterios de aceptación

1. EL equipo entrega un video explicativo de máximo 10 minutos con evidencia funcional
   (código, pruebas del API, GitHub y AWS). La ausencia del video califica la entrega con 0.0.

## Restricciones y no-objetivos

- No se hacen commits ni pushes desde esta sesión; el owner los realiza. Los cambios quedan
  sin stage.
- No se tocan recursos de AWS hasta aprobación explícita del owner.
- Se conserva la CI de la Entrega 2 (`buildspec.yml` de Elastic Beanstalk permanece intacto);
  la Entrega 3 añade `buildspec.ecs.yml`.
- Se preservan las funcionalidades de la Entrega 1 y las pruebas automatizadas de la Entrega 2.
- Se usan únicamente el lab de Academy autorizado, el repositorio y los roles aprobados.
- Las credenciales y valores secretos se mantienen fuera de código, artefactos, capturas y logs.
