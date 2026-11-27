# Market insights

- **run_utc:** 2026-11-27 03:48
- **commit:** 7a801de
- **as_of:** 2026-11-25
- **market:** SPY
- **regime_test_period:** 2015-01-02 -> 2026-11-25

## Today

Market regime (SPY) as of 2026-11-25: **Elevated** (confidence 98%, 12 trading days so far; stretches of this regime have lasted ~13 days on average).

Historically, 38% of Elevated days were still Elevated 21 trading days later.

**SPY**: volatility forecast for the next 5 days 35% (higher than 96% of the last 10 years). In past Elevated periods (659 days in 36 separate episodes since 2015), the next 21 days averaged +2.4%, were up 80% of the time, and fell more than 5% 7% of the time; the worst 10% of 5-day moves were below -2.8%.

**QQQ**: volatility forecast for the next 5 days 47% (higher than 97% of the last 10 years). In past Elevated periods (659 days in 36 separate episodes since 2015), the next 21 days averaged +3.2%, were up 78% of the time, and fell more than 5% 10% of the time; the worst 10% of 5-day moves were below -3.5%.

**XIU.TO**: volatility forecast for the next 5 days 19% (higher than 91% of the last 10 years). In past Elevated periods (647 days in 36 separate episodes since 2015), the next 21 days averaged +1.9%, were up 73% of the time, and fell more than 5% 4% of the time; the worst 10% of 5-day moves were below -2.1%.

**XEQT.TO**: volatility forecast for the next 5 days 24% (higher than 94% of the last 10 years). In past Elevated periods (434 days in 36 separate episodes since 2015), the next 21 days averaged +1.6%, were up 73% of the time, and fell more than 5% 7% of the time; the worst 10% of 5-day moves were below -2.2%.

How much evidence: overlapping 21-day windows are not independent, so the episode count, not the day count, is closer to the real sample size. Treat regime statistics built on few episodes as rough.

## What followed each regime (SPY, out-of-sample labels)

| | days | episodes | share | avg_run_days | fwd21_mean | fwd21_median | p_up_21d | p_drop5_21d | fwd21_vol | q10_5d | p_drop3_5d |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Calm | 957 | 54 | 32.0% | 11 | 0.4% | 1.0% | 64.1% | 5.0% | 11.3% | -1.5% | 2.4% |
| Normal | 1004 | 65 | 33.5% | 10 | 0.7% | 1.5% | 65.6% | 7.9% | 13.6% | -2.1% | 5.7% |
| Elevated | 659 | 36 | 22.0% | 13 | 2.4% | 3.0% | 79.8% | 6.8% | 16.3% | -2.8% | 8.1% |
| Stressed | 373 | 9 | 12.5% | 37 | 2.0% | 2.9% | 64.6% | 15.0% | 24.2% | -3.8% | 14.7% |

## Regime profiles (latest fit)

| | typical_vol | typical_3m_return | typical_drawdown |
|---|---|---|---|
| Calm | 9.4% | +6.4% | -0.4% |
| Normal | 11.9% | +4.7% | -2.9% |
| Elevated | 20.8% | +0.9% | -8.2% |
| Stressed | 29.8% | -6.5% | -16.1% |

## Chance of being in each regime 21 trading days later

| | Calm | Normal | Elevated | Stressed |
|---|---|---|---|---|
| Calm | 56% | 34% | 8% | 1% |
| Normal | 30% | 43% | 25% | 2% |
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
