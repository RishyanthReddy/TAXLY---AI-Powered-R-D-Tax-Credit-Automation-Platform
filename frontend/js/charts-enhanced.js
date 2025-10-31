/**
 * Enhanced Chart Rendering Functions
 * Polished charts matching reference images (donut charts, trend indicators, etc.)
 */

/**
 * Render donut chart with center value (like reference images)
 * @param {string} containerId - Container element ID
 * @param {Array} data - Array of {label, value, color} objects
 * @param {Object} options - Chart options {centerValue, centerLabel, size}
 */
function renderDonutChart(containerId, data, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const {
        centerValue = '',
        centerLabel = '',
        size = 160,
        strokeWidth = 20,
        showLegend = true
    } = options;
    
    const total = data.reduce((sum, item) => sum + item.value, 0);
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    
    let html = '<div class="donut-chart-container">';
    html += '<div class="donut-chart">';
    html += `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">`;
    
    let currentOffset = 0;
    
    data.forEach((item, index) => {
        const percentage = (item.value / total) * 100;
        const strokeDasharray = (item.value / total) * circumference;
        const strokeDashoffset = -currentOffset;
        
        const color = item.color || getChartColor(index);
        
        html += `
            <circle
                cx="${size / 2}"
                cy="${size / 2}"
                r="${radius}"
                fill="none"
                stroke="${color}"
                stroke-width="${strokeWidth}"
                stroke-dasharray="${strokeDasharray} ${circumference}"
                stroke-dashoffset="${strokeDashoffset}"
                class="donut-segment"
                data-label="${item.label}"
                data-value="${item.value}"
                data-percentage="${percentage.toFixed(1)}"
            />
        `;
        
        currentOffset += strokeDasharray;
    });
    
    html += '</svg>';
    
    // Center value and label
    if (centerValue || centerLabel) {
        html += '<div class="donut-chart-center">';
        if (centerValue) {
            html += `<span class="donut-chart-value">${centerValue}</span>`;
        }
        if (centerLabel) {
            html += `<span class="donut-chart-label">${centerLabel}</span>`;
        }
        html += '</div>';
    }
    
    html += '</div>';
    
    // Legend
    if (showLegend) {
        html += '<div class="pie-legend">';
        data.forEach((item, index) => {
            const color = item.color || getChartColor(index);
            const percentage = ((item.value / total) * 100).toFixed(1);
            html += `
                <div class="legend-item">
                    <span class="legend-color" style="background-color: ${color}"></span>
                    <span class="legend-label">${item.label}</span>
                    <span class="legend-value">${percentage}%</span>
                </div>
            `;
        });
        html += '</div>';
    }
    
    html += '</div>';
    
    container.innerHTML = html;
    
    // Add hover effects
    addChartHoverEffects(container);
}

/**
 * Render status breakdown with counts (like reference images)
 * @param {string} containerId - Container element ID
 * @param {Array} statuses - Array of {label, count, status, expandable} objects
 */
function renderStatusBreakdown(containerId, statuses) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    let html = '<div class="status-breakdown">';
    
    statuses.forEach(status => {
        html += `
            <div class="status-item" data-status="${status.status}">
                <span class="status-dot status-${status.status}"></span>
                <span class="status-label">${status.label}</span>
                <span class="status-count">${status.count}</span>
                ${status.expandable ? '<button class="status-toggle">▼</button>' : ''}
            </div>
        `;
    });
    
    html += '</div>';
    
    container.innerHTML = html;
    
    // Add toggle functionality
    container.querySelectorAll('.status-toggle').forEach(btn => {
        btn.addEventListener('click', function() {
            this.classList.toggle('expanded');
            // Could expand to show detailed list
        });
    });
}

/**
 * Render enhanced bar chart with better styling
 * @param {string} containerId - Container element ID
 * @param {Array} data - Array of {label, value, color} objects
 */
function renderEnhancedBarChart(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const maxValue = Math.max(...data.map(d => d.value));
    
    let html = '<div class="bar-chart">';
    data.forEach((item, index) => {
        const percentage = (item.value / maxValue) * 100;
        const color = item.color || getChartColor(index);
        
        html += `
            <div class="bar-item">
                <div class="bar-label">${item.label}</div>
                <div class="bar-container">
                    <div class="bar-fill" style="width: ${percentage}%; background-color: ${color}"></div>
                    <span class="bar-value">${formatCurrency(item.value)}</span>
                </div>
            </div>
        `;
    });
    html += '</div>';
    
    container.innerHTML = html;
}

/**
 * Render metric card with trend indicator
 * @param {string} containerId - Container element ID
 * @param {Object} metric - {value, label, trend, trendValue, icon}
 */
function renderMetricCard(containerId, metric) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const trendClass = metric.trend > 0 ? 'trend-up' : metric.trend < 0 ? 'trend-down' : 'trend-neutral';
    const trendIcon = metric.trend > 0 ? '↑' : metric.trend < 0 ? '↓' : '→';
    
    let html = `
        <div class="card stat-card-enhanced hover-lift">
            ${metric.icon ? `<div class="stat-icon">${metric.icon}</div>` : ''}
            <div class="stat-value">${metric.value}</div>
            ${metric.trend !== undefined ? `
                <div class="stat-trend ${trendClass}">
                    <span class="trend-icon">${trendIcon}</span>
                    <span class="trend-value">${metric.trendValue || Math.abs(metric.trend) + '%'}</span>
                </div>
            ` : ''}
            <div class="stat-label">${metric.label}</div>
        </div>
    `;
    
    container.innerHTML = html;
}

