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

const DEFAULT_MODEL_NAME = "Modern Black  Stair and Porch RG Railing Style";
const DEFAULT_CATEGORY = "Aluminum Railing";
const DEFAULT_MATERIAL = "Metal or Aluminum";
const DEFAULT_FINISH = "Any Color Powder coating";

let currentRawDataUrl = null;
let currentWhiteDataUrl = null;
let catalogItems = [];

document.addEventListener("DOMContentLoaded", () => {
  initVaultStatus();
  loadSavedCatalog();
  bindEvents();
  // Load initial demo railing so the studio is visual and testable immediately
  generateDemoRailingPhoto();
});

function initVaultStatus() {
  const savedKey = localStorage.getItem(VAULT_KEY_NAME);
  const badge = document.getElementById("vaultStatusText");
  if (savedKey && savedKey.length >= 25) {
    badge.innerHTML =
      "🟢 <strong>Gemini Key active in your browser (Private):</strong> Ready to analyze photos (0 keys stored on GitHub).";
  } else {
    badge.innerHTML =
      "🔒 <strong>Private Browser Vault:</strong> Paste your <code>GEMINI_API_KEY</code> here. Saved locally in your browser, NEVER sent to GitHub.";
  }
}

/**
 * Auto-incrementing SKU generator.
 * If RS-1 exists, generates RS-2, RS-3, etc.
 */
function getNextSku(prefix = "RS-") {
  let maxNum = 0;
  const regex = new RegExp(`^${prefix}(\\d+)$`, "i");
  catalogItems.forEach((it) => {
    const sku = (it.sku || "").trim();
    const match = sku.match(regex);
    if (match) {
      const num = parseInt(match[1], 10);
      if (num > maxNum) maxNum = num;
    }
  });
  return `${prefix}${maxNum + 1}`;
}

function updateSkuFieldIfSequential() {
  const skuEl = document.getElementById("prodSku");
  const nextSku = getNextSku("RS-");
  // Only auto-update if empty or matching RS pattern
  if (!skuEl.value.trim() || /^RS-\d+$/i.test(skuEl.value.trim())) {
    skuEl.value = nextSku;
  }
}

function bindEvents() {
  document.getElementById("btnSaveVaultKey").addEventListener("click", () => {
    const val = document.getElementById("inputVaultKey").value.trim();
    if (!val) {
      alert("Please paste your GEMINI_API_KEY into the box before saving.");
      return;
    }
    localStorage.setItem(VAULT_KEY_NAME, val);
    document.getElementById("inputVaultKey").value = "";
    initVaultStatus();
    setStatus("✅ Your GEMINI_API_KEY is saved safely in this browser (LocalVault). GitHub has zero access to it.");
  });

  document.getElementById("btnClearVaultKey").addEventListener("click", () => {
    localStorage.removeItem(VAULT_KEY_NAME);
    initVaultStatus();
    setStatus("🔒 Key removed from this browser memory.");
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
    setStatus("📋 Prompt for Google Flow copied to clipboard.");
  });
}

function setStatus(msg, isError = false) {
  const el = document.getElementById("statusBanner");
  el.textContent = msg;
  el.style.borderColor = isError ? "#e53e3e" : "#38a169";
  el.style.color = isError ? "#feb2b2" : "#9ae6b4";
}

/**
 * Generate a realistic outdoor site photo of a modern black railing
 * so the user can test white-background isolation and PDF export with 1 click.
 */
