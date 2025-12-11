let currentFormToSubmit = null;
const modal = document.getElementById('confirmation-modal');
const modalContent = document.getElementById('modal-content');
const modalTitle = document.getElementById('modal-title');
const modalMessage = document.getElementById('modal-message');
const confirmButton = document.getElementById('confirm-action-button');
const createReciboButton = document.getElementById('create-recibo-button');
const uploadForm = document.getElementById('upload-form'); 

function getCsrfToken() {
  const tokenElement = document.querySelector('input[name="csrfmiddlewaretoken"]');
  return tokenElement ? tokenElement.value : '';
}

function showModal(title, messageHtml, confirmText, confirmColor) {
  modalTitle.textContent = title;

  const formattedMessage = messageHtml.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  modalMessage.innerHTML = formattedMessage; 
  confirmButton.textContent = confirmText;
  
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

  // Deshabilita el botón si es Anulado o si es el modal de función pendiente (color 'yellow' y texto 'Entendido')
  confirmButton.disabled = (confirmColor === 'gray' && confirmText !== 'Sí, Limpiar Logs') || (confirmColor === 'yellow' && confirmText === 'Entendido');

  modal.classList.remove('hidden');
  setTimeout(() => {
    modal.style.opacity = '1';
    modalContent.classList.remove('scale-95', 'opacity-0');
    modalContent.classList.add('scale-100', 'opacity-100');
  }, 10); 

  modal.onclick = function(event) {
    if (event.target === modal) {
      hideModal();
    }
  };
}

function hideModal() {
  modalContent.classList.remove('scale-100', 'opacity-100');
  modalContent.classList.add('scale-95', 'opacity-0');
  modal.style.opacity = '0';
  setTimeout(() => {
    modal.classList.add('hidden');

    if (currentFormToSubmit && currentFormToSubmit.id.startsWith('temp-anular-form-')) {
      currentFormToSubmit.remove(); 
    }
    currentFormToSubmit = null; 
  }, 300);
}

// Función para controlar el estado de carga (Feedback Visual)
function setLoadingState(isLoading) {
    if (isLoading) {
        // Guardar el texto original antes de cambiarlo
        createReciboButton.dataset.originalHtml = createReciboButton.innerHTML;
        
        // Cambiar a estado de carga
        createReciboButton.disabled = true;
        createReciboButton.classList.add('opacity-75', 'cursor-wait');
        createReciboButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Procesando...';
    } else {
        // Restaurar estado normal
        createReciboButton.disabled = false;
        createReciboButton.classList.remove('opacity-75', 'cursor-wait');
        
        // Restaurar el texto original si existe
        if (createReciboButton.dataset.originalHtml) {
           createReciboButton.innerHTML = createReciboButton.dataset.originalHtml;
        } 
        // Si no hay original, el DOMContentLoaded actualizará el texto al estado de archivo/sin archivo.
    }
}

// CORRECCIÓN PRINCIPAL: Lógica para enviar el formulario de subida (Excel)
confirmButton.addEventListener('click', function() {
    if (currentFormToSubmit && !this.disabled) {
        console.log(`[ACCIÓN CONFIRMADA] Enviando formulario: ${currentFormToSubmit.id || 'temporal'}`);
        
        if (currentFormToSubmit.id === 'upload-form') {
            // Pasos esenciales para la carga de Excel:
            hideModal(); // 1. Ocultar el modal inmediatamente.
            setLoadingState(true); // 2. Activar el spinner.
            currentFormToSubmit.submit(); // 3. Enviar el formulario.
        } else {
            // Esto maneja la anulación y limpieza de logs (no necesita spinner ni ocultar antes de submit)
            currentFormToSubmit.submit();
        }
    }
});


