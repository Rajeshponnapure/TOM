# Excel Skills — Mastery Guide

## Overview
Microsoft Excel remains the most widely used data analysis tool in business. Mastery spans formulas, pivot tables, VBA automation, Power Query, Power Pivot, and advanced analytical techniques.

---

## Formulas and Functions

### Lookup Functions

**VLOOKUP** — Vertical lookup. Limited because it only searches the first column and returns a column to the right.

```
=VLOOKUP(lookup_value, table_array, col_index_num, [range_lookup])
```

Example:
```
=VLOOKUP(A2, $D$2:$F$100, 3, FALSE)
```

**INDEX/MATCH** — More flexible than VLOOKUP. Can search any column, return any column, and handles column inserts safely.

```
=INDEX(return_range, MATCH(lookup_value, lookup_range, 0))
```

Example:
```
=INDEX($F$2:$F$100, MATCH(A2, $D$2:$D$100, 0))
```

**XLOOKUP** — Modern replacement for VLOOKUP/HLOOKUP/INDEX/MATCH (Excel 2021+ / 365).

```
=XLOOKUP(lookup_value, lookup_array, return_array, [if_not_found], [match_mode], [search_mode])
```

Example:
```
=XLOOKUP(A2, $D$2:$D$100, $F$2:$F$100, "Not Found", 0, 1)
```

### Conditional Aggregation

**SUMIFS** — Sum with multiple criteria:
```
=SUMIFS(sum_range, criteria_range1, criterion1, [criteria_range2, criterion2, ...])
```

**COUNTIFS** — Count with multiple criteria:
```
=COUNTIFS(criteria_range1, criterion1, [criteria_range2, criterion2, ...])
```

**AVERAGEIFS** — Average with multiple criteria:
```
=AVERAGEIFS(avg_range, criteria_range1, criterion1, ...)
```

Example — Sum all sales in January for Product A:
```
=SUMIFS(SalesAmount, SalesDate, ">=1/1/2024", SalesDate, "<=1/31/2024", Product, "A")
```

### Array Formulas

Classic array formulas (Ctrl+Shift+Enter in older Excel):
```
{=MAX(IF(A2:A100="Product A", B2:B100))}
```

Modern dynamic array formulas (Excel 365):
```
=FILTER(A2:B100, C2:C100>1000)
=SORT(UNIQUE(A2:A100))
=SEQUENCE(10, 1, 1, 1)
```

### Dynamic Array Functions

| Function | Purpose |
|----------|---------|
| `FILTER` | Return filtered rows matching criteria |
| `SORT` | Sort a range by one or more columns |
| `SORTBY` | Sort by another array |
| `UNIQUE` | Extract unique values |
| `SEQUENCE` | Generate sequential numbers |
| `RANDARRAY` | Generate random numbers |
| `SINGLE` | Extract single value from array |

Example — Dynamic list of top 10 sales:
```
=SORT(FILTER(A2:C100, C2:C100>=LARGE(C2:C100, 10)), 3, -1)
```

---

## Pivot Tables

### Creating Pivot Tables

1. Select your data range or table
2. Insert > PivotTable
3. Choose location (new or existing worksheet)
4. Drag fields to Rows, Columns, Values, Filters

### Grouping

- **Date grouping**: Right-click a date field > Group > Days/Months/Quarters/Years
- **Numeric grouping**: Right-click a numeric field > Group > Set start/end/interval
- **Custom grouping**: Select multiple items > Right-click > Group

### Calculated Fields and Items

**Calculated Field** (adds a new field to the pivot):
1. PivotTable Analyze > Fields, Items & Sets > Calculated Field
2. Name: `Profit`
3. Formula: `= Revenue - Cost`

**Calculated Item** (adds a new row within a field):
1. Select a field item
2. Fields, Items & Sets > Calculated Item
3. Formula: `= ProductA + ProductB`

### Slicers and Timelines

- **Slicers**: PivotTable Analyze > Insert Slicer. Connect to multiple pivots.
- **Timeline**: PivotTable Analyze > Insert Timeline. Only works with date fields.
- Connect slicers to multiple pivot tables: Right-click slicer > Report Connections.

