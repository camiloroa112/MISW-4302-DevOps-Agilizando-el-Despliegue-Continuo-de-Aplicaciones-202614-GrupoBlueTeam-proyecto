# Proyecto 1 · Entrega 2 — Integración Continua

**Grupo Blue Team · MISW-4302 DevOps · Universidad de los Andes**

> Fuente del entregable **`Proyecto 1 entrega 2 – Documento.pdf`**. Documento **conciso**: se centra en las dos ejecuciones de AWS CodePipeline (exitosa y fallida), sus hallazgos y capturas reales. La documentación técnica completa (arquitectura, pasos de consola, runbooks) está en `docs/entrega-2/README.md` del repositorio y se muestra en el video.
>
> **No llenar con evidencia inventada.** Reemplazar cada `EVIDENCIA AWS PENDIENTE` por capturas e identificadores reales antes de exportar el PDF. Ver [Cómo generar el PDF](#cómo-generar-el-pdf).

---

## 1. Resumen

Se incorporó **Integración Continua** al microservicio de lista negra de emails mediante **AWS CodeBuild** y **AWS CodePipeline**, con GitHub como origen a través de **AWS CodeConnections (GitHub App)**. Un push a la rama principal **`main`** dispara el pipeline, que instala dependencias, ejecuta las **23 pruebas unitarias** y, **solo si pasan**, genera un **artefacto ZIP** desplegable (plataforma Docker de Elastic Beanstalk) que se retiene en el bucket S3 de la canalización. **Es CI únicamente: no hay etapa de despliegue.**

> **Nota sobre `master`:** en este proyecto la rama principal es **`main`**, que cumple el rol de "master" del enunciado. No se crea una rama `master` duplicada. Detalle y mitigación en el README técnico.

## 2. Repositorio y pipeline

| Elemento | Valor |
|---|---|
| Rama fuente del pipeline | `main` |
| Conexión de origen | AWS CodeConnections (GitHub App) |
| Proyecto de build | CodeBuild `blacklist-ci-build` (`buildspec.yml`) |
| Pipeline | CodePipeline `blacklist-ci-pipeline` (Source + Build) |
| Artefacto | `blacklist-service-<sha>.zip` en el bucket S3 del pipeline |
| Etapa de despliegue | No aplica (CI only) |

## 3. Ejecución EXITOSA de CodePipeline

**Qué demuestra:** un cambio en `main` dispara el pipeline; Source y Build terminan en **Succeeded**, las pruebas pasan y el ZIP queda en S3.

| Dato | Valor |
|---|---|
| Execution ID del pipeline | `EVIDENCIA AWS PENDIENTE` |
| Build run ID de CodeBuild | `EVIDENCIA AWS PENDIENTE` |
| Resultado de pruebas | `EVIDENCIA AWS PENDIENTE` (esperado: 23 passed) |
| Clave del artefacto en S3 | `EVIDENCIA AWS PENDIENTE` |

**Capturas requeridas (reales):**

1. `EVIDENCIA AWS PENDIENTE` — Pipeline con Source + Build en **Succeeded** y el Execution ID.
2. `EVIDENCIA AWS PENDIENTE` — Log de CodeBuild/CloudWatch con `23 passed` y `Artifact created: ... .zip`.
3. `EVIDENCIA AWS PENDIENTE` — Objeto ZIP en el bucket S3 de artefactos.

**Hallazgos:** `EVIDENCIA AWS PENDIENTE`.

## 4. Ejecución FALLIDA de CodePipeline

**Qué demuestra:** cuando una prueba falla, el pipeline falla visiblemente (Source → Build → **Failed**) y **no se genera artefacto**. Se produjo de forma segura y reversible, **sin modificar `main`**, mediante un *source revision override* por SHA sobre el mismo pipeline (o un pipeline espejo como fallback).

| Dato | Valor |
|---|---|
| Execution ID del pipeline (fallo) | `EVIDENCIA AWS PENDIENTE` |
| Build run ID de CodeBuild (fallo) | `EVIDENCIA AWS PENDIENTE` |
| Método usado (override por SHA / espejo) | `EVIDENCIA AWS PENDIENTE` |
| Resultado de pruebas | `EVIDENCIA AWS PENDIENTE` (esperado: 1 failed) |

**Capturas requeridas (reales):**

1. `EVIDENCIA AWS PENDIENTE` — Pipeline con la etapa Build en **Failed** y el Execution ID.
2. `EVIDENCIA AWS PENDIENTE` — Log de CloudWatch con `1 failed`.
3. `EVIDENCIA AWS PENDIENTE` — Evidencia de que no se generó/retuvo artefacto.

**Hallazgos:** `EVIDENCIA AWS PENDIENTE`.

## 5. Conclusión

`EVIDENCIA AWS PENDIENTE` — breve cierre: la CI valida cada cambio en `main`, bloquea artefactos cuando las pruebas fallan y conserva el artefacto desplegable en S3 cuando pasan, sin desplegar automáticamente (CI only).

---

## Cómo generar el PDF

1. Reemplazar cada `EVIDENCIA AWS PENDIENTE` por el identificador o la captura real (insertar las imágenes con `![descripción](ruta-captura.png)`).
2. Exportar a PDF con el nombre exacto `Proyecto 1 entrega 2 – Documento.pdf`:
   - **VS Code + extensión "Markdown PDF":** abrir este archivo → paleta → *Markdown PDF: Export (pdf)* → renombrar la salida.
   - **Pandoc:** `pandoc "docs/entrega-2/documento-pdf.md" -o "Proyecto 1 entrega 2 – Documento.pdf"`.

> El PDF no se genera automáticamente porque aún faltan las capturas reales de AWS. No se fabrica evidencia.
