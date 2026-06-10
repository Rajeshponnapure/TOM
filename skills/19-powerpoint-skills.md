# PowerPoint Skills — Mastery Guide

## Overview
Microsoft PowerPoint is the industry standard for presentation design and delivery. Mastery covers slide master architecture, design principles, animations, transitions, SmartArt, data visualization, embedded objects, presenter tools, templates, and automation via VBA.

---

## Slide Master Design

### Master Hierarchy

```
Slide Master (theme root)
├── Layout 1: Title Slide
│   ├── Placeholder: Title
│   └── Placeholder: Subtitle
├── Layout 2: Title and Content
│   ├── Placeholder: Title
│   └── Placeholder: Content (text, table, chart, SmartArt, picture, etc.)
├── Layout 3: Section Header
├── Layout 4: Two Content
├── Layout 5: Comparison
├── Layout 6: Title Only
├── Layout 7: Blank
├── Layout 8: Content with Caption
└── Layout 9: Picture with Caption
```

View > Slide Master to edit.

### Layout Design

**Placeholder Types:**
- Content (auto-detects: text, table, chart, SmartArt, picture, video)
- Text
- Picture
- Chart
- Table
- SmartArt
- Media

**Placeholder Formatting:**
- Position and size via Format Shape pane
- Edit placeholder text for default instructions
- Insert shapes, headers, footers, page numbers on layouts

### Theme Variants

Slide Master > Variants gallery:
- Color variants
- Font scheme changes
- Background styles
- Effects variants

Create custom variants by modifying theme colors/fonts and saving as a new variant.

### Theme Colors

View > Slide Master > Colors > Customize Colors

| Color Slot | Purpose |
|------------|---------|
| Dark 1 / Light 1 | Text/Background |
| Dark 2 / Light 2 | Subtle accents |
| Accent 1-6 | Main palette |
| Hyperlink | Link color |
| Followed Hyperlink | Visited link color |

### Theme Fonts

View > Slide Master > Fonts > Customize Fonts
- Heading font (used for titles)
- Body font (used for content)

---

## Design Principles

### CRAP Principles

| Principle | Application in PowerPoint |
|-----------|--------------------------|
| **Contrast** | Dark text on light backgrounds; bold colors for key data; varied font sizes for hierarchy |
| **Repetition** | Consistent colors, fonts, bullet styles across slides; repeat logo or accent line |
| **Alignment** | Left-align text; align shapes and images to grid; use guides and smart guides |
| **Proximity** | Group related items; separate unrelated sections with whitespace |

### Typography Guidelines

- Maximum 2 font families per deck
- Minimum 24pt for body text (30pt recommended)
- Headlines: 36-60pt depending on hierarchy
- Sans-serif for on-screen (Calibri, Segoe UI, Arial)
- Serif for print (Georgia, Cambria, Times New Roman)
- Line spacing: 1.2-1.5 for readability

### Visual Hierarchy

```
Title (largest, boldest, most contrast)
    → Subtitle / Section header
        → Body text
            → Bullet points
                → Sub-points
```

### Whitespace

- Minimum 0.5" margins on all sides
- Avoid overcrowding slides
- One key message per slide
- 6x6 rule: max 6 bullets, 6 words per bullet (guideline, not strict rule)

### Color Palette Design

- Primary: 1-2 brand colors
- Secondary: 2-3 complementary colors
- Neutral: dark and light grays
- Accent: 1 highlight color for CTAs

Use the 60-30-10 rule: 60% neutral, 30% primary, 10% accent.

---

## Animations

### Animation Types

| Type | Purpose | Examples |
|------|---------|----------|
| **Entrance** | Element appears | Fade, Fly In, Zoom, Wipe |
| **Emphasis** | Draw attention | Pulse, Spin, Grow/Shrink, Teeter |
| **Exit** | Element disappears | Disappear, Fade Out, Fly Out |
| **Motion Paths** | Moves along path | Lines, Arcs, Custom Path |

### Advanced Animation Settings

**Effect Options:**
- Direction (From Left, etc.)
- Timing (Start: On Click, With Previous, After Previous)
- Duration (0.01-59 seconds)
- Delay (seconds before animation starts)
- Repeat (none, 2-10, until next click, until end of slide)

**Trigger Animations:**
- On Click Of: any shape/object on the slide
- Start Effect on Click of: specific trigger shape

