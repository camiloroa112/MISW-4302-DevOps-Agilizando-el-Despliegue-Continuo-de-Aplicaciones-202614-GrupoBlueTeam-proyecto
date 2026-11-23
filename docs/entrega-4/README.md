# Proyecto 1 – Entrega 4: Monitoreo con New Relic

**Curso:** MISW-4302 DevOps – Agilizando el Despliegue Continuo de Aplicaciones
**Grupo:** Blue Team
**Servicio:** Microservicio de lista negra global de emails (`blacklist-service`)

---

## 1. Objetivo

Instrumentar el microservicio de lista negra con **New Relic APM** y verificar que reporta datos en dos entornos:

- **Desarrollo (local):** contenedor Docker en la máquina del desarrollador.
- **Nube:** AWS ECS Fargate, desplegado con el pipeline de CI/CD (CodePipeline → CodeBuild → CodeDeploy blue/green).

Sobre el entorno en la nube se ejecutó una prueba de estrés con **k6** para analizar tiempos de respuesta (servicio y base de datos), Apdex, errores y alertas.

---

## 2. Arquitectura

```
Cliente / k6
     │  HTTP :80
     ▼
Application Load Balancer (blacklist-alb)
     │  Listener HTTP:80 → blacklist-tg-blue / blacklist-tg-green (blue/green)
     ▼
ECS Fargate (blacklist-cluster / blacklist-service)
  └─ Contenedor blacklist-app :5000
       newrelic-admin run-program gunicorn (1 worker, 4 hilos)
       │                                   │
       ▼                                   ▼
RDS PostgreSQL 16 (db.t3.micro)      New Relic APM
                                     (blacklist-service-cloud)
```

| Componente | Recurso |
|---|---|
| Red | VPC `blacklist-vpc` con 2 subredes públicas (us-east-1a / us-east-1b) |
| Seguridad | `blacklist-alb-sg` (80 desde internet) → `blacklist-ecs-sg` (5000 solo desde el ALB) → `blacklist-rds-sg` (5432 solo desde ECS) |
| Imágenes | ECR `blacklist-service` (tag = SHA corto del commit + `latest`) |
| Cómputo | ECS Fargate, 0,5 vCPU / 1 GB, 1 tarea |
| Base de datos | RDS PostgreSQL 16, `db.t3.micro`, sin acceso público |
| Secretos | SSM Parameter Store (SecureString): `/blacklist/DB_PASSWORD`, `/blacklist/JWT_SECRET_KEY`, `/blacklist/NEW_RELIC_LICENSE_KEY` |
| CI/CD | CodePipeline V2 `blacklist-cicd-pipeline` (Source → Build → Deploy), CodeBuild `blacklist-build`, CodeDeploy `blacklist-app` / `blacklist-dg` |

---

## 3. Configuración de New Relic

### 3.1 Creación de la cuenta (5 %)

Se creó una cuenta gratuita en New Relic. Para el agente se usa la llave de tipo **INGEST - LICENSE**, que se generó desde **API Keys → Create a key**. La llave **no se versiona** en el repositorio:

- En local se carga desde el archivo `.env`, que está en `.gitignore`.
- En la nube se lee desde SSM Parameter Store.

> 📷 *[Pantallazo: página API Keys con la llave INGEST - LICENSE, valor oculto]*

### 3.2 Configuración en el repositorio y verificación en desarrollo (30 %)

**Dependencia** (`pyproject.toml`):

```toml
dependencies = [
    ...
    "newrelic>=14.3.0",
]
```

**Arranque instrumentado** (`Dockerfile`): gunicorn se ejecuta envuelto en `newrelic-admin run-program`, de modo que el agente se inicializa antes de cargar la aplicación Flask, sin modificar el código fuente:

```dockerfile
CMD ["/app/.venv/bin/newrelic-admin", "run-program", "/app/.venv/bin/gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "application:application"]
```

**Configuración por variables de entorno** (sin archivo `newrelic.ini`):

