document.addEventListener('DOMContentLoaded', function() {
    // Check for login transition
    if (document.cookie.split(';').some(item => item.trim().startsWith('justLoggedIn='))) {
        document.cookie = 'justLoggedIn=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
        showTransitionAnimation();
    }
    
    // File input handling
    const fileInput = document.getElementById('faceFile');
    const fileName = document.getElementById('fileName');
    
    if (fileInput && fileName) {
        fileInput.addEventListener('change', function(e) {
            if (e.target.files.length > 0) {
                fileName.textContent = e.target.files[0].name;
                fileName.style.color = '#00ff9d';
            }
        });
    }
    
    // Form submission handling
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const fileInput = this.querySelector('input[type="file"]');
            if (fileInput && fileInput.files.length === 0) {
                e.preventDefault();
                const fileNameDisplay = this.querySelector('.file-name');
                if (fileNameDisplay) {
                    fileNameDisplay.textContent = 'PLEASE SELECT A FILE FIRST';
                    fileNameDisplay.style.color = '#ff00aa';
                }
            }
        });
    });
    
    // Create binary background effect
    createBinaryBackground();
});

function showTransitionAnimation() {
    const overlay = document.createElement('div');
    overlay.className = 'transition-overlay';
    
    overlay.innerHTML = `
        <div class="transition-content">
            <h1>WELCOME TO FACESCAN360</h1>
            <p>Initializing facial recognition system...</p>
            <div class="loading-bar"></div>
        </div>
    `;
    
    document.body.appendChild(overlay);
    
    setTimeout(() => {
        overlay.style.opacity = '0';
        setTimeout(() => {
            overlay.remove();
        }, 1000);
    }, 2500);
}

function createBinaryBackground() {
    const binaryContainer = document.createElement('div');
    binaryContainer.className = 'binary';
    
    for (let i = 0; i < 50; i++) {
        const binaryLine = document.createElement('div');
        binaryLine.textContent = generateBinaryString(50);
        binaryLine.style.position = 'absolute';
        binaryLine.style.left = `${Math.random() * 100}%`;
        binaryLine.style.top = `${Math.random() * 100}%`;
        binaryLine.style.color = '#00ff9d';
        binaryLine.style.fontSize = '0.8rem';
        binaryLine.style.opacity = '0.3';
        binaryLine.style.animation = `float ${5 + Math.random() * 10}s linear infinite`;
        
        binaryContainer.appendChild(binaryLine);
    }
    
    document.body.appendChild(binaryContainer);
}

function generateBinaryString(length) {
    let result = '';
    for (let i = 0; i < length; i++) {
        result += Math.random() > 0.5 ? '1' : '0';
    }
    return result;
}