# Blacklist Service - Grupo Blue Team - Entrega 1

Microservicio REST que gestiona la lista negra global de emails de la organización. Permite agregar emails a la lista negra y consultar si un email se encuentra bloqueado.

Proyecto del curso MISW-4302 DevOps: Agilizando el Despliegue Continuo de Aplicaciones - Universidad de los Andes. El enunciado completo está en [`docs/enunciado.md`](docs/enunciado.md).

## Tabla de Contenido

- [Blacklist Service - Grupo Blue Team - Entrega 1](#blacklist-service---grupo-blue-team---entrega-1)
  - [Tabla de Contenido](#tabla-de-contenido)
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
    - [Configuración](#configuración-1)
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
│   └── resources/
│       ├── health.py           # GET /health
│       ├── blacklist_create.py # POST /blacklists
│       └── blacklist_query.py  # GET /blacklists/<email>
│   ├── __init__.py             # create_app()
│   ├── auth.py                 # Respuestas 401 unificadas
│   ├── config.py               # Configuración desde variables de entorno
│   ├── extensions.py           # Instancias de db, ma y jwt
│   ├── models.py               # Tabla blacklist
│   ├── schemas.py              # Validación y normalización del email
├── scripts/
│   └── generate_token.py       # Genera el token JWT estático
├── tests/                      # Pruebas con pytest
├── postman/                    # Colección de Postman
├── docs/                       # Enunciado de la entrega
├── .ebextensions/              # Configuración de Elastic Beanstalk
├── .env.example                # Plantilla de variables de entorno
├── Dockerfile
├── .dockerignore
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
| 400 | Email vacío o con formato inválido | `{"msg": "Invalid request", "errors": {"email": [...]}}` |
| 401 | Token ausente o inválido | `{"msg": "Missing or invalid token"}` |

[← Volver al inicio](#tabla-de-contenido)

### `GET /health`

Health check para Elastic Beanstalk. No requiere token. Responde `{"status": "ok"}`.

[← Volver al inicio](#tabla-de-contenido)

## Postman

La colección está en [`postman/`](postman/). Para usarla:

1. **Import** del archivo `.json` en Postman.
2. En la colección → **Variables**, completa la columna **Current value** de `base_url` (sin `/` al final) y `token`. No uses **Initial value**: se sincroniza con el workspace y aparece en la documentación publicada.
3. **Run collection**.

Los escenarios de creación generan un email único en cada ejecución, así que la colección puede correrse varias veces.

Documentación publicada: *pendiente*.

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

### Configuración

| Componente | Configuración |
|---|---|
| RDS | PostgreSQL, Configuración completa, plantilla **Entorno de pruebas**, `db.t4g.micro`, gp3 de 20 GiB, sin acceso público, **nombre de base de datos inicial `blacklist`** |
| Security group de la app | `blacklist-app-sg`, asignado a las instancias de Beanstalk |
| Security group de RDS | `blacklist-rds-sg`, entrada PostgreSQL 5432 **solo** desde `blacklist-app-sg` |
| Beanstalk | Entorno con equilibrio de carga, Application Load Balancer público |
| Health check | Ruta `/health`, definida en `.ebextensions/healthcheck.config` y en la consola |
| Variables de entorno | `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` y `JWT_SECRET_KEY` |

[← Volver al inicio](#tabla-de-contenido)

### Lecciones del despliegue

- **Plantilla de RDS:** la plantilla *Producción* configura almacenamiento `io2` con IOPS provisionadas (unos 300 USD al mes). Usar *Entorno de pruebas* con gp3.
- **Regla de entrada de RDS:** RDS crea una regla con la IP de quien crea la base. Hay que eliminarla y crear una nueva con origen `blacklist-app-sg`; una regla por IP no se puede convertir en una que apunte a un security group.
- **Ruta del health check:** lo configurado en la consola tiene prioridad sobre `.ebextensions`. Si la consola deja `/`, el balanceador marca las instancias como no saludables.
- **Subredes:** el balanceador debe tener las **mismas subredes** que las instancias. Una instancia en una zona sin subred del balanceador queda en estado *Unused* y la API responde 503, aunque la aplicación esté funcionando.
- **URL:** el balanceador escucha en HTTP (puerto 80). Usar `http://`, sin `/` al final.

[← Volver al inicio](#tabla-de-contenido)

### Estrategias de despliegue

#### All at once

En la estrategia de despliegue all at once, EB tumba todas las instancias activas actualmente, las actualiza y las vuelve a subir, esto resulta en una baja del servicio la cual tiene una duración igual al tiempo de despliegue y levantamiento de las instancias.

La configuración predeterminada para la aplicación es de 3 a 6 instancias autoescalables como lo recomienda el enunciado, 

- Se usaron 3 instancias ya que este es el limite inferior de la configuración recomendada.
- El despliegue se validó usando el manejador de eventos de EB y la lista de despliegues de EB, el cual nos muestra la hora exacta de inicio, la estrategia de despliegue y el tiempo que tomó. Con este metodo el despliegue tomó 28 segundos.
- El despliegue se realizó sobre las mismas instancias que ya estaban activas, esto fue comprobado comparando los ID de las instancias activas en EC2.
- Tiempo de despliegue:
  
<img width="1653" height="738" alt="image" src="https://github.com/user-attachments/assets/ca327dea-0cff-4f51-8b0a-0a50b4b253e6" />

- Instancias activas de EC2 antes y después del despliegue:
- Antes:
  
<img width="577" height="234" alt="image" src="https://github.com/user-attachments/assets/7a090656-4953-49cc-b722-29532711049d" />

- Después:

<img width="562" height="250" alt="image" src="https://github.com/user-attachments/assets/a929ca8a-81c2-4cef-a56a-e033af5018ff" />

- Los hallazgos que tuvimos fue que esta forma de deploy no toma mucho tiempo en el caso de esta aplicación, pero durante ese periodo se pierde acceso completamente a todas la funcionalidades.

[← Volver al inicio](#tabla-de-contenido)

#### Rolling

En la estrategia rolling se toman baches de instancias, y se hace el despliegue. El beneficio de esta estrategia frente all at once es que se va mantener el servicio con una capacidad reducida en vez de perder todo el servicio, con la desventaja de que toma mas tiempo actualizar todas las instancias.

Para esta estrategia se configuraron baches de 30% del numero de instancias con el objetivo de no reducir tanto la capacidad de manejo de peticiones de la aplicación.

- Se usaron 3 instancias ya que este es el limite inferior de la configuración recomendada.
- El despliegue se validó usando el manejador de eventos de EB y la lista de despliegues de EB, el cual nos muestra la hora exacta de inicio, la estrategia de despliegue y el tiempo que tomó. Con este metodo el despliegue tomó 8 minutos y 34 segundos.
- Con esta estrategia de despliegue tampoco fueron reemplazadas las instancias, el despliegue se hizo de forma progresiva una instancia a la vez por la configuración del 30% de instancias por bache.
- Tiempo de despliegue:
  
<img width="636" height="95" alt="image" src="https://github.com/user-attachments/assets/c18c6711-3a54-4d5e-8a1a-13217f5b0762" />

- Nuestros hallazgos fueron que esta politica nos permite mantener servidores activos, lo cual reduce interrupciones al servicio. Pero tiene ciertas desventajas, toma mucho más tiempo que el all at once, y puede causar inconsistencias en comportamiento si no se tienen medidas, ya que durante el tiempo de despliegue se puede dirigir al usuario a una instancia con un versión anterior.

[← Volver al inicio](#tabla-de-contenido)

#### Rolling with additional batch

Muy similar a la estrategia de Rolling tradicional, solo que esta agrega un bache nuevo de instancias para compensar por la capacidad de computo perdida por cada bache que sale de servicio para actualizar.

- Se usaron 3 instancias ya que este es el limite inferior de la configuración recomendada.
- El despliegue se validó usando el manejador de eventos de EB y la lista de despliegues de EB, el cual nos muestra la hora exacta de inicio, la estrategia de despliegue y el tiempo que tomó. Con este metodo el despliegue tomó 10 minutos y 26 segundos.
- Con esta estrategia de despliegue tampoco fueron reemplazadas las instancias, el despliegue se hizo de forma progresiva una instancia a la vez por la configuración del 30% de instancias por bache. Este metodo inicializó un bache extra para compensar por el computo perdido.
  
<img width="1000" height="272" alt="image" src="https://github.com/user-attachments/assets/ccc64b5e-418a-4a4b-83da-6dc608fac7ce" />

- Una vez terminado el deployment, la nueva instancia es apagada.
  
<img width="553" height="270" alt="image" src="https://github.com/user-attachments/assets/4b05793e-7440-4aea-a33b-82de67432254" />

- Tiempo de despliegue:
  
- Tiempo de despliegue:

<img width="638" height="86" alt="image" src="https://github.com/user-attachments/assets/53f3560a-8898-48d7-bfd4-1dade60517ba" />

- Se conservan los mismos hallazgos que el Rolling normal, solo que este al tener que inicializar una nueva instancia toma un poco más de tiempo.

[← Volver al inicio](#tabla-de-contenido)

#### Immutable

Con esta estrategia, el grupo de autoescalado es reemplazado por otro, inicialmente se crea un grupo temporal donde se inicializa una instancia, si el despliegue falla se cancela el cambio y se hace un rollback.

Si es cambio es exitoso en la instancia de prueba, se inicializan nuevas instancias duplicando las actuales, cuando se completa se apaga el grupo de autoescalado y todo el trafico es redirigido al nuevo.

- Se usaron 3 instancias ya que este es el limite inferior de la configuración recomendada.
- El despliegue se validó usando el manejador de eventos de EB y la lista de despliegues de EB, el cual nos muestra la hora exacta de inicio, la estrategia de despliegue y el tiempo que tomó. Con este metodo el despliegue de 19 minutos y 53 segundos.
- Durante el despliegue podemos ver que se duplica el numero de instancias (La que aparece terminated es la temporal que se creó con Rolling)
  
<img width="887" height="383" alt="image" src="https://github.com/user-attachments/assets/e611971b-9ab8-4057-96a0-d61eb0f4dab3" />

- Y podemos ver que ahora tenemos 2 grupos de autoescalado:
  
<img width="1170" height="323" alt="image" src="https://github.com/user-attachments/assets/913767dd-fd86-41be-a017-5181614bfc99" />

- Al terminar podemos ver que todo se desplegó sobre nuevas instancias y que las originales se encuentran apagadas
  
<img width="1015" height="374" alt="image" src="https://github.com/user-attachments/assets/02bb55d1-7644-42eb-93b0-73624943f9cb" />

- Tiempo de despliegue:
  
<img width="648" height="94" alt="image" src="https://github.com/user-attachments/assets/3d9a684a-dadc-4b7b-9ae0-fb8716291b99" />

- Lo que pudimos ver es que este metodo es el más lento de los probados por un gran margen, ya que tiene que disponibilizar un nuevo grupo de instancias se está replicando la configuración actual más el tiempo que toman las validaciones y el apagado del grupo original de instancias. Tambien es el que mas cuesta, ya que temporalmente duplica el numero de instancias y si se usan instancias de alto costo o muchas instancias puede tener un costo elevado. Por ultimo esta estrategia nos parecio la mas efectiva, ya que se hace con 0 downtime, mientras se configura el nuevo grupo y se valida que funcione de forma correcta, el original sigue funcionando, y cuando se termina el trafico es redirigido inmediatamente al nuevo grupo.

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