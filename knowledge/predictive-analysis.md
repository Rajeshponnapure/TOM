# Predictive Analysis — Complete Knowledge Base

> **For Tom — an AI assistant.** All algorithms, techniques, code patterns, and domain-specific models.
> Covers 7 major sections: Foundations → Algorithms → Domains → Feature Engineering → Evaluation → MLOps → Implementations.
> Target audience: AI agent referencing this for prediction task architecture, algorithm selection, and production patterns.

---

## 1. Foundations of Predictive Analysis

### 1.1 What is Predictive Analytics?

Predictive analytics uses historical data and ML to forecast future outcomes.

| Type | Question | Example |
|---|---|---|
| **Descriptive** | What happened? | "Sales dropped 15%" |
| **Predictive** | What will happen? | "Sales will drop 12% next quarter" |
| **Prescriptive** | What should we do? | "Increase ad spend 20%" |

### 1.2 The Predictive Modeling Pipeline

```
Raw Data → Collection → Cleaning → EDA → Feature Engineering → Split → Train → Evaluate → Deploy → Monitor
```

**Steps:** problem definition → data collection (DBs, APIs, streaming) → cleaning → EDA (distributions, seasonality, stationarity) → feature engineering → train/val/test split (chronological for TS) → model selection → training & tuning → evaluation (backtesting, residual analysis) → deployment (API, batch, streaming) → monitoring (drift detection, retraining).

### 1.3 Data Collection, Cleaning, Feature Engineering

```python
import pandas as pd, numpy as np
from sqlalchemy import create_engine

# SQL extraction
df = pd.read_sql("SELECT * FROM orders WHERE date >= '2024-01-01'",
                 create_engine("postgresql://user:pass@host/db"))

# Cleaning
df = df.drop_duplicates(subset=["timestamp","id"])
df = df.fillna(method="ffill").interpolate(method="linear")
Q1, Q3 = df["value"].quantile([0.25, 0.75])
iqr = Q3 - Q1
df["value"] = df["value"].clip(Q1-1.5*iqr, Q3+1.5*iqr)
df["timestamp"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp").reset_index(drop=True)
```

### 1.4 Training/Testing/Validation Split

```python
# Random split (NOT for time series)
from sklearn.model_selection import train_test_split
X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.2)

# Chronological split (time series)
train = df.iloc[:int(0.7*len(df))]
val = df.iloc[int(0.7*len(df)):int(0.85*len(df))]
test = df.iloc[int(0.85*len(df)):]

# TimeSeriesSplit
from sklearn.model_selection import TimeSeriesSplit
tscv = TimeSeriesSplit(n_splits=5, test_size=24)
for train_idx, test_idx in tscv.split(X):
    X_tr, X_te = X[train_idx], X[test_idx]
```

**Leakage:** Never use future info for past predictions. Fit scaler on train only. Don't compute global stats before split. Don't shuffle time series.

### 1.5 Time Series vs Cross-Sectional

| Aspect | Time Series | Cross-Sectional |
|---|---|---|
| Structure | Ordered by time | Independent |
| Assumption | Temporal dependency | I.I.D. |
| Split | Chronological | Random |
| CV | Expanding/rolling window | K-fold |
| Stationarity | Usually required | Not required |

### 1.6 Overfitting, Underfitting, Bias-Variance Tradeoff

**Error = Bias² + Variance + Irreducible Error**

| Problem | Symptom | Fix |
|---|---|---|
| High bias | Train error high | Add features, deeper model, reduce regularization |
| High variance | Train << test error | More data, regularization, feature selection, ensemble |

```python
from sklearn.learning_curve import learning_curve
train_sizes, train_scores, val_scores = learning_curve(
    model, X, y, cv=5
)
# Converging high error → bias. Diverging gap → variance.
```

---

## 2. All Predictive Algorithms

### 2.1 Regression-Based

```python
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
from sklearn.svm import SVR
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, WhiteKernel

# Linear
lr = LinearRegression().fit(X_tr, y_tr)

# Ridge (L2): Loss = MSE + α·Σβ² — shrinks coefficients
ridge = Ridge(alpha=1.0).fit(X_tr, y_tr)

# Lasso (L1): Loss = MSE + α·Σ|β| — feature selection (can zero coefficients)
lasso = Lasso(alpha=0.01).fit(X_tr, y_tr)
print(f"Features used: {np.sum(lasso.coef_ != 0)}/{len(lasso.coef_)}")

# ElasticNet: L1 + L2 (l1_ratio=0→Ridge, 1→Lasso)
elastic = ElasticNet(alpha=0.1, l1_ratio=0.5).fit(X_tr, y_tr)

# Bayesian Regression — returns uncertainty
from sklearn.linear_model import BayesianRidge
bayes = BayesianRidge().fit(X_tr, y_tr)
y_pred, y_std = bayes.predict(X_te, return_std=True)

# SVR — good for small/medium, sensitive to scaling
from sklearn.preprocessing import StandardScaler
scaler = StandardScaler()
X_tr_s = scaler.fit_transform(X_tr)
svr = SVR(kernel="rbf", C=100, gamma="scale").fit(X_tr_s, y_tr)

# Gaussian Process — natural uncertainty
kernel = RBF(length_scale=1.0) + WhiteKernel(noise_level=0.1)
gpr = GaussianProcessRegressor(kernel=kernel).fit(X_tr, y_tr)
y_mean, y_std = gpr.predict(X_te, return_std=True)
```

### 2.2 Tree-Based

