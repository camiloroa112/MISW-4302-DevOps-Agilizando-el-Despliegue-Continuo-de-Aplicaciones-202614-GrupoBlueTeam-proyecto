# Blacklist Service - Grupo Blue Team

Microservicio REST para gestionar la lista negra global de emails de la organización. Permite agregar emails a la lista negra y consultar si un email está bloqueado.

Proyecto del curso MISW-4302 DevOps: Agilizando el Despliegue Continuo de Aplicaciones - Universidad de los Andes. El enunciado completo está en [`docs/enunciado.md`](docs/enunciado.md).

## Stack

Python 3.12 · Flask · Flask-SQLAlchemy · Flask-RESTful · Flask-Marshmallow · Flask-JWT-Extended · PostgreSQL · Gunicorn · Docker · AWS Elastic Beanstalk · AWS RDS

## Estructura del proyecto

```
├── application.py              # Punto de entrada WSGI
├── app/
│   ├── __init__.py             # create_app()
│   ├── config.py               # Configuración desde variables de entorno
│   ├── extensions.py           # Instancias de db, ma y jwt
│   ├── models.py               # Tabla blacklist
│   ├── schemas.py              # Validación y normalización del email
│   ├── auth.py                 # Respuestas 401 unificadas
│   └── resources/
│       ├── health.py           # GET /health
│       ├── blacklist_create.py # POST /blacklists
│       └── blacklist_query.py  # GET /blacklists/<email>
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

## Requisitos

- [uv](https://docs.astral.sh/uv/)
- Docker

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

## Token de autorización

```bash
uv run python -m scripts.generate_token
```

El token no expira y solo es válido para el `JWT_SECRET_KEY` con el que se generó. Para generar el token de AWS, pasa la clave de producción entre comillas:

```bash
JWT_SECRET_KEY="clave-de-produccion" uv run python -m scripts.generate_token
```

Se envía en el header `Authorization: Bearer <token>`.

## Pruebas

```bash
uv run pytest -v
```

Las pruebas usan SQLite en memoria; no requieren PostgreSQL ni `.env`.

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

### `GET /health`

Health check para Elastic Beanstalk. No requiere token. Responde `{"status": "ok"}`.

## Postman

La colección está en [`postman/`](postman/). Para usarla:

1. **Import** del archivo `.json` en Postman.
2. En la colección → **Variables**, completa la columna **Current value** de `base_url` (sin `/` al final) y `token`. No uses **Initial value**: se sincroniza con el workspace y aparece en la documentación publicada.
3. **Run collection**.

Los escenarios de creación generan un email único en cada ejecución, así que la colección puede correrse varias veces.

Documentación publicada: *pendiente*.

## Despliegue en AWS

Despliegue manual en Elastic Beanstalk, plataforma **Docker running on 64bit Amazon Linux 2023**, con PostgreSQL en RDS.

### Paquete de despliegue

```bash
git archive --format=zip -o blacklist-vN.zip HEAD
```

Solo incluye archivos versionados, así que `.env` y `.venv` nunca se cuelan.

### Configuración

| Componente | Configuración |
|---|---|
| RDS | PostgreSQL, Configuración completa, plantilla **Entorno de pruebas**, `db.t4g.micro`, gp3 de 20 GiB, sin acceso público, **nombre de base de datos inicial `blacklist`** |
| Security group de la app | `blacklist-app-sg`, asignado a las instancias de Beanstalk |
| Security group de RDS | `blacklist-rds-sg`, entrada PostgreSQL 5432 **solo** desde `blacklist-app-sg` |
| Beanstalk | Entorno con equilibrio de carga, Application Load Balancer público |
| Health check | Ruta `/health`, definida en `.ebextensions/healthcheck.config` y en la consola |
| Variables de entorno | `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` y `JWT_SECRET_KEY` |

### Lecciones del despliegue

- **Plantilla de RDS:** la plantilla *Producción* configura almacenamiento `io2` con IOPS provisionadas (unos 300 USD al mes). Usar *Entorno de pruebas* con gp3.
- **Regla de entrada de RDS:** RDS crea una regla con la IP de quien crea la base. Hay que eliminarla y crear una nueva con origen `blacklist-app-sg`; una regla por IP no se puede convertir en una que apunte a un security group.
- **Ruta del health check:** lo configurado en la consola tiene prioridad sobre `.ebextensions`. Si la consola deja `/`, el balanceador marca las instancias como no saludables.
- **Subredes:** el balanceador debe tener las **mismas subredes** que las instancias. Una instancia en una zona sin subred del balanceador queda en estado *Unused* y la API responde 503, aunque la aplicación esté funcionando.
- **URL:** el balanceador escucha en HTTP (puerto 80). Usar `http://`, sin `/` al final.

### Estrategias de despliegue

*Pendiente.*

## Flujo de trabajo con Git

- Todo branch se crea desde `develop`.
- El pipeline del equipo integra los cambios, ejecuta las pruebas y, si todo pasa, los sube a `main`.