function generateDemoRailingPhoto() {
  const c = document.createElement("canvas");
  c.width = 900;
  c.height = 675;
  const ctx = c.getContext("2d");

  // Outdoor background
  const grad = ctx.createLinearGradient(0, 0, 0, c.height);
  grad.addColorStop(0, "#cddbe8");
  grad.addColorStop(1, "#dde4eb");
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, c.width, c.height);

  const metal = "#1a1e24";
  const highlight = "#454d59";

  const leftX = 120;
  const rightX = 780;
  const topY = 155;
  const botY = 505;
  const floorY = 555;

  // Structural Posts
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
    ctx.fillStyle = metal;
    ctx.fill();
  });

  // Top Handrail
  ctx.fillStyle = metal;
  ctx.fillRect(leftX - 25, topY - 18, rightX - leftX + 50, 24);
  ctx.fillStyle = highlight;
  ctx.fillRect(leftX - 25, topY - 16, rightX - leftX + 50, 4);

  // Bottom Rail
  ctx.fillStyle = metal;
  ctx.fillRect(leftX - 10, botY, rightX - leftX + 20, 16);

  // Vertical Pickets (Pickets spacing)
  const picketCount = 17;
  const picketStep = (rightX - leftX - 40) / (picketCount + 1);
  for (let i = 1; i <= picketCount; i++) {
    const x = leftX + 20 + i * picketStep;
    ctx.fillStyle = metal;
    ctx.fillRect(x - 5, topY + 6, 10, botY - (topY + 6));
    ctx.fillStyle = highlight;
    ctx.fillRect(x - 4, topY + 6, 2, botY - (topY + 6));
  }

  // Shadow on floor
  ctx.fillStyle = "rgba(0,0,0,0.25)";
  ctx.fillRect(leftX - 45, floorY, rightX - leftX + 90, 8);

  currentRawDataUrl = c.toDataURL("image/jpeg", 0.92);
  renderRawAndProcessWhite(currentRawDataUrl);
}

/**
 * Process the photo onto a pure white background (#FFFFFF) with studio framing
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
 * Generate a strict image-to-image reference prompt for Google Flow (labs.google/fx/tools/flow).
 * Strictly preserves the railing style, geometry, and color while removing all environmental clutter.
 */
function generateFlowPrompt(name, material, finishColor) {
  const modelTitle = (name || DEFAULT_MODEL_NAME).trim();
  const mat = (material || DEFAULT_MATERIAL).trim();
  const col = (finishColor || DEFAULT_FINISH).trim();
  return (
    `Commercial product catalog studio photograph based on the reference photo. ` +
    `STRICTLY PRESERVE the exact architectural design, picket spacing, top rail profile, ` +
    `mounting post geometry, and authentic ${col} finish of this ${modelTitle} (${mat}). ` +
    `DO NOT alter, redesign, or replace the railing style. ` +
    `ISOLATION: The railing must appear COMPLETELY ALONE on a seamless, pure solid white background (#FFFFFF). ` +
    `ELIMINATE ALL environmental surroundings: NO concrete stairs, NO house siding, NO bricks, ` +
    `NO scaffolding, NO caution tape, and NO ground dirt. ` +
    `ONLY the isolated railing structure is present, centered with balanced padding and a very soft, ` +
    `natural floor contact shadow directly under the mounting base plates. ` +
    `Studio softbox lighting, razor-sharp architectural metalwork details, 8k resolution.`
  );
}

/**
 * Analyze the uploaded photo with Google Gemini using the user's
 * browser-stored API key. Preserves user-pinned default specifications.
 */
