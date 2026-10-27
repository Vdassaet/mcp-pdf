/**
 * NJ Fence and Railing — Online Catalog Studio (GitHub Pages Safe Edition)
 *
 * SECURITY ARCHITECTURE:
 * - ZERO API keys are stored in this code or in the GitHub repository.
 * - Any API key entered by the user is stored EXCLUSIVELY in their own browser's
 *   `localStorage` ("njf_gemini_api_key_vault") and never sent anywhere except
 *   directly to Google's official `generativelanguage.googleapis.com` endpoint.
 * - Pricing is strictly user-entered (Per Linear Foot or Per Kit); never invented.
 */

const VAULT_KEY_NAME = "njf_gemini_api_key_vault";
const CATALOG_STORAGE_KEY = "njf_catalog_items_v1";

let currentRawDataUrl = null;
let currentWhiteDataUrl = null;
let catalogItems = [];

document.addEventListener("DOMContentLoaded", () => {
  initVaultStatus();
  loadSavedCatalog();
  bindEvents();
  // Load initial demo railing so the app is immediately visual and testable
  generateDemoRailingPhoto();
});

function initVaultStatus() {
  const savedKey = localStorage.getItem(VAULT_KEY_NAME);
  const badge = document.getElementById("vaultStatusText");
  if (savedKey && savedKey.length >= 25) {
    badge.innerHTML =
      "🟢 <strong>Llave Gemini guardada en tu navegador (Privada):</strong> Lista para analizar fotos (0 llaves en GitHub).";
  } else {
    badge.innerHTML =
      "🔒 <strong>Bóveda Privada del Navegador:</strong> Pega tu <code>GEMINI_API_KEY</code> aquí. Se guarda SOLO en tu PC/navegador, jamás en GitHub.";
  }
}

function bindEvents() {
  document.getElementById("btnSaveVaultKey").addEventListener("click", () => {
    const val = document.getElementById("inputVaultKey").value.trim();
    if (!val) {
      alert("Pega tu GEMINI_API_KEY (empieza por AIzaSy...) antes de guardar.");
      return;
    }
    localStorage.setItem(VAULT_KEY_NAME, val);
    document.getElementById("inputVaultKey").value = "";
    initVaultStatus();
    setStatus("✅ Tu GEMINI_API_KEY quedó guardada únicamente en este navegador (LocalVault). GitHub no tiene acceso a ella.");
  });

  document.getElementById("btnClearVaultKey").addEventListener("click", () => {
    localStorage.removeItem(VAULT_KEY_NAME);
    initVaultStatus();
    setStatus("🔒 Llave eliminada de la memoria de este navegador.");
  });

  document.getElementById("fileInput").addEventListener("change", (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (ev) => {
      currentRawDataUrl = ev.target.result;
      renderRawAndProcessWhite(currentRawDataUrl);
    };
    reader.readAsDataURL(file);
  });

  document.getElementById("btnLoadDemo").addEventListener("click", () => {
    generateDemoRailingPhoto();
  });

  document.getElementById("tolSlider").addEventListener("input", (e) => {
    document.getElementById("tolValLabel").textContent = e.target.value;
  });

  document.getElementById("btnReprocessWhite").addEventListener("click", () => {
    if (currentRawDataUrl) {
      renderRawAndProcessWhite(currentRawDataUrl);
    }
  });

  document.getElementById("btnAnalyzeGemini").addEventListener("click", () => {
    analyzeCurrentImageWithGemini();
  });

  document.getElementById("btnAddCatalog").addEventListener("click", () => {
    saveCurrentProductToCatalog();
  });

  document.getElementById("btnExportPdf").addEventListener("click", () => {
    exportCatalogPdf();
  });

  document.getElementById("btnCopyFlowPrompt").addEventListener("click", () => {
    const txt = document.getElementById("flowPromptBox").value;
    navigator.clipboard.writeText(txt);
    setStatus("📋 Prompt para Google Flow copiado al portapapeles.");
  });
}

