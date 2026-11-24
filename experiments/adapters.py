"""Maps between embedding spaces, fitted on paired anchor vectors.

Every adapter is fitted on (X, Y): the same anchor texts embedded in the
source space (X, n x ds) and the target space (Y, n x dt), and returns a
function that takes source vectors to the target space. Outputs are
L2-normalised because every space here is searched by cosine similarity.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
import torch

from common import SEED, normalize

Adapter = Callable[[np.ndarray], np.ndarray]


def procrustes(X: np.ndarray, Y: np.ndarray) -> Adapter:
    """Orthogonal Procrustes after centring; semi-orthogonal if ds != dt."""
    mx, my = X.mean(0), Y.mean(0)
    U, _, Vt = np.linalg.svd((X - mx).T @ (Y - my), full_matrices=False)
    W = U @ Vt
    return lambda Z: normalize((Z - mx) @ W + my)


def procrustes_uncentred(X: np.ndarray, Y: np.ndarray) -> Adapter:
    """The orthogonal map without centring: a pure rotation (and projection if ds != dt)."""
    U, _, Vt = np.linalg.svd(X.T @ Y, full_matrices=False)
    W = U @ Vt
    return lambda Z: normalize(Z @ W)


def ridge(X: np.ndarray, Y: np.ndarray, lambdas=(1e-3, 1e-2, 1e-1, 1.0, 10.0)) -> Adapter:
    """Affine least squares; the penalty is chosen on a held-out tenth of the anchors."""
    n = len(X)
    rng = np.random.default_rng(SEED)
    idx = rng.permutation(n)
    val, tr = idx[: max(n // 10, 10)], idx[max(n // 10, 10) :]

    def solve(Xa, Ya, lam):
        mx, my = Xa.mean(0), Ya.mean(0)
        Xc, Yc = (Xa - mx).astype(np.float64), (Ya - my).astype(np.float64)
        if Xc.shape[0] >= Xc.shape[1]:
            W = np.linalg.solve(Xc.T @ Xc + lam * len(Xc) * np.eye(Xc.shape[1]), Xc.T @ Yc)
        else:  # dual form when there are fewer anchors than dimensions
            W = Xc.T @ np.linalg.solve(Xc @ Xc.T + lam * len(Xc) * np.eye(Xc.shape[0]), Yc)
        return mx, my, W.astype(np.float32)

    best, best_cos = lambdas[0], -1.0
    for lam in lambdas:
        mx, my, W = solve(X[tr], Y[tr], lam)
        cos = float((normalize((X[val] - mx) @ W + my) * normalize(Y[val])).sum(1).mean())
        if cos > best_cos:
            best, best_cos = lam, cos
    mx, my, W = solve(X, Y, best)
    return lambda Z: normalize((Z - mx) @ W + my)


def mlp(X: np.ndarray, Y: np.ndarray, hidden: int = 2048, epochs: int = 60) -> Adapter:
    """Residual MLP on top of the ridge solution (cosine loss, early stopping)."""
    base = ridge(X, Y)
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    torch.manual_seed(SEED)
    n = len(X)
    idx = np.random.default_rng(SEED).permutation(n)
    val, tr = idx[: max(n // 10, 10)], idx[max(n // 10, 10) :]
    Xb = torch.tensor(base(X), device=dev)
    Yt = torch.tensor(normalize(Y), device=dev)
    dt = Y.shape[1]
    net = torch.nn.Sequential(
        torch.nn.Linear(dt, hidden), torch.nn.GELU(), torch.nn.Dropout(0.1), torch.nn.Linear(hidden, dt)
    ).to(dev)
    torch.nn.init.zeros_(net[-1].weight)
    torch.nn.init.zeros_(net[-1].bias)
    opt = torch.optim.AdamW(net.parameters(), lr=3e-4, weight_decay=1e-2)

    def forward(x):
        return torch.nn.functional.normalize(x + net(x), dim=1)

    best, best_state, bad = -1.0, None, 0
    tr_t, val_t = torch.tensor(tr, device=dev), torch.tensor(val, device=dev)
    for _ in range(epochs):
        net.train()
        perm = tr_t[torch.randperm(len(tr_t), device=dev)]
        for i in range(0, len(perm), 256):
            b = perm[i : i + 256]
            loss = (1 - (forward(Xb[b]) * Yt[b]).sum(1)).mean()
            opt.zero_grad()
            loss.backward()
            opt.step()
        net.eval()
        with torch.no_grad():
            cos = float((forward(Xb[val_t]) * Yt[val_t]).sum(1).mean())
        if cos > best + 1e-4:
            best, bad = cos, 0
            best_state = {k: v.clone() for k, v in net.state_dict().items()}
        else:
            bad += 1
            if bad >= 5:
                break
    net.load_state_dict(best_state)
    net.eval()

    def apply(Z: np.ndarray) -> np.ndarray:
        out = []
        with torch.no_grad():
            Zb = base(Z)
            for i in range(0, len(Zb), 8192):
                out.append(forward(torch.tensor(Zb[i : i + 8192], device=dev)).cpu().numpy())
        return np.concatenate(out).astype(np.float32)

    return apply


ADAPTERS = {"procrustes": procrustes, "ridge": ridge, "mlp": mlp}
