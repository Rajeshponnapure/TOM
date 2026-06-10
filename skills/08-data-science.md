# Data Science — Comprehensive Skill Guide

## Table of Contents
1. Pandas Advanced
2. NumPy (Broadcasting, Universal Functions)
3. Scikit-Learn Pipeline
4. Statistical Analysis
5. A/B Testing Methodology
6. Dimensionality Reduction (PCA, t-SNE, UMAP)
7. Feature Engineering
8. Model Interpretation (SHAP, LIME, Partial Dependence)

---

## 1. Pandas Advanced

### Groupby Mastery

```python
import pandas as pd
import numpy as np

# Multiple aggregations
df.groupby('category').agg({
    'revenue': ['sum', 'mean', 'std', 'count'],
    'quantity': ['sum', 'mean'],
    'price': 'median',
})

# Named aggregation
df.groupby('category').agg(
    total_revenue=('revenue', 'sum'),
    avg_price=('price', 'mean'),
    order_count=('order_id', 'nunique'),
    std_revenue=('revenue', 'std'),
)

# Transform (same-length output)
df['pct_of_category'] = (
    df.groupby('category')['revenue']
    .transform(lambda x: x / x.sum())
)

# Apply with multiple columns
df.groupby('category').apply(
    lambda g: g['revenue'].corr(g['quantity'])
)

# Resampling time series
df.set_index('date').resample('D')['revenue'].sum()
df.resample('W-MON').agg({
    'revenue': 'sum',
    'orders': 'count',
    'customers': 'nunique',
})

# Rolling window
df['revenue_ma7'] = df['revenue'].rolling(7, min_periods=1).mean()
df['revenue_ewm'] = df['revenue'].ewm(span=14, adjust=False).mean()
```

### Pivot Tables

```python
# Basic pivot
pd.pivot_table(
    df,
    values='revenue',
    index='category',
    columns='region',
    aggfunc='sum',
    fill_value=0,
)

# Multi-index pivot
pd.pivot_table(
    df,
    values='revenue',
    index=['category', 'subcategory'],
    columns=['region', 'quarter'],
    aggfunc='sum',
    margins=True,        # Add totals
    margins_name='Total',
)

# Cross-tabulation
pd.crosstab(
    df['category'],
    df['region'],
    values=df['revenue'],
    aggfunc='sum',
    normalize='index',   # Row percentages
)
```

### Merge Strategies

```python
# Multiple key merge
pd.merge(
    orders, users,
    left_on=['user_id', 'date'],
    right_on=['id', 'signup_date'],
    how='left',
    suffixes=('_order', '_user'),
    indicator=True,       # Add _merge column
)

# Index-based merge
pd.merge(
    sales_data, product_catalog,
    left_index=True,
    right_on='product_id',
)

# Concatenate with keys
pd.concat(
    [q1, q2, q3, q4],
    keys=['Q1', 'Q2', 'Q3', 'Q4'],
    axis=0,
    ignore_index=False,
)

# Update with merge
orders.merge(
    refunds[['order_id', 'refund_amount']],
    on='order_id',
    how='left',
).assign(
    revenue=lambda x: x['revenue'] - x['refund_amount'].fillna(0)
)
```

### Apply vs Vectorized

```python
# BAD — slow, row-by-row
df['label'] = df.apply(
    lambda r: 'high' if r['revenue'] > r['revenue'].median() else 'low',
    axis=1
)

# GOOD — vectorized
median = df['revenue'].median()
df['label'] = np.where(df['revenue'] > median, 'high', 'low')

# Use apply only when vectorization is impossible
# Example: complex string operation
df['domain'] = df['email'].apply(
    lambda x: x.split('@')[1] if '@' in x else None
)

# Map/dictionary replacement
status_map = {1: 'active', 2: 'inactive', 3: 'banned'}
df['status_label'] = df['status_code'].map(status_map)

# Cut for binning
df['age_group'] = pd.cut(
    df['age'],
    bins=[0, 18, 35, 50, 65, 120],
    labels=['<18', '18-35', '35-50', '50-65', '65+'],
)

# qcut for quantile-based bins
df['spending_quantile'] = pd.qcut(
    df['total_spent'],
    q=5,
    labels=['Very Low', 'Low', 'Medium', 'High', 'Very High'],
)
```

---

## 2. NumPy (Broadcasting, Universal Functions)

