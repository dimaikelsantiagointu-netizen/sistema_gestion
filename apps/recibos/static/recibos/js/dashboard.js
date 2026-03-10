document.addEventListener('DOMContentLoaded', function() {

    // 1. COMPONENTES DEL DOM
    const excelFileInput = document.getElementById('excel-file-input');
    const uploadStatus = document.getElementById('upload-status');
    const generationStatus = document.getElementById('generation-status');
    const triggerUploadButton = document.getElementById('trigger-upload-button');
    const uploadForm = document.getElementById('upload-form');
    const logDisplay = document.getElementById('log-display');

    // Modal Components
    const modal = document.getElementById('confirmation-modal');
    const modalContent = document.getElementById('modal-content');
    const modalMessage = document.getElementById('modal-message');
    const confirmButton = document.getElementById('confirm-action-button');
    const anularReciboIdInput = document.getElementById('anular-recibo-id');

    // Componentes Específicos
    const formActionInput = document.getElementById('form-action'); 
    const anularReciboModificarBtn = document.getElementById('anular-recibo-btn');

    const LOG_STORAGE_KEY = 'receipt_logs';

    // --- FUNCIONES DE APOYO ---

    function resetUploadButton() {
        if (triggerUploadButton) {
            triggerUploadButton.disabled = false;
            triggerUploadButton.className = 'mt-4 w-full py-3 bg-intu-blue text-white text-[10px] font-black uppercase tracking-widest rounded-xl transition-all flex justify-center items-center shadow-lg';
            triggerUploadButton.innerHTML = '<i class="fas fa-cloud-upload-alt mr-2"></i> Procesar Ahora';
        }
    }

    function setInitialUploadButtonState() {
        if (triggerUploadButton) {
            triggerUploadButton.disabled = true;
            triggerUploadButton.className = 'mt-4 w-full py-3 bg-gray-100 text-gray-400 text-[10px] font-black uppercase tracking-widest rounded-xl transition-all flex justify-center items-center';
            triggerUploadButton.innerHTML = '<i class="fas fa-arrow-up mr-2"></i> Esperando Archivo';
        }
    }

    // 2. LÓGICA DE LOGS
    function saveLog(message, type) {
        const logs = JSON.parse(localStorage.getItem(LOG_STORAGE_KEY) || '[]');
        if (logs.length > 50) logs.shift();
        logs.push({ message, type, time: new Date().toLocaleTimeString() });
        localStorage.setItem(LOG_STORAGE_KEY, JSON.stringify(logs));
    }
    
    function appendLog(message, type = 'info', persist = true) {
        if (!logDisplay) return;

        if (logDisplay.querySelector('.italic')) {
            logDisplay.innerHTML = '<div id="log-content-wrapper" class="space-y-2"></div>';
        }

        const wrapper = logDisplay.querySelector('#log-content-wrapper') || logDisplay;
        const logItem = document.createElement('p');
        const timestamp = new Date().toLocaleTimeString();
        let colorClass = 'text-gray-700';
        let icon = '•';

        switch (type) {
            case 'success': colorClass = 'text-green-700 font-bold'; icon = '🟢'; break;
            case 'error': colorClass = 'text-red-700 font-bold'; icon = '🔴'; break;
            case 'warning': colorClass = 'text-yellow-700 font-semibold'; icon = '⚠️'; break;
            case 'action': colorClass = 'text-blue-600 font-semibold'; icon = '🚀'; break;
            case 'client': colorClass = 'text-gray-500'; icon = '💻'; break;
            default: colorClass = 'text-indigo-700'; icon = 'ℹ️'; break;
        }

        logItem.className = `${colorClass} py-1 border-b border-gray-100 last:border-0 leading-tight`;
        logItem.innerHTML = `<span class="opacity-50 text-[8px]">[${timestamp}]</span> ${icon} ${message}`;
        wrapper.appendChild(logItem);

        logDisplay.scrollTo({ top: logDisplay.scrollHeight, behavior: 'smooth' });
        if (persist) saveLog(message, type);
    }

    function loadPersistedLogs() {
        const logs = JSON.parse(localStorage.getItem(LOG_STORAGE_KEY) || '[]');
        if (logs.length > 0) {
            appendLog(`Restaurando sesión: ${logs.length} registros encontrados.`, 'client', false);
            logs.forEach(log => appendLog(log.message, log.type, false));
        }
    }

    // 3. CAPTURAR MENSAJES DE DJANGO Y AUTO-DESCARGA
    const djangoMessageCatcher = document.getElementById('django-message-catcher');
    if (djangoMessageCatcher) {
        const messages = djangoMessageCatcher.querySelectorAll('.message-django');
        messages.forEach(msg => {
            appendLog(msg.textContent.trim(), msg.dataset.type, true); 
        });
        
        if (messages.length > 0) {
            if (generationStatus) generationStatus.textContent = 'Proceso completado.';
            if (excelFileInput) excelFileInput.value = ''; 
            resetUploadButton();
        }
    }

    // --- NUEVA LÓGICA DE DESCARGA AUTOMÁTICA ---
const urlParams = new URLSearchParams(window.location.search);
const downloadPks = urlParams.get('download_pks');

if (downloadPks) {
    const pksArray = downloadPks.split(',');
    let downloadUrl = '';

    if (pksArray.length === 1) {
        // Ajusta esta URL a la ruta real de tu PDF
        downloadUrl = `/recibos/generar-pdf/${pksArray[0]}/`; 
    } else {
        // Ajusta esta URL a la ruta real de tu ZIP
        downloadUrl = `/recibos/generar-zip/?pks=${downloadPks}`;
    }

    if (downloadUrl) {
        // MÉTODO DE DESCARGA SEGURO (Evita bloqueos de popups)
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.target = '_blank';
        link.download = ''; 
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // MENSAJE DE LOG CORREGIDO
        const logMsg = pksArray.length === 1 
            ? 'Recibo generado y descargado correctamente.' 
            : 'Archivo comprimido (ZIP) generado y descargado correctamente.';
        
        appendLog(logMsg, 'success', true);
        
        // Limpiar la URL para evitar descargas infinitas
        const cleanUrl = window.location.pathname;
        window.history.replaceState({}, document.title, cleanUrl);
    }
}

    // 4. LÓGICA DE CARGA DE ARCHIVOS
    if (excelFileInput) {
        excelFileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                const fileName = this.files[0].name;
                appendLog(`Archivo listo: "${fileName}"`, 'client', false);
                uploadStatus.textContent = fileName;
                resetUploadButton();
            } else {
                setInitialUploadButtonState();
            }
        });

        triggerUploadButton.addEventListener('click', function() {
            appendLog('Enviando archivo al servidor...', 'action', true);
            this.disabled = true;
            this.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Procesando...';
            
            setTimeout(() => { uploadForm.submit(); }, 150);
        });
    }

    // 5. SEGURO DE PERSISTENCIA (Pageshow)
    window.addEventListener('pageshow', function(event) {
        if (!excelFileInput || excelFileInput.value === "") {
            setInitialUploadButtonState();
        } else {
            resetUploadButton();
        }
    });