function setStatus(msg, isError = false) {
  const el = document.getElementById("statusBanner");
  el.textContent = msg;
  el.style.borderColor = isError ? "#e53e3e" : "#38a169";
  el.style.color = isError ? "#feb2b2" : "#9ae6b4";
}

/**
 * Generate a realistic outdoor site photo of an NJ Fence & Railing ornamental black railing
 * so the user can test white-background isolation and PDF export with 1 click.
 */
function generateDemoRailingPhoto() {
  const c = document.createElement("canvas");
  c.width = 900;
  c.height = 675;
  const ctx = c.getContext("2d");

  // Outdoor sky/stone gradient background
  const grad = ctx.createLinearGradient(0, 0, 0, c.height);
  grad.addColorStop(0, "#cddbe8");
  grad.addColorStop(1, "#dde4eb");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, c.width, c.height);

  const metal = "#1a1e24";
  const highlight = "#454d59";
  const gold = "#c5a044";

  const leftX = 120;
  const rightX = 780;
  const topY = 155;
  const subY = 200;
  const botY = 505;
  const floorY = 555;

  // Posts
  [leftX, rightX].forEach((px) => {
    ctx.fillStyle = metal;
    ctx.fillRect(px - 20, topY - 22, 40, floorY - (topY - 22));
    ctx.fillStyle = highlight;
    ctx.fillRect(px - 10, topY - 18, 3, floorY - topY);
    // Base plate
    ctx.fillStyle = metal;
    ctx.fillRect(px - 32, floorY - 12, 64, 14);
    // Pyramid cap
    ctx.beginPath();
    ctx.moveTo(px - 25, topY - 22);
    ctx.lineTo(px, topY - 42);
    ctx.lineTo(px + 25, topY - 22);
    ctx.closePath();
    ctx.fill();
  });

  // Top, sub, and bottom rails
  ctx.fillStyle = metal;
  ctx.fillRect(leftX + 20, topY, rightX - leftX - 40, 18);
  ctx.fillRect(leftX + 20, subY, rightX - leftX - 40, 12);
  ctx.fillRect(leftX + 20, botY, rightX - leftX - 40, 16);

  // Pickets + decorative rings + gold collars
  const numPickets = 13;
  const span = rightX - leftX - 40;
  const step = span / (numPickets + 1);

  for (let i = 1; i <= numPickets; i++) {
    const bx = Math.round(leftX + 20 + i * step);
    ctx.fillStyle = metal;
    ctx.fillRect(bx - 4, topY + 18, 8, botY - (topY + 18));

    // Ring between topY and subY
    ctx.strokeStyle = metal;
    ctx.lineWidth = 3.5;
    ctx.beginPath();
    ctx.arc(bx, (topY + 18 + subY) / 2, 11, 0, Math.PI * 2);
    ctx.stroke();

    // Alternating gold collar
    if (i % 2 === 1) {
      const my = (subY + 12 + botY) / 2;
      ctx.fillStyle = metal;
      ctx.fillRect(bx - 8, my - 10, 16, 20);
      ctx.strokeStyle = gold;
      ctx.lineWidth = 2;
      ctx.strokeRect(bx - 8, my - 10, 16, 20);
    }
  }

  // Center support foot
  const midX = (leftX + rightX) / 2;
  ctx.fillStyle = metal;
  ctx.fillRect(midX - 6, botY + 16, 12, floorY - (botY + 16));

  currentRawDataUrl = c.toDataURL("image/jpeg", 0.94);
  renderRawAndProcessWhite(currentRawDataUrl);
}

/**
 * Isolate the railing/fence onto a pure white (#FFFFFF) canvas.
 */
