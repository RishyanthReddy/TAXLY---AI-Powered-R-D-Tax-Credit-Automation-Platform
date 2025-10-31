/**
 * Chart Rendering Functions
 * Simple chart rendering using HTML/CSS (no external libraries)
 */

// Render bar chart
function renderBarChart(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const maxValue = Math.max(...data.map(d => d.value));
    
    let html = '<div class="bar-chart">';
    data.forEach(item => {
        const percentage = (item.value / maxValue) * 100;
        html += `
            <div class="bar-item">
                <div class="bar-label">${item.label}</div>
                <div class="bar-container">
                    <div class="bar-fill" style="width: ${percentage}%"></div>
                    <span class="bar-value">${formatCurrency(item.value)}</span>
                </div>
            </div>
        `;
    });
    html += '</div>';
    
    container.innerHTML = html;
}

// Render pie chart
function renderPieChart(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const total = data.reduce((sum, item) => sum + item.value, 0);
    let currentAngle = 0;
    
    let html = '<div class="pie-chart">';
    html += '<svg viewBox="0 0 200 200" width="200" height="200">';
    
    data.forEach((item, index) => {
        const percentage = (item.value / total) * 100;
        const angle = (item.value / total) * 360;
        const endAngle = currentAngle + angle;
        
        const x1 = 100 + 90 * Math.cos((currentAngle - 90) * Math.PI / 180);
        const y1 = 100 + 90 * Math.sin((currentAngle - 90) * Math.PI / 180);
        const x2 = 100 + 90 * Math.cos((endAngle - 90) * Math.PI / 180);
        const y2 = 100 + 90 * Math.sin((endAngle - 90) * Math.PI / 180);
        
        const largeArc = angle > 180 ? 1 : 0;
        
        const colors = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
        const color = colors[index % colors.length];
        
        html += `
            <path d="M 100 100 L ${x1} ${y1} A 90 90 0 ${largeArc} 1 ${x2} ${y2} Z"
                  fill="${color}" opacity="0.8" />
        `;
        
        currentAngle = endAngle;
    });
    
    html += '</svg>';
    html += '<div class="pie-legend">';
    data.forEach((item, index) => {
        const colors = ['#2563eb', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];
        const color = colors[index % colors.length];
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
    html += '</div>';
    
    container.innerHTML = html;
}

// Render line chart
function renderLineChart(containerId, data) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const maxValue = Math.max(...data.map(d => d.value));
    const points = data.map((item, index) => {
        const x = (index / (data.length - 1)) * 300;
        const y = 150 - ((item.value / maxValue) * 120);
        return `${x},${y}`;
    }).join(' ');
    
    let html = '<div class="line-chart">';
    html += '<svg viewBox="0 0 300 150" width="100%" height="150">';
    html += `<polyline points="${points}" fill="none" stroke="#2563eb" stroke-width="2" />`;
    
    data.forEach((item, index) => {
        const x = (index / (data.length - 1)) * 300;
        const y = 150 - ((item.value / maxValue) * 120);
        html += `<circle cx="${x}" cy="${y}" r="4" fill="#2563eb" />`;
    });
    
    html += '</svg>';
    html += '</div>';
    
    container.innerHTML = html;
}

// Add chart styles dynamically
const chartStyles = `
<style>
.bar-chart {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-3);
}

.bar-item {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-1);
}

.bar-label {
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
}

.bar-container {
    position: relative;
    height: 32px;
    background-color: var(--bg-tertiary);
    border-radius: var(--radius-base);
    overflow: hidden;
}

.bar-fill {
    height: 100%;
    background-color: var(--color-primary);
    transition: width var(--transition-slow);
}

.bar-value {
    position: absolute;
    right: var(--spacing-2);
    top: 50%;
    transform: translateY(-50%);
    font-size: var(--font-size-sm);
    font-weight: var(--font-weight-medium);
    color: var(--text-primary);
}

.pie-chart {
    display: flex;
    align-items: center;
    gap: var(--spacing-6);
}

.pie-legend {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: var(--spacing-2);
}

.legend-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-2);
    font-size: var(--font-size-sm);
}

.legend-color {
    width: 12px;
    height: 12px;
    border-radius: 2px;
}

.legend-label {
    flex: 1;
    color: var(--text-secondary);
}

.legend-value {
    font-weight: var(--font-weight-medium);
    color: var(--text-primary);
}

.line-chart {
    width: 100%;
}
</style>
`;

// Inject styles
if (typeof document !== 'undefined') {
    document.head.insertAdjacentHTML('beforeend', chartStyles);
}
