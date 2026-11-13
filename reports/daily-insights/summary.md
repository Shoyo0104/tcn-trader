# Market insights

- **run_utc:** 2026-11-13 02:09
- **commit:** 5f02436
- **as_of:** 2026-11-11
- **market:** SPY
- **regime_test_period:** 2015-01-02 -> 2026-11-11

## Today

Market regime (SPY) as of 2026-11-11: **Elevated** (confidence 80%, 3 trading days so far; stretches of this regime have lasted ~13 days on average).

Historically, 38% of Elevated days were still Elevated 21 trading days later.

**SPY**: volatility forecast for the next 5 days 22% (higher than 85% of the last 10 years). In past Elevated periods (651 days in 35 separate episodes since 2015), the next 21 days averaged +2.4%, were up 80% of the time, and fell more than 5% 7% of the time; the worst 10% of 5-day moves were below -2.7%.

**QQQ**: volatility forecast for the next 5 days 31% (higher than 87% of the last 10 years). In past Elevated periods (651 days in 35 separate episodes since 2015), the next 21 days averaged +3.2%, were up 78% of the time, and fell more than 5% 10% of the time; the worst 10% of 5-day moves were below -3.4%.

**XIU.TO**: volatility forecast for the next 5 days 15% (higher than 81% of the last 10 years). In past Elevated periods (639 days in 35 separate episodes since 2015), the next 21 days averaged +1.9%, were up 73% of the time, and fell more than 5% 4% of the time; the worst 10% of 5-day moves were below -2.0%.

**XEQT.TO**: volatility forecast for the next 5 days 15% (higher than 76% of the last 10 years). In past Elevated periods (426 days in 35 separate episodes since 2015), the next 21 days averaged +1.6%, were up 73% of the time, and fell more than 5% 7% of the time; the worst 10% of 5-day moves were below -2.1%.

How much evidence: overlapping 21-day windows are not independent, so the episode count, not the day count, is closer to the real sample size. Treat regime statistics built on few episodes as rough.

## What followed each regime (SPY, out-of-sample labels)

| | days | episodes | share | avg_run_days | fwd21_mean | fwd21_median | p_up_21d | p_drop5_21d | fwd21_vol | q10_5d | p_drop3_5d |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Calm | 948 | 55 | 31.8% | 11 | 0.4% | 0.9% | 63.8% | 5.1% | 11.3% | -1.5% | 2.4% |
| Normal | 1011 | 66 | 33.9% | 10 | 0.8% | 1.5% | 66.4% | 7.4% | 13.5% | -2.1% | 5.6% |
| Elevated | 651 | 35 | 21.8% | 13 | 2.4% | 3.0% | 79.8% | 6.8% | 16.3% | -2.7% | 7.9% |
| Stressed | 373 | 9 | 12.5% | 37 | 2.0% | 2.9% | 64.6% | 15.0% | 24.2% | -3.8% | 14.7% |

## Regime profiles (latest fit)

| | typical_vol | typical_3m_return | typical_drawdown |
|---|---|---|---|
| Calm | 9.4% | +6.4% | -0.4% |
| Normal | 11.8% | +4.9% | -2.9% |
| Elevated | 20.4% | +1.2% | -7.8% |
| Stressed | 29.3% | -6.3% | -16.0% |

## Chance of being in each regime 21 trading days later

| | Calm | Normal | Elevated | Stressed |
|---|---|---|---|---|
| Calm | 55% | 35% | 8% | 1% |
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
