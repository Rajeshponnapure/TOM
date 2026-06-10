# Machine Learning Skills — Comprehensive Guide

## 1. Supervised Learning — Regression

### Linear Regression

```python
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.model_selection import cross_val_score, learning_curve

# Simple Linear
X = np.array([[1], [2], [3], [4], [5]])
y = np.array([2, 4, 5, 4, 5])

model = LinearRegression()
model.fit(X, y)
print(f"Slope: {model.coef_[0]:.2f}, Intercept: {model.intercept_:.2f}")
print(f"R²: {model.score(X, y):.3f}")

# Multiple Linear
from sklearn.datasets import fetch_california_housing
data = fetch_california_housing()
X, y = data.data, data.target

# Ridge (L2) with cross-validated alpha
from sklearn.linear_model import RidgeCV
ridge = RidgeCV(alphas=[0.1, 1.0, 10.0], cv=5)
ridge.fit(X, y)
print(f"Best alpha: {ridge.alpha_:.2f}, R²: {ridge.score(X, y):.3f}")

# Lasso (L1) for feature selection
from sklearn.linear_model import LassoCV
lasso = LassoCV(cv=5, random_state=42)
lasso.fit(X, y)
n_used = np.sum(lasso.coef_ != 0)
print(f"Features used: {n_used}/{X.shape[1]}")

# ElasticNet (L1 + L2)
from sklearn.linear_model import ElasticNetCV
enet = ElasticNetCV(l1_ratio=[0.1, 0.5, 0.7, 0.9, 0.95, 0.99, 1], cv=5)
enet.fit(X, y)
print(f"Best l1_ratio: {enet.l1_ratio_:.2f}")

# Polynomial regression with pipeline
pipe = Pipeline([
    ('poly', PolynomialFeatures(degree=2, include_bias=False)),
    ('scaler', StandardScaler()),
    ('ridge', Ridge(alpha=1.0))
])
pipe.fit(X, y)
print(f"Polynomial R²: {pipe.score(X, y):.3f}")

# Learning curve analysis
import matplotlib.pyplot as plt
train_sizes, train_scores, val_scores = learning_curve(
    Ridge(alpha=1.0), X, y, cv=5, train_sizes=[0.1, 0.3, 0.5, 0.7, 0.9],
    scoring='r2'
)
train_mean = np.mean(train_scores, axis=1)
val_mean = np.mean(val_scores, axis=1)

plt.plot(train_sizes, train_mean, 'o-', label='Training')
plt.plot(train_sizes, val_mean, 'o-', label='Validation')
plt.xlabel('Training examples')
plt.ylabel('R² Score')
plt.legend()
plt.show()
```

### Regularization Comparison

| Technique | Penalty | Effect | When to Use |
|---|---|---|---|
| Ridge (L2) | λΣβ² | Shrinks coefficients uniformly | Many features, all relevant |
| Lasso (L1) | λΣ\|β\| | Sparse solution, feature selection | Feature selection needed |
| ElasticNet | λ(αL1 + (1-α)L2) | Combination of both | Groups of correlated features |

### Model Evaluation

```python
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import cross_val_score, KFold

# Regression metrics
def regression_metrics(y_true, y_pred, X):
    mae = mean_absolute_error(y_true, y_pred)
    mse = mean_squared_error(y_true, y_pred)
    rmse = np.sqrt(mse)
    r2 = r2_score(y_true, y_pred)

    # Adjusted R²
    n = len(y_true)
    p = X.shape[1]
    adj_r2 = 1 - (1 - r2) * (n - 1) / (n - p - 1)

    # MAPE (Mean Absolute Percentage Error)
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100

    return {
        'MAE': mae, 'MSE': mse, 'RMSE': rmse,
        'R²': r2, 'Adj R²': adj_r2, 'MAPE': mape
    }

# Cross-validation
kf = KFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = cross_val_score(Ridge(alpha=1.0), X, y, cv=kf, scoring='r2')
print(f"CV R²: {cv_scores.mean():.3f} ± {cv_scores.std():.3f}")
```

## 2. SVM (Support Vector Machines)

