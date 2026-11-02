"""Deadbanded volatility-scaled risk map.

w_{t+1} = clip( sigma* / sigma_hat_{t+1} * g_tau(2 p_hat - 1), w_min, w_max )
"""
import numpy as np


def deadband(s, tau):
    """g_tau: zero inside [-tau, tau], then rises linearly so it still reaches +/-1 at the ends."""
    s = np.asarray(s, dtype=float)
    return np.sign(s) * np.maximum(np.abs(s) - tau, 0.0) / (1.0 - tau)


def signal_scale(p_val, cfg):
    """Typical size of the raw signal 2p-1, measured on the VALIDATION set (never the test set).

    Why: honest, calibrated probabilities on market data sit very close to 0.5 (e.g. 0.47-0.53),
    so the raw signal 2p-1 lives in roughly [-0.06, 0.06]. Fed straight into the deadband, it would
    never trade. We rescale so 'signal_sd' standard deviations of the signal = full conviction (+/-1).
    """
    sd = np.std(2.0 * np.asarray(p_val) - 1.0)
    return max(cfg.signal_sd * sd, 1e-6)


def position(p_hat, sigma_hat, cfg, scale=1.0, tau=None):
    tau = cfg.tau if tau is None else tau
    signal = np.clip((2.0 * np.asarray(p_hat) - 1.0) / scale, -1, 1)   # probability -> signal in [-1, 1]
    lev = cfg.target_vol / np.maximum(np.asarray(sigma_hat), 1e-4)
    return np.clip(lev * deadband(signal, tau), cfg.w_min, cfg.w_max)


def vol_scaled_long(sigma_hat, cfg):
    """Baseline: always long, but sized by volatility. Tells you how much of a strategy's
    performance comes from the risk map alone, with no prediction at all."""
    return np.clip(cfg.target_vol / np.maximum(np.asarray(sigma_hat), 1e-4), cfg.w_min, cfg.w_max)
