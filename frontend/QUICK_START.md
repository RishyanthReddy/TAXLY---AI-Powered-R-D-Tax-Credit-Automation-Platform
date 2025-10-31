# Quick Start

## Run the Frontend

```bash
# 1. Start backend
cd rd_tax_agent
python main.py

# 2. Open frontend
open frontend/home.html
```

## Pages

- **home.html** - Landing page with navigation
- **index.html** - Dashboard with metrics
- **workflow.html** - Run pipeline
- **reports.html** - Download reports
- **onboarding.html** - First-time setup

## Enhanced Components

All pages use the enhanced design system with:
- Donut charts with center values
- Status breakdown lists
- Metric cards with trends
- Enhanced progress circles
- Professional data tables

See `dashboard-enhanced-example.html` for component examples.

## Files

**CSS:**
- `css/dashboard-enhanced.css` - Enhanced components
- `css/variables.css` - Design tokens

**JavaScript:**
- `js/charts-enhanced.js` - Enhanced chart functions
- `js/api.js` - Backend integration
- `js/websocket.js` - Real-time updates