```python
from sklearn.svm import SVR, SVC
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

# SVM for Regression (SVR)
svr_pipe = Pipeline([
    ('scaler', StandardScaler()),
    ('svr', SVR(kernel='rbf', C=100, gamma=0.1, epsilon=0.1))
])
svr_pipe.fit(X_train, y_train)

# SVM for Classification (SVC)
from sklearn.datasets import make_classification
X_clf, y_clf = make_classification(n_samples=1000, n_features=20,
                                    n_informative=15, random_state=42)

svc = SVC(kernel='rbf', C=1.0, gamma='scale', probability=True)
svc.fit(X_clf[:700], y_clf[:700])

# Decision function
decision_scores = svc.decision_function(X_clf[700:])
probabilities = svc.predict_proba(X_clf[700:])

# Kernel trick — custom kernel
from sklearn.metrics.pairwise import rbf_kernel, polynomial_kernel

# Grid search for SVM
from sklearn.model_selection import GridSearchCV

param_grid = {
    'C': [0.1, 1, 10, 100],
    'gamma': ['scale', 'auto', 0.1, 0.01],
    'kernel': ['rbf', 'poly', 'sigmoid']
}

grid = GridSearchCV(SVC(), param_grid, cv=5, scoring='accuracy', n_jobs=-1)
grid.fit(X_clf[:700], y_clf[:700])
print(f"Best params: {grid.best_params_}")
print(f"Best score: {grid.best_score_:.3f}")
```

## 3. Random Forest

```python
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
from sklearn.inspection import permutation_importance
import matplotlib.pyplot as plt

# Regression
rf = RandomForestRegressor(
    n_estimators=500,
    max_depth=15,
    min_samples_split=5,
    min_samples_leaf=2,
    max_features='sqrt',
    bootstrap=True,
    oob_score=True,  # Out-of-bag estimate
    random_state=42,
    n_jobs=-1
)
rf.fit(X_train, y_train)
print(f"OOB R²: {rf.oob_score_:.3f}")
print(f"Test R²: {rf.score(X_test, y_test):.3f}")

# Feature importance
feature_importance = rf.feature_importances_
indices = np.argsort(feature_importance)[::-1]

print("Feature ranking:")
for i in range(min(10, len(indices))):
    print(f"{i+1}. feature {indices[i]} ({feature_importance[indices[i]]:.3f})")

# Permutation importance (more reliable)
perm_importance = permutation_importance(
    rf, X_test, y_test,
    n_repeats=10, random_state=42, n_jobs=-1
)

# Partial dependence plot
from sklearn.inspection import PartialDependenceDisplay
PartialDependenceDisplay.from_estimator(
    rf, X_train, [0, 1, (0, 1)],
    grid_resolution=50
)

# Tree visualization
from sklearn.tree import plot_tree
plt.figure(figsize=(20, 10))
plot_tree(rf.estimators_[0], max_depth=3, filled=True)
plt.show()
```

### Key Hyperparameters

| Parameter | Effect | Typical Range |
|---|---|---|
| n_estimators | More = better, diminishing returns | 100-2000 |
| max_depth | Controls overfitting | 3-20, None |
| min_samples_split | Prevents splitting tiny nodes | 2-50 |
| min_samples_leaf | Smooths predictions | 1-20 |
| max_features | Feature sampling ratio | 'sqrt', 'log2', 0.3-0.8 |
| bootstrap | Sampling with/without replacement | True/False |

## 4. XGBoost

```python
import xgboost as xgb
from sklearn.model_selection import RandomizedSearchCV

# Native XGBoost API
dtrain = xgb.DMatrix(X_train, label=y_train)
dtest = xgb.DMatrix(X_test, label=y_test)

params = {
    'objective': 'reg:squarederror',
    'eval_metric': 'rmse',
    'max_depth': 6,
    'learning_rate': 0.01,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'min_child_weight': 3,
    'gamma': 0.1,
    'reg_alpha': 0.01,
    'reg_lambda': 1.0,
    'tree_method': 'hist',  # 'gpu_hist' for GPU
    'device': 'cpu',        # 'cuda' for GPU
}

model = xgb.train(
    params,
    dtrain,
    num_boost_round=1000,
    evals=[(dtrain, 'train'), (dtest, 'eval')],
    early_stopping_rounds=50,
    verbose_eval=100
)

# sklearn API
xgb_model = xgb.XGBRegressor(
    n_estimators=1000,
    max_depth=6,
    learning_rate=0.01,
    subsample=0.8,
    colsample_bytree=0.8,
    early_stopping_rounds=50,
    random_state=42,
    eval_metric='rmse',
)

xgb_model.fit(
    X_train, y_train,
    eval_set=[(X_train, y_train), (X_test, y_test)],
    verbose=False
)

# Randomized search
param_dist = {
    'max_depth': [3, 5, 7, 9],
    'learning_rate': [0.001, 0.01, 0.05, 0.1],
    'subsample': [0.6, 0.7, 0.8, 0.9],
    'colsample_bytree': [0.6, 0.7, 0.8, 0.9],
    'min_child_weight': [1, 3, 5, 7],
    'reg_alpha': [0, 0.01, 0.1, 1],
    'reg_lambda': [0.1, 1, 5, 10],
}

random_search = RandomizedSearchCV(
    xgb.XGBRegressor(n_estimators=500, random_state=42),
    param_distributions=param_dist,
    n_iter=50,
    cv=5,
    scoring='r2',
    n_jobs=-1,
    random_state=42
)
random_search.fit(X_train, y_train, verbose=False)
print(f"Best params: {random_search.best_params_}")
print(f"Best CV score: {random_search.best_score_:.3f}")

# Feature importance (multiple types)
importance_types = ['weight', 'gain', 'cover', 'total_gain', 'total_cover']
for imp_type in importance_types:
    importance = model.get_score(importance_type=imp_type)
    print(f"{imp_type}: {len(importance)} features")
```

