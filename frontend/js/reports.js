/**
 * Reports Page JavaScript
 * Handles reports display and interactions with backend integration
 */

// Sample reports data (fallback if backend is unavailable)
const sampleReports = [
    {
        id: 'RD_TAX_2024_20251030_143000',
        filename: 'rd_tax_credit_report_2024_20251030_143000.pdf',
        generationDate: '2024-10-30T14:30:00',
        taxYear: 2024,
        companyName: 'Acme Corporation',
        totalQualifiedHours: 320.0,
        totalQualifiedCost: 23040.00,
        estimatedCredit: 4608.00,
        projectCount: 10,
        fileSize: 87654,
        pageCount: 12,
        status: 'complete'
    },
    {
        id: 'RD_TAX_2023_20240115_091500',
        filename: 'rd_tax_credit_report_2023_20240115_091500.pdf',
        generationDate: '2024-01-15T09:15:00',
        taxYear: 2023,
        companyName: 'Acme Corporation',
        totalQualifiedHours: 285.5,
        totalQualifiedCost: 20550.00,
        estimatedCredit: 4110.00,
        projectCount: 8,
        fileSize: 76234,
        pageCount: 10,
        status: 'complete'
    }
];

let currentReports = [];
let allReports = [];
let selectedReport = null;
let backendAvailable = false;

// Initialize reports page
async function initReports() {
    showLoadingState();
    await loadReportsFromBackend();
    updateStatistics();
    setupEventListeners();
}

// Show loading state
function showLoadingState() {
    const grid = document.getElementById('reportsGrid');
    if (grid) {
        grid.innerHTML = `
            <div class="loading-state">
                <div class="spinner"></div>
                <p>Loading reports from backend...</p>
            </div>
        `;
    }
}

// Load reports from backend
async function loadReportsFromBackend() {
    try {
        // Check backend health
        const health = await api.getHealth();
        backendAvailable = health.status === 'healthy';
        
        if (backendAvailable) {
            console.log('Backend is healthy, loading real reports...');
            
            // Load existing reports from backend
            const backendReports = await loadExistingReportsFromBackend();
            
            if (backendReports.length > 0) {
                allReports = backendReports;
                currentReports = [...allReports];
                
                // Store in localStorage for quick access
                storage.set('reports', allReports);
                storage.set('reportsLastUpdated', new Date().toISOString());
                
                console.log(`Loaded ${allReports.length} reports from backend`);
            } else {
                console.warn('No reports found in backend, using sample data');
                allReports = [...sampleReports];
                currentReports = [...allReports];
            }
        } else {
            console.warn('Backend unavailable, using sample data');
            allReports = [...sampleReports];
            currentReports = [...allReports];
        }
    } catch (error) {
        console.error('Failed to load reports from backend:', error);
        
        // Try to load from localStorage cache
        const cachedReports = storage.get('reports');
        if (cachedReports && cachedReports.length > 0) {
            console.log('Using cached reports from localStorage');
            allReports = cachedReports;
            currentReports = [...allReports];
        } else {
            console.log('Using sample data as fallback');
            allReports = [...sampleReports];
            currentReports = [...allReports];
        }
    }
    
    loadReports();
}

// Load existing reports from backend outputs/reports directory
async function loadExistingReportsFromBackend() {
    try {
        // Get list of PDF files from backend
        const response = await fetch('http://localhost:8000/api/reports/list');
        
        if (!response.ok) {
            console.warn('Backend reports list endpoint not available yet');
            return await scanLocalReports();
        }
        
        const data = await response.json();
        return data.reports || [];
    } catch (error) {
        console.error('Error loading reports from backend:', error);
        return await scanLocalReports();
    }
}

