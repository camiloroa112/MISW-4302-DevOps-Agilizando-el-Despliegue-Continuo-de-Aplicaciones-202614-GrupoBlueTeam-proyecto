# Proyecto 1 – Entrega 4: Monitoreo con New Relic

**Curso:** MISW-4302 DevOps – Agilizando el Despliegue Continuo de Aplicaciones
**Grupo:** Blue Team
**Servicio:** Microservicio de lista negra global de emails (`blacklist-service`)

La sustentación en video la pueden encontrar en el siguiente link: [VIDEO](URL_DEL_VIDEO)

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

Se creó una cuenta gratuita en New Relic. Para el agente se usa la llave de tipo **INGEST - LICENSE**, que se generó desde **API Keys → Create a key** con el nombre `blacklist-service`. La llave **no se versiona** en el repositorio:

- En local se carga desde el archivo `.env`, que está en `.gitignore`.
- En la nube se lee desde SSM Parameter Store.

#### Página API Keys con la llave INGEST - LICENSE, valor oculto
<img width="2553" height="812" alt="Página API Keys con la llave INGEST - LICENSE, valor oculto" src="https://github.com/user-attachments/assets/4f91e26d-4d00-4f27-960a-f64ec76c7ec0" />

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

El servicio **`blacklist-service-local`** apareció en **APM & Services** con datos de tiempo de respuesta, desglosados entre Python y Postgres, además de Apdex, throughput y errores:

| Métrica New Relic (local, Nov 22 20:30–21:20 UTC) | Valor |
|---|---|
| Tiempo de transacción web promedio | 5,36 ms (pico de 22 ms en la primera conexión a Postgres) |
| Apdex (T = 0,5 s) | 0,98 |
| Throughput | 15,32 rpm promedio (pico ≈ 550 rpm durante k6) |
| Error rate | 1,70 % promedio (pico durante las pruebas manuales de 409, 400 y 401) |

#### APM & Services → blacklist-service-local → Summary
<img width="2553" height="1204" alt="APM & Services → blacklist-service-local → Summary" src="https://github.com/user-attachments/assets/95966974-f590-4a00-a5cc-e190c3d03a41" />

#### Resumen de k6 local

```text
checks_succeeded...: 100.00% 750 out of 750
✓ health 200  ✓ create 201  ✓ query 200  ✓ query missing 200
✓ duplicate 409  ✓ invalid 400  ✓ no token 401
http_req_duration..: avg=9.02ms min=774.34µs med=8.29ms max=87.47ms p(90)=14.6ms p(95)=16.55ms
http_req_failed....: 0.00%  0 out of 750
http_reqs..........: 750    24.681467/s
```

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

