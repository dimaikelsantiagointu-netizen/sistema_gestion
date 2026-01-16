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

    // Componentes Específicos para Modificar Recibo
    const formActionInput = document.getElementById('form-action'); 
    const anularReciboModificarBtn = document.getElementById('anular-recibo-btn'); // Corregido ID

    // Componentes de Filtros
    const filterForm = document.getElementById('filter-form'); 

    // 2. LÓGICA DE LOGS (Persistencia con LocalStorage)
    const LOG_STORAGE_KEY = 'receipt_logs';

    function saveLog(message, type) {
        const logs = JSON.parse(localStorage.getItem(LOG_STORAGE_KEY) || '[]');
        // Limitar a los últimos 50 logs para no saturar el storage
        if (logs.length > 50) logs.shift();
        logs.push({ message, type, time: new Date().toLocaleTimeString() });
        localStorage.setItem(LOG_STORAGE_KEY, JSON.stringify(logs));
    }
    
    /**
     * Añade un mensaje al área visual de logs.
     */
    function appendLog(message, type = 'info', persist = true) {
        if (!logDisplay) return;

        // Eliminar el mensaje de "esperando actividad" si existe
        if (logDisplay.querySelector('.italic')) {
            logDisplay.innerHTML = '<div id="log-content-wrapper" class="space-y-2"></div>';
        }

        const wrapper = logDisplay.querySelector('#log-content-wrapper') || logDisplay;
        const logItem = document.createElement('p');
        const timestamp = new Date().toLocaleTimeString();
        let colorClass = 'text-gray-700';
        let icon = '•';

        switch (type) {
            case 'success':
                colorClass = 'text-green-700 font-bold';
                icon = '🟢';
                break;
            case 'error':
                colorClass = 'text-red-700 font-bold';
                icon = '🔴';
                break;
            case 'warning':
                colorClass = 'text-yellow-700 font-semibold';
                icon = '⚠️';
                break;
            case 'action':
                colorClass = 'text-blue-600 font-semibold';
                icon = '🚀';
                break;
            case 'client':
                colorClass = 'text-gray-500';
                icon = '💻';
                break;
            default:
                colorClass = 'text-indigo-700';
                icon = 'ℹ️';
                break;
        }

        logItem.className = `${colorClass} py-1 border-b border-gray-100 last:border-0 leading-tight`;
        logItem.innerHTML = `<span class="opacity-50 text-[8px]">[${timestamp}]</span> ${icon} ${message}`;
        wrapper.appendChild(logItem);

        // AUTO-SCROLL: Baja automáticamente al último mensaje
        logDisplay.scrollTo({
            top: logDisplay.scrollHeight,
            behavior: 'smooth'
        });

        if (persist) saveLog(message, type);
    }

    function loadPersistedLogs() {
        const logs = JSON.parse(localStorage.getItem(LOG_STORAGE_KEY) || '[]');
        if (logs.length > 0) {
            appendLog(`Restaurando sesión: ${logs.length} registros encontrados.`, 'client', false);
            logs.forEach(log => appendLog(log.message, log.type, false));
        }
    }

    // 3. CAPTURAR MENSAJES DE DJANGO (Backend)
    const djangoMessageCatcher = document.getElementById('django-message-catcher');
    if (djangoMessageCatcher) {
        const messages = djangoMessageCatcher.querySelectorAll('.message-django');
        messages.forEach(msg => {
            const type = msg.dataset.type;
            appendLog(msg.textContent.trim(), type, true); 
        });
        
        if (messages.length > 0 && generationStatus) {
            generationStatus.textContent = 'Proceso completado.';
            excelFileInput.value = ''; 
        }
    }

    // 4. LÓGICA DE CARGA DE ARCHIVOS
    if (excelFileInput) {
        excelFileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                const fileName = this.files[0].name;
                appendLog(`Archivo listo: "${fileName}"`, 'client', false);
                uploadStatus.textContent = fileName;
                triggerUploadButton.disabled = false;
                triggerUploadButton.className = 'mt-4 w-full py-3 bg-intu-blue text-white text-[10px] font-black uppercase tracking-widest rounded-xl transition-all flex justify-center items-center shadow-lg';
                triggerUploadButton.innerHTML = '<i class="fas fa-cloud-upload-alt mr-2"></i> Procesar Ahora';
            }
        });

        triggerUploadButton.addEventListener('click', function() {
            appendLog('Iniciando subida y generación masiva...', 'action', true);
            this.disabled = true;
            this.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Procesando...';
            uploadForm.submit();
        });
    }

    // 5. LÓGICA DEL MODAL UNIVERSAL
    window.showModal = function(message, confirmText, color, formTarget, reciboId = null) {
        if (!modal) return;
        modalMessage.innerHTML = message;
        confirmButton.textContent = confirmText;
        confirmButton.dataset.targetForm = formTarget;
        
        // Ajuste de color dinámico
        confirmButton.className = `px-6 py-2 text-white text-[10px] font-black uppercase rounded-xl transition ${color === 'red' ? 'bg-red-600 hover:bg-red-700' : 'bg-gray-500 hover:bg-gray-600'}`;

        if (reciboId) anularReciboIdInput.value = reciboId;

        modal.classList.remove('hidden');
        setTimeout(() => {
            modal.style.opacity = '1';
            modalContent.classList.remove('scale-95', 'opacity-0');
        }, 10);
    }

    window.hideModal = function() { 
        modal.style.opacity = '0';
        modalContent.classList.add('scale-95', 'opacity-0');
        setTimeout(() => modal.classList.add('hidden'), 300);
    }

    confirmButton.addEventListener('click', function() {
        const target = this.dataset.targetForm;
        if (target === 'clear-logs-form') {
            localStorage.removeItem(LOG_STORAGE_KEY);
            logDisplay.innerHTML = '<p class="text-gray-400 italic">Logs limpiados correctamente.</p>';
        } else if (target === 'anular-form' || target === 'modificar-recibo-form') {
            appendLog('Enviando solicitud de anulación...', 'warning', true);
            if (formActionInput) formActionInput.value = 'anular';
            const form = document.getElementById(target) || document.querySelector('form');
            form.submit();
        }
        hideModal();
    });

    // 6. EVENTOS DE BOTONES
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

    // Inicializar
    loadPersistedLogs();
});