```python
from sklearn.tree import DecisionTreeRegressor
from sklearn.ensemble import RandomForestRegressor, AdaBoostRegressor
import xgboost as xgb, lightgbm as lgb, catboost as cb

# Decision Tree — interpretable but high variance
dt = DecisionTreeRegressor(max_depth=5, min_samples_leaf=10).fit(X_tr, y_tr)

# Random Forest — bagging reduces variance
rf = RandomForestRegressor(n_estimators=500, max_depth=10,
    min_samples_leaf=5, max_features="sqrt", n_jobs=-1).fit(X_tr, y_tr)

# XGBoost — gradient boosting with regularization
xgb_model = xgb.XGBRegressor(n_estimators=1000, max_depth=6,
    learning_rate=0.01, subsample=0.8, colsample_bytree=0.8)
xgb_model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False,
              early_stopping_rounds=50)

# LightGBM — leaf-wise growth, faster, native categorical
lgbm = lgb.LGBMRegressor(n_estimators=1000, num_leaves=31,
    learning_rate=0.01, subsample=0.8, colsample_bytree=0.8)
lgbm.fit(X_tr, y_tr, eval_set=[(X_val, y_val)],
         callbacks=[lgb.early_stopping(50)])

# CatBoost — best for categorical features (no encoding needed)
cat = cb.CatBoostRegressor(iterations=1000, learning_rate=0.01,
    depth=6, cat_features=["cat_col"], verbose=False)
cat.fit(X_tr, y_tr, eval_set=(X_val, y_val))

# AdaBoost
ada = AdaBoostRegressor(estimator=DecisionTreeRegressor(max_depth=3),
    n_estimators=100).fit(X_tr, y_tr)
```

### 2.3 Neural Networks

```python
import torch, torch.nn as nn, torch.optim as optim
import torch.nn.functional as F

# MLP
class MLP(nn.Module):
    def __init__(self, in_dim, dims=[128,64,32]):
        super().__init__()
        layers = []
        for d in dims:
            layers += [nn.Linear(in_dim, d), nn.BatchNorm1d(d), nn.ReLU(), nn.Dropout(0.2)]
            in_dim = d
        layers.append(nn.Linear(in_dim, 1))
        self.net = nn.Sequential(*layers)
    def forward(self, x):
        return self.net(x).squeeze(-1)

# LSTM — handles long sequences via gating mechanism
class LSTMPredictor(nn.Module):
    def __init__(self, in_size, hid=128, n_layers=2):
        super().__init__()
        self.lstm = nn.LSTM(in_size, hid, n_layers, batch_first=True, dropout=0.2, bidirectional=True)
        self.fc = nn.Linear(hid*2, 1)
        self.drop = nn.Dropout(0.2)
    def forward(self, x):
        out, _ = self.lstm(x)
        return self.fc(self.drop(out[:,-1,:])).squeeze(-1)

# GRU — 2 gates vs LSTM's 3, faster, similar performance
class GRUPredictor(nn.Module):
    def __init__(self, in_size, hid=128, n_layers=2):
        super().__init__()
        self.gru = nn.GRU(in_size, hid, n_layers, batch_first=True, dropout=0.2)
        self.fc = nn.Linear(hid, 1)
    def forward(self, x):
        out, _ = self.gru(x)
        return self.fc(out[:,-1,:]).squeeze(-1)

# Transformer — parallel processing, best for long-range dependencies
class TSTransformer(nn.Module):
    def __init__(self, in_dim, d_model=128, nhead=8, n_layers=4):
        super().__init__()
        self.proj = nn.Linear(in_dim, d_model)
        self.pe = PositionalEncoding(d_model)
        enc = nn.TransformerEncoderLayer(d_model, nhead, 512, dropout=0.1, batch_first=True)
        self.tf = nn.TransformerEncoder(enc, n_layers)
        self.fc = nn.Linear(d_model, 1)
    def forward(self, x):
        return self.fc(self.tf(self.pe(self.proj(x)))[:,-1,:]).squeeze(-1)

class PositionalEncoding(nn.Module):
    def __init__(self, d_model, max_len=5000):
        super().__init__()
        pe = torch.zeros(max_len, d_model)
        pos = torch.arange(0,max_len).unsqueeze(1).float()
        div = torch.exp(torch.arange(0,d_model,2).float() * -(np.log(10000)/d_model))
        pe[:,0::2] = torch.sin(pos*div)
        pe[:,1::2] = torch.cos(pos*div)
        self.register_buffer("pe", pe.unsqueeze(0))
    def forward(self, x):
        return x + self.pe[:,:x.size(1)]

# CNN for time series (TCN-style)
class CNNTS(nn.Module):
    def __init__(self, channels, seq_len):
        super().__init__()
        self.c1 = nn.Conv1d(channels, 64, 3, padding=1)
        self.c2 = nn.Conv1d(64, 128, 5, padding=2)
        self.c3 = nn.Conv1d(128, 256, 7, padding=3)
        self.pool = nn.MaxPool1d(2)
        self.fc = nn.Linear(256 * (seq_len // 8), 1)
    def forward(self, x):
        x = self.pool(F.relu(self.c1(x)))
        x = self.pool(F.relu(self.c2(x)))
        x = self.pool(F.relu(self.c3(x)))
        return self.fc(x.view(x.size(0),-1)).squeeze(-1)

# Sequence creation
def create_sequences(data, seq_len=60):
    X, y = [], []
    for i in range(len(data)-seq_len):
        X.append(data[i:i+seq_len])
        y.append(data[i+seq_len])
    return torch.tensor(np.array(X), dtype=torch.float32), torch.tensor(np.array(y), dtype=torch.float32)
```

### 2.4 Time Series Specific

