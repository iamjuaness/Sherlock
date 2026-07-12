// settings.js - Configuración de la extensión Watson

document.addEventListener("DOMContentLoaded", async () => {
  await loadSettings();
  setupEventListeners();
});

// Cargar configuración guardada
async function loadSettings() {
  const result = await chrome.storage.sync.get([
    "endpointUrl",
    "authToken",
    "extractLineups",
    "extractStreaks",
    "extractHomeStats",
    "extractAwayStats",
    "extractIncidents",
    "extractHeatmaps",
    "extractMatchResults",
    "autoSend",
  ]);

  // Endpoint
  if (result.endpointUrl) {
    document.getElementById("endpointUrl").value = result.endpointUrl;
  }
  if (result.authToken) {
    document.getElementById("authToken").value = result.authToken;
  }

  // Checkboxes de extracción
  document.getElementById("extractLineups").checked =
    result.extractLineups !== false;
  document.getElementById("extractStreaks").checked =
    result.extractStreaks !== false;
  document.getElementById("extractHomeStats").checked =
    result.extractHomeStats !== false;
  document.getElementById("extractAwayStats").checked =
    result.extractAwayStats !== false;
  document.getElementById("extractIncidents").checked =
    result.extractIncidents === true;
  document.getElementById("extractHeatmaps").checked =
    result.extractHeatmaps === true;
  document.getElementById("extractMatchResults").checked =
    result.extractMatchResults !== false;
  document.getElementById("autoSend").value = result.autoSend || "never";

  // Auto-send
  document.getElementById("autoSend").value = result.autoSend || "never";
}

// Configurar event listeners
function setupEventListeners() {
  document.getElementById("btnSave").addEventListener("click", saveSettings);
  document.getElementById("btnTest").addEventListener("click", testConnection);
  document.getElementById("btnReset").addEventListener("click", resetSettings);
}

// Guardar configuración
async function saveSettings() {
  const endpointUrl = document.getElementById("endpointUrl").value.trim();
  const authToken = document.getElementById("authToken").value.trim();

  // Validar URL
  if (endpointUrl) {
    try {
      new URL(endpointUrl);
    } catch {
      showStatus("❌ La URL del endpoint no es válida", "error");
      return;
    }
  }

  const settings = {
    endpointUrl: endpointUrl || "",
    authToken: authToken || "",
    extractLineups: document.getElementById("extractLineups").checked,
    extractStreaks: document.getElementById("extractStreaks").checked,
    extractHomeStats: document.getElementById("extractHomeStats").checked,
    extractAwayStats: document.getElementById("extractAwayStats").checked,
    extractIncidents: document.getElementById("extractIncidents").checked,
    extractHeatmaps: document.getElementById("extractHeatmaps").checked,
    extractMatchResults: document.getElementById("extractMatchResults").checked,
    autoSend: document.getElementById("autoSend").value,
  };

  try {
    await chrome.storage.sync.set(settings);
    showStatus("✅ Configuración guardada exitosamente", "success");
  } catch (error) {
    showStatus("❌ Error guardando: " + error.message, "error");
  }
}

// Probar conexión con el endpoint
async function testConnection() {
  const endpointUrl = document.getElementById("endpointUrl").value.trim();
  const authToken = document.getElementById("authToken").value.trim();

  if (!endpointUrl) {
    showStatus("❌ Ingresa primero una URL de endpoint", "error");
    return;
  }

  showStatus("🧪 Probando conexión...", "loading");

  const testPayload = {
    test: true,
    timestamp: new Date().toISOString(),
    message: "Watson - Test de conexión",
  };

  const headers = {
    "Content-Type": "application/json",
    "X-Source": "sofascore-extractor",
    "X-Extractor-Version": "1.1.0",
    "X-Test": "true",
  };

  if (authToken) {
    headers["Authorization"] =
      authToken.startsWith("Bearer") || authToken.startsWith("Basic")
        ? authToken
        : `Bearer ${authToken}`;
  }

  try {
    const response = await fetch(endpointUrl, {
      method: "POST",
      headers,
      body: JSON.stringify(testPayload),
    });

    if (response.ok) {
      showStatus(
        `✅ Conexión exitosa!<br>` +
          `Status: ${response.status} ${response.statusText}<br>` +
          `Headers enviados: ${Object.keys(headers).join(", ")}`,
        "success",
      );
    } else {
      showStatus(
        `⚠️ El endpoint respondió con error<br>` +
          `Status: ${response.status} ${response.statusText}<br>` +
          `Verifica que tu endpoint acepte POST con JSON.`,
        "error",
      );
    }
  } catch (error) {
    showStatus(
      `❌ Error de conexión: ${error.message}<br>` +
        `Verifica que la URL sea accesible y que no haya bloqueos CORS.`,
      "error",
    );
  }
}

// Restaurar configuración por defecto
async function resetSettings() {
  if (!confirm("¿Estás seguro de restaurar la configuración por defecto?")) {
    return;
  }

  const defaults = {
    endpointUrl: "",
    authToken: "",
    extractLineups: true,
    extractStreaks: true,
    extractHomeStats: true,
    extractAwayStats: true,
    extractIncidents: false,
    extractHeatmaps: false,
    extractMatchResults: true,
    autoSend: "never",
  };

  try {
    await chrome.storage.sync.set(defaults);
    await loadSettings();
    showStatus("✅ Configuración restaurada", "success");
  } catch (error) {
    showStatus("❌ Error: " + error.message, "error");
  }
}

// Mostrar mensaje de estado
function showStatus(message, type) {
  const status = document.getElementById("status");
  status.innerHTML = message.replace(/\n/g, "<br>");
  status.className = "status show " + type;

  if (type !== "loading") {
    setTimeout(() => {
      status.classList.remove("show");
    }, 6000);
  }
}