async function analyzeCurrentImageWithGemini() {
  if (!currentRawDataUrl) {
    alert("Please upload a photo of a railing first.");
    return;
  }

  const apiKey = localStorage.getItem(VAULT_KEY_NAME);
  if (!apiKey) {
    alert(
      "To analyze from the web version, please paste your GEMINI_API_KEY in the top 'Private Browser Vault' bar."
    );
    return;
  }

  const btn = document.getElementById("btnAnalyzeGemini");
  btn.disabled = true;
  btn.textContent = "⏳ Analyzing photo with Gemini...";
  setStatus("Connecting with Google Gemini to analyze product features (no price fabrication)...");

  try {
    const base64Data = currentRawDataUrl.split(",")[1];
    const mimeMatch = currentRawDataUrl.match(/^data:(image\/[a-zA-Z0-9+.-]+);base64,/);
    const mimeType = mimeMatch ? mimeMatch[1] : "image/jpeg";

    const prompt =
      "You are the technical catalog specialist for 'NJ Fence and Railing' (New Jersey & New York). " +
      "Analyze ONLY what is visually present in this railing/fence photograph. " +
      "CRITICAL RULE 1: NEVER invent, guess, or mention any price or dollar amount. " +
      "CRITICAL RULE 2: For 'flow_prompt_suggestion', generate a high-precision reference prompt in English for Google Flow (labs.google/fx/tools/flow). It MUST instruct Google Flow to strictly preserve the exact railing architecture, structural design, picket spacing, top rail profile, mounting posts, and authentic color/finish from this reference photo without altering the style, and MUST demand 100% complete isolation on a pure seamless solid white background (#FFFFFF), eliminating all stairs, concrete, siding, scaffolding, dirt, and clutter, so that ONLY the railing appears. " +
      "Return ONLY a JSON object with keys: name, category, material, finish_color, description_es, description_en, features (array of 4 strings in English), flow_prompt_suggestion.";

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
      throw new Error(`Gemini API Error (${resp.status}): ${errText}`);
    }

    const json = await resp.json();
    const rawText = json?.candidates?.[0]?.content?.parts?.[0]?.text || "{}";
    const parsed = JSON.parse(rawText);

    // Maintain user-specified default specification values
    const nameEl = document.getElementById("prodName");
    const matEl = document.getElementById("prodMaterial");
    const colEl = document.getElementById("prodFinish");

    if (!nameEl.value.trim() || nameEl.value.trim() === DEFAULT_MODEL_NAME) {
      nameEl.value = DEFAULT_MODEL_NAME;
    }
    if (!matEl.value.trim() || matEl.value.trim() === DEFAULT_MATERIAL) {
      matEl.value = DEFAULT_MATERIAL;
    }
    if (!colEl.value.trim() || colEl.value.trim() === DEFAULT_FINISH) {
      colEl.value = DEFAULT_FINISH;
    }

    if (parsed.description_en) {
      document.getElementById("prodDescEn").value = String(parsed.description_en).replace(/\$\s*\d+/g, "");
    }
    if (Array.isArray(parsed.features) && parsed.features.length > 0) {
      document.getElementById("prodFeatures").value = parsed.features.join("\n");
    }

    const flowPrompt = parsed.flow_prompt_suggestion || generateFlowPrompt(
      nameEl.value,
      matEl.value,
      colEl.value
    );
    document.getElementById("flowPromptBox").value = flowPrompt;

    setStatus("✅ Photo successfully analyzed by Gemini. Standard specifications preserved.");
  } catch (err) {
    setStatus(`⚠️ ${err.message}`, true);
    alert(err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = "✨ STEP 3: Analyze Photo with Google Gemini";
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
    throw new Error(`Invalid price value '${rawStr}'. Please enter exact numerical values only (e.g. 54.00).`);
  }
  const num = parseFloat(cleaned);
  if (num <= 0) throw new Error("Price must be greater than 0.");
  return num;
}