## 5. LightGBM

```python
import lightgbm as lgb

# Dataset
train_data = lgb.Dataset(X_train, label=y_train)
test_data = lgb.Dataset(X_test, label=y_test, reference=train_data)

params = {
    'objective': 'regression',
    'metric': 'rmse',
    'boosting_type': 'gbdt',  # 'dart', 'goss'
    'num_leaves': 31,
    'max_depth': -1,
    'learning_rate': 0.01,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'min_data_in_leaf': 20,
    'lambda_l1': 0.01,
    'lambda_l2': 0.1,
    'device_type': 'cpu',  # 'gpu'
    'verbose': -1,
}

model = lgb.train(
    params,
    train_data,
    num_boost_round=1000,
    valid_sets=[train_data, test_data],
    callbacks=[
        lgb.early_stopping(50),
        lgb.log_evaluation(100)
    ]
)

# sklearn API
lgb_model = lgb.LGBMRegressor(
    n_estimators=1000,
    num_leaves=31,
    learning_rate=0.01,
    feature_fraction=0.8,
    bagging_fraction=0.8,
    bagging_freq=5,
    early_stopping_round=50,
    random_state=42,
    verbose=-1,
    device_type='cpu',
)

lgb_model.fit(
    X_train, y_train,
    eval_set=[(X_train, y_train), (X_test, y_test)]
)

# Categorical feature support
X_cat = X.copy()
categorical_features = [0, 3, 5]  # Indices of categorical columns
lgb_model.fit(
    X_train, y_train,
    eval_set=[(X_test, y_test)],
    categorical_feature=categorical_features
)
```

### XGBoost vs LightGBM vs CatBoost

| Feature | XGBoost | LightGBM | CatBoost |
|---|---|---|---|
| Tree growth | Level-wise | Leaf-wise | Symmetric |
| Categorical features | Manual encoding | Manual encoding | Native support |
| Training speed | Moderate | Fast | Moderate |
| Memory usage | Higher | Lower | Moderate |
| GPU support | Excellent | Good | Good |
| Default params | Good | Good | Best defaults |
| Interpretability | High | High | Moderate |

## 6. CatBoost

```python
from catboost import CatBoostRegressor, CatBoostClassifier, Pool

# Native with categorical features
cat_features = [0, 1, 5]  # column indices or names

train_pool = Pool(
    data=X_train,
    label=y_train,
    cat_features=cat_features
)

model = CatBoostRegressor(
    iterations=1000,
    learning_rate=0.03,
    depth=6,
    l2_leaf_reg=3,
    border_count=128,
    random_seed=42,
    verbose=100,
    early_stopping_rounds=50,
    eval_metric='RMSE',
    task_type='CPU',  # or 'GPU'
)

model.fit(train_pool, eval_set=(X_test, y_test))

# Text features support
text_features = [3]  # column with text
model.fit(
    X_train, y_train,
    text_features=text_features,
    eval_set=(X_test, y_test)
)

# Prediction explanation
shap_values = model.get_feature_importance(
    train_pool,
    type='ShapValues'
)

# Model export
model.save_model('catboost_model.cbm')
loaded = CatBoostRegressor()
loaded.load_model('catboost_model.cbm')
```

## 7. Unsupervised Learning

### K-Means Clustering

```python
from sklearn.cluster import KMeans, DBSCAN, SpectralClustering
from sklearn.metrics import silhouette_score, calinski_harabasz_score
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA

# Find optimal K
def find_optimal_k(X, max_k=20):
    inertias = []
    sil_scores = []
    K_range = range(2, max_k + 1)

    for k in K_range:
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(X)

        inertias.append(kmeans.inertia_)

        if len(set(labels)) > 1:
            sil_scores.append(silhouette_score(X, labels))
        else:
            sil_scores.append(-1)

    # Elbow method
    deltas = np.diff(inertias)
    delta_deltas = np.diff(deltas)
    elbow = np.argmax(delta_deltas) + 2

    # Silhouette method
    best_k = np.argmax(sil_scores) + 2

    return elbow, best_k, inertias, sil_scores

# Apply K-Means
kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
kmeans.fit(X_scaled)

labels = kmeans.labels_
centroids = kmeans.cluster_centers_

# Cluster quality metrics
sil_score = silhouette_score(X_scaled, labels)
ch_score = calinski_harabasz_score(X_scaled, labels)

print(f"Silhouette: {sil_score:.3f}")
print(f"Calinski-Harabasz: {ch_score:.0f}")

# Visualize with PCA
pca = PCA(n_components=2)
X_pca = pca.fit_transform(X_scaled)

plt.scatter(X_pca[:, 0], X_pca[:, 1], c=labels, cmap='viridis', alpha=0.6)
plt.scatter(pca.transform(centroids)[:, 0],
            pca.transform(centroids)[:, 1],
            marker='X', s=200, c='red')
plt.title('K-Means Clusters (PCA-reduced)')
plt.show()
```