function renderRawAndProcessWhite(dataUrl) {
  const rawImg = document.getElementById("rawPreviewImg");
  rawImg.src = dataUrl;

  const img = new Image();
  img.onload = () => {
    const canvas = document.getElementById("whiteCanvas");
    const ctx = canvas.getContext("2d");
    const cw = 800;
    const ch = 600;
    canvas.width = cw;
    canvas.height = ch;

    // Work canvas for pixel segmentation
    const tmp = document.createElement("canvas");
    tmp.width = img.width;
    tmp.height = img.height;
    const tctx = tmp.getContext("2d");
    tctx.drawImage(img, 0, 0);

    const imgData = tctx.getImageData(0, 0, tmp.width, tmp.height);
    const data = imgData.data;
    const w = tmp.width;
    const h = tmp.height;

    // Sample border colors from top and sides
    let rSum = 0, gSum = 0, bSum = 0, count = 0;
    for (let x = 0; x < w; x += 4) {
      const idxTop = x * 4;
      rSum += data[idxTop];
      gSum += data[idxTop + 1];
      bSum += data[idxTop + 2];
      count++;
    }
    const bgR = rSum / count;
    const bgG = gSum / count;
    const bgB = bSum / count;

    const tol = parseFloat(document.getElementById("tolSlider").value || "42");
    const mode = document.getElementById("bgModeSelect").value;

    let minX = w, minY = h, maxX = 0, maxY = 0;

    if (mode !== "studio_frame_white") {
      for (let y = 0; y < h; y++) {
        for (let x = 0; x < w; x++) {
          const idx = (y * w + x) * 4;
          const r = data[idx];
          const g = data[idx + 1];
          const b = data[idx + 2];
          const dist = Math.hypot(r - bgR, g - bgG, b - bgB);
          const lum = 0.299 * r + 0.587 * g + 0.114 * b;

          const isBg =
            mode === "high_contrast_metal_white"
              ? lum > 175
              : dist <= tol * 1.15;

          if (isBg) {
            data[idx] = 255;
            data[idx + 1] = 255;
            data[idx + 2] = 255;
          } else {
            if (x < minX) minX = x;
            if (y < minY) minY = y;
            if (x > maxX) maxX = x;
            if (y > maxY) maxY = y;
          }
        }
      }
      tctx.putImageData(imgData, 0, 0);
    }

    if (maxX <= minX || maxY <= minY) {
      minX = 0;
      minY = 0;
      maxX = w;
      maxY = h;
    }

    // Pure #FFFFFF studio canvas
    ctx.fillStyle = "#FFFFFF";
    ctx.fillRect(0, 0, cw, ch);

    const cropW = maxX - minX;
    const cropH = maxY - minY;
    const pad = 0.1;
    const availW = cw * (1 - pad * 2);
    const availH = ch * (1 - pad * 2);
    const scale = Math.min(availW / cropW, availH / cropH);
    const drawW = cropW * scale;
    const drawH = cropH * scale;
    const ox = (cw - drawW) / 2;
    const oy = (ch - drawH) / 2;

    ctx.drawImage(tmp, minX, minY, cropW, cropH, ox, oy, drawW, drawH);
    currentWhiteDataUrl = canvas.toDataURL("image/png");
  };
  img.src = dataUrl;
}

/**
 * Analyze the uploaded photo with Google Gemini (`gemini-2.5-flash`) using the user's
 * browser-stored API key. Strictly forbids inventing any prices.
 */
