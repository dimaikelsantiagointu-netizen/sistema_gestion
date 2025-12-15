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
    const anularReciboModificarBtn = document.getElementById('anular-recibo-btn-modificar');

    // Componentes de Filtros
    const filterForm = document.getElementById('filter-form'); 

    // 3. LÓGICA DE LOGS (Persistencia con LocalStorage)
    const LOG_STORAGE_KEY = 'receipt_logs';

    function saveLog(message, type) {
        const logs = JSON.parse(localStorage.getItem(LOG_STORAGE_KEY) || '[]');
        logs.push({ message, type });
        localStorage.setItem(LOG_STORAGE_KEY, JSON.stringify(logs));
    }
    
    /**
     * Añade un mensaje al área visual de logs y lo persiste si es necesario.
     * @param {string} message 
     * @param {string} type 
     * @param {boolean} persist 
     */
    function appendLog(message, type = 'info', persist = true) {
        const logItem = document.createElement('p');
        const timestamp = new Date().toLocaleTimeString();
        let colorClass = 'text-gray-700';
        let icon = '•';

        switch (type) {
            case 'success':
                colorClass = 'text-green-700 font-bold';
                icon = '🟢 RESULTADO:';
                break;
            case 'error':
                colorClass = 'text-red-700 font-bold';
                icon = '🔴 ERROR:';
                break;
            case 'warning':
                colorClass = 'text-yellow-700 font-semibold';
                icon = '⚠️ ADVERTENCIA:';
                break;
            case 'action':
                colorClass = 'text-blue-600 font-semibold';
                icon = '🚀 INICIANDO:';
                break;
            case 'client':
                colorClass = 'text-gray-600';
                icon = '💻 CLIENTE:';
                break;
            default: // info
                colorClass = 'text-indigo-700';
                icon = 'ℹ️ INFO:';
                break;
        }

        logItem.className = `${colorClass} py-0.5 text-sm`;
        logItem.innerHTML = `[${timestamp}] ${icon} ${message}`;
        logDisplay.appendChild(logItem);

        logDisplay.scrollTop = logDisplay.scrollHeight;

        if (persist) {
            saveLog(message, type);
        }
    }

    /**
     * Carga y muestra los logs persistentes al iniciar la página.
     */
    function loadPersistedLogs() {
        const logs = JSON.parse(localStorage.getItem(LOG_STORAGE_KEY) || '[]');
        
        if (logs.length === 0) {
             appendLog('Módulo de logs cargado. Esperando acción.', 'info', false);
        } else {
            appendLog(`--- Logs Anteriores (${logs.length} entradas) ---`, 'info', false);
            logs.forEach(log => {
                appendLog(log.message, log.type, false);
            });
            appendLog('--- Fin de Logs Anteriores. Listo para nuevas acciones. ---', 'info', false);
        }
    }


    // Capturar y mostrar mensajes de Django
    const djangoMessageCatcher = document.getElementById('django-message-catcher');
    if (djangoMessageCatcher) {
        const messages = djangoMessageCatcher.querySelectorAll('.message-django');
        messages.forEach(msg => {
            let type = msg.dataset.type.split(' ').pop();
            if (type === 'success') type = 'success';
            if (type === 'error') type = 'error';
            if (type === 'warning') type = 'warning';
            
            appendLog(msg.textContent.trim(), type, true); 
        });
        
        if (messages.length > 0) {
            generationStatus.textContent = 'Proceso finalizado. Revisa los logs.';
            triggerUploadButton.textContent = 'Subir Nuevo Archivo';
            triggerUploadButton.classList.remove('bg-gray-500');
            triggerUploadButton.classList.add('bg-yellow-600', 'hover:bg-yellow-700');
            excelFileInput.value = ''; 
            uploadStatus.textContent = 'Ningún archivo seleccionado.';
        }
    }


    // LÓGICA DE CARGA DE ARCHIVOS 

    // Manejar la selección de archivos
    excelFileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            const fileName = this.files[0].name;
            
            appendLog(`Archivo detectado: "${fileName}". Interfaz lista para subida.`, 'client', false);

            uploadStatus.textContent = `Archivo seleccionado: ${fileName}`;
            triggerUploadButton.disabled = false;
            triggerUploadButton.textContent = 'Generar Recibos Ahora';
            triggerUploadButton.classList.remove('bg-yellow-600', 'hover:bg-yellow-700', 'bg-gray-400');
            triggerUploadButton.classList.add('bg-green-600', 'hover:bg-green-700');
            generationStatus.textContent = '¡Listo para procesar!';
            
        } else {
            appendLog('Selección de archivo cancelada.', 'client', false);

            uploadStatus.textContent = 'Ningún archivo seleccionado.';
            triggerUploadButton.disabled = true;
            triggerUploadButton.textContent = 'Esperando Archivo';
            triggerUploadButton.classList.remove('bg-green-600', 'hover:bg-green-700');
            triggerUploadButton.classList.add('bg-yellow-600', 'hover:bg-yellow-700');
            generationStatus.textContent = 'Presiona para procesar el archivo seleccionado.';
        }
    });

    triggerUploadButton.addEventListener('click', function() {
        if (!this.disabled) {
            triggerUploadButton.disabled = true;
            triggerUploadButton.textContent = 'Procesando...';
            triggerUploadButton.classList.remove('bg-green-600', 'hover:bg-green-700');
            triggerUploadButton.classList.add('bg-gray-500');
            generationStatus.textContent = 'El procesamiento puede tardar unos segundos...';
            
            appendLog('Solicitud de REGISTRO: Enviando archivo. El servidor está procesando la creación de recibos y planillas.', 'action', true);

            // Enviar el formulario
            uploadForm.submit();
        }
    });
    
    // 5. LÓGICA DE FILTROS Y REPORTES

    if (filterForm) {
        filterForm.addEventListener('submit', function(e) {
            
            const formData = new FormData(filterForm);
            const action = formData.get('action'); 

            if (action === 'filter' || !action) {
                
                // --- Lógica para construir el mensaje de filtros ---
                const searchQ = formData.get('q') || '';
                const estado = formData.get('estado') || '';
                const fechaInicio = formData.get('fecha_inicio') || '';
                const fechaFin = formData.get('fecha_fin') || '';
                
                const categories = [];
                filterForm.querySelectorAll('input[type="checkbox"]:checked').forEach(checkbox => {
                    categories.push(checkbox.dataset.label || checkbox.name);
                });
                
                let detalles = [];
                if (searchQ) detalles.push(`Búsqueda: "${searchQ}"`);
                if (estado) detalles.push(`Estado: ${estado}`);
                if (fechaInicio || fechaFin) {
                    detalles.push(`Período: ${fechaInicio || 'Inicio'} a ${fechaFin || 'Fin'}`);
                }
                if (categories.length > 0) {
                    detalles.push(`Categorías: ${categories.join(', ')}`);
                }
                
                let logMessage = '';

                if (detalles.length > 0) {
                    logMessage = `APLICANDO FILTROS: ${detalles.join(' | ')}. Recargando tabla...`;
                } else {
                    logMessage = 'Filtros de búsqueda vacíos. Se está recargando la tabla principal (sin filtros).';
                }

                // Log: Filtros Aplicados
                appendLog(logMessage, 'action', true);
            } 
            
            // GENERAR REPORTE EXCEL ---
            else if (action === 'excel') {
                appendLog('SOLICITUD DE REPORTE: Generando archivo Excel (XLSX) con los filtros actuales...', 'action', true);
            }
            
            // GENERAR REPORTE PDF ---
            else if (action === 'pdf') {
                appendLog('SOLICITUD DE REPORTE: Generando documento PDF con los filtros actuales...', 'action', true);
            }
        });
    }


    // 4. LÓGICA DEL MODAL DE CONFIRMACIÓN (Anulación)

    /**
     * Muestra el modal de confirmación.
     */
    window.showModal = function(message, confirmText, color, formTarget, reciboId = null) {
        // ... Lógica para mostrar modal  ...
        modalMessage.innerHTML = message;
        confirmButton.textContent = confirmText;
        
        confirmButton.className = 'px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white transition duration-150';
        
        switch (color) {
            case 'red':
                confirmButton.classList.add('bg-red-600', 'hover:bg-red-700');
                break;
            case 'gray':
                confirmButton.classList.add('bg-gray-500', 'hover:bg-gray-600');
                break;
            default:
                confirmButton.classList.add('bg-indigo-600', 'hover:bg-indigo-700');
        }

        confirmButton.dataset.targetForm = formTarget;

        if (reciboId && formTarget === 'anular-form') {
            anularReciboIdInput.value = reciboId;
        } else {
            anularReciboIdInput.value = ''; 
        }

        modal.style.display = 'block';
        setTimeout(() => {
            modal.style.opacity = '1';
            modalContent.classList.remove('scale-95', 'opacity-0');
            modalContent.classList.add('scale-100', 'opacity-100');
        }, 10);
    }

    // Oculta el modal 
    window.hideModal = function() { 
        modal.style.opacity = '0';
        modalContent.classList.remove('scale-100', 'opacity-100');
        modalContent.classList.add('scale-95', 'opacity-0');
        setTimeout(() => {
            modal.style.display = 'none';
        }, 300);
    }

    // Manejar clic en el botón de confirmación (Logs Dinámicos para Anulación)
    confirmButton.addEventListener('click', function() {
        const targetFormId = this.dataset.targetForm;

        if (targetFormId) {
            // Caso 1: Anulación desde modificar_recibo.html
            if (targetFormId === 'modificar-recibo-form') {
                
                appendLog('Solicitud de ANULACIÓN: Confirmación recibida. Enviando al servidor para la cancelación del recibo.', 'action', true);

                if (formActionInput) {
                    formActionInput.value = 'anular';
                }
                
                document.getElementById('modificar-recibo-form').submit();
            }

            // Caso 2: Limpiar Logs Visuales (Dashboard)
            else if (targetFormId === 'clear-logs-form') {
                localStorage.removeItem(LOG_STORAGE_KEY);
                
                logDisplay.innerHTML = ''; 
                appendLog('Logs visuales y persistentes han sido limpiados.', 'client', false);
            } 
            
            // Caso 3: Anulación desde el Dashboard ('anular-form')
            else {
                const reciboId = anularReciboIdInput.value;
                
                appendLog(`Solicitud de ANULACIÓN: Confirmación recibida. Procesando Recibo ID ${reciboId}...`, 'action', true);
                
                document.getElementById(targetFormId).submit();
            }
        }
        hideModal(); 
    });

    // 6. LISTENERS DE ACCIÓN

    // Listener para el botón de ANULAR RECIBO (Tabla del Dashboard)
    document.querySelectorAll('.anular-recibo-btn').forEach(button => {
        button.addEventListener('click', function() {
            showModal(
                this.dataset.message,
                this.dataset.confirmText,
                this.dataset.color,
                'anular-form', 
                this.dataset.reciboId 
            );
        });
    });

    // Listener para el botón de ANULAR RECIBO (Página Modificar Recibo)
     if (anularReciboModificarBtn) {
        anularReciboModificarBtn.addEventListener('click', function() {
            showModal(
                this.dataset.message,
                this.dataset.confirmText,
                this.dataset.color,
                'modificar-recibo-form', 
                null 
            );
        });
    }

    // Listener para el botón de LIMPIAR LOGS (Visual)
    document.getElementById('clear-visual-logs-button').addEventListener('click', function() {
        showModal(
            this.dataset.message,
            this.dataset.confirmText,
            this.dataset.color,
            'clear-logs-form' 
        );
    });

    loadPersistedLogs();
});