**Ejecución evidenciada:** `7c31ef7c-7efa-4199-a13d-3014789099e9`, disparada automáticamente por el push a `main` del commit `c6763be4` (*Merge pull request #35 from camiloroa112/feature/new-relic-configuration*). Las etapas **Source**, **Build** y **Deploy** terminaron con éxito:

- **Build:** 23 pruebas unitarias de pytest aprobadas en 0,48 s, y reporte JUnit publicado en CodeBuild.
- **Deploy:** implementación de CodeDeploy `d-K4HCGD2ZM` (`blacklist-app` / `blacklist-dg`, `CodeDeployDefault.ECSAllAtOnce`). Pasó por los 4 pasos (crear el conjunto de tareas de sustitución → redirigir el 100 % del tráfico → esperar → terminar el conjunto original). Todos los eventos del ciclo de vida (`BeforeInstall` … `AfterAllowTraffic`) terminaron bien; `Install` tomó 1 min 42 s.

Verificación: `GET http://<ALB>/health` → `{"status": "ok"}`. El servicio **`blacklist-service-cloud`** reporta en New Relic APM.

#### CodePipeline con las 3 etapas en verde
<img width="2540" height="1078" alt="CodePipeline con las 3 etapas en verde" src="https://github.com/user-attachments/assets/75eac681-f234-4ba2-aa0b-52ad1a3a089a" />

#### CodeBuild → Informes de pytest
<img width="858" height="521" alt="CodeBuild → Informes de pytest" src="https://github.com/user-attachments/assets/6bf8c6bf-6db2-485a-9817-d5377e6f6850" />

#### CodeDeploy → implementación blue/green completada
<img width="1472" height="1341" alt="CodeDeploy → implementación blue/green completada" src="https://github.com/user-attachments/assets/c140da17-8e3c-4776-8dc9-70558c69edc3" />

#### APM & Services → blacklist-service-cloud
<img width="2260" height="1137" alt="APM & Services → blacklist-service-cloud" src="https://github.com/user-attachments/assets/01bfd563-6b3d-4c32-b910-9bbcf5290732" />

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

#### Resumen de k6 en la nube (ejecución 2)
<img width="1330" height="1005" alt="Resumen de k6 en la nube" src="https://github.com/user-attachments/assets/92b876ba-5f8d-40a2-8d9d-3b305e64980d" />

---

## 6. Análisis

### 6.1 Tiempos de respuesta del servicio y de la base de datos (20 %)

| Medición | Reposo | Carga pico (50 VUs) |
|---|---|---|
| Tiempo de transacción web (New Relic) | ≈ 1 ms | ≈ 28–29 ms (promedio 21,75 ms en la ejecución 1 y 21,30 ms en la ejecución 2) |
| Componente Postgres | ≈ 0 ms | ≈ 22 ms |
| Componente Python | ≈ 1 ms | ≈ 5–6 ms |
| Throughput | 0 rpm | ≈ 6 000–6 200 rpm (≈ 100 req/s) |

**Tiempo por endpoint (Transactions, ejecución 2):**

| Transacción | Tiempo promedio | Tasa de error |
|---|---|---|
| `blacklist_query:BlacklistQueryResource` (GET) | 25,9 ms | 4,38 % |
| `blacklist_create:BlacklistCreateResource` (POST) | 25,2 ms | 0 % |
| `health:HealthResource` | 4,21 ms | 0 % |
| `Flask.handle_http_exception` | 1,49 ms | 0 % |

**Operaciones de base de datos (Databases, % del tiempo total en BD):**

| Operación | % del tiempo |
|---|---|
| Postgres `rollback` | 31,1 % |
| Postgres `blacklist select` | 29,46 % |
| Postgres `blacklist insert` | 28,7 % |
| Postgres `commit` | 10,74 % |

**Hallazgos:**

1. **La base de datos es el cuello de botella.** Con la carga pico, el tiempo atribuido a Postgres crece unas 20 veces (de ≈ 1–2 ms a ≈ 22 ms), mientras que el de Python casi no cambia. La instancia `db.t3.micro` (2 vCPU con créditos de ráfaga, 1 GB de RAM) concentra la mayor parte del tiempo de cada transacción.
2. **El tiempo sigue la carga.** La curva de tiempo de respuesta replica las etapas de k6: sube en la rampa (10 → 50 VUs), se mantiene en el pico y vuelve a la línea base al terminar. No quedó degradación residual.
3. **Tiempo en servidor frente a tiempo de punta a punta.** New Relic mide ≈ 22 ms dentro de la aplicación, mientras que k6 mide 207–208 ms de promedio. La diferencia (≈ 180 ms) corresponde a la red entre el cliente y us-east-1 más el ALB. El mínimo de k6 (≈ 80 ms) es prácticamente la latencia de red base. En el entorno local, sin esa red, el promedio fue de 9 ms.
4. **Los endpoints que tocan la BD son ≈ 6 veces más lentos que `/health`.** Consulta y creación tardan ≈ 25 ms frente a 4,21 ms de `/health`, que no usa base de datos. Esa diferencia es el costo del acceso a Postgres bajo carga.
5. **El `rollback` es la operación que más tiempo consume en la BD (31,1 %), por encima del `select` y del `insert`.** Hay dos fuentes probables:
   - el cierre de la sesión de SQLAlchemy al final de cada request, que hace rollback incluso en las consultas de solo lectura;
   - el `INSERT` duplicado que termina en `IntegrityError` → rollback → 409.

   Es una oportunidad de optimización: validar el duplicado antes del `INSERT` y evitar transacciones innecesarias en las lecturas.
6. **Encolamiento en el pico.** La mediana de k6 (≈ 220 ms) queda por encima del promedio (≈ 207 ms), y el p95 llega a 362 ms. Esto indica que, con 50 usuarios, la tarea (1 worker de gunicorn con 4 hilos sobre 0,5 vCPU) empieza a encolar solicitudes.

#### Summary → Web transactions time
<img width="1284" height="508" alt="Summary → Web transactions time" src="https://github.com/user-attachments/assets/0a67dc52-90b0-431b-87f1-2bbda931bd25" />

#### Transactions → endpoints ordenados por tiempo
<img width="1890" height="366" alt="Transactions → endpoints ordenados por tiempo" src="https://github.com/user-attachments/assets/04b7e41f-4efd-4cb6-80b0-ec701311e229" />

#### Databases → operaciones de Postgres
<img width="588" height="376" alt="Databases → operaciones de Postgres" src="https://github.com/user-attachments/assets/f5fa649f-4471-453b-a35e-a019294dcd98" />

**Recomendaciones:**

- Escalar la base de datos (`db.t4g.small` o superior) o agregar un índice/caché para la consulta por email.
- Reducir los rollbacks: validar duplicados antes del `INSERT` y no abrir transacciones en las lecturas.
- Aumentar `--workers` de gunicorn y la CPU de la tarea, o configurar auto scaling de ECS por CPU o por número de solicitudes del ALB.

### 6.2 Apdex (10 %)

New Relic calcula Apdex con un umbral **T = 0,5 s**:

- **Satisfecha:** tiempo ≤ T.
- **Tolerable:** tiempo ≤ 4T (2 s).
- **Frustrada:** tiempo > 4T o con error.

Apdex = (satisfechas + tolerables / 2) / total.

| Entorno | Apdex |
|---|---|
| Local (ventana completa de pruebas) | 0,98 |
| Local (solo los primeros minutos, con errores provocados) | 0,82 |
| Nube, prueba de estrés (promedio) | **0,98** |
| Nube, peor punto del pico | ≈ 0,97 |

**Hallazgos:**

- Durante toda la prueba el Apdex se mantuvo en la franja **excelente** (> 0,94). Los tiempos en servidor (≈ 29 ms en el pico) están muy por debajo de T, así que prácticamente todas las transacciones son *satisfechas*.
- La pequeña caída en el pico se explica por las transacciones con error (los 401), que New Relic cuenta como *frustradas* sin importar su tiempo, y no por lentitud.
- En local el Apdex bajó a 0,82 solo durante los primeros minutos, porque la muestra era pequeña y tenía una proporción alta de errores provocados a propósito. En la ventana completa fue de 0,98.
- Por la diferencia de la sección 6.1, el Apdex del servidor no refleja la experiencia del usuario final: un usuario lejano de us-east-1 percibe ≈ 200–360 ms.

#### Summary → Apdex score
<img width="629" height="486" alt="Summary → Apdex score" src="https://github.com/user-attachments/assets/f831b789-a054-486b-af45-b52a5e19544d" />

### 6.3 Errores (10 %)

| Fuente | Valor |
|---|---|
| New Relic, tasa de error promedio | 1,87 % (ejecución 1) y 1,75 % (ejecución 2) |
| New Relic, tasa de error en el pico | ≈ 2–2,5 % |
| New Relic, tasa de error de `BlacklistQueryResource` | 4,38 % |
| k6, fallos inesperados | 5 de 40 419 (ejecución 1) y 6 de 40 557 (ejecución 2), 0,01 % en ambas |

**Hallazgos:**

- La tasa de ≈ 2 % coincide con la proporción de solicitudes **sin token (401)** que genera el script (10 % de las iteraciones ≈ 1 de cada 52 requests).
- El desglose por transacción lo confirma: **todos los errores están en `BlacklistQueryResource` (4,38 %)**, que es donde el script envía el request sin token. Ese recurso recibe ≈ 2,1 requests por iteración (consulta existente, consulta inexistente y el 10 % sin token), y 0,1 / 2,1 ≈ 4,8 %, cercano al 4,38 % medido.
- **Errors inbox** muestra un único grupo de error sin resolver: **`flask_jwt_extended.exceptions.NoAuthorizationError` – "Missing Authorization Header"**. Sus atributos lo identifican sin ambigüedad: `http.statusCode = 401`, `request.method = GET`, `request.uri = /blacklists/stress.…@example.com`, `request.headers.userAgent = Grafana k6/2.4.0` y transacción `blacklist_query:BlacklistQueryResource`. El stack trace llega hasta `flask_jwt_extended/view_decorators.py` (`_decode_jwt_from_request`). La gráfica de ocurrencias muestra dos bloques, uno por cada ejecución de la prueba. Errors inbox guarda una muestra de las ocurrencias, mientras que la tasa de error se calcula sobre todas las transacciones.
- `BlacklistCreateResource` tiene **0 % de error** aunque devuelve 409 en cada iteración y 400 en el 10 %. Son respuestas controladas de la API, devueltas como respuesta normal y no como excepción, así que el agente no las cuenta como error.
- Los **fallos inesperados** de k6 (5 y 6 por ejecución) se repartieron entre `health`, `create`, `query`, `query missing`, `duplicate` y `no token`, así que no se concentran en un endpoint. Ninguno aparece como error de la aplicación en Errors inbox, donde el único grupo es el 401. Por eso, lo más probable es que ocurrieran **antes de llegar al contenedor**: cortes de conexión o respuestas del ALB/red durante el pico, y no excepciones del código. Con 6 casos de ≈ 40 000 (0,01 %), su impacto es despreciable. Para confirmarlo habría que revisar las métricas `HTTPCode_ELB_5XX` y `TargetConnectionErrorCount` del ALB en CloudWatch.
- Fuera de la prueba, la tasa de error vuelve a 0 %.

#### Summary → Errors
<img width="946" height="328" alt="Summary → Errors" src="https://github.com/user-attachments/assets/44e07c49-dc60-4079-a787-cbd5d0fe69ac" />

#### Errors inbox
<img width="977" height="1610" alt="Errors inbox" src="https://github.com/user-attachments/assets/ab8d054c-55ab-4e35-acdd-806a8e6ebcbb" />

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
3. **Segunda ejecución (umbrales calibrados): se dispararon dos alertas críticas** (horas en UTC, según New Relic):

   | Condición | Disparo | Abierta | Cerrada | Duración |
   |---|---|---|---|---|
   | Tasa de errores alta | error rate > 1 % durante 1 min | ≈ 5:21 | 5:31 | 10 min |
   | Tiempo de respuesta p95 alto | p95 > 20 ms durante 1 min | 5:26 | 5:31 | 5 min |
   | Apdex bajo | No se disparó (Apdex mínimo ≈ 0,97) | — | — | — |

   Las dos incidencias tienen prioridad **Critical** y quedaron en estado **Closed** en *Issues & Activity*. La de errores se abrió primero porque los 401 aparecen desde los 10 usuarios virtuales. La de tiempo de respuesta se abrió solo cuando la carga se acercó a 50 usuarios virtuales y Postgres pasó de ≈ 2 ms a ≈ 22 ms.

   Las bandas rojas de *Critical alerts* en las gráficas de New Relic (≈ 5:21–5:32) coinciden con la rampa y el pico de 50 usuarios virtuales, y el *Activity stream* del servicio registra los eventos **Critical Issue Activated** y **Critical Issue Closed**. Las dos incidencias se **cerraron solas** cuando la carga bajó y las métricas volvieron a la línea base. Esto demuestra el ciclo completo: detección, incidencia abierta y resolución automática.
4. **Lección:** un umbral solo sirve si está basado en el comportamiento medido del servicio. La alerta de p95 en servidor no detecta la latencia de red que percibe el usuario. Para eso se recomienda complementar con un monitor sintético de New Relic desde la región de los usuarios.

#### Alert Conditions de blacklist-cloud-policy
<img width="2262" height="668" alt="Alert Conditions de blacklist-cloud-policy" src="https://github.com/user-attachments/assets/f1ce8642-095a-4998-9807-e966ad303182" />

#### Issues & Activity con alertas en Active
<img width="2244" height="788" alt="Issues & Activity con alertas en Active" src="https://github.com/user-attachments/assets/ec4d4934-162b-4c29-8582-ce675481fb78" />

#### Issues & Activity con alertas cerradas
<img width="2248" height="788" alt="Issues & Activity con alertas cerradas" src="https://github.com/user-attachments/assets/6d4144e0-7fc5-42ac-ae37-f5a6c7f2611c" />

---

## 7. Conclusiones

- La instrumentación con `newrelic-admin run-program` y variables de entorno permitió monitorear el servicio **sin modificar el código** y con la misma imagen Docker en local y en la nube. Solo cambia el nombre de la aplicación y la fuente de la llave (`.env` frente a SSM).
- El pipeline de CI/CD despliega la versión instrumentada a Fargate con blue/green, y New Relic reportó desde el primer despliegue.
- Bajo 50 usuarios concurrentes (≈ 100 req/s en el pico), el servicio cumplió los criterios de aceptación (p95 de 362 ms de punta a punta, 99,98 % de checks) con Apdex 0,98. El componente que más se degrada es **PostgreSQL**, y dentro de él, el `rollback` es la operación más costosa.
- Los únicos errores de la aplicación son los 401 provocados a propósito por la prueba. Los 400 y 409 son respuestas controladas que el agente no cuenta como error.
- Las alertas deben calibrarse con una línea base medida. Con umbrales genéricos, una degradación de 20 veces en el tiempo de la base de datos pasó desapercibida. Con umbrales calibrados, las dos alertas se abrieron durante el pico y se cerraron solas al terminar la carga.

---

## 8. Seguridad de las credenciales

- `.env` está en `.gitignore`. La license key, la contraseña de la base de datos y la clave JWT nunca se versionan.
- En la nube, los tres secretos son parámetros **SecureString** de SSM (cifrados con `alias/aws/ssm`), inyectados por ECS en tiempo de arranque.
- El token JWT para k6 se pasa con `-e TOKEN=...` y no queda escrito en el script.
