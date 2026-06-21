## Design System: AI Hackathon Berkeley

### Pattern
- **Name:** Event/Conference Landing
- **Conversion Focus:** Early bird pricing with deadline. Social proof (past attendees). Speaker credibility. Multi-ticket discounts.
- **CTA Placement:** Register CTA sticky + After speakers + Bottom
- **Color Strategy:** Urgency colors (countdown). Event branding. Speaker cards professional. Sponsor logos neutral.
- **Sections:** 1. Hero (date/location/countdown), 2. Speakers grid, 3. Agenda/schedule, 4. Sponsors, 5. Register CTA

### Style
- **Name:** Vibrant & Block-based
- **Mode Support:** Light ✓ Full | Dark ✓ Full
- **Keywords:** Bold, energetic, playful, block layout, geometric shapes, high color contrast, duotone, modern, energetic
- **Best For:** Startups, creative agencies, gaming, social media, youth-focused, entertainment, consumer
- **Performance:** ⚡ Good | **Accessibility:** ◐ Ensure WCAG

### Colors
| Role | Hex | CSS Variable |
|------|-----|--------------|
| Primary | `#2563EB` | `--color-primary` |
| On Primary | `#FFFFFF` | `--color-on-primary` |
| Secondary | `#7C3AED` | `--color-secondary` |
| Accent/CTA | `#EC4899` | `--color-accent` |
| Background | `#FFFFFF` | `--color-background` |
| Foreground | `#0F172A` | `--color-foreground` |
| Muted | `#F1F5FD` | `--color-muted` |
| Border | `#E4ECFC` | `--color-border` |
| Destructive | `#DC2626` | `--color-destructive` |
| Ring | `#2563EB` | `--color-ring` |

*Notes: Brand blue + creator purple*

### Typography
- **Heading:** Crimson Pro
- **Body:** Atkinson Hyperlegible
- **Mood:** academic, research, scholarly, accessible, readable, educational
- **Best For:** Universities, research papers, academic journals, educational
- **Google Fonts:** https://fonts.google.com/share?selection.family=Atkinson+Hyperlegible:wght@400;700|Crimson+Pro:wght@400;500;600;700
- **CSS Import:**
```css
@import url('https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:wght@400;700&family=Crimson+Pro:wght@400;500;600;700&display=swap');
```

### Key Effects
Large sections (48px+ gaps), animated patterns, bold hover (color shift), scroll-snap, large type (32px+), 200-300ms

### Avoid (Anti-patterns)
- Confusing registration
- No countdown

### Pre-Delivery Checklist
- [ ] No emojis as icons (use SVG: Heroicons/Lucide)
- [ ] cursor-pointer on all clickable elements
- [ ] Hover states with smooth transitions (150-300ms)
- [ ] Light mode: text contrast 4.5:1 minimum
- [ ] Focus states visible for keyboard nav
- [ ] prefers-reduced-motion respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px