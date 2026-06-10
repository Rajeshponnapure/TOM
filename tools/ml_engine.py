"""
TOM MLEngine — Universal Machine Learning Engine.
Implements EVERY major ML algorithm: regression, classification, clustering,
ensemble, dimensionality reduction, deep learning, time series, anomaly detection,
feature engineering, hyperparameter tuning, evaluation, cross validation.
"""

import numpy as np
import warnings
import json
import time
import math
import itertools
from collections import Counter
from copy import deepcopy

warnings.filterwarnings("ignore")

# ============================================================
# BACKEND DETECTION
# ============================================================

_HAS_SKLEARN = True
_HAS_XGBOOST = False
_HAS_LIGHTGBM = False
_HAS_CATBOOST = False
_HAS_TORCH = False
_HAS_TF = False
_HAS_STATS = False
_HAS_UMAP = False
_HAS_SKOPT = False
_HAS_PROPHET = False
_HAS_PANDAS = False
_HAS_SCIPY = False
_HAS_MATPLOTLIB = False

try:
    import sklearn
    from sklearn import linear_model
    from sklearn import svm
    from sklearn import tree
    from sklearn import ensemble
    from sklearn import neighbors
    from sklearn import naive_bayes
    from sklearn import discriminant_analysis
    from sklearn import cluster as sklearn_cluster
    from sklearn import mixture
    from sklearn import decomposition
    from sklearn import manifold
    from sklearn import feature_selection
    from sklearn import preprocessing
    from sklearn import model_selection
    from sklearn import metrics
    from sklearn import pipeline
    from sklearn import neural_network
    from sklearn import covariance
    from sklearn import feature_extraction
    from sklearn import gaussian_process
    # HalvingGridSearchCV is experimental
    from sklearn.experimental import enable_halving_search_cv
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False

try:
    import xgboost
    _HAS_XGBOOST = True
except ImportError:
    pass

try:
    import lightgbm
    _HAS_LIGHTGBM = True
except ImportError:
    pass

try:
    import catboost
    _HAS_CATBOOST = True
except ImportError:
    pass

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset
    _HAS_TORCH = True
except ImportError:
    pass

try:
    import tensorflow as tf
    _HAS_TF = True
except ImportError:
    pass

try:
    import statsmodels.api as sm
    from statsmodels.tsa.arima.model import ARIMA as StatsARIMA
    from statsmodels.tsa.holtwinters import ExponentialSmoothing as StatsHoltWinters
    from statsmodels.tsa.seasonal import seasonal_decompose
    from statsmodels.tsa.stattools import acf, pacf, adfuller
    _HAS_STATS = True
except ImportError:
    pass

try:
    import umap
    _HAS_UMAP = True
except ImportError:
    pass

try:
    import skopt
    _HAS_SKOPT = True
except ImportError:
    pass

try:
    from fbprophet import Prophet
    _HAS_PROPHET = True
except ImportError:
    try:
        from prophet import Prophet
        _HAS_PROPHET = True
    except ImportError:
        pass

try:
    import pandas as pd
    _HAS_PANDAS = True
except ImportError:
    pass

try:
    import scipy
    from scipy import sparse
    from scipy.spatial.distance import cdist, pdist, squareform
    from scipy.stats import mode
    _HAS_SCIPY = True
except ImportError:
    pass

try:
    import matplotlib.pyplot as plt
    _HAS_MATPLOTLIB = True
except ImportError:
    pass

# ============================================================
# PURE PYTHON FALLBACK IMPLEMENTATIONS
# ============================================================

if not _HAS_SKLEARN:

    class _LinearRegressionScratch:
        """Linear regression using numpy lstsq."""
        def __init__(self, fit_intercept=True):
            self.fit_intercept = fit_intercept
            self.coef_ = None
            self.intercept_ = 0.0

        def fit(self, X, y):
            if self.fit_intercept:
                X = np.column_stack([np.ones(X.shape[0]), X])
            self.coef_ = np.linalg.lstsq(X, y, rcond=None)[0]
            if self.fit_intercept:
                self.intercept_ = self.coef_[0]
                self.coef_ = self.coef_[1:]
            return self

        def predict(self, X):
            return X @ self.coef_ + self.intercept_

    class _KMeansScratch:
        """K-Means clustering from scratch with k-means++ initialization."""
        def __init__(self, n_clusters=8, max_iter=300, tol=1e-4, random_state=42):
            self.n_clusters = n_clusters
            self.max_iter = max_iter
            self.tol = tol
            self.random_state = random_state
            self.cluster_centers_ = None
            self.labels_ = None
            self.inertia_ = None
            self.rng = np.random.RandomState(random_state)

        def _kmeans_plus_plus(self, X):
            n_samples = X.shape[0]
            centers = [X[self.rng.randint(n_samples)]]
            for _ in range(1, self.n_clusters):
                dists = np.min([np.sum((X - c) ** 2, axis=1) for c in centers], axis=0)
                probs = dists / dists.sum()
                centers.append(X[self.rng.choice(n_samples, p=probs)])
            return np.array(centers)

        def fit(self, X):
            self.cluster_centers_ = self._kmeans_plus_plus(X)
            for _ in range(self.max_iter):
                dists = np.array([np.sum((X - c) ** 2, axis=1) for c in self.cluster_centers_])
                self.labels_ = np.argmin(dists, axis=0)
                new_centers = np.array([X[self.labels_ == k].mean(axis=0)
                                        for k in range(self.n_clusters)])
                shift = np.sum((new_centers - self.cluster_centers_) ** 2)
                self.cluster_centers_ = new_centers
                if shift < self.tol:
                    break
            dists = np.array([np.sum((X - c) ** 2, axis=1) for c in self.cluster_centers_])
            self.labels_ = np.argmin(dists, axis=0)
            self.inertia_ = np.sum(np.min(dists, axis=0))
            return self

        def predict(self, X):
            dists = np.array([np.sum((X - c) ** 2, axis=1) for c in self.cluster_centers_])
            return np.argmin(dists, axis=0)

    class _KNNScratch:
        """K-Nearest Neighbors from scratch."""
        def __init__(self, n_neighbors=5, weights='uniform', task='classification'):
            self.n_neighbors = n_neighbors
            self.weights = weights
            self.task = task
            self.X_train = None
            self.y_train = None

        def fit(self, X, y):
            self.X_train = np.asarray(X)
            self.y_train = np.asarray(y)
            self.n_classes = len(np.unique(y)) if self.task == 'classification' else None
            return self

        def predict(self, X):
            X = np.asarray(X)
            preds = []
            for x in X:
                dists = np.sum((self.X_train - x) ** 2, axis=1)
                idx = np.argsort(dists)[:self.n_neighbors]
                neighbor_dists = dists[idx]
                neighbor_labels = self.y_train[idx]
                if self.task == 'classification':
                    if self.weights == 'distance':
                        with np.errstate(divide='ignore'):
                            w = 1.0 / (neighbor_dists + 1e-10)
                        weighted_votes = {}
                        for i, lbl in enumerate(neighbor_labels):
                            weighted_votes[lbl] = weighted_votes.get(lbl, 0) + w[i]
                        preds.append(max(weighted_votes, key=weighted_votes.get))
                    else:
                        preds.append(Counter(neighbor_labels).most_common(1)[0][0])
                else:
                    if self.weights == 'distance':
                        with np.errstate(divide='ignore'):
                            w = 1.0 / (neighbor_dists + 1e-10)
                        preds.append(np.average(neighbor_labels, weights=w))
                    else:
                        preds.append(np.mean(neighbor_labels))
            return np.array(preds)

    class _NaiveBayesScratch:
        """Gaussian Naive Bayes from scratch."""
        def __init__(self, var_smoothing=1e-9):
            self.var_smoothing = var_smoothing
            self.classes_ = None
            self.theta_ = None
            self.sigma_ = None
            self.class_prior_ = None

        def fit(self, X, y):
            X = np.asarray(X)
            y = np.asarray(y)
            self.classes_ = np.unique(y)
            n_features = X.shape[1]
            self.theta_ = np.zeros((len(self.classes_), n_features))
            self.sigma_ = np.zeros((len(self.classes_), n_features))
            self.class_prior_ = np.zeros(len(self.classes_))
            for i, c in enumerate(self.classes_):
                X_c = X[y == c]
                self.theta_[i] = X_c.mean(axis=0)
                self.sigma_[i] = X_c.var(axis=0) + self.var_smoothing
                self.class_prior_[i] = len(X_c) / len(y)
            return self

        def predict(self, X):
            X = np.asarray(X)
            n_classes = len(self.classes_)
            log_probs = np.zeros((X.shape[0], n_classes))
            for i in range(n_classes):
                diff = X - self.theta_[i]
                log_likelihood = -0.5 * np.sum(
                    np.log(2 * np.pi * self.sigma_[i]) + (diff ** 2) / self.sigma_[i], axis=1
                )
                log_probs[:, i] = np.log(self.class_prior_[i] + 1e-10) + log_likelihood
            return self.classes_[np.argmax(log_probs, axis=1)]

        def predict_proba(self, X):
            X = np.asarray(X)
            n_classes = len(self.classes_)
            log_probs = np.zeros((X.shape[0], n_classes))
            for i in range(n_classes):
                diff = X - self.theta_[i]
                log_likelihood = -0.5 * np.sum(
                    np.log(2 * np.pi * self.sigma_[i]) + (diff ** 2) / self.sigma_[i], axis=1
                )
                log_probs[:, i] = np.log(self.class_prior_[i] + 1e-10) + log_likelihood
            log_probs -= log_probs.max(axis=1, keepdims=True)
            probs = np.exp(log_probs)
            return probs / probs.sum(axis=1, keepdims=True)

    class _DecisionTreeScratch:
        """Decision Tree from scratch for classification and regression."""
        class _Node:
            def __init__(self):
                self.feature = None
                self.threshold = None
                self.left = None
                self.right = None
                self.value = None
                self.impurity = 0.0

        def __init__(self, max_depth=None, min_samples_split=2, min_samples_leaf=1, task='classification'):
            self.max_depth = max_depth
            self.min_samples_split = min_samples_split
            self.min_samples_leaf = min_samples_leaf
            self.task = task
            self.root = None
            self.n_features_ = None
            self.n_classes_ = None

        def _gini(self, y):
            _, counts = np.unique(y, return_counts=True)
            probs = counts / counts.sum()
            return 1.0 - np.sum(probs ** 2)

        def _mse(self, y):
            return np.mean((y - np.mean(y)) ** 2)

        def _impurity(self, y):
            if self.task == 'classification':
                return self._gini(y)
            return self._mse(y)

        def _leaf_value(self, y):
            if self.task == 'classification':
                return Counter(y).most_common(1)[0][0]
            return np.mean(y)

        def _best_split(self, X, y):
            best_feat, best_thresh = None, None
            best_impurity = float('inf')
            n_samples, n_features = X.shape
            m = len(y)
            current_impurity = self._impurity(y)

            for feat in range(n_features):
                col = X[:, feat]
                unique_vals = np.unique(col)
                if len(unique_vals) < 2:
                    continue
                candidates = (unique_vals[1:] + unique_vals[:-1]) / 2.0
                for thresh in candidates:
                    left = y[col <= thresh]
                    right = y[col > thresh]
                    if len(left) < self.min_samples_leaf or len(right) < self.min_samples_leaf:
                        continue
                    weighted = (len(left) * self._impurity(left) + len(right) * self._impurity(right)) / m
                    if weighted < best_impurity:
                        best_impurity = weighted
                        best_feat = feat
                        best_thresh = thresh
            if best_feat is None:
                return None, None, current_impurity
            gain = current_impurity - best_impurity
            return best_feat, best_thresh, gain

        def _build_tree(self, X, y, depth=0):
            node = self._Node()
            if len(np.unique(y)) == 1 or len(y) < self.min_samples_split:
                node.value = self._leaf_value(y)
                return node
            if self.max_depth is not None and depth >= self.max_depth:
                node.value = self._leaf_value(y)
                return node

            feat, thresh, gain = self._best_split(X, y)
            if feat is None:
                node.value = self._leaf_value(y)
                return node

            node.feature = feat
            node.threshold = thresh
            node.impurity = gain
            left_idx = X[:, feat] <= thresh
            right_idx = X[:, feat] > thresh
            node.left = self._build_tree(X[left_idx], y[left_idx], depth + 1)
            node.right = self._build_tree(X[right_idx], y[right_idx], depth + 1)
            return node

        def fit(self, X, y):
            X = np.asarray(X)
            y = np.asarray(y)
            self.n_features_ = X.shape[1]
            if self.task == 'classification':
                self.n_classes_ = len(np.unique(y))
            self.root = self._build_tree(X, y)
            return self

        def _predict_one(self, x, node):
            if node.value is not None:
                return node.value
            if x[node.feature] <= node.threshold:
                return self._predict_one(x, node.left)
            return self._predict_one(x, node.right)

        def predict(self, X):
            X = np.asarray(X)
            return np.array([self._predict_one(x, self.root) for x in X])