/**
 * Render enhanced progress circle with SVG
 * @param {string} containerId - Container element ID
 * @param {number} percentage - Progress percentage (0-100)
 * @param {Object} options - {size, strokeWidth, color}
 */
function renderEnhancedProgressCircle(containerId, percentage, options = {}) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const {
        size = 140,
        strokeWidth = 12,
        color = 'var(--color-primary)'
    } = options;
    
    const radius = (size - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const offset = circumference - (percentage / 100) * circumference;
    
    let html = `
        <div class="progress-circle-enhanced">
            <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
                <circle
                    class="progress-circle-bg"
                    cx="${size / 2}"
                    cy="${size / 2}"
                    r="${radius}"
                    stroke-width="${strokeWidth}"
                />
                <circle
                    class="progress-circle-fill"
                    cx="${size / 2}"
                    cy="${size / 2}"
                    r="${radius}"
                    stroke="${color}"
                    stroke-width="${strokeWidth}"
                    stroke-dasharray="${circumference}"
                    stroke-dashoffset="${offset}"
                />
            </svg>
            <span class="progress-value">${Math.round(percentage)}%</span>
        </div>
    `;
    
    container.innerHTML = html;
}

/**
 * Render metric comparison bars (like Arcadia dashboard)
 * @param {string} containerId - Container element ID
 * @param {Array} comparisons - Array of {label, current, previous, unit} objects
 */
function renderMetricComparisons(containerId, comparisons) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    let html = '<div class="metric-comparisons">';
    
    comparisons.forEach(comp => {
        const maxValue = Math.max(comp.current, comp.previous);
        const currentPercentage = (comp.current / maxValue) * 100;
        const previousPercentage = (comp.previous / maxValue) * 100;
        
        html += `
            <div class="metric-comparison">
                <div class="metric-comparison-label">${comp.label}</div>
                <div class="metric-comparison-values">
                    <div class="metric-comparison-value">
                        <div class="metric-comparison-year">2024</div>
                        <div class="metric-comparison-amount">${formatValue(comp.current, comp.unit)}</div>
                    </div>
                    <div class="metric-comparison-bar">
                        <div class="metric-comparison-bar-fill" style="width: ${currentPercentage}%"></div>
                    </div>
                    <div class="metric-comparison-value">
                        <div class="metric-comparison-year">2023</div>
                        <div class="metric-comparison-amount">${formatValue(comp.previous, comp.unit)}</div>
                    </div>
                    <div class="metric-comparison-bar">
                        <div class="metric-comparison-bar-fill" style="width: ${previousPercentage}%; background-color: var(--color-warning)"></div>
                    </div>
                </div>
            </div>
        `;
    });
    
    html += '</div>';
    
    container.innerHTML = html;
}

/**
 * Add hover effects to charts
 */
function addChartHoverEffects(container) {
    const segments = container.querySelectorAll('.donut-segment, .bar-fill');
    
    segments.forEach(segment => {
        segment.addEventListener('mouseenter', function() {
            this.style.opacity = '0.8';
            this.style.cursor = 'pointer';
            
            // Could show tooltip here
            const label = this.dataset.label;
            const value = this.dataset.value;
            const percentage = this.dataset.percentage;
            
            if (label && value) {
                showChartTooltip(this, `${label}: ${value} (${percentage}%)`);
            }
        });
        
        segment.addEventListener('mouseleave', function() {
            this.style.opacity = '1';
            hideChartTooltip();
        });
    });
}

/**
 * Show chart tooltip
 */
function showChartTooltip(element, text) {
    let tooltip = document.getElementById('chartTooltip');
    
    if (!tooltip) {
        tooltip = document.createElement('div');
        tooltip.id = 'chartTooltip';
        tooltip.className = 'chart-tooltip';
        document.body.appendChild(tooltip);
    }
    
    tooltip.textContent = text;
    tooltip.classList.add('visible');
    
    const rect = element.getBoundingClientRect();
    tooltip.style.left = rect.left + rect.width / 2 - tooltip.offsetWidth / 2 + 'px';
    tooltip.style.top = rect.top - tooltip.offsetHeight - 8 + 'px';
}

/**
 * Hide chart tooltip
 */
function hideChartTooltip() {
    const tooltip = document.getElementById('chartTooltip');
    if (tooltip) {
        tooltip.classList.remove('visible');
    }
}

/**
 * Get chart color by index
 */
function getChartColor(index) {
    const colors = [
        '#2563eb', // Blue
        '#10b981', // Green
        '#f59e0b', // Orange
        '#ef4444', // Red
        '#8b5cf6', // Purple
        '#06b6d4', // Cyan
        '#ec4899', // Pink
        '#84cc16'  // Lime
    ];
    return colors[index % colors.length];
}

/**
 * Format value with unit
 */
function formatValue(value, unit) {
    if (unit === 'currency') {
        return formatCurrency(value);
    } else if (unit === 'percentage') {
        return value.toFixed(1) + '%';
    } else if (unit === 'number') {
        return value.toLocaleString();
    }
    return value;
}

/**
 * Create loading skeleton for charts
 */
function showChartSkeleton(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.innerHTML = `
        <div class="skeleton skeleton-card"></div>
    `;
}

/**
 * Animate chart on load
 */
function animateChart(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.classList.add('fade-in');
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        renderDonutChart,
        renderStatusBreakdown,
        renderEnhancedBarChart,
        renderMetricCard,
        renderEnhancedProgressCircle,
        renderMetricComparisons,
        showChartSkeleton,
        animateChart
    };
}
