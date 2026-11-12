# Blacklist Service - Grupo Blue Team - Entrega 1

Microservicio REST que gestiona la lista negra global de emails de la organización. Permite agregar emails a la lista negra y consultar si un email se encuentra bloqueado.

La sustentación en video la pueden encontrar en el siguiente link: [VIDEO](https://youtu.be/NcRHI7uS3iY)

Proyecto del curso MISW-4302 DevOps: Agilizando el Despliegue Continuo de Aplicaciones - Universidad de los Andes. El enunciado completo está en [`main/README.md`](https://github.com/camiloroa112/MISW-4302-DevOps-Agilizando-el-Despliegue-Continuo-de-Aplicaciones-202614-GrupoBlueTeam-proyecto/blob/main/README.md).

## Tabla de Contenido

- [Integrantes - Grupo Blue Team](#integrantes---grupo-blue-team)
- [Stack](#stack)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Requisitos](#requisitos)
- [Configuración](#configuración)
- [Ejecución local](#ejecución-local)
- [Token de autorización](#token-de-autorización)
- [Pruebas](#pruebas)
- [API](#api)
  - [`POST /blacklists`](#post-blacklists)
  - [`GET /blacklists/<email>`](#get-blacklistsemail)
  - [`GET /health`](#get-health)
- [Postman](#postman)
- [Despliegue en AWS](#despliegue-en-aws)
  - [Paquete de despliegue](#paquete-de-despliegue)
  - [Paso a paso de la configuración](#paso-a-paso-de-la-configuración)
    - [1. EC2 → Grupo de seguridad de la aplicación](#1-ec2--grupo-de-seguridad-de-la-aplicación)
    - [2. RDS → Base de datos PostgreSQL](#2-rds--base-de-datos-postgresql)
    - [3. EC2 → Regla de entrada de `blacklist-rds-sg`](#3-ec2--regla-de-entrada-de-blacklist-rds-sg)
    - [4. Elastic Beanstalk → Aplicación y entorno](#4-elastic-beanstalk--aplicación-y-entorno)
    - [5. Health check](#5-health-check)
    - [6. Validación](#6-validación)
  - [Lecciones del despliegue](#lecciones-del-despliegue)
  - [Estrategias de despliegue](#estrategias-de-despliegue)
    - [All at once](#all-at-once)
    - [Rolling](#rolling)
    - [Rolling with additional batch](#rolling-with-additional-batch)
    - [Immutable](#immutable)
    - [Comparación](#comparación)
- [Flujo de trabajo con Git](#flujo-de-trabajo-con-git)

## Integrantes - Grupo Blue Team

| Integrante | Correo Uniandes | Usuario GitHub |
|---|---|---|
| Carlos Ortiz | cd.ortiz@uniandes.edu.co | [cdof00](https://github.com/cdof00) |
| Camilo Roa | ca.roac@uniandes.edu.co | [camiloroa112](https://github.com/camiloroa112) |
| Joseph Gutiérrez | jm.gutierrez23@uniandes.edu.co | [josephgutierrez23](https://github.com/josephgutierrez23) |
| Steven Garzón | sr.garzon@uniandes.edu.co | [stevengr7](https://github.com/stevengr7) |

[← Volver al inicio](#tabla-de-contenido)

## Stack

Python 3.12 · Flask · Flask-SQLAlchemy · Flask-RESTful · Flask-Marshmallow · Flask-JWT-Extended · PostgreSQL · Gunicorn · Docker · AWS Elastic Beanstalk · AWS RDS

[← Volver al inicio](#tabla-de-contenido)

## Estructura del proyecto

```
├── application.py              # Punto de entrada WSGI
├── app/
│   ├── __init__.py             # create_app()
│   ├── auth.py                 # Respuestas 401 unificadas
│   ├── config.py               # Configuración desde variables de entorno
│   ├── extensions.py           # Instancias de db, ma y jwt
│   ├── models.py               # Tabla blacklist
│   ├── schemas.py              # Validación y normalización del email
│   └── resources/
│       ├── health.py           # GET /health
│       ├── blacklist_create.py # POST /blacklists
│       └── blacklist_query.py  # GET /blacklists/<email>
├── scripts/
│   └── generate_token.py       # Genera el token JWT estático
├── tests/                      # Pruebas con pytest
├── postman/                    # Colección de Postman
├── docs/                       # Enunciado y documentación de las entregas
├── .ebextensions/              # Configuración de Elastic Beanstalk
├── .env.example                # Plantilla de variables de entorno
├── .dockerignore
├── Dockerfile
├── pyproject.toml
└── uv.lock
```

[← Volver al inicio](#tabla-de-contenido)

## Requisitos

- [uv](https://docs.astral.sh/uv/)
- Docker

[← Volver al inicio](#tabla-de-contenido)

## Configuración

Copia la plantilla y completa los valores:

```bash
cp .env.example .env
```

| Variable | Descripción |
|---|---|
| `DB_HOST` | Host de PostgreSQL |
| `DB_PORT` | Puerto de PostgreSQL (por defecto `5432`) |
| `DB_NAME` | Nombre de la base de datos |
| `DB_USER` | Usuario de la base de datos |
| `DB_PASSWORD` | Contraseña de la base de datos |
| `JWT_SECRET_KEY` | Clave para firmar y validar tokens |

Para generar `JWT_SECRET_KEY`:

```bash
uv run python -c "import secrets; print(secrets.token_hex(32))"
```

**Nunca subas `.env` al repositorio.** Usa una clave distinta para cada entorno (local y AWS).

[← Volver al inicio](#tabla-de-contenido)

## Ejecución local

**1. PostgreSQL en Docker**, accesible solo desde tu máquina. Toma la contraseña de tu `.env`:

```bash
docker run --name blacklist-db -e POSTGRES_PASSWORD="$(grep '^DB_PASSWORD=' .env | cut -d= -f2-)" -e POSTGRES_DB=blacklist -p 127.0.0.1:5432:5432 -d postgres:16
```

**2. Dependencias:**

```bash
uv sync
```

**3. La aplicación**, con Flask en modo desarrollo (puerto 5000):

```bash
uv run flask --app application run --debug
```

O con Docker, igual que en AWS (puerto 8000):

```bash
docker build -t blacklist-service .
docker run --rm --network host --env-file .env blacklist-service
```

En macOS o Windows, `--network host` no llega a `localhost`; usa `DB_HOST=host.docker.internal` en tu `.env`.

La tabla se crea automáticamente al iniciar la aplicación.

[← Volver al inicio](#tabla-de-contenido)

## Token de autorización

```bash
uv run python -m scripts.generate_token
```

El token no expira y solo es válido para el `JWT_SECRET_KEY` con el que se generó. Para generar el token de AWS, pasa la clave de producción entre comillas:

```bash
JWT_SECRET_KEY="clave-de-produccion" uv run python -m scripts.generate_token
```

Se envía en el header `Authorization: Bearer <token>`.

[← Volver al inicio](#tabla-de-contenido)

## Pruebas

```bash
uv run pytest -v
```

Las pruebas usan SQLite en memoria; no requieren PostgreSQL ni `.env`.

[← Volver al inicio](#tabla-de-contenido)

## API

Todas las respuestas son JSON. Los endpoints de negocio requieren `Authorization: Bearer <token>`.

### `POST /blacklists`

Agrega un email a la lista negra global. El servidor registra la IP de origen (tomada de `X-Forwarded-For` detrás del balanceador) y la fecha/hora UTC de la solicitud.

| Campo | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `email` | String | Sí | Formato válido, máximo 254 caracteres; se normaliza a minúsculas |
| `app_uuid` | String | Sí | UUID válido |
| `blocked_reason` | String | No | Máximo 255 caracteres |

Ejemplo de solicitud:

```json
{
  "email": "cliente@example.com",
  "app_uuid": "6f9619ff-8b86-d011-b42d-00cf4fc964ff",
  "blocked_reason": "Compliance request"
}
```

| Código | Caso | Respuesta |
|---|---|---|
| 201 | Creado | `{"msg": "Email added to the global blacklist"}` |
| 400 | Datos inválidos o campos no permitidos | `{"msg": "Invalid request", "errors": {...}}` |
| 401 | Token ausente o inválido | `{"msg": "Missing or invalid token"}` |
| 409 | El email ya existe (sin distinguir mayúsculas) | `{"msg": "Email already blacklisted"}` |

[← Volver al inicio](#tabla-de-contenido)

### `GET /blacklists/<email>`

Consulta si un email está en la lista negra global. El email se envía como parámetro de la URL y se normaliza a minúsculas antes de consultar la base de datos.

| Parámetro | Tipo | Obligatorio | Regla |
|---|---|---|---|
| `email` | String (path) | Sí | Formato válido, máximo 254 caracteres |

Ejemplo de solicitud:

```http
GET /blacklists/cliente@example.com
Authorization: Bearer <token>
```

Ejemplo de respuesta cuando el email **está bloqueado**:

```json
{
  "email": "cliente@example.com",
  "is_blacklisted": true,
  "blocked_reason": "Compliance request"
}
```

Ejemplo de respuesta cuando el email **no está bloqueado**:

```json
{
  "email": "cliente@example.com",
  "is_blacklisted": false,
  "blocked_reason": null
}
```

| Código | Caso | Respuesta |
|---|---|---|
| 200 | Está bloqueado | `{"email": "...", "is_blacklisted": true, "blocked_reason": "..."}` |
| 200 | No está bloqueado | `{"email": "...", "is_blacklisted": false, "blocked_reason": null}` |
| 400 | Email con formato inválido | `{"msg": "Invalid request", "errors": {"email": [...]}}` |
| 401 | Token ausente o inválido | `{"msg": "Missing or invalid token"}` |

[← Volver al inicio](#tabla-de-contenido)

### `GET /health`

Health check para Elastic Beanstalk. No requiere token. Responde `{"status": "ok"}`.

[← Volver al inicio](#tabla-de-contenido)

## Postman

La colección **Blacklist API - Grupo Blue Team** reúne todos los escenarios de prueba en un solo lugar:

| Carpeta | Escenarios |
|---|---|
| `GET /health` | 200 sin token |
| `POST /blacklists` | 201 válido, 409 duplicado con otra capitalización, 201 sin motivo, 400 sin email, 400 sin `app_uuid`, 400 UUID inválido, 400 email inválido, 400 motivo de 256 caracteres, 400 campo no permitido, 401 sin token, 401 token inválido |
| `GET /blacklists/<email>` | 200 email en la lista (`true`), 200 email fuera de la lista (`false`), 400 email inválido, 401 sin token, 401 token inválido |

- **Documentación publicada:** [Blacklist API - Grupo Blue Team](https://documenter.getpostman.com/view/49240404/2sBYHSy162)
- **Colección en línea:** [Workspace BlueTeam_DevOps](https://www.postman.com/cd-ortiz-4891041/workspace/blueteam-devops/collection/49240404-3bfa60c1-f5d3-43ae-97cd-8386f5147838?action=share&creator=49240404)
- **Archivo de la colección:** [`postman/`](../../postman/)

Para ejecutarla:

1. **Import** del archivo `.json` en Postman (o **Run in Postman** desde la documentación publicada).
2. En la colección → **Variables**, completa el **Current value** de:
   - `base_url`: `http://blacklist-service-env.eba-vezsut9e.us-east-2.elasticbeanstalk.com` (con `http://` y sin `/` al final).
   - `token`: el token JWT fijo, generado con la clave de producción.

   No uses **Initial value**: se sincroniza con el workspace y aparece en la documentación publicada.
3. **Run collection**, en orden: el primer escenario del GET consulta el email creado por el POST.

Los escenarios de creación generan un email único en cada ejecución, así que la colección puede correrse varias veces.

[← Volver al inicio](#tabla-de-contenido)

## Despliegue en AWS

Despliegue manual en Elastic Beanstalk, plataforma **Docker running on 64bit Amazon Linux 2023**, con PostgreSQL en RDS.

[← Volver al inicio](#tabla-de-contenido)

### Paquete de despliegue

```bash
git archive --format=zip -o blacklist-vN.zip HEAD
```

Solo incluye archivos versionados, así que `.env` y `.venv` nunca se cuelan.

[← Volver al inicio](#tabla-de-contenido)

### Paso a paso de la configuración

Todos los recursos se crean en la **VPC predeterminada** de una misma región. El orden importa: primero los security groups y RDS, y al final Beanstalk.

La configuración se validó primero en un despliegue de prueba en **us-east-1** (de donde provienen las capturas de esta sección). El entorno oficial, sobre el que se ejecutaron las estrategias de despliegue, está en **us-east-2** con la misma configuración.

#### 1. EC2 → Grupo de seguridad de la aplicación

*EC2 → Red y seguridad → Grupos de seguridad → Crear grupo de seguridad*

| Opción | Valor |
|---|---|
| Nombre | `blacklist-app-sg` |
| Descripción | `Beanstalk instances of blacklist-service, allowed by RDS` (sin tildes ni ñ) |
| VPC | Predeterminada |
| Reglas de entrada | Ninguna (Beanstalk agrega las del balanceador) |
| Reglas de salida | Todo el tráfico a `0.0.0.0/0` (por defecto) |

Este grupo identifica a las instancias de Beanstalk para que RDS solo acepte conexiones desde ellas.

<img width="1916" height="960" alt="01_ec2_crear_blacklist-app-sg" src="https://github.com/user-attachments/assets/e86f8604-6471-43fc-8dbe-3b8f41025d74" />

[← Volver al inicio](#tabla-de-contenido)

#### 2. RDS → Base de datos PostgreSQL

*Aurora and RDS → Bases de datos → Crear base de datos → **Configuración completa***

| Sección | Opción | Valor |
|---|---|---|
| Opciones del motor | Tipo de motor | PostgreSQL |
| Plantillas | Plantilla | **Entorno de pruebas** |
| Disponibilidad | Implementación | Instancia única (Single-AZ) |
| Configuración | Identificador | `blacklist-db` |
| Credenciales | Usuario maestro | `blacklist_admin` |
| Credenciales | Administración | Autoadministrado (contraseña propia) |
| Instancia | Clase | `db.t4g.micro` |
| Almacenamiento | Tipo / tamaño | SSD de uso general (gp3), 20 GiB, sin escalado automático |
| Conectividad | Recurso de computación | No se conecte a un recurso informático EC2 |
| Conectividad | VPC | Predeterminada |
| Conectividad | Acceso público | No |
| Conectividad | Grupo de seguridad | Crear nuevo: `blacklist-rds-sg` |
| Supervisión | Database Insights | Estándar (7 días, gratis); monitorización mejorada y DevOps Guru desactivados |
| Configuración adicional | **Nombre de base de datos inicial** | `blacklist` |
| Configuración adicional | Cifrado / copias de seguridad | Activado / 1 día |
| Configuración adicional | Protección contra eliminación | Desactivada |

La base creada (`db.t4g.micro`, grupo `blacklist-rds-sg` y `dbname=blacklist` en los pasos de conexión):

<img width="1690" height="933" alt="09_rds_conectividad_y_seguridad" src="https://github.com/user-attachments/assets/a1bfa204-7c5d-4e31-81e8-985bb0a9f1a7" />

[← Volver al inicio](#tabla-de-contenido)

#### 3. EC2 → Regla de entrada de `blacklist-rds-sg`

RDS crea por defecto una regla con la IP de quien crea la base (visible en la captura anterior). Se **eliminó** y se creó una nueva:

| Tipo | Protocolo | Puerto | Origen |
|---|---|---|---|
| PostgreSQL | TCP | 5432 | `blacklist-app-sg` |

Así, la base de datos no es accesible desde internet y solo recibe conexiones de las instancias de la aplicación.

<!-- Subir aquí la captura 10_ec2_grupos_de_seguridad_final.png -->

[← Volver al inicio](#tabla-de-contenido)

#### 4. Elastic Beanstalk → Aplicación y entorno

*Elastic Beanstalk → Crear aplicación*

| Sección | Opción | Valor |
|---|---|---|
| Entorno | Nivel | Entorno de servidor web |
| Entorno | Aplicación / entorno | `blacklist-service` / `blacklist-service-env` |
| Plataforma | Plataforma | Docker, *Docker running on 64bit Amazon Linux 2023* |
| Código | Origen | Archivo local: `blacklist-vN.zip` (generado con `git archive`) |
| Acceso al servicio | Rol de servicio | `aws-elasticbeanstalk-service-role` |
| Acceso al servicio | Perfil de instancia EC2 | `aws-elasticbeanstalk-ec2-role` |
| Infraestructura | Tipo de entorno | **Equilibrio de carga** |
| Infraestructura | Instancias | Mínimo 3, máximo 6 |
| Infraestructura | Tipo de instancia | `t3.micro` |
| Redes | Subredes de instancia | Todas las subredes públicas de la VPC |
| Redes | Grupos de seguridad de EC2 | `blacklist-app-sg` |
| Balanceador | Tipo | Application Load Balancer, dedicado, público |
| Balanceador | Agente de escucha | HTTP, puerto 80 |
| Balanceador | **Subredes del balanceador** | Las **mismas** que las de las instancias |
| Supervisión | Informes de estado | Mejorados |
| Actualizaciones | Actualizaciones administradas | Desactivadas |
| Implementaciones | Política | Según la estrategia que se pruebe (ver [Estrategias de despliegue](#estrategias-de-despliegue)) |
| Propiedades de entorno | Variables (texto sin formato) | `DB_HOST` (endpoint de RDS), `DB_PORT=5432`, `DB_NAME=blacklist`, `DB_USER`, `DB_PASSWORD`, `JWT_SECRET_KEY` |

El proxy nginx de Beanstalk recibe el tráfico del balanceador en el puerto 80 y lo reenvía al contenedor, que expone gunicorn en el puerto 8000.

Entorno, plataforma, código y variables de entorno (valores sensibles ocultos):

<img width="1094" height="930" alt="11_beanstalk_entorno_plataforma_variables" src="https://github.com/user-attachments/assets/3342001f-b49f-42cb-a79b-87954f27ce2b" />

Resumen del entorno `blacklist-service-env` desplegado:

<img width="1653" height="738" alt="Resumen del entorno blacklist-service-env" src="https://github.com/user-attachments/assets/ca327dea-0cff-4f51-8b0a-0a50b4b253e6" />

[← Volver al inicio](#tabla-de-contenido)

#### 5. Health check

| Opción | Valor |
|---|---|
| Ruta | `/health` (sin token) |
| Código esperado | 200 |
| Intervalo / tiempo de espera | 15 s / 5 s |
| Umbral de buen estado / mal estado | 3 / 5 |
| Demora en la anulación del registro | 20 s |

La ruta se configura en *Proceso: default → Comprobación de estado* y también en [`.ebextensions/healthcheck.config`](../../.ebextensions/healthcheck.config). El valor de la consola tiene prioridad, por eso se fijó explícitamente en ambos lugares.

<img width="1094" height="912" alt="14_beanstalk_health_check_proceso_default" src="https://github.com/user-attachments/assets/08911bf1-e7e2-4fca-bcbc-fb367d1d43e3" />

[← Volver al inicio](#tabla-de-contenido)

#### 6. Validación

```bash
curl http://blacklist-service-env.eba-vezsut9e.us-east-2.elasticbeanstalk.com/health
```

Responde `{"status": "ok"}`. Después se ejecuta la [colección de Postman](#postman) contra la misma URL.

[← Volver al inicio](#tabla-de-contenido)

### Lecciones del despliegue

- **Plantilla de RDS:** la plantilla *Producción* configura almacenamiento `io2` con IOPS provisionadas (unos 300 USD al mes). Usar *Entorno de pruebas* con gp3.
- **Regla de entrada de RDS:** RDS crea una regla con la IP de quien crea la base. Hay que eliminarla y crear una nueva con origen `blacklist-app-sg`; una regla por IP no se puede convertir en una que apunte a un security group.
- **Ruta del health check:** lo configurado en la consola tiene prioridad sobre `.ebextensions`. Si la consola deja `/`, el balanceador marca las instancias como no saludables.
- **Subredes:** el balanceador debe tener las **mismas subredes** que las instancias. Una instancia en una zona sin subred del balanceador queda en estado *Unused* y la API responde 503, aunque la aplicación esté funcionando.
- **URL:** el balanceador escucha en HTTP (puerto 80). Usar `http://`, sin `/` al final.

[← Volver al inicio](#tabla-de-contenido)

### Estrategias de despliegue

La configuración del grupo de Auto Scaling es de **3 a 6 instancias**, como recomienda el enunciado. En todas las estrategias se usaron 3 instancias, el límite inferior de esa configuración. Cada despliegue se validó con los eventos de Elastic Beanstalk y su historial de despliegues, que muestran la hora exacta de inicio, la estrategia usada y la duración.

#### All at once

En esta estrategia, Elastic Beanstalk detiene todas las instancias activas, las actualiza y las vuelve a levantar. Esto produce una caída del servicio que dura lo mismo que el despliegue y el arranque de las instancias.

- **Instancias:** 3.
- **Tiempo de despliegue:** 28 segundos.
- **Instancias usadas:** las mismas que ya estaban activas; se comprobó comparando los ID de las instancias en EC2 antes y después.

Tiempo de despliegue:

<img width="1653" height="738" alt="image" src="https://github.com/user-attachments/assets/ca327dea-0cff-4f51-8b0a-0a50b4b253e6" />

Instancias activas en EC2 antes del despliegue:

<img width="577" height="234" alt="image" src="https://github.com/user-attachments/assets/7a090656-4953-49cc-b722-29532711049d" />

Instancias activas en EC2 después del despliegue:

<img width="562" height="250" alt="image" src="https://github.com/user-attachments/assets/a929ca8a-81c2-4cef-a56a-e033af5018ff" />

**Hallazgos:** para esta aplicación el despliegue es muy rápido, pero durante ese tiempo se pierde por completo el acceso a todas las funcionalidades.

[← Volver al inicio](#tabla-de-contenido)

#### Rolling

En esta estrategia las instancias se actualizan por lotes. Frente a All at once, el servicio se mantiene con capacidad reducida en vez de caerse por completo, a cambio de que actualizar todas las instancias toma más tiempo.

Se configuraron lotes del 30% de las instancias para no reducir demasiado la capacidad de atender peticiones.

- **Instancias:** 3.
- **Tiempo de despliegue:** 8 minutos y 34 segundos.
- **Instancias usadas:** las mismas; no se reemplazaron. Con lotes del 30%, el despliegue se hizo de forma progresiva, una instancia a la vez.

Tiempo de despliegue:

<img width="636" height="95" alt="image" src="https://github.com/user-attachments/assets/c18c6711-3a54-4d5e-8a1a-13217f5b0762" />

**Hallazgos:** esta política mantiene servidores activos y reduce las interrupciones del servicio. Sin embargo, toma mucho más tiempo que All at once y puede causar comportamientos inconsistentes: durante el despliegue, un usuario puede ser dirigido a una instancia que todavía tiene la versión anterior.

[← Volver al inicio](#tabla-de-contenido)

#### Rolling with additional batch

Es similar a Rolling, pero antes de actualizar agrega un lote adicional de instancias para compensar la capacidad que se pierde mientras cada lote sale de servicio.

- **Instancias:** 3, más 1 instancia temporal del lote adicional.
- **Tiempo de despliegue:** 10 minutos y 26 segundos.
- **Instancias usadas:** las originales no se reemplazaron; se actualizaron de forma progresiva, una a la vez (lotes del 30%). Además, se lanzó un lote extra para compensar la capacidad.

Lote adicional lanzado durante el despliegue:

<img width="1000" height="272" alt="image" src="https://github.com/user-attachments/assets/ccc64b5e-418a-4a4b-83da-6dc608fac7ce" />

Al terminar el despliegue, la instancia adicional se apaga:

<img width="553" height="270" alt="image" src="https://github.com/user-attachments/assets/4b05793e-7440-4aea-a33b-82de67432254" />

Tiempo de despliegue:

<img width="638" height="86" alt="image" src="https://github.com/user-attachments/assets/53f3560a-8898-48d7-bfd4-1dade60517ba" />

**Hallazgos:** se mantienen los hallazgos de Rolling, con capacidad completa durante el despliegue. Al tener que lanzar una instancia nueva, toma un poco más de tiempo.

[← Volver al inicio](#tabla-de-contenido)

#### Immutable

En esta estrategia el grupo de Auto Scaling se reemplaza por otro. Primero se crea un grupo temporal con una instancia de prueba; si el despliegue falla, se cancela el cambio y se hace rollback. Si funciona, se lanzan instancias nuevas hasta igualar las actuales. Al completarse, el grupo original se elimina y todo el tráfico pasa al nuevo.

- **Instancias:** 3, más 3 temporales del grupo nuevo.
- **Tiempo de despliegue:** 19 minutos y 53 segundos.
- **Instancias usadas:** todas nuevas.

Durante el despliegue se duplica el número de instancias (la que aparece como *terminated* es la temporal creada en la estrategia Rolling with additional batch):

<img width="887" height="383" alt="image" src="https://github.com/user-attachments/assets/e611971b-9ab8-4057-96a0-d61eb0f4dab3" />

Durante el despliegue existen 2 grupos de Auto Scaling:

<img width="1170" height="323" alt="image" src="https://github.com/user-attachments/assets/913767dd-fd86-41be-a017-5181614bfc99" />

Al terminar, todo quedó desplegado en instancias nuevas y las originales se apagaron:

<img width="1015" height="374" alt="image" src="https://github.com/user-attachments/assets/02bb55d1-7644-42eb-93b0-73624943f9cb" />

Tiempo de despliegue:

<img width="648" height="94" alt="image" src="https://github.com/user-attachments/assets/3d9a684a-dadc-4b7b-9ae0-fb8716291b99" />

**Hallazgos:** es por amplio margen el método más lento de los probados, porque debe crear un grupo nuevo de instancias replicando la configuración actual, validarlo y luego apagar el grupo original. También es el más costoso, ya que duplica temporalmente el número de instancias; con instancias costosas o en gran cantidad, el costo puede ser elevado. Aun así, nos pareció la estrategia más efectiva: no hay tiempo de inactividad, porque mientras se configura y valida el nuevo grupo el original sigue funcionando, y al terminar el tráfico se redirige de inmediato al nuevo.

[← Volver al inicio](#tabla-de-contenido)

#### Comparación

| Estrategia | Instancias | Tiempo | ¿Instancias nuevas? | Disponibilidad durante el despliegue |
|---|---|---|---|---|
| All at once | 3 | 0 min 28 s | No, las mismas | Se pierde el servicio |
| Rolling (lotes de 30%) | 3 | 8 min 34 s | No, las mismas | Capacidad reducida, versiones mezcladas |
| Rolling with additional batch | 3 + 1 temporal | 10 min 26 s | No, más un lote extra temporal | Capacidad completa |
| Immutable | 3 + 3 temporales | 19 min 53 s | Sí, grupo de Auto Scaling nuevo | Sin interrupción |

[← Volver al inicio](#tabla-de-contenido)

## Flujo de trabajo con Git

- Todo branch se crea desde `develop`.
- El pipeline del equipo integra los cambios, ejecuta las pruebas y, si todo pasa, los sube a `main`.

[← Volver al inicio](#tabla-de-contenido)
