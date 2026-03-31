document.addEventListener('DOMContentLoaded', () => {

    function setupDropzone(dropzoneId, inputId, listId, isMultiple = false) {
        const dropzone = document.getElementById(dropzoneId);
        const input = document.getElementById(inputId);
        const list = document.getElementById(listId);

        if (!dropzone) return;

        dropzone.addEventListener('click', () => input.click());

        dropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            dropzone.classList.add('dragover');
        });

        dropzone.addEventListener('dragleave', () => {
            dropzone.classList.remove('dragover');
        });

        dropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            dropzone.classList.remove('dragover');
            
            if (e.dataTransfer.files.length) {
                // Update input files
                input.files = e.dataTransfer.files;
                updateList(input.files, list);
            }
        });

        input.addEventListener('change', () => {
            if (input.files.length) {
                updateList(input.files, list);
            }
        });
    }

    function updateList(files, listElement) {
        listElement.innerHTML = '';
        Array.from(files).forEach(file => {
            const el = document.createElement('div');
            el.textContent = `• ${file.name}`;
            listElement.appendChild(el);
        });
    }

    setupDropzone('imageDropzone', 'imageInput', 'imageList', true);
    setupDropzone('audioDropzone', 'audioInput', 'audioList', false);

    // Form Submission
    const uploadForm = document.getElementById('uploadForm');
    const generateBtn = document.getElementById('generateBtn');
    const uploadStatus = document.getElementById('uploadStatus');

    if (uploadForm) {
        uploadForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const imageInput = document.getElementById('imageInput');
            const audioInput = document.getElementById('audioInput');

            if (!imageInput.files.length || !audioInput.files.length) {
                uploadStatus.style.display = 'block';
                uploadStatus.style.color = '#721C24';
                uploadStatus.textContent = "Please provide both images and an audio track.";
                return;
            }

            const formData = new FormData();
            Array.from(imageInput.files).forEach(file => {
                formData.append('images', file);
            });
            formData.append('enable_captions', document.getElementById('enable_captions').checked);
            formData.append('audio', audioInput.files[0]);
            formData.append('template', document.getElementById('template').value);
            
            //  THE NEW LINE: Grabbing the language dropdown value <---
            formData.append('language', document.getElementById('language').value);

            generateBtn.disabled = true;
            generateBtn.textContent = 'Uploading Assets...';
            uploadStatus.style.display = 'none';

            try {
                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();

                if (response.ok) {
                    // Success! Refresh the page to show new processing job in history.
                    window.location.reload();
                } else {
                    throw new Error(result.error || "Upload failed");
                }
            } catch (error) {
                uploadStatus.style.display = 'block';
                uploadStatus.style.color = '#721C24';
                uploadStatus.textContent = error.message;
                generateBtn.disabled = false;
                generateBtn.textContent = 'Generate Video';
            }
        });
    }
});