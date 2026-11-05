# Baseline manual en AWS Fargate — Runbook (Entrega 3)

Grupo Blue Team · MISW-4302

Este runbook establece el **baseline manual** del microservicio en ECS Fargate antes de
habilitar el despliegue automático (CD). Es el requisito **R-FARGATE**. Ejecutar solo tras la
aprobación del owner. Todos los comandos existen en versión PowerShell y bash; cuando el
comando es idéntico, se muestra una sola vez.

> **Convención de parámetros.** Reemplaza los valores `__PLACEHOLDER__` con los IDs reales del
> lab de Academy. No escribas secretos en archivos versionados; usa Secrets Manager / SSM.

| Parámetro | Descripción |
|---|---|
| `__ACCOUNT_ID__` | ID de cuenta AWS (12 dígitos) |
| `__REGION__` | Región (p. ej. `us-east-1`) |
| `__VPC_ID__` | VPC del lab Academy |
| `__SUBNET_A__`, `__SUBNET_B__` | Dos subnets (para ALB y tasks) |
| `__TASK_EXECUTION_ROLE__` | Rol de ejecución de la task (pull ECR, logs, secrets) |
| `__TASK_ROLE__` | Rol de la task (acceso a dependencias) |
| `__DB_HOST__`, `__DB_NAME__` | Endpoint y nombre de la base de datos |
| `__DB_SECRET__`, `__JWT_SECRET__` | Nombres/ARN de secretos en Secrets Manager |

El contenedor se llama **`blacklist`** y escucha en el puerto **8000** (coincide con
`Dockerfile`, `deploy/taskdef.json` y `deploy/appspec.yaml`). El health check es **`/health`**.

---

## 0. Verificación read-only previa (operador)

Antes de crear nada, inventariar y confirmar lo que ya existe (no crea recursos):

```bash
aws sts get-caller-identity
aws ec2 describe-subnets --filters Name=vpc-id,Values=__VPC_ID__ --query "Subnets[].{Id:SubnetId,AZ:AvailabilityZone,Public:MapPublicIpOnLaunch}"
aws rds describe-db-instances --query "DBInstances[?DBInstanceIdentifier=='blacklist-db'].{Status:DBInstanceStatus,Endpoint:Endpoint.Address,Public:PubliclyAccessible}"
aws ecr describe-repositories --query "repositories[].repositoryName"
aws iam list-roles --query "Roles[?contains(RoleName, 'ecs') || contains(RoleName, 'CodeDeploy') || contains(RoleName, 'LabRole')].RoleName"
```

- Si `blacklist-db` existe, está `available`, no es público y es alcanzable desde las subnets
  de las tasks, **reutilízalo**. Si no, ver el anexo "RDS mínimo privado" al final.
- Verifica que las subnets de las tasks tengan **egress** (NAT o endpoints) para el pull de
  ECR y el acceso a Secrets Manager/CloudWatch.

> **Hallazgo de la verificación local:** la aplicación ejecuta `db.create_all()` al arrancar
> (en `create_app`). La task **no inicia** si la base de datos no es alcanzable al boot; el
> health check del ALB solo pasa cuando el worker de gunicorn arranca. Confirma la
> conectividad RDS ↔ subnets/SG de las tasks antes de desplegar.

---

## 1. ECR: repositorio y primera imagen (bootstrap)

```bash
# Crear el repositorio (idempotente: ignora error si ya existe)
aws ecr create-repository --repository-name blacklist-service --region __REGION__ || true

# Login a ECR
aws ecr get-login-password --region __REGION__ | docker login --username AWS --password-stdin __ACCOUNT_ID__.dkr.ecr.__REGION__.amazonaws.com
```

Construir y publicar la primera imagen con un tag trazable (SHA del commit del baseline):

