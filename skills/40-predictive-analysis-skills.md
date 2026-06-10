# Predictive Analysis Skills

## Core Concepts
- Predictive vs Descriptive vs Prescriptive Analytics
- Supervised vs Unsupervised vs Reinforcement Learning
- Classification vs Regression vs Time Series tasks
- Overfitting, underfitting, bias-variance tradeoff
- Cross-validation techniques: K-fold, stratified, time series
- Feature engineering, selection, extraction
- Model evaluation metrics for different task types

## Regression Algorithms
- Linear Regression (OLS)
- Polynomial Regression
- Ridge Regression (L2 regularization)
- Lasso Regression (L1 regularization)
- ElasticNet (L1 + L2)
- Support Vector Regression (SVR)
- Decision Tree Regression
- Random Forest Regression
- Gradient Boosting Regression (XGBoost, LightGBM, CatBoost)
- Bayesian Regression
- Neural Network Regression (MLP, RNN, LSTM)

## Classification Algorithms
- Logistic Regression
- K-Nearest Neighbors (KNN)
- Support Vector Machines (SVM, SVC)
- Decision Trees (CART, C4.5, ID3)
- Random Forest
- Gradient Boosting (XGBoost, LightGBM, CatBoost)
- Naive Bayes (Gaussian, Bernoulli, Multinomial)
- Neural Networks (MLP, CNN)
- Linear Discriminant Analysis (LDA)
- Quadratic Discriminant Analysis (QDA)
- Ensemble Methods: Voting, Stacking, Bagging

## Clustering Algorithms
- K-Means
- DBSCAN
- Hierarchical (Agglomerative)
- Gaussian Mixture Models
- Mean Shift
- OPTICS
- Affinity Propagation
- Spectral Clustering
- BIRCH
- Mini-Batch K-Means

## Time Series Analysis
- Components: Trend, Seasonality, Cyclical, Residual
- Decomposition: Additive, Multiplicative, STL
- Stationarity: ADF test, KPSS test, differencing
- Autocorrelation: ACF, PACF plots
- ARIMA: p,d,q parameter selection
- SARIMA: Seasonal ARIMA
- SARIMAX: With exogenous variables
- Exponential Smoothing: Simple, Holt's, Holt-Winters
- Prophet: Facebook's time series forecasting
- LSTM/GRU for time series
- N-BEATS: Neural basis expansion
- Temporal Fusion Transformer
- DeepAR: Amazon's probabilistic forecasting
- Ensemble forecasting for weather/climate
- Evaluation: MAE, MSE, RMSE, MAPE, sMAPE, MASE

## Feature Engineering
- Lag features (t-1, t-2, ..., t-n)
- Rolling window statistics (mean, std, min, max)
- Expanding window statistics
- Fourier transforms for seasonality
- Date/time features (hour, day, month, quarter, year, day of week, weekend)
- Holiday indicators
- Differencing (first order, second order, seasonal)
- Interaction features
- Polynomial features
- Binning/discretization
- One-hot encoding, label encoding, target encoding

## Hyperparameter Tuning
- Grid Search
- Random Search
- Bayesian Optimization (Hyperopt, Optuna)
- Halving Grid/Random Search
- Genetic Algorithms
- Cross-Validation for parameter selection

## Model Deployment
- Model serialization (pickle, joblib, ONNX)
- Model serving (Flask, FastAPI, TensorFlow Serving, MLflow)
- Docker containerization
- Feature stores (Feast, Tecton, Hopsworks)
- Monitoring drift (data drift, concept drift, prediction drift)
- A/B testing for model comparison
- CI/CD for ML pipelines
- MLOps: MLflow, Kubeflow, Airflow, DVC

## Domain-Specific Predictive Models

### Stock Market Prediction
- Technical indicators: RSI, MACD, Bollinger Bands, Moving Averages, Stochastic
- Fundamental analysis: PE ratio, EPS, revenue growth, debt/equity
- Sentiment analysis: News sentiment, social media, earnings calls
- Time series models: ARIMA, LSTM, Transformer
- Risk management: Value at Risk (VaR), Monte Carlo simulation
- Portfolio optimization: Markowitz efficient frontier, Sharpe ratio

### Weather Prediction
- Numerical Weather Prediction (NWP): GFS, ECMWF, UK Met Office
- Ensemble forecasting: Multiple model runs for uncertainty quantification
- Machine learning: CNN for satellite imagery, LSTM for time series
- Nowcasting: Radar-based precipitation prediction (0-6 hours)
- Climate modeling: Global Climate Models (GCMs), RCP scenarios

### Healthcare Prediction
- Disease diagnosis from symptoms/imaging/lab results
- Patient readmission risk within 30 days
- Disease progression modeling for chronic conditions
- Drug response prediction: Pharmacogenomics
- Epidemic forecasting: SIR, SEIR, agent-based models
- Mortality prediction: ICU scoring systems (APACHE, SOFA)
- Medical imaging: CNN for X-ray, CT, MRI classification

### Demand Forecasting
- Time series: ARIMA, Prophet, exponential smoothing
- Causal models: Incorporate promotions, holidays, pricing
- Machine learning: Gradient boosting with external features
- Deep learning: DeepAR, Temporal Fusion Transformer
- Hierarchical forecasting: Top-down, bottom-up, optimal combination

### Fraud Detection
- Anomaly detection: Isolation Forest, LOF, One-Class SVM
- Supervised: Gradient boosting on labeled fraud data
- Graph-based: Network analysis for fraud rings
- Real-time: Streaming models with feature engineering
- Explainability: SHAP, LIME for fraud investigation

### Churn Prediction
- Customer lifetime value (CLV/LTV) modeling
- Survival analysis: Kaplan-Meier, Cox proportional hazards
- Propensity scoring: Logistic regression, gradient boosting
- Feature engineering: Usage patterns, support tickets, payment history

### Energy Forecasting
- Load forecasting: Short-term (hours), medium-term (days), long-term (years)
- Renewable generation: Solar irradiance, wind speed prediction
- Price forecasting: Electricity market price prediction
- Smart grid: Real-time consumption prediction

### Sports Prediction
- Elo rating systems
- Win probability models
- Player performance prediction
- Draft prospect evaluation
- Betting odds analysis

## Python Libraries
- scikit-learn: All classic ML algorithms
- statsmodels: ARIMA, SARIMAX, VAR, exponential smoothing
- Prophet: Facebook's time series
- XGBoost, LightGBM, CatBoost: Gradient boosting
- PyTorch, TensorFlow/Keras: Deep learning
- pytorch-forecasting: Time series deep learning
- darts: Time series made easy
- sktime: Unified time series ML
- tsfresh: Time series feature extraction
- AutoML: AutoGluon, H2O, TPOT, FLAML

## Building Predictive Bots
- Architecture: Data pipeline → feature store → model → prediction API → dashboard
- Real-time vs batch prediction
- Feature serving latency optimization
- Model versioning and rollback
- Prediction explanations (SHAP, LIME)
- Alerting on prediction drift
- Automated retraining pipelines