### GETPIVOTDATA

Excel's GETPIVOTDATA function extracts values from a pivot table:
```
=GETPIVOTDATA("Sales", $A$3, "Region", "East")
```

Disable it: File > Options > Formulas > Use GetPivotData functions for PivotTable references.

---

## Charts

### Combination Charts

Combine column and line charts on different axes:
1. Create a column chart
2. Right-click a series > Change Series Chart Type > Line
3. Check Secondary Axis for line series

### Sparklines

Insert > Sparklines — mini charts in single cells:
- Line, Column, Win/Loss
- Customize: Sparkline color, markers, axis

### Dynamic Chart Ranges

Use named ranges with OFFSET or INDEX:
```
=OFFSET(Sheet1!$A$2, 0, 0, COUNTA(Sheet1!$A:$A)-1, 1)
```

Or use Excel Tables (structured references auto-expand):
```
=SERIES(, Table1[Date], Table1[Sales], 1)
```

---

## VBA Macros

### Recording and Editing

Record a macro: View > Macros > Record Macro. Then edit in the VBA Editor (Alt+F11).

**VBE Structure:**
- Project Explorer (Ctrl+R) — navigate modules
- Properties Window (F4) — control properties
- Immediate Window (Ctrl+G) — debug, test
- Code Window — write/edit code

### Fundamental VBA Patterns

```vba
' Loop through cells
Sub LoopCells()
    Dim cell As Range
    For Each cell In Range("A1:A100")
        If cell.Value > 100 Then
            cell.Interior.Color = vbYellow
        End If
    Next cell
End Sub

' Copy data to another sheet
Sub CopyData()
    Dim wsSource As Worksheet, wsDest As Worksheet
    Set wsSource = ThisWorkbook.Sheets("Data")
    Set wsDest = ThisWorkbook.Sheets("Report")
    
    Dim lastRow As Long
    lastRow = wsSource.Cells(wsSource.Rows.Count, 1).End(xlUp).Row
    
    wsSource.Range("A1:C" & lastRow).Copy _
        wsDest.Range("A1")
End Sub

' Error handling
Sub SafeMacro()
    On Error GoTo ErrorHandler
    Application.ScreenUpdating = False
    Application.Calculation = xlCalculationManual
    
    ' ... your code ...
    
CleanExit:
    Application.ScreenUpdating = True
    Application.Calculation = xlCalculationAutomatic
    Exit Sub
    
ErrorHandler:
    MsgBox "Error " & Err.Number & ": " & Err.Description
    Resume CleanExit
End Sub
```

### UserForms

```vba
' Show form and collect data
Private Sub btnSubmit_Click()
    Dim ws As Worksheet
    Set ws = ThisWorkbook.Sheets("Data")
    Dim nextRow As Long
    nextRow = ws.Cells(ws.Rows.Count, 1).End(xlUp).Row + 1
    
    ws.Cells(nextRow, 1).Value = txtName.Text
    ws.Cells(nextRow, 2).Value = cbCategory.Value
    ws.Cells(nextRow, 3).Value = dtpDate.Value
    ws.Cells(nextRow, 4).Value = Val(txtAmount.Text)
    
    ' Clear form
    txtName.Text = ""
    cbCategory.Value = ""
    dtpDate.Value = Date
    txtAmount.Text = ""
    txtName.SetFocus
End Sub

Private Sub UserForm_Initialize()
    ' Populate combobox
    cbCategory.List = Array("Revenue", "Expense", "Asset", "Liability")
    dtpDate.Value = Date
End Sub
```

### Event Handlers

```vba
' Worksheet Change event
Private Sub Worksheet_Change(ByVal Target As Range)
    If Target.Column = 1 Then
        ' Auto-format based on entry
        If Target.Value > 0 Then
            Target.Offset(0, 1).Value = "Active"
        Else
            Target.Offset(0, 1).Value = "Inactive"
        End If
    End If
End Sub

' Workbook Open event
Private Sub Workbook_Open()
    ' Refresh all data connections
    ThisWorkbook.RefreshAll
    
    ' Set date stamp
    ThisWorkbook.Sheets("Dashboard").Range("A1").Value = "Last Updated: " & Now()
End Sub

' Before Save event
Private Sub Workbook_BeforeSave(ByVal SaveAsUI As Boolean, Cancel As Boolean)
    ' Remove sensitive data before saving
    Sheets("TempData").Cells.Clear
End Sub
```

