document.addEventListener("DOMContentLoaded", async () => {
    // Cargar configuración guardada
    const settings = await chrome.storage.sync.get([
        'endpointUrl', 'authToken', 'extractLineups', 'extractStreaks',
        'extractHomeStats', 'extractAwayStats', 'extractIncidents',
        'extractHeatmaps', 'autoSend'
    ]);

    document.getElementById('endpointUrl').value = settings.endpointUrl || '';
    document.getElementById('authToken').value = settings.authToken || '';
    document.getElementById('extractLineups').checked = settings.extractLineups !== false;
    document.getElementById('extractStreaks').checked = settings.extractStreaks !== false;
    document.getElementById('extractHomeStats').checked = settings.extractHomeStats !== false;
    document.getElementById('extractAwayStats').checked = settings.extractAwayStats !== false;
    document.getElementById('extractIncidents').checked = settings.extractIncidents === true;
    document.getElementById('extractHeatmaps').checked = settings.extractHeatmaps === true;
    document.getElementById('autoSend').value = settings.autoSend || 'never';

    // Presets de endpoint
    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.getElementById('endpointUrl').value = btn.dataset.url;
        });
    });

    // Guardar
    document.getElementById('saveBtn').addEventListener('click', async () => {
        const newSettings = {
            endpointUrl: document.getElementById('endpointUrl').value.trim(),
            authToken: document.getElementById('authToken').value.trim(),
            extractLineups: document.getElementById('extractLineups').checked,
            extractStreaks: document.getElementById('extractStreaks').checked,
            extractHomeStats: document.getElementById('extractHomeStats').checked,
            extractAwayStats: document.getElementById('extractAwayStats').checked,
            extractIncidents: document.getElementById('extractIncidents').checked,
            extractHeatmaps: document.getElementById('extractHeatmaps').checked,
            autoSend: document.getElementById('autoSend').value,
        };

        await chrome.storage.sync.set(newSettings);
        showStatus('success', '✅ Configuración guardada correctamente');
    });

    // Probar conexión
    document.getElementById('testBtn').addEventListener('click', async () => {
        const url = document.getElementById('endpointUrl').value.trim();
        if (!url) {
            showStatus('error', '❌ Ingresa una URL de endpoint primero');
            return;
        }

        showStatus('loading', '⏳ Probando conexión...');

        try {
            const response = await fetch(url, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
            });

            if (response.ok || response.status === 405) {
                showStatus('success', '✅ Conexión exitosa con Sherlock');
            } else {
                showStatus('error', `⚠️ Respuesta inesperada: ${response.status}`);
            }
        } catch (error) {
            showStatus('error', `❌ Error de conexión: ${error.message}`);
        }
    });
});

function showStatus(type, message) {
    const status = document.getElementById('status');
    status.textContent = message;
    status.className = `status show ${type}`;

    if (type === 'success' || type === 'error') {
        setTimeout(() => status.classList.remove('show'), 5000);
    }
}
