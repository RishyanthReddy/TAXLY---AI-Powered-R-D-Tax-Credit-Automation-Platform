/**
 * PDF Viewer Module
 * Handles in-browser PDF viewing using PDF.js
 */

// PDF.js Configuration
const PDFJS_CDN = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174';
let pdfjsLib = null;
let currentPdfDoc = null;
let currentPage = 1;
let totalPages = 0;
let currentScale = 1.0;
let isRendering = false;

/**
 * Initialize PDF.js library
 */
async function initPdfJs() {
    if (pdfjsLib) return pdfjsLib;
    
    try {
        // Load PDF.js from CDN
        if (typeof window.pdfjsLib === 'undefined') {
            await loadScript(`${PDFJS_CDN}/pdf.min.js`);
        }
        
        pdfjsLib = window.pdfjsLib;
        
        // Configure worker
        pdfjsLib.GlobalWorkerOptions.workerSrc = `${PDFJS_CDN}/pdf.worker.min.js`;
        
        console.log('PDF.js initialized successfully');
        return pdfjsLib;
    } catch (error) {
        console.error('Failed to initialize PDF.js:', error);
        throw error;
    }
}

/**
 * Load external script dynamically
 */
function loadScript(src) {
    return new Promise((resolve, reject) => {
        const script = document.createElement('script');
        script.src = src;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
    });
}

/**
 * Load PDF from backend
 * @param {string} reportId - Report ID or filename
 * @returns {Promise<Object>} PDF document object
 */
async function loadPdf(reportId) {
    try {
        await initPdfJs();
        
        // Construct PDF URL
        const pdfUrl = `${API_BASE_URL}/api/download/report/${reportId}`;
        
        console.log(`Loading PDF from: ${pdfUrl}`);
        
        // Load PDF document
        const loadingTask = pdfjsLib.getDocument(pdfUrl);
        const pdf = await loadingTask.promise;
        
        console.log(`PDF loaded successfully. Pages: ${pdf.numPages}`);
        
        currentPdfDoc = pdf;
        totalPages = pdf.numPages;
        currentPage = 1;
        currentScale = 1.0;
        
        return pdf;
    } catch (error) {
        console.error('Failed to load PDF:', error);
        throw error;
    }
}

/**
 * Render PDF page to canvas
 * @param {number} pageNum - Page number to render
 * @param {HTMLCanvasElement} canvas - Canvas element to render to
 * @param {number} scale - Scale factor for rendering
 */
async function renderPage(pageNum, canvas, scale = 1.0) {
    if (!currentPdfDoc || isRendering) return;
    
    try {
        isRendering = true;
        
        // Get page
        const page = await currentPdfDoc.getPage(pageNum);
        
        // Calculate viewport
        const viewport = page.getViewport({ scale });
        
        // Set canvas dimensions
        const context = canvas.getContext('2d');
        canvas.height = viewport.height;
        canvas.width = viewport.width;
        
        // Render page
        const renderContext = {
            canvasContext: context,
            viewport: viewport
        };
        
        await page.render(renderContext).promise;
        
        console.log(`Rendered page ${pageNum} at scale ${scale}`);
    } catch (error) {
        console.error(`Failed to render page ${pageNum}:`, error);
        throw error;
    } finally {
        isRendering = false;
    }
}

/**
 * Generate thumbnail for first page
 * @param {string} reportId - Report ID or filename
 * @param {HTMLImageElement} imgElement - Image element to set thumbnail
 * @param {number} maxWidth - Maximum thumbnail width
 */
async function generateThumbnail(reportId, imgElement, maxWidth = 200) {
    try {
        await initPdfJs();
        
        // Load PDF
        const pdfUrl = `${API_BASE_URL}/api/download/report/${reportId}`;
        const loadingTask = pdfjsLib.getDocument(pdfUrl);
        const pdf = await loadingTask.promise;
        
        // Get first page
        const page = await pdf.getPage(1);
        
        // Calculate scale to fit maxWidth
        const viewport = page.getViewport({ scale: 1.0 });
        const scale = maxWidth / viewport.width;
        const scaledViewport = page.getViewport({ scale });
        
        // Create temporary canvas
        const canvas = document.createElement('canvas');
        canvas.width = scaledViewport.width;
        canvas.height = scaledViewport.height;
        
        // Render to canvas
        const context = canvas.getContext('2d');
        await page.render({
            canvasContext: context,
            viewport: scaledViewport
        }).promise;
        
        // Convert canvas to image
        imgElement.src = canvas.toDataURL('image/png');
        imgElement.alt = 'PDF Thumbnail';
        
        console.log(`Generated thumbnail for ${reportId}`);
    } catch (error) {
        console.error('Failed to generate thumbnail:', error);
        // Set placeholder image on error
        imgElement.src = 'assets/images/pdf-placeholder.png';
        imgElement.alt = 'PDF Preview Unavailable';
    }
}

