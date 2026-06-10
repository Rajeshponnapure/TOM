# Power BI Skills — Mastery Guide

## Overview
Power BI is Microsoft's flagship business analytics tool. Mastery spans DAX (Data Analysis Expressions), M language (Power Query), data modeling, visual customization, deployment, and performance optimization.

---

## DAX — Data Analysis Expressions

### Core Concepts

**Filter context** — the environment of filters that apply when a measure is evaluated. Filters come from slicers, report filters, row/column context, and explicit FILTER usage.

**Row context** — exists inside calculated columns and iterator functions (SUMX, FILTER, ADDCOLUMNS). Iterates row by row.

**Context transition** — converting row context to filter context using CALCULATE. This is the most important DAX concept.

### CALCULATE (The Master Function)

CALCULATE modifies filter context. Every serious DAX measure uses it.

```
CALCULATE(<expression>, <filter1>, <filter2>, ...)
```

```dax
Total Sales = SUM(Sales[Amount])

Sales East = 
CALCULATE(
    [Total Sales],
    Customer[Region] = "East"
)

Sales High Value = 
CALCULATE(
    [Total Sales],
    Sales[Amount] > 1000
)

Sales Multiple Conditions = 
CALCULATE(
    [Total Sales],
    Customer[Region] = "East",
    Product[Category] = "Electronics"
)
```

### FILTER Function

FILTER returns a table filtered by a condition. Used inside CALCULATE for complex filtering.

```dax
Sales Top Products = 
CALCULATE(
    [Total Sales],
    FILTER(
        Product,
        Product[SalesRank] <= 10
    )
)

Sales Exclude Returns = 
CALCULATE(
    [Total Sales],
    FILTER(
        Sales,
        Sales[TransactionType] <> "Return"
    )
)
```

### ALL and ALLEXCEPT

ALL removes all filters from a table or column:
```dax
Total Sales All = CALCULATE([Total Sales], ALL(Sales))

Sales vs Total = 
DIVIDE(
    [Total Sales],
    CALCULATE([Total Sales], ALL(Product))
)
```

ALLEXCEPT removes all filters except those on specified columns:
```dax
Sales by Category Share = 
DIVIDE(
    [Total Sales],
    CALCULATE([Total Sales], ALLEXCEPT(Product, Product[Category]))
)
```

### VALUES and DISTINCT

VALUES returns unique values, including blank if present. DISTINCT returns unique values without blank.

```dax
Unique Customers = COUNTROWS(VALUES(Customer[CustomerID]))

Category List = CONCATENATEX(VALUES(Product[Category]), Product[Category], ", ")
```

### SUMMARIZE and ADDCOLUMNS

```dax
Summary Table = 
SUMMARIZE(
    Sales,
    Product[Category],
    "Total Sales", SUM(Sales[Amount]),
    "Total Qty", SUM(Sales[Quantity]),
    "Avg Price", AVERAGE(Sales[UnitPrice])
)

Product Performance = 
ADDCOLUMNS(
    Product,
    "Total Sales", CALCULATE(SUM(Sales[Amount])),
    "Rank", RANKX(ALL(Product), CALCULATE(SUM(Sales[Amount])))
)
```

### Time Intelligence

```dax
Sales YTD = TOTALYTD([Total Sales], 'Date'[Date])

Sales QTD = TOTALQTD([Total Sales], 'Date'[Date])

Sales MTD = TOTALMTD([Total Sales], 'Date'[Date])

Sales Previous Year = 
CALCULATE([Total Sales], SAMEPERIODLASTYEAR('Date'[Date]))

Sales Previous Quarter = 
CALCULATE([Total Sales], PREVIOUSQUARTER('Date'[Date]))

Sales Previous Month = 
CALCULATE([Total Sales], PREVIOUSMONTH('Date'[Date]))

Sales YoY Growth = 
VAR CurrentSales = [Total Sales]
VAR PreviousSales = CALCULATE([Total Sales], SAMEPERIODLASTYEAR('Date'[Date]))
RETURN
    DIVIDE(CurrentSales - PreviousSales, PreviousSales, 0)

Rolling 12 Months = 
CALCULATE(
    [Total Sales],
    DATESINPERIOD('Date'[Date], MAX('Date'[Date]), -12, MONTH)
)

Same Period Last Year to Date = 
CALCULATE(
    [Total Sales],
    DATESYTD(SAMEPERIODLASTYEAR('Date'[Date]))
)
```

