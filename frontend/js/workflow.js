/**
 * Workflow Page JavaScript
 * Handles workflow visualization with real-time WebSocket updates
 * 
 * Requirements: 5.2, 5.3
 */

// Stage mapping from backend to frontend
const STAGE_MAPPING = {
    'data_ingestion': { id: 1, name: 'Data Ingestion', estimatedDuration: 4 },
    'qualification': { id: 3, name: 'Project Qualification', estimatedDuration: 12 },
    'audit_trail': { id: 6, name: 'PDF Generation', estimatedDuration: 9 }
};

// All stages for display (including intermediate stages)
const stages = [
    { id: 1, name: 'Data Ingestion', backendStage: 'data_ingestion' },
    { id: 2, name: 'Data Validation', backendStage: null }, // Intermediate stage
    { id: 3, name: 'Project Qualification', backendStage: 'qualification' },
    { id: 4, name: 'Narrative Generation', backendStage: null }, // Part of audit_trail
    { id: 5, name: 'Compliance Review', backendStage: null }, // Part of audit_trail
    { id: 6, name: 'PDF Generation', backendStage: 'audit_trail' }
];

let isRunning = false;
let isPaused = false;
let currentStageIndex = 0;
let startTime = null;
let elapsedSeconds = 0;
let timerInterval = null;
let playbackSpeed = 2;

// WebSocket manager instance
let wsManager = null;
let useRealBackend = false; // Toggle between simulation and real backend

// Initialize workflow
function initWorkflow() {
    setupEventListeners();
    resetWorkflow();
    initWebSocket();
}

// Initialize WebSocket connection
function initWebSocket() {
    // Create WebSocket manager
    wsManager = new WebSocketManager('ws://localhost:8000/ws');
    
    // Set up event handlers
    wsManager.onStatusUpdate = handleStatusUpdate;
    wsManager.onError = handleError;
    wsManager.onProgress = handleProgress;
    wsManager.onConnectionChange = handleConnectionChange;
    
    // Connect to backend
    wsManager.connect();
    
    addLogEntry('info', 'Connecting to backend WebSocket...');
}

// Handle WebSocket connection status change
function handleConnectionChange(isConnected) {
    const statusIndicator = document.getElementById('backendStatus');
    
    if (isConnected) {
        if (statusIndicator) {
            statusIndicator.textContent = 'Connected';
            statusIndicator.className = 'status-badge status-healthy';
        }
        addLogEntry('success', 'Connected to backend successfully');
        useRealBackend = true;
    } else {
        if (statusIndicator) {
            statusIndicator.textContent = 'Disconnected';
            statusIndicator.className = 'status-badge status-error';
        }
        addLogEntry('error', 'Disconnected from backend - using simulation mode');
        useRealBackend = false;
    }
}

// Handle status update from backend
function handleStatusUpdate(update) {
    console.log('Status update received:', update);
    
    const { stage, status, details, timestamp } = update;
    
    // Map backend stage to frontend stage
    const stageInfo = STAGE_MAPPING[stage];
    if (!stageInfo) {
        console.warn('Unknown backend stage:', stage);
        return;
    }
    
    // Update the corresponding stage element
    updateStageStatus(stageInfo.id, status, details);
    
    // Log the update
    const logType = status === 'error' ? 'error' : 
                   status === 'completed' ? 'success' : 'info';
    addLogEntry(logType, `${stageInfo.name}: ${details}`);
    
    // Update overall progress
    updateOverallProgress();
}

// Handle error from backend
function handleError(error) {
    console.error('Error received:', error);
    
    const { error_type, message, timestamp } = error;
    
    addLogEntry('error', `Error (${error_type}): ${message}`);
    
    // Show error notification
    if (typeof showNotification === 'function') {
        showNotification(`Error: ${message}`, 'error');
    }
}

// Handle progress update from backend
function handleProgress(progress) {
    console.log('Progress update received:', progress);
    
    const { current_step, total_steps, percentage, description } = progress;
    
    if (description) {
        addLogEntry('info', description);
    }
    
    // Update progress bar if available
    const progressBar = document.getElementById('currentStageProgress');
    if (progressBar) {
        progressBar.style.width = `${percentage}%`;
    }
}

