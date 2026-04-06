const LOG_STORAGE_KEY = 'receipt_logs';

window.hideModal = function() {
    const modal = document.getElementById('confirmation-modal');
    const content = document.getElementById('modal-content');
    if (modal) {
        modal.style.opacity = '0';
        if (content) {
            content.classList.remove('scale-100', 'opacity-100');
            content.classList.add('scale-95', 'opacity-0');
        }
        setTimeout(() => {
            modal.classList.add('hidden');
            const msgElem = document.getElementById('modal-message');
            if (msgElem) msgElem.innerHTML = "";
        }, 300);
    }
};

window.showModal = function(message, confirmText, color, formTarget, reciboId = null) {
    const modal = document.getElementById('confirmation-modal');
    const content = document.getElementById('modal-content');
    const msgElem = document.getElementById('modal-message');
    const btn = document.getElementById('confirm-action-button');
    const inputId = document.getElementById('anular-recibo-id');

    if (!modal || !btn || !msgElem) return;

    msgElem.innerHTML = message;
    btn.textContent = confirmText;
    btn.dataset.targetForm = formTarget;

    if (inputId) {
        inputId.value = reciboId ? reciboId : "";
    }

    btn.className = `px-6 py-2 text-white text-[10px] font-black uppercase rounded-xl transition-all shadow-lg ${
        color === 'red' ? 'bg-red-600 hover:bg-red-700 shadow-red-200' : 'bg-gray-500 hover:bg-gray-600'
    }`;

    modal.classList.remove('hidden');
    void modal.offsetWidth; 
    modal.style.opacity = '1';
    if (content) {
        content.classList.remove('scale-95', 'opacity-0');
        content.classList.add('scale-100', 'opacity-100');
    }
};

document.addEventListener('DOMContentLoaded', function() {
    const excelFileInput = document.getElementById('excel-file-input');
    const uploadStatus = document.getElementById('upload-status');
    const generationStatus = document.getElementById('generation-status');
    const triggerUploadButton = document.getElementById('trigger-upload-button');
    const uploadForm = document.getElementById('upload-form');
    const logDisplay = document.getElementById('log-display');
    const confirmButton = document.getElementById('confirm-action-button');

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

    const urlParams = new URLSearchParams(window.location.search);
    const downloadPks = urlParams.get('download_pks');
    if (downloadPks) {
        const pksArray = downloadPks.split(',');
        let downloadUrl = pksArray.length === 1 
            ? `/recibos/generar-pdf/${pksArray[0]}/` 
            : `/recibos/generar-zip/?pks=${downloadPks}`;
        const link = document.createElement('a');
        link.href = downloadUrl;
        link.target = '_blank';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        appendLog(pksArray.length === 1 ? 'Recibo descargado.' : 'ZIP descargado.', 'success', true);
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    if (excelFileInput) {
        excelFileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                uploadStatus.textContent = this.files[0].name;
                resetUploadButton();
            } else {
                setInitialUploadButtonState();
            }
        });
        triggerUploadButton.addEventListener('click', function() {
            appendLog('Iniciando procesamiento...', 'action', true);
            this.disabled = true;
            this.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Procesando...';
            setTimeout(() => { uploadForm.submit(); }, 150);
        });
    }

    if (confirmButton) {
        confirmButton.addEventListener('click', function() {
            const targetId = this.dataset.targetForm;
            
            // Acción inmediata de cierre
            window.hideModal(); 

            if (targetId === 'clear-logs-form') {
                localStorage.removeItem(LOG_STORAGE_KEY);
                if (logDisplay) {
                    logDisplay.innerHTML = '<div id="log-content-wrapper" class="space-y-2"><p class="text-gray-400 italic">Esperando actividad...</p></div>';
                }
                // No necesitamos recargar la página, solo limpiar visualmente
                appendLog('Historial local borrado.', 'warning', false);
            } else {
                const targetForm = document.getElementById(targetId);
                if (targetForm) {
                    // Solo enviamos el formulario si NO es el de logs
                    setTimeout(() => { targetForm.submit(); }, 250);
                }
            }
        });
    }

    document.querySelectorAll('.anular-recibo-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            window.showModal(
                this.dataset.message, 
                this.dataset.confirmText, 
                this.dataset.color || 'red', 
                'anular-form', 
                this.dataset.reciboId
            );
        });
    });

    const clearLogsBtn = document.getElementById('clear-visual-logs-button');
    if (clearLogsBtn) {
        clearLogsBtn.addEventListener('click', function() {
            window.showModal(
                '¿Deseas limpiar el historial visual de esta sesión?', 
                'Sí, Limpiar', 
                'gray', 
                'clear-logs-form'
            );
        });
    }

    loadPersistedLogs();
});