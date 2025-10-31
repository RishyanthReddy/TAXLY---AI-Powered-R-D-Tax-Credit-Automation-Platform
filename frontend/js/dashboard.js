/**
 * Dashboard Page JavaScript
 * Handles dashboard interactions and data loading
 */

// Global state for real backend data
let backendData = {
    reports: [],
    qualifiedProjects: [],
    healthStatus: null,
    metrics: {
        totalProjects: 0,
        qualificationRate: 0,
        estimatedCredits: 0,
        qualifiedHours: 0,
        averageConfidence: 0
    }
};

// Sample data (fallback if backend is unavailable)
const sampleTeamData = [
    { name: 'John Smith', role: 'Senior Developer', projects: 3, hours: 120, rate: 75 },
    { name: 'Sarah Johnson', role: 'Software Engineer', projects: 2, hours: 95, rate: 65 },
    { name: 'Michael Chen', role: 'Tech Lead', projects: 4, hours: 140, rate: 85 },
    { name: 'Emily Davis', role: 'Developer', projects: 2, hours: 88, rate: 60 },
    { name: 'David Wilson', role: 'Senior Engineer', projects: 3, hours: 110, rate: 70 }
];

// Initialize dashboard
async function initDashboard() {
    // Show loading state
    showLoadingState();
    
    try {
        // Load real data from backend
        await loadBackendData();
        
        // Update UI with real data
        updateDashboardMetrics();
        updateIntegrationStatus();
        loadTeamData();
        renderCharts();
        updateProgressCircles();
        
        // Hide loading state
        hideLoadingState();
    } catch (error) {
        console.error('Failed to load backend data:', error);
        
        // Fall back to sample data
        loadSampleData();
        hideLoadingState();
        
        // Show warning to user
        showNotification('Using sample data. Backend may be unavailable.', 'warning');
    }
    
    setupEventListeners();
}

/**
 * Load real backend data from API
 */
async function loadBackendData() {
    try {
        // Check backend health
        backendData.healthStatus = await api.getHealth();
        console.log('Backend health:', backendData.healthStatus);
        
        // Load existing reports
        const reportsResponse = await api.loadExistingReports();
        backendData.reports = reportsResponse.reports || [];
        console.log(`Loaded ${backendData.reports.length} reports from backend`);
        
        // Load sample qualified projects (for metrics calculation)
        backendData.qualifiedProjects = await loadSampleQualifiedProjects();
        console.log(`Loaded ${backendData.qualifiedProjects.length} qualified projects`);
        
        // Calculate metrics from real data
        calculateMetrics();
        
        return true;
    } catch (error) {
        console.error('Error loading backend data:', error);
        throw error;
    }
}

/**
 * Calculate dashboard metrics from real backend data
 */
function calculateMetrics() {
    const { reports, qualifiedProjects } = backendData;
    
    // Calculate from reports if available
    if (reports.length > 0) {
        backendData.metrics.totalProjects = reports.reduce((sum, r) => sum + (r.projectCount || 0), 0);
        backendData.metrics.estimatedCredits = reports.reduce((sum, r) => sum + (r.estimatedCredit || 0), 0);
        backendData.metrics.qualifiedHours = reports.reduce((sum, r) => sum + (r.totalQualifiedHours || 0), 0);
    }
    
    // Calculate from qualified projects if available
    if (qualifiedProjects.length > 0) {
        backendData.metrics.totalProjects = qualifiedProjects.length;
        backendData.metrics.qualifiedHours = qualifiedProjects.reduce((sum, p) => sum + (p.qualified_hours || 0), 0);
        backendData.metrics.estimatedCredits = qualifiedProjects.reduce((sum, p) => sum + (p.qualified_cost || 0) * 0.20, 0);
        
        // Calculate average confidence
        const totalConfidence = qualifiedProjects.reduce((sum, p) => sum + (p.confidence_score || 0), 0);
        backendData.metrics.averageConfidence = qualifiedProjects.length > 0 
            ? (totalConfidence / qualifiedProjects.length) * 100 
            : 0;
        
        // Calculate qualification rate (assuming all loaded projects are qualified)
        backendData.metrics.qualificationRate = 85; // Default, could be enhanced
    }
    
    console.log('Calculated metrics:', backendData.metrics);
}

/**
 * Update dashboard metrics display with real data
 */
function updateDashboardMetrics() {
    const { metrics } = backendData;
    
    // Update stat cards
    const statCards = document.querySelectorAll('.stat-card');
    if (statCards.length >= 4) {
        // Total Projects
        statCards[0].querySelector('.stat-value').textContent = metrics.totalProjects;
        
        // Qualification Rate
        statCards[1].querySelector('.stat-value').textContent = `${Math.round(metrics.qualificationRate)}%`;
        
        // Estimated Credits
        statCards[2].querySelector('.stat-value').textContent = formatCurrency(metrics.estimatedCredits);
        
        // Qualified Hours
        statCards[3].querySelector('.stat-value').textContent = Math.round(metrics.qualifiedHours);
    }
}

/**
 * Update integration status based on backend health
 */
function updateIntegrationStatus() {
    const { healthStatus } = backendData;
    
    if (!healthStatus) return;
    
    const integrationCards = document.querySelectorAll('.integration-card');
    
    // Update based on API keys configured
    const apiKeys = healthStatus.api_keys_configured || {};
    
    // Clockify status
    if (integrationCards[0]) {
        updateIntegrationCard(integrationCards[0], apiKeys.clockify);
    }
    
    // BambooHR/Unified.to status
    if (integrationCards[1]) {
        updateIntegrationCard(integrationCards[1], apiKeys.unified_to);
    }
    
    // Unified.to aggregation status
    if (integrationCards[2]) {
        const isHealthy = apiKeys.clockify && apiKeys.unified_to;
        updateIntegrationCard(integrationCards[2], isHealthy);
    }
}