// Update stage status based on backend update
function updateStageStatus(stageId, status, details) {
    const stageElement = document.querySelector(`.pipeline-stage[data-stage="${stageId}"]`);
    if (!stageElement) {
        console.warn('Stage element not found:', stageId);
        return;
    }
    
    const statusBadge = stageElement.querySelector('.status-badge');
    const progressBar = stageElement.querySelector('.progress-bar-inner');
    
    // Map backend status to frontend status
    let displayStatus = status;
    let badgeClass = 'status-badge';
    let progressWidth = '0%';
    
    switch (status) {
        case 'pending':
            displayStatus = 'Pending';
            badgeClass += ' status-pending';
            progressWidth = '0%';
            break;
        case 'in_progress':
            displayStatus = 'In Progress';
            badgeClass += ' status-info';
            progressWidth = '50%'; // Show partial progress
            break;
        case 'completed':
            displayStatus = 'Completed';
            badgeClass += ' status-healthy';
            progressWidth = '100%';
            break;
        case 'error':
            displayStatus = 'Error';
            badgeClass += ' status-error';
            progressWidth = '0%';
            break;
    }
    
    stageElement.dataset.status = status;
    statusBadge.textContent = displayStatus;
    statusBadge.className = badgeClass;
    progressBar.style.width = progressWidth;
    
    // Store details for stage details panel
    stageElement.dataset.details = details;
}

// Setup event listeners
function setupEventListeners() {
    // Start workflow button
    const startBtn = document.getElementById('startWorkflowBtn');
    if (startBtn) {
        startBtn.addEventListener('click', startWorkflow);
    }
    
    // Pause button
    const pauseBtn = document.getElementById('pauseBtn');
    if (pauseBtn) {
        pauseBtn.addEventListener('click', pauseWorkflow);
    }
    
    // Reset button
    const resetBtn = document.getElementById('resetBtn');
    if (resetBtn) {
        resetBtn.addEventListener('click', resetWorkflow);
    }
    
    // Speed controls
    document.querySelectorAll('[data-speed]').forEach(btn => {
        btn.addEventListener('click', (e) => {
            playbackSpeed = parseInt(e.target.dataset.speed);
            document.querySelectorAll('[data-speed]').forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
        });
    });
    
    // Stage click handlers
    document.querySelectorAll('.pipeline-stage').forEach(stage => {
        stage.addEventListener('click', () => showStageDetails(stage));
    });
    
    // Close panel button
    const closeBtn = document.getElementById('closePanelBtn');
    if (closeBtn) {
        closeBtn.addEventListener('click', hideStageDetails);
    }
    
    // Clear log button
    const clearLogBtn = document.getElementById('clearLogBtn');
    if (clearLogBtn) {
        clearLogBtn.addEventListener('click', clearLog);
    }
}

// Start workflow
async function startWorkflow() {
    if (isRunning) return;
    
    isRunning = true;
    isPaused = false;
    startTime = Date.now();
    
    // Update UI
    const startBtn = document.getElementById('startWorkflowBtn');
    const pauseBtn = document.getElementById('pauseBtn');
    
    if (startBtn) startBtn.disabled = true;
    if (pauseBtn) pauseBtn.disabled = false;
    
    // Start timer
    startTimer();
    
    // Log start
    addLogEntry('info', 'Workflow started');
    
    // Check if we should use real backend
    if (useRealBackend && wsManager && wsManager.isConnected) {
        // Run real backend pipeline
        await runRealPipeline();
    } else {
        // Run simulated workflow
        addLogEntry('warning', 'Backend not connected - running simulation');
        
        // Run stages
        for (let i = 0; i < stages.length; i++) {
            if (!isRunning) break;
            
            currentStageIndex = i;
            await runStage(stages[i]);
        }
        
        // Complete
        if (isRunning) {
            completeWorkflow();
        }
    }
}

