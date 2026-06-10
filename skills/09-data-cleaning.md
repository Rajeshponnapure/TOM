# Data Cleaning — Comprehensive Skill Guide

## Table of Contents
1. Handling Missing Data
2. Outlier Detection (IQR, Z-Score, Isolation Forest, DBSCAN)
3. Duplicate Detection
4. Data Validation
5. String Cleaning
6. Date/Time Standardization
7. Categorical Encoding
8. Data Normalization / Standardization
9. Data Quality Metrics
10. Automated Cleaning Pipelines

---

## 1. Handling Missing Data

### Types of Missing Data

| Type | Description | Example | Treatment |
|------|-------------|---------|-----------|
| MCAR | Missing Completely At Random | Survey respondent accidentally skips a question | Listwise deletion safe |
| MAR | Missing At Random | Women less likely to report income | Imputation valid |
| MNAR | Missing Not At Random | People with high income don't report it | Must model missingness |

### Detection

```python
import pandas as pd
import numpy as np
import missingno as msno

# Visualize missing patterns
msno.matrix(df)
msno.heatmap(df)
msno.dendrogram(df)

# Summary statistics
def missing_summary(df):
    summary = pd.DataFrame({
        'missing_count': df.isnull().sum(),
        'missing_pct': df.isnull().sum() / len(df) * 100,
        'dtype': df.dtypes,
        'unique_values': df.nunique(),
    })
    return summary[summary['missing_count'] > 0].sort_values('missing_pct', ascending=False)

# Correlation of missingness
def missing_correlation(df):
    return df.isnull().corr()
```

### Imputation Strategies

```python
from sklearn.impute import SimpleImputer, KNNImputer
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer

# Simple imputation
# Numerical: mean, median, mode, constant
df['age'].fillna(df['age'].median(), inplace=True)
df['income'].fillna(df['income'].mean(), inplace=True)

# Categorical: mode, constant
df['category'].fillna(df['category'].mode()[0], inplace=True)
df['status'].fillna('unknown', inplace=True)

# Forward/backward fill (time series)
df['value'].ffill(inplace=True)   # Last observation carried forward
df['value'].bfill(inplace=True)   # Next observation carried backward
df['value'].interpolate(method='linear', inplace=True)
df['value'].interpolate(method='time', inplace=True)

# Value-based imputation
df['outlier_flag'].fillna(False, inplace=True)

# Scikit-learn imputers
imputer = SimpleImputer(strategy='median')
X_imputed = imputer.fit_transform(X)

# KNN Imputation (uses similar rows)
knn_imputer = KNNImputer(n_neighbors=5, weights='distance')
X_knn = knn_imputer.fit_transform(X)

# MICE (Multiple Imputation by Chained Equations)
mice_imputer = IterativeImputer(
    max_iter=10,
    random_state=42,
    sample_posterior=True,  # For proper uncertainty estimation
)
X_mice = mice_imputer.fit_transform(X)

# Indicator column (informative missingness)
df['age_missing'] = df['age'].isnull().astype(int)
df['age'].fillna(df['age'].median(), inplace=True)
```

---

## 2. Outlier Detection

### IQR Method

```python
def detect_outliers_iqr(df, column, multiplier=1.5):
    Q1 = df[column].quantile(0.25)
    Q3 = df[column].quantile(0.75)
    IQR = Q3 - Q1

    lower_bound = Q1 - multiplier * IQR
    upper_bound = Q3 + multiplier * IQR

    outliers = df[(df[column] < lower_bound) | (df[column] > upper_bound)]
    return outliers, lower_bound, upper_bound

# Adaptive multiplier based on distribution
def adaptive_iqr(df, column):
    skewness = df[column].skew()
    if abs(skewness) > 1:
        multiplier = 3.0  # More permissive for skewed data
    else:
        multiplier = 1.5  # Standard for normal distributions
    return detect_outliers_iqr(df, column, multiplier)
```

### Z-Score Method