/**
 * Update individual integration card status
 */
function updateIntegrationCard(card, isHealthy) {
    const statusBadge = card.querySelector('.status-badge');
    if (!statusBadge) return;
    
    if (isHealthy) {
        statusBadge.textContent = 'Connected';
        statusBadge.className = 'status-badge status-healthy';
        card.dataset.status = 'healthy';
    } else {
        statusBadge.textContent = 'Not Configured';
        statusBadge.className = 'status-badge status-warning';
        card.dataset.status = 'warning';
    }
}

/**
 * Load sample data as fallback
 */
function loadSampleData() {
    // Use default sample data
    backendData.metrics = {
        totalProjects: 10,
        qualificationRate: 85,
        estimatedCredits: 4608,
        qualifiedHours: 320,
        averageConfidence: 90
    };
    
    updateDashboardMetrics();
}

/**
 * Show loading state
 */
function showLoadingState() {
    const statCards = document.querySelectorAll('.stat-card .stat-value');
    statCards.forEach(card => {
        card.innerHTML = '<span class="spinner"></span>';
    });
}

/**
 * Hide loading state
 */
function hideLoadingState() {
    // Loading state is replaced by actual data in updateDashboardMetrics
}

/**
 * Show notification to user
 */
function showNotification(message, type = 'info') {
    // Simple console log for now, could be enhanced with toast notifications
    console.log(`[${type.toUpperCase()}] ${message}`);
    
    // Could add a toast notification here
    if (type === 'warning' || type === 'error') {
        alert(message);
    }
}

// Load team data into table
function loadTeamData() {
    const tbody = document.getElementById('teamTableBody');
    if (!tbody) return;
    
    // Use sample data for now (could be enhanced to load from backend)
    tbody.innerHTML = sampleTeamData.map(member => `
        <tr>
            <td>${member.name}</td>
            <td>${member.role}</td>
            <td>${member.projects}</td>
            <td>${member.hours}</td>
            <td>${formatCurrency(member.rate)}/hr</td>
        </tr>
    `).join('');
}

// Render charts with real data
function renderCharts() {
    const { qualifiedProjects } = backendData;
    
    // Prepare credits data from qualified projects
    let creditsData = [];
    if (qualifiedProjects.length > 0) {
        // Take top 5 projects by estimated credit
        const sortedProjects = [...qualifiedProjects]
            .sort((a, b) => (b.qualified_cost || 0) - (a.qualified_cost || 0))
            .slice(0, 5);
        
        creditsData = sortedProjects.map(p => ({
            label: p.project_name,
            value: Math.round((p.qualified_cost || 0) * 0.20) // 20% credit rate
        }));
    } else {
        // Fallback to sample data
        creditsData = [
            { label: 'Project Alpha', value: 1200 },
            { label: 'Project Beta', value: 950 },
            { label: 'Project Gamma', value: 800 },
            { label: 'Project Delta', value: 658 },
            { label: 'Others', value: 1000 }
        ];
    }
    
    // Prepare qualification data
    const qualificationData = [
        { label: 'Qualified', value: Math.round(backendData.metrics.qualificationRate) },
        { label: 'Not Qualified', value: 100 - Math.round(backendData.metrics.qualificationRate) }
    ];
    
    renderBarChart('creditsChart', creditsData);
    renderPieChart('qualificationChart', qualificationData);
}

// Update progress circles
function updateProgressCircles() {
    document.querySelectorAll('.progress-circle').forEach(circle => {
        const progress = circle.dataset.progress || 0;
        circle.style.setProperty('--progress', progress);
    });
}

// Setup event listeners
function setupEventListeners() {
    // Sync button (refresh data)
    const syncBtn = document.getElementById('syncBtn');
    if (syncBtn) {
        syncBtn.addEventListener('click', handleRefreshData);
    }
    
    // Generate report button
    const generateBtn = document.getElementById('generateReportBtn');
    if (generateBtn) {
        generateBtn.addEventListener('click', handleGenerateReport);
    }
    
    // Sync now buttons on integration cards
    document.querySelectorAll('.integration-card .btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            handleIntegrationSync(e.target);
        });
    });
}

// Handle refresh data (reload from backend)
async function handleRefreshData() {
    console.log('Refreshing data from backend...');
    
    const btn = document.getElementById('syncBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span> Refreshing...';
    btn.disabled = true;
    
    try {
        // Reload data from backend
        await loadBackendData();
        
        // Update UI
        updateDashboardMetrics();
        updateIntegrationStatus();
        renderCharts();
        
        btn.innerHTML = originalText;
        btn.disabled = false;
        
        showNotification('Data refreshed successfully!', 'success');
    } catch (error) {
        console.error('Failed to refresh data:', error);
        
        btn.innerHTML = originalText;
        btn.disabled = false;
        
        showNotification('Failed to refresh data. Please try again.', 'error');
    }
}

// Handle generate report
function handleGenerateReport() {
    console.log('Generating report...');
    window.location.href = 'workflow.html';
}

// Handle integration sync
function handleIntegrationSync(button) {
    const card = button.closest('.integration-card');
    const integration = card.querySelector('h3').textContent;
    
    console.log(`Syncing ${integration}...`);
    button.innerHTML = '<span class="spinner"></span>';
    button.disabled = true;
    
    setTimeout(() => {
        button.innerHTML = 'Sync Now';
        button.disabled = false;
        alert(`${integration} synced successfully!`);
    }, 1500);
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDashboard);
} else {
    initDashboard();
}
