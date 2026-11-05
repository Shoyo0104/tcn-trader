# Market insights

- **run_utc:** 2026-11-05 01:49
- **commit:** 1c5878f
- **as_of:** 2026-11-03
- **market:** SPY
- **regime_test_period:** 2015-01-02 -> 2026-11-03

## Today

Market regime (SPY) as of 2026-11-03: **Normal** (confidence 64%, 1 trading days so far; stretches of this regime have lasted ~10 days on average).

Historically, 43% of Normal days were still Normal 21 trading days later.

**SPY**: volatility forecast for the next 5 days 12% (higher than 56% of the last 10 years). In past Normal periods (999 days in 65 separate episodes since 2015), the next 21 days averaged +0.8%, were up 66% of the time, and fell more than 5% 8% of the time; the worst 10% of 5-day moves were below -2.1%.

**QQQ**: volatility forecast for the next 5 days 18% (higher than 59% of the last 10 years). In past Normal periods (999 days in 65 separate episodes since 2015), the next 21 days averaged +1.1%, were up 64% of the time, and fell more than 5% 11% of the time; the worst 10% of 5-day moves were below -2.7%.

**XIU.TO**: volatility forecast for the next 5 days 16% (higher than 86% of the last 10 years). In past Normal periods (978 days in 65 separate episodes since 2015), the next 21 days averaged +1.0%, were up 67% of the time, and fell more than 5% 4% of the time; the worst 10% of 5-day moves were below -1.8%.

**XEQT.TO**: volatility forecast for the next 5 days 12% (higher than 64% of the last 10 years). In past Normal periods (607 days in 65 separate episodes since 2015), the next 21 days averaged +1.2%, were up 73% of the time, and fell more than 5% 3% of the time; the worst 10% of 5-day moves were below -1.4%.

How much evidence: overlapping 21-day windows are not independent, so the episode count, not the day count, is closer to the real sample size. Treat regime statistics built on few episodes as rough.

## What followed each regime (SPY, out-of-sample labels)

| | days | episodes | share | avg_run_days | fwd21_mean | fwd21_median | p_up_21d | p_drop5_21d | fwd21_vol | q10_5d | p_drop3_5d |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Calm | 957 | 54 | 32.1% | 11 | 0.4% | 1.0% | 64.5% | 4.9% | 11.2% | -1.5% | 2.4% |
| Normal | 999 | 65 | 33.6% | 10 | 0.8% | 1.5% | 66.2% | 7.5% | 13.5% | -2.1% | 5.5% |
| Elevated | 648 | 35 | 21.8% | 13 | 2.4% | 3.0% | 79.8% | 6.8% | 16.3% | -2.7% | 7.9% |
| Stressed | 373 | 9 | 12.5% | 37 | 2.0% | 2.9% | 64.6% | 15.0% | 24.2% | -3.8% | 14.7% |

## Regime profiles (latest fit)

| | typical_vol | typical_3m_return | typical_drawdown |
|---|---|---|---|
| Calm | 9.4% | +6.3% | -0.4% |
| Normal | 13.1% | +4.2% | -3.4% |
| Elevated | 22.6% | -1.1% | -12.8% |
| Stressed | 31.9% | -7.2% | -11.8% |

## Chance of being in each regime 21 trading days later

| | Calm | Normal | Elevated | Stressed |
|---|---|---|---|---|
| Calm | 57% | 34% | 8% | 1% |
| Normal | 31% | 43% | 24% | 2% |
| Elevated | 16% | 35% | 38% | 11% |
| Stressed | 3% | 1% | 24% | 72% |

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