| Variable | Local (`.env`) | Nube (`taskdef.json`) |
|---|---|---|
| `NEW_RELIC_LICENSE_KEY` | valor en `.env` | secreto SSM `/blacklist/NEW_RELIC_LICENSE_KEY` |
| `NEW_RELIC_APP_NAME` | `blacklist-service-local` | `blacklist-service-cloud` |
| `NEW_RELIC_DISTRIBUTED_TRACING_ENABLED` | `true` | `true` |
| `NEW_RELIC_APPLICATION_LOGGING_FORWARDING_ENABLED` | `true` | `true` |

Al usar dos nombres de aplicación distintos, los datos de cada entorno quedan separados en APM.

**Verificación local:**

```bash
docker run -d --name blacklist-pg -p 5432:5432 -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=blacklist postgres:16
docker build -t blacklist-test .
docker run --rm --network host --env-file .env blacklist-test
```

Se generó tráfico con Postman (201, 200, 409, 400 y 401) y con una prueba corta de k6:

| Métrica k6 (local, 5 VUs, 30 s) | Valor |
|---|---|
| Requests | 750 |
| Checks exitosos | 100 % |
| `http_req_duration` promedio | 9,02 ms |
| p(95) | 16,55 ms |
| `http_req_failed` | 0 % |

El servicio **`blacklist-service-local`** apareció en **APM & Services** con datos de tiempo de respuesta, desglosados entre Python y Postgres, además de Apdex, throughput y errores.

> 📷 *[Pantallazo: APM & Services → blacklist-service-local → Summary]*
> 📷 *[Pantallazo: resumen de k6 local]*

### 3.3 Despliegue en la nube con el pipeline de CI/CD y verificación (15 %)

Cambios en `taskdef.json` (plantilla que usa CodeDeploy):

```json
"environment": [
  { "name": "DB_HOST", "value": "<endpoint RDS>" },
  { "name": "NEW_RELIC_APP_NAME", "value": "blacklist-service-cloud" },
  { "name": "NEW_RELIC_DISTRIBUTED_TRACING_ENABLED", "value": "true" },
  { "name": "NEW_RELIC_APPLICATION_LOGGING_FORWARDING_ENABLED", "value": "true" }
],
"secrets": [
  { "name": "DB_PASSWORD", "valueFrom": "arn:aws:ssm:us-east-1:<cuenta>:parameter/blacklist/DB_PASSWORD" },
  { "name": "JWT_SECRET_KEY", "valueFrom": "arn:aws:ssm:us-east-1:<cuenta>:parameter/blacklist/JWT_SECRET_KEY" },
  { "name": "NEW_RELIC_LICENSE_KEY", "valueFrom": "arn:aws:ssm:us-east-1:<cuenta>:parameter/blacklist/NEW_RELIC_LICENSE_KEY" }
]
```

El rol `ecsTaskExecutionRole` tiene la política en línea `ReadBlacklistSecrets` (`ssm:GetParameters` sobre `parameter/blacklist/*`), así que la llave de New Relic quedó cubierta sin cambios de IAM.

**Flujo del pipeline:**

1. **Source:** cambio en `main` en GitHub (conexión CodeConnections).
2. **Build (CodeBuild):** `uv sync` → `uv lock --locked` → `pytest` → `docker build` → push a ECR con el tag del commit → genera `imageDetail.json`, `appspec.json` y `taskdef.json`.
3. **Deploy (CodeDeploy blue/green):** registra una nueva revisión de la definición de tarea, levanta las tareas en el grupo de destino alterno, mueve el 100 % del tráfico (`ECSAllAtOnce`) y termina la versión anterior a los 5 minutos. Tiene rollback automático si falla.

Ejecución: `c5a959e6-dbb1-4e90-8964-5d94655fad8d`. Etapas **Source**, **Build** y **Deploy** exitosas.

Verificación: `GET http://<ALB>/health` → `{"status": "ok"}`. El servicio **`blacklist-service-cloud`** reporta en New Relic APM.

> 📷 *[Pantallazo: CodePipeline con las 3 etapas en verde]*
> 📷 *[Pantallazo: CodeBuild → Informes de pytest]*
> 📷 *[Pantallazo: CodeDeploy → implementación blue/green completada]*
> 📷 *[Pantallazo: APM & Services → blacklist-service-cloud]*