### Animation Timeline

Animation Pane > Advanced Timeline:
- Drag bars to adjust timing
- Right-click for effect options
- Reorder by dragging

**Staggered animations:** Select multiple items > Add animation > Set timing with delay intervals.

### Best Practices for Animations

- Use consistent animation patterns across slides
- Keep total animation duration under 5 seconds per slide
- Avoid random, boomerang, or flashy animations
- Use subtle motion (fade, wipe) for professional content
- Save heavy animation builds for dramatic moments
- Test timing with presenter mode before presentation

### Motion Paths

Custom path: Insert > Shapes > Scribble, or Animation > Add Animation > Custom Path

**Editing motion paths:**
- Green arrow = start point
- Red arrow = end point
- Right-click path > Edit Points
- Smooth/straight/curve point options

---

## Transitions

### Transition Types

| Category | Examples | Best Use |
|----------|----------|----------|
| Subtle | Fade, Push, Wipe, Split | Standard content |
| Exciting | Cube, Doors, Orbit, Ripple | Section transitions |
| Dynamic Content | Morph | Transforming elements between slides |
| None | Instant cut | Fast-paced presentations |

### Morph Transition (PowerPoint 2019+ / 365)

Works by matching object names between slides:
1. Name objects: Selection Pane > rename to same word on both slides
2. Apply Morph transition
3. Animates position, size, rotation, color, opacity

Works with:
- Text boxes, shapes, pictures, SmartArt, charts
- 3D models
- Characters in text (letter-by-letter morph)

### Transition Settings

- **Duration**: 0.25-5 seconds (default 1 sec)
- **Sound**: Use sparingly (None for professional decks)
- **Advance Slide**: On Mouse Click, After (timed)
- **Apply To All**: For consistent transitions

### Push and Cover Transitions

- **Push**: New slide pushes old one off (direction options)
- **Cover**: New slide covers old one
- **Uncover**: Old slide uncovers new one

Best for: Sequential storytelling, step-by-step reveals.

---

## SmartArt Graphics

### SmartArt Categories

| Category | Best For | Examples |
|----------|----------|----------|
| List | Grouped information | Vertical bullet list, Horizontal list |
| Process | Sequential steps | Arrow processes, Chevron list |
| Cycle | Repeating processes | Circular, Gear, Basic cycle |
| Hierarchy | Org charts | Organizational chart, Pyramid |
| Relationship | Connections | Venn diagram, Radial, Target |
| Matrix | Quadrant data | Grid matrix, Cycle matrix |
| Pyramid | Proportions | Basic pyramid, Inverted |

### SmartArt Tips

- Convert existing text to SmartArt: Select text > Convert to SmartArt
- Add shapes: Design tab > Add Shape (After/Before/Above/Below)
- Promote/Demote: Design tab > Promote/Demote
- Change layout: Design tab > Layouts gallery
- Reset graphic: Design tab > Reset Graphic
- Convert to shapes: Cannot revert to SmartArt

### Formatting SmartArt

SmartArt Format tab:
- Shape Fill, Outline, Effects
- Change shape (any shape can become any other shape)
- Larger/smaller shape icons
- Text Pane (Ctrl+Shift+F2) for keyboard navigation

---

## Chart Animation

### Chart Animation Options

1. Select chart > Add Animation (e.g., Wipe)
2. Effect Options > Sequence:
   - As One Object: Entire chart animates together
   - By Series: Each data series appears one at a time
   - By Category: Each category appears one at a time
   - By Series Element: Each point in each series
   - By Category Element: Each point in each category

### Advanced Chart Animation

- Use multiple animations on the same chart
- Animate individual series with trigger timings
- Animate chart elements with delay for data storytelling
- Combine chart animations with shape overlays for build effects

---

## Embedded Objects

### Embedding Excel Ranges

Insert > Object > Create from File > Browse

Or: Paste Special > Paste Link > Microsoft Excel Worksheet Object

**Live data connections:**
1. Copy Excel range
2. Home > Paste > Paste Special > Paste Link
3. Right-click object > Linked Worksheet Object > Links > Update manually/automatically

### Embedding Other Content

- **Word documents**: Insert > Object > Word Document
- **PDFs**: Insert > Object > Adobe Acrobat Document
- **Video**: Insert > Video > This Device / Online Video
- **Audio**: Insert > Audio > Audio on My PC / Record Audio
- **3D Models**: Insert > 3D Models > From a File / Online Sources