### Best Practices for VBA

- Always declare variables with `Dim` and use `Option Explicit`
- Turn off `ScreenUpdating`, `Calculation`, and `EnableEvents` during execution
- Use `With` blocks for repeated object references
- Avoid `Select` and `Activate` — directly reference ranges
- Use error handlers in every Sub/Function
- Name macros descriptively (e.g., `GenerateMonthlyReport`, not `Macro1`)

---

## Power Query (Get & Transform)

### M Language Basics

Power Query uses the M formula language. Every query has steps.

```
let
    Source = Excel.CurrentWorkbook(){[Name="Table1"]}[Content],
    #"Changed Type" = Table.TransformColumnTypes(Source,{{"Date", type date}, {"Amount", type number}}),
    #"Filtered Rows" = Table.SelectRows(#"Changed Type", each [Amount] > 1000),
    #"Grouped Rows" = Table.Group(#"Filtered Rows", {"Category"}, {
        {"Total Sales", each List.Sum([Amount]), type number},
        {"Count", each Table.RowCount(_), type number}
    }),
    #"Sorted" = Table.Sort(#"Grouped Rows",{{"Total Sales", Order.Descending}})
in
    #"Sorted"
```

### Common M Transformations

```powerquery
// Merge queries
let
    Source = Table.NestedJoin(SalesTable, {"ProductID"}, ProductsTable, {"ID"}, "Products", JoinKind.LeftOuter),
    Expanded = Table.ExpandTableColumn(Source, "Products", {"ProductName", "Price"}, {"ProductName", "Price"})
in
    Expanded

// Add conditional column
let
    Source = SalesTable,
    AddRating = Table.AddColumn(Source, "Rating", each
        if [Amount] > 10000 then "High"
        else if [Amount] > 5000 then "Medium"
        else "Low"
    )
in
    AddRating

// Custom function
let
    MultiplyByFactor = (value as number, factor as number) =>
        let result = value * factor in result
in
    MultiplyByFactor

// Unpivot columns
let
    Source = Table.UnpivotOtherColumns(Table1, {"Date", "Product"}, "Attribute", "Value")
in
    Source

// Date table from scratch
let
    StartDate = #date(2020, 1, 1),
    EndDate = #date(2025, 12, 31),
    DateList = List.Dates(StartDate, Duration.Days(EndDate - StartDate) + 1, #duration(1, 0, 0, 0)),
    TableFromList = Table.FromList(DateList, Splitter.SplitByNothing()),
    DateTable = Table.TransformColumnTypes(TableFromList, {{"Column1", type date}}),
    AddColumns = Table.TransformColumns(DateTable, {}, (date) =>
        [Date = date,
         Year = Date.Year(date),
         Month = Date.Month(date),
         MonthName = Date.MonthName(date),
         Quarter = Date.QuarterOfYear(date),
         DayOfWeek = Date.DayOfWeekName(date),
         WeekNumber = Date.WeekOfYear(date)]
    )
in
    AddColumns
```

### Data Transformation Best Practices

- Always promote column names from the first row when needed
- Rename steps descriptively in Applied Steps pane
- Use parameters for dynamic filtering (file paths, dates)
- Combine multiple files from a folder using the Folder connector
- Use Reference queries to avoid repeating transformations

---

## Conditional Formatting

### Formula-Based Conditional Formatting

Highlight entire row based on a cell value:
```
= $C2 > 1000
```
Apply to range: `=$A$2:$F$100`

Highlight weekends:
```
= WEEKDAY($A2, 2) > 5
```

Highlight duplicates in a range:
```
= COUNTIF($A$2:$A$100, $A2) > 1
```

Alternating row colors:
```
= MOD(ROW(), 2) = 0
```

### Color Scales and Icon Sets