### DBSCAN

```python
from sklearn.cluster import DBSCAN
from sklearn.neighbors import NearestNeighbors

# Find optimal eps using k-distance graph
def find_eps(X, k=5):
    neighbors = NearestNeighbors(n_neighbors=k)
    neighbors_fit = neighbors.fit(X)
    distances, _ = neighbors_fit.kneighbors(X)
    distances = np.sort(distances[:, k-1])

    plt.plot(distances)
    plt.xlabel('Points')
    plt.ylabel(f'{k}-th nearest neighbor distance')
    plt.title('K-Distance Graph for DBSCAN eps')
    plt.show()

    # Look for the "elbow" point
    return distances

# Apply DBSCAN
dbscan = DBSCAN(
    eps=0.5,       # Maximum distance between points in a cluster
    min_samples=5,  # Minimum points to form a dense region
    metric='euclidean',
    algorithm='auto',
    leaf_size=30
)
labels = dbscan.fit_predict(X_scaled)

n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
n_noise = list(labels).count(-1)

print(f"Clusters found: {n_clusters}")
print(f"Noise points: {n_noise}")
print(f"Silhouette score: {silhouette_score(X_scaled[labels != -1], labels[labels != -1]):.3f}")

# Comparison of clustering algorithms
from sklearn.cluster import AgglomerativeClustering, Birch, MeanShift

algorithms = [
    ('K-Means', KMeans(n_clusters=5, random_state=42)),
    ('DBSCAN', DBSCAN(eps=0.5, min_samples=5)),
    ('Agglomerative', AgglomerativeClustering(n_clusters=5)),
    ('Birch', Birch(n_clusters=5)),
    ('Spectral', SpectralClustering(n_clusters=5, random_state=42)),
]

for name, algo in algorithms:
    labels = algo.fit_predict(X_scaled)
    sil = silhouette_score(X_scaled, labels) if len(set(labels)) > 1 else -1
    print(f"{name:15s} Silhouette: {sil:.3f}")
```

### PCA (Dimensionality Reduction)

```python
from sklearn.decomposition import PCA, IncrementalPCA

# Standard PCA
pca = PCA(n_components=0.95)  # Keep 95% variance
X_pca = pca.fit_transform(X_scaled)
print(f"Components to explain 95% var: {pca.n_components_}")

# Explained variance
cumulative_variance = np.cumsum(pca.explained_variance_ratio_)

plt.plot(range(1, len(cumulative_variance) + 1), cumulative_variance, 'bo-')
plt.axhline(y=0.95, color='r', linestyle='--')
plt.xlabel('Number of Components')
plt.ylabel('Cumulative Explained Variance')
plt.title('Explained Variance vs Components')
plt.show()

# Incremental PCA (for large datasets)
n_batches = 100
inc_pca = IncrementalPCA(n_components=50)

for batch in np.array_split(X, n_batches):
    inc_pca.partial_fit(batch)

X_inc_pca = inc_pca.transform(X_scaled)
print(f"Explained variance: {inc_pca.explained_variance_ratio_.sum():.3f}")

# PCA for visualization
pca_2d = PCA(n_components=2)
X_pca_2d = pca_2d.fit_transform(X_scaled)

# Biplot
components = pca_2d.components_
for i, (x, y) in enumerate(components.T):
    plt.arrow(0, 0, x, y, head_width=0.02, head_length=0.03, fc='red', ec='red')
    plt.text(x * 1.1, y * 1.1, i, color='red')

plt.scatter(X_pca_2d[:, 0], X_pca_2d[:, 1], alpha=0.5)
plt.title('PCA Biplot')
plt.show()
```

### t-SNE

