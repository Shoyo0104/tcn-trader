"""TCN -> global average pool -> sigmoid head, plus Platt calibration and a logistic baseline.

p_hat = sigmoid(w^T TCN(X) + b),  X in R^{64 x 12}
"""
import copy

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.linear_model import LogisticRegression


def get_device():
    if torch.cuda.is_available():
        return torch.device("cuda")
    if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
        return torch.device("mps")          # Apple Silicon Macs
    return torch.device("cpu")


class CausalConv1d(nn.Module):
    """1D convolution that only looks backward in time (pads on the left only)."""

    def __init__(self, c_in, c_out, k, dilation):
        super().__init__()
        self.pad = (k - 1) * dilation
        self.conv = nn.utils.parametrizations.weight_norm(nn.Conv1d(c_in, c_out, k, dilation=dilation))

    def forward(self, x):
        return self.conv(F.pad(x, (self.pad, 0)))


class TemporalBlock(nn.Module):
    def __init__(self, c_in, c_out, k, dilation, dropout):
        super().__init__()
        self.net = nn.Sequential(
            CausalConv1d(c_in, c_out, k, dilation), nn.ReLU(), nn.Dropout(dropout),
            CausalConv1d(c_out, c_out, k, dilation), nn.ReLU(), nn.Dropout(dropout),
        )
        self.skip = nn.Conv1d(c_in, c_out, 1) if c_in != c_out else nn.Identity()

    def forward(self, x):
        return F.relu(self.net(x) + self.skip(x))


class TCNClassifier(nn.Module):
    def __init__(self, n_features, channels=32, levels=5, k=3, dropout=0.2):
        super().__init__()
        blocks, c_in = [], n_features
        for i in range(levels):
            blocks.append(TemporalBlock(c_in, channels, k, 2 ** i, dropout))
            c_in = channels
        self.tcn = nn.Sequential(*blocks)
        self.head = nn.Linear(channels, 1)            # w^T(.) + b

    def forward(self, x):                             # x: (batch, time, features)
        h = self.tcn(x.transpose(1, 2))               # -> (batch, channels, time)
        h = h.mean(dim=2)                             # global average pool over time
        return self.head(h).squeeze(-1)               # logit; sigmoid applied outside


def train_tcn(Xtr, ytr, Xva, yva, cfg, verbose=False):
    torch.manual_seed(cfg.seed)
    dev = get_device()
    model = TCNClassifier(Xtr.shape[-1], cfg.channels, cfg.levels, cfg.kernel_size, cfg.dropout).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)
    loss_fn = nn.BCEWithLogitsLoss()

    Xtr_t, ytr_t = torch.from_numpy(Xtr), torch.from_numpy(ytr)
    Xva_t, yva_t = torch.from_numpy(Xva).to(dev), torch.from_numpy(yva).to(dev)
    g = torch.Generator().manual_seed(cfg.seed)

    best, best_state, bad = np.inf, None, 0
    for ep in range(cfg.epochs):
        model.train()
        perm = torch.randperm(len(Xtr_t), generator=g)
        for i in range(0, len(perm), cfg.batch_size):
            b = perm[i:i + cfg.batch_size]
            xb, yb = Xtr_t[b].to(dev), ytr_t[b].to(dev)
            opt.zero_grad()
            loss_fn(model(xb), yb).backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            vl = loss_fn(model(Xva_t), yva_t).item()
        if verbose:
            print(f"    epoch {ep + 1:02d}  val_loss {vl:.5f}")
        if vl < best - 1e-5:
            best, best_state, bad = vl, copy.deepcopy(model.state_dict()), 0
        else:
            bad += 1
            if bad >= cfg.patience:
                break
    model.load_state_dict(best_state)
    return model


@torch.no_grad()
def predict_logits(model, X, batch=2048):
    dev = next(model.parameters()).device
    model.eval()
    out = [model(torch.from_numpy(X[i:i + batch]).to(dev)).cpu().numpy() for i in range(0, len(X), batch)]
    return np.concatenate(out)


class PlattCalibrator:
    """Maps raw logits to honest probabilities, fit on the validation set.

    After this, p = 0.6 should mean "up about 60% of the time" (check the calibration plot).
    """

    def fit(self, logits, y):
        self.lr = LogisticRegression(C=1e6).fit(logits.reshape(-1, 1), y)
        return self

    def predict(self, logits):
        return self.lr.predict_proba(logits.reshape(-1, 1))[:, 1]


def baseline_features(X):
    """Logistic baseline sees the latest day's 12 features + the 64-day average of each (24 inputs)."""
    return np.concatenate([X[:, -1, :], X.mean(axis=1)], axis=1)


def train_logistic(Xtr, ytr):
    return LogisticRegression(C=0.1, max_iter=2000).fit(baseline_features(Xtr), ytr)
