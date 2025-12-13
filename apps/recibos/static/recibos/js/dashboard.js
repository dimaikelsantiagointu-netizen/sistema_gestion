// =================================================================
// 1. VARIABLES GLOBALES Y UTILIDADES
// =================================================================

// Elementos del Modal
const modal = document.getElementById('confirmation-modal');
const modalContent = document.getElementById('modal-content');
const modalTitle = document.getElementById('modal-title');
const modalMessage = document.getElementById('modal-message');
const confirmButton = document.getElementById('confirm-action-button');

// Elementos de Carga
const fileInput = document.getElementById('excel-file-input');
const uploadStatus = document.getElementById('upload-status');
const triggerUploadButton = document.getElementById('trigger-upload-button');
const uploadForm = document.getElementById('upload-form');
const logDisplay = document.getElementById('log-display'); // Declaración principal

// Formularios Ocultos
const anularForm = document.getElementById('anular-form');
const clearLogsForm = document.getElementById('clear-logs-form'); 

// Botón de Logs Visuales
const clearVisualLogsButton = document.getElementById('clear-visual-logs-button'); // Declaración principal

let currentFormToSubmit = null; // Variable para rastrear qué formulario debe enviarse


// =======================================================
// 2. FUNCIONALIDAD DE LOGS VISUALES
// =======================================================

/**
 * Agrega un mensaje al panel de logs con estilos de color.
 * Esta función es la que genera todas las entradas.
 * @param {string} message - El texto del mensaje.
 * @param {string} type - 'success', 'error', 'warning', 'info', o 'default'.
 */
function logMessage(message, type = 'default') {
    if (!logDisplay) return;

    const newMessage = document.createElement('p');
    newMessage.textContent = `[${new Date().toLocaleTimeString()}] ${message}`;

    // Definición de clases de Tailwind según el tipo
    let classColor = 'text-gray-700';
    
    switch (type) {
        case 'success':
            classColor = 'text-green-600 font-bold';
            break;
        case 'error':
            classColor = 'text-red-600 font-bold';
            break;
        case 'warning':
            classColor = 'text-yellow-600';
            break;
        case 'info':
            classColor = 'text-blue-600';
            break;
        case 'default':
        default:
            classColor = 'text-gray-700';
            break;
    }

    newMessage.classList.add('log-entry', classColor);
    
    // Añadir el mensaje al inicio del log para ver lo más reciente
    logDisplay.prepend(newMessage); 
}


// =================================================================
// 3. FUNCIONES DEL MODAL (Hechas globales para acceso en HTML)
// =================================================================

window.showModal = function(title, messageHtml, confirmText, targetAction, confirmColor) {
    modalTitle.textContent = title;

    // Formatear mensaje para negritas
    const formattedMessage = messageHtml.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    modalMessage.innerHTML = formattedMessage;
    confirmButton.textContent = confirmText;

    // Aplicar color y resetear clases
    confirmButton.className = 'px-4 py-2 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white transition duration-150';
    if (confirmColor === 'red') {
        confirmButton.classList.add('bg-red-600', 'hover:bg-red-700');
    } else if (confirmColor === 'gray') {
        confirmButton.classList.add('bg-gray-500', 'hover:bg-gray-600');
    } else if (confirmColor === 'yellow') {
        confirmButton.classList.add('bg-yellow-600', 'hover:bg-yellow-700');
    } else if (confirmColor === 'indigo') {
        confirmButton.classList.add('bg-indigo-600', 'hover:bg-indigo-700');
    }

    // Asignar la acción para el manejador unificado de click
    confirmButton.setAttribute('data-action-type', targetAction);

    // Lógica para deshabilitar o cambiar texto si es "solo informativo"
    const isInfoOnly = (targetAction === 'info'); 
    confirmButton.disabled = isInfoOnly;

    modal.classList.remove('hidden');
    setTimeout(() => {
        modal.style.opacity = '1';
        modalContent.classList.remove('scale-95', 'opacity-0');
        modalContent.classList.add('scale-100', 'opacity-100');
    }, 10);

    modal.onclick = function(event) {
        if (event.target === modal) {
            window.hideModal();
        }
    };
}