```python
from scipy import stats

def detect_outliers_zscore(df, column, threshold=3):
    z_scores = np.abs(stats.zscore(df[column].dropna()))
    outlier_mask = z_scores > threshold
    outliers = df.loc[df[column].dropna().index[outlier_mask]]
    return outliers

# Modified Z-Score (more robust)
def detect_outliers_modified_zscore(df, column, threshold=3.5):
    median = df[column].median()
    mad = np.median(np.abs(df[column] - median))
    modified_z = 0.6745 * (df[column] - median) / mad
    outlier_mask = np.abs(modified_z) > threshold
    return df[outlier_mask]
```

### Isolation Forest

```python
from sklearn.ensemble import IsolationForest

def detect_outliers_isolation_forest(
    df,
    contamination='auto',
    n_estimators=100,
    random_state=42,
):
    iso_forest = IsolationForest(
        contamination=contamination,  # Expected proportion of outliers
        n_estimators=n_estimators,
        random_state=random_state,
        n_jobs=-1,
    )

    predictions = iso_forest.fit_predict(df.select_dtypes(include=[np.number]))
    outlier_mask = predictions == -1

    return df[outlier_mask]
```

### DBSCAN

```python
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

def detect_outliers_dbscan(df, eps=0.5, min_samples=5):
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df.select_dtypes(include=[np.number]))

    clustering = DBSCAN(
        eps=eps,
        min_samples=min_samples,
        n_jobs=-1,
    ).fit(X_scaled)

    # Points labeled -1 are outliers
    outlier_mask = clustering.labels_ == -1
    return df[outlier_mask]
```

### Outlier Treatment

```python
def treat_outliers(df, column, method='clip'):
    if method == 'clip':
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - 1.5 * IQR
        upper = Q3 + 1.5 * IQR
        df[column] = df[column].clip(lower, upper)

    elif method == 'winsorize':
        from scipy.stats.mstats import winsorize
        df[column] = winsorize(df[column], limits=[0.01, 0.01])

    elif method == 'remove':
        outliers, lower, upper = detect_outliers_iqr(df, column)
        df.drop(outliers.index, inplace=True)

    elif method == 'cap_percentile':
        lower = df[column].quantile(0.01)
        upper = df[column].quantile(0.99)
        df[column] = df[column].clip(lower, upper)
```

---

## 3. Duplicate Detection

### Exact Duplicates

```python
# Exact row duplicates
exact_dupes = df[df.duplicated(keep='first')]
exact_count = df.duplicated(keep='first').sum()

# Column-specific duplicates
email_dupes = df[df.duplicated(subset=['email'], keep='first')]
composite_dupes = df[df.duplicated(subset=['user_id', 'date', 'amount'], keep=False)]
```

### Fuzzy Duplicates

```python
from rapidfuzz import fuzz, process
from itertools import combinations

def find_fuzzy_duplicates(
    series,
    threshold=85,
    scorer=fuzz.token_sort_ratio,
):
    """Find near-duplicate strings in a series."""
    pairs = []
    scores = []

    # Only compare within blocks to reduce O(n²)
    # Use first letter, soundex, or other blocking key
    series_clean = series.str.lower().str.strip()

    for (i1, s1), (i2, s2) in combinations(series_clean.items(), 2):
        score = scorer(s1, s2)
        if score >= threshold:
            pairs.append((i1, i2))
            scores.append(score)

    return pd.DataFrame({
        'idx_1': [p[0] for p in pairs],
        'idx_2': [p[1] for p in pairs],
        'similarity': scores,
    }).sort_values('similarity', ascending=False)

# Deduplication decision
def deduplicate_fuzzy(df, key_column, threshold=85):
    duplicates = find_fuzzy_duplicates(df[key_column], threshold)

    # Group similar records
    from scipy.cluster.hierarchy import fcluster, linkage
    # ... clustering logic for transitivity
```

### Record Linkage

```python
import recordlinkage

# Indexing (blocking)
indexer = recordlinkage.Index()
indexer.block('postal_code')
pairs = indexer.index(df_a, df_b)

# Comparison
compare = recordlinkage.Compare()
compare.string('name', 'name', method='jarowinkler', threshold=0.85)
compare.string('address', 'address', method='levenshtein', threshold=0.8)
compare.exact('phone', 'phone')
compare.date('dob', 'dob')

features = compare.compute(pairs, df_a, df_b)

# Classification
matches = features[features.sum(axis=1) > 3]
```