async function analyzeCurrentImageWithGemini() {
  if (!currentRawDataUrl) {
    alert("Primero sube una foto de una barandilla.");
    return;
  }

  const apiKey = localStorage.getItem(VAULT_KEY_NAME);
  if (!apiKey) {
    alert(
      "Para analizar desde la versión web, pega primero tu GEMINI_API_KEY en la barra superior 'Bóveda Privada del Navegador' (o usa la aplicación de escritorio en tu PC que ya está conectada a tu cuenta de Antigravity)."
    );
    return;
  }

  const btn = document.getElementById("btnAnalyzeGemini");
  btn.disabled = true;
  btn.textContent = "⏳ Analizando fotografía con Gemini...";
  setStatus("Conectando con Google Gemini 2.5 Flash para describir la barandilla (sin inventar precios)...");

  try {
    const base64Data = currentRawDataUrl.split(",")[1];
    const mimeMatch = currentRawDataUrl.match(/^data:(image\/[a-zA-Z0-9+.-]+);base64,/);
    const mimeType = mimeMatch ? mimeMatch[1] : "image/jpeg";

    const prompt =
      "You are the technical catalog specialist for 'NJ Fence and Railing' (New Jersey & New York). " +
      "Analyze ONLY what is visually present in this railing/fence photograph. " +
      "CRITICAL RULE: NEVER invent, guess, or mention any price or dollar amount. " +
      "Return ONLY a JSON object with keys: name, category, material, finish_color, description_es, description_en, features (array of 4 strings), flow_prompt_suggestion.";

    const resp = await fetch(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key=${encodeURIComponent(apiKey)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [
            {
              parts: [
                { text: prompt },
                { inline_data: { mime_type: mimeType, data: base64Data } },
              ],
            },
          ],
          generationConfig: { responseMimeType: "application/json" },
        }),
      }
    );

    if (!resp.ok) {
      const errText = await resp.text();
      throw new Error(`Error de Gemini API (${resp.status}): ${errText}`);
    }

    const json = await resp.json();
    const rawText = json?.candidates?.[0]?.content?.parts?.[0]?.text || "{}";
    const parsed = JSON.parse(rawText);

    if (parsed.name) document.getElementById("prodName").value = parsed.name;
    if (parsed.category) document.getElementById("prodCategory").value = parsed.category;
    if (parsed.material) document.getElementById("prodMaterial").value = parsed.material;
    if (parsed.finish_color) document.getElementById("prodFinish").value = parsed.finish_color;
    if (parsed.description_es) {
      document.getElementById("prodDescEs").value = String(parsed.description_es).replace(/\$\s*\d+/g, "");
    }
    if (parsed.description_en) {
      document.getElementById("prodDescEn").value = String(parsed.description_en).replace(/\$\s*\d+/g, "");
    }
    if (Array.isArray(parsed.features)) {
      document.getElementById("prodFeatures").value = parsed.features.join("\n");
    }
    if (parsed.flow_prompt_suggestion) {
      document.getElementById("flowPromptBox").value = parsed.flow_prompt_suggestion;
    }

    setStatus("✅ Fotografía analizada con éxito por Google Gemini 2.5 Flash. Ahora introduce tus precios reales.");
  } catch (err) {
    setStatus(`⚠️ ${err.message}`, true);
    alert(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "✨ Analizar Foto con Gemini y Proponer Descripción";
  }
}

/**
 * Parse a user-entered price strictly. Never invents numbers.
 */
function parseStrictUserPrice(rawStr) {
  if (!rawStr) return null;
  const cleaned = String(rawStr).replace(/[$,\s]/g, "");
  if (!cleaned) return null;
  if (!/^\d+(\.\d{1,2})?$/.test(cleaned)) {
    throw new Error(`Precio inválido '${rawStr}'. Introduce únicamente números reales (ej. 54.00).`);
  }
  const num = parseFloat(cleaned);
  if (num <= 0) throw new Error("El precio debe ser mayor que 0.");
  return num;
}