window.hideModal = function() {
    modalContent.classList.remove('scale-100', 'opacity-100');
    modalContent.classList.add('scale-95', 'opacity-0');
    modal.style.opacity = '0';
    setTimeout(() => {
        modal.classList.add('hidden');
        currentFormToSubmit = null; // Limpiar la referencia al formulario
    }, 300);
}


// =================================================================
// 4. MANEJO DE ESTADO DE CARGA (FEEDBACK VISUAL)
// =================================================================

function setLoadingState(isLoading, fileName = '') {
    if (isLoading) {
        // Guardar el HTML original
        triggerUploadButton.dataset.originalHtml = triggerUploadButton.innerHTML;

        // Cambiar a estado de carga
        triggerUploadButton.disabled = true;
        triggerUploadButton.classList.add('opacity-75', 'cursor-wait');
        triggerUploadButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Procesando...';
        
        // Agregar log (Usamos la función unificada)
        logMessage(`Iniciando carga y procesamiento de ${fileName}...`, 'warning');


    } else {
        // Restaurar estado normal
        triggerUploadButton.classList.remove('opacity-75', 'cursor-wait');

        // Restaurar el texto original si existe
        if (triggerUploadButton.dataset.originalHtml) {
            triggerUploadButton.innerHTML = triggerUploadButton.dataset.originalHtml;
        }
        
        // Sincronizar estado del botón con el archivo actual
        updateUploadButtonState(fileInput.files.length > 0);
    }
}

function updateUploadButtonState(hasFile) {
    if (hasFile) {
        triggerUploadButton.disabled = false;
        triggerUploadButton.classList.remove('bg-yellow-600', 'hover:bg-yellow-700');
        triggerUploadButton.classList.add('bg-indigo-600', 'hover:bg-indigo-700');
        triggerUploadButton.innerHTML = '<i class="fas fa-upload mr-2"></i> Generar Nuevo Recibo';
    } else {
        triggerUploadButton.disabled = true;
        triggerUploadButton.classList.remove('bg-indigo-600', 'hover:bg-indigo-700');
        triggerUploadButton.classList.add('bg-yellow-600', 'hover:bg-yellow-700');
        triggerUploadButton.innerHTML = '<i class="fas fa-arrow-up mr-2"></i> Esperando Archivo'; //Texto original
    }
}


// =================================================================
// 5. MANEJADOR ÚNICO DE CLICK EN EL BOTÓN DE CONFIRMACIÓN DEL MODAL
// =================================================================

confirmButton.addEventListener('click', function() {
    const actionType = this.getAttribute('data-action-type');

    if (actionType === 'clear_visual_logs') {
        // Limpieza de logs visuales (no necesita submit de formulario)
        if (logDisplay) {
            logDisplay.innerHTML = `<p class="text-gray-400">Logs limpios. Listo para nuevos procesos.</p>`;
        }
        logMessage('Limpieza de logs visuales completada.', 'info');
        window.hideModal();
    } 
    else if (actionType === 'info') {
        // Botón 'Entendido' (solo es informativo)
        window.hideModal();
    }
    else if (currentFormToSubmit && !this.disabled) {
        // Acciones que requieren envío de formulario (Anular, Limpiar BD, Carga Excel)
        
        if (actionType === 'upload') {
            const fileName = fileInput.files.length > 0 ? fileInput.files[0].name : '';
            window.hideModal(); // Ocultar antes de submit para ver el spinner
            setLoadingState(true, fileName);
            
            // Retraso pequeño para asegurar que el DOM se actualice (spinner/log) antes de la navegación
            setTimeout(() => {
                currentFormToSubmit.submit();
            }, 50); 
        } else {
            // Anular o Limpiar Logs de BD
            currentFormToSubmit.submit();
            window.hideModal(); 
        }
    }
});


// =================================================================
// 6. EVENTOS (DOMContentLoaded)
// =================================================================