---

## 4. Data Validation

### Schema Validation

```python
from pandera import DataFrameSchema, Column, Check, io
import pandera as pa

# Define schema
schema = DataFrameSchema(
    columns={
        'user_id': Column(int, checks=[
            Check.greater_than(0),
            Check(lambda x: x.notnull(), element_wise=False),
        ]),
        'email': Column(str, checks=[
            Check.str_matches(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
        ]),
        'age': Column(float, checks=[
            Check.in_range(0, 120),
            Check(lambda s: s.fillna(0) >= 0),
        ], nullable=True),
        'signup_date': Column(
            pd.DatetimeTZDtype(tz='UTC'),
            checks=[
                Check.less_than(pd.Timestamp.now(tz='UTC')),
            ],
        ),
        'status': Column(str, checks=[
            Check.isin(['active', 'inactive', 'banned']),
        ]),
        'revenue': Column(float, checks=[
            Check.greater_than_or_equal_to(0),
            Check(lambda s: s.notnull()),
        ]),
    },
    index=pa.Index(int),
    strict=True,  # Reject extra columns
)

# Validate
validated_df = schema.validate(df)

# Get validation errors
try:
    schema.validate(df, lazy=True)
except pa.errors.SchemaErrors as e:
    print(e.failure_cases)
```

### Great Expectations

```python
import great_expectations as gx

# Create expectation suite
suite = gx.dataset.PandasDataset(df)
suite.expect_column_values_to_not_be_null('user_id')
suite.expect_column_values_to_be_unique('email')
suite.expect_column_values_to_be_between('age', 0, 120)
suite.expect_column_values_to_be_in_set('status', ['active', 'inactive'])
suite.expect_column_to_exist('revenue')
suite.expect_column_values_to_be_of_type('signup_date', 'datetime64[ns]')

# Validation
results = suite.validate()
assert results['success'], "Data validation failed!"
```

### Custom Validation Rules

```python
def validate_dataset(df, rules):
    errors = []

    for rule in rules:
        try:
            if rule['type'] == 'not_null':
                null_count = df[rule['column']].isnull().sum()
                if null_count > rule.get('max_nulls', 0):
                    errors.append(f"{rule['column']}: {null_count} nulls")

            elif rule['type'] == 'unique':
                dup_count = df[rule['column']].duplicated().sum()
                if dup_count > rule.get('max_dupes', 0):
                    errors.append(f"{rule['column']}: {dup_count} duplicates")

            elif rule['type'] == 'range':
                violations = ~df[rule['column']].between(rule['min'], rule['max'])
                if violations.any():
                    errors.append(f"{rule['column']}: values outside [{rule['min']}, {rule['max']}]")

            elif rule['type'] == 'referential_integrity':
                fk_values = set(df[rule['column']].dropna())
                pk_values = set(rule['reference_df'][rule['reference_column']])
                orphans = fk_values - pk_values
                if orphans:
                    errors.append(f"{rule['column']}: {len(orphans)} orphan values")

            elif rule['type'] == 'distribution':
                # Check for distribution shift using KS test
                from scipy import stats
                stat, p = stats.ks_2samp(
                    df[rule['column']],
                    rule['reference']  # Historical reference distribution
                )
                if p < rule.get('alpha', 0.05):
                    errors.append(f"{rule['column']}: distribution shift detected (p={p:.4f})")

        except Exception as e:
            errors.append(f"{rule['column']}: validation failed — {e}")

    return errors
```

---

## 5. String Cleaning

### Regex Patterns