// Scan local reports (fallback method using known filenames)
async function scanLocalReports() {
    // List of known report files from the outputs/reports directory
    const knownReports = [
        'rd_tax_credit_report_2024_20251030_135256.pdf',
        'rd_tax_credit_report_2024_20251030_133741.pdf',
        'rd_tax_credit_report_2024_20251030_124136.pdf',
        'rd_tax_credit_report_2024_20251030_123853.pdf',
        'rd_tax_credit_report_2024_20251030_123658.pdf',
        'rd_tax_credit_report_RPT-2024-001_20251030_000706.pdf',
        'rd_tax_credit_report_RPT-2024-003_20251030_000706.pdf',
        'professional_audit_report.pdf',
        'custom_styled_report.pdf'
    ];
    
    const reports = [];
    
    for (const filename of knownReports) {
        try {
            // Parse filename to extract metadata
            const metadata = parseReportFilename(filename);
            
            // Try to get file size from backend
            let fileSize = 85000; // Default ~85KB
            let pageCount = 12; // Default
            
            try {
                const sizeResponse = await fetch(`http://localhost:8000/api/reports/${filename}/info`);
                if (sizeResponse.ok) {
                    const info = await sizeResponse.json();
                    fileSize = info.size || fileSize;
                    pageCount = info.pages || pageCount;
                }
            } catch (e) {
                // Use defaults
            }
            
            reports.push({
                id: metadata.reportId,
                filename: filename,
                generationDate: metadata.generationDate.toISOString(),
                taxYear: metadata.taxYear,
                companyName: metadata.companyName,
                totalQualifiedHours: 320.0, // Default values
                totalQualifiedCost: 23040.00,
                estimatedCredit: 4608.00,
                projectCount: 10,
                fileSize: fileSize,
                pageCount: pageCount,
                status: 'complete'
            });
        } catch (error) {
            console.error(`Failed to process report ${filename}:`, error);
        }
    }
    
    return reports;
}

// Load reports into table
function loadReports() {
    const tableBody = document.getElementById('reportsTableBody');
    const emptyState = document.getElementById('emptyState');
    const table = document.getElementById('reportsTable');
    
    if (!tableBody) return;
    
    if (currentReports.length === 0) {
        if (table) table.style.display = 'none';
        if (emptyState) emptyState.style.display = 'block';
        return;
    }
    
    if (table) table.style.display = 'table';
    if (emptyState) emptyState.style.display = 'none';
    
    tableBody.innerHTML = currentReports.map(report => `
        <tr data-report-id="${report.id}">
            <td>
                <div class="report-name">${report.companyName} Tax Credit ${report.taxYear}</div>
                <div class="report-id">${report.id}</div>
            </td>
            <td class="client-name">${report.companyName}</td>
            <td class="tax-year">${report.taxYear}</td>
            <td>
                <span class="status-badge status-${report.status}">${capitalize(report.status)}</span>
            </td>
            <td>${formatDate(report.generationDate)}</td>
            <td>${formatFileSize(report.fileSize)}</td>
            <td>
                <div class="table-actions" onclick="event.stopPropagation()">
                    <button class="action-icon-btn" onclick="previewPdfInViewer('${report.id}')" title="Preview PDF">
                        📄
                    </button>
                    <button class="action-icon-btn" onclick="viewReport('${report.id}')" title="View Details">
                        ℹ️
                    </button>
                    <button class="action-icon-btn" onclick="downloadReport('${report.id}')" title="Download PDF">
                        ⬇️
                    </button>
                </div>
            </td>
        </tr>
    `).join('');
}

// Update statistics
function updateStatistics() {
    const totalReports = currentReports.length;
    const completeReports = currentReports.filter(r => r.status === 'complete').length;
    const inProgressReports = currentReports.filter(r => r.status === 'in_progress' || r.status === 'partial').length;
    const totalSize = currentReports.reduce((sum, r) => sum + r.fileSize, 0);
    const avgSize = totalReports > 0 ? totalSize / totalReports : 0;
    
    // Latest date
    const latestDate = currentReports.length > 0 
        ? formatDate(currentReports[0].generationDate)
        : '-';
    
    // This month count
    const now = new Date();
    const thisMonthCount = currentReports.filter(r => {
        const reportDate = new Date(r.generationDate);
        return reportDate.getMonth() === now.getMonth() && 
               reportDate.getFullYear() === now.getFullYear();
    }).length;
    
    // Update donut chart
    document.getElementById('totalReports').textContent = totalReports;
    document.getElementById('completeReports').textContent = completeReports;
    document.getElementById('inProgressReports').textContent = inProgressReports;
    
    // Update donut segment (percentage of complete reports)
    const completePercentage = totalReports > 0 ? (completeReports / totalReports) * 100 : 0;
    const donutSegment = document.getElementById('donutSegment');
    if (donutSegment) {
        const circumference = 2 * Math.PI * 40; // radius = 40
        const offset = circumference - (completePercentage / 100) * circumference;
        donutSegment.style.strokeDashoffset = offset;
    }
    
    // Update storage metrics
    document.getElementById('totalSize').textContent = formatFileSize(totalSize);
    document.getElementById('avgSize').textContent = formatFileSize(avgSize);
    
    // Update activity metrics
    document.getElementById('latestDate').textContent = latestDate;
    document.getElementById('thisMonthCount').textContent = thisMonthCount;
}