// 6. LÓGICA DEL MODAL UNIVERSAL
window.showModal = function(message, confirmText, color, formTarget, reciboId = null) {
    if (!modal) return;
    
    modalMessage.innerHTML = message;
    confirmButton.textContent = confirmText;
    confirmButton.dataset.targetForm = formTarget;
    
    if (anularReciboIdInput) {
        anularReciboIdInput.value = reciboId ? reciboId : "";
    }

    confirmButton.className = `px-6 py-2 text-white text-[10px] font-black uppercase rounded-xl transition ${
        color === 'red' ? 'bg-red-600 hover:bg-red-700 shadow-lg shadow-red-200' : 'bg-gray-500 hover:bg-gray-600'
    }`;

    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.style.opacity = '1';
        modalContent.classList.remove('scale-95', 'opacity-0');
    }, 10);
}

confirmButton.addEventListener('click', function() {
    const targetId = this.dataset.targetForm;
    
    if (targetId === 'clear-logs-form') {
        localStorage.removeItem(LOG_STORAGE_KEY);
        if (logDisplay) logDisplay.innerHTML = '<p class="text-gray-400 italic text-[10px]">Logs limpiados correctamente.</p>';
    } else {
        const targetForm = document.getElementById(targetId);
        
        if (targetForm) {
            appendLog(`Ejecutando acción: ${targetId}...`, 'action', true);
            
            const actionInput = targetForm.querySelector('input[name="action"]');
            if (actionInput) actionInput.value = 'anular';
            
            targetForm.submit();
        } else {
            console.error(`Error crítico: No se encontró el formulario #${targetId}`);
            appendLog('Error: Formulario de destino no encontrado.', 'error', true);
        }
    }
    hideModal();
});

    // 7. EVENTOS DE BOTONES DE TABLA
    document.querySelectorAll('.anular-recibo-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            showModal(this.dataset.message, this.dataset.confirmText, this.dataset.color, 'anular-form', this.dataset.reciboId);
        });
    });

    if (anularReciboModificarBtn) {
        anularReciboModificarBtn.addEventListener('click', function() {
            showModal('¿Estás seguro de anular este recibo?', 'Sí, Anular', 'red', 'modificar-recibo-form');
        });
    }

    const clearLogsBtn = document.getElementById('clear-visual-logs-button');
    if (clearLogsBtn) {
        clearLogsBtn.addEventListener('click', function() {
            showModal(this.dataset.message, this.dataset.confirmText, 'gray', 'clear-logs-form');
        });
    }

    // Inicializar aplicación
    loadPersistedLogs();
});