```python
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.tsa.stattools import adfuller
from prophet import Prophet
from pmdarima import auto_arima
from sktime.forecasting.theta import ThetaForecaster
from sktime.forecasting.tbats import TBATS

# Stationarity check
def is_stationary(series):
    return adfuller(series.dropna())[1] < 0.05

# ARIMA(p,d,q) — autoregressive integrated moving average
if not is_stationary(df["value"]):
    df["value_diff"] = df["value"].diff()
model = ARIMA(df["value"], order=(2,1,2)).fit()
forecast = model.forecast(steps=10)

# SARIMA — with seasonality
model = SARIMAX(df["value"], order=(1,1,1), seasonal_order=(1,1,1,12)).fit(disp=False)

# Auto ARIMA
model = auto_arima(df["value"], seasonal=True, m=12, trace=True, stepwise=True)

# SARIMAX — with external regressors
model = SARIMAX(df["value"], exog=df[["holiday","temp","promo"]],
                order=(1,1,1), seasonal_order=(1,1,1,12)).fit(disp=False)

# Prophet — trend + seasonality + holidays + regressors
pdf = df.rename(columns={"timestamp":"ds", "value":"y"})
m = Prophet(yearly_seasonality=True, weekly_seasonality=True,
            seasonality_mode="multiplicative")
m.add_country_holidays("US")
m.add_regressor("temperature")
m.fit(pdf)
future = m.make_future_dataframe(periods=30)
future["temperature"] = temps
forecast = m.predict(future)

# Holt-Winters — exponential smoothing
ets = ExponentialSmoothing(df["value"], trend="add", seasonal="add",
                           seasonal_periods=12, damped_trend=True).fit()
forecast = ets.forecast(steps=12)

# Theta — M3 competition winner
theta = ThetaForecaster().fit(df["value"])
pred = theta.predict(fh=[1,2,3,4,5,6])

# TBATS — multiple seasonalities
tbats = TBATS(use_box_cox=True, use_trend=True, seasonal_periods=[7, 365.25])
tbats.fit(df["value"])
pred = tbats.predict(fh=[1,2,3,4,5,6,7])

# Deep learning TS models (via pytorch-forecasting, darts, neuralforecast)
# N-BEATS — pure ML, no feature engineering, basis expansion
# DeepAR — probabilistic RNN, prediction intervals
# Temporal Fusion Transformer — best-in-class hybrid

# TFT with pytorch-forecasting
from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
training = TimeSeriesDataSet(df, time_idx="time_idx", target="value",
    group_ids=["product_id"], max_encoder_length=96, max_prediction_length=24,
    static_categoricals=["product_category"],
    time_varying_known_categoricals=["day_of_week"],
    time_varying_known_reals=["price","promotion"],
    time_varying_unknown_reals=["value"])
tft = TemporalFusionTransformer.from_dataset(training, hidden_size=128,
    attention_head_size=4, dropout=0.1, output_size=7)
```

### 2.5 Probabilistic Models

```python
import numpy as np
from hmmlearn import hmm
from pgmpy.models import BayesianNetwork
from pgmpy.estimators import MaximumLikelihoodEstimator
from pgmpy.inference import VariableElimination

# Markov Chain — state transition probabilities
class MarkovChain:
    def __init__(self, states):
        self.states = states; self.n = len(states)
        self.counts = np.zeros((self.n, self.n))
    def fit(self, seq):
        for i in range(len(seq)-1):
            s0,s1 = self.states.index(seq[i]), self.states.index(seq[i+1])
            self.counts[s0,s1] += 1
        self.P = self.counts / self.counts.sum(axis=1, keepdims=True)
    def predict(self, state):
        return np.random.choice(self.n, p=self.P[self.states.index(state)])

# Hidden Markov Model — latent states, Gaussian emissions
hmm_model = hmm.GaussianHMM(n_components=3, covariance_type="full", n_iter=100)
hmm_model.fit(X)  # (n_samples, n_features)
states = hmm_model.predict(X_test)
log_prob = hmm_model.score(X_test)

# Bayesian Network — causal/dependency structure
model = BayesianNetwork([("Weather","Traffic"),("Weather","Demand"),
                         ("Traffic","Delivery"),("Demand","Delivery")])
model.fit(data, estimator=MaximumLikelihoodEstimator)
infer = VariableElimination(model)
result = infer.query(["Delivery"], evidence={"Weather":"Rain"})

# Monte Carlo Simulation — GBM for prices
def monte_carlo_price(S0, mu, sigma, days=252, sims=10000):
    dt = 1/252; prices = np.zeros((days, sims)); prices[0] = S0
    for t in range(1, days):
        e = np.random.standard_normal(sims)
        prices[t] = prices[t-1] * np.exp((mu-0.5*sigma**2)*dt + sigma*np.sqrt(dt)*e)
    return prices

prices = monte_carlo_price(100, 0.08, 0.2)
var_95 = np.percentile(prices[-1] - 100, 5)
```

### 2.6 Ensemble Methods