// Setup event listeners
function setupEventListeners() {
    // Filter button
    const filterBtn = document.getElementById('filterBtn');
    if (filterBtn) {
        filterBtn.addEventListener('click', toggleFilterPanel);
    }
    
    // View sample report button
    const viewSampleBtn = document.getElementById('viewSampleReportBtn');
    if (viewSampleBtn) {
        viewSampleBtn.addEventListener('click', viewSampleReport);
    }
    
    // Generate new report button
    const generateBtn = document.getElementById('generateNewReportBtn');
    if (generateBtn) {
        generateBtn.addEventListener('click', generateNewReport);
    }
    
    // Apply filters button
    const applyBtn = document.getElementById('applyFiltersBtn');
    if (applyBtn) {
        applyBtn.addEventListener('click', applyFilters);
    }
    
    // Clear filters button
    const clearBtn = document.getElementById('clearFiltersBtn');
    if (clearBtn) {
        clearBtn.addEventListener('click', clearFilters);
    }
}

// View sample report (showcase 80KB+ PDF)
function viewSampleReport() {
    // Find the most recent complete report with largest file size
    const sampleReport = currentReports
        .filter(r => r.status === 'complete' && r.fileSize > 80000)
        .sort((a, b) => b.fileSize - a.fileSize)[0];
    
    if (sampleReport) {
        viewReport(sampleReport.id);
    } else if (currentReports.length > 0) {
        // Fallback to most recent report
        viewReport(currentReports[0].id);
    } else {
        showNotification('error', 'No reports available to view');
    }
}

// Toggle filter panel
function toggleFilterPanel() {
    const panel = document.getElementById('filterPanel');
    if (panel) {
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    }
}

// Apply filters
function applyFilters() {
    const taxYear = document.getElementById('filterTaxYear').value;
    const status = document.getElementById('filterStatus').value;
    const company = document.getElementById('filterCompany').value.toLowerCase();
    
    currentReports = sampleReports.filter(report => {
        if (taxYear && report.taxYear.toString() !== taxYear) return false;
        if (status && report.status !== status) return false;
        if (company && !report.companyName.toLowerCase().includes(company)) return false;
        return true;
    });
    
    loadReports();
    updateStatistics();
    toggleFilterPanel();
}

// Clear filters
function clearFilters() {
    document.getElementById('filterTaxYear').value = '';
    document.getElementById('filterStatus').value = '';
    document.getElementById('filterCompany').value = '';
    
    currentReports = [...sampleReports];
    loadReports();
    updateStatistics();
}

// View report
function viewReport(reportId) {
    selectedReport = currentReports.find(r => r.id === reportId);
    if (!selectedReport) return;
    
    // Populate modal
    document.getElementById('previewReportId').textContent = selectedReport.id;
    document.getElementById('previewCompany').textContent = selectedReport.companyName;
    document.getElementById('previewTaxYear').textContent = selectedReport.taxYear;
    document.getElementById('previewDate').textContent = formatDate(selectedReport.generationDate);
    document.getElementById('previewStatus').innerHTML = `<span class="status-badge status-${selectedReport.status}">${capitalize(selectedReport.status)}</span>`;
    
    document.getElementById('previewProjects').textContent = selectedReport.projectCount;
    document.getElementById('previewHours').textContent = selectedReport.totalQualifiedHours;
    document.getElementById('previewCost').textContent = formatCurrency(selectedReport.totalQualifiedCost);
    document.getElementById('previewCredit').textContent = formatCurrency(selectedReport.estimatedCredit);
    
    document.getElementById('previewFileSize').textContent = formatFileSize(selectedReport.fileSize);
    document.getElementById('previewPageCount').textContent = selectedReport.pageCount;
    document.getElementById('previewFilename').textContent = selectedReport.filename;
    
    // Generate PDF thumbnail
    generatePdfThumbnail(selectedReport);
    
    // Setup download button
    const downloadBtn = document.getElementById('downloadReportBtn');
    downloadBtn.onclick = () => downloadReport(selectedReport.id);
    
    // Setup PDF viewer button
    const openPdfBtn = document.getElementById('openPdfViewerBtn');
    if (openPdfBtn) {
        openPdfBtn.onclick = () => openFullPdfViewer(selectedReport);
    }
    
    // Show modal
    openModal();
}