# ============================================================
# PYTORCH DEEP LEARNING HELPERS
# ============================================================

if _HAS_TORCH:
    class _TorchMLP(nn.Module):
        def __init__(self, input_dim, hidden_dims, output_dim, dropout=0.0):
            super().__init__()
            layers = []
            prev = input_dim
            for h in hidden_dims:
                layers.append(nn.Linear(prev, h))
                layers.append(nn.ReLU())
                if dropout > 0:
                    layers.append(nn.Dropout(dropout))
                prev = h
            layers.append(nn.Linear(prev, output_dim))
            self.net = nn.Sequential(*layers)

        def forward(self, x):
            return self.net(x)

    class _TorchAutoencoder(nn.Module):
        def __init__(self, input_dim, encoding_dim, hidden_dims=None):
            super().__init__()
            if hidden_dims is None:
                hidden_dims = [max(input_dim // 2, encoding_dim + 8)]
            encoder_layers = []
            prev = input_dim
            for h in hidden_dims:
                encoder_layers.append(nn.Linear(prev, h))
                encoder_layers.append(nn.ReLU())
                prev = h
            encoder_layers.append(nn.Linear(prev, encoding_dim))
            self.encoder = nn.Sequential(*encoder_layers)

            decoder_layers = []
            prev = encoding_dim
            for h in reversed(hidden_dims):
                decoder_layers.append(nn.Linear(prev, h))
                decoder_layers.append(nn.ReLU())
                prev = h
            decoder_layers.append(nn.Linear(prev, input_dim))
            self.decoder = nn.Sequential(*decoder_layers)

        def forward(self, x):
            encoded = self.encoder(x)
            decoded = self.decoder(encoded)
            return decoded

        def encode(self, x):
            return self.encoder(x)


# ============================================================
# MLEngine CLASS
# ============================================================

class MLEngine:
    """
    Universal ML Engine — ALL algorithms, ALL tasks.

    Provides a unified interface for regression, classification, clustering,
    dimensionality reduction, deep learning, time series, anomaly detection,
    ensemble methods, feature engineering, hyperparameter tuning, evaluation,
    cross validation, auto-ML, and explainability.

    Parameters
    ----------
    random_state : int, default=42
        Random state for reproducibility.
    verbose : bool, default=False
        If True, print progress messages.
    """

    def __init__(self, random_state=42, verbose=False):
        self.random_state = random_state
        self.verbose = verbose
        self.rng = np.random.RandomState(random_state)

    # ------------------------------------------------------------------
    # INTERNAL HELPERS
    # ------------------------------------------------------------------

    def _log(self, msg):
        if self.verbose:
            print(f"[MLEngine] {msg}")

    def _auto_detect_task(self, y):
        """Auto-detect whether y is continuous (regression) or categorical (classification)."""
        y = np.asarray(y).ravel()
        nunique = len(np.unique(y))
        if y.dtype.kind in ('i', 'u', 'b') or nunique <= 15:
            return 'classification'
        # If float with few unique values relative to size, treat as classification
        if y.dtype.kind == 'f' and nunique <= 20 and nunique / len(y) < 0.05:
            return 'classification'
        return 'regression'

    def _ensure_2d(self, X):
        X = np.asarray(X, dtype=float)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        return X

    def _safe_init(self, cls, params):
        """Initialize a class, safely handling params the constructor doesn't accept."""
        try:
            return cls(**params)
        except TypeError:
            cleaned = {k: v for k, v in params.items() if k not in ('random_state',)}
            try:
                return cls(**cleaned)
            except TypeError:
                raise

    def _check_sklearn(self):
        if not _HAS_SKLEARN:
            return {"status": "error", "result": None, "message": "scikit-learn is required for this operation but not installed."}
        return None

    def _check_torch(self):
        if not _HAS_TORCH:
            return {"status": "error", "result": None, "message": "PyTorch is required for this operation but not installed."}
        return None

    def _get_algorithm_registry(self):
        """Return dicts mapping algorithm names to sklearn classes (and fallbacks)."""
        reg = {}

        if _HAS_SKLEARN:
            reg['regression'] = {
                'linearregression': sklearn.linear_model.LinearRegression,
                'ridge': sklearn.linear_model.Ridge,
                'lasso': sklearn.linear_model.Lasso,
                'elasticnet': sklearn.linear_model.ElasticNet,
                'svr': sklearn.svm.SVR,
                'decisiontreeregressor': sklearn.tree.DecisionTreeRegressor,
                'randomforestregressor': sklearn.ensemble.RandomForestRegressor,
                'gradientboostingregressor': sklearn.ensemble.GradientBoostingRegressor,
                'adaboostregressor': sklearn.ensemble.AdaBoostRegressor,
                'huberregressor': sklearn.linear_model.HuberRegressor,
                'bayesianridge': sklearn.linear_model.BayesianRidge,
                'kernelridge': sklearn.kernel_ridge.KernelRidge,
            }
            if _HAS_XGBOOST:
                reg['regression']['xgboostregressor'] = xgboost.XGBRegressor
            reg['classification'] = {
                'logisticregression': sklearn.linear_model.LogisticRegression,
                'knn': sklearn.neighbors.KNeighborsClassifier,
                'svc': sklearn.svm.SVC,
                'decisiontreeclassifier': sklearn.tree.DecisionTreeClassifier,
                'randomforestclassifier': sklearn.ensemble.RandomForestClassifier,
                'gradientboostingclassifier': sklearn.ensemble.GradientBoostingClassifier,
                'adaboostclassifier': sklearn.ensemble.AdaBoostClassifier,
                'naivebayes': sklearn.naive_bayes.GaussianNB,
                'bernoullinb': sklearn.naive_bayes.BernoulliNB,
                'multinomialnb': sklearn.naive_bayes.MultinomialNB,
                'sgdclassifier': sklearn.linear_model.SGDClassifier,
                'ridgeclassifier': sklearn.linear_model.RidgeClassifier,
                'passiveaggressiveclassifier': sklearn.linear_model.PassiveAggressiveClassifier,
                'lineardiscriminantanalysis': sklearn.discriminant_analysis.LinearDiscriminantAnalysis,
                'quadraticdiscriminantanalysis': sklearn.discriminant_analysis.QuadraticDiscriminantAnalysis,
            }
            if _HAS_XGBOOST:
                reg['classification']['xgboostclassifier'] = xgboost.XGBClassifier
            reg['clustering'] = {
                'kmeans': sklearn.cluster.KMeans,
                'dbscan': sklearn.cluster.DBSCAN,
                'agglomerative': sklearn.cluster.AgglomerativeClustering,
                'gaussianmixture': sklearn.mixture.GaussianMixture,
                'meanshift': sklearn.cluster.MeanShift,
                'optics': sklearn.cluster.OPTICS,
                'affinitypropagation': sklearn.cluster.AffinityPropagation,
                'spectralclustering': sklearn.cluster.SpectralClustering,
                'birch': sklearn.cluster.Birch,
                'minibatchkmeans': sklearn.cluster.MiniBatchKMeans,
            }
            reg['dim_reduction'] = {
                'pca': sklearn.decomposition.PCA,
                'lda': sklearn.discriminant_analysis.LinearDiscriminantAnalysis,
                'truncatedsvd': sklearn.decomposition.TruncatedSVD,
                'factoranalysis': sklearn.decomposition.FactorAnalysis,
                'nmf': sklearn.decomposition.NMF,
                'isomap': sklearn.manifold.Isomap,
            }
            reg['ensemble'] = {
                'votingclassifier': sklearn.ensemble.VotingClassifier,
                'votingregressor': sklearn.ensemble.VotingRegressor,
                'stackingclassifier': sklearn.ensemble.StackingClassifier,
                'stackingregressor': sklearn.ensemble.StackingRegressor,
                'baggingclassifier': sklearn.ensemble.BaggingClassifier,
                'baggingregressor': sklearn.ensemble.BaggingRegressor,
            }
            reg['anomaly'] = {
                'isolationforest': sklearn.ensemble.IsolationForest,
                'lof': sklearn.neighbors.LocalOutlierFactor,
                'oneclasssvm': sklearn.svm.OneClassSVM,
                'ellipticenvelope': sklearn.covariance.EllipticEnvelope,
            }
            reg['feature_engineering'] = {
                'polynomialfeatures': sklearn.preprocessing.PolynomialFeatures,
                'standardscaler': sklearn.preprocessing.StandardScaler,
                'minmaxscaler': sklearn.preprocessing.MinMaxScaler,
                'robustscaler': sklearn.preprocessing.RobustScaler,
                'normalizer': sklearn.preprocessing.Normalizer,
                'labelencoder': sklearn.preprocessing.LabelEncoder,
                'onehotencoder': sklearn.preprocessing.OneHotEncoder,
                'ordinalencoder': sklearn.preprocessing.OrdinalEncoder,
                'variancethreshold': sklearn.feature_selection.VarianceThreshold,
                'selectkbest': sklearn.feature_selection.SelectKBest,
                'rfe': sklearn.feature_selection.RFE,
            }
            reg['cv'] = {
                'kfold': sklearn.model_selection.KFold,
                'stratifiedkfold': sklearn.model_selection.StratifiedKFold,
                'groupkfold': sklearn.model_selection.GroupKFold,
                'timeseriessplit': sklearn.model_selection.TimeSeriesSplit,
                'leaveoneout': sklearn.model_selection.LeaveOneOut,
                'repeatedkfold': sklearn.model_selection.RepeatedKFold,
            }
            reg['tuning'] = {
                'gridsearchcv': sklearn.model_selection.GridSearchCV,
                'randomizedsearchcv': sklearn.model_selection.RandomizedSearchCV,
                'halvinggridsearchcv': sklearn.model_selection.HalvingGridSearchCV,
            }

        return reg

    def _get_sklearn_registry(self):
        return self._get_algorithm_registry()

    # ------------------------------------------------------------------
    # REGRESSION
    # ------------------------------------------------------------------

    def regression(self, algorithm, X, y, **params):
        """
        Train a regression model.

        Parameters
        ----------
        algorithm : str
            One of: linearregression, polynomialregression, ridge, lasso, elasticnet,
            svr, decisiontreeregressor, randomforestregressor, gradientboostingregressor,
            adaboostregressor, xgboostregressor, huberregressor, bayesianridge, kernelridge.
        X : array-like of shape (n_samples, n_features)
            Training data.
        y : array-like of shape (n_samples,)
            Target values.
        **params : dict
            Additional parameters passed to the model constructor.

        Returns
        -------
        dict with keys: status, result (trained model object), message, metrics (optional).
        """
        try:
            X = self._ensure_2d(X)
            y = np.asarray(y).ravel()
            algo = algorithm.lower().replace(" ", "").replace("-", "").replace("_", "")

            if algo == 'polynomialregression':
                degree = params.pop('degree', 2)
                include_bias = params.pop('include_bias', False)
                if _HAS_SKLEARN:
                    from sklearn.preprocessing import PolynomialFeatures
                    from sklearn.linear_model import LinearRegression
                    poly = PolynomialFeatures(degree=degree, include_bias=include_bias)
                    X_poly = poly.fit_transform(X)
                    model = LinearRegression(**{k: v for k, v in params.items() if k != 'random_state'})
                    model.fit(X_poly, y)
                    model.poly_features_ = poly
                else:
                    # pure python poly features
                    X_poly = self._poly_features(X, degree, include_bias)
                    model = _LinearRegressionScratch(**{k: v for k, v in params.items() if k in ['fit_intercept']})
                    model.fit(X_poly, y)
                    model.poly_degree_ = degree
                y_pred = model.predict(X_poly if _HAS_SKLEARN else X_poly)
                metrics_dict = self._compute_regression_metrics(y, y_pred)
                return {"status": "success", "result": model, "message": f"PolynomialRegression (degree={degree}) trained successfully.", "metrics": metrics_dict}

            if not _HAS_SKLEARN:
                if algo == 'linearregression':
                    model = _LinearRegressionScratch(**{k: v for k, v in params.items() if k in ['fit_intercept']})
                    model.fit(X, y)
                    y_pred = model.predict(X)
                    metrics_dict = self._compute_regression_metrics(y, y_pred)
                    return {"status": "success", "result": model, "message": "LinearRegression trained successfully.", "metrics": metrics_dict}
                return {"status": "error", "result": None, "message": f"Algorithm '{algorithm}' requires scikit-learn."}

            err = self._check_sklearn()
            if err:
                return err

            registry = self._get_sklearn_registry()['regression']
            if algo not in registry:
                available = list(registry.keys()) + ['polynomialregression']
                return {"status": "error", "result": None, "message": f"Unknown regression algorithm '{algorithm}'. Available: {available}"}

            ModelClass = registry[algo]
            model = self._safe_init(ModelClass, params)
            model.fit(X, y)
            y_pred = model.predict(X)
            metrics_dict = self._compute_regression_metrics(y, y_pred)
            return {"status": "success", "result": model, "message": f"{algorithm} trained successfully.", "metrics": metrics_dict}

        except Exception as e:
            return {"status": "error", "result": None, "message": f"Regression error: {str(e)}"}

    def _poly_features(self, X, degree, include_bias=False):
        """Generate polynomial features from scratch."""
        n_samples, n_features = X.shape
        combinations = []
        for d in range(1, degree + 1):
            for combo in itertools.combinations_with_replacement(range(n_features), d):
                combinations.append(combo)
        result = []
        if include_bias:
            result.append(np.ones(n_samples))
        for combo in combinations:
            feat = np.ones(n_samples)
            for idx in combo:
                feat *= X[:, idx]
            result.append(feat)
        return np.column_stack(result)

    def _compute_regression_metrics(self, y_true, y_pred):
        """Compute regression metrics."""
        y_true = np.asarray(y_true).ravel()
        y_pred = np.asarray(y_pred).ravel()
        n = len(y_true)
        residuals = y_true - y_pred
        mse = np.mean(residuals ** 2)
        rmse = np.sqrt(mse)
        mae = np.mean(np.abs(residuals))
        ss_res = np.sum(residuals ** 2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
        r2 = 1 - (ss_res / (ss_tot + 1e-15))
        ev = 1 - (np.var(residuals) / (np.var(y_true) + 1e-15))
        mape = np.mean(np.abs(residuals / (np.abs(y_true) + 1e-10))) * 100
        return {
            "mse": float(mse), "rmse": float(rmse), "mae": float(mae),
            "r2": float(r2), "explained_variance": float(ev), "mape": float(mape)
        }

    # ------------------------------------------------------------------
    # CLASSIFICATION
    # ------------------------------------------------------------------

    def classify(self, algorithm, X, y, **params):
        """
        Train a classification model.

        Parameters
        ----------
        algorithm : str
            One of: logisticregression, knn, svc, decisiontreeclassifier,
            randomforestclassifier, gradientboostingclassifier, adaboostclassifier,
            xgboostclassifier, naivebayes, bernoullinb, multinomialnb, sgdclassifier,
            ridgeclassifier, passiveaggressiveclassifier, lineardiscriminantanalysis,
            quadraticdiscriminantanalysis.
        X : array-like of shape (n_samples, n_features)
            Training data.
        y : array-like of shape (n_samples,)
            Target labels.
        **params : dict
            Additional parameters passed to the model constructor.

        Returns
        -------
        dict with keys: status, result, message, metrics (optional).
        """
        try:
            X = self._ensure_2d(X)
            y = np.asarray(y).ravel()
            algo = algorithm.lower().replace(" ", "").replace("-", "").replace("_", "")

            if not _HAS_SKLEARN:
                if algo in ('knn',):
                    model = _KNNScratch(n_neighbors=params.get('n_neighbors', 5), weights=params.get('weights', 'uniform'), task='classification')
                    model.fit(X, y)
                    y_pred = model.predict(X)
                    metrics_dict = self._compute_classification_metrics(y, y_pred)
                    return {"status": "success", "result": model, "message": "KNN trained successfully.", "metrics": metrics_dict}
                if algo in ('naivebayes',):
                    model = _NaiveBayesScratch(var_smoothing=params.get('var_smoothing', 1e-9))
                    model.fit(X, y)
                    y_pred = model.predict(X)
                    metrics_dict = self._compute_classification_metrics(y, y_pred)
                    return {"status": "success", "result": model, "message": "NaiveBayes trained successfully.", "metrics": metrics_dict}
                if algo in ('decisiontreeclassifier',):
                    model = _DecisionTreeScratch(max_depth=params.get('max_depth'), min_samples_split=params.get('min_samples_split', 2), min_samples_leaf=params.get('min_samples_leaf', 1), task='classification')
                    model.fit(X, y)
                    y_pred = model.predict(X)
                    metrics_dict = self._compute_classification_metrics(y, y_pred)
                    return {"status": "success", "result": model, "message": "DecisionTreeClassifier trained successfully.", "metrics": metrics_dict}
                if algo in ('logisticregression', 'svc', 'randomforestclassifier', 'gradientboostingclassifier', 'adaboostclassifier'):
                    return {"status": "error", "result": None, "message": f"Algorithm '{algorithm}' requires scikit-learn."}
                return {"status": "error", "result": None, "message": f"Unknown classification algorithm '{algorithm}'."}

            err = self._check_sklearn()
            if err:
                return err

            registry = self._get_sklearn_registry()['classification']
            if algo not in registry:
                available = list(registry.keys())
                return {"status": "error", "result": None, "message": f"Unknown classification algorithm '{algorithm}'. Available: {available}"}

            ModelClass = registry[algo]
            model = self._safe_init(ModelClass, params)
            model.fit(X, y)
            y_pred = model.predict(X)
            try:
                y_prob = model.predict_proba(X)
            except Exception:
                y_prob = None
            metrics_dict = self._compute_classification_metrics(y, y_pred, y_prob)
            return {"status": "success", "result": model, "message": f"{algorithm} trained successfully.", "metrics": metrics_dict}

        except Exception as e:
            return {"status": "error", "result": None, "message": f"Classification error: {str(e)}"}

    def _compute_classification_metrics(self, y_true, y_pred, y_prob=None):
        """Compute classification metrics."""
        y_true = np.asarray(y_true).ravel()
        y_pred = np.asarray(y_pred).ravel()
        n = len(y_true)
        classes = np.unique(np.concatenate([y_true, y_pred]))
        n_classes = len(classes)

        accuracy = np.mean(y_true == y_pred)
        confusion = np.zeros((n_classes, n_classes), dtype=int)
        label_to_idx = {lbl: i for i, lbl in enumerate(classes)}
        for t, p in zip(y_true, y_pred):
            confusion[label_to_idx[t], label_to_idx[p]] += 1

        precision = {}
        recall = {}
        f1 = {}
        support = {}
        for i, c in enumerate(classes):
            tp = confusion[i, i]
            fp = confusion[:, i].sum() - tp
            fn = confusion[i, :].sum() - tp
            support[c] = int((y_true == c).sum())
            precision[c] = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
            recall[c] = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
            f1[c] = float(2 * precision[c] * recall[c] / (precision[c] + recall[c])) if (precision[c] + recall[c]) > 0 else 0.0

        macro_precision = np.mean(list(precision.values()))
        macro_recall = np.mean(list(recall.values()))
        macro_f1 = np.mean(list(f1.values()))
        weighted_precision = np.average(list(precision.values()), weights=[support[c] for c in classes])
        weighted_recall = np.average(list(recall.values()), weights=[support[c] for c in classes])
        weighted_f1 = np.average(list(f1.values()), weights=[support[c] for c in classes])

        metrics = {
            "accuracy": float(accuracy), "macro_precision": float(macro_precision),
            "macro_recall": float(macro_recall), "macro_f1": float(macro_f1),
            "weighted_precision": float(weighted_precision), "weighted_recall": float(weighted_recall),
            "weighted_f1": float(weighted_f1), "n_classes": int(n_classes),
            "classes": [str(c) for c in classes], "support": {str(c): int(s) for c, s in zip(classes, [support[c] for c in classes])},
            "confusion_matrix": confusion.tolist(),
            "classification_report": {str(c): {"precision": precision[c], "recall": recall[c], "f1": f1[c], "support": support[c]} for c in classes},
        }

        if y_prob is not None:
            try:
                from sklearn.metrics import roc_auc_score, log_loss
                if n_classes == 2:
                    metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob[:, 1]))
                else:
                    metrics["roc_auc"] = float(roc_auc_score(y_true, y_prob, multi_class='ovr'))
                metrics["log_loss"] = float(log_loss(y_true, y_prob))
            except Exception:
                pass

        return metrics

    # ------------------------------------------------------------------
    # CLUSTERING
    # ------------------------------------------------------------------

    def cluster(self, algorithm, X, **params):
        """
        Perform clustering.

        Parameters
        ----------
        algorithm : str
            One of: kmeans, dbscan, agglomerative, gaussianmixture, meanshift,
            optics, affinitypropagation, spectralclustering, birch, minibatchkmeans.
        X : array-like of shape (n_samples, n_features)
            Data to cluster.
        **params : dict
            Additional parameters passed to the clustering algorithm.

        Returns
        -------
        dict with keys: status, result, message, labels (cluster assignments), metrics (optional).
        """
        try:
            X = self._ensure_2d(X)
            algo = algorithm.lower().replace(" ", "").replace("-", "").replace("_", "")

            if not _HAS_SKLEARN:
                if algo == 'kmeans':
                    n_clusters = params.pop('n_clusters', 8)
                    model = _KMeansScratch(n_clusters=n_clusters, random_state=params.get('random_state', self.random_state))
                    model.fit(X)
                    labels = model.labels_
                    sil = self._silhouette_score(X, labels)
                    return {
                        "status": "success", "result": model, "labels": labels.tolist(),
                        "message": "KMeans clustering completed.",
                        "metrics": {"silhouette_score": float(sil), "inertia": float(model.inertia_)}
                    }
                return {"status": "error", "result": None, "message": f"Clustering algorithm '{algorithm}' requires scikit-learn."}

            err = self._check_sklearn()
            if err:
                return err

            registry = self._get_sklearn_registry()['clustering']
            if algo not in registry:
                return {"status": "error", "result": None, "message": f"Unknown clustering algorithm '{algorithm}'. Available: {list(registry.keys())}"}

            if algo in ('dbscan', 'optics', 'affinitypropagation', 'meanshift', 'spectralclustering', 'agglomerative'):
                model = self._safe_init(registry[algo], params)
                model.fit(X)
                if hasattr(model, 'labels_'):
                    labels = model.labels_
                else:
                    labels = model.predict(X)
                if hasattr(model, 'cluster_centers_'):
                    centers = model.cluster_centers_.tolist()
                else:
                    centers = None
            elif algo == 'gaussianmixture':
                model = self._safe_init(registry[algo], params)
                model.fit(X)
                labels = model.predict(X)
                centers = model.means_.tolist() if hasattr(model, 'means_') else None
            else:
                if 'n_init' not in params and algo in ('kmeans', 'minibatchkmeans'):
                    params['n_init'] = 'auto'
                model = self._safe_init(registry[algo], params)
                model.fit(X)
                labels = model.labels_ if hasattr(model, 'labels_') else model.predict(X)
                centers = model.cluster_centers_.tolist() if hasattr(model, 'cluster_centers_') else None

            n_clusters_found = len(set(labels) - {-1})
            unique_labels = list(set(labels))
            n_noise = int((labels == -1).sum()) if -1 in labels else 0

            metrics_dict = {
                "n_clusters": int(n_clusters_found),
                "n_noise": n_noise,
                "unique_labels": sorted([int(x) for x in unique_labels]),
            }

            if n_clusters_found > 1:
                try:
                    sil = sklearn.metrics.silhouette_score(X, labels)
                    metrics_dict["silhouette_score"] = float(sil)
                except Exception:
                    pass
                try:
                    ch = sklearn.metrics.calinski_harabasz_score(X, labels)
                    metrics_dict["calinski_harabasz_score"] = float(ch)
                except Exception:
                    pass
                try:
                    db = sklearn.metrics.davies_bouldin_score(X, labels)
                    metrics_dict["davies_bouldin_score"] = float(db)
                except Exception:
                    pass

            result = {
                "status": "success",
                "result": model,
                "labels": [int(x) for x in labels],
                "message": f"{algorithm} clustering completed with {n_clusters_found} clusters.",
                "metrics": metrics_dict,
            }
            if centers is not None:
                result["cluster_centers"] = centers
            return result

        except Exception as e:
            return {"status": "error", "result": None, "message": f"Clustering error: {str(e)}"}

    def _silhouette_score(self, X, labels):
        """Compute silhouette score from scratch."""
        n = len(labels)
        if n < 2 or len(set(labels)) < 2:
            return -1.0
        scores = []
        for i in range(n):
            same_cluster = labels == labels[i]
            same_cluster[i] = False
            other_clusters = set(labels) - {labels[i]}
            if same_cluster.sum() == 0 or not other_clusters:
                scores.append(0)
                continue
            a = np.mean(np.sqrt(np.sum((X[i] - X[same_cluster]) ** 2, axis=1)))
            b_vals = []
            for c in other_clusters:
                mask = labels == c
                if mask.sum() > 0:
                    b_vals.append(np.mean(np.sqrt(np.sum((X[i] - X[mask]) ** 2, axis=1))))
            b = min(b_vals) if b_vals else a
            scores.append((b - a) / max(a, b))
        return float(np.mean(scores))

    # ------------------------------------------------------------------
    # DIMENSIONALITY REDUCTION
    # ------------------------------------------------------------------

    def reduce_dim(self, algorithm, X, **params):
        """
        Perform dimensionality reduction.

        Parameters
        ----------
        algorithm : str
            One of: pca, tsne, lda, truncatedsvd, factoranalysis, nmf, isomap, umap.
        X : array-like of shape (n_samples, n_features)
            Data to reduce.
        **params : dict
            Additional parameters passed to the algorithm.

        Returns
        -------
        dict with keys: status, result, transformed_data, message, metrics (optional).
        """
        try:
            X = self._ensure_2d(X)
            algo = algorithm.lower().replace(" ", "").replace("-", "").replace("_", "")

            err = self._check_sklearn()
            if err and algo != 'umap':
                if algo == 'pca':
                    return self._pca_scratch(X, **params)
                return err

            if algo == 'pca':
                if _HAS_SKLEARN:
                    from sklearn.decomposition import PCA
                    model = PCA(**params)
                    transformed = model.fit_transform(X)
                    return {
                        "status": "success", "result": model, "transformed_data": transformed.tolist(),
                        "message": "PCA completed.",
                        "metrics": {
                            "explained_variance_ratio": model.explained_variance_ratio_.tolist(),
                            "singular_values": model.singular_values_.tolist() if hasattr(model, 'singular_values_') else None,
                            "n_components": int(model.n_components_)
                        }
                    }
                else:
                    return self._pca_scratch(X, **params)

            elif algo == 'tsne':
                if _HAS_SKLEARN:
                    from sklearn.manifold import TSNE
                    if 'random_state' not in params:
                        params['random_state'] = self.random_state
                    model = TSNE(**params)
                    transformed = model.fit_transform(X)
                    return {
                        "status": "success", "result": model, "transformed_data": transformed.tolist(),
                        "message": "t-SNE completed.",
                        "metrics": {
                            "kl_divergence": float(getattr(model, 'kl_divergence_', 0)),
                            "n_iter": int(getattr(model, 'n_iter_', 0))
                        }
                    }
                return {"status": "error", "result": None, "message": "t-SNE requires scikit-learn."}

            elif algo == 'lda':
                if 'y' not in params:
                    return {"status": "error", "result": None, "message": "LDA requires target 'y' passed via params['y']."}
                y = params.pop('y')
                from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
                model = LinearDiscriminantAnalysis(**params)
                transformed = model.fit_transform(X, y)
                return {
                    "status": "success", "result": model, "transformed_data": transformed.tolist(),
                    "message": "LDA completed.",
                    "metrics": {
                        "explained_variance_ratio": model.explained_variance_ratio_.tolist() if hasattr(model, 'explained_variance_ratio_') else None
                    }
                }

            elif algo == 'truncatedsvd':
                from sklearn.decomposition import TruncatedSVD
                if 'random_state' not in params:
                    params['random_state'] = self.random_state
                model = TruncatedSVD(**params)
                transformed = model.fit_transform(X)
                return {
                    "status": "success", "result": model, "transformed_data": transformed.tolist(),
                    "message": "TruncatedSVD completed.",
                    "metrics": {"explained_variance_ratio": model.explained_variance_ratio_.tolist()}
                }

            elif algo == 'factoranalysis':
                from sklearn.decomposition import FactorAnalysis
                if 'random_state' not in params:
                    params['random_state'] = self.random_state
                model = FactorAnalysis(**params)
                transformed = model.fit_transform(X)
                return {
                    "status": "success", "result": model, "transformed_data": transformed.tolist(),
                    "message": "FactorAnalysis completed.",
                    "metrics": {
                        "noise_variance": model.noise_variance_.tolist() if hasattr(model, 'noise_variance_') else None,
                        "log_likelihood": float(getattr(model, 'loglikelihood_', 0))
                    }
                }

            elif algo == 'nmf':
                from sklearn.decomposition import NMF
                if 'random_state' not in params:
                    params['random_state'] = self.random_state
                X_pos = np.maximum(X, 0)
                if X_pos.min() < 0:
                    X_pos = X_pos - X_pos.min()
                model = NMF(**params)
                transformed = model.fit_transform(X_pos)
                return {
                    "status": "success", "result": model, "transformed_data": transformed.tolist(),
                    "message": "NMF completed.",
                    "metrics": {
                        "reconstruction_err": float(model.reconstruction_err_),
                        "n_components": int(model.n_components_)
                    }
                }

            elif algo == 'isomap':
                from sklearn.manifold import Isomap
                model = self._safe_init(Isomap, params)
                transformed = model.fit_transform(X)
                return {
                    "status": "success", "result": model, "transformed_data": transformed.tolist(),
                    "message": "Isomap completed.",
                    "metrics": {
                        "reconstruction_error": float(getattr(model, 'reconstruction_error_', 0))
                    }
                }

            elif algo == 'umap':
                if _HAS_UMAP:
                    model = umap.UMAP(**params)
                    transformed = model.fit_transform(X)
                    return {
                        "status": "success", "result": model, "transformed_data": transformed.tolist(),
                        "message": "UMAP completed.",
                        "metrics": {}
                    }
                return {"status": "error", "result": None, "message": "UMAP library not installed. Install with: pip install umap-learn"}

            else:
                return {"status": "error", "result": None, "message": f"Unknown dimensionality reduction algorithm '{algorithm}'."}

        except Exception as e:
            return {"status": "error", "result": None, "message": f"Dimensionality reduction error: {str(e)}"}

    def _pca_scratch(self, X, n_components=None, **kwargs):
        """PCA from scratch using numpy SVD."""
        X = np.asarray(X)
        n_samples, n_features = X.shape
        if n_components is None:
            n_components = min(n_samples, n_features)
        X_centered = X - X.mean(axis=0)
        U, S, Vt = np.linalg.svd(X_centered, full_matrices=False)
        components = Vt[:n_components]
        transformed = X_centered @ components.T
        explained_var = (S[:n_components] ** 2) / (S ** 2).sum()
        return {
            "status": "success",
            "result": {"components": components.tolist(), "explained_variance_ratio": explained_var.tolist()},
            "transformed_data": transformed.tolist(),
            "message": "PCA (scratch) completed.",
            "metrics": {"explained_variance_ratio": explained_var.tolist(), "n_components": int(n_components)}
        }

    # ------------------------------------------------------------------
    # DEEP LEARNING
    # ------------------------------------------------------------------

    def deep_learn(self, algorithm, X, y=None, task_type='auto', **params):
        """
        Train a deep learning model.

        Parameters
        ----------
        algorithm : str
            One of: mlpclassifier, mlpregressor, autoencoder.
        X : array-like of shape (n_samples, n_features)
            Training data.
        y : array-like of shape (n_samples,), optional
            Target values (not needed for autoencoder).
        task_type : str, default='auto'
            'classification', 'regression', or 'auto'. Ignored for autoencoder.
        **params : dict
            Additional parameters. Common: hidden_layers=[64,32], epochs=100, lr=0.001.

        Returns
        -------
        dict with keys: status, result, message, metrics (optional), history (optional).
        """
        try:
            X = self._ensure_2d(X)
            algo = algorithm.lower().replace(" ", "").replace("-", "").replace("_", "")

            # Try sklearn neural network first
            if _HAS_SKLEARN and algo in ('mlpclassifier', 'mlpregressor'):
                mlp_params = {k: v for k, v in params.items() if k not in ('epochs', 'hidden_layers', 'lr', 'batch_size', 'dropout')}
                if 'hidden_layers' in params and 'hidden_layer_sizes' not in mlp_params:
                    mlp_params['hidden_layer_sizes'] = params['hidden_layers']
                if algo == 'mlpclassifier':
                    from sklearn.neural_network import MLPClassifier
                    model = self._safe_init(MLPClassifier, mlp_params)
                    epochs = params.get('epochs', 200)
                    if hasattr(model, 'max_iter'):
                        model.max_iter = epochs
                    model.fit(X, y)
                    return {"status": "success", "result": model, "message": f"MLPClassifier trained.", "metrics": {"loss": float(model.loss_), "n_iter": int(model.n_iter_)}}
                else:
                    from sklearn.neural_network import MLPRegressor
                    model = self._safe_init(MLPRegressor, mlp_params)
                    epochs = params.get('epochs', 200)
                    if hasattr(model, 'max_iter'):
                        model.max_iter = epochs
                    model.fit(X, y)
                    return {"status": "success", "result": model, "message": f"MLPRegressor trained.", "metrics": {"loss": float(model.loss_), "n_iter": int(model.n_iter_)}}

            # PyTorch implementations
            if _HAS_TORCH:
                hidden_dims = params.get('hidden_layers', [64, 32])
                epochs = params.get('epochs', 100)
                lr = params.get('lr', 0.001)
                batch_size = params.get('batch_size', 32)
                dropout = params.get('dropout', 0.0)
                device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

                if algo == 'autoencoder':
                    encoding_dim = params.get('encoding_dim', max(2, X.shape[1] // 2))
                    model = _TorchAutoencoder(X.shape[1], encoding_dim, hidden_dims).to(device)
                    criterion = nn.MSELoss()
                    optimizer = optim.Adam(model.parameters(), lr=lr)
                    dataset = TensorDataset(torch.FloatTensor(X), torch.FloatTensor(X))
                    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
                    history = []
                    for epoch in range(epochs):
                        epoch_loss = 0.0
                        for batch_X, _ in loader:
                            batch_X = batch_X.to(device)
                            optimizer.zero_grad()
                            output = model(batch_X)
                            loss = criterion(output, batch_X)
                            loss.backward()
                            optimizer.step()
                            epoch_loss += loss.item()
                        avg_loss = epoch_loss / len(loader)
                        history.append(avg_loss)
                        if (epoch + 1) % 20 == 0:
                            self._log(f"Autoencoder epoch {epoch+1}/{epochs}, loss={avg_loss:.6f}")
                    encoded = model.encode(torch.FloatTensor(X).to(device)).detach().cpu().numpy()
                    with torch.no_grad():
                        reconstructed = model(torch.FloatTensor(X).to(device)).cpu().numpy()
                    recon_error = float(np.mean((X - reconstructed) ** 2))
                    return {
                        "status": "success", "result": model, "message": "Autoencoder trained.",
                        "metrics": {"reconstruction_error": recon_error, "encoding_dim": int(encoding_dim)},
                        "history": history, "encoded_data": encoded.tolist()
                    }

                elif algo in ('mlpclassifier', 'mlpregressor'):
                    y = np.asarray(y).ravel()
                    if task_type == 'auto':
                        task_type = self._auto_detect_task(y)
                    if task_type == 'classification':
                        classes = np.unique(y)
                        n_classes = len(classes)
                        y_mapped = np.array([np.where(classes == v)[0][0] for v in y])
                        output_dim = n_classes
                        criterion = nn.CrossEntropyLoss()
                    else:
                        y_mapped = y.astype(float).reshape(-1, 1)
                        output_dim = 1
                        criterion = nn.MSELoss()

                    model = _TorchMLP(X.shape[1], hidden_dims, output_dim, dropout).to(device)
                    optimizer = optim.Adam(model.parameters(), lr=lr)
                    X_t = torch.FloatTensor(X)
                    y_t = torch.LongTensor(y_mapped) if task_type == 'classification' else torch.FloatTensor(y_mapped)
                    dataset = TensorDataset(X_t, y_t)
                    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
                    history = []
                    for epoch in range(epochs):
                        epoch_loss = 0.0
                        for batch_X, batch_y in loader:
                            batch_X, batch_y = batch_X.to(device), batch_y.to(device)
                            optimizer.zero_grad()
                            outputs = model(batch_X)
                            if task_type == 'regression':
                                loss = criterion(outputs, batch_y)
                            else:
                                loss = criterion(outputs, batch_y.squeeze() if batch_y.ndim > 1 else batch_y)
                            loss.backward()
                            optimizer.step()
                            epoch_loss += loss.item()
                        avg_loss = epoch_loss / len(loader)
                        history.append(avg_loss)
                        if (epoch + 1) % 20 == 0:
                            self._log(f"Epoch {epoch+1}/{epochs}, loss={avg_loss:.6f}")

                    with torch.no_grad():
                        all_preds = model(X_t.to(device)).cpu().numpy()
                    if task_type == 'classification':
                        y_pred = classes[np.argmax(all_preds, axis=1)]
                        metrics_dict = self._compute_classification_metrics(y, y_pred)
                    else:
                        y_pred = all_preds.ravel()
                        metrics_dict = self._compute_regression_metrics(y, y_pred)

                    return {
                        "status": "success", "result": model, "message": f"PyTorch {algorithm} trained.",
                        "metrics": metrics_dict, "history": history
                    }

                return {"status": "error", "result": None, "message": f"Unknown deep learning algorithm '{algorithm}'."}

            return {"status": "error", "result": None, "message": "No deep learning backend available. Install scikit-learn or PyTorch."}

        except Exception as e:
            return {"status": "error", "result": None, "message": f"Deep learning error: {str(e)}"}

    # ------------------------------------------------------------------
    # TIME SERIES
    # ------------------------------------------------------------------

    def time_series(self, algorithm, data, **params):
        """
        Perform time series analysis / forecasting.

        Parameters
        ----------
        algorithm : str
            One of: arima, sarima, exponential_smoothing, simple_moving_average,
            holtwinters, seasonal_decompose, prophet_decomposition.
        data : array-like of shape (n_timesteps,)
            Time series data.
        **params : dict
            Additional parameters.

        Returns
        -------
        dict with keys: status, result, message, forecast (optional), metrics (optional).
        """
        try:
            data = np.asarray(data).ravel()
            algo = algorithm.lower().replace(" ", "").replace("-", "").replace("_", "")

            n = len(data)
            forecast_steps = params.get('forecast_steps', 10)

            # --- Simple Moving Average ---
            if algo == 'simplemovingaverage':
                window = params.get('window', 3)
                if len(data) < window:
                    return {"status": "error", "result": None, "message": f"Data length ({n}) < window ({window})."}
                smoothed = np.convolve(data, np.ones(window) / window, mode='valid')
                last_vals = data[-window:]
                forecast = np.full(forecast_steps, last_vals.mean())
                padded = np.concatenate([data, forecast])
                full_smoothed = np.convolve(padded, np.ones(window) / window, mode='valid')
                full_forecast = full_smoothed[-(forecast_steps + window):][:forecast_steps] if len(full_smoothed) >= forecast_steps else full_smoothed[-forecast_steps:]
                return {
                    "status": "success", "result": {"smoothed": smoothed.tolist(), "forecast": full_forecast.tolist()},
                    "smoothed": smoothed.tolist(), "forecast": full_forecast.tolist(),
                    "message": f"SimpleMovingAverage (window={window}) completed."
                }

            # --- Exponential Smoothing ---
            elif algo == 'exponentialsmoothing':
                alpha = params.get('alpha', 0.3)
                result = [data[0]]
                for t in range(1, n):
                    result.append(alpha * data[t] + (1 - alpha) * result[-1])
                last = result[-1]
                forecast = [alpha * last + (1 - alpha) * last] * forecast_steps
                for i in range(1, forecast_steps):
                    forecast[i] = alpha * forecast[i-1] + (1 - alpha) * forecast[i-1]
                return {
                    "status": "success",
                    "result": {"smoothed": result, "forecast": forecast},
                    "smoothed": result, "forecast": forecast,
                    "message": f"ExponentialSmoothing (alpha={alpha}) completed."
                }

            # --- Holt-Winters ---
            elif algo == 'holtwinters':
                alpha = params.get('alpha', 0.3)
                beta = params.get('beta', 0.1)
                gamma = params.get('gamma', 0.1)
                period = params.get('period', max(2, min(12, n // 3)))

                if _HAS_STATS and params.get('use_statsmodels', True):
                    try:
                        model = StatsHoltWinters(
                            data, seasonal_periods=period, trend='add', seasonal='add'
                        ).fit()
                        forecast = model.forecast(forecast_steps).tolist()
                        fitted = model.fittedvalues.tolist() if hasattr(model, 'fittedvalues') else data.tolist()
                        return {
                            "status": "success",
                            "result": model,
                            "fitted": fitted,
                            "forecast": forecast,
                            "message": f"HoltWinters (statsmodels, period={period}) completed.",
                            "metrics": {"aic": float(getattr(model, 'aic', 0)), "sse": float(getattr(model, 'sse', 0))}
                        }
                    except Exception:
                        pass

                # Pure Python Holt-Winters
                if period < 2:
                    period = max(2, n // 4)
                level = data[0]
                trend = data[1] - data[0] if n > 1 else 0
                seasonal = np.array([data[i] - level for i in range(min(period, n))])
                if len(seasonal) < period:
                    seasonal = np.pad(seasonal, (0, period - len(seasonal)), mode='edge')

                fitted = np.zeros(n)
                for i in range(n):
                    if i < len(seasonal):
                        season_idx = i % period
                    else:
                        season_idx = i % period
                    old_level = level
                    level = alpha * (data[i] - seasonal[season_idx]) + (1 - alpha) * (level + trend)
                    trend = beta * (level - old_level) + (1 - beta) * trend
                    seasonal[season_idx] = gamma * (data[i] - level) + (1 - gamma) * seasonal[season_idx]
                    fitted[i] = level + trend + seasonal[season_idx]

                last_level = level
                last_trend = trend
                forecast = []
                for i in range(forecast_steps):
                    season_idx = (n + i) % period
                    val = last_level + (i + 1) * last_trend + seasonal[season_idx]
                    forecast.append(float(val))

                return {
                    "status": "success",
                    "result": {"fitted": fitted.tolist(), "forecast": forecast},
                    "fitted": fitted.tolist(), "forecast": forecast,
                    "message": f"HoltWinters (scratch, period={period}) completed."
                }

            # --- Seasonal Decompose ---
            elif algo == 'seasonaldecompose':
                period = params.get('period', max(2, min(12, n // 3)))
                model_type = params.get('model', 'additive')

                if _HAS_STATS:
                    try:
                        result = seasonal_decompose(data, model=model_type, period=period)
                        return {
                            "status": "success",
                            "result": result,
                            "trend": result.trend.tolist() if hasattr(result, 'trend') and result.trend is not None else [None] * n,
                            "seasonal": result.seasonal.tolist() if hasattr(result, 'seasonal') and result.seasonal is not None else [None] * n,
                            "residual": result.resid.tolist() if hasattr(result, 'resid') and result.resid is not None else [None] * n,
                            "message": "SeasonalDecompose completed."
                        }
                    except Exception:
                        pass

                # Pure Python seasonal decompose
                trend = np.full(n, np.nan)
                half = period // 2
                for i in range(half, n - half):
                    trend[i] = np.mean(data[i - half:i + half + 1])
                detrended = data - trend
                seasonal = np.full(n, np.nan)
                for i in range(period):
                    idxs = list(range(i, n, period))
                    vals = [detrended[j] for j in idxs if not np.isnan(detrended[j])]
                    if vals:
                        seasonal_val = np.mean(vals)
                        for j in idxs:
                            seasonal[j] = seasonal_val
                seasonal = np.array(seasonal)
                if model_type == 'additive':
                    seasonal -= np.nanmean(seasonal)
                residual = data - trend - seasonal

                return {
                    "status": "success",
                    "result": {"trend": trend.tolist(), "seasonal": seasonal.tolist(), "residual": residual.tolist()},
                    "trend": [None if np.isnan(x) else float(x) for x in trend],
                    "seasonal": [None if np.isnan(x) else float(x) for x in seasonal],
                    "residual": [None if np.isnan(x) else float(x) for x in residual],
                    "message": f"SeasonalDecompose (scratch, period={period}) completed."
                }

            # --- ARIMA ---
            elif algo in ('arima', 'sarima'):
                if _HAS_STATS:
                    try:
                        order = params.get('order', (1, 0, 0))
                        seasonal_order = params.get('seasonal_order', None)
                        if algo == 'sarima' and seasonal_order is None:
                            seasonal_order = (1, 0, 0, params.get('period', 12))
                        if algo == 'arima':
                            model = StatsARIMA(data, order=order).fit()
                        else:
                            from statsmodels.tsa.arima.model import ARIMA as StatsARIMA
                            model = StatsARIMA(data, order=order, seasonal_order=seasonal_order).fit()
                        forecast = model.forecast(forecast_steps).tolist()
                        return {
                            "status": "success", "result": model,
                            "forecast": forecast,
                            "message": f"{algorithm.upper()} (statsmodels) completed.",
                            "metrics": {
                                "aic": float(model.aic), "bic": float(model.bic),
                                "mse": float(model.mse) if hasattr(model, 'mse') else 0
                            }
                        }
                    except Exception as e_stats:
                        pass

                # Pure Python ARIMA (simple AR with differencing)
                d = params.get('d', params.get('order', (1, 0, 0))[1]) if algo == 'arima' else 1
                p = params.get('p', params.get('order', (1, 0, 0))[0]) if algo == 'arima' else 1
                q = params.get('q', params.get('order', (1, 0, 0))[2]) if algo == 'arima' else 0

                # Differencing
                diff_data = data.copy()
                for _ in range(d):
                    diff_data = diff_data[1:] - diff_data[:-1]
                if len(diff_data) == 0:
                    return {"status": "error", "result": None, "message": "Data too short for differencing."}

                # Fit AR(p) using least squares
                p_actual = min(p, len(diff_data) - 1)
                if p_actual < 1:
                    ar_coefs = np.array([0.0])
                    residuals = diff_data
                else:
                    X_ar = np.column_stack([diff_data[i:len(diff_data) - p_actual + i] for i in range(p_actual)])
                    y_ar = diff_data[p_actual:]
                    if len(X_ar) > p_actual:
                        ar_coefs = np.linalg.lstsq(X_ar, y_ar, rcond=None)[0]
                        residuals = y_ar - X_ar @ ar_coefs
                    else:
                        ar_coefs = np.zeros(p_actual)
                        residuals = diff_data

                # Fit MA(q) on residuals
                q_actual = min(q, len(residuals) - 1)
                if q_actual >= 1 and len(residuals) > q_actual:
                    X_ma = np.column_stack([residuals[i:len(residuals) - q_actual + i] for i in range(q_actual)])
                    y_ma = residuals[q_actual:]
                    if len(X_ma) > q_actual:
                        ma_coefs = np.linalg.lstsq(X_ma, y_ma, rcond=None)[0]
                    else:
                        ma_coefs = np.zeros(q_actual)
                else:
                    ma_coefs = np.zeros(1) if q_actual == 0 else []

                # Forecast
                last_values = list(diff_data[-p_actual:]) if p_actual > 0 else [0]
                last_residuals = list(residuals[-q_actual:]) if q_actual > 0 else [0]
                forecast_diff = []
                for i in range(forecast_steps):
                    ar_part = sum(ar_coefs[j] * (last_values[-(j + 1)] if j < len(last_values) else 0) for j in range(len(ar_coefs))) if len(ar_coefs) > 0 else 0
                    ma_part = sum(ma_coefs[j] * (last_residuals[-(j + 1)] if j < len(last_residuals) else 0) for j in range(len(ma_coefs))) if len(ma_coefs) > 0 else 0
                    fc = float(ar_part + ma_part)
                    forecast_diff.append(fc)
                    last_values.append(fc)
                    last_residuals.append(0)

                # Undo differencing
                forecast = forecast_diff
                for _ in range(d):
                    last_original = data[-1]
                    cumsum = np.cumsum(forecast) + last_original
                    forecast = cumsum.tolist()

                return {
                    "status": "success",
                    "result": {
                        "ar_coefs": ar_coefs.tolist() if isinstance(ar_coefs, np.ndarray) else ar_coefs,
                        "ma_coefs": ma_coefs.tolist() if isinstance(ma_coefs, np.ndarray) else ma_coefs
                    },
                    "forecast": forecast,
                    "message": f"{algorithm.upper()} (scratch) completed."
                }

            # --- Prophet-style decomposition ---
            elif algo == 'prophetdecomposition':
                period = params.get('period', max(2, min(12, n // 3)))

                if _HAS_PROPHET:
                    try:
                        df = pd.DataFrame({'ds': pd.date_range(end=pd.Timestamp.now(), periods=n, freq='D'), 'y': data})
                        model = Prophet(**params)
                        model.fit(df)
                        future = model.make_future_dataframe(periods=forecast_steps)
                        forecast = model.predict(future)
                        return {
                            "status": "success", "result": model,
                            "forecast": forecast[['ds', 'yhat']].tail(forecast_steps).to_dict('records'),
                            "message": "Prophet decomposition completed."
                        }
                    except Exception:
                        pass

                # Simple trend + seasonality decomposition
                x = np.arange(n)
                A = np.column_stack([x, np.ones(n)])
                trend_coefs = np.linalg.lstsq(A, data, rcond=None)[0]
                trend = A @ trend_coefs
                detrended = data - trend

                seasonal = np.full(n, np.nan)
                for i in range(period):
                    idxs = list(range(i, n, period))
                    vals = detrended[idxs]
                    seasonal_vals = np.full(len(idxs), np.mean(vals))
                    for j, idx in enumerate(idxs):
                        seasonal[idx] = seasonal_vals[j]
                seasonal = np.array(seasonal)
                seasonal -= np.nanmean(seasonal)
                residuals = data - trend - seasonal

                x_future = np.arange(n, n + forecast_steps)
                future_trend = trend_coefs[0] * x_future + trend_coefs[1]
                future_seasonal = np.array([seasonal[i % period] if not np.isnan(seasonal[i % period]) else 0 for i in range(n, n + forecast_steps)])
                future_forecast = future_trend + future_seasonal

                return {
                    "status": "success",
                    "result": {
                        "trend": trend.tolist(), "seasonal": seasonal.tolist(), "residual": residuals.tolist(),
                        "trend_coefficients": trend_coefs.tolist()
                    },
                    "trend": [None if np.isnan(x) else float(x) for x in trend],
                    "seasonal": [None if np.isnan(x) else float(x) for x in seasonal],
                    "residual": [None if np.isnan(x) else float(x) for x in residuals],
                    "forecast": [float(x) for x in future_forecast],
                    "message": f"Prophet-style decomposition completed."
                }

            else:
                return {"status": "error", "result": None, "message": f"Unknown time series algorithm '{algorithm}'."}

        except Exception as e:
            return {"status": "error", "result": None, "message": f"Time series error: {str(e)}"}

    # ------------------------------------------------------------------
    # ANOMALY DETECTION
    # ------------------------------------------------------------------

    def detect_anomalies(self, algorithm, X, **params):
        """
        Detect anomalies in data.

        Parameters
        ----------
        algorithm : str
            One of: isolationforest, lof, oneclasssvm, ellipticenvelope, dbscan_outlier.
        X : array-like of shape (n_samples, n_features)
            Data to analyze.
        **params : dict
            Additional parameters passed to the algorithm.

        Returns
        -------
        dict with keys: status, result, anomalies (bool array), message, metrics.
        """
        try:
            X = self._ensure_2d(X)
            algo = algorithm.lower().replace(" ", "").replace("-", "").replace("_", "")

            err = self._check_sklearn()
            if err and algo not in ('dbscan_outlier',):
                return err

            if algo == 'isolationforest':
                from sklearn.ensemble import IsolationForest
                model = self._safe_init(IsolationForest, params)
                model.fit(X)
                preds = model.predict(X)
                anomalies = preds == -1
                scores = model.decision_function(X)
                return {
                    "status": "success", "result": model,
                    "anomalies": anomalies.tolist(),
                    "scores": scores.tolist(),
                    "n_anomalies": int(anomalies.sum()),
                    "message": f"IsolationForest detected {int(anomalies.sum())}/{len(X)} anomalies."
                }

            elif algo == 'lof':
                from sklearn.neighbors import LocalOutlierFactor
                model = self._safe_init(LocalOutlierFactor, params)
                preds = model.fit_predict(X)
                anomalies = preds == -1
                scores = -model.negative_outlier_factor_ if hasattr(model, 'negative_outlier_factor_') else None
                return {
                    "status": "success", "result": model,
                    "anomalies": anomalies.tolist(),
                    "scores": (-model.negative_outlier_factor_).tolist() if scores is not None else None,
                    "n_anomalies": int(anomalies.sum()),
                    "message": f"LOF detected {int(anomalies.sum())}/{len(X)} anomalies."
                }

            elif algo == 'oneclasssvm':
                from sklearn.svm import OneClassSVM
                model = self._safe_init(OneClassSVM, params)
                model.fit(X)
                preds = model.predict(X)
                anomalies = preds == -1
                scores = model.decision_function(X) if hasattr(model, 'decision_function') else None
                return {
                    "status": "success", "result": model,
                    "anomalies": anomalies.tolist(),
                    "scores": scores.tolist() if scores is not None else None,
                    "n_anomalies": int(anomalies.sum()),
                    "message": f"OneClassSVM detected {int(anomalies.sum())}/{len(X)} anomalies."
                }

            elif algo == 'ellipticenvelope':
                from sklearn.covariance import EllipticEnvelope
                model = self._safe_init(EllipticEnvelope, params)
                model.fit(X)
                preds = model.predict(X)
                anomalies = preds == -1
                scores = model.decision_function(X) if hasattr(model, 'decision_function') else None
                return {
                    "status": "success", "result": model,
                    "anomalies": anomalies.tolist(),
                    "scores": scores.tolist() if scores is not None else None,
                    "n_anomalies": int(anomalies.sum()),
                    "message": f"EllipticEnvelope detected {int(anomalies.sum())}/{len(X)} anomalies."
                }

            elif algo == 'dbscanoutlier':
                eps = params.get('eps', 0.5)
                min_samples = params.get('min_samples', 5)
                if _HAS_SKLEARN:
                    from sklearn.cluster import DBSCAN
                    model = DBSCAN(eps=eps, min_samples=min_samples)
                    model.fit(X)
                    preds = model.labels_
                else:
                    from sklearn.cluster import DBSCAN
                    model = DBSCAN(eps=eps, min_samples=min_samples)
                    model.fit(X)
                    preds = model.labels_
                anomalies = preds == -1
                return {
                    "status": "success", "result": model,
                    "anomalies": anomalies.tolist(),
                    "n_anomalies": int(anomalies.sum()),
                    "message": f"DBSCAN outlier detection found {int(anomalies.sum())}/{len(X)} anomalies.",
                    "cluster_labels": [int(x) for x in preds]
                }

            else:
                return {"status": "error", "result": None, "message": f"Unknown anomaly detection algorithm '{algorithm}'."}

        except Exception as e:
            return {"status": "error", "result": None, "message": f"Anomaly detection error: {str(e)}"}

    # ------------------------------------------------------------------
    # ENSEMBLE
    # ------------------------------------------------------------------

    def ensemble(self, algorithm, estimators, X, y, task_type='auto', **params):
        """
        Build an ensemble model.

        Parameters
        ----------
        algorithm : str
            One of: votingclassifier, votingregressor, stackingclassifier,
            stackingregressor, baggingclassifier, baggingregressor.
        estimators : list of (name, estimator) tuples
            Base estimators for the ensemble.
        X : array-like
            Training data.
        y : array-like
            Target values.
        task_type : str, default='auto'
            'classification', 'regression', or 'auto'.
        **params : dict
            Additional parameters.

        Returns
        -------
        dict with keys: status, result, message, metrics (optional).
        """
        try:
            X = self._ensure_2d(X)
            y = np.asarray(y).ravel()
            algo = algorithm.lower().replace(" ", "").replace("-", "").replace("_", "")

            if task_type == 'auto':
                task_type = self._auto_detect_task(y)

            err = self._check_sklearn()
            if err:
                return err

            registry = self._get_sklearn_registry()['ensemble']
            if algo not in registry:
                return {"status": "error", "result": None, "message": f"Unknown ensemble algorithm '{algorithm}'. Available: {list(registry.keys())}"}

            ModelClass = registry[algo]
            model = self._safe_init(ModelClass, {**params, 'estimators': estimators})
            model.fit(X, y)
            y_pred = model.predict(X)

            if task_type == 'classification':
                metrics_dict = self._compute_classification_metrics(y, y_pred)
            else:
                metrics_dict = self._compute_regression_metrics(y, y_pred)

            return {
                "status": "success", "result": model, "message": f"{algorithm} ensemble trained.",
                "metrics": metrics_dict
            }

        except Exception as e:
            return {"status": "error", "result": None, "message": f"Ensemble error: {str(e)}"}

    # ------------------------------------------------------------------
    # FEATURE ENGINEERING
    # ------------------------------------------------------------------

    def feature_engineer(self, technique, X, y=None, **params):
        """
        Apply feature engineering / preprocessing techniques.

        Parameters
        ----------
        technique : str
            One of: polynomialfeatures, standardscaler, minmaxscaler, robustscaler,
            normalizer, labelencoder, onehotencoder, ordinalencoder, variancethreshold,
            selectkbest, rfe, pca_features.
        X : array-like
            Data to transform.
        y : array-like, optional
            Target values (needed for supervised feature selection).
        **params : dict
            Additional parameters.

        Returns
        -------
        dict with status, result (fitted transformer), transformed_data, message.
        """
        try:
            X = self._ensure_2d(X)
            tech = technique.lower().replace(" ", "").replace("-", "").replace("_", "")

            err = self._check_sklearn()
            if err:
                return err

            from sklearn import preprocessing
            from sklearn import feature_selection as fs

            if tech == 'polynomialfeatures':
                degree = params.get('degree', 2)
                trans = preprocessing.PolynomialFeatures(degree=degree, include_bias=params.get('include_bias', False))
                transformed = trans.fit_transform(X)
                return {"status": "success", "result": trans, "transformed_data": transformed.tolist(),
                        "message": f"PolynomialFeatures (degree={degree}) applied. New shape: {transformed.shape}"}

            elif tech == 'standardscaler':
                trans = preprocessing.StandardScaler(**params)
                transformed = trans.fit_transform(X)
                return {"status": "success", "result": trans, "transformed_data": transformed.tolist(),
                        "message": "StandardScaler applied.", "metrics": {"mean": trans.mean_.tolist(), "scale": trans.scale_.tolist()}}

            elif tech == 'minmaxscaler':
                trans = preprocessing.MinMaxScaler(**params)
                transformed = trans.fit_transform(X)
                return {"status": "success", "result": trans, "transformed_data": transformed.tolist(),
                        "message": "MinMaxScaler applied."}

            elif tech == 'robustscaler':
                trans = preprocessing.RobustScaler(**params)
                transformed = trans.fit_transform(X)
                return {"status": "success", "result": trans, "transformed_data": transformed.tolist(),
                        "message": "RobustScaler applied."}

            elif tech == 'normalizer':
                trans = preprocessing.Normalizer(**params)
                transformed = trans.fit_transform(X)
                return {"status": "success", "result": trans, "transformed_data": transformed.tolist(),
                        "message": "Normalizer applied."}

            elif tech == 'labelencoder':
                if y is None:
                    return {"status": "error", "result": None, "message": "LabelEncoder requires y."}
                trans = preprocessing.LabelEncoder()
                transformed = trans.fit_transform(y)
                return {"status": "success", "result": trans, "transformed_data": transformed.tolist(),
                        "message": "LabelEncoder applied.", "classes": trans.classes_.tolist()}

            elif tech == 'onehotencoder':
                trans = preprocessing.OneHotEncoder(**params)
                transformed = trans.fit_transform(X)
                if _HAS_SCIPY and scipy.sparse.issparse(transformed):
                    transformed = transformed.toarray()
                return {"status": "success", "result": trans, "transformed_data": transformed.tolist() if not scipy.sparse.issparse(transformed) else transformed.toarray().tolist(),
                        "message": "OneHotEncoder applied."}

            elif tech == 'ordinalencoder':
                trans = preprocessing.OrdinalEncoder(**params)
                transformed = trans.fit_transform(X)
                return {"status": "success", "result": trans, "transformed_data": transformed.tolist(),
                        "message": "OrdinalEncoder applied."}

            elif tech == 'variancethreshold':
                threshold = params.get('threshold', 0.0)
                trans = fs.VarianceThreshold(threshold=threshold)
                transformed = trans.fit_transform(X)
                return {"status": "success", "result": trans, "transformed_data": transformed.tolist(),
                        "message": f"VarianceThreshold (threshold={threshold}) applied. {transformed.shape[1]} features kept."}

            elif tech == 'selectkbest':
                if y is None:
                    return {"status": "error", "result": None, "message": "SelectKBest requires y."}
                score_func = params.pop('score_func', 'f_classif')
                k = params.get('k', 5)
                if isinstance(score_func, str):
                    if score_func == 'f_classif':
                        from sklearn.feature_selection import f_classif
                        score_func = f_classif
                    elif score_func == 'f_regression':
                        from sklearn.feature_selection import f_regression
                        score_func = f_regression
                    elif score_func == 'chi2':
                        from sklearn.feature_selection import chi2
                        score_func = chi2
                    elif score_func == 'mutual_info_classif':
                        from sklearn.feature_selection import mutual_info_classif
                        score_func = mutual_info_classif
                    elif score_func == 'mutual_info_regression':
                        from sklearn.feature_selection import mutual_info_regression
                        score_func = mutual_info_regression
                    else:
                        score_func = None
                if score_func is None:
                    return {"status": "error", "result": None, "message": "Invalid score_func for SelectKBest."}
                trans = fs.SelectKBest(score_func=score_func, k=k)
                transformed = trans.fit_transform(X, y)
                return {"status": "success", "result": trans, "transformed_data": transformed.tolist(),
                        "message": f"SelectKBest (k={k}) applied.",
                        "metrics": {"scores": trans.scores_.tolist(), "pvalues": trans.pvalues_.tolist() if trans.pvalues_ is not None else None}}

            elif tech == 'rfe':
                if y is None:
                    return {"status": "error", "result": None, "message": "RFE requires y."}
                n_features_to_select = params.get('n_features_to_select', max(1, X.shape[1] // 2))
                step = params.get('step', 1)
                estimator = params.get('estimator', None)
                if estimator is None:
                    from sklearn.linear_model import LinearRegression
                    estimator = LinearRegression()
                trans = fs.RFE(estimator=estimator, n_features_to_select=n_features_to_select, step=step)
                transformed = trans.fit_transform(X, y)
                return {"status": "success", "result": trans, "transformed_data": transformed.tolist(),
                        "message": f"RFE applied. {trans.n_features_} features selected.",
                        "metrics": {"ranking": trans.ranking_.tolist(), "support": trans.support_.tolist()}}

            elif tech == 'pca_features':
                n_components = params.get('n_components', min(X.shape[0], X.shape[1]))
                from sklearn.decomposition import PCA
                trans = PCA(n_components=n_components, random_state=params.get('random_state', self.random_state))
                transformed = trans.fit_transform(X)
                return {"status": "success", "result": trans, "transformed_data": transformed.tolist(),
                        "message": f"PCA-based feature extraction applied. {n_components} components.",
                        "metrics": {"explained_variance_ratio": trans.explained_variance_ratio_.tolist()}}

            else:
                return {"status": "error", "result": None, "message": f"Unknown feature engineering technique '{technique}'."}

        except Exception as e:
            return {"status": "error", "result": None, "message": f"Feature engineering error: {str(e)}"}

    # ------------------------------------------------------------------
    # HYPERPARAMETER TUNING
    # ------------------------------------------------------------------

    def tune_hyperparams(self, estimator, param_grid, X, y, method='gridsearchcv', cv=5, **params):
        """
        Perform hyperparameter tuning.

        Parameters
        ----------
        estimator : estimator object
            The base model to tune.
        param_grid : dict or list of dict
            Parameter grid to search.
        X : array-like
            Training data.
        y : array-like
            Target values.
        method : str, default='gridsearchcv'
            One of: gridsearchcv, randomizedsearchcv, bayessearchcv, halvinggridsearchcv.
        cv : int or CV splitter, default=5
            Cross-validation strategy.
        **params : dict
            Additional parameters.

        Returns
        -------
        dict with status, result (tuned model), best_params, best_score, cv_results, message.
        """
        try:
            X = self._ensure_2d(X)
            y = np.asarray(y).ravel()
            method = method.lower().replace(" ", "").replace("-", "").replace("_", "")

            err = self._check_sklearn()
            if err:
                return err

            if method == 'bayessearchcv':
                if _HAS_SKOPT:
                    from skopt import BayesSearchCV
                    search = BayesSearchCV(estimator=estimator, search_spaces=param_grid, cv=cv, **params)
                else:
                    return {"status": "error", "result": None, "message": "BayesSearchCV requires scikit-optimize. Install: pip install scikit-optimize"}
            elif method == 'gridsearchcv':
                from sklearn.model_selection import GridSearchCV
                search = GridSearchCV(estimator=estimator, param_grid=param_grid, cv=cv,
                                      **{k: v for k, v in params.items() if k != 'random_state'})
            elif method == 'randomizedsearchcv':
                from sklearn.model_selection import RandomizedSearchCV
                n_iter = params.pop('n_iter', 10) if 'n_iter' in params else 10
                search = RandomizedSearchCV(estimator=estimator, param_distributions=param_grid, n_iter=n_iter, cv=cv,
                                            **{k: v for k, v in params.items() if k != 'random_state'})
            elif method == 'halvinggridsearchcv':
                from sklearn.model_selection import HalvingGridSearchCV
                search = HalvingGridSearchCV(estimator=estimator, param_grid=param_grid, cv=cv,
                                              **{k: v for k, v in params.items() if k != 'random_state'})
            else:
                return {"status": "error", "result": None, "message": f"Unknown tuning method '{method}'."}

            search.fit(X, y)

            cv_results = search.cv_results_
            # Convert cv_results to serializable format
            cv_results_safe = {}
            for k, v in cv_results.items():
                if isinstance(v, np.ndarray):
                    cv_results_safe[k] = v.tolist() if v.ndim <= 1 else v.tolist()
                elif isinstance(v, list):
                    cv_results_safe[k] = [str(x) if isinstance(x, (np.ndarray, list)) else x for x in v]
                else:
                    try:
                        json.dumps({k: v})
                        cv_results_safe[k] = v
                    except Exception:
                        cv_results_safe[k] = str(v)

            return {
                "status": "success",
                "result": search,
                "best_params": search.best_params_,
                "best_score": float(search.best_score_),
                "cv_results": cv_results_safe,
                "message": f"{method} completed. Best score: {search.best_score_:.4f}"
            }

        except Exception as e:
            return {"status": "error", "result": None, "message": f"Hyperparameter tuning error: {str(e)}"}

    # ------------------------------------------------------------------
    # CROSS VALIDATION
    # ------------------------------------------------------------------

    def cross_validate(self, estimator, X, y, cv_method='kfold', **params):
        """
        Perform cross-validation.

        Parameters
        ----------
        estimator : estimator object
            The model to evaluate.
        X : array-like
            Training data.
        y : array-like
            Target values.
        cv_method : str, default='kfold'
            One of: kfold, stratifiedkfold, groupkfold, timeseriessplit,
            leaveoneout, repeatedkfold.
        **params : dict
            Additional parameters including n_splits, cv (direct splitter), etc.

        Returns
        -------
        dict with status, result (scores), message.
        """
        try:
            X = self._ensure_2d(X)
            y = np.asarray(y).ravel()
            cv_method = cv_method.lower().replace(" ", "").replace("-", "").replace("_", "")

            err = self._check_sklearn()
            if err:
                return err

            from sklearn.model_selection import cross_val_score, cross_validate as sk_cross_validate

            # Check if a pre-built CV splitter is provided
            cv = None
            if 'cv' in params:
                cv = params.pop('cv')
            else:
                n_splits = params.get('n_splits', 5)
                registry = self._get_sklearn_registry()['cv']
                if cv_method not in registry:
                    return {"status": "error", "result": None, "message": f"Unknown CV method '{cv_method}'. Available: {list(registry.keys())}"}

                if cv_method == 'kfold':
                    cv = registry[cv_method](n_splits=n_splits, shuffle=True, random_state=params.get('random_state', self.random_state))
                elif cv_method == 'stratifiedkfold':
                    cv = registry[cv_method](n_splits=n_splits, shuffle=True, random_state=params.get('random_state', self.random_state))
                elif cv_method == 'groupkfold':
                    cv = registry[cv_method](n_splits=n_splits)
                elif cv_method == 'timeseriessplit':
                    cv = registry[cv_method](n_splits=n_splits)
                elif cv_method == 'leaveoneout':
                    cv = registry[cv_method]()
                elif cv_method == 'repeatedkfold':
                    n_repeats = params.get('n_repeats', 10)
                    cv = registry[cv_method](n_splits=n_splits, n_repeats=n_repeats, random_state=params.get('random_state', self.random_state))
                else:
                    cv = registry[cv_method](n_splits=n_splits)

            scoring = params.get('scoring', None)
            result = sk_cross_validate(estimator, X, y, cv=cv, scoring=scoring, return_estimator=False, return_train_score=True, error_score='raise')

            scores = {
                "test_scores": result['test_score'].tolist(),
                "train_scores": result['train_score'].tolist() if 'train_score' in result else None,
                "test_mean": float(result['test_score'].mean()),
                "test_std": float(result['test_score'].std()),
                "test_min": float(result['test_score'].min()),
                "test_max": float(result['test_score'].max()),
                "fit_times": result.get('fit_time', []).tolist() if hasattr(result.get('fit_time', []), 'tolist') else list(result.get('fit_time', [])),
                "score_times": result.get('score_time', []).tolist() if hasattr(result.get('score_time', []), 'tolist') else list(result.get('score_time', [])),
            }

            return {
                "status": "success",
                "result": result,
                "scores": scores,
                "cv_method": cv_method,
                "message": f"Cross-validation ({cv_method}) completed. Mean score: {scores['test_mean']:.4f} +/- {scores['test_std']:.4f}"
            }

        except Exception as e:
            return {"status": "error", "result": None, "message": f"Cross-validation error: {str(e)}"}

    # ------------------------------------------------------------------
    # MODEL EVALUATION
    # ------------------------------------------------------------------

    def evaluate(self, y_true, y_pred, task_type='auto', **params):
        """
        Evaluate model predictions.

        Parameters
        ----------
        y_true : array-like
            Ground truth labels.
        y_pred : array-like
            Predicted labels.
        task_type : str, default='auto'
            'classification', 'regression', or 'auto'.
        **params : dict
            Additional parameters. For classification: y_prob (predicted probabilities).

        Returns
        -------
        dict with status, result (metrics dict), message.
        """
        try:
            y_true = np.asarray(y_true).ravel()
            y_pred = np.asarray(y_pred).ravel()

            if task_type == 'auto':
                task_type = self._auto_detect_task(y_true)

            if task_type == 'classification':
                metrics = self._compute_classification_metrics(y_true, y_pred, y_prob=params.get('y_prob'))
                return {"status": "success", "result": metrics, "message": "Classification evaluation completed."}

            else:
                metrics = self._compute_regression_metrics(y_true, y_pred)
                # Add additional regression metrics
                residuals = y_true - y_pred
                metrics['max_error'] = float(np.max(np.abs(residuals)))
                metrics['median_absolute_error'] = float(np.median(np.abs(residuals)))
                return {"status": "success", "result": metrics, "message": "Regression evaluation completed."}

        except Exception as e:
            return {"status": "error", "result": None, "message": f"Evaluation error: {str(e)}"}

    # ------------------------------------------------------------------
    # AUTO ML
    # ------------------------------------------------------------------

    def auto_ml(self, X, y, task_type='auto', **params):
        """
        Auto-pick the best algorithm for the given data.

        Tries multiple algorithms and returns the best one based on
        cross-validation score.

        Parameters
        ----------
        X : array-like
            Training data.
        y : array-like
            Target values.
        task_type : str, default='auto'
            'classification', 'regression', or 'auto'.
        **params : dict
            Additional parameters:
            - cv_folds : int, default=3
            - metric : str, optional, scoring metric
            - fast_mode : bool, default=True, if True skips slower algorithms
            - exclude : list, algorithms to exclude
            - time_budget : float, optional, time budget in seconds

        Returns
        -------
        dict with status, result (best model), best_algorithm, leaderboard, message.
        """
        try:
            X = self._ensure_2d(X)
            y = np.asarray(y).ravel()

            if task_type == 'auto':
                task_type = self._auto_detect_task(y)

            cv_folds = params.get('cv_folds', 3)
            fast_mode = params.get('fast_mode', True)
            exclude = [a.lower() for a in params.get('exclude', [])]
            time_budget = params.get('time_budget', None)
            scoring = params.get('metric', None)

            start_time = time.time()

            err = self._check_sklearn()
            if err:
                return err

            from sklearn.model_selection import cross_val_score

            if task_type == 'classification':
                candidates = [
                    ('logisticregression', sklearn.linear_model.LogisticRegression, {'max_iter': 500, 'random_state': self.random_state}),
                    ('knn', sklearn.neighbors.KNeighborsClassifier, {'n_neighbors': 5}),
                    ('naivebayes', sklearn.naive_bayes.GaussianNB, {}),
                    ('decisiontreeclassifier', sklearn.tree.DecisionTreeClassifier, {'max_depth': 10, 'random_state': self.random_state}),
                    ('randomforestclassifier', sklearn.ensemble.RandomForestClassifier, {'n_estimators': 50 if fast_mode else 100, 'random_state': self.random_state}),
                    ('svc', sklearn.svm.SVC, {'kernel': 'linear', 'random_state': self.random_state}),
                    ('gradientboostingclassifier', sklearn.ensemble.GradientBoostingClassifier, {'n_estimators': 50 if fast_mode else 100, 'random_state': self.random_state}),
                    ('adaboostclassifier', sklearn.ensemble.AdaBoostClassifier, {'n_estimators': 50, 'random_state': self.random_state}),
                    ('sgdclassifier', sklearn.linear_model.SGDClassifier, {'max_iter': 500, 'random_state': self.random_state}),
                    ('ridgeclassifier', sklearn.linear_model.RidgeClassifier, {'random_state': self.random_state}),
                    ('lineardiscriminantanalysis', sklearn.discriminant_analysis.LinearDiscriminantAnalysis, {}),
                ]
                if _HAS_XGBOOST:
                    candidates.append(('xgboostclassifier', xgboost.XGBClassifier, {'n_estimators': 50 if fast_mode else 100, 'random_state': self.random_state, 'verbosity': 0}))
            else:
                candidates = [
                    ('linearregression', sklearn.linear_model.LinearRegression, {}),
                    ('ridge', sklearn.linear_model.Ridge, {'random_state': self.random_state}),
                    ('lasso', sklearn.linear_model.Lasso, {'random_state': self.random_state}),
                    ('elasticnet', sklearn.linear_model.ElasticNet, {'random_state': self.random_state}),
                    ('decisiontreeregressor', sklearn.tree.DecisionTreeRegressor, {'max_depth': 10, 'random_state': self.random_state}),
                    ('randomforestregressor', sklearn.ensemble.RandomForestRegressor, {'n_estimators': 50 if fast_mode else 100, 'random_state': self.random_state}),
                    ('svr', sklearn.svm.SVR, {'kernel': 'linear'}),
                    ('gradientboostingregressor', sklearn.ensemble.GradientBoostingRegressor, {'n_estimators': 50 if fast_mode else 100, 'random_state': self.random_state}),
                    ('adaboostregressor', sklearn.ensemble.AdaBoostRegressor, {'n_estimators': 50, 'random_state': self.random_state}),
                    ('bayesianridge', sklearn.linear_model.BayesianRidge, {}),
                    ('huberregressor', sklearn.linear_model.HuberRegressor, {}),
                ]
                if _HAS_XGBOOST:
                    candidates.append(('xgboostregressor', xgboost.XGBRegressor, {'n_estimators': 50 if fast_mode else 100, 'random_state': self.random_state, 'verbosity': 0}))

            if fast_mode and task_type == 'classification':
                candidates = [c for c in candidates if c[0] not in ('svc', 'gradientboostingclassifier')]
            elif fast_mode and task_type == 'regression':
                candidates = [c for c in candidates if c[0] not in ('svr', 'gradientboostingregressor')]

            candidates = [c for c in candidates if c[0] not in exclude]

            leaderboard = []
            best_score = -float('inf') if task_type == 'classification' else float('inf')
            best_model = None
            best_name = None

            for name, ModelClass, default_params in candidates:
                if time_budget and (time.time() - start_time) > time_budget:
                    self._log(f"Time budget ({time_budget}s) exceeded. Stopping.")
                    break

                try:
                    model = ModelClass(**default_params)
                    if task_type == 'classification':
                        scores = cross_val_score(model, X, y, cv=cv_folds, scoring=scoring)
                        mean_score = scores.mean()
                        # Higher is better for accuracy
                        is_better = mean_score > best_score if best_score != -float('inf') else True
                    else:
                        if scoring:
                            scores = cross_val_score(model, X, y, cv=cv_folds, scoring=scoring)
                            if scoring in ('neg_mean_squared_error', 'neg_mean_absolute_error', 'neg_root_mean_squared_error'):
                                mean_score = scores.mean()
                                is_better = mean_score > best_score if best_score != -float('inf') else True
                            else:
                                mean_score = scores.mean()
                                is_better = mean_score > best_score if best_score != -float('inf') else True
                        else:
                            scores = cross_val_score(model, X, y, cv=cv_folds, scoring='neg_mean_squared_error')
                            mean_score = scores.mean()
                            is_better = mean_score > best_score if best_score != -float('inf') else True

                    leaderboard.append({
                        "algorithm": name,
                        "score": float(mean_score),
                        "score_std": float(scores.std()),
                        "cv_scores": scores.tolist()
                    })

                    if is_better:
                        best_score = mean_score
                        best_model = model
                        best_name = name

                    self._log(f"{name}: {mean_score:.4f} +/- {scores.std():.4f}")

                except Exception as e:
                    self._log(f"{name}: FAILED - {str(e)}")
                    continue

            if best_model is None:
                return {"status": "error", "result": None, "message": "All algorithms failed during auto_ml.", "leaderboard": leaderboard}

            # Retrain best on full data
            best_model.fit(X, y)

            leaderboard.sort(key=lambda x: x['score'], reverse=(task_type == 'classification'))

            return {
                "status": "success",
                "result": best_model,
                "best_algorithm": best_name,
                "best_score": float(best_score),
                "leaderboard": leaderboard,
                "task_type": task_type,
                "message": f"AutoML complete. Best: {best_name} with score {best_score:.4f}"
            }

        except Exception as e:
            return {"status": "error", "result": None, "message": f"AutoML error: {str(e)}"}

    # ------------------------------------------------------------------
    # MODEL EXPLAINABILITY
    # ------------------------------------------------------------------

    def explain_model(self, model, X, feature_names=None):
        """
        Explain model predictions using feature importance / coefficients.

        Parameters
        ----------
        model : trained model
            The model to explain.
        X : array-like of shape (n_samples, n_features)
            Data to explain.
        feature_names : list of str, optional
            Names of features.

        Returns
        -------
        dict with status, result (feature importance dict), message.
        """
        try:
            X = self._ensure_2d(X)
            n_features = X.shape[1]

            if feature_names is None:
                feature_names = [f"Feature_{i}" for i in range(n_features)]

            importance = {}

            # Try sklearn-style feature_importances_
            if hasattr(model, 'feature_importances_'):
                importances = model.feature_importances_
                if importances is not None:
                    importance['feature_importances'] = {
                        feature_names[i]: float(importances[i]) for i in range(len(importances))
                    }
                    sorted_idx = np.argsort(importances)[::-1]
                    importance['sorted_importances'] = [
                        {"feature": feature_names[i], "importance": float(importances[i])}
                        for i in sorted_idx
                    ]

            # Try coefficients
            if hasattr(model, 'coef_'):
                coefs = model.coef_
                if coefs is not None:
                    if coefs.ndim > 1:
                        # Multiclass: take mean absolute
                        coef_imp = np.mean(np.abs(coefs), axis=0)
                    else:
                        coef_imp = np.abs(coefs)
                    importance['coefficients'] = {
                        feature_names[i]: float(coefs[i] if coefs.ndim == 1 else coefs[:, i].tolist()) for i in range(len(coef_imp))
                    }
                    importance['abs_coefficient_importance'] = {
                        feature_names[i]: float(coef_imp[i]) for i in range(len(coef_imp))
                    }

            # Try permutation importance (using sklearn)
            if _HAS_SKLEARN and hasattr(model, 'predict'):
                try:
                    from sklearn.inspection import permutation_importance
                    perm_result = permutation_importance(model, X, np.zeros(X.shape[0]) if hasattr(model, 'predict') else np.zeros(X.shape[0]), n_repeats=5, random_state=self.random_state)
                    importance['permutation_importance'] = {
                        feature_names[i]: {
                            "mean": float(perm_result.importances_mean[i]),
                            "std": float(perm_result.importances_std[i])
                        } for i in range(n_features)
                    }
                except Exception:
                    pass

            # Tree structure info
            if hasattr(model, 'tree_'):
                tree = model.tree_
                importance['tree_info'] = {
                    "node_count": int(tree.node_count),
                    "max_depth": int(tree.max_depth),
                    "n_features": int(tree.n_features),
                }

            if not importance:
                return {"status": "success", "result": {"note": "Model doesn't expose feature importance or coefficients."},
                        "message": "No explainability information available for this model."}

            return {"status": "success", "result": importance, "message": "Model explanation generated."}

        except Exception as e:
            return {"status": "error", "result": None, "message": f"Model explanation error: {str(e)}"}

    # ------------------------------------------------------------------
    # GENERATE REPORT
    # ------------------------------------------------------------------

    def generate_report(self, results, format="markdown"):
        """
        Generate a formatted report of ML results.

        Parameters
        ----------
        results : dict or list of dict
            Results from MLEngine methods.
        format : str, default='markdown'
            Output format: 'markdown' or 'text'.

        Returns
        -------
        str : Formatted report.
        """
        if format not in ("markdown", "text"):
            format = "markdown"

        if not isinstance(results, list):
            results = [results]

        lines = []
        if format == "markdown":
            lines.append("# TOM MLEngine Report")
            lines.append("")
            lines.append(f"*Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}*")
            lines.append("")

            for i, result in enumerate(results):
                lines.append(f"## Result {i+1}")
                lines.append("")
                lines.append(f"- **Status**: {result.get('status', 'N/A')}")
                lines.append(f"- **Message**: {result.get('message', 'N/A')}")
                lines.append("")

                if result.get('status') == 'error':
                    continue

                # Metrics
                if 'metrics' in result and result['metrics']:
                    metrics = result['metrics']
                    lines.append("### Metrics")
                    lines.append("")
                    lines.append("| Metric | Value |")
                    lines.append("|--------|-------|")
                    for key, val in metrics.items():
                        if isinstance(val, (int, float, np.integer, np.floating)):
                            lines.append(f"| {key} | {val:.6f} |")
                        elif isinstance(val, str):
                            lines.append(f"| {key} | {val} |")
                        elif isinstance(val, list):
                            if len(val) <= 10:
                                lines.append(f"| {key} | {str(val)[:80]} |")
                            else:
                                lines.append(f"| {key} | [{len(val)} values] |")
                        elif isinstance(val, dict):
                            lines.append(f"| {key} | {str(val)[:80]} |")
                        else:
                            lines.append(f"| {key} | {val} |")
                    lines.append("")

                # Confusion Matrix
                if 'metrics' in result and isinstance(result['metrics'], dict) and 'confusion_matrix' in result['metrics']:
                    cm = result['metrics']['confusion_matrix']
                    lines.append("#### Confusion Matrix")
                    lines.append("")
                    lines.append("```")
                    for row in cm:
                        lines.append("  " + "  ".join(f"{v:4d}" for v in row))
                    lines.append("```")
                    lines.append("")

                # Labels / Clusters
                if 'labels' in result:
                    labels = result['labels']
                    unique, counts = np.unique(labels, return_counts=True)
                    lines.append("### Label Distribution")
                    lines.append("")
                    lines.append("| Label | Count |")
                    lines.append("|-------|-------|")
                    for lbl, cnt in zip(unique, counts):
                        lbl_str = str(lbl) if lbl != -1 else "noise"
                        lines.append(f"| {lbl_str} | {cnt} |")
                    lines.append("")

                # Anomalies
                if 'n_anomalies' in result:
                    lines.append(f"- **Anomalies Detected**: {result['n_anomalies']}")
                    lines.append("")

                # Forecast
                if 'forecast' in result:
                    forecast = result['forecast']
                    lines.append("### Forecast")
                    lines.append("")
                    lines.append("```")
                    for j, val in enumerate(forecast[:20]):
                        lines.append(f"  Step {j+1}: {val:.4f}")
                    if len(forecast) > 20:
                        lines.append(f"  ... ({len(forecast)} total steps)")
                    lines.append("```")
                    lines.append("")

                # Best params (tuning)
                if 'best_params' in result:
                    lines.append("### Best Parameters")
                    lines.append("")
                    lines.append("```json")
                    lines.append(str(result['best_params']))
                    lines.append("```")
                    lines.append("")

                if 'best_algorithm' in result:
                    lines.append(f"- **Best Algorithm**: {result['best_algorithm']}")
                    lines.append(f"- **Best Score**: {result.get('best_score', 'N/A')}")
                    lines.append("")

                # Leaderboard
                if 'leaderboard' in result:
                    lines.append("### Leaderboard")
                    lines.append("")
                    lines.append("| Algorithm | Score | Std Dev |")
                    lines.append("|-----------|-------|---------|")
                    for entry in result['leaderboard']:
                        lines.append(f"| {entry['algorithm']} | {entry['score']:.4f} | {entry.get('score_std', 0):.4f} |")
                    lines.append("")

                # Cross-validation scores
                if 'scores' in result:
                    scores = result['scores']
                    if isinstance(scores, dict) and 'test_scores' in scores:
                        lines.append("### Cross-Validation Scores")
                        lines.append("")
                        test_scores = scores['test_scores']
                        lines.append(f"- **Mean**: {scores.get('test_mean', np.mean(test_scores)):.4f}")
                        lines.append(f"- **Std**: {scores.get('test_std', np.std(test_scores)):.4f}")
                        lines.append(f"- **Min**: {scores.get('test_min', np.min(test_scores)):.4f}")
                        lines.append(f"- **Max**: {scores.get('test_max', np.max(test_scores)):.4f}")
                        lines.append("")

                # Feature importance
                if 'result' in result and isinstance(result['result'], dict) and 'feature_importances' in result['result']:
                    lines.append("### Feature Importance")
                    lines.append("")
                    fi = result['result']['feature_importances']
                    lines.append("| Feature | Importance |")
                    lines.append("|---------|------------|")
                    for feat, imp in fi.items():
                        lines.append(f"| {feat} | {imp:.4f} |")
                    lines.append("")

                lines.append("---")
                lines.append("")

            if not lines:
                lines = ["# TOM MLEngine Report", "", "No results to report.", ""]

        else:
            # Text format
            lines.append("TOM MLEngine Report")
            lines.append("=" * 50)
            lines.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("")

            for i, result in enumerate(results):
                lines.append(f"Result {i+1}")
                lines.append("-" * 30)
                lines.append(f"Status: {result.get('status', 'N/A')}")
                lines.append(f"Message: {result.get('message', 'N/A')}")
                lines.append("")

                if 'metrics' in result and result['metrics']:
                    lines.append("Metrics:")
                    for key, val in result['metrics'].items():
                        if isinstance(val, (int, float)):
                            lines.append(f"  {key}: {val:.6f}")
                        else:
                            lines.append(f"  {key}: {str(val)[:60]}")
                    lines.append("")

                lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # UTILITY: LIST AVAILABLE ALGORITHMS
    # ------------------------------------------------------------------

    def list_algorithms(self):
        """Return a dict of all available algorithms grouped by category."""
        registry = self._get_algorithm_registry()
        result = {
            "regression": sorted(list(registry.get('regression', {}).keys()) + ['polynomialregression']),
            "classification": sorted(list(registry.get('classification', {}).keys())),
            "clustering": sorted(list(registry.get('clustering', {}).keys())),
            "dim_reduction": sorted(list(registry.get('dim_reduction', {}).keys()) + ['tsne', 'umap']),
            "ensemble": sorted(list(registry.get('ensemble', {}).keys())),
            "anomaly_detection": sorted(list(registry.get('anomaly', {}).keys()) + ['dbscan_outlier']),
            "deep_learning": ['mlpclassifier', 'mlpregressor', 'autoencoder'],
            "time_series": ['arima', 'sarima', 'exponential_smoothing', 'simple_moving_average',
                            'holtwinters', 'seasonal_decompose', 'prophet_decomposition'],
            "feature_engineering": sorted(list(registry.get('feature_engineering', {}).keys()) + ['pca_features']),
            "hyperparameter_tuning": ['gridsearchcv', 'randomizedsearchcv', 'bayessearchcv', 'halvinggridsearchcv'],
            "cross_validation": sorted(list(registry.get('cv', {}).keys())),
        }
        return result