```python
from sklearn.ensemble import StackingRegressor, VotingRegressor, BaggingRegressor
from sklearn.linear_model import Ridge

# Stacking — meta-model learns how to combine base models
stack = StackingRegressor([
    ("rf", RandomForestRegressor(n_estimators=200, max_depth=10)),
    ("xgb", xgb.XGBRegressor(n_estimators=200, max_depth=6)),
    ("svr", SVR(kernel="rbf", C=100))
], final_estimator=Ridge(alpha=1.0), cv=5).fit(X_tr, y_tr)

# Blending — simpler stacking with holdout
X_tr_b, X_bl, y_tr_b, y_bl = train_test_split(X_tr, y_tr, test_size=0.2)
rf = RandomForestRegressor().fit(X_tr_b, y_tr_b)
xgb_m = xgb.XGBRegressor().fit(X_tr_b, y_tr_b)
blend = np.column_stack([rf.predict(X_bl), xgb_m.predict(X_bl)])
meta = Ridge().fit(blend, y_bl)
test_feat = np.column_stack([rf.predict(X_te), xgb_m.predict(X_te)])
final_pred = meta.predict(test_feat)

# Voting — weighted average
vote = VotingRegressor([
    ("rf", RandomForestRegressor(n_estimators=200)),
    ("xgb", xgb.XGBRegressor(n_estimators=200))
]).fit(X_tr, y_tr)

# Weighted manual ensemble — optimize weights by validation performance
from scipy.optimize import minimize
def optimize_weights(preds, y_val):
    def objective(w):
        w = np.array(w)/sum(w)
        return mean_squared_error(y_val, sum(w[i]*preds[i] for i in range(len(preds))))
    return minimize(objective, [1/len(preds)]*len(preds), bounds=[(0,1)]*len(preds)).x

weights = optimize_weights([rf_pred, xgb_pred, lgbm_pred], y_val)
ensemble = sum(w*p for w,p in zip(weights, [rf_pred, xgb_pred, lgbm_pred]))

# Bagging — bootstrap + aggregation
bag = BaggingRegressor(estimator=DecisionTreeRegressor(max_depth=5),
    n_estimators=500, max_samples=0.8, max_features=0.8,
    oob_score=True, n_jobs=-1).fit(X_tr, y_tr)
```

---

## 3. Domain-Specific Predictive Models

### 3.1 Stock Market Prediction

```python
# Technical Indicators
def add_indicators(df):
    delta = df["close"].diff()
    gain = delta.where(delta>0,0).rolling(14).mean()
    loss = (-delta.where(delta<0,0)).rolling(14).mean()
    rs = gain/loss
    df["rsi"] = 100 - 100/(1+rs)
    ema12 = df["close"].ewm(span=12).mean()
    ema26 = df["close"].ewm(span=26).mean()
    df["macd"] = ema12 - ema26
    df["macd_signal"] = df["macd"].ewm(span=9).mean()
    sma20 = df["close"].rolling(20).mean()
    std20 = df["close"].rolling(20).std()
    df["bb_upper"] = sma20 + 2*std20
    df["bb_lower"] = sma20 - 2*std20
    df["atr"] = pd.concat([
        df["high"]-df["low"], (df["high"]-df["close"].shift()).abs(),
        (df["low"]-df["close"].shift()).abs()
    ], axis=1).max(axis=1).rolling(14).mean()
    return df

# Sentiment score from news
from transformers import pipeline
sent = pipeline("text-classification", model="mrm8488/distilroberta-finetuned-financial-news-sentiment")
def sentiment_score(headlines):
    scores = {"positive":0,"negative":0,"neutral":0}
    for r in sent(headlines):
        scores[r["label"].lower()] += r["score"]
    return (scores["positive"]-scores["negative"])/sum(scores.values())

# Order flow imbalance
def ofi(trades):
    trades["side"] = trades.apply(lambda x: "buy" if x.price>x.mid_price else "sell", axis=1)
    buy = trades[trades.side=="buy"].volume.sum()
    sell = trades[trades.side=="sell"].volume.sum()
    return (buy-sell)/(buy+sell) if (buy+sell)>0 else 0

# VaR
def calc_var(returns, cl=0.95):
    mu, sigma = returns.mean(), returns.std()
    z = stats.norm.ppf(1-cl)
    var_param = mu + z*sigma
    var_hist = np.percentile(returns, (1-cl)*100)
    var_mc = np.percentile(np.random.normal(mu, sigma, 10000), (1-cl)*100)
    return {"parametric":var_param, "historical":var_hist, "mc":var_mc}
```

### 3.2 Weather & Healthcare

```python
# SIR Epidemic Model
from scipy.integrate import odeint
def sir(y, t, beta, gamma):
    S,I,R = y
    return [-beta*S*I, beta*S*I-gamma*I, gamma*I]
def forecast_epidemic(S0,I0,R0,beta,gamma,days):
    sol = odeint(sir, [S0,I0,R0], np.linspace(0,days,days), args=(beta,gamma))
    return pd.DataFrame({"day":range(days), "S":sol[:,0],"I":sol[:,1],"R":sol[:,2]})

# Patient readmission
import xgboost as xgb
readmit_model = xgb.XGBClassifier(n_estimators=500, max_depth=4,
    learning_rate=0.01, scale_pos_weight=3, eval_metric="auc")
readmit_model.fit(df[feats], df["readmitted_30d"])

# Disease progression (mixed effects)
import statsmodels.api as sm
from statsmodels.regression.mixed_linear_model import MixedLM
mixed = MixedLM.from_formula("biomarker ~ time + age + treatment",
    groups="patient_id", re_formula="1+time").fit()
```

### 3.3 Sports, Sales, Energy

