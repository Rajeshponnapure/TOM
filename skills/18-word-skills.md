# Word Skills — Mastery Guide

## Overview
Microsoft Word remains the premier document processing application for professional, academic, and business use. Mastery involves styles, templates, mail merge, fields, sections, forms, macros, and document automation.

---

## Styles

### Style Types

| Style Type | Purpose | Example |
|------------|---------|---------|
| Paragraph | Formats entire paragraph | Heading 1, Normal |
| Character | Formats text within paragraph | Strong, Emphasis |
| Linked | Acts as paragraph or character | Heading 1-9 |
| Table | Formats table elements | Table Grid |
| List | Formats numbered/bulleted lists | List Bullet |

### Creating and Modifying Styles

1. Open Styles pane (Alt+Ctrl+Shift+S)
2. Click New Style button (bottom left)
3. Set properties:
   - Name: `Report Title`
   - Style type: Paragraph
   - Based on: `Normal`
   - Style for following: `Subtitle`
4. Format: Font, Paragraph, Tabs, Border, Frame, Numbering, Shortcut Key

### Style Hierarchy

```
Theme fonts/colors
    └── Document defaults
         └── Normal (base style)
              ├── Heading 1-9
              ├── List Paragraph
              ├── Body Text
              └── Custom styles
```

Style inheritance: Child styles inherit from parent. Change the parent, and all children update.

### Shortcut Keys for Styles

| Shortcut | Style |
|----------|-------|
| Ctrl+Alt+1 | Heading 1 |
| Ctrl+Alt+2 | Heading 2 |
| Ctrl+Alt+3 | Heading 3 |
| Ctrl+Shift+N | Normal |
| Ctrl+Shift+S | Apply Styles pane |

### StyleRef Fields

StyleRef pulls text from the nearest matching style in the document.

```
{ STYLEREF "Heading 1" }
```

Options:
- `\l` — Show the last occurrence on the page
- `\p` — Position relative to paragraph
- `\n` — Show paragraph number

Use cases: Running headers that show current chapter title, headers that repeat document title.

---

## Templates

### Template Structure

Templates (.dotx, .dotm) contain:
- Styles, formatting presets
- Building Blocks (Quick Parts)
- Macros (in .dotm)
- Content controls
- Default text
- Page layout, margins, headers/footers

### Building Blocks and Quick Parts

Building Blocks are reusable content stored in templates.

**Create a Building Block:**
1. Select content (text, table, graphic)
2. Insert > Quick Parts > Save Selection to Quick Part Gallery
3. Set name, gallery (AutoText, etc.), category, template

**Insert:** Insert > Quick Parts > Building Blocks Organizer

**Built-in galleries:** AutoText, Cover Pages, Equations, Page Numbers, Watermarks, Tables of Contents.

### Template Organization

- **Global template (Normal.dotm):** Loaded automatically. For personal macros and styles.
- **Workgroup templates:** Shared via network or SharePoint.
- **Custom templates:** File > New > Personal.

Change template location: File > Options > Advanced > File Locations > User templates.

---

## Mail Merge

### Data Sources

Supported data sources:
- Excel workbook
- Access database
- Outlook contacts
- Word table
- Text file (CSV, tab-delimited)
- SQL Server

### Mail Merge Process

1. **Start**: Mailings > Start Mail Merge > Step-by-Step Mail Merge Wizard
2. **Select document type**: Letters, Email, Envelopes, Labels, Directory
3. **Select starting document**: Current, template, existing
4. **Select recipients**: Browse for data source
5. **Write your letter**: Insert merge fields
6. **Preview results**: Check each record
7. **Complete merge**: Print or send email

### Conditional Merge Fields

**IF field for conditional content:**
```
{ IF { MERGEFIELD Region } = "East" "East Region Pricing" "Standard Pricing" }
```

**Skip record if condition:**
```
{ SKIPIF { MERGEFIELD Status } = "Inactive" }
```

**Fill-in for manual data:**
```
{ FILLIN "Enter discount percentage:" }
```

### Merge Field Formatting

Control number/date formatting:
```
{ MERGEFIELD Amount \# "#,##0.00" }
{ MERGEFIELD Date \@ "MMMM d, yyyy" }
```

---

## Table of Contents

### TOC Fields

Insert a TOC: References > Table of Contents.

The underlying field:
```
{ TOC \o "1-3" \h \z \u }
```

Switches:
- `\o "1-3"` — Include heading styles 1-3
- `\h` — Hyperlinks
- `\z` — Hide tab leader and page numbers in Web layout
- `\u` — Use outline levels from paragraph formatting
- `\t "CustomStyle,1,OtherStyle,2"` — Custom styles

### Custom TOC

