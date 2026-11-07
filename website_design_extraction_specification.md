# WEBSITE DESIGN EXTRACTION SPECIFICATION

**Objective:** Extract the source website's brand identity, content and assets, and the reference website's complete design system, layout and visual properties. All findings must be measurable, structured and reusable by an AI redesign agent.

---

# 1. SOURCE WEBSITE — BRAND & CONTENT

**Purpose:** Preserve the website's identity and original content.

## 1.1 Brand Identity
- Brand name and description
- Primary, secondary and alternative logos
- Brand symbols and favicon
- Logo variations (light, dark, monochrome)
- Logo dimensions and aspect ratios
- Brand personality and positioning
- Tone of voice and visual language

## 1.2 Brand Colors
- Primary and secondary colors
- Accent colors
- Background and surface colors
- Heading and body text colors
- Button and link colors
- Border and divider colors
- Hover and active colors
- Gradients

Record HEX, RGB, RGBA, CSS variables and usage for each color.

## 1.3 Typography & Fonts
- Primary and secondary font families
- Heading and body fonts
- Navigation and button fonts
- Font file URLs and formats
- Available font weights and styles
- Variable font properties
- Fallback fonts
- Original font sizes, line heights and letter spacing

## 1.4 Content
- All H1–H6 headings
- Subheadings and paragraphs
- Lists and captions
- Buttons and CTA text
- Navigation and footer content
- Testimonials and statistics
- FAQs
- Product and service descriptions
- Blog and editorial content
- Legal and contact information

Preserve all original text exactly.

For each element, record its page, section, HTML tag, position and associated links.

## 1.5 Images & Assets
- Logos and icons
- Hero images
- Product and service images
- Background images
- Team photography
- Illustrations and SVGs
- Videos and animations
- Partner logos
- Decorative graphics

Record asset URL, filename, format, dimensions, aspect ratio, file size, alt text, page, section and usage.

## 1.6 Website Structure
- All accessible URLs
- Sitemap and page hierarchy
- Navigation structure
- Header and footer
- Breadcrumbs
- Internal links
- Page templates
- Section hierarchy and order
- Reusable components

## 1.7 Functionality
- Menus and dropdowns
- Forms and validation
- Search and filters
- Tabs and accordions
- Sliders and carousels
- Modals and popups
- Sticky elements
- Animations and hover interactions
- Booking and shopping functionality
- Third-party integrations

Record component behavior, triggers, states and destinations.

## 1.8 Technical Stack
- Frontend framework
- CMS
- CSS framework
- JavaScript framework
- CSS architecture
- External dependencies
- Font loading
- Image optimization
- SEO metadata
- Accessibility attributes

---

# 2. REFERENCE WEBSITE — DESIGN SYSTEM & LAYOUT

**Purpose:** Reproduce its visual structure, proportions and design patterns without transferring its brand identity or content.

## 2.1 Global Dimensions
- Website and viewport width
- Maximum container width
- Main content width
- Left and right margins
- Header and footer dimensions
- Global horizontal and vertical padding
- Main content offsets
- Full-width and boxed section dimensions
- Overflow behavior

## 2.2 Grid System
- Number of columns
- Column widths and proportions
- Column gaps
- Row gaps
- Grid container width
- Grid alignment and justification
- Grid-template-columns and rows
- Grid areas
- Flexbox direction and alignment
- Flexbox wrapping and gaps

## 2.3 Spacing & Whitespace
- Global page margins
- Section-to-section spacing
- Section padding (top, bottom, left, right)
- Element margins
- Heading-to-paragraph spacing
- Paragraph-to-paragraph spacing
- Text-to-button spacing
- Image-to-text spacing
- Card-to-card spacing
- Navigation spacing
- Footer spacing
- Empty space distribution
- Content density

Record margins, padding and gaps separately.

## 2.4 Typography Scale
For H1–H6, body text, captions, labels, navigation, buttons and links:

- Font size
- Font weight
- Line height
- Letter spacing
- Text alignment
- Text transformation
- Maximum text width
- Text color
- Margins
- Text wrapping behavior

**Important:** Extract the reference typography measurements, not its font family. The source website's fonts must be retained.

## 2.5 Header & Navigation
- Header height and width
- Positioning and sticky behavior
- Background and transparency
- Internal padding
- Logo dimensions and positioning
- Navigation alignment and spacing
- Navigation typography
- CTA position and dimensions
- Borders and shadows
- Dropdown dimensions
- Mobile navigation

## 2.6 Section Layouts
Analyze every section on every accessible page.

For each section collect:

