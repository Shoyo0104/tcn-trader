# Backtest report

- **run_utc:** 2026-11-02 11:40
- **commit:** 76dac35
- **placebo:** False
- **device:** cpu
- **test_period:** 2015-01-02 -> 2026-10-29
- **samples:** 17827

## Strategy performance (out-of-sample, after costs)

| | CAGR | Volatility | Sharpe | Max drawdown | Avg exposure | Turnover/yr |
|---|---|---|---|---|---|---|
| Buy & hold | 12.7% | 16.1% | 0.83 | -31.6% | 1.00 | 0.1 |
| Vol-scaled long | 7.5% | 9.1% | 0.84 | -14.9% | 0.76 | 5.8 |
| Logistic + risk map | 2.8% | 7.2% | 0.42 | -12.1% | 0.53 | 33.0 |
| TCN + risk map | 4.6% | 8.3% | 0.58 | -14.7% | 0.63 | 6.5 |

## Prediction quality

| | AUC | Accuracy | Brier | Log loss |
|---|---|---|---|---|
| Always 'up' (base rate) | 0.5000 | 0.5480 | 0.2477 | 0.6885 |
| Logistic | 0.4818 | 0.5393 | 0.2496 | 0.6925 |
| TCN (calibrated) | 0.4833 | 0.5406 | 0.2495 | 0.6922 |

## Sharpe by year

| | Buy & hold | Vol-scaled long | Logistic + risk map | TCN + risk map |
|---|---|---|---|---|
| 2015 | -0.04 | -0.58 | -0.58 | -0.58 |
| 2016 | 1.13 | 0.93 | 0.66 | 0.93 |
| 2017 | 2.80 | 2.72 | 2.45 | 1.79 |
| 2018 | -0.38 | -0.56 | -0.54 | -0.53 |
| 2019 | 2.42 | 2.08 | 0.87 | 1.93 |
| 2020 | 0.72 | 0.77 | 0.57 | 0.49 |
| 2021 | 2.10 | 1.88 | 1.32 | 1.88 |
| 2022 | -0.96 | -1.18 | -0.89 | -1.17 |
| 2023 | 1.81 | 1.44 | 0.58 | 1.09 |
| 2024 | 1.87 | 1.83 | 0.68 | 1.56 |
| 2025 | 1.18 | 1.24 | 0.87 | 1.23 |
| 2026 | 1.10 | 0.61 | 0.17 | 0.61 |

## Significance

TCN vs vol-scaled long: mean Sharpe gap -0.25; share of bootstrap draws where TCN is NOT better: 100% -> **indistinguishable from luck**.

![equity](equity.png)

![calibration](calibration.png)

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
  "retrain_freq": "Y",
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
