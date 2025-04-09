const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const processingContainer = document.querySelector('.processing-container');

// Drag and drop handlers
dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = '#1F6AA5';
});

dropZone.addEventListener('dragleave', () => {
    dropZone.style.borderColor = '#3B8ED0';
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.style.borderColor = '#3B8ED0';
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
});

fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) handleFile(file);
});

async function handleFile(file) {
    document.querySelector('.processing-container').classList.remove('hidden');
    document.getElementById('fileInfo').textContent = `Processing: ${file.name}`;
    document.querySelector('.spinner').style.display = 'block';

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await axios.post('/api/process', formData, {
            headers: {'Content-Type': 'multipart/form-data'}
        });

        if (response.data.status === 'success') {
            // Pass both the data and response to showResults
            showResults(response.data.data, file, response.data); 
        } else {
            showError(response.data.message);
        }
    } catch (error) {
        showError(error.response?.data?.error || 'Processing failed! Try again with Clear image.');
    } finally {
        document.querySelector('.spinner').style.display = 'none';
    }
}

function showResults(data, file) {
    const resultsDiv = document.getElementById('results');
    const reader = new FileReader();
    
    reader.onload = (e) => {
        // Change the header to "PAN Details" and remove paths
        document.getElementById('fileInfo').textContent = "PAN Details:";
        
        resultsDiv.innerHTML = `
            <div class="image-preview">
                <img src="${e.target.result}" alt="Uploaded PAN Card">
            </div>
            <div class="results">
                <div class="result-item">
                    <label>Card Holder Name:</label>
                    <input value="${data.name || 'Not Detected'}" readonly>
                </div>
                <div class="result-item">
                    <label>Father's Name:</label>
                    <input value="${data.father_name || 'Not Detected'}" readonly>
                </div>
                <div class="result-item">
                    <label>PAN Number:</label>
                    <input value="${data.pan_number || 'Not Detected'}" readonly>
                </div>
                <div class="result-item">
                    <label>Date of Birth:</label>
                    <input value="${data.dob || 'Not Detected'}" readonly>
                </div>
                <button class="try-again" onclick="location.reload()">Try Another One</button>
            </div>
        `;
    };
    
    reader.onerror = (error) => {
        console.error('File reading error:', error);
        showError('Failed to preview image');
    };
    
    reader.readAsDataURL(file);
}

function showError(message) {
    const resultsDiv = document.getElementById('results');
    resultsDiv.innerHTML = `
        <div class="error-message">
            ${message}
        </div>
        <button class="try-again" onclick="location.reload()">Try Again</button>
    `;
}