---

## Video and Audio Integration

### Video Setup

- Start: Automatically, On Click
- Playback options: Loop, Rewind, Full screen
- Trim video: Trimming handles
- Fade duration: Fade In / Fade Out
- Poster Frame: Set still image when video is not playing
- Bookmark chapters: Add bookmarks for rapid navigation

### Audio Setup

- Speaker icon hidden options: Start > Automatically, Play Across Slides
- Loop until stopped
- Trim audio
- Fade in/out
- Bookmark chapters

---

## Custom Shows

Slide Show > Custom Slide Show > Custom Shows

**Base show** slideshow includes all slides. **Custom shows** can:
- Show only selected slides
- Reorder slides without changing original
- Create different versions from one deck

Hyperlink to custom show: Select text/shape > Insert > Link > Place in This Document > Custom Show

---

## Presenter Tools

### Presenter View (Alt+F5)

Presenter view provides:
- Current slide (large)
- Next slide preview
- Speaker notes (large, readable)
- Timer (elapsed, clock)
- Pen/laser pointer/highlighter
- Zoom into slide
- Black/unblack slide (B key)
- Thumbnail navigation

### Rehearse Timings

Slide Show > Rehearse Timings
- Records time spent on each slide
- Saves timings for auto-advance
- Clears timings: Slide Show > Record Slide Show > Clear

### Teleprompter Mode

- Use Presenter View with large font notes
- Increase zoom in notes pane
- Practice with scrolling notes
- Third-party add-ins for teleprompter functionality

### Speaker Notes

Add notes: View > Notes (below slide) or Notes Page view

Best practices:
- Write conversational text, not reading script
- Include pronunciation guides
- Note slide triggers (animations, video starts)
- Add timing cues

---

## Templates

### Creating Custom Themes

1. Design slide master with layouts, colors, fonts
2. Save as .thmx: Design > Themes > Save Current Theme
3. Save as .potx: File > Save As > PowerPoint Template (.potx)
4. Save as .potm (macro-enabled template) for VBA automation

### Template Distribution

- **Organization-wide**: Install to `%USERPROFILE%\AppData\Roaming\Microsoft\Templates\Document Themes`
- **SharePoint**: Upload to organization asset library
- **Add-in**: Deploy as Office add-in
- **Company template**: Set default template location in Group Policy

### Template Elements

Complete template should include:
```
[ ] Slide master with company branding
[ ] All layouts (title, content, section, blank, etc.)
[ ] Theme colors file (.thmx)
[ ] Font scheme
[ ] Effect scheme
[ ] Background styles
[ ] Placeholder positioning guidelines
[ ] Default animations and transitions
[ ] Consistent footer/slide numbers
[ ] Company logo on master
[ ] Sample slides for quick start
[ ] Speaker notes template
```

---

## Infographics and Data Visualization

### Infographic Creation

Tools within PowerPoint:
- SmartArt for process flows
- Icons: Insert > Icons
- Shapes: Insert > Shapes (combine with Merge Shapes)
- Remove backgrounds: Picture Format > Remove Background
- Screenshot: Insert > Screenshot

**Merge Shapes tools:**
- Union: Combine shapes into one
- Combine: Merge, remove overlap
- Fragment: Split into pieces
- Intersect: Keep overlap only
- Subtract: Remove overlapping area

### Data Visualization Best Practices

- Choose the right chart type:
  - Comparison: Bar/Column
  - Composition: Pie (small data), Stacked bar, Treemap
  - Distribution: Histogram, Scatter
  - Trend: Line chart
  - Relationship: Scatter with trendline
- Remove chart junk: gridlines, 3D effects, unnecessary legends
- Use data labels instead of axis when precise values matter
- Sort data logically (ascending/descending)
- Use consistent color coding

### Chart Directly in PowerPoint

Insert > Chart > Choose type

Data opens in Excel worksheet. Edit data in linked sheet.

---

## Storytelling Frameworks

### Common Structures