```python
# Elo Rating
class Elo:
    def __init__(self, K=32, init=1500):
        self.ratings = {}; self.K = K; self.init = init
    def expected(self, a, b):
        return 1/(1+10**((b-a)/400))
    def update(self, a, b, sa, sb):
        self.ratings.setdefault(a, self.init)
        self.ratings.setdefault(b, self.init)
        ea, eb = self.expected(self.ratings[a], self.ratings[b]), self.expected(self.ratings[b], self.ratings[a])
        wa, wb = (1,0) if sa>sb else ((0,1) if sa<sb else (0.5,0.5))
        self.ratings[a] += self.K*(wa-ea)
        self.ratings[b] += self.K*(wb-eb)

# Demand forecasting with Prophet + regressors
m = Prophet(yearly_seasonality=True, weekly_seasonality=True)
m.add_regressor("price"); m.add_regressor("promotion")
m.add_regressor("competitor_price"); m.add_regressor("holiday_flag")
m.fit(pdf)
future = m.make_future_dataframe(periods=90)

# Energy load forecasting
df["hour"] = df.timestamp.dt.hour; df["day_of_week"] = df.timestamp.dt.dayofweek
df["is_weekend"] = df.day_of_week.isin([5,6]).astype(int)
model = lgb.LGBMRegressor(n_estimators=1000, num_leaves=63, learning_rate=0.05)
model.fit(df[features], df["load"])

# Fraud detection
from sklearn.ensemble import IsolationForest
df["amount_zscore"] = (df.amount-df.amount.mean())/df.amount.std()
df["tx_count_1h"] = df.groupby("user_id").timestamp.transform(
    lambda x: x.rolling("1h", closed="left").count())
iso = IsolationForest(contamination=0.01).fit(df[["amount_zscore","tx_count_1h"]])
df["anomaly_score"] = iso.fit_predict(df[["amount_zscore","tx_count_1h"]])

# Churn prediction — RFM + survival
df["recency"] = (df.ref_date - df.last_purchase).dt.days
df["frequency"] = df.purchase_count_90d
df["monetary"] = df.total_spend_90d
churn_model = RandomForestClassifier(n_estimators=500, max_depth=8,
    min_samples_leaf=20, class_weight="balanced").fit(df[feats], df.churned)
df["churn_prob"] = churn_model.predict_proba(df[feats])[:,1]
```

---

## 4. Feature Engineering for Prediction

```python
# Lag features
def lags(df, cols, lags=[1,2,3,6,12,24,48]):
    for c in cols:
        for l in lags:
            df[f"{c}_lag_{l}"] = df[c].shift(l)
    return df

# Rolling windows
def rolling(df, cols, windows=[3,6,12,24]):
    for c in cols:
        for w in windows:
            df[f"{c}_mean_{w}"] = df[c].rolling(w).mean()
            df[f"{c}_std_{w}"] = df[c].rolling(w).std()
            df[f"{c}_min_{w}"] = df[c].rolling(w).min()
            df[f"{c}_max_{w}"] = df[c].rolling(w).max()
            df[f"{c}_skew_{w}"] = df[c].rolling(w).skew()
            df[f"{c}_q25_{w}"] = df[c].rolling(w).quantile(0.25)
            df[f"{c}_q75_{w}"] = df[c].rolling(w).quantile(0.75)
    return df

# Expanding windows
df["cumsum"] = df["value"].cumsum()
df["expanding_mean"] = df["value"].expanding().mean()
df["drawdown"] = df["value"] / df["value"].expanding().max() - 1

# Fourier features for seasonality
def fourier(df, periods={"daily":24,"weekly":168}, order=3):
    t = np.arange(len(df))
    for name, period in periods.items():
        for k in range(1, order+1):
            df[f"sin_{name}_{k}"] = np.sin(2*np.pi*k*t/period)
            df[f"cos_{name}_{k}"] = np.cos(2*np.pi*k*t/period)
    return df

# Differencing
df["diff_1"] = df["value"].diff()
df["pct_change_1"] = df["value"].pct_change()
df["log"] = np.log1p(df["value"].clip(lower=0))
df["log_diff"] = df["log"].diff()

# Calendar features
df["hour"] = df.timestamp.dt.hour
df["day_of_week"] = df.timestamp.dt.dayofweek
df["month"] = df.timestamp.dt.month
df["quarter"] = df.timestamp.dt.quarter
df["is_weekend"] = df.day_of_week.isin([5,6]).astype(int)
df["is_holiday"] = df.timestamp.isin(holidays).astype(int)
# Cyclical encoding
for col, period in [("hour",24),("day_of_week",7),("month",12)]:
    df[f"{col}_sin"] = np.sin(2*np.pi*df[col]/period)
    df[f"{col}_cos"] = np.cos(2*np.pi*df[col]/period)

# Interaction features
df["price_x_promo"] = df.price * df.promotion
df["ratio"] = df.price / df.sma_20
df["deviation"] = df.price - df.groupby("category").price.transform("mean")
```

---

## 5. Model Evaluation for Prediction

