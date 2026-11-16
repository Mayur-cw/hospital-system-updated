# DESIGN SYSTEM & ROLE-NATIVE UX SPECIFICATION
**System Name:** Hospital OS "Clinical Precision" System  
**Evaluation:** Formally evaluated three design concepts (Clinical Precision, Operations Command, Quiet Hospitality) against clinical legibility, error reduction, and operational throughput.

---

## 1. Visual Directions Evaluation & Selection

### Concept A: Clinical Precision (SELECTED)
- **Palette:** Deep Navy (`#0A192F`), Crisp White Canvas (`#FFFFFF`), Muted Sea Glass / Teal (`#0D9488`), Slate Gray Borders (`#E2E8F0`), Subtle Charcoal Text (`#0F172A`).
- **Typography:** DM Sans & Inter (high-legibility grotesque sans-serif with tabular numeric figures for dosages, prices, and timestamps).
- **Rationale for Selection:** Provides the highest legibility under fluorescent hospital lighting, fast visual scanning of critical patient alerts (allergies, pending Rx), and high aesthetic trust without distractingly dark themes or frivolous neon gradients.

### Concept B: Operations Command (Evaluated)
- High-contrast charcoal/black terminal layout with glowing status chips.
- *Tradeoff:* High fatigue for clinicians during long 12-hour shifts; harsh for elderly patients in portal views.

### Concept C: Quiet Hospitality (Evaluated)
- Soft warm beige/cream tones, rounded cards, generous whitespace.
- *Tradeoff:* Insufficient information density for busy reception and cashier desks where 50+ queue rows must be reviewed quickly.

---

## 2. Token & Component Foundations

### 2.1 Color Tokens
```css
:root {
  /* Brand Foundations */
  --hos-navy-900: #0a192f;
  --hos-navy-800: #112240;
  --hos-navy-700: #1e3a5f;
  
  /* Primary Clinical Accents */
  --hos-teal-600: #0d9488;
  --hos-teal-500: #14b8a6;
  --hos-teal-50:  #f0fdfa;

  /* Semantic Alerts */
  --hos-danger-600: #dc2626;
  --hos-danger-50:  #fef2f2;
  --hos-warning-600: #d97706;
  --hos-warning-50:  #fffbeb;
  --hos-success-600: #16a34a;
  --hos-success-50:  #f0fdf4;
  --hos-info-600:    #2563eb;
  --hos-info-50:     #eff6ff;

  /* Neutral Surface & Borders */
  --hos-surface:     #f8fafc;
  --hos-card-bg:     #ffffff;
  --hos-border:      #e2e8f0;
  --hos-border-subtle: #f1f5f9;
  --hos-text-main:   #0f172a;
  --hos-text-muted:  #64748b;
  --hos-text-light:  #94a3b8;

  /* Geometry & Shadows */
  --hos-radius-sm: 6px;
  --hos-radius-md: 10px;
  --hos-radius-lg: 16px;
  --hos-radius-pill: 9999px;
  --hos-shadow-sm: 0 1px 3px rgba(15, 23, 42, 0.06);
  --hos-shadow-md: 0 4px 12px rgba(15, 23, 42, 0.08);
  --hos-shadow-lg: 0 10px 25px rgba(15, 23, 42, 0.12);
}
```

### 2.2 Typography Scale
- Headings: `Syne` / `Inter`, 600–800 weight.
- Body: `DM Sans`, 400 regular, 500 medium, 700 bold.
- Data Tables / Numbers: `font-variant-numeric: tabular-nums;` for aligning money, MRNs, bed numbers, and vitals.

---

## 3. Standard UI Component Library
1. **Persistent Patient Identity Strip**: Displays Patient Name, MRN, Age/Gender, Allergy Alert Banner, and Visit Status at the top of every clinical and billing screen.
2. **Dense Operational Data Tables**: Sticky table headers, subtle row hover, explicit status badges with icons + text (never color alone), and keyboard focus indicators.
3. **Structured Prescription Matrix**: Drug Name, Dose, Route, Frequency, Duration, Instructions, with an interactive "Add Drug" row.
4. **Bed Board Card Matrix**: Visual room cards showing bed status (Available in green, Occupied in navy, Cleaning in amber, Maintenance in gray).
5. **State Handling Standards**: Every Golden Screen provides explicit UI representations for:
   - `Loading` (subtle pulse skeleton)
   - `Empty` (helpful empty state illustration with call to action)
   - `Saved / Success` (durable toast notification)
   - `Permission Denied` (clear reason and safe back button)
   - `Demo Mock Warning` (visible amber tag on simulated features)