### Broadcasting Rules

```python
import numpy as np

# Shape compatibility: (3, 1) + (5,) → (3, 5)
A = np.array([[1], [2], [3]])      # Shape: (3, 1)
B = np.array([10, 20, 30, 40, 50])  # Shape: (5,)
C = A + B  # Result: (3, 5)

# Broadcasting rules:
# 1. Align dimensions from the right
# 2. Dimensions are compatible if equal or one is 1
# 3. Missing dimensions are treated as 1

# Common broadcasting patterns
# Subtract mean from each column
data = np.random.randn(100, 50)
centered = data - data.mean(axis=0)  # (100, 50) - (50,)

# Scale by standard deviation
scaled = data / data.std(axis=0)     # (100, 50) / (50,)

# Outer operation
x = np.array([1, 2, 3])
y = np.array([4, 5])
outer = x[:, np.newaxis] * y  # (3, 2)

# All-pairs distance
distances = np.sqrt(
    ((data[:, np.newaxis, :] - data[np.newaxis, :, :]) ** 2).sum(axis=2)
)
```

### Universal Functions (ufunc)

```python
# Element-wise operations (fast C implementation)
arr = np.random.randn(1000000)

# Fast
result = np.where(arr > 0, arr * 2, arr * 0.5)
result = np.clip(arr, -1, 1)
result = np.interp(arr, [-2, 0, 2], [0, 0.5, 1])

# Reduction operations
np.add.reduce(arr)       # Sum (like sum but ufunc)
np.multiply.reduce(arr)  # Product
np.logical_and.reduce(arr > 0)  # All positive

# Accumulate
cumsum = np.add.accumulate(arr)  # Running sum

# Outer product
outer = np.multiply.outer(arr1, arr2)

# Custom ufunc with numba
from numba import vectorize

@vectorize(['float64(float64, float64)'])
def custom_kernel(x, y):
    return np.exp(-x**2 - y**2) * np.sin(x * y)

result = custom_kernel(X, Y)
```

### Advanced Indexing

```python
# Boolean indexing
filtered = arr[(arr > 0) & (arr < 1)]

# Fancy indexing
indices = np.array([0, 2, 5, 9])
selected = arr[indices]

# np.take for repeated indices
selected = np.take(arr, [0, 0, 1, 1, 2, 2])

# np.where with multiple conditions
conditions = [
    df['revenue'] > 1000,
    df['revenue'] > 500,
    df['revenue'] > 0,
]
choices = ['high', 'medium', 'low']
df['tier'] = np.select(conditions, choices, default='zero')

# Meshgrid for 2D computations
x = np.linspace(-5, 5, 100)
y = np.linspace(-5, 5, 100)
X, Y = np.meshgrid(x, y)
Z = np.sin(np.sqrt(X**2 + Y**2))
```

---

## 3. Scikit-Learn Pipeline

### Full Pipeline

```python
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import (
    StandardScaler, MinMaxScaler,
    OneHotEncoder, LabelEncoder,
    OrdinalEncoder, FunctionTransformer,
    PolynomialFeatures, KBinsDiscretizer,
)
from sklearn.impute import SimpleImputer
from sklearn.feature_selection import (
    SelectKBest, SelectFromModel,
    RFE, VarianceThreshold,
)
from sklearn.model_selection import (
    train_test_split, cross_val_score,
    GridSearchCV, RandomizedSearchCV,
    StratifiedKFold, learning_curve,
)
from sklearn.ensemble import (
    RandomForestClassifier, GradientBoostingClassifier,
    HistGradientBoostingClassifier,
)
from sklearn.metrics import (
    classification_report, confusion_matrix,
    roc_auc_score, precision_recall_curve,
    mean_squared_error, r2_score,
)
from sklearn.decomposition import PCA

# Preprocessing definition
numeric_features = ['age', 'income', 'spending_score']
categorical_features = ['gender', 'education', 'region']
text_features = ['description']

numeric_transformer = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler()),
    ('poly', PolynomialFeatures(degree=2, include_bias=False)),
])

categorical_transformer = Pipeline([
    ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
    ('encoder', OneHotEncoder(drop='first', sparse_output=False)),
    ('selector', VarianceThreshold(threshold=0.01)),
])

from sklearn.feature_extraction.text import TfidfVectorizer
text_transformer = Pipeline([
    ('tfidf', TfidfVectorizer(max_features=1000, stop_words='english')),
    ('selector', SelectKBest(k=100)),
])

# Combine preprocessing
preprocessor = ColumnTransformer(
    transformers=[
        ('num', numeric_transformer, numeric_features),
        ('cat', categorical_transformer, categorical_features),
        ('text', text_transformer, 'description'),
    ],
    remainder='drop',
    verbose_feature_names_out=False,
)

# Full pipeline
pipeline = Pipeline([
    ('preprocessor', preprocessor),
    ('feature_selection', SelectFromModel(
        RandomForestClassifier(n_estimators=100, max_depth=10),
        threshold='median',
    )),
    ('classifier', HistGradientBoostingClassifier(
        max_iter=300,
        learning_rate=0.1,
        max_depth=5,
    )),
])
```