function saveCurrentProductToCatalog() {
  const name = document.getElementById("prodName").value.trim() || DEFAULT_MODEL_NAME;
  if (!currentWhiteDataUrl) {
    alert("Please upload and process a railing photograph on a white background first.");
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
    alert("You selected 'Per Linear Foot'. Please enter the exact price per linear foot.");
    return;
  }
  if (pricingMode === "per_kit" && priceKit === null) {
    alert("You selected 'Per Full Kit'. Please enter the exact price per complete kit.");
    return;
  }
  if (pricingMode === "both" && (priceLf === null || priceKit === null)) {
    alert("You selected 'Both'. Please enter both the price per linear foot and per kit.");
    return;
  }

  const currentSku = document.getElementById("prodSku").value.trim() || getNextSku("RS-");
  const item = {
    sku: currentSku,
    name,
    category: document.getElementById("prodCategory").value,
    material: document.getElementById("prodMaterial").value.trim() || DEFAULT_MATERIAL,
    finish: document.getElementById("prodFinish").value.trim() || DEFAULT_FINISH,
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

  const idx = catalogItems.findIndex((x) => x.sku.toLowerCase() === item.sku.toLowerCase());
  if (idx >= 0) {
    catalogItems[idx] = item;
  } else {
    catalogItems.push(item);
  }

  localStorage.setItem(CATALOG_STORAGE_KEY, JSON.stringify(catalogItems));
  renderCatalogList();

  // Auto-increment to the next SKU (e.g. RS-1 -> RS-2 -> RS-3) for the next item
  const nextSku = getNextSku("RS-");
  document.getElementById("prodSku").value = nextSku;

  setStatus(`✅ Product '${item.name}' [${item.sku}] saved to catalog. Next SKU automatically set to ${nextSku}.`);
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
  // Ensure the SKU input reflects the next available code on load
  updateSkuFieldIfSequential();
}

function formatItemPricingText(item) {
  const parts = [];
  if (
    (item.pricingMode === "per_linear_foot" || item.pricingMode === "both") &&
    typeof item.priceLf === "number"
  ) {
    parts.push(`$${item.priceLf.toFixed(2)} USD / Linear Foot (LF)`);
  }
  if (
    (item.pricingMode === "per_kit" || item.pricingMode === "both") &&
    typeof item.priceKit === "number"
  ) {
    parts.push(`$${item.priceKit.toFixed(2)} USD / Complete Kit`);
  }
  if (parts.length === 0) {
    parts.push("Price Upon Request");
  }
  return parts.join("  |  ");
}

function renderCatalogList() {
  const container = document.getElementById("catalogListContainer");
  document.getElementById("catalogCount").textContent = catalogItems.length;
  container.innerHTML = "";

  if (catalogItems.length === 0) {
    container.innerHTML =
      '<p style="color:#a0aec0;font-size:0.9rem;">No products in the catalog yet. Save a product using the form above.</p>';
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
        <div style="font-size:0.82rem;color:#cbd5e0;">Material: ${item.material} • Finish: ${item.finish}</div>
        <div style="font-size:0.82rem;color:#a0aec0;margin-top:2px;">${item.descEn || ""}</div>
      </div>
      <button class="btn btn-danger" data-sku="${item.sku}">🗑️ Delete</button>
    `;
    div.querySelector("button").addEventListener("click", () => {
      catalogItems = catalogItems.filter((x) => x.sku !== item.sku);
      localStorage.setItem(CATALOG_STORAGE_KEY, JSON.stringify(catalogItems));
      renderCatalogList();
      updateSkuFieldIfSequential();
    });
    container.appendChild(div);
  });
}

async function exportCatalogPdf() {
  if (catalogItems.length === 0) {
    alert("Please add at least one product to the catalog before exporting the PDF.");
    return;
  }

  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ unit: "pt", format: "letter" });
  const pageW = doc.internal.pageSize.getWidth();
  const pageH = doc.internal.pageSize.getHeight();

  // Corporate Header Banner (English)
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
  doc.text("Official Product & Pricing Catalog", 50, 76);

  doc.setTextColor(226, 232, 240);
  doc.setFont("helvetica", "normal");
  doc.setFontSize(9);
  doc.text("New Jersey & New York Metro Area  |  sales@njfenceandrailing.com  |  (973) 555-0199", 50, 93);

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
    doc.text(`SKU: ${item.sku} | PURE WHITE BACKGROUND (#FFFFFF)`, 54, y + cardH - 15);

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
      `Category: ${item.category}  •  Material: ${item.material || "Metal or Aluminum"}  •  Finish: ${item.finish || "Any Color Powder coating"}`,
      rx,
      ry
    );
    ry += 14;

    doc.setTextColor(26, 32, 44);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8.8);
    if (item.descEn) {
      const enLines = doc.splitTextToSize(item.descEn, maxW);
      doc.text(enLines.slice(0, 3), rx, ry);
      ry += Math.min(3, enLines.length) * 11 + 4;
    }

    // Pricing box
    doc.setDrawColor(212, 175, 55);
    doc.setFillColor(255, 253, 247);
    const priceBoxH = item.kitNote ? 48 : 34;
    doc.rect(rx, ry + 2, maxW, priceBoxH, "FD");

    doc.setTextColor(36, 50, 74);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(8);
    doc.text("PRICING SPECIFICATION:", rx + 8, ry + 14);

    doc.setTextColor(183, 121, 31);
    doc.setFontSize(9);
    doc.text(formatItemPricingText(item), rx + 8, ry + 27);

    if (item.kitNote) {
      doc.setTextColor(74, 85, 104);
      doc.setFont("helvetica", "italic");
      doc.setFontSize(7.5);
      doc.text(`Includes: ${item.kitNote}`, rx + 8, ry + 41);
    }

    y += cardH + 12;
  });

  // Footer on each page
  const pageCount = doc.internal.getNumberOfPages();
  for (let i = 1; i <= pageCount; i++) {
    doc.setPage(i);
    doc.setDrawColor(200, 157, 69);
    doc.line(36, pageH - 32, pageW - 36, pageH - 32);
    doc.setFontSize(7.5);
    doc.setTextColor(113, 128, 150);
    doc.text(
      "NJ Fence and Railing • Exact USD Pricing • Taxes and installation quoted per site measurements.",
      36,
      pageH - 20
    );
    doc.text(`Page ${i} of ${pageCount}`, pageW - 80, pageH - 20);
  }

  doc.save("NJ_Fence_and_Railing_Product_Catalog.pdf");
  setStatus("📄 Official PDF Catalog downloaded successfully.");
}