// Run real backend pipeline
async function runRealPipeline() {
    try {
        addLogEntry('info', 'Calling backend API to run complete pipeline...');
        
        // Call the backend API
        const response = await fetch('http://localhost:8000/api/run-pipeline', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                use_sample_data: true,
                tax_year: 2024,
                company_name: 'Acme Corporation'
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || errorData.message || `HTTP error! status: ${response.status}`);
        }
        
        const result = await response.json();
        
        addLogEntry('success', `Pipeline completed successfully!`);
        addLogEntry('info', `Report ID: ${result.report_id}`);
        addLogEntry('info', `Projects: ${result.project_count}`);
        addLogEntry('info', `Total Hours: ${result.total_qualified_hours.toFixed(1)}h`);
        addLogEntry('info', `Total Cost: $${result.total_qualified_cost.toLocaleString()}`);
        addLogEntry('info', `Estimated Credit: $${result.estimated_credit.toLocaleString()}`);
        addLogEntry('info', `Execution Time: ${result.execution_time_seconds.toFixed(1)}s`);
        
        // Show download button
        showDownloadButton(result.report_id, result.pdf_path);
        
        // Complete workflow
        completeWorkflow();
        
    } catch (error) {
        addLogEntry('error', `Pipeline failed: ${error.message}`);
        
        // Show error notification
        if (typeof showNotification === 'function') {
            showNotification(`Pipeline failed: ${error.message}`, 'error');
        } else {
            alert(`Pipeline failed: ${error.message}`);
        }
        
        // Reset workflow
        isRunning = false;
        stopTimer();
        
        const startBtn = document.getElementById('startWorkflowBtn');
        const pauseBtn = document.getElementById('pauseBtn');
        
        if (startBtn) startBtn.disabled = false;
        if (pauseBtn) pauseBtn.disabled = true;
    }
}

// Show download button for generated report
function showDownloadButton(reportId, pdfPath) {
    // Check if download section already exists
    let downloadSection = document.getElementById('downloadSection');
    
    if (!downloadSection) {
        // Create download section
        downloadSection = document.createElement('section');
        downloadSection.id = 'downloadSection';
        downloadSection.className = 'download-section';
        downloadSection.innerHTML = `
            <div class="download-header">
                <h3>Report Generated Successfully!</h3>
            </div>
            <div class="download-body">
                <p class="download-info">
                    <strong>Report ID:</strong> <span id="downloadReportId"></span>
                </p>
                <p class="download-info">
                    <strong>File Path:</strong> <span id="downloadFilePath"></span>
                </p>
                <div class="download-actions">
                    <button class="btn btn-primary" id="downloadReportBtn">
                        <span class="icon">📥</span> Download Report
                    </button>
                    <button class="btn btn-secondary" id="viewReportsBtn">
                        <span class="icon">📄</span> View All Reports
                    </button>
                </div>
            </div>
        `;
        
        // Insert after workflow log
        const workflowLog = document.querySelector('.workflow-log');
        if (workflowLog && workflowLog.parentNode) {
            workflowLog.parentNode.insertBefore(downloadSection, workflowLog.nextSibling);
        }
    }
    
    // Update download section content
    document.getElementById('downloadReportId').textContent = reportId;
    document.getElementById('downloadFilePath').textContent = pdfPath;
    
    // Add event listeners
    const downloadBtn = document.getElementById('downloadReportBtn');
    if (downloadBtn) {
        downloadBtn.onclick = () => downloadReport(reportId);
    }
    
    const viewReportsBtn = document.getElementById('viewReportsBtn');
    if (viewReportsBtn) {
        viewReportsBtn.onclick = () => {
            window.location.href = 'reports.html';
        };
    }
    
    // Show the section with animation
    downloadSection.style.display = 'block';
    setTimeout(() => {
        downloadSection.classList.add('active');
    }, 100);
}