- **Color Scales**: 2-color or 3-color gradients. Conditional Formatting > Color Scales.
- **Icon Sets**: Traffic lights, flags, arrows, ratings. Conditional Formatting > Icon Sets.
- Customize: Conditional Formatting > Manage Rules > Edit Rule

### Named Ranges

| Name | Refers To | Scope |
|------|-----------|-------|
| `SalesData` | `=$A$2:$F$1000` | Workbook |
| `TaxRate` | `=0.21` | Workbook |
| `MyTable` | `=OFFSET(Sheet1!$A$1,,,COUNTA(Sheet1!$A:$A),5)` | Workbook |

Create via Formulas > Name Manager (Ctrl+F3) or the Name Box.

---

## Data Validation

Settings: Data > Data Validation

| Validation | Formula |
|------------|---------|
| List from range | `=$A$2:$A$10` |
| Custom formula | `=ISNUMBER(B2)` |
| Date range | `=AND(B2>=TODAY(), B2<=EDATE(TODAY(),3))` |
| Prevent duplicates | `=COUNTIF($A$2:$A$100, A2)=1` |
| Dependent dropdown | `=INDIRECT($A2)` |

Input Message and Error Alert tabs provide user guidance.

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl + Arrow` | Navigate to edge of data region |
| `Ctrl + Shift + Arrow` | Select to edge |
| `Ctrl + Space` | Select column |
| `Shift + Space` | Select row |
| `Ctrl + T` | Create table |
| `Alt + =` | AutoSum |
| `F4` | Toggle absolute/relative reference |
| `Ctrl + ~` | Show formulas |
| `Alt + D + P` | Open PivotTable wizard |
| `Ctrl + Shift + L` | Toggle filters |
| `Ctrl + ;` | Insert current date |
| `Ctrl + Shift + :` | Insert current time |
| `F2` | Edit active cell |
| `Alt + Enter` | New line in cell |
| `Ctrl + [ ` | Go to precedent |
| `Ctrl + ]` | Go to dependent |
| `F5` | Go To |

---

## Power Pivot and DAX

### DAX Fundamentals

DAX (Data Analysis Expressions) is used in Power Pivot, Power BI, and SSAS Tabular.

**Basic DAX functions:**
```
Total Sales = SUM(Sales[Amount])
Total Quantity = SUM(Sales[Qty])
Transaction Count = COUNTROWS(Sales)
Average Price = AVERAGE(Sales[UnitPrice])
```

**Filter context and CALCULATE:**
```
Sales East Region = CALCULATE(
    SUM(Sales[Amount]),
    Customer[Region] = "East"
)

Sales Previous Year = CALCULATE(
    SUM(Sales[Amount]),
    SAMEPERIODLASTYEAR(DateTable[Date])
)
```

**Time Intelligence:**
```
Total Sales YTD = TOTALYTD(SUM(Sales[Amount]), DateTable[Date])

Total Sales QTD = TOTALQTD(SUM(Sales[Amount]), DateTable[Date])

Sales Same Period Last Year = CALCULATE(
    SUM(Sales[Amount]),
    SAMEPERIODLASTYEAR(DateTable[Date])
)

Rolling 12 Months = CALCULATE(
    SUM(Sales[Amount]),
    DATESINPERIOD(DateTable[Date], MAX(DateTable[Date]), -12, MONTH)
)
```

**Variables in DAX:**
```
YoY Growth % = 
VAR CurrentSales = SUM(Sales[Amount])
VAR PreviousSales = CALCULATE(SUM(Sales[Amount]), SAMEPERIODLASTYEAR(DateTable[Date]))
RETURN
    DIVIDE(CurrentSales - PreviousSales, PreviousSales, 0)
```

**Context Transition — SUMX and FILTER:**
```
Top Product Sales = 
CALCULATE(
    SUM(Sales[Amount]),
    FILTER(
        Product,
        Product[SalesRank] <= 10
    )
)

