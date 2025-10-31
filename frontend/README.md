# R&D Tax Credit Automation - Frontend

HTML+CSS frontend for the R&D Tax Credit Automation Agent MVP dashboard.

## 🎨 NEW: Professional Design System

**Status**: Reports page redesigned with modern dashboard aesthetic!

- ✅ **Reports Page** - Fully redesigned with donut charts, info cards, and data tables
- 🔄 **Dashboard Page** - To be updated with new design system
- 🔄 **Workflow Page** - To be updated with new design system  
- 🔄 **Onboarding Page** - To be updated with new design system

**Documentation:**
- `DESIGN_SYSTEM.md` - Complete design system specification
- `DESIGN_IMPLEMENTATION_GUIDE.md` - Quick reference for developers
- `REPORTS_REDESIGN.md` - Detailed redesign documentation

**Key Features:**
- Donut charts with centered metrics
- Clean table layouts instead of card grids
- Info cards with icon + metric layout
- Soft color palette (blues, greens, purples)
- Consistent spacing and typography
- Smooth transitions and hover effects

## Project Structure

```
frontend/
├── index.html              # Main dashboard page
├── onboarding.html         # Onboarding wizard
├── workflow.html           # Agent workflow visualization
├── reports.html            # Reports showcase
├── css/
│   ├── variables.css       # CSS custom properties (design tokens)
│   ├── reset.css           # CSS reset/normalize
│   ├── utilities.css       # Utility classes
│   ├── components.css      # Reusable component styles
│   ├── dashboard.css       # Dashboard page styles
│   ├── onboarding.css      # Onboarding page styles
│   ├── workflow.css        # Workflow page styles
│   └── reports.css         # Reports page styles
├── js/
│   ├── utils.js            # Utility functions
│   ├── charts.js           # Chart rendering
│   ├── dashboard.js        # Dashboard page logic
│   ├── onboarding.js       # Onboarding flow logic
│   ├── workflow.js         # Workflow simulation logic
│   └── reports.js          # Reports page logic
├── assets/
│   ├── icons/              # Icon files (SVG, PNG)
│   ├── images/             # Image files
│   └── fonts/              # Custom fonts (if needed)
├── data/
│   └── sample-integration-data.json  # Sample data fixtures
└── README.md               # This file
```

## Features

### 1. Dashboard (index.html)
- Integration status cards (Clockify, BambooHR, Unified.to)
- Engagement summary with key metrics
- Compliance health tracking
- Team information table
- Interactive charts

### 2. Onboarding (onboarding.html)
- 6-step wizard flow
- Platform selection (HR/Payroll and Time Tracking)
- Simulated OAuth authentication
- Configuration review
- Skip to demo option

### 3. Workflow Visualization (workflow.html)
- Real-time pipeline visualization
- 6-stage workflow simulation
- Progress tracking
- Workflow log
- Playback speed controls
- Stage details panel

### 4. Reports (reports.html)
- Report grid display
- Filter functionality
- Report preview modal
- Download functionality
- Statistics dashboard

## CSS Architecture

### Design System
The CSS architecture follows a modern, scalable approach:

1. **Variables (variables.css)**: Centralized design tokens
   - Color palette
   - Typography scale
   - Spacing scale
   - Border radius
   - Shadows
   - Transitions

2. **Reset (reset.css)**: Consistent baseline across browsers
   - Box-sizing
   - Margin/padding reset
   - Focus styles
   - Accessibility considerations

3. **Utilities (utilities.css)**: Atomic utility classes
   - Layout (flexbox, grid)
   - Spacing (margin, padding)
   - Typography
   - Colors
   - Display

4. **Components (components.css)**: Reusable UI components
   - Buttons
   - Cards
   - Forms
   - Tables
   - Navigation
   - Modals
   - Status badges

5. **Page-specific styles**: Custom styles for each page
   - dashboard.css
   - onboarding.css
   - workflow.css
   - reports.css

## JavaScript Architecture

### Modular Structure
Each page has its own JavaScript file with:
- Initialization function
- Event listeners
- Data loading
- UI updates

### Shared Utilities (utils.js)
- Formatting functions (currency, date, file size)
- Local storage helpers
- Debounce/throttle
- Common helpers

### Chart Rendering (charts.js)
- Simple HTML/CSS-based charts
- No external dependencies
- Bar charts
- Pie charts
- Line charts

## Getting Started

### Prerequisites
- Modern web browser (Chrome, Firefox, Safari, Edge)
- No build tools required
- No dependencies to install

### Running Locally

1. Open any HTML file directly in your browser:
   ```
   file:///path/to/frontend/index.html
   ```

2. Or use a simple HTTP server:
   ```bash
   # Python 3
   python -m http.server 8000
   
   # Node.js (http-server)
   npx http-server
   ```

3. Navigate to:
   ```
   http://localhost:8000/index.html
   ```

## Usage

### First-Time Users
1. Open `onboarding.html`
2. Complete the 6-step wizard or click "Skip for Demo"
3. You'll be redirected to the dashboard

### Dashboard
- View integration status
- Monitor compliance health
- Review team information
- Generate new reports

### Workflow
- Click "Start Workflow" to simulate the pipeline
- Watch real-time progress through 6 stages
- Click stages for detailed information
- Adjust playback speed (1x, 2x, 5x)

### Reports
- View generated reports
- Filter by tax year, status, or company
- Click reports to preview
- Download reports

## Data Storage

The application uses browser localStorage for:
- Onboarding data
- User preferences
- Session state

No backend connection required for MVP demonstration.

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Responsive Design

The application is responsive and works on:
- Desktop (1280px+)
- Tablet (768px - 1279px)
- Mobile (< 768px)

## Customization

### Colors
Edit `css/variables.css` to change the color scheme:
```css
:root {
    --color-primary: #2563eb;
    --color-success: #10b981;
    /* ... */
}
```

### Typography
Modify font settings in `css/variables.css`:
```css
:root {
    --font-family-base: -apple-system, BlinkMacSystemFont, 'Segoe UI', ...;
    --font-size-base: 1rem;
    /* ... */
}
```

### Spacing
Adjust spacing scale in `css/variables.css`:
```css
:root {
    --spacing-4: 1rem;
    --spacing-6: 1.5rem;
    /* ... */
}
```

## Performance

- No external dependencies
- Minimal JavaScript
- CSS-based animations
- Optimized for fast loading

## Accessibility

- Semantic HTML
- ARIA labels where needed
- Keyboard navigation support
- Focus indicators
- Color contrast compliance

## Future Enhancements

- Connect to backend API
- Real-time WebSocket updates
- Advanced chart library integration
- PDF preview in browser
- Export functionality
- Dark mode support

## License

Part of the R&D Tax Credit Automation Agent project.