document.addEventListener('DOMContentLoaded', function() {

    // --- A. Inicialización y Limpieza de Estado ---
    setLoadingState(false); 
    updateUploadButtonState(fileInput.files.length > 0);

    const hasErrorMessages = document.querySelector('.bg-red-100');
    if (hasErrorMessages && fileInput) {
        fileInput.value = ''; 
        updateUploadButtonState(false);
        uploadStatus.textContent = 'Ningún archivo seleccionado.';
        uploadStatus.classList.remove('text-indigo-600', 'font-semibold');
        uploadStatus.classList.add('text-gray-500');
    }
    
    // --- B. Manejo de Carga de Archivos ---
    if (fileInput) {
        fileInput.addEventListener('change', function(e) {
            const hasFile = e.target.files.length > 0;
            if (hasFile) {
                uploadStatus.textContent = 'Archivo listo para cargar: ' + e.target.files[0].name;
                uploadStatus.classList.remove('text-gray-500');
                uploadStatus.classList.add('text-indigo-600', 'font-semibold');
            } else {
                uploadStatus.textContent = 'Ningún archivo seleccionado.';
                uploadStatus.classList.remove('text-indigo-600', 'font-semibold');
                uploadStatus.classList.add('text-gray-500');
            }
            updateUploadButtonState(hasFile);
        });
    }

    // --- C. Clic en Botón de Carga (triggerUploadButton) ---
    if (triggerUploadButton && uploadForm) {
        triggerUploadButton.addEventListener('click', function() {
            if (fileInput.files.length > 0) {
                currentFormToSubmit = uploadForm;
                
                window.showModal(
                    'Confirmación de Carga Masiva',
                    `¿Estás seguro que deseas **cargar los recibos del archivo Excel "${fileInput.files[0].name}"**? Esto creará nuevos registros.`,
                    'Sí, Cargar Excel',
                    'upload', 
                    'indigo'
                );
            } else {
                window.showModal(
                    'Acción Inválida',
                    'Por favor, selecciona un archivo Excel primero. (La creación/modificación individual se maneja en la tabla de resultados).',
                    'Entendido',
                    'info',
                    'yellow'
                );
            }
        });
    }

    // --- D. Clic en Botón Anular Recibo (Tabla) ---
    document.querySelectorAll('.anular-recibo-btn').forEach(button => {
        button.addEventListener('click', function() {
            const reciboId = this.getAttribute('data-recibo-id');
            document.getElementById('anular-recibo-id').value = reciboId;
            currentFormToSubmit = anularForm; 

            window.showModal(
                'Confirmar Anulación',
                this.getAttribute('data-message'),
                this.getAttribute('data-confirm-text'),
                'anular', 
                this.getAttribute('data-color')
            );
        });
    });

    // --- F. Clic en Botón Limpiar Logs (Visual) ---
    if (clearVisualLogsButton) {
        clearVisualLogsButton.addEventListener('click', function() {
            window.showModal(
                'Confirmar Limpieza de Logs',
                this.dataset.message,
                this.dataset.confirmText,
                'clear_visual_logs', 
                this.dataset.color
            );
        });
    }
    
    // --- G. Integración con Mensajes de Django ---
    const djangoMessages = document.querySelectorAll('.message-django'); 

    djangoMessages.forEach(messageDiv => {
        const text = messageDiv.textContent.trim();
        let type = messageDiv.getAttribute('data-type') || 'default';
        
        // Mapear los tipos de mensajes de Django a los tipos de log
        if (type === 'success') type = 'success';
        if (type === 'error') type = 'error';
        if (type === 'warning') type = 'warning';
        if (type === 'info') type = 'info';

        // Manda el mensaje de Django al panel de logs
        logMessage(`[Mensaje del Servidor] ${text}`, type);

        // Opcional: Eliminar los mensajes de Django de su ubicación original
        messageDiv.remove(); 
    });
    
    // Si no hay mensajes, muestra un log inicial de estado
    if (djangoMessages.length === 0) {
        logMessage('Sistema iniciado. Listo para recibir comandos.', 'default');
    }


    // --- H. Manejo ade Filtros Automáticos ---
    document.querySelectorAll('#estado, #fecha_inicio, #fecha_fin').forEach(element => {
        element.addEventListener('change', function() {
            document.getElementById('filter-form').submit();
        });
    });

    // --- I. Auto-descarte de Mensajes de Éxito ---
    const successMessages = document.querySelectorAll('.bg-green-100');
    successMessages.forEach(message => {
        setTimeout(() => {
            message.style.opacity = '0';
            message.style.transition = 'opacity 0.5s ease-out';
            setTimeout(() => {
                message.remove();
            }, 500);
        }, 5000); 
    });

});