| Framework | Structure | Best For |
|-----------|-----------|----------|
| **Problem-Solution** | Problem → Impact → Solution → Results | Sales pitches |
| **Before-After-Bridge** | Current state → Future state → How to get there | Transformation |
| **Hero's Journey** | Status quo → Challenge → Guide → Success | Case studies |
| **Pyramid Principle** | Conclusion first → Supporting arguments → Evidence | Executive reports |
| **Story Arc** | Setup → Rising action → Climax → Resolution | Narrative decks |

### Slide Structure Per Story Point

```
Slide 1: Hook (title, dramatic stat, question)
Slide 2-3: Context (problem, background)
Slide 4-5: Complication (why current approach fails)
Slide 6-7: Solution (approach, evidence)
Slide 8-9: Results (data, testimonials)
Slide 10: Call to Action (clear next step)
```

### Section Breaks

Use section header slides between major sections:
- Full-bleed image with text overlay
- Large number or section title
- Consistent divider style throughout deck

---

## Section Zoom / Summary Zoom

Insert > Zoom > Section Zoom / Summary Zoom

**Section Zoom:** Thumbnail that navigates to a section.
**Summary Zoom:** Landing page with thumbnails for all sections.

Benefits:
- Visual navigation
- Non-linear presentation flexibility
- Professional appearance
- No slide deletion needed

---

## Add-ins and Extensions

### Office.js Add-ins

Web-based add-ins built with HTML/JS/CSS. Deploy via AppSource or internal catalog.

Basic structure:
```html
<!-- taskpane.html -->
<!DOCTYPE html>
<html>
<head>
  <script src="https://appsforoffice.microsoft.com/lib/1/hosted/office.js"></script>
</head>
<body>
  <button id="run">Insert Slide</button>
  <script>
    Office.onReady(() => {
      document.getElementById('run').onclick = () => {
        PowerPoint.run(async (context) => {
          const slides = context.presentation.slides;
          context.load(slides);
          await context.sync();
          console.log(`Total slides: ${slides.items.length}`);
        });
      };
    });
  </script>
</body>
</html>
```

### VSTO Add-ins

.NET-based add-ins for deeper integration with Office.

---

## Export Formats

| Format | When to Use |
|--------|-------------|
| .pptx | Standard editable format |
| .pdf | Distribution, printing, no editing |
| .xps | Alternative to PDF |
| .mp4 | Video export with timings/narration |
| .wmv | Legacy video format |
| .jpg/.png | Slide images (one per slide) |
| .tiff | High-quality slide images |
| .bmp | Uncompressed bitmap |
| .gif | Animated GIF (with transitions/timings) |
| .rtf | Outline/text only |
| .odp | OpenDocument presentation |
| .htm | Web page format |

---

## Collaboration

### Co-Authoring (Real-time)

- Save to OneDrive, SharePoint, or OneDrive for Business
- Multiple users edit simultaneously
- Presence indicators show each author's location
- Version history: File > Info > Version History

### Comments

Review > New Comment (Ctrl+Alt+M)
- @mention colleagues for notifications
- Resolve comments when addressed
- Navigate comments: Review > Previous/Next

### Compare and Merge

Review > Compare > Compare
- Merge changes from multiple versions
- Accept/reject individual changes
- Works with tracked changes from co-authors

---

## VBA Automation

### Slide Creation

```vba
Sub CreatePresentation()
    Dim pptApp As Object
    Dim pptPres As Object
    Dim slide As Object
    
    Set pptApp = CreateObject("PowerPoint.Application")
    pptApp.Visible = True
    Set pptPres = pptApp.Presentations.Add
    
    ' Add title slide
    Set slide = pptPres.Slides.Add(1, ppLayoutTitle)
    slide.Shapes.Title.TextFrame.TextRange.Text = "Q4 Sales Review"
    slide.Shapes(2).TextFrame.TextRange.Text = "Presented by: Sales Team"
    
    ' Add content slide
    Set slide = pptPres.Slides.Add(2, ppLayoutText)
    slide.Shapes.Title.TextFrame.TextRange.Text = "Key Metrics"
    slide.Shapes(2).TextFrame.TextRange.Text = _
        "• Revenue: $12.4M" & vbCrLf & _
        "• Growth: 23% YoY" & vbCrLf & _
        "• New Customers: 1,247"
    
    ' Add blank slide with shapes
    Set slide = pptPres.Slides.Add(3, ppLayoutBlank)
    With slide.Shapes.AddShape(msoShapeRoundedRectangle, 50, 50, 200, 100)
        .Fill.ForeColor.RGB = RGB(0, 114, 178)
        .TextFrame.TextRange.Text = "Q4 Target"
        .TextFrame.TextRange.Font.Color.RGB = RGB(255, 255, 255)
        .TextFrame.TextRange.Font.Size = 24
    End With
    
    Set pptPres = Nothing
    Set pptApp = Nothing
End Sub
```

