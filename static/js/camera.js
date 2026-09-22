/**
 * eSavadh - Camera Scanning & Multi-Side Capture Controller
 * Made by Team Avyukt
 */

class CameraScannerController {
    constructor() {
        this.videoEl = document.getElementById("camera-video");
        this.canvasEl = document.getElementById("capture-canvas");
        this.stream = null;
        this.currentSide = "Front";
        this.capturedViews = {};
    }

    async initCamera() {
        if (!this.videoEl) return;

        try {
            this.stream = await navigator.mediaDevices.getUserMedia({
                video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } }
            });
            this.videoEl.srcObject = this.stream;
            this.videoEl.play();
            console.log("[Camera] Camera feed initialized successfully.");
        } catch (err) {
            console.warn("[Camera] Camera hardware not available or permission denied. Using file upload fallback.", err);
            const placeholder = document.getElementById("camera-placeholder-notice");
            if (placeholder) placeholder.style.display = "block";
        }
    }

    stopCamera() {
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
            this.stream = null;
        }
    }

    selectSide(sideName) {
        this.currentSide = sideName;
        document.querySelectorAll(".side-chip").forEach(chip => {
            chip.classList.toggle("active", chip.dataset.side === sideName);
        });

        const label = document.getElementById("active-side-label");
        if (label) label.innerText = `${sideName} Principal View`;
        
        const sideInput = document.getElementById("selected-side-input");
        if (sideInput) sideInput.value = sideName;
    }

    captureCurrentFrame() {
        if (!this.videoEl || !this.canvasEl) return null;

        const ctx = this.canvasEl.getContext("2d");
        this.canvasEl.width = this.videoEl.videoWidth || 640;
        this.canvasEl.height = this.videoEl.videoHeight || 480;
        ctx.drawImage(this.videoEl, 0, 0, this.canvasEl.width, this.canvasEl.height);

        const dataUrl = this.canvasEl.toDataURL("image/jpeg", 0.9);
        this.capturedViews[this.currentSide] = dataUrl;

        // Mark chip as captured
        const chip = document.querySelector(`.side-chip[data-side="${this.currentSide}"]`);
        if (chip) chip.classList.add("captured");

        return dataUrl;
    }
}

window.cameraScanner = new CameraScannerController();
