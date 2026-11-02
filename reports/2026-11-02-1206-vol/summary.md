# Volatility forecast report

- **run_utc:** 2026-11-02 12:06
- **commit:** e9f32fa
- **placebo:** False
- **horizon_days:** 5
- **test_period:** 2015-01-02 -> 2026-10-23
- **samples:** 10661
- **best_by_qlike:** EWMA (current risk map)

## Forecast quality (out-of-sample)

| | R2 (log vol) | R2 (avg per year) | RMSE (log vol) | QLIKE | Correlation |
|---|---|---|---|---|---|
| EWMA (current risk map) | 0.2579 | 0.1378 | 0.6073 | 0.5234 | 0.5579 |
| EWMA recalibrated | 0.3043 | 0.1993 | 0.5880 | 0.6173 | 0.5517 |
| HAR | 0.2748 | 0.2342 | 0.6004 | 206.3448 | 0.5483 |
| Gradient boosting | 0.3597 | 0.2683 | 0.5641 | 0.5810 | 0.6009 |

## Vol-targeting strategy using each forecast (after costs)

| | CAGR | Volatility | Sharpe | Max drawdown | Yearly vol miss | Worst month |
|---|---|---|---|---|---|---|
| EWMA (current risk map) | 7.6% | 9.1% | 0.85 | -14.9% | 1.3% | -6.4% |
| EWMA recalibrated | 8.8% | 10.4% | 0.87 | -17.8% | 1.6% | -6.9% |
| HAR | 8.8% | 10.6% | 0.85 | -20.0% | 1.9% | -8.8% |
| Gradient boosting | 8.5% | 10.1% | 0.86 | -19.3% | 1.6% | -7.1% |

## R2 by year

| | EWMA (current risk map) | EWMA recalibrated | HAR | Gradient boosting |
|---|---|---|---|---|
| 2015 | -0.001 | 0.095 | 0.112 | 0.165 |
| 2016 | 0.077 | 0.179 | 0.379 | 0.383 |
| 2017 | -0.059 | 0.006 | 0.012 | -0.177 |
| 2018 | 0.397 | 0.420 | 0.474 | 0.451 |
| 2019 | 0.006 | 0.036 | -0.148 | 0.111 |
| 2020 | 0.417 | 0.482 | 0.381 | 0.402 |
| 2021 | 0.091 | 0.185 | 0.298 | 0.359 |
| 2022 | 0.317 | 0.208 | 0.239 | 0.345 |
| 2023 | 0.109 | 0.205 | 0.278 | 0.258 |
| 2024 | 0.128 | 0.201 | 0.233 | 0.228 |
| 2025 | 0.088 | 0.232 | 0.326 | 0.413 |
| 2026 | 0.084 | 0.142 | 0.226 | 0.282 |

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