PowerShell:
```powershell
$sha = (git rev-parse --short HEAD)
$uri = "__ACCOUNT_ID__.dkr.ecr.__REGION__.amazonaws.com/blacklist-service:$sha"
docker build --platform linux/amd64 --provenance=false -t $uri .
docker push $uri
Write-Output "IMAGE_URI=$uri"
```

bash:
```bash
SHA=$(git rev-parse --short HEAD)
URI=__ACCOUNT_ID__.dkr.ecr.__REGION__.amazonaws.com/blacklist-service:$SHA
docker build --platform linux/amd64 --provenance=false -t "$URI" .
docker push "$URI"
echo "IMAGE_URI=$URI"
```

---

## 2. Secretos (Secrets Manager)

Crear los secretos con las claves que consume `deploy/taskdef.json`
(`DB_USER`, `DB_PASSWORD`, `JWT_SECRET_KEY`). Genera el JWT con `scripts/generate_token.py`
usando el mismo `JWT_SECRET_KEY` para las pruebas con Postman.

```bash
aws secretsmanager create-secret --name blacklist/db --secret-string '{"DB_USER":"postgres","DB_PASSWORD":"__REDACTED__"}' --region __REGION__
aws secretsmanager create-secret --name blacklist/jwt --secret-string '{"JWT_SECRET_KEY":"__REDACTED__"}' --region __REGION__
```

> No pegues los valores reales en el documento ni en capturas. Usa `__REDACTED__` en la evidencia.

---

## 3. CloudWatch Logs

```bash
aws logs create-log-group --log-group-name /ecs/blacklist-service --region __REGION__ || true
```

---

## 4. Seguridad de red (security groups)

```bash
# SG del ALB: entra 80 desde Internet
aws ec2 create-security-group --group-name blacklist-alb-sg --description "ALB blacklist" --vpc-id __VPC_ID__ --region __REGION__
aws ec2 authorize-security-group-ingress --group-id __ALB_SG__ --protocol tcp --port 80 --cidr 0.0.0.0/0 --region __REGION__

# SG de las tasks: entra 8000 SOLO desde el SG del ALB
aws ec2 create-security-group --group-name blacklist-task-sg --description "Tasks blacklist" --vpc-id __VPC_ID__ --region __REGION__
aws ec2 authorize-security-group-ingress --group-id __TASK_SG__ --protocol tcp --port 8000 --source-group __ALB_SG__ --region __REGION__
```

Asegúrate de que el SG de RDS permita 5432 desde `__TASK_SG__` y que RDS siga privado.

---

## 5. ALB + dos target groups IP + listener de producción

CodeDeploy blue/green para ECS requiere **dos target groups** de tipo `ip` y un listener de
producción en el ALB.

```bash
# ALB público
aws elbv2 create-load-balancer --name blacklist-alb --type application --scheme internet-facing \
  --subnets __SUBNET_A__ __SUBNET_B__ --security-groups __ALB_SG__ --region __REGION__

# Dos target groups IP con health check en /health y puerto 8000
aws elbv2 create-target-group --name blacklist-tg-blue  --protocol HTTP --port 8000 --vpc-id __VPC_ID__ \
  --target-type ip --health-check-path /health --region __REGION__
aws elbv2 create-target-group --name blacklist-tg-green --protocol HTTP --port 8000 --vpc-id __VPC_ID__ \
  --target-type ip --health-check-path /health --region __REGION__

# Listener de producción :80 apuntando inicialmente al target group blue
aws elbv2 create-listener --load-balancer-arn __ALB_ARN__ --protocol HTTP --port 80 \
  --default-actions Type=forward,TargetGroupArn=__TG_BLUE_ARN__ --region __REGION__
```

---

## 6. Task definition

Materializa `deploy/taskdef.json` reemplazando los placeholders y regístrala. Para el baseline,
la imagen puede fijarse al `IMAGE_URI` del paso 1 (en el pipeline la reemplaza
`<IMAGE1_NAME>`).

