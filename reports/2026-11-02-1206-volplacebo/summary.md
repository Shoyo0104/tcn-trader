# Volatility forecast report (PLACEBO - skill should vanish)

- **run_utc:** 2026-11-02 12:07
- **commit:** e9f32fa
- **placebo:** True
- **horizon_days:** 5
- **test_period:** 2015-01-02 -> 2026-10-23
- **samples:** 10661
- **best_by_qlike:** EWMA (current risk map)

## Forecast quality (out-of-sample)

| | R2 (log vol) | R2 (avg per year) | RMSE (log vol) | QLIKE | Correlation |
|---|---|---|---|---|---|
| EWMA (current risk map) | 0.2579 | 0.1378 | 0.6073 | 0.5234 | 0.5579 |
| EWMA recalibrated | -0.0645 | -0.3653 | 0.7274 | 1.5296 | -0.2011 |
| HAR | -0.0597 | -0.3623 | 0.7257 | 1.4731 | -0.1777 |
| Gradient boosting | -0.1007 | -0.4255 | 0.7396 | 1.6401 | -0.1310 |

## Vol-targeting strategy using each forecast (after costs)

| | CAGR | Volatility | Sharpe | Max drawdown | Yearly vol miss | Worst month |
|---|---|---|---|---|---|---|
| EWMA (current risk map) | 7.6% | 9.1% | 0.85 | -14.9% | 1.3% | -6.4% |
| EWMA recalibrated | 10.9% | 14.1% | 0.80 | -29.4% | 6.3% | -16.3% |
| HAR | 11.0% | 13.9% | 0.82 | -28.1% | 6.1% | -15.4% |
| Gradient boosting | 9.4% | 14.2% | 0.71 | -30.1% | 6.4% | -16.4% |

## R2 by year

| | EWMA (current risk map) | EWMA recalibrated | HAR | Gradient boosting |
|---|---|---|---|---|
| 2015 | -0.001 | -0.011 | -0.015 | -0.097 |
| 2016 | 0.077 | -0.261 | -0.240 | -0.303 |
| 2017 | -0.059 | -1.976 | -1.968 | -2.120 |
| 2018 | 0.397 | 0.004 | -0.013 | -0.043 |
| 2019 | 0.006 | -0.066 | -0.063 | -0.079 |
| 2020 | 0.417 | -0.385 | -0.339 | -0.409 |
| 2021 | 0.091 | -0.037 | -0.031 | -0.078 |
| 2022 | 0.317 | -1.605 | -1.627 | -1.729 |
| 2023 | 0.109 | -0.001 | -0.003 | 0.006 |
| 2024 | 0.128 | -0.018 | -0.014 | -0.090 |
| 2025 | 0.088 | 0.003 | -0.004 | -0.055 |
| 2026 | 0.084 | -0.032 | -0.031 | -0.109 |

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