```python
from sklearn.metrics import (mean_absolute_error, mean_squared_error,
    r2_score, mean_absolute_percentage_error, roc_auc_score, log_loss,
    accuracy_score, precision_score, recall_score, f1_score, confusion_matrix)
from scipy import stats

# Regression metrics
def reg_metrics(y, p):
    mae = mean_absolute_error(y,p)
    rmse = np.sqrt(mean_squared_error(y,p))
    mape = mean_absolute_percentage_error(y,p)*100
    denominator = (np.abs(y)+np.abs(p))/2
    smape = np.mean(np.abs(y-p)/np.where(denominator==0,1,denominator))*100
    naive_mae = np.mean(np.abs(np.diff(y)))
    mase = mae/naive_mae if naive_mae>0 else np.nan
    return {"MAE":mae,"RMSE":rmse,"MAPE":mape,"sMAPE":smape,"MASE":mase,"R2":r2_score(y,p)}

# Classification metrics
def clf_metrics(y, p, proba=None):
    m = {"accuracy":accuracy_score(y,p),"precision":precision_score(y,p),
         "recall":recall_score(y,p),"f1":f1_score(y,p)}
    if proba is not None:
        m["AUC-ROC"] = roc_auc_score(y,proba)
        m["log_loss"] = log_loss(y,proba)
    tn,fp,fn,tp = confusion_matrix(y,p).ravel()
    m["specificity"] = tn/(tn+fp) if (tn+fp)>0 else 0
    return m

# Time series CV
from sklearn.model_selection import TimeSeriesSplit
tscv = TimeSeriesSplit(n_splits=5, test_size=24)
scores = []
for tr_idx, te_idx in tscv.split(X):
    model.fit(X[tr_idx], y[tr_idx])
    scores.append(np.sqrt(mean_squared_error(y[te_idx], model.predict(X[te_idx]))))
print(f"CV RMSE: {np.mean(scores):.4f} ± {np.std(scores):.4f}")

# Expanding window CV
def expanding_cv(df, n_splits=5, min_train=100, step=24):
    scores = []
    for i in range(n_splits):
        end = min_train + i*step
        model.fit(df.iloc[:end][feats], df.iloc[:end].target)
        p = model.predict(df.iloc[end:end+step][feats])
        scores.append(np.sqrt(mean_squared_error(df.iloc[end:end+step].target, p)))
    return np.mean(scores), np.std(scores)

# Backtesting — walk-forward validation
def backtest(model, df, feats, target, init=500, step=24):
    preds, actuals = [], []
    for i in range(init, len(df), step):
        model.fit(df.iloc[:i][feats], df.iloc[:i][target])
        preds.extend(model.predict(df.iloc[i:i+step][feats]))
        actuals.extend(df.iloc[i:i+step][target].values)
    errs = np.array(preds) - np.array(actuals)
    return {"predictions":preds,"actuals":actuals,
            "rmse":np.sqrt(np.mean(errs**2)),
            "mae":np.mean(np.abs(errs)),
            "direction_acc":np.mean(np.sign(errs[:-1]) != np.sign(errs[1:]))}

# Diebold-Mariano test — compares two forecast models
    d = e1**2 - e2**2
    T = len(d); md = d.mean()
    gamma = np.array([(d[:T-j]*d[j:]).mean() for j in range(h)])
    var = gamma[0] + 2*sum(gamma[1:])
    if var <= 0: return 0, 1.0
    dm = md/np.sqrt(var/T)
    pv = 2*(1-stats.norm.cdf(abs(dm)))
    return dm, pv

# Residual analysis
def residual_analysis(res):
    from statsmodels.stats.stattools import durbin_watson
    from statsmodels.stats.diagnostic import acorr_ljungbox
    dw = durbin_watson(res)  # ≈2 = no autocorrelation
    lb = acorr_ljungbox(res, lags=[10])["lb_pvalue"].iloc[0]
    _, p_norm = stats.normaltest(res)  # >0.05 = normal
    return {"mean":res.mean(),"std":res.std(),"dw":dw,"ljung_p":lb,"norm_p":p_norm}
```

---

## 6. Building Predictive Bots

### 6.1 Architecture

```
Data Sources (Kafka/API) → Feature Store (Feast) → Model Serving (MLflow/BentoML) → Monitoring (Evidently)
                                                                                          ↓
                                                                                    Retraining Pipeline
```

### 6.2 Feature Store (Feast)

```python
from feast import FeatureStore, Entity, FeatureView, FileSource, ValueType

customer = Entity(name="customer_id", value_type=ValueType.INT64)
source = FileSource(path="data/customer_stats.parquet", timestamp_field="event_timestamp")
fv = FeatureView(name="customer_features", entities=["customer_id"], ttl="90d",
    features=[Feature(name="purchase_frequency", dtype=ValueType.FLOAT),
              Feature(name="avg_order_value", dtype=ValueType.FLOAT)],
    online=True, batch_source=source)

store = FeatureStore(repo_path="./feature_repo")
vec = store.get_online_features(features=["customer_features:purchase_frequency"],
    entity_rows=[{"customer_id": 12345}]).to_dict()
```

### 6.3 Model Serving

```python
import mlflow.pyfunc
class PredModel(mlflow.pyfunc.PythonModel):
    def __init__(self, model, pipeline):
        self.model = model; self.pipeline = pipeline
    def predict(self, ctx, inp):
        return self.model.predict(self.pipeline.transform(inp))
mlflow.pyfunc.save_model(path="models/churn_model", python_model=PredModel(m, pipe))

# BentoML
import bentoml
@bentoml.service(name="churn_predictor")
class ChurnSvc:
    def __init__(self):
        self.model = bentoml.mlflow.load_model("churn_model:latest")
    @bentoml.api(input=bentoml.io.PandasDataFrame(), output=bentoml.io.JSON())
    def predict(self, df):
        return {"predictions": self.model.predict(df).tolist()}
```

### 6.4 Monitoring Drift

```python
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset

def check_drift(ref, curr):
    r = Report(metrics=[DataDriftPreset()])
    r.run(ref, curr)
    d = r.as_dict()
    ratio = d["metrics"][0]["result"]["number_of_drifted_features"] / \
            d["metrics"][0]["result"]["number_of_features"]
    return {"drift_ratio": ratio, "alert": ratio > 0.3}

# Concept drift
def detect_concept_drift(model, X, y, window=1000):
    errs = [abs(model.predict(X.iloc[i:i+1])[0]-y.iloc[i]) for i in range(window, len(y))]
    recent = np.mean(errs[-100:])
    baseline = np.mean(errs)
    return (recent-baseline)/baseline > 0.2

# A/B test
def ab_test(ctrl, treat, X, y, n_boot=1000):
    l1, l2 = mean_squared_error(y, ctrl.predict(X)), mean_squared_error(y, treat.predict(X))
    diffs = [np.sqrt(mean_squared_error(y.sample(frac=1,replace=True),
                ctrl.predict(X.iloc[idx]))) for idx in ...]  # bootstrap
    return {"ctrl_rmse":np.sqrt(l1),"treat_rmse":np.sqrt(l2),
            "improvement":(l1-l2)/l1*100,
            "winner":"treatment" if l2<l1 else "control"}
```

### 6.5 MLOps Pipeline

