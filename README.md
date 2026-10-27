# NJ Fence and Railing — Desktop PDF Catalog Studio (`mcp-pdf`)

Aplicación de escritorio independiente (100% separada de la página web actual) diseñada para **NJ Fence and Railing** que permite:

1. **Subir fotografías de barandillas, cercas y portones** y procesarlas automáticamente sobre un **fondo blanco puro (`#FFFFFF`)** de estudio.
2. **Analizar las imágenes con Google Gemini** usando directamente tu **cuenta personal de Google ya autenticada en Antigravity (`vdassaet98@gmail.com`)** sin necesidad de pagar servicios adicionales (con soporte opcional para `GEMINI_API_KEY` de Google AI Studio).
3. **Introducir precios exactos Por Pie Lineal (`$ / Linear Ft`) o Por Kit (`$ / Kit`)**, cumpliendo la regla estricta de **nunca inventar cifras**.
4. **Asistente manual para Google Flow (`labs.google/fx/tools/flow`)** sin simular conexiones inexistentes, más soporte opcional para los modelos subyacentes oficiales (`Imagen 3` / `Veo` vía `google-genai`).
5. **Generar catálogos PDF profesionales** listos para clientes en New Jersey y New York.

---

## 🚀 Cómo Ejecutar la Aplicación de Escritorio en tu PC

Haz doble clic en [`run_app.bat`](file:///e:/mcp/run_app.bat) o ejecuta desde PowerShell en `e:\mcp`:

```powershell
.\.venv\Scripts\python.exe main.py
```

Para ejecutar la comprobación automática de integraciones de Google y generar un catálogo PDF de prueba verificado:

```powershell
.\.venv\Scripts\python.exe main.py --verify
```

---

## 🔍 Estado Verificado de Integraciones con tus Servicios de Google

| Servicio / Integración | ¿Funciona? | Autorización | Costes |
| :--- | :--- | :--- | :--- |
| **1. Gemini vía tu Cuenta Personal en Antigravity (`agy` OAuth)** | ✅ **SÍ (Activo)** | Ya autenticado con `vdassaet98@gmail.com` en el Keyring de Windows (`useG1Credits: true`). | **$0.00 adicional** (Incluido en tu cuenta personal de Antigravity / Google One). |
| **2. Gemini API Directa (`google-genai` — Google AI Studio)** | 🟡 **Listo (Opcional)** | Requiere `GEMINI_API_KEY` en `.env` solo si deseas análisis instantáneo (1–2s) sin pasar por `agy` CLI. | **Nivel Gratuito ($0.00)**: hasta 1,500 fotos/día en Google AI Studio. **Nivel de Pago**: ~$0.0002 USD/foto (< $0.01 por 50 fotos). |
| **3. Google Flow Web (`labs.google/fx/tools/flow`)** | 🔵 **Modo Manual Asistido** | **No existe API pública oficial de Google Flow.** Se usa iniciando sesión manualmente en el navegador. | **$0.00 adicional** usando manualmente tu suscripción de Google en la web de Flow. |
| **4. Modelos Subyacentes de Flow por API (`Imagen 3` / `Veo`)** | ⚪ **Implementado (Opcional)** | Requiere `GEMINI_API_KEY` con facturación (Billing) activa en Google Cloud. | **De pago por uso**: Imagen 3 ~$0.03–$0.04 USD/imagen; Veo ~$0.35–$0.50 USD/seg de video. |

---

## 📁 Estructura del Proyecto (`e:\mcp`)

- [`main.py`](file:///e:/mcp/main.py): Punto de entrada de la aplicación de escritorio y verificador CLI (`--verify`).
- [`run_app.bat`](file:///e:/mcp/run_app.bat): Lanzador directo de escritorio para Windows.
- [`src/models.py`](file:///e:/mcp/src/models.py): Modelos de datos y validador estricto de precios (`parse_user_price`) que prohíbe inventar cifras.
- [`src/image_processor.py`](file:///e:/mcp/src/image_processor.py): Procesador de fotografías hacia fondo blanco puro (`#FFFFFF`) con aislamiento de barrotes/postes y mejora de nitidez.
- [`src/google_integrations.py`](file:///e:/mcp/src/google_integrations.py): Conexión real con tu cuenta de Google en Antigravity (`agy`), SDK oficial `google-genai` y asistente honesto para Google Flow.
- [`src/pdf_generator.py`](file:///e:/mcp/src/pdf_generator.py): Motor `ReportLab` para exportar catálogos PDF ejecutivos de **NJ Fence and Railing**.
- [`src/ui_app.py`](file:///e:/mcp/src/ui_app.py): Interfaz gráfica de escritorio (`CustomTkinter`).
- [`src/storage.py`](file:///e:/mcp/src/storage.py): Almacenamiento local en JSON e imágenes (`data/`, `output/catalogs/`).