function saveCurrentProductToCatalog() {
  const name = document.getElementById("prodName").value.trim();
  if (!name) {
    alert("Introduce el nombre del modelo o analízalo primero con Gemini.");
    return;
  }
  if (!currentWhiteDataUrl) {
    alert("Sube y procesa primero una fotografía sobre fondo blanco.");
    return;
  }

  const pricingMode = document.getElementById("pricingMode").value;
  let priceLf = null;
  let priceKit = null;

  try {
    priceLf = parseStrictUserPrice(document.getElementById("priceLf").value);
    priceKit = parseStrictUserPrice(document.getElementById("priceKit").value);
  } catch (err) {
    alert(err.message);
    return;
  }

  if (pricingMode === "per_linear_foot" && priceLf === null) {
    alert("Seleccionaste 'Por Pie Lineal'. Introduce el precio exacto por pie lineal (no inventamos cifras).");
    return;
  }
  if (pricingMode === "per_kit" && priceKit === null) {
    alert("Seleccionaste 'Por Kit'. Introduce el precio exacto por kit (no inventamos cifras).");
    return;
  }
  if (pricingMode === "both" && (priceLf === null || priceKit === null)) {
    alert("Seleccionaste 'Ambos'. Introduce tanto el precio por pie lineal como por kit.");
    return;
  }

  const sku = document.getElementById("prodSku").value.trim() || `NJF-${Math.floor(100 + Math.random() * 900)}`;
  const item = {
    sku,
    name,
    category: document.getElementById("prodCategory").value,
    material: document.getElementById("prodMaterial").value.trim(),
    finish: document.getElementById("prodFinish").value.trim(),
    descEs: document.getElementById("prodDescEs").value.trim(),
    descEn: document.getElementById("prodDescEn").value.trim(),
    features: document
      .getElementById("prodFeatures")
      .value.split("\n")
      .map((s) => s.trim())
      .filter(Boolean),
    pricingMode,
    priceLf,
    priceKit,
    kitNote: document.getElementById("kitNote").value.trim(),
    whiteImage: currentWhiteDataUrl,
  };

  const idx = catalogItems.findIndex((x) => x.sku === item.sku);
  if (idx >= 0) {
    catalogItems[idx] = item;
  } else {
    catalogItems.push(item);
  }

  localStorage.setItem(CATALOG_STORAGE_KEY, JSON.stringify(catalogItems));
  renderCatalogList();
  setStatus(`✅ Modelo '${item.name}' (${item.sku}) añadido al catálogo con sus precios exactos.`);
}

function loadSavedCatalog() {
  try {
    const raw = localStorage.getItem(CATALOG_STORAGE_KEY);
    if (raw) {
      catalogItems = JSON.parse(raw);
    }
  } catch (_) {
    catalogItems = [];
  }
  renderCatalogList();
}

function formatItemPricingText(item) {
  const parts = [];
  if (
    (item.pricingMode === "per_linear_foot" || item.pricingMode === "both") &&
    typeof item.priceLf === "number"
  ) {
    parts.push(`$${item.priceLf.toFixed(2)} USD / Pie Lineal (LF)`);
  }
  if (
    (item.pricingMode === "per_kit" || item.pricingMode === "both") &&
    typeof item.priceKit === "number"
  ) {
    parts.push(`$${item.priceKit.toFixed(2)} USD / Kit Completo`);
  }
  if (parts.length === 0) {
    parts.push("Cotización Bajo Pedido / Price Upon Request");
  }
  return parts.join("  |  ");
}

function renderCatalogList() {
  const container = document.getElementById("catalogListContainer");
  document.getElementById("catalogCount").textContent = catalogItems.length;
  container.innerHTML = "";

  if (catalogItems.length === 0) {
    container.innerHTML =
      '<p style="color:#a0aec0;font-size:0.9rem;">No hay productos en el catálogo todavía. Guarda un producto usando el formulario superior.</p>';
    return;
  }

  catalogItems.forEach((item, index) => {
    const div = document.createElement("div");
    div.className = "catalog-item";
    div.innerHTML = `
      <img src="${item.whiteImage}" alt="${item.name}" />
      <div class="catalog-item-info">
        <h4>${index + 1}. ${item.name} [${item.sku}] — ${item.category}</h4>
        <div class="catalog-item-price">💲 ${formatItemPricingText(item)}</div>
        <div style="font-size:0.82rem;color:#cbd5e0;">${item.descEs || item.descEn || ""}</div>
      </div>
      <button class="btn btn-danger" data-sku="${item.sku}">🗑️ Eliminar</button>
    `;
    div.querySelector("button").addEventListener("click", () => {
      catalogItems = catalogItems.filter((x) => x.sku !== item.sku);
      localStorage.setItem(CATALOG_STORAGE_KEY, JSON.stringify(catalogItems));
      renderCatalogList();
    });
    container.appendChild(div);
  });
}