1. Insert TOC > Custom Table of Contents
2. Options: Assign TOC levels to styles
3. Modify: Change formatting of TOC 1-9 styles

### Update TOC

- `F9` — Update field
- Ctrl+A, F9 — Update all fields in document
- Set to update on open: File > Options > Display > Update fields before printing

---

## Cross-References

Insert > Cross-reference

| Reference Type | What You Can Reference |
|----------------|----------------------|
| Numbered item | List numbers |
| Heading | Headings by style |
| Bookmark | Any bookmarked text |
| Footnote/Endnote | Note numbers |
| Equation | Equation numbers |
| Figure/Table | Caption labels |

Cross-reference field code:
```
{ REF _Ref123456 \h }
```

Switches: `\h` hyperlink, `\p` show paragraph context, `\n` show number only.

---

## Captions and Indexing

### Captions

Insert captions for tables, figures, equations:
1. Right-click object > Insert Caption
2. Or: References > Insert Caption

**Auto-caption:** Insert Caption > AutoCaption — automatically add captions to selected object types.

### Table of Figures

References > Insert Table of Figures
- Uses caption labels (Figure, Table, Equation)
- Customizable via TOC field-like options

### Indexing

1. Select text and mark: References > Mark Entry (Alt+Shift+X)
2. Create index: References > Insert Index

Index entry fields:
```
{ XE "Term; Subterm" \b \i }
```

Bookmarks with `\b` for bold page, `\i` for italic.

### Bookmarks

Insert > Bookmark (Ctrl+Shift+F5)

Bookmark field:
```
{ BOOKMARK "TargetSection" }
```

GoTo with bookmark:
```
{GOTOBUTTON TargetSection "Go to Target"}
```

---

## Fields

### Common Field Codes

| Field | Purpose |
|-------|---------|
| `{ DATE \@ "MMMM d, yyyy" }` | Current date |
| `{ TIME }` | Current time |
| `{ PAGE }` | Current page number |
| `{ NUMPAGES }` | Total pages |
| `{ FILENAME \p }` | File name with path |
| `{ AUTHOR }` | Document author |
| `{ DOCPROPERTY "Company" }` | Custom document property |
| `{ =SUM(LEFT) }` | Sum of table row |

### Document Properties

File > Info > Properties > Advanced Properties

Custom properties can be inserted via field codes:
```
{ DOCPROPERTY "Project" }
```

### IF Fields

```
{ IF { MERGEFIELD Score } >= 90 "Excellent" "Needs Improvement" }
```

Nested IF for multiple conditions:
```
{ IF { MERGEFIELD Grade } = "A" "Distinguished" 
  { IF { MERGEFIELD Grade } = "B" "Proficient" "Developing" } }
```

### Formula Fields in Tables

Layout > Formula (in Table Design context)
```
{ =SUM(ABOVE) }
{ =AVERAGE(LEFT) }
{ =MAX(BELOW) }
```

---

## Sections

### Section Breaks

| Break Type | Purpose |
|------------|---------|
| Next Page | New section starts on next page |
| Continuous | Same page, different formatting |
| Even Page | Start on next even page |
| Odd Page | Start on next odd page |

### Different Headers and Footers

Section-dependent headers:
1. Insert section breaks between chapters
2. Double-click header area
3. Deselect "Link to Previous" for each section
4. Set unique header/footer per section

### Page Numbering

- Restart numbering per section: Insert > Page Number > Format Page Numbers > Start at
- Different first page: Header & Footer > Different First Page
- Skip page number on title page: Insert section break, unlink, remove from first section

### Section Orientation

Mix portrait and landscape in one document:
1. Insert section break before landscape content
2. Layout > Orientation > Landscape (applied to current section only)
3. Insert section break after, switch back to Portrait

---

## Track Changes

### Managing Track Changes

- **Turn on/off**: Review > Track Changes (Ctrl+Shift+E)
- **View modes**: Simple Markup, All Markup, No Markup, Original
- **Balloons**: Show revisions in balloons (right margin)

### Accepting and Rejecting

| Action | Button |
|--------|--------|
| Accept single change | Right-click > Accept |
| Accept all changes | Accept dropdown > Accept All Changes |
| Reject all | Reject dropdown > Reject All |

### Comparing Documents

Review > Compare > Compare:
1. Original document and revised document
2. Choose what to compare (formatting, content)
3. Show changes in new document or original

### Combining Documents

Review > Compare > Combine — merges changes from multiple reviewers into one document.

---

## Macros (VBA for Word)

### VBA Editor

- Open: Alt+F11
- Insert Module: Insert > Module
- Run: F5 or Macros dialog (Alt+F8)

### Document Automation Examples

