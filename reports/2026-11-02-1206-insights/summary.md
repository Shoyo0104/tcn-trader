# Market insights

- **run_utc:** 2026-11-02 12:07
- **commit:** e9f32fa
- **as_of:** 2026-10-30
- **market:** SPY
- **regime_test_period:** 2015-01-02 -> 2026-10-30

## Today

Market regime (SPY) as of 2026-10-30: **Calm** (confidence 55%, 2 trading days so far; stretches of this regime have lasted ~12 days on average).

Historically, 57% of Calm days were still Calm 21 trading days later.

**SPY**: volatility forecast for the next 5 days 10% (higher than 44% of the last 10 years). In past Calm periods (983 days since 2015), the next 21 days averaged +0.4%, were up 65% of the time, and fell more than 5% 5% of the time; the worst 10% of 5-day moves were below -1.5%.

**XIU.TO**: volatility forecast for the next 5 days 12% (higher than 69% of the last 10 years). In past Calm periods (961 days since 2015), the next 21 days averaged +0.1%, were up 59% of the time, and fell more than 5% 3% of the time; the worst 10% of 5-day moves were below -1.5%.

**QQQ**: volatility forecast for the next 5 days 15% (higher than 45% of the last 10 years). In past Calm periods (983 days since 2015), the next 21 days averaged +0.7%, were up 65% of the time, and fell more than 5% 9% of the time; the worst 10% of 5-day moves were below -2.6%.

**XEQT.TO**: volatility forecast for the next 5 days 10% (higher than 50% of the last 10 years). In past Calm periods (407 days since 2015), the next 21 days averaged +0.5%, were up 66% of the time, and fell more than 5% 3% of the time; the worst 10% of 5-day moves were below -1.3%.

## What followed each regime (SPY, out-of-sample labels)

| | days | share | avg_run_days | fwd21_mean | fwd21_median | p_up_21d | p_drop5_21d | fwd21_vol | q10_5d | p_drop3_5d |
|---|---|---|---|---|---|---|---|---|---|---|
| Calm | 983 | 33.0% | 12 | 0.4% | 1.0% | 64.8% | 5.0% | 11.5% | -1.5% | 2.6% |
| Normal | 994 | 33.4% | 10 | 0.9% | 1.4% | 66.0% | 7.6% | 13.5% | -2.1% | 5.5% |
| Elevated | 639 | 21.5% | 14 | 2.3% | 3.0% | 79.2% | 7.4% | 17.1% | -2.9% | 9.2% |
| Stressed | 359 | 12.1% | 36 | 2.3% | 3.3% | 66.3% | 14.2% | 22.9% | -3.3% | 12.5% |

## Regime profiles (latest fit)

| | typical_vol | typical_3m_return | typical_drawdown |
|---|---|---|---|
| Calm | 9.4% | +6.4% | -0.4% |
| Normal | 13.0% | +4.2% | -3.4% |
| Elevated | 22.6% | -1.1% | -12.8% |
| Stressed | 31.7% | -7.1% | -11.8% |

## Chance of being in each regime 21 trading days later

| | Calm | Normal | Elevated | Stressed |
|---|---|---|---|---|
| Calm | 57% | 34% | 8% | 2% |
| Normal | 32% | 42% | 25% | 1% |
| Elevated | 17% | 35% | 36% | 12% |
| Stressed | 4% | 2% | 24% | 71% |

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
