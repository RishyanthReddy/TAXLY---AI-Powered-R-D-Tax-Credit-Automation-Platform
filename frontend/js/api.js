/**
 * API Integration Module
 * Handles all backend API communication
 */

// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// API Client
const api = {
    /**
     * Get health status from backend
     */
    async getHealth() {
        try {
            const response = await fetch(`${API_BASE_URL}/health`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Health check failed:', error);
            throw error;
        }
    },

    /**
     * Load existing reports from backend
     * Scans outputs/reports/ directory and returns report metadata
     */
    async loadExistingReports() {
        try {
            const response = await fetch(`${API_BASE_URL}/api/reports/list`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Failed to load reports:', error);
            // Return empty array if endpoint doesn't exist yet
            // This allows the frontend to work with sample data
            return [];
        }
    },

    /**
     * Get report metadata by ID
     */
    async getReportMetadata(reportId) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/reports/${reportId}/metadata`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error('Failed to get report metadata:', error);
            throw error;
        }
    },

    /**
     * Download report PDF
     */
    async downloadReport(reportId) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/download/report/${reportId}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            // Get filename from Content-Disposition header
            const contentDisposition = response.headers.get('Content-Disposition');
            let filename = reportId;
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
            
            return { success: true, filename };
        } catch (error) {
            console.error('Failed to download report:', error);
            throw error;
        }
    },

    /**
     * Generate new report from qualified projects
     * @param {Array} qualifiedProjects - Array of qualified project objects
     * @param {number} taxYear - Tax year for the report
     * @param {string} companyName - Optional company name
     * @returns {Promise<Object>} Report generation response with report_id and pdf_path
     */
    async generateReport(qualifiedProjects, taxYear, companyName = 'Acme Corporation') {
        try {
            const response = await fetch(`${API_BASE_URL}/api/generate-report`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ 
                    qualified_projects: qualifiedProjects,
                    tax_year: taxYear,
                    company_name: companyName
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.message || errorData.detail || `HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Failed to generate report:', error);
            throw error;
        }
    },

    /**
     * Qualify projects
     */
    async qualifyProjects(timeEntries, costs, taxYear) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/qualify`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    time_entries: timeEntries,
                    costs: costs,
                    tax_year: taxYear
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Failed to qualify projects:', error);
            throw error;
        }
    },

    /**
     * Ingest data from external APIs
     */
    async ingestData(startDate, endDate, credentials) {
        try {
            const response = await fetch(`${API_BASE_URL}/api/ingest`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    start_date: startDate,
                    end_date: endDate,
                    ...credentials
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.message || `HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Failed to ingest data:', error);
            throw error;
        }
    },

    /**
     * Run complete pipeline
     * @param {boolean} useSampleData - Whether to use sample data from fixtures
     * @param {number} taxYear - Tax year for the report
     * @param {string} companyName - Company name for report header
     * @returns {Promise<Object>} Pipeline execution response with report details
     */
    async runPipeline(useSampleData = true, taxYear = 2024, companyName = 'Acme Corporation') {
        try {
            const response = await fetch(`${API_BASE_URL}/api/run-pipeline`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    use_sample_data: useSampleData,
                    tax_year: taxYear,
                    company_name: companyName
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || errorData.message || `HTTP error! status: ${response.status}`);
            }
            
            return await response.json();
        } catch (error) {
            console.error('Failed to run pipeline:', error);
            throw error;
        }
    }
};

/**
 * Load sample qualified projects from fixtures
 * @returns {Promise<Array>} Array of qualified project objects
 */
async function loadSampleQualifiedProjects() {
    try {
        // Try multiple paths to find the fixture file
        const paths = [
            '../tests/fixtures/sample_qualified_projects.json',
            '../../tests/fixtures/sample_qualified_projects.json',
            '/tests/fixtures/sample_qualified_projects.json',
            'data/sample_qualified_projects.json'
        ];
        
        for (const path of paths) {
            try {
                const response = await fetch(path);
                if (response.ok) {
                    const data = await response.json();
                    console.log(`Loaded sample qualified projects from ${path}`);
                    return data;
                }
            } catch (e) {
                // Continue to next path
                continue;
            }
        }
        
        // If all paths fail, return empty array
        console.warn('Could not load sample_qualified_projects.json from any path, using empty array');
        return [];
    } catch (error) {
        console.error('Error loading sample qualified projects:', error);
        return [];
    }
}