// Download report
async function downloadReport(reportId) {
    try {
        addLogEntry('info', `Downloading report: ${reportId}`);
        
        // Call download endpoint
        const response = await fetch(`http://localhost:8000/api/download/report/${reportId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        // Get filename from Content-Disposition header
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `${reportId}.pdf`;
        if (contentDisposition) {
            const filenameMatch = contentDisposition.match(/filename="?(.+)"?/);
            if (filenameMatch) {
                filename = filenameMatch[1];
            }
        }
        
        // Create blob and download
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        
        addLogEntry('success', `Report downloaded: ${filename}`);
        
        if (typeof showNotification === 'function') {
            showNotification(`Report downloaded successfully: ${filename}`, 'success');
        }
        
    } catch (error) {
        addLogEntry('error', `Download failed: ${error.message}`);
        
        if (typeof showNotification === 'function') {
            showNotification(`Download failed: ${error.message}`, 'error');
        } else {
            alert(`Download failed: ${error.message}`);
        }
    }
}

// Run single stage
async function runStage(stage) {
    const stageElement = document.querySelector(`.pipeline-stage[data-stage="${stage.id}"]`);
    const statusBadge = stageElement.querySelector('.status-badge');
    const progressBar = stageElement.querySelector('.progress-bar-inner');
    
    // Set to in progress
    stageElement.dataset.status = 'in_progress';
    statusBadge.textContent = 'In Progress';
    statusBadge.className = 'status-badge status-info';
    
    addLogEntry('info', `${stage.name} started`);
    
    // Simulate progress
    const adjustedDuration = stage.duration / playbackSpeed;
    const steps = 100;
    const stepDuration = adjustedDuration / steps;
    
    for (let i = 0; i <= steps; i++) {
        if (!isRunning) break;
        
        progressBar.style.width = `${i}%`;
        await sleep(stepDuration);
    }
    
    // Set to completed
    stageElement.dataset.status = 'completed';
    statusBadge.textContent = 'Completed';
    statusBadge.className = 'status-badge status-healthy';
    progressBar.style.width = '100%';
    
    addLogEntry('success', `${stage.name} completed`);
    
    // Update overall progress
    updateOverallProgress();
}

// Pause workflow
function pauseWorkflow() {
    isPaused = !isPaused;
    const pauseBtn = document.getElementById('pauseBtn');
    
    if (isPaused) {
        isRunning = false;
        pauseBtn.innerHTML = '<span class="icon">▶️</span> Resume';
        addLogEntry('warning', 'Workflow paused');
        stopTimer();
    } else {
        isRunning = true;
        pauseBtn.innerHTML = '<span class="icon">⏸️</span> Pause';
        addLogEntry('info', 'Workflow resumed');
        startTimer();
        continueWorkflow();
    }
}

// Continue workflow after pause
async function continueWorkflow() {
    for (let i = currentStageIndex; i < stages.length; i++) {
        if (!isRunning) break;
        await runStage(stages[i]);
    }
    
    if (isRunning) {
        completeWorkflow();
    }
}

// Complete workflow
function completeWorkflow() {
    isRunning = false;
    stopTimer();
    
    document.getElementById('startWorkflowBtn').disabled = false;
    document.getElementById('pauseBtn').disabled = true;
    
    addLogEntry('success', 'Workflow completed successfully!');
    
    // Show completion message
    setTimeout(() => {
        alert('Workflow completed! Report generated successfully.');
    }, 500);
}

// Reset workflow
function resetWorkflow() {
    isRunning = false;
    isPaused = false;
    currentStageIndex = 0;
    elapsedSeconds = 0;
    
    stopTimer();
    
    // Reset UI
    document.getElementById('startWorkflowBtn').disabled = false;
    document.getElementById('pauseBtn').disabled = true;
    document.getElementById('pauseBtn').innerHTML = '<span class="icon">⏸️</span> Pause';
    
    // Reset stages
    document.querySelectorAll('.pipeline-stage').forEach(stage => {
        stage.dataset.status = 'pending';
        const statusBadge = stage.querySelector('.status-badge');
        statusBadge.textContent = 'Pending';
        statusBadge.className = 'status-badge status-pending';
        stage.querySelector('.progress-bar-inner').style.width = '0%';
    });
    
    // Reset progress
    updateOverallProgress();
    
    // Clear log
    clearLog();
    addLogEntry('info', 'Workflow ready to start');
}

// Update overall progress
function updateOverallProgress() {
    const completed = document.querySelectorAll('.pipeline-stage[data-status="completed"]').length;
    const percentage = (completed / stages.length) * 100;
    
    document.getElementById('overallProgressBar').style.width = `${percentage}%`;
    document.getElementById('progressPercentage').textContent = `${Math.round(percentage)}%`;
    document.getElementById('completedStages').textContent = completed;
    
    // Calculate remaining time
    if (completed > 0 && completed < stages.length) {
        const avgTimePerStage = elapsedSeconds / completed;
        const remainingStages = stages.length - completed;
        const remainingSeconds = Math.round(avgTimePerStage * remainingStages);
        document.getElementById('remainingTime').textContent = formatDuration(remainingSeconds);
    } else {
        document.getElementById('remainingTime').textContent = '--:--';
    }
}

// Start timer
function startTimer() {
    timerInterval = setInterval(() => {
        elapsedSeconds++;
        document.getElementById('elapsedTime').textContent = formatDuration(elapsedSeconds);
    }, 1000);
}

// Stop timer
function stopTimer() {
    if (timerInterval) {
        clearInterval(timerInterval);
        timerInterval = null;
    }
}

// Show stage details
function showStageDetails(stageElement) {
    const stageId = stageElement.dataset.stage;
    const stage = stages[stageId - 1];
    const panel = document.getElementById('stageDetailsPanel');
    const title = document.getElementById('detailsTitle');
    const body = document.getElementById('detailsBody');
    
    const status = stageElement.dataset.status || 'pending';
    const details = stageElement.dataset.details || 'No details available';
    const backendStage = stage.backendStage || 'N/A';
    
    title.textContent = stage.name;
    body.innerHTML = `
        <div class="detail-section">
            <h4>Status</h4>
            <p class="status-${status}">${status.replace('_', ' ').toUpperCase()}</p>
        </div>
        <div class="detail-section">
            <h4>Backend Stage</h4>
            <p>${backendStage}</p>
        </div>
        <div class="detail-section">
            <h4>Details</h4>
            <p>${details}</p>
        </div>
        <div class="detail-section">
            <h4>Description</h4>
            <p>${getStageDescription(stageId)}</p>
        </div>
    `;
    
    panel.classList.add('active');
}

// Get stage description
function getStageDescription(stageId) {
    const descriptions = {
        1: 'Collects employee time tracking data from Clockify and payroll data from Unified.to.',
        2: 'Validates and normalizes ingested data using Pydantic models.',
        3: 'Determines R&D qualification using RAG system and You.com Agent API.',
        4: 'Generates technical narratives for qualified projects using You.com Agent API.',
        5: 'Reviews narratives for compliance using You.com Express Agent API.',
        6: 'Generates audit-ready PDF report using ReportLab.'
    };
    return descriptions[stageId] || 'Stage of the R&D tax credit automation pipeline.';
}

// Hide stage details
function hideStageDetails() {
    document.getElementById('stageDetailsPanel').classList.remove('active');
}

// Add log entry
function addLogEntry(type, message) {
    const logBody = document.getElementById('logBody');
    const timestamp = new Date().toLocaleTimeString();
    
    const entry = document.createElement('div');
    entry.className = `log-entry log-${type}`;
    entry.innerHTML = `
        <span class="log-timestamp">[${timestamp}]</span>
        <span class="log-message">${message}</span>
    `;
    
    logBody.appendChild(entry);
    logBody.scrollTop = logBody.scrollHeight;
}

// Clear log
function clearLog() {
    const logBody = document.getElementById('logBody');
    logBody.innerHTML = '';
}

// Sleep utility
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// Format duration in seconds to MM:SS
function formatDuration(seconds) {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
}

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (wsManager) {
        wsManager.close();
    }
});

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initWorkflow);
} else {
    initWorkflow();
}