### Hyperparameter Tuning

```python
# Parameter grid
param_grid = {
    'preprocessor__num__imputer__strategy': ['mean', 'median'],
    'feature_selection__estimator__n_estimators': [50, 100],
    'classifier__learning_rate': [0.01, 0.05, 0.1],
    'classifier__max_iter': [100, 200, 300],
    'classifier__max_depth': [3, 5, 7],
}

# Grid search with cross-validation
grid_search = GridSearchCV(
    pipeline,
    param_grid,
    cv=StratifiedKFold(n_splits=5, shuffle=True),
    scoring='roc_auc',
    n_jobs=-1,
    verbose=1,
    return_train_score=True,
)

grid_search.fit(X_train, y_train)

print(f"Best params: {grid_search.best_params_}")
print(f"Best CV score: {grid_search.best_score_:.4f}")

# Randomized search for larger spaces
random_search = RandomizedSearchCV(
    pipeline,
    param_distributions=param_grid,
    n_iter=50,
    cv=5,
    scoring='roc_auc',
    n_jobs=-1,
    random_state=42,
)

# Learning curves
train_sizes, train_scores, test_scores = learning_curve(
    pipeline, X, y,
    train_sizes=np.linspace(0.1, 1.0, 10),
    cv=5,
    scoring='roc_auc',
    n_jobs=-1,
)

# Feature importance after pipeline
feature_names = pipeline[:-1].get_feature_names_out()
importances = pipeline[-1].feature_importances_
feature_importance_df = pd.DataFrame({
    'feature': feature_names,
    'importance': importances,
}).sort_values('importance', ascending=False)
```

### Cross-Validation Strategies

```python
# Time series split
from sklearn.model_selection import TimeSeriesSplit

tscv = TimeSeriesSplit(n_splits=5)
for train_idx, val_idx in tscv.split(X):
    X_train, X_val = X[train_idx], X[val_idx]
    y_train, y_val = y[train_idx], y[val_idx]

# Group K-Fold (no data leakage between groups)
from sklearn.model_selection import GroupKFold
gkf = GroupKFold(n_splits=5)
for train_idx, val_idx in gkf.split(X, y, groups=df['user_id']):
    pass

# Stratified shuffle split
from sklearn.model_selection import StratifiedShuffleSplit
sss = StratifiedShuffleSplit(n_splits=10, test_size=0.2)
```

---

## 4. Statistical Analysis

### Hypothesis Testing

```python
from scipy import stats

# T-test: compare two groups
control = df[df['group'] == 'control']['revenue']
treatment = df[df['group'] == 'treatment']['revenue']

t_stat, p_value = stats.ttest_ind(treatment, control)
# If p < 0.05, significant difference

# Paired t-test (same subjects, before/after)
before = df['pre_score']
after = df['post_score']
t_stat, p_value = stats.ttest_rel(before, after)

# ANOVA (3+ groups)
groups = [df[df['version'] == v]['metric'] for v in ['A', 'B', 'C']]
f_stat, p_value = stats.f_oneway(*groups)

# Chi-squared test (categorical)
from scipy.stats import chi2_contingency
contingency = pd.crosstab(df['group'], df['converted'])
chi2, p_value, dof, expected = chi2_contingency(contingency)

# Mann-Whitney U (non-parametric)
u_stat, p_value = stats.mannwhitneyu(treatment, control)

# Kolmogorov-Smirnov (distribution comparison)
ks_stat, p_value = stats.ks_2samp(control, treatment)
```

### Confidence Intervals