/**
 * Parse PDF filename to extract metadata
 * Format: rd_tax_credit_report_{report_id}_{timestamp}.pdf
 * Example: rd_tax_credit_report_2024_20251030_143000.pdf
 */
function parseReportFilename(filename) {
    // Remove .pdf extension
    const nameWithoutExt = filename.replace('.pdf', '');
    
    // Try to parse standard format: rd_tax_credit_report_{tax_year}_{timestamp}
    const standardMatch = nameWithoutExt.match(/rd_tax_credit_report_(\d{4})_(\d{8})_(\d{6})/);
    if (standardMatch) {
        const [, taxYear, dateStr, timeStr] = standardMatch;
        const year = dateStr.substring(0, 4);
        const month = dateStr.substring(4, 6);
        const day = dateStr.substring(6, 8);
        const hour = timeStr.substring(0, 2);
        const minute = timeStr.substring(2, 4);
        const second = timeStr.substring(4, 6);
        
        return {
            reportId: `${taxYear}_${dateStr}_${timeStr}`,
            taxYear: parseInt(taxYear),
            generationDate: new Date(`${year}-${month}-${day}T${hour}:${minute}:${second}`),
            companyName: 'Acme Corporation' // Default, can be enhanced
        };
    }
    
    // Try to parse custom format: rd_tax_credit_report_{custom_id}_{timestamp}
    const customMatch = nameWithoutExt.match(/rd_tax_credit_report_(.+?)_(\d{8})_(\d{6})/);
    if (customMatch) {
        const [, customId, dateStr, timeStr] = customMatch;
        const year = dateStr.substring(0, 4);
        const month = dateStr.substring(4, 6);
        const day = dateStr.substring(6, 8);
        const hour = timeStr.substring(0, 2);
        const minute = timeStr.substring(2, 4);
        const second = timeStr.substring(4, 6);
        
        return {
            reportId: customId,
            taxYear: parseInt(year),
            generationDate: new Date(`${year}-${month}-${day}T${hour}:${minute}:${second}`),
            companyName: 'Acme Corporation' // Default
        };
    }
    
    // Fallback for other formats
    return {
        reportId: nameWithoutExt,
        taxYear: new Date().getFullYear(),
        generationDate: new Date(),
        companyName: 'Unknown'
    };
}

/**
 * Scan outputs/reports directory and build report list
 * This is a client-side implementation that works with the backend API
 */
async function scanReportsDirectory() {
    try {
        // First, try to get reports from backend API
        const reports = await api.loadExistingReports();
        if (reports && reports.length > 0) {
            return reports;
        }
        
        // If API doesn't return reports, we'll need to implement a backend endpoint
        // For now, return empty array and let the UI show sample data
        console.warn('No reports returned from backend API. Using sample data.');
        return [];
    } catch (error) {
        console.error('Failed to scan reports directory:', error);
        return [];
    }
}

/**
 * Get file size from backend
 */
async function getFileSize(filename) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/reports/${filename}/size`);
        if (!response.ok) {
            return 0;
        }
        const data = await response.json();
        return data.size || 0;
    } catch (error) {
        console.error('Failed to get file size:', error);
        return 0;
    }
}

/**
 * Get PDF page count from backend
 */
async function getPageCount(filename) {
    try {
        const response = await fetch(`${API_BASE_URL}/api/reports/${filename}/pages`);
        if (!response.ok) {
            return 0;
        }
        const data = await response.json();
        return data.pages || 0;
    } catch (error) {
        console.error('Failed to get page count:', error);
        return 0;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        api,
        parseReportFilename,
        scanReportsDirectory,
        getFileSize,
        getPageCount,
        loadSampleQualifiedProjects,
        API_BASE_URL
    };
}
