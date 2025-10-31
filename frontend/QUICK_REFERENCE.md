# Frontend Quick Reference Card

## 🚀 Quick Start

```bash
# View pages locally
start rd_tax_agent/frontend/index.html

# Run with backend
cd rd_tax_agent
python main.py
# Then open: http://localhost:8000/frontend/index.html
```

## 📄 Pages

| Page | File | Purpose |
|------|------|---------|
| Dashboard | `index.html` | Status overview, metrics |
| Home | `home.html` | Landing page, features |
| Workflow | `workflow.html` | Pipeline visualization |
| Reports | `reports.html` | Report management |
| Onboarding | `onboarding.html` | Setup wizard |

## 🎨 Colors

```css
Primary:    #6366f1  /* Indigo */
Success:    #10b981  /* Green */
Warning:    #f59e0b  /* Orange */
Info:       #38bdf8  /* Cyan */
Background: #fafafa  /* Light gray */
Cards:      #ffffff  /* White */
Text:       #171717  /* Dark */
Border:     #e5e7eb  /* Light gray */
```

## 📏 Spacing

```css
2:  8px   /* Tight */
3:  12px  /* Small */
4:  16px  /* Default */
5:  20px  /* Card padding */
6:  24px  /* Section gaps */
8:  32px  /* Large sections */
```

## 🔤 Typography

```css
XS:   12px  /* Small labels */
SM:   14px  /* Body text */
Base: 16px  /* Default */
LG:   18px  /* Section titles */
2XL:  24px  /* Page titles */
3XL:  30px  /* Large numbers */
```

## 🧩 Components

### Card
```html
<div class="card">
    <h3 class="card-title">Title</h3>
    <div class="card-body">Content</div>
</div>
```

### Button
```html
<button class="btn btn-primary">Primary</button>
<button class="btn btn-secondary">Secondary</button>
```

### Status Badge
```html
<span class="status-badge status-healthy">Complete</span>
<span class="status-badge status-warning">Pending</span>
```

### Data Table
```html
<div class="data-table-container">
    <table class="data-table">
        <thead><tr><th>Column</th></tr></thead>
        <tbody><tr><td>Data</td></tr></tbody>
    </table>
</div>
```

## 📱 Breakpoints

```css
Desktop: >1024px  /* Full layout */
Tablet:  768-1024px  /* Adjusted columns */
Mobile:  <768px   /* Single column */
```

## 🔧 Customization

### Change Primary Color
```css
/* css/variables.css */
:root {
    --color-primary: #your-color;
}
```

### Adjust Spacing
```css
/* css/variables.css */
:root {
    --spacing-6: 2rem;  /* Increase gap */
}
```

### Modify Cards
```css
/* css/components.css */
.card {
    border-radius: 16px;  /* More rounded */
    padding: 32px;        /* More padding */
}
```

## 🔗 API Endpoints

```javascript
GET  /health                    // Health check
GET  /api/dashboard/stats       // Dashboard data
POST /api/pipeline/run          // Run pipeline
GET  /api/reports               // Get reports
GET  /api/reports/{id}/download // Download report
```

## 🌐 WebSocket

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    // Handle update
};
```

## 📚 Documentation

| File | Purpose |
|------|---------|
| `README_MASTER.md` | Master guide |
| `REDESIGN_COMPLETE.md` | Complete summary |
| `DESIGN_GUIDELINES_NEW.md` | Design system |
| `REDESIGN_README.md` | Quick start |
| `CLEANUP_GUIDE.md` | Cleanup instructions |

## 🧪 Testing

```bash
# Manual testing
1. Open each page
2. Test all features
3. Check on mobile
4. Test keyboard navigation

# Browser DevTools
F12 → Lighthouse → Run audit

# Target scores
Performance:    >90
Accessibility:  >95
Best Practices: >90
SEO:            >90
```

## 🐛 Troubleshooting

### Styles Not Applying
```bash
# Clear cache
Ctrl+Shift+Delete

# Check CSS order
1. variables.css
2. reset.css
3. utilities.css
4. components.css
5. page-specific.css
```

### Backend Not Connecting
```bash
# Check backend running
python main.py

# Test endpoint
curl http://localhost:8000/health

# Check CORS settings
```

## 📦 File Structure

```
frontend/
├── index.html              Dashboard
├── home.html               Home
├── workflow.html           Workflow
├── reports.html            Reports
├── onboarding.html         Onboarding
├── css/
│   ├── variables.css       Tokens
│   ├── components.css      Shared
│   ├── dashboard-new.css   Dashboard
│   ├── home-new.css        Home
│   ├── workflow-new.css    Workflow
│   ├── reports-new.css     Reports
│   └── onboarding-new.css  Onboarding
└── js/
    ├── api.js              API calls
    ├── dashboard.js        Dashboard
    ├── workflow.js         Workflow
    ├── reports.js          Reports
    └── onboarding.js       Onboarding
```

## ✅ Checklist

### Before Deployment
- [ ] Test all pages
- [ ] Check mobile responsive
- [ ] Run Lighthouse audit
- [ ] Test backend integration
- [ ] Verify PDF viewer
- [ ] Check WebSocket
- [ ] Test forms
- [ ] Verify navigation
- [ ] Check accessibility
- [ ] Test on multiple browsers

### After Deployment
- [ ] Monitor errors
- [ ] Check performance
- [ ] Get user feedback
- [ ] Track analytics
- [ ] Update documentation

## 🎯 Key Features

### Dashboard
- Status cards with donut charts
- Deadline tracking
- Engagement table
- Filter dropdown

### Workflow
- 6-stage pipeline
- Real-time progress
- WebSocket updates
- Stage details

### Reports
- Report statistics
- Filter panel
- PDF preview
- Download options

### Onboarding
- 6-step wizard
- Platform selection
- Authentication
- Review summary

## 💡 Tips

1. Start with Dashboard
2. Test on mobile
3. Use DevTools
4. Check accessibility
5. Optimize images
6. Cache assets
7. Monitor errors
8. Get feedback

## 🚀 Deploy

```bash
# Static hosting
- Netlify
- Vercel
- GitHub Pages

# With backend
# In main.py:
app.mount("/frontend", StaticFiles(directory="frontend"))
```

## 📞 Help

1. Check documentation
2. Review guidelines
3. Inspect examples
4. Use DevTools
5. Check logs

---

**Quick Reference v1.0**  
**Last Updated**: Now  
**Status**: Production Ready ✅