```python
from sklearn.manifold import TSNE

# t-SNE (non-linear, for visualization only)
tsne = TSNE(
    n_components=2,
    perplexity=30,      # Related to expected cluster size
    learning_rate=200,
    n_iter=1000,
    random_state=42,
    init='pca',         # Better initialization
    method='barnes_hut' # or 'exact' for small datasets
)

X_tsne = tsne.fit_transform(X_scaled)

plt.figure(figsize=(10, 8))
plt.scatter(X_tsne[:, 0], X_tsne[:, 1], c=y_labels, cmap='viridis', alpha=0.7)
plt.title('t-SNE Visualization')
plt.colorbar()
plt.show()

# Compare perplexity values
perplexities = [5, 10, 30, 50, 100]
fig, axes = plt.subplots(1, 5, figsize=(20, 4))

for i, perp in enumerate(perplexities):
    tsne = TSNE(n_components=2, perplexity=perp, random_state=42)
    X_tsne = tsne.fit_transform(X_scaled)
    axes[i].scatter(X_tsne[:, 0], X_tsne[:, 1], c=y_labels, cmap='viridis', s=5)
    axes[i].set_title(f'Perplexity={perp}')

plt.tight_layout()
plt.show()
```

## 8. Model Evaluation

### Classification Metrics

```python
from sklearn.metrics import (
    accuracy_score, precision_score, recall_score, f1_score,
    confusion_matrix, classification_report, roc_curve, auc,
    precision_recall_curve, average_precision_score, log_loss
)

y_pred = model.predict(X_test)
y_proba = model.predict_proba(X_test)[:, 1]

# Basic metrics
print(f"Accuracy:  {accuracy_score(y_test, y_pred):.3f}")
print(f"Precision: {precision_score(y_test, y_pred):.3f}")
print(f"Recall:    {recall_score(y_test, y_pred):.3f}")
print(f"F1-Score:  {f1_score(y_test, y_pred):.3f}")

# Detailed classification report
print(classification_report(y_test, y_pred, target_names=['Class 0', 'Class 1']))

# Confusion matrix
cm = confusion_matrix(y_test, y_pred)
tn, fp, fn, tp = cm.ravel()
print(f"TN={tn} FP={fp} FN={fn} TP={tp}")
print(f"Specificity: {tn/(tn+fp):.3f}")
print(f"Prevalence:  {(tp+fn)/len(y_test):.3f}")

# ROC curve
fpr, tpr, thresholds = roc_curve(y_test, y_proba)
roc_auc = auc(fpr, tpr)

plt.figure()
plt.plot(fpr, tpr, label=f'ROC curve (AUC = {roc_auc:.3f})')
plt.plot([0, 1], [0, 1], 'k--')
plt.xlabel('False Positive Rate')
plt.ylabel('True Positive Rate')
plt.title('ROC Curve')
plt.legend()
plt.show()

# PR curve
precision, recall, _ = precision_recall_curve(y_test, y_proba)
avg_precision = average_precision_score(y_test, y_proba)

plt.figure()
plt.plot(recall, precision, label=f'PR curve (AP = {avg_precision:.3f})')
plt.xlabel('Recall')
plt.ylabel('Precision')
plt.title('Precision-Recall Curve')
plt.legend()
plt.show()

# Log loss
ll = log_loss(y_test, y_proba)
print(f"Log Loss: {ll:.3f}")

# Threshold tuning
def find_best_threshold(y_true, y_proba):
    fpr, tpr, thresholds = roc_curve(y_true, y_proba)
    youden_j = tpr - fpr
    best_idx = np.argmax(youden_j)
    return thresholds[best_idx]

best_threshold = find_best_threshold(y_test, y_proba)
print(f"Best threshold (Youden J): {best_threshold:.3f}")

# Cross-validation with multiple metrics
from sklearn.model_selection import cross_validate

scoring = ['accuracy', 'precision', 'recall', 'f1', 'roc_auc']
cv_results = cross_validate(
    RandomForestClassifier(),
    X, y,
    cv=5,
    scoring=scoring,
    return_train_score=True
)

for metric in scoring:
    test_scores = cv_results[f'test_{metric}']
    print(f"{metric:15s} {test_scores.mean():.3f} ± {test_scores.std():.3f}")
```

### Learning Curves & Validation

```python
from sklearn.model_selection import learning_curve, validation_curve

# Learning curve
train_sizes = np.linspace(0.1, 1.0, 10)
train_sizes_abs, train_scores, val_scores = learning_curve(
    RandomForestClassifier(n_estimators=100),
    X, y,
    train_sizes=train_sizes,
    cv=5,
    scoring='f1',
    n_jobs=-1
)

train_mean = np.mean(train_scores, axis=1)
train_std = np.std(train_scores, axis=1)
val_mean = np.mean(val_scores, axis=1)
val_std = np.std(val_scores, axis=1)

plt.figure()
plt.fill_between(train_sizes_abs, train_mean - train_std, train_mean + train_std, alpha=0.1)
plt.fill_between(train_sizes_abs, val_mean - val_std, val_mean + val_std, alpha=0.1)
plt.plot(train_sizes_abs, train_mean, 'o-', label='Training score')
plt.plot(train_sizes_abs, val_mean, 'o-', label='Cross-validation score')
plt.xlabel('Training examples')
plt.ylabel('F1 Score')
plt.title('Learning Curve')
plt.legend()
plt.show()

# Validation curve (max_depth)
param_range = [1, 3, 5, 7, 9, 11, 15, 20]
train_scores, val_scores = validation_curve(
    RandomForestClassifier(n_estimators=100),
    X, y,
    param_name='max_depth',
    param_range=param_range,
    cv=5,
    scoring='f1',
    n_jobs=-1
)

train_mean = np.mean(train_scores, axis=1)
val_mean = np.mean(val_scores, axis=1)

plt.figure()
plt.plot(param_range, train_mean, 'o-', label='Training')
plt.plot(param_range, val_mean, 'o-', label='Validation')
plt.xlabel('max_depth')
plt.ylabel('F1 Score')
plt.title('Validation Curve')
plt.legend()
plt.show()
```