/**
 * Open PDF viewer modal
 * @param {string} reportId - Report ID or filename
 * @param {Object} reportMetadata - Report metadata for display
 */
async function openPdfViewer(reportId, reportMetadata = {}) {
    try {
        // Show loading state
        showPdfViewerLoading();
        
        // Load PDF
        await loadPdf(reportId);
        
        // Update modal UI
        updatePdfViewerUI(reportMetadata);
        
        // Render first page
        const canvas = document.getElementById('pdfCanvas');
        if (canvas) {
            await renderPage(currentPage, canvas, currentScale);
        }
        
        // Show modal
        const modal = document.getElementById('pdfViewerModal');
        if (modal) {
            modal.classList.add('active');
        }
        
        // Update page info
        updatePageInfo();
    } catch (error) {
        console.error('Failed to open PDF viewer:', error);
        showNotification('error', `Failed to load PDF: ${error.message}`);
    }
}

/**
 * Close PDF viewer modal
 */
function closePdfViewer() {
    const modal = document.getElementById('pdfViewerModal');
    if (modal) {
        modal.classList.remove('active');
    }
    
    // Clean up
    currentPdfDoc = null;
    currentPage = 1;
    totalPages = 0;
    currentScale = 1.0;
}

/**
 * Navigate to specific page
 * @param {number} pageNum - Page number to navigate to
 */
async function goToPage(pageNum) {
    if (!currentPdfDoc || pageNum < 1 || pageNum > totalPages) return;
    
    currentPage = pageNum;
    
    const canvas = document.getElementById('pdfCanvas');
    if (canvas) {
        await renderPage(currentPage, canvas, currentScale);
    }
    
    updatePageInfo();
}

/**
 * Navigate to previous page
 */
async function previousPage() {
    if (currentPage > 1) {
        await goToPage(currentPage - 1);
    }
}

/**
 * Navigate to next page
 */
async function nextPage() {
    if (currentPage < totalPages) {
        await goToPage(currentPage + 1);
    }
}

/**
 * Zoom in
 */
async function zoomIn() {
    currentScale = Math.min(currentScale + 0.25, 3.0);
    
    const canvas = document.getElementById('pdfCanvas');
    if (canvas && currentPdfDoc) {
        await renderPage(currentPage, canvas, currentScale);
    }
    
    updateZoomInfo();
}

/**
 * Zoom out
 */
async function zoomOut() {
    currentScale = Math.max(currentScale - 0.25, 0.5);
    
    const canvas = document.getElementById('pdfCanvas');
    if (canvas && currentPdfDoc) {
        await renderPage(currentPage, canvas, currentScale);
    }
    
    updateZoomInfo();
}

/**
 * Reset zoom to 100%
 */
async function resetZoom() {
    currentScale = 1.0;
    
    const canvas = document.getElementById('pdfCanvas');
    if (canvas && currentPdfDoc) {
        await renderPage(currentPage, canvas, currentScale);
    }
    
    updateZoomInfo();
}

/**
 * Fit to width
 */
async function fitToWidth() {
    const canvas = document.getElementById('pdfCanvas');
    const container = document.getElementById('pdfCanvasContainer');
    
    if (!canvas || !container || !currentPdfDoc) return;
    
    // Get page to calculate dimensions
    const page = await currentPdfDoc.getPage(currentPage);
    const viewport = page.getViewport({ scale: 1.0 });
    
    // Calculate scale to fit container width
    const containerWidth = container.clientWidth - 40; // Account for padding
    currentScale = containerWidth / viewport.width;
    
    await renderPage(currentPage, canvas, currentScale);
    updateZoomInfo();
}

/**
 * Update page info display
 */
function updatePageInfo() {
    const pageInfo = document.getElementById('pdfPageInfo');
    if (pageInfo) {
        pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
    }
    
    // Update navigation buttons
    const prevBtn = document.getElementById('pdfPrevBtn');
    const nextBtn = document.getElementById('pdfNextBtn');
    
    if (prevBtn) {
        prevBtn.disabled = currentPage <= 1;
    }
    
    if (nextBtn) {
        nextBtn.disabled = currentPage >= totalPages;
    }
}

/**
 * Update zoom info display
 */