```python
def bootstrap_ci(data, metric=np.mean, n_bootstrap=10000, ci=0.95):
    """Bootstrap confidence interval for any metric."""
    bootstrapped_metrics = []
    n = len(data)

    for _ in range(n_bootstrap):
        sample = np.random.choice(data, size=n, replace=True)
        bootstrapped_metrics.append(metric(sample))

    alpha = (1 - ci) / 2
    lower = np.percentile(bootstrapped_metrics, alpha * 100)
    upper = np.percentile(bootstrapped_metrics, (1 - alpha) * 100)

    return lower, upper

# Usage
conversion_rates = df[df['group'] == 'treatment']['converted']
ci_lower, ci_upper = bootstrap_ci(conversion_rates, metric=np.mean)

# Bayesian credible interval
from scipy.stats import beta

def bayesian_conversion_rate(successes, trials, alpha_prior=1, beta_prior=1):
    alpha_post = alpha_prior + successes
    beta_post = beta_prior + trials - successes
    posterior = beta(alpha_post, beta_post)

    return {
        'mean': posterior.mean(),
        'ci_95': posterior.interval(0.95),
        'median': posterior.median(),
        'std': posterior.std(),
    }
```

### Bayesian Inference

```python
# Bayesian A/B testing with PyMC
import pymc as pm

with pm.Model() as ab_test:
    # Priors
    p_A = pm.Beta('p_A', alpha=1, beta=1)
    p_B = pm.Beta('p_B', alpha=1, beta=1)

    # Likelihood
    obs_A = pm.Binomial('obs_A', n=trials_A, p=p_A, observed=successes_A)
    obs_B = pm.Binomial('obs_B', n=trials_B, p=p_B, observed=successes_B)

    # Derived quantity
    lift = pm.Deterministic('lift', (p_B - p_A) / p_A)
    risk = pm.Deterministic('risk', pm.math.switch(p_B > p_A, 0, 1 - p_B / p_A))

    # Sampling
    trace = pm.sample(2000, tune=1000, cores=4)

# Results
print(f"P(A) mean: {trace['p_A'].mean():.3f}")
print(f"P(B) mean: {trace['p_B'].mean():.3f}")
print(f"P(B > A): {(trace['lift'] > 0).mean():.3f}")
print(f"95% HDI lift: {pm.hdi(trace['lift'], hdi_prob=0.95)}")
```

---

## 5. A/B Testing Methodology

### Test Design

```python
# Sample size calculation
from scipy.stats import norm

def minimum_sample_size(
    baseline_rate,
    minimum_detectable_effect,
    alpha=0.05,
    power=0.8,
):
    """Calculate required sample size per variant."""
    z_alpha = norm.ppf(1 - alpha / 2)
    z_beta = norm.ppf(power)

    p_pooled = baseline_rate * (1 + minimum_detectable_effect / 2)
    variance = 2 * p_pooled * (1 - p_pooled)

    effect_size = baseline_rate * minimum_detectable_effect
    n = (z_alpha + z_beta)**2 * variance / effect_size**2

    return int(np.ceil(n))

# Example: detect 10% lift from 5% baseline
n = minimum_sample_size(
    baseline_rate=0.05,
    minimum_detectable_effect=0.10,  # 10% relative lift
    alpha=0.05,
    power=0.80,
)
print(f"Need {n} users per variant")
```

### Analysis Framework

```python
def analyze_ab_test(data, metric_column, variant_column='variant', control='control'):
    """Full A/B test analysis."""
    control_data = data[data[variant_column] == control][metric_column]
    treatment_data = data[data[variant_column] != control][metric_column]

    # Descriptive stats
    results = {
        'control': {
            'n': len(control_data),
            'mean': control_data.mean(),
            'std': control_data.std(),
            'ci': bootstrap_ci(control_data),
        },
        'treatment': {
            'n': len(treatment_data),
            'mean': treatment_data.mean(),
            'std': treatment_data.std(),
            'ci': bootstrap_ci(treatment_data),
        },
    }

    # Statistical test
    t_stat, p_value = stats.ttest_ind(treatment_data, control_data)
    results['p_value'] = p_value
    results['significant'] = p_value < 0.05

    # Effect size
    diff = treatment_data.mean() - control_data.mean()
    results['absolute_lift'] = diff
    results['relative_lift'] = diff / control_data.mean()

    # Sequential testing (always valid inference)
    # For continuous monitoring, use always-valid p-values
    # or Bayesian approach to avoid peeking bias

    return results
```

### Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| Peeking at results | Pre-register sample size, use sequential testing |
| Multiple comparisons | Bonferroni correction, FDR control |
| Simpson's paradox | Pre-stratify, check within segments |
| Novelty effect | Run test long enough (at least 2 weeks) |
| Selection bias | Proper randomization, avoid cherry-picking |
| Survivorship bias | Include all users who entered the test |
| Carryover effects | Washout periods between treatments |

---

## 6. Dimensionality Reduction

### PCA

```python
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

# Scale first (PCA is variance-based)
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Fit PCA
pca = PCA()
X_pca = pca.fit_transform(X_scaled)

# Explained variance
explained_var = pca.explained_variance_ratio_
cumulative_var = explained_var.cumsum()

# Find components for 95% variance
n_components = np.argmax(cumulative_var >= 0.95) + 1
print(f"Need {n_components} components for 95% variance")

# Scree plot
import matplotlib.pyplot as plt
plt.figure(figsize=(10, 6))
plt.plot(range(1, len(explained_var) + 1), cumulative_var, 'bo-')
plt.axhline(y=0.95, color='r', linestyle='--')
plt.axvline(x=n_components, color='r', linestyle='--')
plt.xlabel('Number of Components')
plt.ylabel('Cumulative Explained Variance')
plt.show()

# Component loadings
loadings = pd.DataFrame(
    pca.components_.T,
    columns=[f'PC{i+1}' for i in range(pca.n_components_)],
    index=feature_names,
)
```

### t-SNE

```python
from sklearn.manifold import TSNE

# t-SNE parameters
tsne = TSNE(
    n_components=2,
    perplexity=30,       # Balance local/global structure
    learning_rate=200,
    n_iter=1000,
    random_state=42,
    init='pca',           # Better initialization than random
    angle=0.3,            # Performance-speed tradeoff
)

X_tsne = tsne.fit_transform(X_scaled)

# Visualization
plt.figure(figsize=(12, 8))
scatter = plt.scatter(
    X_tsne[:, 0], X_tsne[:, 1],
    c=y, cmap='Spectral',
    alpha=0.7, s=10,
)
plt.colorbar(scatter)
plt.title('t-SNE Visualization')
plt.show()
```

### UMAP

```python
import umap

reducer = umap.UMAP(
    n_neighbors=15,       # Local neighborhood size
    min_dist=0.1,         # Minimum distance between points
    n_components=2,
    metric='euclidean',
    random_state=42,
)

X_umap = reducer.fit_transform(X_scaled)

# UMAP preserves more global structure than t-SNE
# Much faster for large datasets
# Good for both visualization and as preprocessing
```

### When to Use Which

| Method | Speed | Global Structure | Local Structure | Interpretability |
|--------|-------|-----------------|-----------------|-----------------|
| PCA | Fast | Excellent | Poor | Excellent |
| t-SNE | Slow | Poor | Excellent | Poor |
| UMAP | Fast | Good | Excellent | Moderate |
| LDA | Fast | Good | Moderate | Good (supervised) |

---

## 7. Feature Engineering

### Feature Creation

```python
# Temporal features
df['hour'] = df['timestamp'].dt.hour
df['day_of_week'] = df['timestamp'].dt.dayofweek
df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
df['month'] = df['timestamp'].dt.month
df['quarter'] = df['timestamp'].dt.quarter
df['day_sin'] = np.sin(2 * np.pi * df['day_of_week'] / 7)
df['day_cos'] = np.cos(2 * np.pi * df['day_of_week'] / 7)
df['hour_sin'] = np.sin(2 * np.pi * df['hour'] / 24)
df['hour_cos'] = np.cos(2 * np.pi * df['hour'] / 24)
df['days_since_last_purchase'] = (
    df['purchase_date'] - df.groupby('user_id')['purchase_date'].shift(1)
).dt.days

# Aggregated features
user_features = df.groupby('user_id').agg({
    'purchase_amount': ['sum', 'mean', 'std', 'count'],
    'days_since_signup': 'max',
    'category': lambda x: x.nunique(),
}).reset_index()
user_features.columns = ['_'.join(col).strip('_') for col in user_features.columns]

# Ratio features
df['purchase_frequency'] = df['total_purchases'] / df['customer_tenure_days']
df['avg_order_value'] = df['total_spent'] / df['total_orders']
df['return_rate'] = df['returned_items'] / df['total_items']

# Interaction features
df['income_x_age'] = df['income'] * df['age']
df['category_region'] = df['category'] + '_' + df['region']

# Target encoding (with smoothing)
def target_encode(series, target, prior=None, min_samples_curve=100):
    prior = prior or target.mean()
    data = pd.DataFrame({'feature': series, 'target': target})

    agg = data.groupby('feature')['target'].agg(['count', 'mean'])
    smooth = 1 / (1 + np.exp(-(agg['count'] - min_samples_curve) / 10000))
    encoded = prior * (1 - smooth) + agg['mean'] * smooth

    return series.map(encoded)
```