// Generate PDF thumbnail for preview
async function generatePdfThumbnail(report) {
    const thumbnailContainer = document.getElementById('pdfThumbnailContainer');
    const thumbnailImg = document.getElementById('pdfThumbnail');
    
    if (!thumbnailContainer || !thumbnailImg) return;
    
    // Show loading state
    thumbnailContainer.innerHTML = `
        <div class="pdf-thumbnail-loading">
            <div class="spinner"></div>
            <p>Generating preview...</p>
        </div>
    `;
    
    try {
        // Use the filename (without .pdf) as the report_id for the backend
        const reportIdForBackend = report.filename.replace('.pdf', '');
        
        // Generate thumbnail using PDF.js
        const img = document.createElement('img');
        await generateThumbnail(reportIdForBackend, img, 300);
        
        // Replace loading state with thumbnail
        thumbnailContainer.innerHTML = '';
        thumbnailContainer.appendChild(img);
        
        // Make thumbnail clickable to open full viewer
        thumbnailContainer.style.cursor = 'pointer';
        thumbnailContainer.onclick = () => openFullPdfViewer(report);
    } catch (error) {
        console.error('Failed to generate thumbnail:', error);
        
        // Show placeholder on error
        thumbnailContainer.innerHTML = `
            <img src="assets/images/pdf-placeholder.png" alt="PDF Preview Unavailable">
        `;
    }
}

// Open full PDF viewer
async function openFullPdfViewer(report) {
    try {
        // Close the preview modal first
        closeModal();
        
        // Use the filename (without .pdf) as the report_id for the backend
        const reportIdForBackend = report.filename.replace('.pdf', '');
        
        // Open PDF viewer with report data
        await openPdfViewer(reportIdForBackend, {
            filename: report.filename,
            fileSize: report.fileSize,
            generationDate: report.generationDate,
            reportId: reportIdForBackend
        });
        
        // Store report ID in title element for download functionality
        const titleEl = document.getElementById('pdfViewerTitle');
        if (titleEl) {
            titleEl.dataset.reportId = reportIdForBackend;
        }
    } catch (error) {
        console.error('Failed to open PDF viewer:', error);
        showNotification('error', `Failed to open PDF viewer: ${error.message}`);
    }
}

// Preview PDF directly in viewer (from table action button)
async function previewPdfInViewer(reportId) {
    const report = currentReports.find(r => r.id === reportId);
    if (!report) return;
    
    await openFullPdfViewer(report);
}

// Download report
async function downloadReport(reportId) {
    const report = currentReports.find(r => r.id === reportId);
    if (!report) return;
    
    console.log(`Downloading report: ${report.filename}`);
    
    try {
        // Show loading indicator
        const downloadBtn = document.getElementById('downloadReportBtn');
        if (downloadBtn) {
            downloadBtn.disabled = true;
            downloadBtn.innerHTML = '<span class="icon">⏳</span> Downloading...';
        }
        
        // Use the filename (without .pdf) as the report_id for the backend
        const reportIdForBackend = report.filename.replace('.pdf', '');
        
        // Download from backend
        await api.downloadReport(reportIdForBackend);
        
        // Show success message
        showNotification('success', `Downloaded ${report.filename} successfully!`);
        
        // Reset button
        if (downloadBtn) {
            downloadBtn.disabled = false;
            downloadBtn.innerHTML = '<span class="icon">⬇️</span> Download Report';
        }
    } catch (error) {
        console.error('Download failed:', error);
        showNotification('error', `Failed to download report: ${error.message}`);
        
        // Reset button
        const downloadBtn = document.getElementById('downloadReportBtn');
        if (downloadBtn) {
            downloadBtn.disabled = false;
            downloadBtn.innerHTML = '<span class="icon">⬇️</span> Download Report';
        }
    }
}