```vba
' Format entire document with consistent styles
Sub FormatDocument()
    Dim para As Paragraph
    
    For Each para In ActiveDocument.Paragraphs
        If para.Range.Words.Count > 20 Then
            para.Style = "Body Text"
        End If
    Next para
End Sub

' Insert header with field codes
Sub InsertChapterHeader()
    With ActiveDocument.Sections(1).Headers(wdHeaderFooterPrimary)
        .Range.Text = ""
        With .Range
            .Fields.Add _
                Range:=.Range, _
                Type:=wdFieldEmpty, _
                Text:="STYLEREF ""Heading 1"" \n \* MERGEFORMAT"
        End With
    End With
End Sub

' Mail merge from code
Sub RunMailMerge()
    With ActiveDocument.MailMerge
        .Destination = wdSendToNewDocument
        .SuppressBlankLines = True
        With .DataSource
            .FirstName = "Data"
            .FileName = "C:\Data\Customers.xlsx"
            .OpenDataSource _
                Name:="C:\Data\Customers.xlsx", _
                ConfirmConversions:=False, _
                ReadOnly:=False, _
                LinkToSource:=True, _
                AddToRecentFiles:=False, _
                Connection:="Provider=Microsoft.ACE.OLEDB.12.0;Data Source=C:\Data\Customers.xlsx;Extended Properties=""Excel 12.0;HDR=YES;IMEX=1"";", _
                SQLStatement:="SELECT * FROM [Sheet1$]"
        End With
        .Execute Pause:=False
    End With
End Sub
```

### Find and Replace with VBA

```vba
Sub ReplaceFormatting()
    Selection.Find.ClearFormatting
    Selection.Find.Replacement.ClearFormatting
    
    With Selection.Find
        .Text = "([0-9]{1,})%"
        .Forward = True
        .Wrap = wdFindContinue
        .Format = False
        .MatchWildcards = True
    End With
    
    With Selection.Find.Replacement
        .Text = "\1 percent"
        .Font.Bold = True
    End With
    
    Selection.Find.Execute Replace:=wdReplaceAll
End Sub

' Find specific style
Sub FindHeadingStyles()
    Dim rng As Range
    Set rng = ActiveDocument.Content
    
    With rng.Find
        .ClearFormatting
        .Style = "Heading 2"
        .Format = True
        .Forward = True
        .Wrap = wdFindStop
        
        Do While .Execute
            ' Add bookmark for each heading
            ActiveDocument.Bookmarks.Add _
                Name:="H2_" & Replace(rng.Text, " ", "_"), _
                Range:=rng
        Loop
    End With
End Sub
```

### Form Automation

```vba
' Protect document for form filling
Sub ProtectForm()
    With ActiveDocument
        .Protect Type:=wdAllowOnlyFormFields, NoReset:=True
        If .ProtectionType <> wdNoProtection Then
            MsgBox "Document is protected. Fill in the form fields."
        End If
    End With
End Sub

' Collect form data
Sub CollectFormResponses()
    Dim fld As FormField
    Dim ws As Object
    Dim row As Long
    
    ' Requires Excel reference
    Set ws = CreateObject("Excel.Application").Workbooks.Add.Sheets(1)
    row = 1
    
    For Each fld In ActiveDocument.FormFields
        ws.Cells(row, 1).Value = fld.Name
        If fld.Type = wdFieldFormTextInput Then
            ws.Cells(row, 2).Value = fld.Result
        ElseIf fld.Type = wdFieldFormDropDown Then
            ws.Cells(row, 2).Value = fld.DropDown.Value
        End If
        row = row + 1
    Next fld
    
    ws.Application.Visible = True
End Sub
```

---

## Forms

### Legacy Form Fields

Developer > Legacy Tools > Legacy Form (Legacy Forms toolbar):

| Field | Purpose |
|-------|---------|
| Text Form Field | Text, number, date input |
| Check Box Form Field | Yes/No, selected/cleared |
| Drop-Down Form Field | List selection |

Properties: Right-click form field > Properties

### Content Controls

Developer > Controls gallery:

| Control | Purpose |
|---------|---------|
| Rich Text | Formatted text entry |
| Plain Text | Unformatted text |
| Picture | Image insertion |
| Combo Box | Dropdown with custom entry |
| Drop-Down List | Fixed list selection |
| Date Picker | Calendar date selection |
| Check Box | Toggle selection |
| Building Block Gallery | Reusable content selector |

Content control properties:
- Title, Tag
- Locking (cannot be deleted, cannot edit)
- Color
- Placeholder text
- XML mapping (for data binding)

### Form Protection

Developer > Restrict Editing:
- Allow only this type of editing: Filling in forms
- Select sections to protect
- Apply password (optional but weak)

