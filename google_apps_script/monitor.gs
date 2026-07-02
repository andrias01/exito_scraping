/**
 * Monitor Precios Éxito Colombia - Google Apps Script
 * 
 * Este script ejecuta automáticamente el monitoreo de precios
 * realizando peticiones a la API del sistema desplegado en Streamlit.
 * 
 * Configuración:
 *   1. Abre script.google.com
 *   2. Crea un nuevo proyecto y pega este código
 *   3. Configura APP_URL con tu URL de Streamlit
 *   4. Ejecuta setupTrigger() una sola vez para configurar el trigger automático
 */

// ─── Configuración ────────────────────────────────────────────────────────────

const CONFIG = {
  APP_URL: "https://exitoscraping-production.up.railway.app",   // URL del servicio FastAPI en Railway
  FREQUENCY_MINUTES: 30,                      // Frecuencia del trigger (5, 10, 15, 30, 60)
  MAX_RETRIES: 3,                             // Reintentos ante fallo
  RETRY_DELAY_MS: 5000,                       // Delay entre reintentos (ms)
  SHEET_NAME: "Logs",                         // Nombre de la hoja de logs
  TIMEOUT_MS: 30000,                          // Timeout de la petición (ms)
  ALERT_EMAIL: "",                            // Email para alertas (dejar vacío para deshabilitar)
};

// ─── Función principal ────────────────────────────────────────────────────────

/**
 * Función principal que ejecuta el monitoreo.
 * Es invocada automáticamente por el trigger de tiempo.
 */
function runMonitor() {
  const startTime = new Date();
  Logger.log(`[${startTime.toISOString()}] Iniciando monitoreo...`);

  let success = false;
  let responseData = null;
  let errorMessage = null;

  // Intentos con reintentos
  for (let attempt = 1; attempt <= CONFIG.MAX_RETRIES; attempt++) {
    try {
      Logger.log(`Intento ${attempt}/${CONFIG.MAX_RETRIES}`);

      const result = callRunEndpoint();
      
      if (result.success) {
        success = true;
        responseData = result.data;
        Logger.log(`✅ Monitoreo exitoso en intento ${attempt}`);
        Logger.log(`Respuesta: ${JSON.stringify(result.data)}`);
        break;
      } else {
        errorMessage = result.error;
        Logger.log(`⚠️ Intento ${attempt} fallido: ${result.error}`);
      }
    } catch (error) {
      errorMessage = error.toString();
      Logger.log(`❌ Error en intento ${attempt}: ${errorMessage}`);
    }

    if (attempt < CONFIG.MAX_RETRIES) {
      Logger.log(`Esperando ${CONFIG.RETRY_DELAY_MS}ms antes del siguiente intento...`);
      Utilities.sleep(CONFIG.RETRY_DELAY_MS * attempt); // Backoff incremental
    }
  }

  const endTime = new Date();
  const durationMs = endTime - startTime;

  // Registrar en hoja de cálculo
  const logEntry = {
    fecha: startTime.toISOString(),
    exitoso: success,
    duracion_ms: durationMs,
    respuesta: responseData ? JSON.stringify(responseData) : null,
    error: errorMessage,
    intentos: success ? 1 : CONFIG.MAX_RETRIES,
  };

  writeLog(logEntry);

  // Enviar alerta por email si hay error persistente
  if (!success && CONFIG.ALERT_EMAIL) {
    sendErrorAlert(errorMessage, startTime);
  }

  Logger.log(`Monitoreo finalizado en ${durationMs}ms. Exitoso: ${success}`);
}

// ─── Funciones de petición HTTP ───────────────────────────────────────────────

/**
 * Llama al endpoint /run de la API.
 * @returns {{success: boolean, data: object|null, error: string|null}}
 */
