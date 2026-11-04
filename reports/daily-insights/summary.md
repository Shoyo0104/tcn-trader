# Market insights

- **run_utc:** 2026-11-04 01:41
- **commit:** 4193749
- **as_of:** 2026-11-02
- **market:** SPY
- **regime_test_period:** 2015-01-02 -> 2026-11-02

## Today

Market regime (SPY) as of 2026-11-02: **Normal** (confidence 56%, 8 trading days so far; stretches of this regime have lasted ~10 days on average).

Historically, 42% of Normal days were still Normal 21 trading days later.

**SPY**: volatility forecast for the next 5 days 15% (higher than 68% of the last 10 years). In past Normal periods (995 days in 63 separate episodes since 2015), the next 21 days averaged +0.9%, were up 66% of the time, and fell more than 5% 8% of the time; the worst 10% of 5-day moves were below -2.1%.

**QQQ**: volatility forecast for the next 5 days 24% (higher than 75% of the last 10 years). In past Normal periods (995 days in 63 separate episodes since 2015), the next 21 days averaged +1.1%, were up 64% of the time, and fell more than 5% 11% of the time; the worst 10% of 5-day moves were below -2.7%.

**XIU.TO**: volatility forecast for the next 5 days 14% (higher than 77% of the last 10 years). In past Normal periods (972 days in 63 separate episodes since 2015), the next 21 days averaged +1.0%, were up 66% of the time, and fell more than 5% 4% of the time; the worst 10% of 5-day moves were below -1.8%.

**XEQT.TO**: volatility forecast for the next 5 days 11% (higher than 53% of the last 10 years). In past Normal periods (601 days in 63 separate episodes since 2015), the next 21 days averaged +1.2%, were up 73% of the time, and fell more than 5% 3% of the time; the worst 10% of 5-day moves were below -1.4%.

How much evidence: overlapping 21-day windows are not independent, so the episode count, not the day count, is closer to the real sample size. Treat regime statistics built on few episodes as rough.

## What followed each regime (SPY, out-of-sample labels)

| | days | episodes | share | avg_run_days | fwd21_mean | fwd21_median | p_up_21d | p_drop5_21d | fwd21_vol | q10_5d | p_drop3_5d |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Calm | 983 | 54 | 33.0% | 12 | 0.4% | 1.0% | 64.8% | 5.0% | 11.5% | -1.5% | 2.6% |
| Normal | 995 | 63 | 33.4% | 10 | 0.9% | 1.4% | 66.0% | 7.5% | 13.5% | -2.1% | 5.5% |
| Elevated | 639 | 36 | 21.5% | 14 | 2.3% | 3.0% | 79.2% | 7.4% | 17.1% | -2.9% | 9.2% |
| Stressed | 359 | 9 | 12.1% | 36 | 2.3% | 3.3% | 66.3% | 14.2% | 22.9% | -3.3% | 12.5% |

## Regime profiles (latest fit)

| | typical_vol | typical_3m_return | typical_drawdown |
|---|---|---|---|
| Calm | 9.3% | +6.6% | -0.4% |
| Normal | 14.2% | +2.9% | -3.7% |
| Elevated | 15.2% | +5.3% | -5.4% |
| Stressed | 25.4% | -4.3% | -14.7% |

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
