/**
 * Dashboard Page JavaScript
 * Handles dashboard interactions and data loading
 */

// Sample data
const sampleTeamData = [
    { name: 'John Smith', role: 'Senior Developer', projects: 3, hours: 120, rate: 75 },
    { name: 'Sarah Johnson', role: 'Software Engineer', projects: 2, hours: 95, rate: 65 },
    { name: 'Michael Chen', role: 'Tech Lead', projects: 4, hours: 140, rate: 85 },
    { name: 'Emily Davis', role: 'Developer', projects: 2, hours: 88, rate: 60 },
    { name: 'David Wilson', role: 'Senior Engineer', projects: 3, hours: 110, rate: 70 }
];

const creditsData = [
    { label: 'Project Alpha', value: 1200 },
    { label: 'Project Beta', value: 950 },
    { label: 'Project Gamma', value: 800 },
    { label: 'Project Delta', value: 658 },
    { label: 'Others', value: 1000 }
];

const qualificationData = [
    { label: 'Qualified', value: 85 },
    { label: 'Not Qualified', value: 15 }
];

// Initialize dashboard
function initDashboard() {
    loadTeamData();
    renderCharts();
    setupEventListeners();
    updateProgressCircles();
}

// Load team data into table
function loadTeamData() {
    const tbody = document.getElementById('teamTableBody');
    if (!tbody) return;
    
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

// Render charts
function renderCharts() {
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
    // Sync button
    const syncBtn = document.getElementById('syncBtn');
    if (syncBtn) {
        syncBtn.addEventListener('click', handleSync);
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

// Handle sync
function handleSync() {
    console.log('Syncing data...');
    // Show loading state
    const btn = document.getElementById('syncBtn');
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="spinner"></span> Syncing...';
    btn.disabled = true;
    
    // Simulate sync
    setTimeout(() => {
        btn.innerHTML = originalText;
        btn.disabled = false;
        alert('Data synced successfully!');
    }, 2000);
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