---

## 4. Estrategia de pruebas de estrés

**Herramienta:** k6 (script `tests/stress/blacklist-stress.js`), ejecutado con Docker (`grafana/k6`), sin instalaciones adicionales.

**Escenario por iteración**, que simula el uso real del servicio:

| # | Request | Respuesta esperada |
|---|---|---|
| 1 | `GET /health` | 200 |
| 2 | `POST /blacklists` con email único | 201 |
| 3 | `GET /blacklists/<email agregado>` | 200 (`is_blacklisted: true`) |
| 4 | `GET /blacklists/<email inexistente>` | 200 (`is_blacklisted: false`) |
| 5 | `POST /blacklists` duplicado | 409 |
| 6 | 10 % de las iteraciones: body inválido | 400 |
| 7 | 10 % de las iteraciones: sin token | 401 |

Cada usuario virtual espera 1 s entre iteraciones (`sleep(1)`).

**Perfil de carga (10 minutos):**

| Etapa | Duración | Usuarios virtuales |
|---|---|---|
| Calentamiento | 1 min | 0 → 10 |
| Carga normal | 3 min | 10 |
| Rampa | 2 min | 10 → 50 |
| Carga pico | 3 min | 50 |
| Enfriamiento | 1 min | 50 → 0 |

**Criterios de aceptación (thresholds):**

- `http_req_duration` p(95) < 800 ms.
- `checks` > 95 %.

Las respuestas 400, 401 y 409 se marcan como esperadas (`http.expectedStatuses`), así que no cuentan como fallos de k6.

**Ejecución contra la nube:**

```bash
docker run --rm -i --user "$(id -u):$(id -g)" -v "$PWD/tests/stress:/scripts" grafana/k6 run \
  --summary-export /scripts/resultado-nube.json \
  -e BASE_URL=http://<ALB> -e TOKEN=$TOKEN /scripts/blacklist-stress.js
```

El token JWT se pasa por variable de entorno y nunca queda escrito en el script.

---

## 5. Resultados de k6 en la nube

Se hicieron dos ejecuciones idénticas de 10 minutos. La primera usó los umbrales de alerta iniciales y la segunda, los umbrales calibrados (sección 6.4).

| Métrica | Ejecución 1 | Ejecución 2 |
|---|---|---|
| Requests totales | 40 419 (67,3 req/s) | 40 557 (67,5 req/s) |
| Iteraciones | 7 777 | 7 807 |
| Checks exitosos | 99,98 % (5 fallos) | 99,98 % (7 fallos) |
| `http_req_duration` mínimo | 80,94 ms | 78,15 ms |
| Promedio | 208,27 ms | 206,94 ms |
| Mediana | 220,65 ms | 219,82 ms |
| p(90) | 310,03 ms | 310,17 ms |
| **p(95)** | **361,77 ms** ✓ | **361,82 ms** ✓ |
| Máximo | 580,54 ms | 577,21 ms |
| `http_req_failed` | 0,01 % (5) | 0,01 % (6) |

Ambos thresholds se cumplieron en las dos ejecuciones. Los resultados son prácticamente iguales (diferencias menores al 1 %), lo que muestra que el comportamiento del servicio bajo esta carga es **reproducible**. Los fallos inesperados se mantienen en el mismo orden (5–7 de ≈ 40 000) y se reparten entre distintos endpoints (`create`, `query`, `duplicate`, `no token`), así que no se concentran en una operación específica.

> 📷 *[Pantallazo: resumen de k6 en la nube]*

---

## 6. Análisis

### 6.1 Tiempos de respuesta del servicio y de la base de datos (20 %)

| Medición | Reposo | Carga pico (50 VUs) |
|---|---|---|
| Tiempo de transacción web (New Relic, promedio de la prueba) | ≈ 1 ms | ≈ 28 ms (promedio 21,75 ms) |
| Componente Postgres | ≈ 0 ms | ≈ 22 ms |
| Componente Python | ≈ 1 ms | ≈ 5–6 ms |
| Throughput | 0 rpm | ≈ 6 000 rpm (≈ 100 req/s) |