// Generate new report using sample data
async function generateNewReport() {
    console.log('Generating new report with sample data...');
    
    try {
        // Show loading state
        const generateBtn = document.getElementById('generateNewReportBtn');
        if (generateBtn) {
            generateBtn.disabled = true;
            generateBtn.innerHTML = '<span class="icon">⏳</span> Generating Report...';
        }
        
        // Show notification
        showNotification('info', 'Loading sample data and generating report...');
        
        // Load sample qualified projects from fixtures
        let qualifiedProjects = await loadSampleQualifiedProjects();
        
        // If loading failed, use fallback data
        if (!qualifiedProjects || qualifiedProjects.length === 0) {
            console.warn('Using fallback qualified projects data');
            qualifiedProjects = [
                {
                    project_name: "Alpha Development",
                    qualified_hours: 14.5,
                    qualified_cost: 1045.74,
                    confidence_score: 0.92,
                    qualification_percentage: 95.0,
                    supporting_citation: "The project involves developing a new authentication algorithm with encryption, which constitutes qualified research under IRC Section 41.",
                    reasoning: "This project clearly meets the four-part test for qualified research.",
                    irs_source: "CFR Title 26 § 1.41-4(a)(1) - Four-Part Test for Qualified Research",
                    flagged_for_review: false
                }
            ];
        }
        
        console.log(`Loaded ${qualifiedProjects.length} qualified projects`);
        
        // Get current tax year
        const taxYear = new Date().getFullYear();
        const companyName = 'Acme Corporation';
        
        // Call backend API to generate report
        console.log('Calling backend API to generate report...');
        const response = await api.generateReport(qualifiedProjects, taxYear, companyName);
        
        console.log('Report generation response:', response);
        
        if (response.success) {
            // Show success message
            showNotification('success', `Report generated successfully! Report ID: ${response.report_id}`);
            
            // Wait a moment for user to see the message
            await new Promise(resolve => setTimeout(resolve, 1500));
            
            // Refresh reports list to show the new report
            console.log('Refreshing reports list...');
            await loadReportsFromBackend();
            
            // Scroll to top to show the new report
            window.scrollTo({ top: 0, behavior: 'smooth' });
            
            // Optionally, open the new report in preview
            if (response.report_id) {
                // Find the new report in the list
                const newReport = currentReports.find(r => r.id === response.report_id);
                if (newReport) {
                    setTimeout(() => viewReport(response.report_id), 500);
                }
            }
        } else {
            throw new Error('Report generation failed');
        }
        
    } catch (error) {
        console.error('Error generating report:', error);
        showNotification('error', `Failed to generate report: ${error.message}`);
    } finally {
        // Reset button
        const generateBtn = document.getElementById('generateNewReportBtn');
        if (generateBtn) {
            generateBtn.disabled = false;
            generateBtn.innerHTML = '<span class="icon">➕</span> Generate New Report';
        }
    }
}

// Show notification
function showNotification(type, message) {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    
    // Choose icon based on type
    let icon = '✓';
    if (type === 'error') icon = '✗';
    if (type === 'info') icon = 'ℹ';
    if (type === 'warning') icon = '⚠';
    
    notification.innerHTML = `
        <span class="notification-icon">${icon}</span>
        <span class="notification-message">${message}</span>
    `;
    
    // Add to page
    document.body.appendChild(notification);
    
    // Animate in
    setTimeout(() => notification.classList.add('show'), 10);
    
    // Remove after 5 seconds (longer for info messages)
    const duration = type === 'info' ? 5000 : 3000;
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, duration);
}

// Open modal
function openModal() {
    const modal = document.getElementById('reportPreviewModal');
    if (modal) {
        modal.classList.add('active');
    }
}

// Close modal
function closeModal() {
    const modal = document.getElementById('reportPreviewModal');
    if (modal) {
        modal.classList.remove('active');
    }
    selectedReport = null;
}

// Initialize when DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initReports);
} else {
    initReports();
}
