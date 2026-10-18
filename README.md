# MISW-4302-DevOps-Agilizando-el-Despliegue-Continuo-de-Aplicaciones-202614-GrupoBlueTeam-proyecto

## Entrega 1 – Despliegue manual de un microservicio sobre un servicio PaaS

Universidad de los Andes · DevOps

## Tabla de contenido

- [MISW-4302-DevOps-Agilizando-el-Despliegue-Continuo-de-Aplicaciones-202614-GrupoBlueTeam-proyecto](#misw-4302-devops-agilizando-el-despliegue-continuo-de-aplicaciones-202614-grupoblueteam-proyecto)
  - [Entrega 1 – Despliegue manual de un microservicio sobre un servicio PaaS](#entrega-1--despliegue-manual-de-un-microservicio-sobre-un-servicio-paas)
  - [Tabla de contenido](#tabla-de-contenido)
  - [Objetivos](#objetivos)
  - [Tiempo de dedicación](#tiempo-de-dedicación)
  - [Lecturas previas](#lecturas-previas)
  - [Esquema de evaluación](#esquema-de-evaluación)
  - [Lugar y formato de entrega](#lugar-y-formato-de-entrega)
  - [Infraestructura requerida](#infraestructura-requerida)
  - [Stack tecnológico](#stack-tecnológico)
  - [Alcance de la entrega](#alcance-de-la-entrega)
  - [Desarrollo de la aplicación](#desarrollo-de-la-aplicación)
    - [Agregar un email (POST)](#agregar-un-email-post)
    - [Consultar un email (GET)](#consultar-un-email-get)
  - [Diseño del API REST](#diseño-del-api-rest)
    - [`POST /blacklists`](#post-blacklists)
    - [`GET /blacklists/<string:email>`](#get-blacklistsstringemail)
    - [Consideraciones](#consideraciones)
  - [Documentación del API REST](#documentación-del-api-rest)
  - [Documento de la entrega](#documento-de-la-entrega)
    - [1. Paso a paso del despliegue (10%)](#1-paso-a-paso-del-despliegue-10)
    - [2. Estrategias de despliegue (20%)](#2-estrategias-de-despliegue-20)
  - [Sustentación de la entrega](#sustentación-de-la-entrega)
- [Desarrollo - Entrega 1](#desarrollo---entrega-1)

---

## Objetivos

- Desarrollar y desplegar un microservicio que involucre el uso de servidores de nube pública y servicios de control de versiones.
- Realizar el despliegue manual de una aplicación sobre los servicios de un proveedor cloud, **sin** incluir servicios de Continuous Integration / Continuous Deployment.

## Tiempo de dedicación

La entrega está planeada para **dos semanas (semanas 1 y 2)**. Cada estudiante debe invertir las horas definidas en la planeación semanal. Para el éxito de la actividad es necesario conformar un equipo de trabajo según las pautas del curso.

## Lecturas previas

- Tutoriales públicos de Flask o los vistos en cursos anteriores
- Tutorial de AWS Elastic Beanstalk del curso
- Documentación pública de AWS Elastic Beanstalk
- AWS Elastic Beanstalk deployment strategies
- Documentación pública de GitHub

## Esquema de evaluación

| Componente | Peso |
|---|---|
| Verificación funcional de los requerimientos de la aplicación desplegada en el proveedor de nube, configuración de GitHub y documentación en Postman | **70%** |
| Documento del despliegue | **30%** |

## Lugar y formato de entrega

La entrega está conformada por:

1. Aplicación en ejecución sobre **AWS Elastic Beanstalk**, accesible vía Postman.
2. Repositorio con el código fuente en **GitHub** (creado por los estudiantes).
3. Documento del despliegue realizado, con el nombre:

   ```
   Proyecto 1 entrega 1 – Documento.pdf
   ```

## Infraestructura requerida

- AWS Academy o cuenta de AWS propia
- Servicios de AWS (se recomienda **AWS RDS** para la base de datos relacional)

## Stack tecnológico

La aplicación web debe desarrollarse en **Python** con el framework **Flask**, sobre servicios PaaS de un proveedor de nube pública. Se pueden usar las versiones que más se faciliten o las más recientes.

| # | Tecnología | Descripción |
|---|---|---|
| 1 | Python | Lenguaje de programación |
| 2 | Flask | Micro framework web |
| 3 | Flask-SQLAlchemy | Soporte para el ORM SQLAlchemy, que simplifica la interacción con una base de datos SQL |
| 4 | Flask-RESTful | Desarrollo de APIs REST con un patrón orientado a objetos |
| 5 | Flask-Marshmallow | Integración con Marshmallow para la serialización de objetos |
| 6 | Flask-JWT-Extended | Soporte de JSON Web Tokens (JWT) para proteger vistas, crear y refrescar tokens, entre otras funciones |
| 7 | Werkzeug | Biblioteca completa de aplicaciones web WSGI |
| 8 | PostgreSQL | Motor open source de base de datos SQL |

## Alcance de la entrega

Una compañía multinacional quiere mejorar la gestión de **listas negras de emails**, ya que en los últimos años ha recibido demandas y problemas legales por su mala gestión en los cientos de aplicaciones que usa en su día a día.

La compañía decidió que un equipo centralizado despliegue la primera versión de un **microservicio que gestione la lista negra global** de la empresa, de modo que cientos de sistemas internos puedan:

- Consultar si un email está en la lista negra global.
- Agregar emails a la lista negra global.

## Desarrollo de la aplicación

| Peso | Actividad |
|---|---|
| **45%** | Desarrollar y exponer un servicio REST **(POST)** para agregar un email a la lista negra global. |
| **25%** | Desarrollar y exponer un servicio REST **(GET)** para consultar si un email está en la lista negra global. |

### Agregar un email (POST)

Datos requeridos:

| Campo | Obligatorio | Detalle |
|---|---|---|
| `email` | Sí | Email del cliente a agregar a la lista negra global |
| `app_uuid` | Sí | Id de la app cliente (UUID) |
| `blocked_reason` | No | Motivo por el que se agrega, máximo **255 caracteres** |

Internamente, el microservicio debe guardar:

- La **dirección IP** desde donde se hace la solicitud.
- La **fecha/hora** en que se realiza la solicitud.

### Consultar un email (GET)

Recibe como parámetro el email del cliente y retorna si ese email está o no en la lista negra global.

## Diseño del API REST

Esta definición debe respetarse a lo largo de todo el proyecto.

### `POST /blacklists`

| Atributo | Valor |
|---|---|
| **Descripción** | Permite agregar un email a la lista negra global de la organización. |
| **Método** | `POST` |
| **Retorno** | `application/json`. Mensaje de confirmación notificando si la cuenta pudo o no ser creada. |
| **Parámetros** | `email` (String), `app_uuid` (String), `blocked_reason` (String) |
| **Autorización** | Bearer Token |

### `GET /blacklists/<string:email>`

| Atributo | Valor |
|---|---|
| **Descripción** | Permite saber si un email está en la lista negra global de la organización y el motivo por el que fue agregado. |
| **Método** | `GET` |
| **Retorno** | `application/json`. Valor booleano indicando si el email está o no en la lista negra global, y el motivo por el que fue agregado. |
| **Parámetros** | Ninguno |
| **Autorización** | Bearer Token |

### Consideraciones

- La API recibe un **token de autorización**. Por simplicidad, puede definirse de forma estática o predefinida para toda la aplicación, sin generarlo dinámicamente.
- Todas las funcionalidades deben ofrecerse desde **un único microservicio**.
- Al ser la primera iteración, no se consideran otras funcionalidades relacionadas.
- **No** se diseña interfaz de usuario; los servicios se validan con escenarios de prueba en **Postman**.
- La información debe persistir en un **servicio de base de datos relacional**. Se recomienda **AWS RDS** con el motor de preferencia.

## Documentación del API REST

Como no hay cliente frontend, la API se especifica, documenta y prueba con **Postman**:

1. Un integrante del equipo crea un **workspace en Postman** (personal o público, según el Plan Free) y una **colección** con los endpoints, especificando los parámetros mínimos para probar el API.
2. Para compartir el trabajo, el equipo puede:
   - Invitar a sus integrantes dentro del límite del plan, o
   - Exportar la colección y el environment en formato **JSON** y versionarlos en el repositorio.
3. Documentar cada endpoint con su **ejemplo de solicitud y respuesta**.
4. **Publicar** la documentación de la colección y anexar la URL publicada al informe de la entrega.

## Documento de la entrega

### 1. Paso a paso del despliegue (10%)

Capturas de pantalla de la creación y despliegue de la aplicación sobre AWS Elastic Beanstalk (con o sin contenedores), incluyendo:

- [ ] a. Configuración de RDS
- [ ] b. Configuración del proyecto en AWS Elastic Beanstalk
- [ ] c. Configuración de los health checks de la aplicación en Elastic Beanstalk

### 2. Estrategias de despliegue (20%)

Ejecutar **4 estrategias de despliegue diferentes** en Elastic Beanstalk que requieran más de una instancia, por ejemplo:

- All at once
- Rolling
- Rolling with additional batch
- Immutable
- Traffic splitting

> Se recomienda un grupo de Auto Scaling de **mínimo 3 y máximo 6 instancias**.

Por cada estrategia, documentar:

- [ ] a. Cantidad de instancias utilizadas
- [ ] b. Cómo se validó que el despliegue estaba en ejecución
- [ ] c. Tiempo total del despliegue (minutos y segundos)
- [ ] d. Si el despliegue se hizo sobre las instancias iniciales o sobre instancias nuevas
- [ ] e. Capturas de pantalla de la consola de AWS con los resultados del despliegue
- [ ] f. Hallazgos encontrados

## Sustentación de la entrega

- Se debe realizar un **video de máximo 10 minutos**. Lo que pase del minuto 10 no se tendrá en cuenta y se considerará no presentado.
- El video debe ser explicado por los integrantes del grupo (uno o varios) e incluir explicación y evidencias funcionales (consola de AWS, repositorios de código, etc.) de todos los requisitos, sin dejar dudas de si algo fue o no incluido.
- Debe evidenciar:
  - La configuración y ejecución de los escenarios de prueba de los endpoints.
  - Los repositorios de código.
  - El ambiente en GitHub y AWS.
- **No** cuenta como sustentación mostrar únicamente el contenido del PDF, ya que el tutor lo revisará aparte.
- ⚠️ **Sin video no hay sustentación**, y la entrega se califica con **0.0**.
- El tutor también podrá citar al grupo a una **sustentación síncrona**.

# Desarrollo - Entrega 1
La ruta del enlace se encuentra en el archivo [README.md](https://github.com/camiloroa112/MISW-4302-DevOps-Agilizando-el-Despliegue-Continuo-de-Aplicaciones-202614-GrupoBlueTeam-proyecto/blob/main/docs/entrega-1/README.md)