function updateZoomInfo() {
    const zoomInfo = document.getElementById('pdfZoomInfo');
    if (zoomInfo) {
        zoomInfo.textContent = `${Math.round(currentScale * 100)}%`;
    }
}

/**
 * Update PDF viewer UI with metadata
 */
function updatePdfViewerUI(metadata) {
    // Update title
    const title = document.getElementById('pdfViewerTitle');
    if (title) {
        title.textContent = metadata.filename || 'PDF Report';
    }
    
    // Update metadata display
    const metadataEl = document.getElementById('pdfMetadata');
    if (metadataEl) {
        metadataEl.innerHTML = `
            <div class="pdf-meta-item">
                <span class="pdf-meta-label">Pages:</span>
                <span class="pdf-meta-value">${totalPages}</span>
            </div>
            <div class="pdf-meta-item">
                <span class="pdf-meta-label">Size:</span>
                <span class="pdf-meta-value">${formatFileSize(metadata.fileSize || 0)}</span>
            </div>
            <div class="pdf-meta-item">
                <span class="pdf-meta-label">Generated:</span>
                <span class="pdf-meta-value">${formatDate(metadata.generationDate || new Date())}</span>
            </div>
        `;
    }
}

/**
 * Show loading state in PDF viewer
 */
function showPdfViewerLoading() {
    const canvas = document.getElementById('pdfCanvas');
    const container = document.getElementById('pdfCanvasContainer');
    
    if (container) {
        container.innerHTML = `
            <div class="pdf-loading">
                <div class="spinner"></div>
                <p>Loading PDF...</p>
            </div>
        `;
    }
}

/**
 * Download current PDF
 */
async function downloadCurrentPdf() {
    if (!currentPdfDoc) return;
    
    try {
        // Get report ID from modal
        const title = document.getElementById('pdfViewerTitle');
        const reportId = title ? title.dataset.reportId : null;
        
        if (reportId) {
            await api.downloadReport(reportId);
            showNotification('success', 'PDF downloaded successfully!');
        }
    } catch (error) {
        console.error('Failed to download PDF:', error);
        showNotification('error', `Failed to download PDF: ${error.message}`);
    }
}

/**
 * Setup PDF viewer event listeners
 */
function setupPdfViewerListeners() {
    // Navigation buttons
    const prevBtn = document.getElementById('pdfPrevBtn');
    const nextBtn = document.getElementById('pdfNextBtn');
    
    if (prevBtn) {
        prevBtn.addEventListener('click', previousPage);
    }
    
    if (nextBtn) {
        nextBtn.addEventListener('click', nextPage);
    }
    
    // Zoom buttons
    const zoomInBtn = document.getElementById('pdfZoomInBtn');
    const zoomOutBtn = document.getElementById('pdfZoomOutBtn');
    const resetZoomBtn = document.getElementById('pdfResetZoomBtn');
    const fitWidthBtn = document.getElementById('pdfFitWidthBtn');
    
    if (zoomInBtn) {
        zoomInBtn.addEventListener('click', zoomIn);
    }
    
    if (zoomOutBtn) {
        zoomOutBtn.addEventListener('click', zoomOut);
    }
    
    if (resetZoomBtn) {
        resetZoomBtn.addEventListener('click', resetZoom);
    }
    
    if (fitWidthBtn) {
        fitWidthBtn.addEventListener('click', fitToWidth);
    }
    
    // Download button
    const downloadBtn = document.getElementById('pdfDownloadBtn');
    if (downloadBtn) {
        downloadBtn.addEventListener('click', downloadCurrentPdf);
    }
    
    // Close button
    const closeBtn = document.getElementById('pdfViewerCloseBtn');
    if (closeBtn) {
        closeBtn.addEventListener('click', closePdfViewer);
    }
    
    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        const modal = document.getElementById('pdfViewerModal');
        if (!modal || !modal.classList.contains('active')) return;
        
        switch(e.key) {
            case 'ArrowLeft':
                previousPage();
                break;
            case 'ArrowRight':
                nextPage();
                break;
            case '+':
            case '=':
                zoomIn();
                break;
            case '-':
                zoomOut();
                break;
            case '0':
                resetZoom();
                break;
            case 'Escape':
                closePdfViewer();
                break;
        }
    });
}

// Initialize PDF viewer when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', setupPdfViewerListeners);
} else {
    setupPdfViewerListeners();
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        initPdfJs,
        loadPdf,
        renderPage,
        generateThumbnail,
        openPdfViewer,
        closePdfViewer,
        goToPage,
        previousPage,
        nextPage,
        zoomIn,
        zoomOut,
        resetZoom,
        fitToWidth
    };
}
