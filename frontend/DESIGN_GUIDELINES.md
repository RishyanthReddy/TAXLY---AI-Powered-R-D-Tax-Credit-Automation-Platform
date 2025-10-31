# Frontend Design Guidelines

## Quick Reference for All Future Pages

### CSS Stack (Required Order)
```html
<link rel="stylesheet" href="css/variables.css">
<link rel="stylesheet" href="css/reset.css">
<link rel="stylesheet" href="css/utilities.css">
<link rel="stylesheet" href="css/components.css">
<link rel="stylesheet" href="css/dashboard-enhanced.css">
<link rel="stylesheet" href="css/your-page.css">
```

### Design Tokens (Use These)
**Colors:**
- Primary: `#2563eb`
- Success: `#10b981`
- Warning: `#f59e0b`
- Error: `#ef4444`

**Typography:**
- Page titles: 30px, bold
- Section titles: 24px, semibold
- Body text: 14px, regular

**Spacing:**
- Card padding: 24px
- Section margins: 32px
- Element gaps: 12px

### Navigation Bar (Required on All Pages)
```html
<nav class="navbar">
    <div class="container">
        <div class="navbar-brand">
            <span class="brand-name">🚀 R&D Tax Credit Automation</span>
        </div>
        <ul class="navbar-menu">
            <li><a href="home.html">Home</a></li>
            <li><a href="index.html">Dashboard</a></li>
            <li><a href="workflow.html">Workflow</a></li>
            <li><a href="reports.html">Reports</a></li>
            <!-- Add your new page here -->
        </ul>
    </div>
</nav>
```

### Enhanced Components (Reuse These)
- **Donut Charts:** `renderDonutChart(id, data, options)`
- **Metric Cards:** `renderMetricCard(id, metric)`
- **Progress Circles:** `renderEnhancedProgressCircle(id, percentage, options)`
- **Tables:** Use `.data-table-enhanced` class
- **Dropdowns:** Use `.filter-dropdown` class

### Integration Checklist
- [ ] Uses standard CSS stack
- [ ] Includes navbar with all pages
- [ ] Uses design tokens from variables.css
- [ ] Reuses enhanced components
- [ ] Added to home.html navigation
- [ ] Updated navbar on all existing pages

### Examples
See `dashboard-enhanced-example.html` for component usage examples.