PowerShell:
```powershell
(Get-Content deploy\taskdef.json) `
  -replace '__ACCOUNT_ID__','__ACCOUNT_ID__' `
  -replace '__REGION__','__REGION__' `
  -replace '__TASK_EXECUTION_ROLE__','__TASK_EXECUTION_ROLE__' `
  -replace '__TASK_ROLE__','__TASK_ROLE__' `
  -replace '__DB_HOST__','__DB_HOST__' `
  -replace '__DB_NAME__','__DB_NAME__' `
  -replace '__DB_SECRET__','blacklist/db' `
  -replace '__JWT_SECRET__','blacklist/jwt' `
  -replace '<IMAGE1_NAME>',$uri | Set-Content deploy\taskdef.baseline.json
aws ecs register-task-definition --cli-input-json file://deploy/taskdef.baseline.json --region __REGION__
```

bash (usar `sed` con los mismos reemplazos) y luego:
```bash
aws ecs register-task-definition --cli-input-json file://deploy/taskdef.baseline.json --region __REGION__
```

> `deploy/taskdef.baseline.json` es un archivo generado y temporal; no lo versiones.

---

## 7. Cluster y servicio ECS (controlador CODE_DEPLOY)

```bash
aws ecs create-cluster --cluster-name blacklist-cluster --region __REGION__

aws ecs create-service \
  --cluster blacklist-cluster \
  --service-name blacklist-service \
  --task-definition blacklist-service \
  --desired-count 1 \
  --launch-type FARGATE \
  --deployment-controller type=CODE_DEPLOY \
  --network-configuration "awsvpcConfiguration={subnets=[__SUBNET_A__,__SUBNET_B__],securityGroups=[__TASK_SG__],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=__TG_BLUE_ARN__,containerName=blacklist,containerPort=8000" \
  --region __REGION__
```

> `assignPublicIp=ENABLED` solo si las tasks están en subnets públicas y necesitan salida
> directa; si usas subnets privadas con NAT/endpoints, ponlo en `DISABLED`.

---

## 8. Verificación del baseline (checklist de evidencia)

1. **Task RUNNING:**
   ```bash
   aws ecs describe-services --cluster blacklist-cluster --services blacklist-service \
     --query "services[0].{Running:runningCount,Desired:desiredCount,Controller:deploymentController.type}"
   ```
   Esperado: `Running=1`, `Desired=1`, `Controller=CODE_DEPLOY`.

2. **Target healthy:**
   ```bash
   aws elbv2 describe-target-health --target-group-arn __TG_BLUE_ARN__ \
     --query "TargetHealthDescriptions[].TargetHealth.State"
   ```
   Esperado: `healthy`.

3. **Postman contra el ALB:** fijar `baseUrl = http://__ALB_DNS__` y `token = <JWT>` en la
   colección `postman/Blacklist API - Entrega 3 CD.postman_collection.json` y ejecutar:
   - `GET /health` → `200 {"status":"ok"}`
   - `POST /blacklists` → `201` (email desechable)
   - `GET /blacklists/<email>` → `200 is_blacklisted: true`

4. **Capturas a conservar (antes de la primera entrega automática):**
   - ECS: servicio con la task RUNNING y controlador CODE_DEPLOY.
   - ALB: salud del target group blue en `healthy`.
   - Postman: respuestas 200/201 desde el `baseUrl` del ALB.

---

## Anexo — RDS mínimo privado (solo si `blacklist-db` no es usable)

```bash
aws rds create-db-instance \
  --db-instance-identifier blacklist-db \
  --engine postgres \
  --db-instance-class db.t4g.micro \
  --allocated-storage 20 \
  --db-name blacklist \
  --master-username postgres \
  --master-user-password __REDACTED__ \
  --no-publicly-accessible \
  --vpc-security-group-ids __RDS_SG__ \
  --db-subnet-group-name __DB_SUBNET_GROUP__ \
  --region __REGION__
```

Mantén RDS privado y permite 5432 solo desde `__TASK_SG__`.