### Context Transition

The most common source of confusion. Row context does NOT propagate to related tables automatically. Use CALCULATE to convert row context to filter context.

```dax
-- Calculated column (row context)
Product Revenue = SUMX(
    RELATEDTABLE(Sales),
    Sales[Quantity] * Sales[UnitPrice]
)

-- Using CALCULATE to transition context
Product Revenue Correct = 
CALCULATE(
    SUM(Sales[Quantity] * Sales[UnitPrice]),
    Product[ProductID] = EARLIER(Product[ProductID])
)
```

---

## DAX Patterns

### Running Total

```dax
Running Total = 
CALCULATE(
    SUM(Sales[Amount]),
    FILTER(
        ALL('Date'),
        'Date'[Date] <= MAX('Date'[Date])
    )
)
```

### Moving Average (3-month)

```dax
Moving Avg 3 Months = 
VAR PeriodEnd = MAX('Date'[Date])
VAR PeriodStart = EDATE(PeriodEnd, -2)
RETURN
    CALCULATE(
        AVERAGE(Sales[Amount]),
        DATESBETWEEN('Date'[Date], PeriodStart, PeriodEnd)
    )
```

### Parent-Child Hierarchy

For org chart depth calculation:
```dax
Depth = 
PATHLENGTH(
    Employee[EmployeeID],
    Employee[ManagerID]
)

Level 1 = 
LOOKUPVALUE(
    Employee[Name],
    Employee[EmployeeID],
    PATHITEM(Employee[Path], 1, INTEGER)
)
```

### ABC Analysis (Pareto)

```dax
Sales Rank = RANKX(ALL(Product), [Total Sales])

Cumulative Sales % = 
VAR TotalSalesAll = CALCULATE([Total Sales], ALL(Product))
VAR CumSales = 
    CALCULATE(
        [Total Sales],
        FILTER(
            ALL(Product),
            [Total Sales] >= [Total Sales]  -- descending order
        )
    )
RETURN
    DIVIDE(CumSales, TotalSalesAll)

ABC Category = 
SWITCH(
    TRUE(),
    [Cumulative Sales %] <= 0.8, "A",
    [Cumulative Sales %] <= 0.95, "B",
    "C"
)
```

### Dynamic Segmentation

```dax
Sales Segment = 
SWITCH(
    TRUE(),
    [Total Sales] < 1000, "Low",
    [Total Sales] < 5000, "Medium",
    [Total Sales] < 10000, "High",
    "Premium"
)
```

---

## Data Modeling

### Star Schema Design

```
Fact Table: Sales
    DateKey, ProductKey, CustomerKey, StoreKey, Amount, Quantity

Dimension Tables:
    Date (DateKey, Date, Year, Month, Quarter, Day of Week)
    Product (ProductKey, ProductName, Category, SubCategory, Brand)
    Customer (CustomerKey, CustomerName, Region, Segment, Channel)
    Store (StoreKey, StoreName, City, State, Country)
```

### Relationship Guidelines

| Cardinality | Usage | Performance |
|-------------|-------|-------------|
| Many-to-1 (M:1) | Fact to dimension | Best |
| 1:1 | Rare, dimension extension | Good |
| Many-to-Many (M:M) | Avoid if possible | Complex, slow |

- Always use single-direction filtering (from dimension to fact)
- Bidirectional only when necessary (with limited tables)
- Define filter context with relationships, not CALCULATE

### Date Table Requirements

A proper date table must:
- Have every date in the date range
- Have one row per day
- Be marked as a date table: Table Tools > Mark as Date Table