## 9. Feature Engineering

### Numerical Features

```python
import pandas as pd
import numpy as np

def engineer_numerical_features(df, numerical_cols):
    for col in numerical_cols:
        # Log transformation (for skewed data)
        df[f'{col}_log'] = np.log1p(df[col].clip(lower=0))

        # Square root
        df[f'{col}_sqrt'] = np.sqrt(df[col].clip(lower=0))

        # Square
        df[f'{col}_squared'] = df[col] ** 2

        # Binning
        df[f'{col}_binned'] = pd.qcut(df[col], q=5, labels=False, duplicates='drop')

        # Interactions with target
        df[f'{col}_is_zero'] = (df[col] == 0).astype(int)
        df[f'{col}_is_negative'] = (df[col] < 0).astype(int)

        # Rank transformation
        df[f'{col}_rank'] = df[col].rank(pct=True)

    # Ratios and differences (if multiple related features)
    if 'price' in df and 'cost' in df:
        df['profit_margin'] = (df['price'] - df['cost']) / df['price']
        df['markup'] = df['price'] / df['cost']

    if 'start_date' in df and 'end_date' in df:
        df['duration_days'] = (df['end_date'] - df['start_date']).dt.days

    return df
```

### Categorical Features

```python
from sklearn.preprocessing import LabelEncoder, OneHotEncoder, TargetEncoder
from sklearn.feature_extraction import FeatureHasher

def engineer_categorical_features(df, cat_cols, target=None):
    for col in cat_cols:
        # Frequency encoding
        freq = df[col].value_counts() / len(df)
        df[f'{col}_freq'] = df[col].map(freq)

        # Target encoding (with smoothing)
        if target is not None:
            global_mean = target.mean()
            prior_weight = 10
            stats = target.groupby(df[col]).agg(['mean', 'count'])
            df[f'{col}_target_enc'] = df[col].map(
                (stats['count'] * stats['mean'] + prior_weight * global_mean) /
                (stats['count'] + prior_weight)
            )

        # Rare category flag
        threshold = 0.01
        rare_cats = freq[freq < threshold].index
        df[f'{col}_is_rare'] = df[col].isin(rare_cats).astype(int)

        # Missing indicator
        df[f'{col}_is_missing'] = df[col].isna().astype(int)

    return df

# One-hot encoding (for high cardinality, use k-bins or hashing)
def sparse_one_hot(df, col, max_categories=50):
    ohe = OneHotEncoder(
        handle_unknown='infrequent_if_exist',
        max_categories=max_categories,
        sparse_output=True
    )
    encoded = ohe.fit_transform(df[[col]])
    return encoded

# Feature hashing for high-cardinality
hasher = FeatureHasher(n_features=128, input_type='string')
hashed_features = hasher.transform(df[cat_cols].astype(str).values)
```

### Text Features

```python
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
import re

def engineer_text_features(texts):
    # TF-IDF with n-grams
    tfidf = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 3),
        stop_words='english',
        max_df=0.95,
        min_df=2,
        sublinear_tf=True
    )
    X_tfidf = tfidf.fit_transform(texts)

    # Additional text features
    def extract_text_features(text):
        return pd.Series({
            'char_count': len(text),
            'word_count': len(text.split()),
            'avg_word_length': np.mean([len(w) for w in text.split()]) if text else 0,
            'unique_words': len(set(text.lower().split())),
            'uppercase_ratio': sum(1 for c in text if c.isupper()) / max(len(text), 1),
            'digit_ratio': sum(1 for c in text if c.isdigit()) / max(len(text), 1),
            'exclamation_count': text.count('!'),
            'question_count': text.count('?'),
            'has_url': int(bool(re.search(r'http[s]?://', text))),
            'has_email': int(bool(re.search(r'\S+@\S+', text))),
        })

    text_features = pd.concat([extract_text_features(t) for t in texts], axis=1).T
    return X_tfidf, text_features
```

### DateTime Features