**Hallazgos:**

1. **La base de datos es el cuello de botella.** Con la carga pico, el tiempo atribuido a Postgres crece unas 20 veces, mientras que el de Python casi no cambia. La instancia `db.t3.micro` (2 vCPU con créditos de ráfaga, 1 GB de RAM) concentra la mayor parte del tiempo de cada transacción.
2. **El tiempo sigue la carga.** La curva de tiempo de respuesta replica las etapas de k6: sube en la rampa (10 → 50 VUs), se mantiene en el pico y vuelve a la línea base al terminar. No quedó degradación residual.
3. **Tiempo en servidor frente a tiempo de punta a punta.** New Relic mide ≈ 22 ms dentro de la aplicación, mientras que k6 mide 208 ms de promedio. La diferencia (≈ 180 ms) corresponde a la red entre el cliente y us-east-1 más el ALB. El mínimo de k6 (81 ms) es prácticamente la latencia de red base. En el entorno local, sin esa red, el promedio fue de 9 ms.
4. **Encolamiento en el pico.** La mediana de k6 (221 ms) queda por encima del promedio (208 ms), y el p95 llega a 362 ms. Esto indica que, con 50 usuarios, la tarea (1 worker de gunicorn con 4 hilos sobre 0,5 vCPU) empieza a encolar solicitudes.

> 📷 *[Pantallazo: Summary → Web transactions time]*
> 📷 *[Pantallazo: Transactions → endpoints ordenados por tiempo]*
> 📷 *[Pantallazo: Databases → operaciones SELECT / INSERT]*

**Recomendaciones:**

- Escalar la base de datos (`db.t4g.small` o superior) o agregar un índice/caché para la consulta por email.
- Aumentar `--workers` de gunicorn y la CPU de la tarea, o configurar auto scaling de ECS por CPU o por número de solicitudes del ALB.

### 6.2 Apdex (10 %)

New Relic calcula Apdex con un umbral **T = 0,5 s**:

- **Satisfecha:** tiempo ≤ T.
- **Tolerable:** tiempo ≤ 4T (2 s).
- **Frustrada:** tiempo > 4T o con error.

Apdex = (satisfechas + tolerables / 2) / total.

| Entorno | Apdex |
|---|---|
| Local (pruebas manuales con errores provocados) | 0,82 |
| Nube, prueba de estrés (promedio) | **0,98** |
| Nube, peor punto del pico | ≈ 0,97 |

**Hallazgos:**

- Durante toda la prueba el Apdex se mantuvo en la franja **excelente** (> 0,94). Los tiempos en servidor (≈ 28 ms en el pico) están muy por debajo de T, así que prácticamente todas las transacciones son *satisfechas*.
- La pequeña caída en el pico se explica por las transacciones con error, que New Relic cuenta como *frustradas* sin importar su tiempo, y no por lentitud.
- En local el Apdex fue más bajo (0,82) porque la muestra era pequeña y tenía una proporción alta de errores provocados a propósito.
- Por la diferencia de la sección 6.1, el Apdex del servidor no refleja la experiencia del usuario final: un usuario lejano de us-east-1 percibe ≈ 200–360 ms.

> 📷 *[Pantallazo: Summary → Apdex score]*

### 6.3 Errores (10 %)

| Fuente | Valor |
|---|---|
| New Relic, tasa de error promedio | 1,87 % |
| New Relic, tasa de error en el pico | ≈ 2 % |
| k6, fallos inesperados | 5 de 40 419 (ejecución 1) y 6 de 40 557 (ejecución 2), 0,01 % en ambas |

**Hallazgos:**

- La tasa de ≈ 2 % coincide con la proporción de solicitudes **sin token (401)** que genera el script (10 % de las iteraciones ≈ 1 de cada 52 requests). New Relic las registra como error porque la validación JWT las rechaza.
  *[Confirmar en Errors inbox qué códigos aparecen agrupados y su conteo]*
- Las respuestas **409** (duplicado) y **400** (body inválido) son respuestas controladas de la API y no aparecen como errores del agente.
  *[Confirmar en Errors inbox]*
