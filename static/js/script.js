// Digital Rain Effect
function createDigitalRain() {
    const canvas = document.getElementById('digital-rain');
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    canvas.height = window.innerHeight;
    canvas.width = window.innerWidth;

    const chars = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ@#$%';
    const fontSize = 14;
    const columns = canvas.width / fontSize;
    const drops = [];

    for (let x = 0; x < columns; x++) {
        drops[x] = 1;
    }

    function draw() {
        ctx.fillStyle = 'rgba(10, 10, 10, 0.05)';
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        ctx.fillStyle = '#00ff00';
        ctx.font = fontSize + 'px Fira Code';

        for (let i = 0; i < drops.length; i++) {
            const text = chars.charAt(Math.floor(Math.random() * chars.length));
            ctx.fillText(text, i * fontSize, drops[i] * fontSize);

            if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
                drops[i] = 0;
            }

            drops[i]++;
        }
    }

    setInterval(draw, 33);
}

// Webcam and Scanning Animation
function initWebcam() {
    const warmupTime = 2000; // 2 seconds warmup time
    const video = document.getElementById('webcam');
    const overlay = document.getElementById('overlay');
    const status = document.getElementById('status');
    const confidence = document.getElementById('confidence');

    // Robust null checks
    if (!video || !overlay || !status || !confidence) {
        console.warn('Missing required elements for webcam');
        return;
    }

    const ctx = overlay.getContext('2d');
    if (!ctx) {
        console.error('Failed to get 2D context for overlay');
        status.textContent = '> Error: Canvas not supported';
        return;
    }

    overlay.width = 640;
    overlay.height = 480;

    // Flag to stop animation on page unload
    let isActive = true;

    // Request webcam access
    navigator.mediaDevices.getUserMedia({ video: true })
        .then(stream => {
            video.srcObject = stream;
            status.textContent = '> Searching for Match...';
            setTimeout(() => {
                if (isActive) {
                    animateScan();
                }
            }, warmupTime);
        })
        .catch(err => {
            status.textContent = '> Error: Camera access denied';
            console.error('Webcam error:', err);
        });

    // Simulated face detection animation
    function animateScan() {
        if (!isActive) return;

        ctx.clearRect(0, 0, overlay.width, overlay.height);

        // Simulate face rectangle (faster movement)
        if (Math.random() > 0.2) { // More frequent rectangles
            const x = overlay.width * 0.2 + Math.random() * overlay.width * 0.6;
            const y = overlay.height * 0.2 + Math.random() * overlay.height * 0.6;
            const w = 80 + Math.random() * 70; // Smaller, varied size
            const h = 80 + Math.random() * 70;

            ctx.strokeStyle = '#00ff00';
            ctx.lineWidth = 2;
            ctx.strokeRect(x, y, w, h);

            // Simulate confidence update
            const conf = Math.min(100, ((Date.now() % 30000) / 30000) * 100);
            confidence.textContent = `> Confidence: ${conf.toFixed(1)}%`;
        }

        requestAnimationFrame(animateScan);
    }

    // Stop animation on page unload
    window.addEventListener('beforeunload', () => {
        isActive = false;
        if (video.srcObject) {
            video.srcObject.getTracks().forEach(track => track.stop());
        }
    });
}

// Dynamic Stats for Index Dashboard
function updateDashboardStats() {
    const scanCount = document.getElementById('scan-count');
    const uptime = document.getElementById('uptime');
    if (!scanCount || !uptime) return;

    let scans = 0;
    let startTime = Date.now();

    function update() {
        scans += Math.random() > 0.9 ? 1 : 0; // Simulate scan increments
        scanCount.textContent = `> Scans: ${scans}`;
        const elapsed = Math.floor((Date.now() - startTime) / 1000);
        uptime.textContent = `> Uptime: ${elapsed}s`;
    }

    update();
    setInterval(update, 2000);
}

// Initialize effects
if (document.getElementById('digital-rain')) {
    window.addEventListener('load', () => {
        createDigitalRain();
        if (document.getElementById('webcam')) {
            initWebcam();
        }
        if (document.getElementById('scan-count')) {
            updateDashboardStats();
        }
    });
    window.addEventListener('resize', () => {
        const canvas = document.getElementById('digital-rain');
        if (canvas) {
            canvas.height = window.innerHeight;
            canvas.width = window.innerWidth;
        }
    });
}