```python
def engineer_datetime_features(df, date_col):
    dates = pd.to_datetime(df[date_col])

    # Cyclical encoding
    df['hour_sin'] = np.sin(2 * np.pi * dates.dt.hour / 24)
    df['hour_cos'] = np.cos(2 * np.pi * dates.dt.hour / 24)
    df['month_sin'] = np.sin(2 * np.pi * dates.dt.month / 12)
    df['month_cos'] = np.cos(2 * np.pi * dates.dt.month / 12)
    df['day_of_week_sin'] = np.sin(2 * np.pi * dates.dt.dayofweek / 7)
    df['day_of_week_cos'] = np.cos(2 * np.pi * dates.dt.dayofweek / 7)

    # Extracted features
    df['year'] = dates.dt.year
    df['month'] = dates.dt.month
    df['day'] = dates.dt.day
    df['day_of_week'] = dates.dt.dayofweek
    df['day_of_year'] = dates.dt.dayofyear
    df['week_of_year'] = dates.dt.isocalendar().week.astype(int)
    df['quarter'] = dates.dt.quarter
    df['is_weekend'] = (dates.dt.dayofweek >= 5).astype(int)
    df['is_month_start'] = (dates.dt.day == 1).astype(int)
    df['is_month_end'] = (dates.dt.is_month_end).astype(int)
    df['is_year_start'] = dates.dt.is_year_start.astype(int)
    df['is_year_end'] = dates.dt.is_year_end.astype(int)
    df['hour'] = dates.dt.hour
    df['minute'] = dates.dt.minute

    # Time since reference
    reference = pd.Timestamp('2020-01-01')
    df['days_since_reference'] = (dates - reference).dt.days

    return df
```

## 10. Hyperparameter Tuning

### GridSearchCV

```python
from sklearn.model_selection import GridSearchCV, RandomizedSearchCV
from scipy.stats import randint, uniform

# Grid search (exhaustive)
param_grid = {
    'n_estimators': [100, 200, 500],
    'max_depth': [5, 10, 15, None],
    'min_samples_split': [2, 5, 10],
    'min_samples_leaf': [1, 2, 4],
}

grid_search = GridSearchCV(
    RandomForestRegressor(random_state=42),
    param_grid,
    cv=5,
    scoring='r2',
    n_jobs=-1,
    verbose=1
)
grid_search.fit(X_train, y_train)
print(f"Best params: {grid_search.best_params_}")
print(f"Best score: {grid_search.best_score_:.3f}")
```

### RandomizedSearchCV

```python
param_dist = {
    'n_estimators': randint(100, 1000),
    'max_depth': randint(3, 20),
    'min_samples_split': randint(2, 20),
    'min_samples_leaf': randint(1, 10),
    'max_features': uniform(0.3, 0.7),
    'bootstrap': [True, False],
}

random_search = RandomizedSearchCV(
    RandomForestRegressor(random_state=42),
    param_distributions=param_dist,
    n_iter=100,  # 100 random combinations
    cv=5,
    scoring='r2',
    n_jobs=-1,
    random_state=42,
    verbose=1
)
random_search.fit(X_train, y_train)
print(f"Best params: {random_search.best_params_}")
```

### Optuna

```python
import optuna
from optuna.samplers import TPESampler
from optuna.pruners import MedianPruner

def objective(trial):
    # Suggest hyperparameters
    params = {
        'n_estimators': trial.suggest_int('n_estimators', 100, 1000, step=50),
        'max_depth': trial.suggest_int('max_depth', 3, 20),
        'min_samples_split': trial.suggest_int('min_samples_split', 2, 20),
        'min_samples_leaf': trial.suggest_int('min_samples_leaf', 1, 10),
        'max_features': trial.suggest_float('max_features', 0.3, 1.0),
        'ccp_alpha': trial.suggest_float('ccp_alpha', 0.0, 0.1, log=True),
    }

    model = RandomForestRegressor(**params, random_state=42, n_jobs=-1)

    # Cross-validation score
    scores = cross_val_score(model, X_train, y_train, cv=5, scoring='r2')
    return scores.mean()

# Create study
study = optuna.create_study(
    direction='maximize',
    sampler=TPESampler(seed=42),
    pruner=MedianPruner()
)

study.optimize(objective, n_trials=100, show_progress_bar=True)

print(f"Best value: {study.best_value:.4f}")
print(f"Best params: {study.best_params}")

# Parameter importance
from optuna.visualization import plot_param_importances
plot_param_importances(study)

# Optimization history
from optuna.visualization import plot_optimization_history
plot_optimization_history(study)
```

### Bayesian Optimization (scikit-optimize)