```python
# Retraining trigger
def should_retrain(drift, perf_degradation, days_since_training):
    return drift > 0.3 or perf_degradation > 0.2 or days_since_training > 7

# Full pipeline
# Data ingest → Feature engineering → Train → Evaluate → Register → Deploy → Monitor
```

---

### 6.6 Hyperparameter Optimization

```python
from skopt import gp_minimize
from skopt.space import Integer, Real

def optimize_xgb(params):
    lr, md, ss, cs = params
    model = xgb.XGBRegressor(n_estimators=500, learning_rate=lr,
        max_depth=int(md), subsample=ss, colsample_bytree=cs, random_state=42)
    model.fit(X_tr, y_tr, eval_set=[(X_val, y_val)], verbose=False, early_stopping_rounds=50)
    return mean_squared_error(y_val, model.predict(X_val))

space = [Real(0.001, 0.3, name="learning_rate"),
         Integer(3, 10, name="max_depth"),
         Real(0.5, 1.0, name="subsample"),
         Real(0.3, 1.0, name="colsample_bytree")]
result = gp_minimize(optimize_xgb, space, n_calls=30, random_state=42)
print(f"Best params: {result.x}, Best RMSE: {result.fun:.4f}")
```

### 6.7 Prediction Intervals

```python
# Quantile regression for uncertainty
from sklearn.ensemble import GradientBoostingRegressor

lower = GradientBoostingRegressor(loss="quantile", alpha=0.1).fit(X_tr, y_tr)
upper = GradientBoostingRegressor(loss="quantile", alpha=0.9).fit(X_tr, y_tr)
median = GradientBoostingRegressor(loss="quantile", alpha=0.5).fit(X_tr, y_tr)

lo, mid, hi = lower.predict(X_te), median.predict(X_te), upper.predict(X_te)
# 80% prediction interval: [lo, hi]

# Conformal prediction — distribution-free uncertainty
from mapie.regression import MapieRegressor
mapie = MapieRegressor(xgb.XGBRegressor(), method="plus", cv=5)
mapie.fit(X_tr, y_tr)
y_pred, y_pis = mapie.predict(X_te, alpha=0.1)
# y_pis[:, 0] = lower bound, y_pis[:, 1] = upper bound
```

## 7. Practical Implementation

### 7.1 Python Libraries

| Library | Purpose |
|---|---|
| `scikit-learn` | General ML (linear, ensemble, SVM, preprocessing) |
| `statsmodels` | ARIMA, SARIMAX, VAR, ETS, statistical tests |
| `prophet` | Time series (trend + seasonality + holidays) |
| `pytorch-forecasting` | TFT, N-BEATS, NHiTS, DeepAR |
| `darts` | Unified TS (ARIMA, Prophet, Transformer, TFT) |
| `sktime` | Forecasting, transformations, TS CV |
| `tsfresh` | Automatic feature extraction |
| `neuralforecast` | LSTM, NBEATS, NHITS, PatchTST |
| `gluonts` | DeepAR, WaveNet, Transformer |
| `mlforecast` | ML-based (LGBM, XGBoost) forecasting |

### 7.2 Quick Code: Stock Prediction

```python
import yfinance as yf, pandas as pd, numpy as np, xgboost as xgb
from sklearn.metrics import mean_squared_error

df = yf.Ticker("AAPL").history(period="5y")
df.columns = df.columns.str.lower()

# Features
df["sma_20"] = df.close.rolling(20).mean()
df["rsi"] = 100 - 100/(1+df.close.diff().where(lambda x: x>0,0).rolling(14).mean()/
    (-df.close.diff().where(lambda x: x<0,0).rolling(14).mean()))
df["return"] = df.close.pct_change()
for l in [1,2,3,5]:
    df[f"lag_{l}"] = df.close.shift(l)

df = df.dropna()
feats = [c for c in df.columns if c not in ["open","high","low","close","volume"]]
X, y = df[feats], df["return"].shift(-1).dropna()

split = int(len(X)*0.8)
model = xgb.XGBRegressor(n_estimators=500, max_depth=5, learning_rate=0.01).fit(
    X.iloc[:split], y.iloc[:split])
pred = model.predict(X.iloc[split:])
print(f"RMSE: {np.sqrt(mean_squared_error(y.iloc[split:], pred)):.4f}")
```

### 7.3 Quick Code: Demand Forecasting

```python
import lightgbm as lgb

df["day_of_week"] = df.date.dt.dayofweek
df["month"] = df.date.dt.month
df["is_weekend"] = df.day_of_week.isin([5,6]).astype(int)

for l in [1,2,3,7,14,28]:
    df[f"demand_lag_{l}"] = df.groupby("product_id").demand.shift(l)
for w in [7,14,28]:
    df[f"demand_roll_mean_{w}"] = df.groupby("product_id").demand.transform(
        lambda x: x.shift(1).rolling(w).mean())

df = df.dropna()
feats = [c for c in df.columns if c not in ["date","demand","product_id"]]
model = lgb.LGBMRegressor(n_estimators=1000, num_leaves=31, learning_rate=0.05)
model.fit(df.iloc[:800][feats], df.iloc[:800].demand,
          eval_set=[(df.iloc[800:][feats], df.iloc[800:].demand)],
          callbacks=[lgb.early_stopping(50)])
```

### 7.4 Quick Code: Churn Prediction