Create it with DAX:
```dax
DateTable = 
CALENDAR(
    DATE(2018, 1, 1),
    DATE(2026, 12, 31)
)
```

Add columns:
```dax
Year = YEAR('DateTable'[Date])
Month = MONTH('DateTable'[Date])
MonthName = FORMAT('DateTable'[Date], "MMMM")
Quarter = QUARTER('DateTable'[Date])
QuarterLabel = "Q" & FORMAT('DateTable'[Date], "Q")
Weekday = WEEKDAY('DateTable'[Date], 2)  -- Monday=1
WeekdayName = FORMAT('DateTable'[Date], "dddd")
WeekNumber = WEEKNUM('DateTable'[Date], 2)
IsWeekend = WEEKDAY('DateTable'[Date], 2) > 5
YearMonth = FORMAT('DateTable'[Date], "YYYY-MM")
```

---

## M Language (Power Query)

### Basic Transformations

```powerquery
let
    Source = Excel.Workbook(File.Contents("C:\Data\Sales.xlsx"), null, true),
    SalesTable = Source{[Item="Sales",Kind="Sheet"]}[Data],
    
    // Promote headers
    PromoteHeaders = Table.PromoteHeaders(SalesTable, [PromoteAllScalars=true]),
    
    // Change types
    TypedTable = Table.TransformColumnTypes(PromoteHeaders, {
        {"Date", type date},
        {"Amount", type number},
        {"Quantity", Int64.Type},
        {"Product", type text}
    }),
    
    // Filter rows
    FilteredRows = Table.SelectRows(TypedTable, each [Amount] > 0),
    
    // Add conditional column
    AddCategory = Table.AddColumn(FilteredRows, "Category", each
        if [Amount] > 10000 then "High"
        else if [Amount] > 5000 then "Medium"
        else "Low"
    ),
    
    // Remove empty rows
    RemoveEmpty = Table.SelectRows(AddCategory, each [Product] <> null)
in
    RemoveEmpty
```

### Merging Queries

```powerquery
let
    SalesSource = Excel.Workbook(File.Contents("C:\Data\Sales.xlsx"), null, true),
    SalesTable = SalesSource{[Item="Sales",Kind="Sheet"]}[Data],
    SalesPromoted = Table.PromoteHeaders(SalesTable, [PromoteAllScalars=true]),
    
    ProductSource = Excel.Workbook(File.Contents("C:\Data\Products.xlsx"), null, true),
    ProductTable = ProductSource{[Item="Products",Kind="Sheet"]}[Data],
    ProductPromoted = Table.PromoteHeaders(ProductTable, [PromoteAllScalars=true]),
    
    // Merge (SQL LEFT JOIN equivalent)
    MergedTables = Table.NestedJoin(
        SalesPromoted, {"ProductID"},
        ProductPromoted, {"ID"},
        "ProductDetails",
        JoinKind.LeftOuter
    ),
    
    // Expand merged columns
    Expanded = Table.ExpandTableColumn(
        MergedTables,
        "ProductDetails",
        {"ProductName", "Category", "Price"},
        {"ProductName", "Category", "Price"}
    )
in
    Expanded
```

### Custom Functions

```powerquery
// Custom function to compute discount
let
    ApplyDiscount = (price as number, discount as number) as number =>
        let
            discounted = price * (1 - discount)
        in
            discounted,
    
    // Use the function
    Source = SalesTable,
    AddDiscounted = Table.AddColumn(Source, "DiscountedPrice", 
        each ApplyDiscount([Price], 0.1), 
        type number
    )
in
    AddDiscounted
```

### Parameters

Create parameters in Power Query: Manage Parameters > New Parameter

```powerquery
// Using a parameter for dynamic filtering
let
    Source = Sql.Database("server", "database"),
    Sales = Source{[Schema="dbo",Item="Sales"]}[Data],
    
    FilterByYear = Table.SelectRows(Sales, each [Year] >= YearParameter)
in
    FilterByYear
```

### Advanced M Techniques

