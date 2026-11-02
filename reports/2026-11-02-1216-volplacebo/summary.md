# Volatility forecast report (PLACEBO - skill should vanish)

- **run_utc:** 2026-11-02 12:16
- **commit:** 1dfb39f
- **placebo:** True
- **horizon_days:** 5
- **test_period:** 2015-01-02 -> 2026-10-23
- **samples:** 10661
- **best_by_qlike:** EWMA (current risk map)

## Forecast quality (out-of-sample)

| | R2 (log vol) | R2 (avg per year) | RMSE (log vol) | QLIKE | Correlation |
|---|---|---|---|---|---|
| EWMA (current risk map) | 0.2579 | 0.1378 | 0.6073 | 0.5234 | 0.5579 |
| EWMA recalibrated | -0.0645 | -0.3653 | 0.7274 | 0.8737 | -0.2011 |
| HAR | -0.0608 | -0.3616 | 0.7261 | 0.8676 | -0.1849 |
| Gradient boosting | -0.1032 | -0.4276 | 0.7405 | 0.9188 | -0.1363 |

## Vol-targeting strategy using each forecast (after costs)

| | CAGR | Volatility | Sharpe | Max drawdown | Yearly vol miss | Worst month |
|---|---|---|---|---|---|---|
| EWMA (current risk map) | 7.6% | 9.1% | 0.85 | -14.9% | 1.3% | -6.4% |
| EWMA recalibrated | 6.7% | 8.0% | 0.85 | -16.2% | 3.7% | -8.3% |
| HAR | 6.7% | 7.9% | 0.85 | -16.1% | 3.7% | -8.3% |
| Gradient boosting | 5.7% | 8.0% | 0.74 | -16.5% | 3.7% | -8.4% |

## R2 by year

| | EWMA (current risk map) | EWMA recalibrated | HAR | Gradient boosting |
|---|---|---|---|---|
| 2015 | -0.001 | -0.011 | -0.015 | -0.088 |
| 2016 | 0.077 | -0.261 | -0.240 | -0.308 |
| 2017 | -0.059 | -1.976 | -1.968 | -2.143 |
| 2018 | 0.397 | 0.004 | -0.013 | -0.045 |
| 2019 | 0.006 | -0.066 | -0.065 | -0.084 |
| 2020 | 0.417 | -0.385 | -0.356 | -0.413 |
| 2021 | 0.091 | -0.037 | -0.021 | -0.088 |
| 2022 | 0.317 | -1.605 | -1.621 | -1.724 |
| 2023 | 0.109 | -0.001 | 0.004 | 0.000 |
| 2024 | 0.128 | -0.018 | -0.012 | -0.091 |
| 2025 | 0.088 | 0.003 | 0.001 | -0.047 |
| 2026 | 0.084 | -0.032 | -0.032 | -0.101 |

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
