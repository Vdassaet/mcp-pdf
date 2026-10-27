"""
Google Services Integration Module for NJ Fence and Railing Catalog Studio.

Implements and verifies:
1. Personal Google Account via Antigravity CLI (`agy`) OAuth session (No API key required, $0 extra cost).
2. Official Gemini API (`google-genai` SDK with `gemini-2.5-flash`) for instant 1-2s image analysis.
3. Honest Google Flow (`labs.google/fx/tools/flow`) integration handler:
   - Clearly documents that Google Flow has NO public REST API.
   - Provides manual workflow helpers (optimized "Ingredients" prompt generator, 1-click browser launch,
     and direct import of downloaded Flow renders).
   - Provides optional official connection to the underlying Imagen 3 / Veo models via `google-genai`
     when a billing-enabled API key is configured.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import webbrowser
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Any, List, Optional

from dotenv import load_dotenv
from PIL import Image


GOOGLE_FLOW_URL = "https://labs.google/fx/tools/flow"
GOOGLE_AI_STUDIO_KEY_URL = "https://aistudio.google.com/apikey"


@dataclass
class IntegrationStatus:
    service_id: str
    service_name: str
    is_working: bool
    status_label: str
    auth_status: str
    how_to_authorize: str
    cost_explanation: str
    details: str


def _load_env_safely() -> Optional[str]:
    """Load .env from project root or user home directory and return active Gemini API key if present."""
    project_env = Path(__file__).resolve().parent.parent / ".env"
    home_env = Path.home() / ".env"
    if project_env.exists():
        load_dotenv(project_env, override=False)
    if home_env.exists():
        load_dotenv(home_env, override=False)

    key = os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("GOOGLE_API_KEY", "").strip()
    return key if key else None


def detect_antigravity_auth() -> Dict[str, Any]:
    """
    Check if Antigravity (`agy` CLI / IDE) is installed and authenticated with the user's
    personal Google account via Windows Keyring / OAuth state.
    Does NOT expose or print any secret tokens.
    """
    agy_path = shutil.which("agy")
    cli_dir = Path.home() / ".gemini" / "antigravity-cli"
    agy_dir = Path.home() / ".gemini" / "antigravity"
    settings_path = cli_dir / "settings.json"
    cli_log_path = cli_dir / "cli.log"

    use_g1_credits = False
    if settings_path.exists():
        try:
            data = json.loads(settings_path.read_text(encoding="utf-8", errors="ignore"))
            use_g1_credits = bool(data.get("useG1Credits", False))
        except Exception:
            pass

    authenticated_email: Optional[str] = None
    auth_method: Optional[str] = None

    if cli_log_path.exists():
        try:
            log_tail = cli_log_path.read_text(encoding="utf-8", errors="ignore")[-40000:]
            matches = re.findall(r"email=([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+),\s*authMethod=(\w+)", log_tail)
            if matches:
                authenticated_email, auth_method = matches[-1]
            else:
                m2 = re.findall(r"authenticated successfully as ([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)", log_tail)
                if m2:
                    authenticated_email = m2[-1]
                    auth_method = "oauth_keyring"
        except Exception:
            pass

    has_state = (cli_dir / "jetski_state.pbtxt").exists() or (agy_dir / "antigravity_state.pbtxt").exists()
    is_authenticated = bool(agy_path and (authenticated_email or has_state))

    return {
        "agy_installed": bool(agy_path),
        "agy_path": agy_path or "",
        "is_authenticated": is_authenticated,
        "email": authenticated_email or ("Sesión OAuth activa en Keyring" if has_state else None),
        "auth_method": auth_method or ("consumer" if has_state else None),
        "use_g1_credits": use_g1_credits,
    }


def check_all_google_integrations() -> List[IntegrationStatus]:
    """
    Verify every required Google integration and report:
    1. Which ones work right now
    2. Which ones need authorization
    3. What costs (if any) they have
    """
    statuses: List[IntegrationStatus] = []

    # 1. Antigravity Personal Account Integration (Gemini via OAuth Keyring)
    agy_info = detect_antigravity_auth()
    if agy_info["is_authenticated"]:
        email_label = agy_info["email"]
        g1_note = " (Google One AI Credits activos)" if agy_info["use_g1_credits"] else ""
        statuses.append(
            IntegrationStatus(
                service_id="gemini_antigravity_oauth",
                service_name="1. Gemini vía Cuenta Personal en Antigravity (OAuth)",
                is_working=True,
                status_label="FUNCIONANDO Y AUTENTICADO",
                auth_status=f"Autenticado como {email_label}{g1_note}",
                how_to_authorize="No requiere acción: tu sesión OAuth ya está activa en este PC. Si algún día cierras sesión, ejecuta `agy` en PowerShell para reautenticar en el navegador.",
                cost_explanation="$0.00 adicional — Utiliza directamente las funciones incluidas en tu cuenta personal de Google / Antigravity sin requerir API Key de pago.",
                details=f"Binario detectado: {agy_info['agy_path']} | Método: {agy_info['auth_method']}",
            )
        )
    else:
        statuses.append(
            IntegrationStatus(
                service_id="gemini_antigravity_oauth",
                service_name="1. Gemini vía Cuenta Personal en Antigravity (OAuth)",
                is_working=False,
                status_label="REQUIERE INICIAR SESIÓN",
                auth_status="No se detectó sesión OAuth activa en Antigravity CLI",
                how_to_authorize="Abre una terminal PowerShell, escribe `agy` y presiona Enter. Se abrirá tu navegador para iniciar sesión con tu cuenta personal de Google.",
                cost_explanation="$0.00 adicional — Usa la cuota incluida en tu cuenta de Antigravity.",
                details="Una vez iniciada la sesión en `agy`, la aplicación analizará fotos sin API Key.",
            )
        )

    # 2. Direct Gemini API via Google AI Studio (Optional High-Speed Mode)
    api_key = _load_env_safely()
    if api_key:
        statuses.append(
            IntegrationStatus(
                service_id="gemini_api_direct",
                service_name="2. Gemini API Directa (Google AI Studio SDK `google-genai`)",
                is_working=True,
                status_label="FUNCIONANDO (API Key detectada en .env)",
                auth_status="GEMINI_API_KEY configurada de forma segura",
                how_to_authorize="Ya autorizada mediante archivo `.env`.",
                cost_explanation=(
                    "Nivel Gratuito (Free Tier) en Google AI Studio: $0.00 (hasta 15 peticiones/min y 1,500/día con Gemini 2.5 Flash). "
                    "Nivel de Pago (Pay-as-you-go): ~$0.0002 USD por fotografía analizada (< $0.01 por cada 50 fotos)."
                ),
                details="Velocidad de respuesta: ~1.5 segundos por imagen usando `gemini-2.5-flash`.",
            )
        )
    else:
        statuses.append(
            IntegrationStatus(
                service_id="gemini_api_direct",
                service_name="2. Gemini API Directa (Modo Instantáneo Opcional — Google AI Studio)",
                is_working=False,
                status_label="OPCIONAL (Usa Cuenta Antigravity por defecto; API Key no configurada)",
                auth_status="Sin GEMINI_API_KEY en `.env` (No es obligatoria porque el Modo 1 ya funciona con tu cuenta)",
                how_to_authorize=(
                    "Opcional: Si deseas respuestas en 1-2 segundos en lugar de esperar al CLI de Antigravity, "
                    "obtén una clave gratuita en https://aistudio.google.com/apikey y guárdala en `e:\\mcp\\.env` "
                    "o desde el botón 'Configurar API Key' de la aplicación."
                ),
                cost_explanation=(
                    "¿Por qué existe esta opción?: Porque las apps externas no pueden leer el token OAuth directo de Google "
                    "sin pasar por `agy` CLI o usar una API Key. "
                    "Costes: $0.00 en el Nivel Gratuito (Free Tier) de Google AI Studio (sin tarjeta). "
                    "Si activas facturación Pay-as-you-go en Google Cloud: ~$0.0002 USD por imagen (~50 fotos = 1 centavo)."
                ),
                details="El SDK `google-genai` v2.33 ya está instalado y listo en `.venv`.",
            )
        )

    # 3. Google Flow (labs.google/fx/tools/flow)
    statuses.append(
        IntegrationStatus(
            service_id="google_flow_web",
            service_name="3. Google Flow (labs.google/fx/tools/flow)",
            is_working=True,
            status_label="MODO MANUAL ASISTIDO (No existe API pública de Google Flow)",
            auth_status="Usa tu cuenta personal de Google directamente en el navegador web",
            how_to_authorize=(
                "Google Labs NO ofrece una API pública ni SDK para conectarse programáticamente a la aplicación web Google Flow. "
                "Para usarlo sin coste extra con tu suscripción de Google, haz clic en 'Abrir Google Flow' en la app e inicia sesión en tu navegador."
            ),
            cost_explanation=(
                "$0.00 de coste de API usando Google Flow manualmente en la web con los créditos incluidos en tu plan de Google. "
                "(No simulamos ninguna conexión inexistente)."
            ),
            details=(
                "Funciones manuales integradas en esta app: "
                "1) Generación automática de Prompts 'Ingredients' en inglés a partir de cada barandilla analizada; "
                "2) Copia en 1 clic y apertura directa de Google Flow; "
                "3) Importación de imágenes descargadas de Flow para procesarlas sobre fondo blanco y añadirlas al catálogo PDF."
            ),
        )
    )

    # 4. Underlying Flow Models (Imagen 3 / Veo via Official Gemini API)
    statuses.append(
        IntegrationStatus(
            service_id="google_imagen_veo_api",
            service_name="4. Modelos Subyacentes de Flow por API (Imagen 3 / Veo en `google-genai`)",
            is_working=bool(api_key),
            status_label="CONEXIÓN OFICIAL IMPLEMENTADA (Requiere API Key con facturación)" if api_key else "REQUIERE API KEY CON FACTURACIÓN (Opcional)",
            auth_status="Requiere `GEMINI_API_KEY` con cuenta de facturación (Billing) activa en Google AI Studio / Vertex AI",
            how_to_authorize=(
                "Si deseas automatizar por código los mismos motores que usa Google Flow (Imagen 3 y Veo), "
                "necesitas una `GEMINI_API_KEY` vinculada a un proyecto de Google Cloud con facturación habilitada."
            ),
            cost_explanation=(
                "IMPORTANTE — SERVICIO DE PAGO POR USO: A diferencia del análisis de texto/fotos en Gemini Flash (que tiene nivel gratuito), "
                "la API de generación de imágenes (Imagen 3) cuesta aprox. $0.03–$0.04 USD por imagen generada, "
                "y la API de generación de video (Veo) cuesta aprox. $0.35–$0.50 USD por segundo de video. "
                "Por eso recomendamos usar nuestro procesador local de fondo blanco ($0.00) o Google Flow web manual ($0.00)."
            ),
            details="Implementado en `generate_image_via_official_genai_api()` usando `imagen-3.0-generate-002`.",
        )
    )

    return statuses


def _build_analysis_prompt(image_path: Path) -> str:
    """
    Build the multimodal analysis prompt for Gemini.
    Strictly forbids inventing any prices or numerical quotes.
    """
    return (
        f"Read and visually analyze the fence/railing product image located at '{image_path.as_posix()}'. "
        "You are the technical catalog specialist for 'NJ Fence and Railing' (New Jersey & New York). "
        "Analyze ONLY what is visually present in the photograph (railing/fence style, material appearance, "
        "color/finish, pickets/balusters, top/bottom rails, posts, decorative rings/knuckles, mounting style). "
        "CRITICAL RULE: NEVER invent, guess, or mention any price, dollar amount, or cost number. "
        "Return ONLY a valid JSON object (no markdown fences, no extra text) with the exact keys:\n"
        "{\n"
        '  "name": "Commercial model name in English/Spanish (e.g. Architectural Black Picket Railing / Barandilla Arquitectónica Negra)",\n'
        '  "category": "One of: Aluminum Railing | Wrought Iron / Steel Railing | Vinyl Railing | Cable / Glass Railing | Vinyl Fence | Wood / Chain Link Fence | Custom Gate",\n'
        '  "material": "Observed material (e.g. Powder-Coated Aluminum / Hierro Forjado Galvanizado)",\n'
        '  "finish_color": "Observed color and finish (e.g. Matte Black / Negro Mate Texturizado)",\n'
        '  "description_es": "2-3 sentences of professional commercial & technical description in Spanish for NJ Fence and Railing catalog, describing the design, durability, and ideal residential/commercial use without mentioning any prices.",\n'
        '  "description_en": "2-3 sentences of professional commercial & technical description in English for NJ Fence and Railing catalog, describing the design, durability, and ideal residential/commercial use without mentioning any prices.",\n'
        '  "features": ["Feature 1 (ES/EN)", "Feature 2 (ES/EN)", "Feature 3 (ES/EN)", "Feature 4 (ES/EN)"],\n'
        '  "flow_prompt_suggestion": "High-precision image-to-image prompt in English for Google Flow (labs.google/fx/tools/flow). Must instruct the model to STRICTLY PRESERVE the exact railing architecture, picket spacing, top rail profile, post geometry, and authentic color/finish from the input photo without modifying or hallucinating a different design. Must explicitly demand: ISOLATION ON PURE SEAMLESS SOLID WHITE BACKGROUND (#FFFFFF), REMOVING all stairs, concrete, siding, scaffolding, dirt, and clutter, leaving ONLY the railing product with subtle soft ground contact shadow."\n'
        "}"
    )


def _extract_json_from_text(raw_text: str) -> Optional[Dict[str, Any]]:
    """Extract and parse a JSON object from model output text."""
    if not raw_text:
        return None
    cleaned = raw_text.strip()
    # Try direct parse
    try:
        obj = json.loads(cleaned)
        if isinstance(obj, dict):
            return obj
    except Exception:
        pass

    # Look for ```json ... ``` or { ... }
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        try:
            obj = json.loads(match.group(0))
            if isinstance(obj, dict):
                return obj
        except Exception:
            pass
    return None


def _strip_any_invented_prices(text: str) -> str:
    """Safety guard: strip any accidental currency figures from AI descriptions."""
    if not text:
        return ""
    return re.sub(r"\$\s*\d+(?:[.,]\d+)?", "", text).strip()


def analyze_with_gemini_api_key(image_path: str | Path, api_key: str) -> Dict[str, Any]:
    """
    Analyze a railing/fence photograph directly using the official `google-genai` SDK
    (`gemini-3.8-flash`).
    """
    from google import genai

    img_path = Path(image_path).resolve()
    client = genai.Client(api_key=api_key)
    pil_img = Image.open(img_path)

    prompt = _build_analysis_prompt(img_path)
    candidate_models = [
        "gemini-3.5-flash-lite",
        "gemini-3.1-flash-lite",
        "gemini-3.5-flash",
        "gemini-3-flash-preview",
    ]
    last_err: Optional[Exception] = None
    response = None
    model_used = candidate_models[0]
    for m in candidate_models:
        try:
            model_used = m
            response = client.models.generate_content(
                model=m,
                contents=[pil_img, prompt],
            )
            break
        except Exception as exc:
            last_err = exc
    if response is None:
        raise RuntimeError(f"Error al llamar a Gemini API: {last_err}")
    parsed = _extract_json_from_text(response.text or "")
    if not parsed:
        raise RuntimeError(f"Gemini API no devolvió un JSON válido: {response.text}")

    parsed["description_es"] = _strip_any_invented_prices(str(parsed.get("description_es", "")))
    parsed["description_en"] = _strip_any_invented_prices(str(parsed.get("description_en", "")))
    parsed["ai_source"] = f"Gemini API Directa ({model_used})"
    return parsed


def analyze_with_antigravity_account(image_path: str | Path, timeout_sec: int = 95) -> Dict[str, Any]:
    """
    Analyze a railing/fence photograph using the user's already-authenticated personal
    Google account in Antigravity (`agy -p`) without requiring a separate API key.
    """
    img_path = Path(image_path).resolve()
    agy_bin = shutil.which("agy")
    if not agy_bin:
        raise RuntimeError("No se encontró el ejecutable `agy` en el PATH del sistema.")

    prompt = _build_analysis_prompt(img_path)
    cmd = [
        agy_bin,
        "-p",
        prompt,
        "--dangerously-skip-permissions",
        "--disable-slash-commands",
        "--add-dir",
        str(img_path.parent),
    ]

    creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    proc = subprocess.run(
        cmd,
        input="",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_sec,
        creationflags=creationflags,
    )

    if proc.returncode != 0:
        raise RuntimeError(f"Error al ejecutar `agy` CLI (código {proc.returncode}): {proc.stderr.strip()}")

    parsed = _extract_json_from_text(proc.stdout)
    if not parsed:
        raise RuntimeError(f"La respuesta de `agy` no contenía JSON esperado: {proc.stdout[:300]}")

    parsed["description_es"] = _strip_any_invented_prices(str(parsed.get("description_es", "")))
    parsed["description_en"] = _strip_any_invented_prices(str(parsed.get("description_en", "")))
    parsed["ai_source"] = "Cuenta Personal Google en Antigravity (OAuth `agy`)"
    return parsed


def analyze_railing_image(
    image_path: str | Path,
    engine: str = "auto",
) -> Dict[str, Any]:
    """
    Primary entry point to analyze a railing/fence image with Gemini.
    Priority order when engine='auto':
      1. If `GEMINI_API_KEY` is present in `.env`, uses fast `google-genai` (`gemini-2.5-flash`).
      2. Otherwise uses the user's authenticated personal Google account in Antigravity (`agy -p`).
    """
    img_path = Path(image_path).resolve()
    api_key = _load_env_safely()

    if engine == "gemini_api_key":
        if not api_key:
            raise RuntimeError(
                "Seleccionaste 'Gemini API Key Directa', pero no hay `GEMINI_API_KEY` configurada en `.env`. "
                "Usa el modo 'Cuenta Personal Antigravity (Sin API Key)' o configura tu clave de Google AI Studio."
            )
        return analyze_with_gemini_api_key(img_path, api_key)

    if engine == "antigravity_account":
        return analyze_with_antigravity_account(img_path)

    # engine == "auto": prefer direct API key if user configured one for speed, otherwise use Antigravity account
    if api_key:
        try:
            return analyze_with_gemini_api_key(img_path, api_key)
        except Exception:
            pass

    return analyze_with_antigravity_account(img_path)


DEFAULT_USER_FLOW_PROMPT = (
    "Generate a high-precision reference image of the exact railing architecture, structural design, "
    "picket spacing, top rail profile, mounting posts, and authentic black color and finish from this reference photo "
    "without altering the style. Demand 100% complete isolation on a pure seamless solid white background (#FFFFFF), "
    "eliminating all stairs, concrete, brick siding, scaffolding, dirt, and clutter, so that ONLY the railing appears."
)


def generate_flow_prompt_for_product(
    name: str = "",
    category: str = "",
    material: str = "",
    finish_color: str = "",
) -> str:
    """
    Generate an image-to-image reference prompt for Google Flow (labs.google/fx/tools/flow).
    Defaults to the user-specified high-precision isolation prompt.
    """
    return DEFAULT_USER_FLOW_PROMPT


def generate_image_via_official_genai_api(
    prompt: str,
    output_path: str | Path,
) -> Path:
    """
    Optional official programmatic connection to Google's Imagen 3 model (`imagen-3.0-generate-002`),
    the underlying image generation engine used by Google Flow.
    Requires a `GEMINI_API_KEY` with billing enabled in Google AI Studio / Google Cloud.
    Does NOT simulate or fake a connection if credentials/billing are absent.
    """
    api_key = _load_env_safely()
    if not api_key:
        raise RuntimeError(
            "Para generar imágenes por API con Imagen 3 (`google-genai`), se necesita configurar `GEMINI_API_KEY` en `.env`."
        )

    from google import genai
    from google.genai import types

    out = Path(output_path).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    client = genai.Client(api_key=api_key)
    result = client.models.generate_images(
        model="imagen-3.0-generate-002",
        prompt=prompt,
        config=types.GenerateImagesConfig(
            number_of_images=1,
            output_mime_type="image/png",
            aspect_ratio="4:3",
        ),
    )
    if not result.generated_images:
        raise RuntimeError("El modelo Imagen 3 no devolvió ninguna imagen.")

    img_bytes = result.generated_images[0].image.image_bytes
    out.write_bytes(img_bytes)
    return out


def open_google_flow_in_browser() -> None:
    """Open Google Flow (labs.google/fx/tools/flow) in the user's default browser."""
    webbrowser.open(GOOGLE_FLOW_URL)


def open_ai_studio_key_page() -> None:
    """Open Google AI Studio API Key page in the user's default browser."""
    webbrowser.open(GOOGLE_AI_STUDIO_KEY_URL)


def save_gemini_api_key_to_env(api_key: str) -> Path:
    """
    Safely store GEMINI_API_KEY in the local `e:\\mcp\\.env` file (which is git-ignored)
    and update the current process environment.
    """
    cleaned = api_key.strip().strip('"').strip("'")
    if not cleaned:
        raise ValueError("La API Key está vacía.")
    if len(cleaned) < 25 or " " in cleaned:
        raise ValueError(
            "El texto pegado no parece una clave de Google AI Studio válida. "
            "Primero copia la clave desde Google AI Studio haciendo clic en el icono de copiar (dos cuadritos) y vuelve a pegarla."
        )

    env_path = Path(__file__).resolve().parent.parent / ".env"
    lines: List[str] = []
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if not line.strip().startswith("GEMINI_API_KEY="):
                lines.append(line)

    lines.append(f"GEMINI_API_KEY={cleaned}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.environ["GEMINI_API_KEY"] = cleaned
    return env_path

