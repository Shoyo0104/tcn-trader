# Volatility forecast report

- **run_utc:** 2026-11-02 12:17
- **commit:** 1dfb39f
- **placebo:** False
- **horizon_days:** 5
- **test_period:** 2015-01-02 -> 2026-10-23
- **samples:** 10661
- **best_by_qlike:** EWMA (current risk map)

## Forecast quality (out-of-sample)

| | R2 (log vol) | R2 (avg per year) | RMSE (log vol) | QLIKE | Correlation |
|---|---|---|---|---|---|
| EWMA (current risk map) | 0.2579 | 0.1378 | 0.6073 | 0.5234 | 0.5579 |
| EWMA recalibrated | 0.3037 | 0.1988 | 0.5883 | 0.6131 | 0.5511 |
| HAR | 0.3762 | 0.2770 | 0.5568 | 0.5339 | 0.6155 |
| Gradient boosting | 0.3595 | 0.2658 | 0.5642 | 0.5253 | 0.6007 |

## Vol-targeting strategy using each forecast (after costs)

| | CAGR | Volatility | Sharpe | Max drawdown | Yearly vol miss | Worst month |
|---|---|---|---|---|---|---|
| EWMA (current risk map) | 7.6% | 9.1% | 0.85 | -14.9% | 1.3% | -6.4% |
| EWMA recalibrated | 6.2% | 8.1% | 0.78 | -14.3% | 2.9% | -5.6% |
| HAR | 6.3% | 8.1% | 0.79 | -16.9% | 2.7% | -6.5% |
| Gradient boosting | 6.0% | 7.9% | 0.78 | -15.9% | 2.8% | -6.0% |

## R2 by year

| | EWMA (current risk map) | EWMA recalibrated | HAR | Gradient boosting |
|---|---|---|---|---|
| 2015 | -0.001 | 0.095 | 0.112 | 0.170 |
| 2016 | 0.077 | 0.179 | 0.379 | 0.386 |
| 2017 | -0.059 | 0.006 | 0.013 | -0.190 |
| 2018 | 0.397 | 0.420 | 0.474 | 0.453 |
| 2019 | 0.006 | 0.036 | 0.149 | 0.115 |
| 2020 | 0.417 | 0.476 | 0.454 | 0.403 |
| 2021 | 0.091 | 0.185 | 0.343 | 0.352 |
| 2022 | 0.317 | 0.208 | 0.330 | 0.338 |
| 2023 | 0.109 | 0.205 | 0.265 | 0.246 |
| 2024 | 0.128 | 0.201 | 0.217 | 0.232 |
| 2025 | 0.088 | 0.232 | 0.379 | 0.414 |
| 2026 | 0.084 | 0.142 | 0.208 | 0.274 |

## Config

```json
{
  "tickers": [
    "SPY",
    "QQQ",
    "XIU.TO",
    "XEQT.TO"
  ],
  "start": "2005-01-01",
  "data_dir": "data",
  "results_dir": "results",
  "window": 64,
  "test_start_year": 2015,
  "retrain_freq": "M",
  "train_years": 10,
  "min_train_years": 5,
  "val_frac": 0.2,
  "embargo_days": 1,
  "channels": 32,
  "levels": 5,
  "kernel_size": 3,
  "dropout": 0.2,
  "epochs": 40,
  "patience": 6,
  "batch_size": 256,
  "lr": 0.001,
  "weight_decay": 0.0001,
  "seed": 42,
  "target_vol": 0.1,
  "vol_span": 20,
  "signal_sd": 2.0,
  "min_signal_scale": 0.02,
  "tau": 0.25,
  "w_min": 0.0,
  "w_max": 1.0,
  "cost_bps": 5.0
}
```