```powerquery
// Unpivot columns (pivot to normal form)
let
    Source = PivotTable,
    Unpivoted = Table.UnpivotOtherColumns(Source, {"Date", "Product"}, "Attribute", "Value")
in
    Unpivoted

// Group and aggregate
let
    Source = SalesTable,
    Grouped = Table.Group(Source, {"Category"}, {
        {"Total Sales", each List.Sum([Amount]), type number},
        {"Average", each List.Average([Amount]), type number},
        {"Count", each Table.RowCount(_), type number},
        {"Max", each List.Max([Amount]), type number},
        {"Min", each List.Min([Amount]), type number}
    })
in
    Grouped

// Combine multiple files from folder
let
    Source = Folder.Files("C:\Data\Sales\"),
    Filtered = Table.SelectRows(Source, each Text.EndsWith([Name], ".xlsx")),
    Imported = Table.AddColumn(Filtered, "Data", each 
        Excel.Workbook(File.Contents([FullPath]), null, true)
    ),
    Expanded = Table.ExpandTableColumn(Imported, "Data", {"Data"}),
    Promoted = Table.PromoteHeaders(Expanded[Data])
in
    Promoted
```

---

## Visual Customization

### Custom Visuals

Get custom visuals: AppSource (built-in) or download .pbiviz files.

Popular custom visuals:
- **Charticulator**: Drag-and-drop custom chart builder
- **Advanced Card**: Custom KPI cards
- **Tornado Chart**: Sensitivity/comparison
- **Beyondsoft Calendar**: Calendar heatmap
- **Hierarchy Slicer**: Hierarchical filtering
- **Enlighten Data Story**: Narrative summaries
- **HTML Content**: Render HTML/JS in reports

### Charticulator

1. Get from AppSource
2. Drop Charticulator visual on report canvas
3. Drag fields to Glyph, X, Y, Color, etc.
4. Customize: axes, legends, shapes, scales
5. Export as SVG for custom visuals

### Report Themes

JSON-based theme files control all visual defaults.

```json
{
  "name": "Corporate Theme",
  "dataColors": ["#0072B5", "#ED7D31", "#A5A5A5", "#FFC000", "#4472C4", "#70AD47"],
  "background": "#FFFFFF",
  "foreground": "#333333",
  "tableAccent": "#0072B5",
  "visualStyles": {
    "*": {
      "*": {
        "background": [{ "solid": { "color": "#F5F5F5" } }],
        "border": [{ "show": false }],
        "fontFamily": "Segoe UI",
        "title": [{ "fontSize": 14 }]
      }
    },
    "columnChart": {
      "*": {
        "dataPointStyle": [{ "fontSize": 10 }]
      }
    }
  }
}
```

### Bookmarks and Buttons

Bookmarks capture the state of the report page:
1. Set slicers, filters, visual visibility
2. View > Bookmarks > Add
3. Create buttons to navigate bookmarks

Button actions:
- **Back**: Navigate to previous bookmark
- **Bookmark**: Navigate to specific bookmark
- **Page Navigation**: Go to different page
- **Drill**: Drill through to another page
- **Q&A**: Open Q&A

### Drill Through

1. Create detail page with relevant visuals
2. Set drill-through fields on the detail page
3. Right-click data point > Drill Through

---

## Performance Optimization

### VertiPaq Engine

Power BI's in-memory columnar storage engine.

**Optimization principles:**
- Reduce cardinality of columns (fewer unique values)
- Split high-cardinality columns (e.g., store full datetime as separate Date + Time)
- Disable Auto Date/Time for large models (File > Options > Global > Time Intelligence)
- Use integer keys instead of text for relationships
- Avoid columns with many distinct values in fact tables

### Storage Mode

| Mode | Description | Use Case |
|------|-------------|----------|
| Import | All data in memory (default) | Best performance |
| DirectQuery | Query source directly | Real-time, large data |
| Dual | Both modes | Hybrid, composite models |
| Composite | Mix of Import and DirectQuery | Enterprise BI |

### Model Size Reduction