document.addEventListener('DOMContentLoaded', function() {
  const fileInput = document.getElementById('excel-file-input');
  const statusElement = document.getElementById('upload-status');
  const csrfToken = getCsrfToken(); 
        
  let fileSelected = false;

  // 💡 CORRECCIÓN UX: Restablecer el botón de carga a su estado normal al cargar la página.
  // Esto revierte el estado de "Procesando" si la página se recarga después de un POST.
  setLoadingState(false); 

  if (fileInput) {
    fileInput.addEventListener('change', function(e) {
      fileSelected = e.target.files.length > 0;
      if (fileSelected) {
        statusElement.textContent = 'Archivo listo para cargar: ' + e.target.files[0].name;
        statusElement.classList.remove('text-gray-500');
        statusElement.classList.add('text-indigo-600', 'font-semibold');
      } else {
        statusElement.textContent = 'Ningún archivo seleccionado.';
        statusElement.classList.remove('text-indigo-600', 'font-semibold');
        statusElement.classList.add('text-gray-500');
      }

      updateCreateButtonText(fileSelected);
    });

    // Limpiar el formulario y el estado si hay un error
    const hasErrorMessages = document.querySelector('.bg-red-100');
    if (hasErrorMessages) {
         fileInput.value = ''; 
         fileSelected = false;
         updateCreateButtonText(false);
         statusElement.textContent = 'Ningún archivo seleccionado.';
         statusElement.classList.remove('text-indigo-600', 'font-semibold');
         statusElement.classList.add('text-gray-500');
    }

    updateCreateButtonText(fileInput.files.length > 0);
  }
        
  function updateCreateButtonText(hasFile) {
    if (hasFile) {
      createReciboButton.classList.remove('bg-yellow-600', 'hover:bg-yellow-700');
      createReciboButton.classList.add('bg-indigo-600', 'hover:bg-indigo-700');
      createReciboButton.innerHTML = '<i class="fas fa-upload mr-2"></i> **CARGAR** Datos Excel';
    } else {
      createReciboButton.classList.remove('bg-indigo-600', 'hover:bg-indigo-700');
      createReciboButton.classList.add('bg-yellow-600', 'hover:bg-yellow-700');
      createReciboButton.innerHTML = '<i class="fas fa-plus-circle mr-2"></i> Crear Nuevo Recibo';
    }
  }
        
  if (createReciboButton) {
    createReciboButton.addEventListener('click', function() {
      if (fileSelected) {
        currentFormToSubmit = uploadForm;
        showModal(
          'Confirmación de Carga Masiva',
          '¿Estás seguro que deseas **cargar los recibos del archivo Excel** seleccionado? Esto creará nuevos registros de forma masiva. Se recomienda solo hacer esto **una vez** por archivo.',
          'Sí, Cargar Excel',
          'indigo'
        );
      } else {
        // Manejo de la acción "Crear Nuevo Recibo" (pendiente de implementar)
        currentFormToSubmit = null; 
        showModal(
          'Función Pendiente',
          'La **creación de recibos individuales** aún no está implementada. Por favor, utiliza la carga de archivos Excel.',
          'Entendido',
          'yellow'
        );
      }
    });
  }

  document.querySelectorAll('.anular-recibo-button').forEach(button => {
    button.addEventListener('click', function() {
      if (this.disabled) return; 
      const actionUrl = this.dataset.actionUrl;
      const message = this.dataset.message;
      const confirmText = this.dataset.confirmText;
      const color = this.dataset.color;
      
      const tempForm = document.createElement('form');
      tempForm.method = 'POST';
      tempForm.action = actionUrl;
      tempForm.id = 'temp-anular-form-' + Math.random().toString(36).substring(2, 9); 
      
      if (csrfToken) {
        const csrfInput = document.createElement('input');
        csrfInput.type = 'hidden';
        csrfInput.name = 'csrfmiddlewaretoken';
        csrfInput.value = csrfToken;
        tempForm.appendChild(csrfInput);
      } else {
        console.error("CSRF Token no encontrado. La solicitud POST fallará.");
      }
      
      const actionInput = document.createElement('input');
      actionInput.type = 'hidden';
      actionInput.name = 'action';
      actionInput.value = 'anular'; 
      tempForm.appendChild(actionInput);

      document.body.appendChild(tempForm);
      
      currentFormToSubmit = tempForm;
      
      showModal('Confirmación de Anulación', message, confirmText, color);
    });
  });
        
  const clearLogsButton = document.getElementById('clear-logs-button-modal'); 
  if (clearLogsButton) {
    clearLogsButton.addEventListener('click', function() {
      const message = this.dataset.message;
      const confirmText = this.dataset.confirmText;
      const color = this.dataset.color;
      
      const clearLogsForm = document.getElementById('clear-logs-form');
      if (clearLogsForm) {
        currentFormToSubmit = clearLogsForm;
        showModal('Confirmación de Limpieza', message, confirmText, color);
      }
    });
  }
  
  // 💡 OPCIONAL: Auto-descarte de mensajes de éxito
  const successMessages = document.querySelectorAll('.bg-green-100');
  successMessages.forEach(message => {
      // Desvanecer después de 5 segundos
      setTimeout(() => {
          message.style.opacity = '0';
          message.style.transition = 'opacity 0.5s ease-out';
          
          // Eliminar del DOM después del desvanecimiento
          setTimeout(() => {
              message.remove();
          }, 500);
      }, 5000); 
  });
});

document.addEventListener('DOMContentLoaded', function() {
        const triggerButton = document.getElementById('trigger-upload-button');
        const uploadForm = document.getElementById('upload-form');
        const fileInput = document.getElementById('excel-file-input');

        if (triggerButton && uploadForm) {
            triggerButton.addEventListener('click', function() {
                // 1. Verificar si un archivo fue seleccionado
                if (fileInput.files.length > 0) {
                    // 2. Si hay un archivo, enviar el formulario
                    uploadForm.submit();
                    // Opcional: Deshabilitar el botón para evitar doble clic
                    triggerButton.disabled = true; 
                    triggerButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i> Procesando...';
                } else {
                    // 3. Si no hay archivo, mostrar una alerta simple
                    alert("Por favor, selecciona un archivo Excel primero.");
                    fileInput.focus();
                }
            });
        }
    });