```python
from skopt import BayesSearchCV
from skopt.space import Real, Integer, Categorical

opt = BayesSearchCV(
    RandomForestRegressor(random_state=42),
    {
        'n_estimators': Integer(100, 1000),
        'max_depth': Integer(3, 20),
        'min_samples_split': Integer(2, 20),
        'min_samples_leaf': Integer(1, 10),
        'max_features': Real(0.3, 1.0),
    },
    n_iter=50,
    cv=5,
    scoring='r2',
    n_jobs=-1,
    random_state=42
)
opt.fit(X_train, y_train)
print(f"Best score: {opt.best_score_:.3f}")
```

## 11. Ensemble Methods

### Stacking

```python
from sklearn.ensemble import StackingRegressor, StackingClassifier
from sklearn.linear_model import Ridge, LogisticRegression

# Stacking Regression
base_learners = [
    ('rf', RandomForestRegressor(n_estimators=200, random_state=42)),
    ('xgb', xgb.XGBRegressor(n_estimators=200, random_state=42)),
    ('lgbm', lgb.LGBMRegressor(n_estimators=200, random_state=42, verbose=-1)),
    ('gb', GradientBoostingRegressor(n_estimators=200, random_state=42)),
]

meta_learner = Ridge(alpha=1.0)

stacking = StackingRegressor(
    estimators=base_learners,
    final_estimator=meta_learner,
    cv=5,           # Out-of-fold predictions
    passthrough=False  # Include base features
)

stacking.fit(X_train, y_train)
print(f"Stacking R²: {stacking.score(X_test, y_test):.3f}")

# Voting Ensemble
from sklearn.ensemble import VotingRegressor

voting = VotingRegressor([
    ('rf', RandomForestRegressor(n_estimators=200)),
    ('xgb', xgb.XGBRegressor(n_estimators=200)),
    ('ridge', Ridge(alpha=1.0)),
], weights=[2, 2, 1])  # Weighted voting

voting.fit(X_train, y_train)
```

### Blending

```python
# Holdout blending
X_train_base, X_blend, y_train_base, y_blend = train_test_split(
    X_train, y_train, test_size=0.2, random_state=42
)

# Train base models
rf = RandomForestRegressor(n_estimators=200).fit(X_train_base, y_train_base)
xgb_model = xgb.XGBRegressor(n_estimators=200).fit(X_train_base, y_train_base)

# Generate blend features
rf_blend_pred = rf.predict(X_blend)
xgb_blend_pred = xgb_model.predict(X_blend)

# Stack predictions as features for meta model
blend_features = np.column_stack([rf_blend_pred, xgb_blend_pred])
meta_model = Ridge(alpha=1.0).fit(blend_features, y_blend)

# Final prediction
rf_test_pred = rf.predict(X_test)
xgb_test_pred = xgb_model.predict(X_test)
test_features = np.column_stack([rf_test_pred, xgb_test_pred])
final_pred = meta_model.predict(test_features)
```

## 12. AutoML

```python
# TPOT
from tpot import TPOTRegressor

tpot = TPOTRegressor(
    generations=5,
    population_size=50,
    scoring='r2',
    cv=5,
    random_state=42,
    verbosity=2,
    n_jobs=-1
)
tpot.fit(X_train, y_train)
print(f"TPOT R²: {tpot.score(X_test, y_test):.3f}")
tpot.export('tpot_best_pipeline.py')

# AutoGluon
# from autogluon.tabular import TabularPredictor
# predictor = TabularPredictor(label='target').fit(
#     'train.csv',
#     time_limit=3600,
#     presets='best_quality'
# )
```

## Pipeline Best Practices

```python
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer

# Full preprocessing pipeline
numeric_features = ['age', 'income', 'hours_per_week']
categorical_features = ['education', 'occupation', 'marital_status']
text_features = ['description']

numeric_transformer = Pipeline([
    ('imputer', SimpleImputer(strategy='median')),
    ('scaler', StandardScaler()),
])

categorical_transformer = Pipeline([
    ('imputer', SimpleImputer(strategy='constant', fill_value='missing')),
    ('encoder', OneHotEncoder(handle_unknown='infrequent_if_exist', max_categories=20)),
])

preprocessor = ColumnTransformer([
    ('numeric', numeric_transformer, numeric_features),
    ('categorical', categorical_transformer, categorical_features),
])

# Full pipeline
pipeline = Pipeline([
    ('preprocessor', preprocessor),
    ('classifier', RandomForestClassifier(n_estimators=200, random_state=42)),
])

# Grid search over pipeline parameters
param_grid = {
    'classifier__n_estimators': [100, 200, 500],
    'classifier__max_depth': [5, 10, None],
    'preprocessor__numeric__imputer__strategy': ['mean', 'median'],
}

grid = GridSearchCV(pipeline, param_grid, cv=5, scoring='f1', n_jobs=-1)
grid.fit(X_train, y_train)

# Save pipeline
import joblib
joblib.dump(grid.best_estimator_, 'model_pipeline.pkl')
loaded = joblib.load('model_pipeline.pkl')
predictions = loaded.predict(X_new)
```
