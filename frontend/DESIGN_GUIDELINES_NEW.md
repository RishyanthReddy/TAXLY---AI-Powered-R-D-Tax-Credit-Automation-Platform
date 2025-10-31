# Frontend Design Guidelines - Reference-Based Design

## Overview
This design system is based on the provided reference dashboard image, featuring a clean, modern, and professional aesthetic suitable for enterprise tax credit automation software.

## Design Principles

### 1. Clean & Minimal
- Light, airy backgrounds (#fafafa)
- Generous white space
- Subtle borders and shadows
- No heavy gradients or decorative elements

### 2. Professional & Trustworthy
- Neutral color palette with strategic color accents
- Clear typography hierarchy
- Consistent spacing and alignment
- Data-focused presentation

### 3. Scannable & Organized
- Clear visual grouping with cards
- Consistent grid layouts
- Logical information hierarchy
- Easy-to-read tables and lists

## Color Palette

### Primary Colors
```css
--color-primary: #6366f1;        /* Indigo - primary actions, progress indicators */
--color-secondary: #8b5cf6;      /* Purple - secondary elements */
```

### Status Colors
```css
--color-success: #10b981;        /* Green - complete, approved, healthy */
--color-warning: #f59e0b;        /* Orange - ready for review, due soon */
--color-info: #38bdf8;           /* Light Blue - sent, informational */
--color-error: #ef4444;          /* Red - overdue, errors */
```

### Neutral Colors
```css
--bg-primary: #fafafa;           /* Page background */
--bg-secondary: #ffffff;         /* Card backgrounds */
--text-primary: #171717;         /* Headings, primary text */
--text-secondary: #525252;       /* Body text, labels */
--border-color: #e5e7eb;         /* Borders, dividers */
```

## Typography

### Font Family
- System fonts: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif
- Clean, readable, native to each platform

### Font Sizes
```css
--font-size-xs: 0.75rem;    /* 12px - badges, small labels */
--font-size-sm: 0.875rem;   /* 14px - body text, table content */
--font-size-base: 1rem;     /* 16px - default text */
--font-size-lg: 1.125rem;   /* 18px - section titles */
--font-size-2xl: 1.5rem;    /* 24px - page titles */
--font-size-3xl: 1.875rem;  /* 30px - large numbers in charts */
```

### Font Weights
```css
--font-weight-normal: 400;   /* Body text */
--font-weight-medium: 500;   /* Labels, emphasis */
--font-weight-semibold: 600; /* Headings, titles */
```

## Layout

### Grid System
- Use CSS Grid for card layouts
- Responsive: `grid-template-columns: repeat(auto-fit, minmax(320px, 1fr))`
- Consistent gap: `var(--spacing-6)` (24px)

### Spacing Scale
```css
--spacing-2: 0.5rem;    /* 8px - tight spacing */
--spacing-3: 0.75rem;   /* 12px - small gaps */
--spacing-4: 1rem;      /* 16px - default spacing */
--spacing-5: 1.25rem;   /* 20px - card padding */
--spacing-6: 1.5rem;    /* 24px - section gaps */
--spacing-8: 2rem;      /* 32px - large sections */
```

### Container
- Max-width: 1280px
- Centered with auto margins
- Padding: 32px on desktop, 16px on mobile

## Components

### Cards
```css
background-color: #ffffff;
border: 1px solid #e5e7eb;
border-radius: 12px;
padding: 24px;
box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
```

### Donut Charts
- SVG-based for crisp rendering
- Stroke width: 20px
- Radius: 50px
- Center value: large, bold number
- Legend: aligned to the right with color dots

### Status Badges
```css
display: inline-flex;
padding: 4px 12px;
font-size: 12px;
font-weight: 500;
border-radius: 9999px;
background-color: rgba(color, 0.1);
color: darker-shade;
```

### Tables
- White background cards
- Light gray header background (#fafafa)
- Subtle row borders (#e5e7eb)
- Hover state: light gray background
- Padding: 16px vertical, 24px horizontal

### Buttons
- Primary: Indigo background, white text
- Secondary: White background, gray border
- Icon buttons: 32x32px, transparent, hover gray
- Border radius: 8-10px
- Padding: 8px 16px

## Donut Chart Implementation

### Structure
```html
<div class="donut-chart-container">
    <svg class="donut-chart" viewBox="0 0 120 120">
        <!-- Background circle -->
        <circle cx="60" cy="60" r="50" fill="none" stroke="#e5e7eb" stroke-width="20"></circle>
        <!-- Data segments -->
        <circle cx="60" cy="60" r="50" fill="none" stroke="color" stroke-width="20" 
                stroke-dasharray="segment total" stroke-dashoffset="offset"></circle>
    </svg>
    <div class="donut-chart-center">
        <div class="donut-chart-value">5</div>
    </div>
</div>
```

### Calculations
- Circumference = 2 × π × radius = 2 × 3.14159 × 50 = 314.159
- Segment length = (value / total) × circumference
- Offset = previous segments' total length

## Status Legend

### Structure
```html
<div class="status-legend">
    <div class="status-legend-item">
        <div class="status-legend-label">
            <span class="status-legend-dot color-complete"></span>
            <span>Complete</span>
        </div>
        <div class="status-legend-value">
            <span>1</span>
            <span class="status-legend-toggle">▼</span>
        </div>
    </div>
</div>
```

### Color Dots
- Size: 12px × 12px
- Border-radius: 50%
- Colors match chart segments

## Data Table

### Best Practices
- Left-align text columns
- Right-align number columns
- Use monospace for numbers if needed
- Sortable headers with ↕ indicator
- Action menu (⋮) in last column
- Hover state for rows

### Staff List Display
- Circular avatars with initials
- Overlap avatars: `margin-left: -8px`
- Show "+N" for additional staff
- Border around avatars for separation

## Responsive Design

### Breakpoints
```css
/* Mobile */
@media (max-width: 768px) {
    - Single column grid
    - Stack header elements
    - Horizontal scroll for tables
}
```

### Mobile Considerations
- Touch-friendly targets (min 44px)
- Simplified navigation
- Collapsible sections
- Readable font sizes (min 14px)

## Accessibility

### Color Contrast
- Text on white: minimum 4.5:1 ratio
- Status badges: sufficient contrast
- Focus indicators: visible outlines

### Semantic HTML
- Proper heading hierarchy (h1 → h2 → h3)
- Table headers with `<th>`
- Button elements for actions
- ARIA labels where needed

### Keyboard Navigation
- Tab order follows visual flow
- Focus visible on all interactive elements
- Escape to close modals/dropdowns
- Enter/Space to activate buttons

## Icons

### Style
- Simple, line-based icons
- Emoji for quick implementation: 📅 📋 💬 🔍 🔽 👥 ⋮
- Or use icon library: Heroicons, Lucide, Feather

### Usage
- 16px for inline icons
- 20px for card headers
- 24px for prominent actions
- Consistent stroke width

## Animation & Transitions

### Timing
```css
--transition-fast: 150ms ease-in-out;   /* Hover states */
--transition-base: 200ms ease-in-out;   /* Default */
--transition-slow: 300ms ease-in-out;   /* Complex animations */
```

### What to Animate
- Hover states: background, color, transform
- Dropdowns: opacity, transform
- Modals: opacity, scale
- Loading states: spinner rotation

### What NOT to Animate
- Layout shifts
- Text content changes
- Critical data updates

## File Structure

```
frontend/
├── css/
│   ├── variables.css          # Design tokens
│   ├── reset.css              # CSS reset
│   ├── utilities.css          # Utility classes
│   ├── dashboard-new.css      # Dashboard-specific styles
│   └── components.css         # Reusable components
├── js/
│   ├── utils.js               # Helper functions
│   ├── api.js                 # API calls
│   └── dashboard.js           # Dashboard logic
└── dashboard-new.html         # Dashboard page
```

## Implementation Checklist

### Phase 1: Foundation
- [x] Set up CSS variables
- [x] Create base layout structure
- [x] Implement card components
- [x] Build donut chart component

### Phase 2: Components
- [x] Status cards with charts
- [x] Deadline cards
- [x] Data table
- [x] Staff list display
- [x] Action buttons

### Phase 3: Interactivity
- [ ] Filter dropdown functionality
- [ ] Sortable table columns
- [ ] Expandable legend items
- [ ] Action menu dropdowns
- [ ] Search functionality

### Phase 4: Data Integration
- [ ] Connect to backend API
- [ ] Real-time data updates
- [ ] Loading states
- [ ] Error handling
- [ ] Empty states

### Phase 5: Polish
- [ ] Responsive testing
- [ ] Accessibility audit
- [ ] Performance optimization
- [ ] Cross-browser testing
- [ ] User testing

## Key Differences from Previous Design

### What Changed
1. **Color Palette**: Shifted from blue (#2563eb) to indigo (#6366f1)
2. **Background**: Changed from pure white to light gray (#fafafa)
3. **Cards**: More subtle shadows and borders
4. **Typography**: Slightly smaller, more refined sizes
5. **Spacing**: More generous, airier layout
6. **Charts**: Donut charts instead of bar/line charts
7. **Tables**: Cleaner, more minimal styling

### Why It's Better
- More professional and enterprise-ready
- Better visual hierarchy
- Easier to scan and digest information
- Matches modern SaaS dashboard standards
- Less "AI-generated" appearance
- More trustworthy for financial/tax software

## Resources

### Design Inspiration
- Linear (linear.app)
- Notion (notion.so)
- Stripe Dashboard (stripe.com)
- Vercel Dashboard (vercel.com)

### Tools
- Figma for mockups
- Chrome DevTools for debugging
- Lighthouse for performance
- axe DevTools for accessibility

### Further Reading
- [Refactoring UI](https://www.refactoringui.com/)
- [Material Design](https://material.io/design)
- [Apple Human Interface Guidelines](https://developer.apple.com/design/)