function callRunEndpoint() {
  const url = `${CONFIG.APP_URL}/run`;
  
  const options = {
    method: "get",
    muteHttpExceptions: true,
    followRedirects: true,
    headers: {
      "User-Agent": "GoogleAppsScript-MonitorExico/1.0",
      "Accept": "application/json",
    },
  };

  const response = UrlFetchApp.fetch(url, options);
  const statusCode = response.getResponseCode();
  const content = response.getContentText();

  if (statusCode >= 200 && statusCode < 300) {
    try {
      const data = JSON.parse(content);
      return { success: true, data, error: null };
    } catch {
      return { success: true, data: { raw: content }, error: null };
    }
  } else {
    return {
      success: false,
      data: null,
      error: `HTTP ${statusCode}: ${content.substring(0, 200)}`,
    };
  }
}

/**
 * Llama al endpoint /health para verificar disponibilidad.
 * @returns {{online: boolean, latency_ms: number}}
 */
function checkHealth() {
  const url = `${CONFIG.APP_URL}/health`;
  const start = new Date();

  try {
    const response = UrlFetchApp.fetch(url, {
      method: "get",
      muteHttpExceptions: true,
      followRedirects: true,
    });
    const latency = new Date() - start;
    const online = response.getResponseCode() === 200;
    return { online, latency_ms: latency };
  } catch (error) {
    return { online: false, latency_ms: -1, error: error.toString() };
  }
}

// ─── Función de activación (wake-up) ─────────────────────────────────────────

/**
 * Despierta la aplicación Streamlit antes de ejecutar el monitoreo.
 * Streamlit entra en suspensión si no hay usuarios activos.
 */
function wakeUpAndRun() {
  Logger.log("Intentando despertar la aplicación Streamlit...");
  
  // Primera petición a /health para despertar la app
  const health = checkHealth();
  
  if (!health.online) {
    Logger.log("La app está dormida, enviando petición de activación...");
    // Esperar a que la app arranque
    Utilities.sleep(15000);
    
    // Verificar nuevamente
    const healthRetry = checkHealth();
    if (!healthRetry.online) {
      Logger.log("⚠️ La app no respondió después de 15s. Continuando de todas formas...");
    }
  } else {
    Logger.log(`✅ App disponible (latencia: ${health.latency_ms}ms)`);
  }

  // Ejecutar monitoreo
  runMonitor();
}

// ─── Logs en Google Sheets ────────────────────────────────────────────────────

/**
 * Obtiene o crea la hoja de logs.
 * @returns {GoogleAppsScript.Spreadsheet.Sheet}
 */
function getOrCreateSheet() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  let sheet = ss.getSheetByName(CONFIG.SHEET_NAME);
  
  if (!sheet) {
    sheet = ss.insertSheet(CONFIG.SHEET_NAME);
    // Crear encabezados
    const headers = ["Fecha", "Exitoso", "Duración (ms)", "Respuesta", "Error", "Intentos"];
    sheet.appendRow(headers);
    
    // Dar formato al encabezado
    const headerRange = sheet.getRange(1, 1, 1, headers.length);
    headerRange.setBackground("#e53e3e");
    headerRange.setFontColor("white");
    headerRange.setFontWeight("bold");
    
    sheet.setFrozenRows(1);
    sheet.setColumnWidth(1, 180);
    sheet.setColumnWidth(4, 400);
    sheet.setColumnWidth(5, 300);
  }
  
  return sheet;
}

/**
 * Escribe una entrada en el log de Google Sheets.
 * @param {object} entry - Datos del log
 */
function writeLog(entry) {
  try {
    const sheet = getOrCreateSheet();
    
    const row = [
      entry.fecha,
      entry.exitoso ? "✅ Sí" : "❌ No",
      entry.duracion_ms,
      entry.respuesta || "",
      entry.error || "",
      entry.intentos,
    ];
    
    sheet.appendRow(row);
    
    // Colorear la fila según resultado
    const lastRow = sheet.getLastRow();
    const rowRange = sheet.getRange(lastRow, 1, 1, row.length);
    
    if (entry.exitoso) {
      rowRange.setBackground("#c6f6d5"); // Verde claro
    } else {
      rowRange.setBackground("#fed7d7"); // Rojo claro
    }
    
    // Mantener solo los últimos 1000 registros
    const totalRows = sheet.getLastRow();
    if (totalRows > 1001) {
      sheet.deleteRows(2, totalRows - 1001);
    }
    
    Logger.log("Log guardado en Google Sheets.");
  } catch (error) {
    Logger.log(`Error guardando log: ${error}`);
  }
}