```python
import re

# Common cleaning patterns
def clean_text(text):
    if not isinstance(text, str):
        return ''

    text = text.lower().strip()
    text = re.sub(r'\s+', ' ', text)         # Normalize whitespace
    text = re.sub(r'[^\w\s@\.\-]', '', text)  # Keep word chars, @, ., -
    text = re.sub(r'https?://\S+', '', text)  # Remove URLs
    text = re.sub(r'\S+@\S+', '', text)       # Remove emails
    text = re.sub(r'\d+', '', text)           # Remove numbers
    return text.strip()

# Apply to column
df['clean_text'] = df['raw_text'].apply(clean_text)
```

### Normalization

```python
import unicodedata

def normalize_unicode(text):
    """Normalize Unicode characters (accents, special chars)."""
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ASCII', 'ignore').decode('ASCII')
    return text

# Company name normalization
def normalize_company(name):
    name = str(name).lower().strip()
    name = re.sub(r'\b(inc|ltd|llc|corp|gmbh|co|company)\b\.?', '', name)
    name = re.sub(r'[^a-z0-9\s]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    name = normalize_unicode(name)
    return name

# Address standardization
def standardize_address(address):
    address = address.lower().strip()
    replacements = {
        r'\bst\b': 'street',
        r'\bave\b': 'avenue',
        r'\bblvd\b': 'boulevard',
        r'\brd\b': 'road',
        r'\bdr\b': 'drive',
        r'\bapt\b': 'apartment',
        r'\bste\b': 'suite',
    }
    for pattern, replacement in replacements.items():
        address = re.sub(pattern, replacement, address)
    return address
```

### Fuzzy Matching

```python
from rapidfuzz import fuzz

def best_match(value, choices, scorer=fuzz.token_sort_ratio, threshold=80):
    """Find best match for a value in a list of choices."""
    best_score = 0
    best_match = None

    for choice in choices:
        score = scorer(value, choice)
        if score > best_score:
            best_score = score
            best_match = choice

    return best_match if best_score >= threshold else None, best_score

# Batch matching
def match_to_master(df, column, master_list, threshold=85):
    matches = df[column].apply(
        lambda x: best_match(x, master_list, threshold=threshold)
    )
    return pd.DataFrame(matches.tolist(), columns=['master_value', 'score'])
```

---

## 6. Date/Time Standardization

```python
import pandas as pd

# Parse mixed formats
def parse_dates(series):
    """Parse a series with mixed date formats."""
    # Try common formats
    formats = [
        '%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y',
        '%Y-%m-%d %H:%M:%S', '%m/%d/%Y %I:%M %p',
        '%Y%m%d', '%d-%b-%Y', '%B %d, %Y',
    ]

    parsed = pd.to_datetime(series, format=None, errors='coerce', infer_datetime_format=True)
    if parsed.isna().sum() < series.isna().sum() * 0.1:
        return parsed

    # Fallback: custom parser for remaining
    for fmt in formats:
        mask = parsed.isna()
        parsed[mask] = pd.to_datetime(series[mask], format=fmt, errors='coerce')

    return parsed

# Extract features
def extract_date_features(df, date_column):
    dates = pd.to_datetime(df[date_column])

    df[f'{date_column}_year'] = dates.dt.year
    df[f'{date_column}_month'] = dates.dt.month
    df[f'{date_column}_day'] = dates.dt.day
    df[f'{date_column}_dayofweek'] = dates.dt.dayofweek
    df[f'{date_column}_quarter'] = dates.dt.quarter
    df[f'{date_column}_is_weekend'] = dates.dt.dayofweek.isin([5, 6]).astype(int)
    df[f'{date_column}_hour'] = dates.dt.hour
    df[f'{date_column}_minute'] = dates.dt.minute
    df[f'{date_column}_is_month_start'] = dates.dt.is_month_start
    df[f'{date_column}_is_month_end'] = dates.dt.is_month_end

    return df

# Timezone handling
def standardize_timezone(series, source_tz='US/Eastern', target_tz='UTC'):
    return pd.to_datetime(series).dt.tz_localize(source_tz, ambiguous='NaT').dt.tz_convert(target_tz)
```

---

## 7. Categorical Encoding