- Remove unused columns
- Remove unused tables
- Reduce row count (filter at source)
- Use aggregation tables for large fact tables
- Disable Auto-Date/Time globally
- Split DateTime into separate Date and Time columns

### Aggregations

Create aggregation tables for large datasets:

1. Create aggregated table in Power Query
2. Set storage mode to Import
3. Define aggregations: Manage Aggregations
4. Configure them to respond to queries at different grain

### Incremental Refresh

Configure in Power Query:
1. Enable incremental refresh: Table properties > Incremental refresh
2. Set range boundaries (e.g., 5 years full + 30 days incremental)
3. Set refresh policy in Power BI Service

### DAX Performance

```dax
-- BAD: Row-by-row iteration
Slow Measure = 
SUMX(
    Sales,
    Sales[Quantity] * RELATED(Product[Price])
)

-- GOOD: Single table operation with calculated column
Fast Measure = SUM(Sales[LineTotal])  
-- where LineTotal is a calculated column in Sales table

-- BAD: Nested iterators
Very Slow = 
SUMX(
    FILTER(Sales, Sales[Year] = 2024),
    Sales[Quantity] * RELATED(Product[Price])
)

-- BETTER: Push filters into measures
Better = 
CALCULATE(
    SUMX(Sales, Sales[Quantity] * RELATED(Product[Price])),
    Sales[Year] = 2024
)
```

### Performance Analyzer

View > Performance Analyzer
- Records duration of each visual
- Identifies slowest queries
- Shows DAX query text for optimization
- Start Recording > Refresh visuals > Analyze

---

## Row-Level Security (RLS)

### Creating Roles

Modeling > Manage Roles > New

**Static RLS:**
```dax
[Region] = "East"
```

**Dynamic RLS (based on user email):**
```dax
[SalespersonEmail] = USERPRINCIPALNAME()
```

**Manager hierarchy RLS:**
```dax
-- Employee table has: EmployeeID, ManagerID, Email
VAR CurrentUserEmail = USERPRINCIPALNAME()
VAR UserEmployeeID = LOOKUPVALUE(Employee[EmployeeID], Employee[Email], CurrentUserEmail)
VAR AllSubordinates = 
    FILTER(
        Employee,
        PATHCONTAINS(PATH(Employee[EmployeeID], Employee[ManagerID]), UserEmployeeID)
    )
RETURN
    Employee[EmployeeID] IN AllSubordinates
```

### Validating RLS

View as Role: Modeling > View As > Select role > OK

### Testing RLS

Use `USERNAME()` or `USERPRINCIPALNAME()` in DAX measures:
```dax
Current User Test = USERPRINCIPALNAME()
```

---

## Deployment

### Workspaces

- **My Workspace**: Personal scratchpad
- **Workspaces**: Collaboration and deployment
  - Development → Test → Production workspaces
  - Assign role: Admin, Member, Contributor, Viewer

### Deployment Pipelines

1. Create pipeline: https://app.powerbi.com > Deployment pipelines
2. Assign workspaces to stages (Dev, Test, Prod)
3. Deploy: Compare > Deploy
4. Set deployment rules (data source, parameters per stage)

### Power BI Apps

Publish reports as an App:
1. Create or open a workspace
2. Create App button
3. Select content (reports, dashboards, datasets)
4. Set permissions (entire org or specific users/groups)
5. Publish App

---

## Paginated Reports

Paginated Reports (SSRS-based, Power BI Premium):
- Pixel-perfect reports
- Print-ready (PDF, Word, Excel, etc.)
- Row-by-row rendering

Create with Power BI Report Builder.

**Parameters:**
- Date range, product category, region
- Cascading parameters (region depends on country)

**Expressions:**
```vb
=Sum(Fields!Sales.Value)
=IIF(Fields!Amount.Value > 1000, "High", "Low")
=Format(Fields!Date.Value, "MMMM yyyy")
```

---

## Embedded Analytics

Embed Power BI in applications:
- **Embed for your organization**: Users need Power BI license
- **Embed for your customers**: ISV embedding, App owns data

