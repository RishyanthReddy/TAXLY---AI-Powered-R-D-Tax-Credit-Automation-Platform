# R&D Tax Credit Automation - Frontend

## Quick Start

```bash
# 1. Start backend
cd rd_tax_agent
python main.py

# 2. Open frontend
open frontend/home.html
```

## Pages

- **home.html** - Landing page with navigation
- **index.html** - Dashboard with real-time metrics
- **workflow.html** - Pipeline visualization with WebSocket updates
- **reports.html** - Download PDF reports
- **onboarding.html** - First-time setup wizard

## Enhanced Design System

All pages use consistent styling with:
- Donut charts with center values
- Status breakdown lists with colored dots
- Metric cards with trend indicators
- Enhanced progress circles (SVG)
- Professional data tables
- Filter dropdowns

## Project Structure

```
frontend/
├── *.html                      # Pages
├── css/
│   ├── variables.css           # Design tokens
│   ├── dashboard-enhanced.css  # Enhanced components
│   └── *.css                   # Page-specific styles
├── js/
│   ├── charts-enhanced.js      # Enhanced chart functions
│   ├── api.js                  # Backend integration
│   ├── websocket.js            # Real-time updates
│   └── *.js                    # Page-specific logic
└── data/
    └── sample-integration-data.json
```

## Component Examples

**Donut Chart:**
```javascript
renderDonutChart('chartId', data, {
    centerValue: '10',
    centerLabel: 'Total'
});
```

**Metric Card:**
```javascript
renderMetricCard('metricId', {
    value: '$4,608',
    label: 'Credits',
    trend: 20,
    icon: '💰'
});
```

See `dashboard-enhanced-example.html` for more examples.

## Technology Stack

- HTML5 + CSS3 (Grid, Flexbox, Custom Properties)
- Vanilla JavaScript ES6+
- WebSocket for real-time updates
- FastAPI backend integration

## Tasks Completed

- ✅ Task 132: Frontend structure
- ✅ Task 133: Load existing reports
- ✅ Task 134: Generate reports
- ✅ Task 135: WebSocket integration
- ✅ Task 136: Run pipeline button
- ✅ Task 137: Real backend data + enhanced design