```python
from sklearn.preprocessing import LabelEncoder, TargetEncoder

# One-hot encoding
one_hot = pd.get_dummies(df['category'], prefix='cat', drop_first=True)

# Label encoding
le = LabelEncoder()
df['category_encoded'] = le.fit_transform(df['category'])

# Target encoding (with smoothing to prevent overfitting)
def target_encode_with_cv(df, feature, target, n_folds=5, random_state=42):
    from sklearn.model_selection import KFold

    df = df.copy()
    df['target_encoded'] = np.nan
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=random_state)
    prior = df[target].mean()

    for train_idx, val_idx in kf.split(df):
        train = df.iloc[train_idx]
        val = df.iloc[val_idx]

        encodings = train.groupby(feature)[target].mean()
        df.loc[val_idx, 'target_encoded'] = val[feature].map(encodings)

    # Fill unseen categories
    df['target_encoded'].fillna(prior, inplace=True)

    return df

# Ordinal encoding
ordinal_mapping = {'low': 0, 'medium': 1, 'high': 2}
df['priority_encoded'] = df['priority'].map(ordinal_mapping)

# Frequency encoding
freq = df['category'].value_counts(normalize=True)
df['category_freq'] = df['category'].map(freq)

# Count encoding
counts = df['category'].value_counts()
df['category_count'] = df['category'].map(counts)
```

---

## 8. Data Normalization / Standardization

```python
from sklearn.preprocessing import StandardScaler, MinMaxScaler, RobustScaler, PowerTransformer

# Standardization (Z-score)
scaler = StandardScaler()
df['age_scaled'] = scaler.fit_transform(df[['age']])

# Min-Max scaling (to [0, 1])
mm_scaler = MinMaxScaler(feature_range=(0, 1))
df['income_scaled'] = mm_scaler.fit_transform(df[['income']])

# Robust scaling (median, IQR)
robust_scaler = RobustScaler(quantile_range=(25, 75))
df['spending_scaled'] = robust_scaler.fit_transform(df[['spending']])

# Power transform (make data more Gaussian)
pt = PowerTransformer(method='yeo-johnson')  # or 'box-cox'
df['skewed_feature'] = pt.fit_transform(df[['skewed_feature']])

# Log transform (for positive skewed data)
df['revenue_log'] = np.log1p(df['revenue'])

# Rank transform
df['revenue_rank'] = df['revenue'].rank(method='average', pct=True)
```

---

## 9. Data Quality Metrics

```python
def data_quality_report(df):
    """Comprehensive data quality report."""
    n_rows, n_cols = df.shape
    total_cells = n_rows * n_cols
    filled_cells = df.notna().sum().sum()
    completeness = filled_cells / total_cells * 100

    report = {
        'dataset_info': {
            'rows': n_rows,
            'columns': n_cols,
            'memory_usage_mb': df.memory_usage(deep=True).sum() / 1024 / 1024,
        },
        'completeness': {
            'score': completeness,
            'total_cells': total_cells,
            'missing_cells': total_cells - filled_cells,
            'columns_with_missing': (df.isnull().sum() > 0).sum(),
        },
        'uniqueness': {
            'duplicate_rows': df.duplicated().sum(),
            'duplicate_rate': df.duplicated().sum() / n_rows * 100,
        },
        'column_report': {},
    }

    for col in df.columns:
        col_report = {
            'dtype': str(df[col].dtype),
            'missing_pct': df[col].isnull().mean() * 100,
            'unique_values': df[col].nunique(),
            'unique_rate': df[col].nunique() / n_rows * 100,
        }

        if pd.api.types.is_numeric_dtype(df[col]):
            col_report.update({
                'mean': df[col].mean(),
                'std': df[col].std(),
                'min': df[col].min(),
                'max': df[col].max(),
                'zeros_pct': (df[col] == 0).mean() * 100,
                'negative_pct': (df[col] < 0).mean() * 100,
            })

        report['column_report'][col] = col_report

    return report
```

---

## 10. Automated Cleaning Pipelines