- Section name and purpose
- Width and height
- Background color, image or gradient
- Container width
- Padding and margins
- Layout type
- Grid structure
- Number of columns
- Column proportions
- Row and column gaps
- Text and image positioning
- Horizontal and vertical alignment
- Internal spacing
- Borders, shadows and radius
- Decorative elements

Identify layout patterns such as:
- Split-screen hero
- Centered hero
- Two-column layouts
- Three/four-column grids
- Masonry
- Alternating image/text
- Overlapping sections
- Full-bleed images
- Asymmetric compositions
- Centered CTAs

## 2.7 Image Presentation
- Image and container dimensions
- Aspect ratio
- Object-fit and object-position
- Cropping behavior
- Border radius
- Overflow
- Shadows and borders
- Overlays
- Background positioning
- Hover effects and animations

Identify whether images are HTML elements, CSS backgrounds, SVGs or embedded media.

## 2.8 Cards & Content Blocks
- Width and height
- Minimum and maximum dimensions
- Background color
- Internal padding
- External margins
- Card gaps
- Border width and radius
- Shadow
- Image positioning
- Heading and paragraph typography
- Button and icon positioning
- Hover behavior

## 2.9 Buttons & Interactive Elements
- Width and height
- Horizontal and vertical padding
- Font size and weight
- Background and text colors
- Border and radius
- Icon dimensions and positioning
- Hover and active states
- Focus and disabled states
- Transition duration and easing

## 2.10 Visual Styling
- Background color distribution
- Alternating section backgrounds
- Accent color placement
- Border and divider colors
- Gradients and overlays
- Shadow properties
- Corner radii
- Decorative shapes
- Transparency

## 2.11 Responsive Design
Inspect at:

- 1920px desktop
- 1440px desktop
- 1280px laptop
- 768px tablet
- 390px mobile
- 320px small mobile

For each viewport extract:
- Container width and margins
- Section padding
- Grid columns and proportions
- Typography sizes
- Image dimensions
- Navigation behavior
- Card arrangement
- Content stacking order
- Hidden and visible elements
- Overflow behavior
- CSS breakpoints and media queries

## 2.12 Animations & Transitions
- Animation type
- Trigger
- Duration and delay
- Easing
- Direction and distance
- Opacity and transform changes
- Hover behavior
- Scroll-triggered behavior
- Loop behavior
- Reduced-motion support

---

# 3. EXTRACTION METHODS

Use the following inspection methods:

1. DOM inspection.
2. Computed CSS inspection.
3. Stylesheet inspection.
4. Browser rendering.
5. Screenshot analysis.
6. Responsive viewport testing.
7. Interaction testing.
8. Asset inspection.
9. Network resource inspection.

Prioritize actual computed CSS values over visual estimates.

For each measurement record:
- Property name
- Declared CSS value
- Computed value
- Unit
- Page URL
- DOM selector
- Viewport
- Extraction method
- Confidence level

Never invent missing values. Mark inaccessible or unknown properties as null.

---

# 4. SCREENSHOT REQUIREMENTS

For both websites capture:

- Full-page desktop screenshots
- Individual section screenshots
- Desktop screenshots
- Tablet screenshots
- Mobile screenshots
- Hover and interactive states
- Open dropdown and mobile menus

Store screenshots in separate source and reference directories.

---

# 5. FINAL DATA DELIVERABLES

**Source website:**
- brand_identity.json
- logos.json
- color_palette.json
- typography.json
- content.json
- assets.json
- sitemap.json
- page_structure.json
- functionality.json
- technical_stack.json

**Reference website:**
- global_layout.json
- grid_system.json
- spacing_system.json
- typography_scale.json
- header_footer.json
- section_layouts.json
- image_layouts.json
- cards_and_buttons.json
- visual_styles.json
- responsive_rules.json
- animations.json

**Final reports:**
- extraction_summary.json
- missing_data.json
- extraction_errors.json
- page_inventory.json

---

# 6. DESIGN TRANSFER RULES

The final redesign must follow these rules:

| Preserve from source | Replicate from reference |
|---|---|
| Brand identity | Layout |
| Logos | Grid system |
| Brand colors | Spacing |
| Font families | Font sizes |
| Font weights available | Typography hierarchy |
| Original content | White space |
| Original images | Image positioning |
| Functionality | Component composition |
| Brand personality | Dimensions |
| Assets | Responsive structure |

**Golden rule:** Preserve the source website's identity, content, assets and functionality. Reproduce the reference website's layout, spacing, proportions, typography scale and visual hierarchy.

Do not copy the reference website's brand identity, content or proprietary assets.

The final output must be a complete, measurable and implementation-ready design specification, not a subjective visual description.
