(function () {
    const form = document.getElementById('expediente-form');
    if (!form) return;

    const estado = form.querySelector('[name="estado"]');
    const municipio = form.querySelector('[name="municipio"]');
    const parroquia = form.querySelector('[name="parroquia"]');
    const comuna = form.querySelector('[name="comuna"]');
    const surface = form.querySelector('[name="superficie_m2"]');
    const hectares = document.getElementById('superficie-hectareas');
    const filesInput = form.querySelector('[name="archivos"]');
    const fileNames = document.getElementById('file-names');

    function clearOptions(select, label) {
        select.replaceChildren(new Option(label, ''));
    }

    async function loadOptions(select, url, label) {
        clearOptions(select, label);
        select.disabled = true;
        try {
            const response = await fetch(url, {
                credentials: 'same-origin',
                headers: { Accept: 'application/json' }
            });
            if (!response.ok) throw new Error(`Solicitud fallida (${response.status})`);
            const rows = await response.json();
            rows.forEach((row) => select.add(new Option(row.nombre, row.id)));
        } catch (error) {
            console.error('No se pudieron cargar las opciones territoriales.', error);
            window.alert('No fue posible cargar los datos territoriales. Verifica tu conexión e inténtalo nuevamente.');
        } finally {
            select.disabled = false;
        }
    }

    estado.addEventListener('change', () => {
        clearOptions(municipio, 'Selecciona un municipio');
        clearOptions(parroquia, 'Selecciona una parroquia');
        clearOptions(comuna, 'Sin comuna');
        if (estado.value) {
            loadOptions(
                municipio,
                form.dataset.municipiosUrl.replace('/0/', `/${estado.value}/`),
                'Selecciona un municipio'
            );
        }
    });

    municipio.addEventListener('change', () => {
        clearOptions(parroquia, 'Selecciona una parroquia');
        clearOptions(comuna, 'Sin comuna');
        if (municipio.value) {
            loadOptions(
                parroquia,
                form.dataset.parroquiasUrl.replace('/0/', `/${municipio.value}/`),
                'Selecciona una parroquia'
            );
        }
    });

    parroquia.addEventListener('change', () => {
        clearOptions(comuna, 'Sin comuna');
        if (parroquia.value) {
            loadOptions(
                comuna,
                form.dataset.comunasUrl.replace('/0/', `/${parroquia.value}/`),
                'Sin comuna'
            );
        }
    });

    if (surface && hectares) {
        const updateHectares = () => {
            const value = Number(surface.value);
            hectares.value = Number.isFinite(value) && value > 0
                ? (value / 10000).toFixed(4)
                : '';
        };
        surface.addEventListener('input', updateHectares);
        updateHectares();
    }

    if (filesInput && fileNames) {
        filesInput.addEventListener('change', () => {
            fileNames.textContent = Array.from(filesInput.files)
                .map((file) => file.name)
                .join(', ');
        });
    }
})();