### Chart Addition

```vba
Sub AddChartToSlide()
    Dim pptPres As Presentation
    Set pptPres = ActivePresentation
    
    Dim sld As Slide
    Set sld = pptPres.Slides.Add(pptPres.Slides.Count + 1, ppLayoutBlank)
    
    ' Add clustered bar chart
    Dim cht As Chart
    Set cht = sld.Shapes.AddChart2(251, xlColumnClustered, 50, 50, 600, 400).Chart
    
    ' Set chart data
    Dim ws As Object
    Set ws = cht.ChartData.Workbook.Worksheets(1)
    
    ' Clear default data
    ws.Cells.Clear
    
    ' Fill data
    ws.Cells(1, 1).Value = "Quarter"
    ws.Cells(1, 2).Value = "Sales"
    ws.Cells(1, 3).Value = "Target"
    
    ws.Cells(2, 1).Value = "Q1"
    ws.Cells(2, 2).Value = 1200000
    ws.Cells(2, 3).Value = 1000000
    
    ws.Cells(3, 1).Value = "Q2"
    ws.Cells(3, 2).Value = 1450000
    ws.Cells(3, 3).Value = 1200000
    
    ws.Cells(4, 1).Value = "Q3"
    ws.Cells(4, 2).Value = 1350000
    ws.Cells(4, 3).Value = 1300000
    
    ws.Cells(5, 1).Value = "Q4"
    ws.Cells(5, 2).Value = 1800000
    ws.Cells(5, 3).Value = 1500000
    
    ' Set chart title
    cht.HasTitle = True
    cht.ChartTitle.Text = "2024 Sales vs Target"
    
    ' Style
    cht.ChartStyle = 204
    
    cht.ChartData.Workbook.Close
End Sub
```

### Export Presentation to Images

```vba
Sub ExportSlidesAsImages()
    Dim pptPres As Presentation
    Set pptPres = ActivePresentation
    
    Dim exportPath As String
    exportPath = "C:\Exports\Slides\"
    
    ' Ensure directory exists
    If Dir(exportPath, vbDirectory) = "" Then
        MkDir exportPath
    End If
    
    ' Export each slide as PNG
    Dim i As Long
    For i = 1 To pptPres.Slides.Count
        pptPres.Slides(i).Export _
            exportPath & "Slide" & Format(i, "00") & ".png", _
            "PNG", 1920, 1080
    Next i
    
    MsgBox "Exported " & pptPres.Slides.Count & " slides to " & exportPath
End Sub
```

### Update All Charts

```vba
Sub RefreshAllCharts()
    Dim sld As Slide
    Dim shp As Shape
    
    For Each sld In ActivePresentation.Slides
        For Each shp In sld.Shapes
            If shp.HasChart Then
                shp.Chart.Refresh
            End If
        Next shp
    Next sld
    
    MsgBox "All charts refreshed."
End Sub
```

---

## Presentation Best Practices

### Pre-Presentation Checklist

```
[ ] Check font rendering (no missing fonts)
[ ] Run Slide Show > Rehearse Timings
[ ] Test all hyperlinks
[ ] Test embedded videos/audio
[ ] Review speaker notes
[ ] Check slide numbers
[ ] Proofread all text (use spell check)
[ ] Verify chart data accuracy
[ ] Check presenter display setup
[ ] Have backup copy (PDF)
[ ] Test on presentation computer
[ ] Check aspect ratio (16:9 vs 4:3)
```

### Delivery Tips

- Use B key to black screen during Q&A
- W key for white screen
- Ctrl+P for pen tool in slideshow
- Ctrl+A for arrow cursor
- Ctrl+E for eraser
- Slide number + Enter to jump to slide
- Right-click > See All Slides for navigation

### File Management

- Keep file size under 10MB when possible
- Compress images: Picture Format > Compress Pictures
- Embed fonts: File > Options > Save > Embed fonts in the file
- Remove personal info: File > Info > Check for Issues > Inspect Document
