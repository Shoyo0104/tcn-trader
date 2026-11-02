"""All the knobs in one place. Change things here, not inside the code."""
from dataclasses import dataclass, field


@dataclass
class Config:
    # ---- Data ----
    tickers: list = field(default_factory=lambda: ["SPY", "QQQ", "XIU.TO"])
    start: str = "2005-01-01"          # first day of history to download (10y window + test period)
    data_dir: str = "data"             # cached CSVs go here
    results_dir: str = "results"

    # ---- Problem setup ----
    window: int = 64                   # timesteps per sample (the 64 in 64x12)
    # Label: did the NEXT day's close-to-close return come out positive?

    # ---- Walk-forward (mirrors the live system) ----
    test_start_year: int = 2015        # first out-of-sample year
    retrain_freq: str = "M"            # "M" = retrain monthly (live plan), "Y" = yearly (faster)
    train_years: int = 10              # rolling training window: most recent 10 years
    min_train_years: int = 5           # don't test until at least 5 years of history exist
    val_frac: float = 0.2              # last 20% of each training set = validation
    embargo_days: int = 1              # gap between train and test so labels can't leak

    # ---- TCN ----
    channels: int = 32
    levels: int = 5                    # dilations 1,2,4,8,16 -> receptive field > 64
    kernel_size: int = 3
    dropout: float = 0.2

    # ---- Training ----
    epochs: int = 40
    patience: int = 6                  # early stopping on validation loss
    batch_size: int = 256
    lr: float = 1e-3
    weight_decay: float = 1e-4
    seed: int = 42

    # ---- Risk map: w = clip(target_vol / sigma_hat * g_tau(2p - 1), w_min, w_max) ----
    target_vol: float = 0.10           # sigma*, annualized (10%)
    vol_span: int = 20                 # EWMA span for the volatility forecast sigma_hat
    signal_sd: float = 2.0             # raw signal is divided by (signal_sd x its validation std),
                                       # so a 2-standard-deviation signal = full conviction
    tau: float = 0.25                  # deadband on the rescaled signal: |s| below this -> no position
    w_min: float = 0.0                 # 0 = long-or-flat (no shorting). Use -1.0 to allow shorts.
    w_max: float = 1.0                 # 1.0 = no leverage

    # ---- Costs ----
    cost_bps: float = 5.0              # cost per 100% of position traded, in basis points
                                       # (spread + slippage + fees; raise it to be pessimistic)
