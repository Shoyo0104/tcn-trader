# Market insights

- **run_utc:** 2026-11-14 01:49
- **commit:** ea03a72
- **as_of:** 2026-11-13
- **market:** SPY
- **regime_test_period:** 2015-01-02 -> 2026-11-13

## Today

Market regime (SPY) as of 2026-11-13: **Elevated** (confidence 90%, 5 trading days so far; stretches of this regime have lasted ~13 days on average).

Historically, 36% of Elevated days were still Elevated 21 trading days later.

**SPY**: volatility forecast for the next 5 days 20% (higher than 82% of the last 10 years). In past Elevated periods (643 days in 36 separate episodes since 2015), the next 21 days averaged +2.3%, were up 79% of the time, and fell more than 5% 7% of the time; the worst 10% of 5-day moves were below -2.9%.

**XIU.TO**: volatility forecast for the next 5 days 13% (higher than 76% of the last 10 years). In past Elevated periods (633 days in 36 separate episodes since 2015), the next 21 days averaged +1.8%, were up 74% of the time, and fell more than 5% 4% of the time; the worst 10% of 5-day moves were below -2.2%.

**QQQ**: volatility forecast for the next 5 days 30% (higher than 86% of the last 10 years). In past Elevated periods (643 days in 36 separate episodes since 2015), the next 21 days averaged +3.1%, were up 77% of the time, and fell more than 5% 10% of the time; the worst 10% of 5-day moves were below -3.6%.

**XEQT.TO**: volatility forecast for the next 5 days 15% (higher than 78% of the last 10 years). In past Elevated periods (420 days in 36 separate episodes since 2015), the next 21 days averaged +1.4%, were up 73% of the time, and fell more than 5% 7% of the time; the worst 10% of 5-day moves were below -2.3%.

How much evidence: overlapping 21-day windows are not independent, so the episode count, not the day count, is closer to the real sample size. Treat regime statistics built on few episodes as rough.

## What followed each regime (SPY, out-of-sample labels)

| | days | episodes | share | avg_run_days | fwd21_mean | fwd21_median | p_up_21d | p_drop5_21d | fwd21_vol | q10_5d | p_drop3_5d |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Calm | 983 | 54 | 32.9% | 12 | 0.4% | 1.0% | 64.3% | 5.1% | 11.5% | -1.5% | 2.6% |
| Normal | 1000 | 63 | 33.5% | 10 | 0.9% | 1.4% | 65.8% | 7.5% | 13.5% | -2.1% | 5.5% |
| Elevated | 643 | 36 | 21.5% | 13 | 2.3% | 3.0% | 79.2% | 7.4% | 17.1% | -2.9% | 9.2% |
| Stressed | 359 | 9 | 12.0% | 36 | 2.3% | 3.3% | 66.3% | 14.2% | 22.9% | -3.3% | 12.5% |

## Regime profiles (latest fit)

| | typical_vol | typical_3m_return | typical_drawdown |
|---|---|---|---|
| Calm | 9.4% | +6.4% | -0.4% |
| Normal | 11.8% | +4.9% | -2.9% |
| Elevated | 20.4% | +1.2% | -7.7% |
| Stressed | 29.2% | -6.3% | -16.0% |

## Chance of being in each regime 21 trading days later

| | Calm | Normal | Elevated | Stressed |
|---|---|---|---|---|
| Calm | 56% | 34% | 9% | 2% |
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