---

## Table Design

### Table Creation and Formatting

Insert > Table > Quick Tables (built-in templates)

**Table Design tab:**
- Header Row, Total Row, Banded Rows/Columns
- Shading, Borders, Effects
- Table styles gallery

**Layout tab:**
- Insert/delete rows/columns
- Merge/split cells
- Cell size (distribute, auto-fit)
- Text direction
- Cell margins

### Table Alignment and Positioning

- Table Properties > Table tab: Alignment, Text wrapping
- Row tab: Repeat as header row on every page
- Column tab: Preferred width
- Cell tab: Vertical alignment

### Table Calculations

Layout > Formula (for basic calculations):
```
{ =SUM(ABOVE) }
{ =PRODUCT(LEFT) }
{ =IF(C2>D2,"High","Low") }
```

---

## SmartArt

Insert > SmartArt

| Category | Use Case |
|----------|----------|
| List | Non-sequential or grouped items |
| Process | Steps in a workflow |
| Cycle | Repeating or circular process |
| Hierarchy | Org charts, tree structures |
| Relationship | Connections, overlaps |
| Matrix | Quadrant-based layouts |
| Pyramid | Hierarchical proportions |

**SmartArt Design tab:** Add shapes, promote/demote, change layout, change colors
**SmartArt Format tab:** Shape fill, outline, effects, text pane

---

## Watermarks

Design > Watermark

- Built-in: Confidential, Draft, Urgent, Sample
- Custom: Custom Watermark > Text or Picture
- Text: Font, size, color, layout (horizontal/diagonal)

Remove: Design > Watermark > Remove Watermark

---

## Document Protection

File > Info > Protect Document

| Protection | Purpose |
|------------|---------|
| Mark as Final | Read-only, no editing |
| Encrypt with Password | Password to open |
| Restrict Editing | Limit formatting, track changes, forms |
| Restrict Permission | IRM (Information Rights Management) |
| Add a Digital Signature | Authenticate document |

---

## Accessibility

### Alt Text

Right-click object > Edit Alt Text

Guidelines:
- Describe the content and function of the image
- Decorative images: Mark as decorative
- Keep concise (1-2 sentences)

### Heading Structure

- Use true heading styles (H1, H2, H3), not bold+larger font
- Never skip levels (H1 > H2 > H3)
- Only one H1 per document

### Reading Order

- Selection pane (Home > Arrange > Selection Pane)
- Reading order should be top-to-bottom in Selection Pane
- Screen readers read items in reverse selection pane order

### Accessibility Checker

Review > Check Accessibility

Checks for:
- Missing alt text
- Missing heading structure
- Improper table structure (merged/split cells)
- Low contrast
- Empty table rows/columns
- Missing document title

### Additional Accessibility

- Use sufficient color contrast (4.5:1 for text)
- Don't use color alone to convey meaning
- Use simple table structure (no nested tables)
- Set document language (Review > Language)
- Add meaningful hyperlink text (not "click here")
- Use bulleted lists for related items
- Avoid floating objects (use In Line with Text)

---

## Export and Compatibility

### Export Formats

| Format | Use Case |
|--------|----------|
| PDF | Universal sharing, fixed layout |
| PDF/A | Long-term archival |
| DOCX | Standard Word format |
| DOC | Legacy compatibility |
| RTF | Cross-platform |
| TXT | Plain text |
| HTML | Web publishing |
| XML | Data interchange |

### File > Export

- Create PDF/XPS Document
- Change File Type (DOCX, DOTX, RTF, PDF, etc.)

---

## Best Practices

### Document Organization

```
Title: One H1
├── Heading 1: Chapter/Section
│   ├── Heading 2: Subsection
│   │   ├── Heading 3: Sub-subsection
│   │   ├── Body text
│   │   └── List items
│   └── Heading 2
├── Heading 1
│   ├── Tables with captions
│   ├── Figures with captions
│   └── Cross-references
└── Appendices (restart H1 with appendix numbering)
```

### Style-Based Formatting

- Never use direct formatting (bold, font size) — always apply a style
- Modify existing styles rather than creating new ones
- Use character styles (Emphasis, Strong) over direct bold/italic
- Set up template once, reuse for all similar documents

### Template Design

```
Templates folder: %USERPROFILE%\AppData\Roaming\Microsoft\Templates

Global template: Normal.dotm — stores macros, AutoText, styles

Best practice:
    [ ] Define all styles in the template
    [ ] Add building blocks for reusable content
    [ ] Store macros in the template
    [ ] Set content controls for variable content
    [ ] Define default document properties
    [ ] Set up headers/footers
    [ ] Create AutoText entries for standard clauses
    [ ] Protect boilerplate sections
```