**Power BI Embedded (Azure):**
- Capacity-based pricing (A, EM, P SKUs)
- REST APIs and PowerShell for management
- JavaScript SDK for embedding

```javascript
// Embed report with JavaScript SDK
const embedConfig = {
  type: 'report',
  id: 'report-id',
  embedUrl: 'https://app.powerbi.com/reportEmbed?reportId=...',
  tokenType: models.TokenType.Embed,
  accessToken: 'embed-token',
  settings: {
    filterPaneEnabled: false,
    navContentPaneEnabled: true
  }
};

const report = powerbi.embed(embedContainer, embedConfig);
```

---

## Composite Models

Combining Import and DirectQuery:
1. Create composite model in Power BI Desktop
2. Add some tables via Import, others via DirectQuery
3. Define relationships across modes
4. Set storage mode per table

Limitations:
- Many-to-many relationships not supported across sources
- Some DAX functions restricted in DirectQuery mode
- Performance depends on source query speed

---

## Calculation Groups

Calculation groups reduce redundant measures. Create in Tabular Editor (external tool):

```xml
<CalculationGroup>
  <Name>Time Intelligence</Name>
  <CalculationItem>
    <Name>Current Period</Name>
    <Expression>SELECTEDMEASURE()</Expression>
  </CalculationItem>
  <CalculationItem>
    <Name>Same Period Last Year</Name>
    <Expression>
      CALCULATE(SELECTEDMEASURE(), SAMEPERIODLASTYEAR('Date'[Date]))
    </Expression>
  </CalculationItem>
  <CalculationItem>
    <Name>YTD</Name>
    <Expression>
      CALCULATE(SELECTEDMEASURE(), DATESYTD('Date'[Date]))
    </Expression>
  </CalculationItem>
  <CalculationItem>
    <Name>YoY Growth %</Name>
    <Expression>
      VAR Current = SELECTEDMEASURE()
      VAR Previous = CALCULATE(SELECTEDMEASURE(), SAMEPERIODLASTYEAR('Date'[Date]))
      RETURN DIVIDE(Current - Previous, Previous)
    </Expression>
  </CalculationItem>
</CalculationGroup>
```

---

## Field Parameters

Create dynamic axes/measures selected by users:
1. Modeling > New Parameter > Fields
2. Add fields to parameter
3. Add slicer with parameter
4. Use parameter in visual field wells

---

## What-If Parameters

Modeling > New Parameter > Numeric Range

Creates a table with a single value. Use in measures:
```dax
Projected Sales = 
SUM(Sales[Amount]) * (1 + 'WhatIf Parameter'[WhatIf Parameter Value])
```

---

## External Tools

| Tool | Purpose |
|------|---------|
| **DAX Studio** | DAX query, performance, tracing |
| **Tabular Editor** | Advanced model editing (calculation groups, perspectives) |
| **ALM Toolkit** | Application lifecycle management, compare/merge |
| **Power BI Helper** | Model documentation, size analysis |
| **Bravo** | Data modeling, date table creation |
| **Analyze in Excel** | Pivot with Power BI data in Excel |

---

## Best Practices Summary

```
Design
    [ ] Star schema (fact + dimensions)
    [ ] Proper date table
    [ ] Consistent naming (Prefix: dim_, fact_, vDim_)
    [ ] Single-direction relationships

DAX
    [ ] Use CALCULATE for context modification
    [ ] Prefer SUM/SUMX over iterators when possible
    [ ] Use variables (VAR) for readability and performance
    [ ] Avoid bidirectional filtering unless necessary
    [ ] Test with Performance Analyzer

Development
    [ ] Use parameters for dynamic filtering
    [ ] Document measures with descriptions
    [ ] Create measure folders in Display Folders
    [ ] Use field parameters for user-driven axes
    [ ] Implement RLS early in development

Deployment
    [ ] Use deployment pipelines
    [ ] Set refresh schedules
    [ ] Monitor dataset refresh history
    [ ] Use gateway for on-premises data
    [ ] Enable incremental refresh for large data
```