```python
import xgboost as xgb
from sklearn.metrics import roc_auc_score

df["log_tenure"] = np.log1p(df.tenure_days)
df["support_rate"] = df.support_tickets / (df.tenure_days + 1)
df["login_rate"] = df.login_frequency / (df.tenure_days + 1)

feats = [c for c in df.columns if c not in ["customer_id","churned"]]
X_tr, X_te, y_tr, y_te = train_test_split(df[feats], df.churned, test_size=0.2,
    stratify=df.churned)
scale = (y_tr==0).sum()/(y_tr==1).sum()

model = xgb.XGBClassifier(n_estimators=500, max_depth=4, scale_pos_weight=scale,
    learning_rate=0.01, eval_metric="auc").fit(X_tr, y_tr, eval_set=[(X_te, y_te)],
    verbose=False, early_stopping_rounds=50)

print(f"AUC: {roc_auc_score(y_te, model.predict_proba(X_te)[:,1]):.4f}")
print(pd.DataFrame({"feature":feats,"importance":model.feature_importances_})
      .sort_values("importance",ascending=False).head(10))
```

### 7.5 API Design

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mlflow, pandas as pd, numpy as np

app = FastAPI(title="Prediction Service")

class Req(BaseModel):
    features: dict

class Res(BaseModel):
    prediction: float
    model_version: str

models = {}
@app.on_event("startup")
async def startup():
    models["churn"] = mlflow.pyfunc.load_model("models:/churn_model/latest")

@app.post("/predict/{name}")
async def predict(name: str, req: Req):
    if name not in models:
        raise HTTPException(404, "Model not found")
    df = pd.DataFrame([req.features])
    pred = float(models[name].predict(df)[0])
    return Res(prediction=pred, model_version="1.0")

# Run: uvicorn app:app --host 0.0.0.0 --port 8000
```

### 7.6 Streaming with Kafka

```python
from kafka import KafkaProducer, KafkaConsumer
import json

# Producer — stream transactions
producer = KafkaProducer(bootstrap_servers=["localhost:9092"],
    value_serializer=lambda v: json.dumps(v).encode())
producer.send("transactions", {"user_id":123,"amount":250,"merchant":"store"})

# Consumer — receive predictions
consumer = KafkaConsumer("predictions", bootstrap_servers=["localhost:9092"],
    value_deserializer=lambda v: json.loads(v.decode()))
for msg in consumer:
    if msg.value["fraud_score"] > 0.9:
        print(f"ALERT: Blocking {msg.value['transaction_id']}")
```

---

### 7.7 Multi-Step Forecasting Strategies

```python
# Recursive multi-step: predict one step, feed prediction back as input
def recursive_forecast(model, X_last, n_steps, feature_fn):
    preds = []
    X = X_last.copy()
    for _ in range(n_steps):
        pred = model.predict(X.reshape(1, -1))[0]
        preds.append(pred)
        X = feature_fn(X, pred)  # update lags/features with new prediction
    return preds

# Direct multi-step: train separate model for each forecast horizon
models = {}
for h in range(1, 25):
    y_h = df["value"].shift(-h)
    df_h = pd.concat([df[feats], y_h.rename("target")], axis=1).dropna()
    models[h] = lgb.LGBMRegressor().fit(df_h[feats], df_h["target"])
preds_24h = [models[h].predict(X_last.reshape(1, -1))[0] for h in range(1, 25)]

# Multi-output: single model predicts all horizons at once
from sklearn.multioutput import MultiOutputRegressor
Y = pd.DataFrame({f"h{h+1}": df["value"].shift(-(h+1)) for h in range(24)}).dropna()
X_multi = df[feats].iloc[:len(Y)]
mo = MultiOutputRegressor(RandomForestRegressor(n_estimators=200)).fit(X_multi, Y)
multi_preds = mo.predict(X_last.reshape(1, -1))[0]

# MIMO (Multiple Input Multiple Output): sequence-to-sequence with RNN/Transformer
# seq2seq model outputs entire forecast horizon in one forward pass
```

## Quick Reference

### Algorithm Selection

| Scenario | Algorithm |
|---|---|
| Small data, linear | Ridge / Linear Regression |
| Small data, non-linear | SVR, Gaussian Process |
| Medium, no seasonality | XGBoost, Random Forest |
| Medium, seasonal | Prophet, SARIMA |
| Large data | LightGBM, CatBoost |
| Very large + seasonal | Temporal Fusion Transformer, N-BEATS |

### Key Hyperparameters

| Model | Param | Range | Effect |
|---|---|---|---|
| XGBoost | `learning_rate` | 0.001-0.3 | Lower = better generalization |
| XGBoost | `max_depth` | 3-10 | Higher = more complex |
| XGBoost | `subsample` | 0.5-1.0 | Lower = more robust |
| LightGBM | `num_leaves` | 15-127 | Higher = more complex |
| LSTM | `hidden_size` | 32-512 | Higher = more capacity |
| LSTM | `dropout` | 0-0.5 | Higher = more regularization |
| Prophet | `changepoint_prior_scale` | 0.001-0.5 | Higher = more trend changes |
| ARIMA | `p` | 0-5 | Autoregressive order |
| ARIMA | `d` | 0-2 | Differencing order |
| ARIMA | `q` | 0-5 | Moving average order |
| Ridge | `alpha` | 0.01-100 | Higher = more shrinkage |

### Common Pitfalls

| Problem | Symptom | Fix |
|---|---|---|
| Leakage | Perfect train, poor test | Chronological split, fit scaler on train only |
| Non-stationarity | Spurious correlations | Differencing, detrend |
| Overfitting | Train << test error | Regularization, simpler model, more data |
| Underfitting | Both high error | More complex model, better features |
| Seasonality mismatch | Systematic periodic errors | Fourier features, seasonal model |
| Multi-step drift | Short-term ok, long-term bad | Direct multi-step, curriculum learning |

---

*Full code examples for stock prediction, demand forecasting, and churn prediction are included above. Adapt feature engineering and model selection to your specific domain and data.*