// ─── Alertas por email ────────────────────────────────────────────────────────

/**
 * Envía una alerta por email cuando el monitoreo falla repetidamente.
 * @param {string} errorMessage - Mensaje de error
 * @param {Date} fecha - Fecha del fallo
 */
function sendErrorAlert(errorMessage, fecha) {
  if (!CONFIG.ALERT_EMAIL) return;
  
  const subject = "⚠️ Monitor Precios Éxito - Error de monitoreo";
  const body = `
    El sistema de monitoreo de precios ha fallado.
    
    Fecha: ${fecha.toISOString()}
    Error: ${errorMessage}
    URL: ${CONFIG.APP_URL}
    
    Por favor verifica que la API esté funcionando correctamente.
    
    Este email fue enviado automáticamente por Google Apps Script.
  `;
  
  try {
    GmailApp.sendEmail(CONFIG.ALERT_EMAIL, subject, body);
    Logger.log(`Alerta enviada a ${CONFIG.ALERT_EMAIL}`);
  } catch (error) {
    Logger.log(`Error enviando alerta: ${error}`);
  }
}

// ─── Gestión de triggers ──────────────────────────────────────────────────────

/**
 * Configura el trigger automático.
 * Ejecutar esta función UNA SOLA VEZ para activar el monitoreo automático.
 */
function setupTrigger() {
  // Eliminar triggers existentes para evitar duplicados
  removeTriggers();
  
  // Crear nuevo trigger
  ScriptApp.newTrigger("wakeUpAndRun")
    .timeBased()
    .everyMinutes(CONFIG.FREQUENCY_MINUTES)
    .create();
  
  Logger.log(`✅ Trigger configurado: cada ${CONFIG.FREQUENCY_MINUTES} minutos`);
  Logger.log("El monitoreo automático está activo.");
  
  // Registrar la configuración
  const ss = SpreadsheetApp.getActiveSpreadsheet();
  const ui = SpreadsheetApp.getUi();
  ui.alert(
    "✅ Trigger Configurado",
    `El monitoreo se ejecutará automáticamente cada ${CONFIG.FREQUENCY_MINUTES} minutos.\n\nURL: ${CONFIG.APP_URL}`,
    ui.ButtonSet.OK
  );
}

/**
 * Elimina todos los triggers existentes del script.
 */
function removeTriggers() {
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => ScriptApp.deleteTrigger(trigger));
  Logger.log(`${triggers.length} trigger(s) eliminado(s).`);
}

/**
 * Muestra el estado actual de los triggers.
 */
function showTriggerStatus() {
  const triggers = ScriptApp.getProjectTriggers();
  
  if (triggers.length === 0) {
    Logger.log("No hay triggers configurados.");
    return;
  }
  
  triggers.forEach(trigger => {
    Logger.log(
      `Trigger: ${trigger.getHandlerFunction()} | ` +
      `Tipo: ${trigger.getEventType()} | ` +
      `ID: ${trigger.getUniqueId()}`
    );
  });
}

/**
 * Menú personalizado en Google Sheets.
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu("🛒 Monitor Éxito")
    .addItem("▶ Ejecutar ahora", "wakeUpAndRun")
    .addItem("✅ Verificar salud de la app", "checkHealthAndReport")
    .addSeparator()
    .addItem("⚙️ Configurar trigger automático", "setupTrigger")
    .addItem("🛑 Detener monitoreo automático", "removeTriggers")
    .addItem("📊 Ver estado de triggers", "showTriggerStatus")
    .addToUi();
}

/**
 * Verifica la salud y muestra un reporte.
 */
function checkHealthAndReport() {
  const health = checkHealth();
  const ui = SpreadsheetApp.getUi();
  
  const msg = health.online
    ? `✅ La aplicación está activa\nLatencia: ${health.latency_ms}ms\nURL: ${CONFIG.APP_URL}`
    : `❌ La aplicación no responde\nURL: ${CONFIG.APP_URL}\nError: ${health.error || "Timeout"}`;
  
  ui.alert("Estado de la Aplicación", msg, ui.ButtonSet.OK);
}