```python
class DataCleaningPipeline:
    def __init__(self, config=None):
        self.config = config or {}
        self.steps = []

    def add_step(self, name, func, **kwargs):
        self.steps.append({'name': name, 'func': func, 'params': kwargs})
        return self

    def run(self, df, verbose=True):
        results = {}

        for step in self.steps:
            if verbose:
                print(f"Running: {step['name']}...")

            try:
                df, step_results = step['func'](df, **step['params'])
                results[step['name']] = {'success': True, 'details': step_results}
            except Exception as e:
                results[step['name']] = {'success': False, 'error': str(e)}
                if self.config.get('stop_on_error', True):
                    raise

        return df, results

# Build pipeline
pipeline = DataCleaningPipeline({'stop_on_error': False})

@pipeline.add_step
def remove_duplicates(df, subset=None):
    before = len(df)
    df = df.drop_duplicates(subset=subset, keep='first')
    return df, {'rows_before': before, 'rows_after': len(df), 'removed': before - len(df)}

@pipeline.add_step
def impute_missing(df, strategy='median', max_null_pct=50):
    details = {}
    for col in df.columns:
        null_pct = df[col].isnull().mean() * 100
        if null_pct == 0:
            continue
        if null_pct > max_null_pct:
            details[col] = f'dropped ({null_pct:.1f}% null)'
            df.drop(columns=[col], inplace=True)
        elif df[col].dtype in ['float64', 'int64']:
            fill_val = df[col].median() if strategy == 'median' else df[col].mean()
            df[col].fillna(fill_val, inplace=True)
            details[col] = f'imputed with {strategy} ({null_pct:.1f}% null)'
        else:
            df[col].fillna(df[col].mode()[0], inplace=True)
            details[col] = f'imputed with mode ({null_pct:.1f}% null)'

    return df, details

@pipeline.add_step
def remove_outliers(df, columns=None, method='iqr', multiplier=3):
    """Remove outliers from specified columns."""
    if columns is None:
        columns = df.select_dtypes(include=[np.number]).columns.tolist()

    before = len(df)
    for col in columns:
        outliers, lower, upper = detect_outliers_iqr(df, col, multiplier)
        df = df.drop(outliers.index, errors='ignore')

    return df, {
        'rows_before': before,
        'rows_removed': before - len(df),
        'columns_checked': len(columns),
    }

@pipeline.add_step
def standardize_types(df):
    """Auto-detect and fix column types."""
    details = {}

    for col in df.columns:
        # Try parsing as datetime
        if df[col].dtype == 'object':
            try:
                parsed = pd.to_datetime(df[col], errors='coerce')
                if parsed.notna().mean() > 0.8:
                    df[col] = parsed
                    details[col] = 'converted to datetime'
                    continue
            except:
                pass

            # Try numeric
            try:
                df[col] = pd.to_numeric(df[col].str.replace('[\$,]', '', regex=True), errors='coerce')
                details[col] = 'converted to numeric'
            except:
                pass

    return df, details

# Run the pipeline
clean_df, results = pipeline.run(raw_df)
```

---

## Cleaning Checklist

### Pre-Processing
- [ ] Load data and inspect shape, dtypes, head
- [ ] Check memory usage (optimize dtypes if needed)
- [ ] Identify missing data patterns (MCAR/MAR/MNAR)
- [ ] Validate schema (expected columns, types)
- [ ] Remove completely empty rows/columns

### Cleaning
- [ ] Handle missing values (impute, drop, or flag)
- [ ] Detect and treat outliers
- [ ] Remove exact and fuzzy duplicates
- [ ] Standardize string formats (lowercase, whitespace)
- [ ] Fix inconsistent categorical labels
- [ ] Parse and standardize date/time columns
- [ ] Validate referential integrity (FK relationships)

### Transformation
- [ ] Encode categorical variables
- [ ] Scale/normalize numerical features
- [ ] Create feature from date columns
- [ ] Log transform skewed distributions
- [ ] Generate missing-indicator columns

### Validation
- [ ] Run data quality report
- [ ] Check summary statistics (mean, std, min, max)
- [ ] Verify distribution shapes
- [ ] Check for data leakage (future data in training)
- [ ] Validate against known business rules
- [ ] Document all transformations for reproducibility
