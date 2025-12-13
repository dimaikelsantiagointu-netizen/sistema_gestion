document.addEventListener('DOMContentLoaded', function() {

    // =========================================================
    // 1. COMPONENTES DEL DOM
    // =========================================================
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

    // =========================================================
    // 2. LÓGICA DE CARGA DE ARCHIVOS
    // =========================================================

    // Manejar la selección de archivos
    excelFileInput.addEventListener('change', function() {
        if (this.files.length > 0) {
            const fileName = this.files[0].name;
            uploadStatus.textContent = `Archivo seleccionado: ${fileName}`;
            triggerUploadButton.disabled = false;
            triggerUploadButton.textContent = 'Generar Recibos Ahora';
            triggerUploadButton.classList.remove('bg-yellow-600', 'hover:bg-yellow-700', 'bg-gray-400');
            triggerUploadButton.classList.add('bg-green-600', 'hover:bg-green-700');
            generationStatus.textContent = '¡Listo para procesar!';
        } else {
            uploadStatus.textContent = 'Ningún archivo seleccionado.';
            triggerUploadButton.disabled = true;
            triggerUploadButton.textContent = 'Esperando Archivo';
            triggerUploadButton.classList.remove('bg-green-600', 'hover:bg-green-700');
            triggerUploadButton.classList.add('bg-yellow-600', 'hover:bg-yellow-700');
            generationStatus.textContent = 'Presiona para procesar el archivo seleccionado.';
        }
    });

    // Manejar el clic en el botón de subida (que activa el envío del formulario)
    triggerUploadButton.addEventListener('click', function() {
        if (!this.disabled) {
            // Deshabilitar UI durante la subida
            triggerUploadButton.disabled = true;
            triggerUploadButton.textContent = 'Procesando...';
            triggerUploadButton.classList.remove('bg-green-600', 'hover:bg-green-700');
            triggerUploadButton.classList.add('bg-gray-500');
            generationStatus.textContent = 'El procesamiento puede tardar unos segundos...';

            // Enviar el formulario
            uploadForm.submit();
        }
    });


    // =========================================================
    // 3. LÓGICA DE LOGS (Muestra logs de Django y Logs Visuales)
    // =========================================================

    /**
     * Añade un mensaje al área visual de logs.
     * @param {string} message - El mensaje a mostrar.
     * @param {string} type - 'success', 'error', 'warning', 'info'.
     */
    function appendLog(message, type = 'info') {
        const logItem = document.createElement('p');
        const timestamp = new Date().toLocaleTimeString();
        let colorClass = 'text-gray-700';
        let icon = '•';

        switch (type) {
            case 'success':
                colorClass = 'text-green-700 font-semibold';
                icon = '✅';
                break;
            case 'error':
                colorClass = 'text-red-700 font-semibold';
                icon = '❌';
                break;
            case 'warning':
                colorClass = 'text-yellow-700';
                icon = '⚠️';
                break;
            default:
                colorClass = 'text-indigo-700';
                icon = 'ℹ️';
                break;
        }

        logItem.className = `${colorClass} py-0.5`;
        logItem.innerHTML = `[${timestamp}] ${icon} ${message}`;
        logDisplay.appendChild(logItem);

        // Auto-scroll al final del log
        logDisplay.scrollTop = logDisplay.scrollHeight;
    }

    // Capturar y mostrar mensajes de Django
    const djangoMessageCatcher = document.getElementById('django-message-catcher');
    if (djangoMessageCatcher) {
        const messages = djangoMessageCatcher.querySelectorAll('.message-django');
        messages.forEach(msg => {
            // El tipo de Django es "success", "error", etc.
            const type = msg.dataset.type.split(' ').pop(); 
            appendLog(msg.textContent.trim(), type);
        });
        
        // Si se procesó un archivo, actualizar el estado
        if (messages.length > 0) {
            generationStatus.textContent = 'Proceso finalizado. Revisa los logs.';
            triggerUploadButton.textContent = 'Subir Nuevo Archivo';
            triggerUploadButton.classList.remove('bg-gray-500');
            triggerUploadButton.classList.add('bg-yellow-600', 'hover:bg-yellow-700');
            excelFileInput.value = ''; // Limpiar el input para permitir la subida de un nuevo archivo
            uploadStatus.textContent = 'Ningún archivo seleccionado.';
        }
    }


    // =========================================================
    // 4. LÓGICA DEL MODAL DE CONFIRMACIÓN
    // =========================================================

    /**
     * Muestra el modal de confirmación.
     * @param {string} message - El mensaje HTML a mostrar.
     * @param {string} confirmText - Texto para el botón de confirmación.
     * @param {string} color - 'red', 'gray', 'indigo' para el botón.
     * @param {string} formTarget - ID del formulario a enviar (ej: 'anular-form').
     * @param {number|null} reciboId - PK del recibo si la acción es anular.
     */
    function showModal(message, confirmText, color, formTarget, reciboId = null) {
        // 1. Rellenar contenido del modal
        modalMessage.innerHTML = message;
        confirmButton.textContent = confirmText;
        
        // 2. Limpiar y establecer color del botón
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

        // 3. Establecer el formulario destino
        confirmButton.dataset.targetForm = formTarget;

        // 4. *** CORRECCIÓN CLAVE: Asignar el ID del recibo si existe ***
        if (reciboId && formTarget === 'anular-form') {
            anularReciboIdInput.value = reciboId;
        } else {
            // Asegurarse de que el input esté limpio para otras acciones
            anularReciboIdInput.value = ''; 
        }
        // -------------------------------------------------------------

        // 5. Mostrar el modal con transiciones
        modal.style.display = 'block';
        setTimeout(() => {
            modal.style.opacity = '1';
            modalContent.classList.remove('scale-95', 'opacity-0');
            modalContent.classList.add('scale-100', 'opacity-100');
        }, 10);
    }

    // Oculta el modal
    window.hideModal = function() { // Exponer globalmente para el botón 'Cancelar'
        modal.style.opacity = '0';
        modalContent.classList.remove('scale-100', 'opacity-100');
        modalContent.classList.add('scale-95', 'opacity-0');
        setTimeout(() => {
            modal.style.display = 'none';
        }, 300);
    }

    // Manejar clic en el botón de confirmación
    confirmButton.addEventListener('click', function() {
        const targetFormId = this.dataset.targetForm;
        if (targetFormId) {
            // Si es 'clear-visual-logs-button', limpiamos solo el DOM, no enviamos POST
            if (targetFormId === 'clear-logs-form') {
                logDisplay.innerHTML = '<p class="text-gray-400">Log inicial: Listo para cargar archivo.</p>';
                appendLog('Logs visuales han sido limpiados.', 'warning');
            } else {
                // Para las acciones que sí requieren POST (ej: anular)
                document.getElementById(targetFormId).submit();
            }
        }
        hideModal(); 
    });

    // =========================================================
    // 5. LISTENERS DE ACCIÓN (Botones que activan el modal)
    // =========================================================

    // Listener para el botón de ANULAR RECIBO (Tabla del Dashboard)
    document.querySelectorAll('.anular-recibo-btn').forEach(button => {
        button.addEventListener('click', function() {
            showModal(
                this.dataset.message,
                this.dataset.confirmText,
                this.dataset.color,
                'anular-form', // ID del formulario de anulación oculto
                this.dataset.reciboId // El PK del recibo
            );
        });
    });

    // Listener para el botón de LIMPIAR LOGS (Visual)
    document.getElementById('clear-visual-logs-button').addEventListener('click', function() {
        showModal(
            this.dataset.message,
            this.dataset.confirmText,
            this.dataset.color,
            'clear-logs-form' // Usamos un nombre de formulario ficticio para activar el manejo de logs en el confirmButton
        );
    });

    // Si quieres un botón de limpiar logs de la BD (asume que existe un endpoint de Django):
    // document.getElementById('clear-db-logs-button').addEventListener('click', function() {
    //     showModal(
    //         this.dataset.message,
    //         this.dataset.confirmText,
    //         this.dataset.color,
    //         'clear-logs-db-form' // Asume un formulario oculto para la limpieza de BD
    //     );
    // });


});