---

## 8. Model Interpretation (SHAP, LIME, PDP)

### SHAP

```python
import shap

# Tree explainer (fast for tree-based models)
explainer = shap.TreeExplainer(model)
shap_values = explainer.shap_values(X_test)

# Summary plot
shap.summary_plot(shap_values, X_test, feature_names=feature_names)

# Bar plot (feature importance)
shap.summary_plot(shap_values, X_test, plot_type='bar')

# Force plot (single prediction)
shap.force_plot(
    explainer.expected_value,
    shap_values[0, :],
    X_test.iloc[0, :],
    matplotlib=True,
)

# Dependence plot (relationship between feature and SHAP value)
shap.dependence_plot('income', shap_values, X_test)

# SHAP interaction values
shap_interaction = shap.TreeExplainer(model).shap_interaction_values(X_test)
shap.summary_plot(shap_interaction, X_test, feature_names=feature_names)
```

### LIME

```python
from lime import lime_tabular

explainer = lime_tabular.LimeTabularExplainer(
    X_train.values,
    feature_names=feature_names,
    class_names=['No Conversion', 'Conversion'],
    mode='classification',
    kernel_width=3,
    discretize_continuous=True,
)

# Explain single prediction
exp = explainer.explain_instance(
    X_test.iloc[0].values,
    model.predict_proba,
    num_features=10,
    top_labels=1,
)

exp.show_in_notebook(show_table=True)
exp.as_list()
```

### Partial Dependence Plots

```python
from sklearn.inspection import PartialDependenceDisplay

# 1D PDP
PartialDependenceDisplay.from_estimator(
    model, X_train,
    features=['income', 'age'],
    kind='average',
    grid_resolution=50,
    subsample=1000,
)

# 2D interaction
PartialDependenceDisplay.from_estimator(
    model, X_train,
    features=[('income', 'age')],
    kind='average',
    grid_resolution=20,
)
```

### Feature Importance Comparison

```python
# Multiple importance measures
importance_df = pd.DataFrame({
    'feature': feature_names,
    'coef': model.coef_[0] if hasattr(model, 'coef_') else np.nan,
    'permutation': permutation_importance(
        model, X_val, y_val, n_repeats=10, random_state=42
    ).importances_mean,
    'shap': np.abs(shap_values).mean(axis=0),
    'tree_imp': model.feature_importances_ if hasattr(model, 'feature_importances_') else np.nan,
}).set_index('feature')
```

---

## Decision Framework

### Model Selection Guide

| Problem Type | Dataset Size | Recommended Model |
|-------------|--------------|-------------------|
| Classification | Small (< 1k) | Logistic Regression, SVM |
| Classification | Medium (1k–100k) | Random Forest, XGBoost |
| Classification | Large (> 100k) | LightGBM, CatBoost, Neural Net |
| Regression | Small | Ridge, Lasso, ElasticNet |
| Regression | Large | Gradient Boosting, Neural Net |
| Text | Any | TF-IDF + Linear, Transformer |
| Time Series | Any | Prophet, LightGBM with features, LSTM |
| Image | Any | CNN, ResNet, ViT |

### Evaluation Metrics

| Task | Metric | When to Use |
|------|--------|-------------|
| Classification | Accuracy | Balanced classes |
| Classification | Precision/Recall | Imbalanced, cost matters |
| Classification | AUC-ROC | Ranking quality |
| Classification | F1 Score | Balance precision/recall |
| Regression | MAE | Interpretable error |
| Regression | RMSE | Penalize large errors |
| Regression | R² | Variance explained |
| Clustering | Silhouette | Cluster separation |
| Clustering | Inertia | Within-cluster distance |