async function exportCatalogPdf() {
  if (catalogItems.length === 0) {
    alert("Añade al menos un producto al catálogo antes de generar el PDF.");
    return;
  }

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ unit: "pt", format: "letter" });
  const pageW = doc.internal.pageSize.getWidth();
  const pageH = doc.internal.pageSize.getHeight();

  // Corporate Header Banner
  doc.setFillColor(20, 28, 43);
  doc.rect(36, 32, pageW - 72, 74, "F");
  doc.setFillColor(200, 157, 69);
  doc.rect(36, 104, pageW - 72, 3, "F");

  doc.setTextColor(255, 255, 255);
  doc.setFont("helvetica", "bold");
  doc.setFontSize(18);
  doc.text("NJ Fence and Railing", 50, 58);

  doc.setTextColor(200, 157, 69);
  doc.setFontSize(11);
  doc.text("Catálogo Oficial de Barandillas y Cercas / Product & Pricing Catalog", 50, 76);

  doc.setTextColor(226, 232, 240);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.text("New Jersey & New York Metro Area  |  sales@njfenceandrailing.com", 50, 93);

  let y = 124;

  catalogItems.forEach((item, idx) => {
    const cardH = 195;
    if (y + cardH > pageH - 55) {
      doc.addPage();
      y = 45;
    }

    // Card Box
    doc.setDrawColor(220, 226, 236);
    doc.setFillColor(247, 249, 252);
    doc.rect(36, y, pageW - 72, cardH, "FD");

    // White photo box (#FFFFFF)
    doc.setFillColor(255, 255, 255);
    doc.rect(44, y + 10, 185, cardH - 20, "FD");
    try {
      doc.addImage(item.whiteImage, "PNG", 50, y + 16, 173, cardH - 42);
    } catch (_) {}

    doc.setTextColor(74, 85, 104);
    doc.setFontSize(7.5);
    doc.text(`SKU: ${item.sku} | FONDO BLANCO (#FFFFFF)`, 54, y + cardH - 15);

    // Product info on right
    const rx = 242;
    const maxW = pageW - rx - 48;
    let ry = y + 24;

    doc.setTextColor(20, 28, 43);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(12);
    const titleLines = doc.splitTextToSize(`${idx + 1}. ${item.name}`, maxW);
    doc.text(titleLines, rx, ry);
    ry += titleLines.length * 14 + 2;

    doc.setTextColor(36, 50, 74);
    doc.setFontSize(8.5);
    doc.text(
      `Categoría: ${item.category}  •  Material: ${item.material || "N/A"}  •  Acabado: ${item.finish || "N/A"}`,
      rx,
      ry
    );
    ry += 14;

    doc.setTextColor(26, 32, 44);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8.8);
    if (item.descEs) {
      const esLines = doc.splitTextToSize(`ES: ${item.descEs}`, maxW);
      doc.text(esLines.slice(0, 3), rx, ry);
      ry += Math.min(3, esLines.length) * 11 + 4;
    }
    if (item.descEn) {
      const enLines = doc.splitTextToSize(`EN: ${item.descEn}`, maxW);
      doc.text(enLines.slice(0, 3), rx, ry);
      ry += Math.min(3, enLines.length) * 11 + 6;
    }

    // Strict Pricing Box
    doc.setFillColor(255, 253, 247);
    doc.setDrawColor(212, 175, 55);
    doc.rect(rx, y + cardH - 52, maxW, 42, "FD");

    doc.setTextColor(20, 28, 43);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(10.5);
    doc.text(formatItemPricingText(item), rx + 10, y + cardH - 32);

    if (item.kitNote) {
      doc.setFont("helvetica", "italic");
      doc.setFontSize(8);
      doc.setTextColor(74, 85, 104);
      doc.text(`Nota: ${item.kitNote.substring(0, 85)}`, rx + 10, y + cardH - 17);
    }

    y += cardH + 14;
  });

  doc.save("NJ_Fence_and_Railing_Catalog.pdf");
}