Running Total = 
CALCULATE(
    SUM(Sales[Amount]),
    FILTER(
        ALL(DateTable),
        DateTable[Date] <= MAX(DateTable[Date])
    )
)
```

### Data Modeling in Power Pivot

- **Star Schema**: Central fact table with dimension tables
- **Relationships**: 1-to-many from dimension to fact
- **Bidirectional filtering**: Use sparingly — may cause ambiguous relationships
- **Calculated columns** vs **Measures**: Columns are row-by-row, measures use filter context

---

## What-If Analysis

### Goal Seek

Data > What-If Analysis > Goal Seek
- Set cell: Target result cell
- To value: Desired number
- By changing cell: Input variable

### Data Tables

**One-variable data table:**
1. Set up input values in a column
2. Formula referencing input in top row
3. Data > Data Table > Column input cell

**Two-variable data table:**
1. Input values in both first row and first column
2. Formula at intersection
3. Data > Data Table > Row and Column input cells

### Solver

Add-in: File > Options > Add-ins > Excel Add-ins > Solver Add-in

Solves optimization problems:
- Objective cell (minimize, maximize, or target value)
- Variable cells
- Constraints (=, <=, >=, int, bin)

Example — Portfolio optimization:
```
Objective: Maximize Portfolio Return
Variables: Allocation percentages per asset
Constraints: Sum = 100%, Each >= 0%, Max risk <= threshold
```

---

## Best Practices

### Naming Conventions

| Item | Convention | Example |
|------|------------|---------|
| Named Range | PascalCase | `SalesData2024` |
| VBA Variable | camelCase | `lastRow` |
| VBA Constants | UPPER_SNAKE | `MAX_ITERATIONS` |
| Sheet name | Descriptive | `InputData`, `Report` |
| Table name | Prefix + Name | `tblSales`, `tblProducts` |
| Pivot name | Prefix | `ptSalesByRegion` |
| Macro name | VerbNoun | `GenerateInvoice` |

### Template Creation

Create a .xltm (macro-enabled template):
1. Build standard sheets, styles, named ranges
2. Add macro buttons and automation
3. Add data validation and conditional formatting
4. Save as Excel Template (.xltx or .xltm)

### Error Handling in Formulas

- `IFERROR(value, value_if_error)` — catches all errors
- `IF(ISERROR(...), ...)` — pre-2010 alternative
- `IFNA(value, value_if_na)` — catches #N/A only
- Use `IF(COUNTIF(...), ...)` to check existence before lookup

### Performance Tips

- Use Excel Tables (ListObjects) for dynamic data
- Avoid volatile functions (INDIRECT, OFFSET, TODAY, NOW) in large models
- Use Power Query for heavy data transformation, not formulas
- Limit conditional formatting rules to necessary ranges
- Use manual calculation mode (F9 to recalc) in large workbooks
- Convert formulas to values when source data is static
- Use Power Pivot for datasets over 1M rows

### Audit Tools

- **Trace Precedents**: Formulas > Trace Precedents (Alt+M+P)
- **Trace Dependents**: Formulas > Trace Dependents (Alt+M+D)
- **Evaluate Formula**: Formulas > Evaluate Formula (Alt+M+V)
- **Watch Window**: Formulas > Watch Window
- **Error Checking**: Formulas > Error Checking

---

## Excel for Business Workflows

### Clean Raw Data

```
1. Remove duplicates: Data > Remove Duplicates
2. Text to Columns: Data > Text to Columns (fixed width or delimited)
3. Use TRIM to clean whitespace: =TRIM(A2)
4. Use PROPER/UPPER/LOWER for text normalization
5. Find & Replace character cleanup
```

### Build a Report

```
1. Define inputs with data validation dropdowns
2. Use SUMIFS/COUNTIFS with cell references for criteria
3. Create pivot tables for summary views
4. Add conditional formatting for variance highlights
5. Build combo charts with primary/secondary axes
6. Add slicers for interactive filtering
7. Protect input sheets, leave output sheets unprotected
```

### Automation Checklist

```
[ ] Record macros for repetitive tasks
[ ] Use named ranges in VBA (Range("SalesData") not Range("A2:F100"))
[ ] Add error handling
[ ] Add progress indicators for long macros
[ ] Test on different data sizes
[ ] Add input validation
[ ] Document macros with comments
[ ] Disable events/screenupdating during execution
[ ] Always set calculation mode back to automatic
```