- Los **fallos inesperados** de k6 (5 y 6 por ejecución) se repartieron entre `health`, `create`, `query`, `query missing`, `duplicate` y `no token`, lo que apunta a un problema transitorio de capacidad (saturación de la tarea o del ALB) y no a un endpoint específico.
  *[Completar con el código observado en Errors inbox / métricas 5XX del ALB]*
- Fuera de la prueba, la tasa de error vuelve a 0 %.

> 📷 *[Pantallazo: Summary → Errors]*
> 📷 *[Pantallazo: Errors inbox]*

### 6.4 Alertas (10 %)

Se creó la política **`blacklist-cloud-policy`** (agrupación: *One issue per condition*) con tres condiciones NRQL sobre `blacklist-service-cloud`. Las tres usan ventana de 1 minuto, *Event flow* y 2 minutos de retraso.

| Condición | Consulta NRQL | Umbral inicial | Umbral calibrado |
|---|---|---|---|
| Tiempo de respuesta p95 alto | `SELECT percentile(duration, 95) * 1000 FROM Transaction WHERE appName = 'blacklist-service-cloud'` | > 200 ms por 1 min | **> 20 ms** por 1 min |
| Tasa de errores alta | `SELECT percentage(count(*), WHERE error IS true) FROM Transaction WHERE appName = 'blacklist-service-cloud'` | > 5 % por 1 min | **> 1 %** por 1 min |
| Apdex bajo | `SELECT apdex(duration, t: 0.5) FROM Transaction WHERE appName = 'blacklist-service-cloud'` | < 0,85 por 1 min | < 0,85 por 1 min |

**Hallazgos:**

1. **Primera ejecución (umbrales iniciales): no se disparó ninguna alerta.** El p95 en servidor (≈ 30 ms), la tasa de error (≈ 2 %) y el Apdex (≈ 0,97) quedaron todos dentro de los límites. Los umbrales se habían fijado de forma genérica, sin una línea base del servicio.
2. **Calibración.** Con la línea base medida en reposo (≈ 1 ms, 0 % de errores) se ajustaron los umbrales para detectar la degradación observada bajo carga: p95 > 20 ms y errores > 1 %.
3. **Segunda ejecución (umbrales calibrados):** *[Completar: qué alertas pasaron a Active, a qué hora (minuto de la prueba) y cuándo se cerraron al terminar la carga]*.
4. **Lección:** un umbral solo sirve si está basado en el comportamiento medido del servicio. La alerta de p95 en servidor no detecta la latencia de red que percibe el usuario. Para eso se recomienda complementar con un monitor sintético de New Relic desde la región de los usuarios.

> 📷 *[Pantallazo: Alert Conditions de blacklist-cloud-policy]*
> 📷 *[Pantallazo: Issues & Activity con alertas en Active]*
> 📷 *[Pantallazo: Issues & Activity con alertas cerradas]*

---

## 7. Conclusiones

- La instrumentación con `newrelic-admin run-program` y variables de entorno permitió monitorear el servicio **sin modificar el código** y con la misma imagen Docker en local y en la nube. Solo cambia el nombre de la aplicación y la fuente de la llave (`.env` frente a SSM).
- El pipeline de CI/CD despliega la versión instrumentada a Fargate con blue/green, y New Relic reportó desde el primer despliegue.
- Bajo 50 usuarios concurrentes (≈ 100 req/s en el pico), el servicio cumplió los criterios de aceptación (p95 de 362 ms de punta a punta, 99,98 % de checks) con Apdex 0,98. El componente que más se degrada es **PostgreSQL**.
- Las alertas deben calibrarse con una línea base medida. Con umbrales genéricos, una degradación de 20 veces en el tiempo de la base de datos pasó desapercibida.

---

## 8. Seguridad de las credenciales

- `.env` está en `.gitignore`. La license key, la contraseña de la base de datos y la clave JWT nunca se versionan.
- En la nube, los tres secretos son parámetros **SecureString** de SSM (cifrados con `alias/aws/ssm`), inyectados por ECS en tiempo de arranque.
- El token JWT para k6 se pasa con `-e TOKEN=...` y no queda escrito en el script.
