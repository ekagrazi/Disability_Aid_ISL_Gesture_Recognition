"""
model.py — BiLSTM model definition and hand-feature extraction.

All dimensions and normalization steps are taken directly from live_inference.py
to ensure exact parity.
"""

import numpy as np
import torch
import torch.nn as nn

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


# ── BiLSTM Model ──────────────────────────────────────────────────────────────

class BiLSTM(nn.Module):
    """Bidirectional LSTM classifier for sign-language sequences."""

    def __init__(self, input_size: int, num_classes: int):
        super().__init__()
        self.lstm = nn.LSTM(
            input_size,
            128,                # hidden units
            num_layers=2,
            batch_first=True,
            bidirectional=True,
        )
        self.fc = nn.Linear(256, num_classes)  # 128 * 2 (bidirectional)

    def forward(self, x):
        out, _ = self.lstm(x)
        out = out[:, -1, :]   # take the last time-step
        return self.fc(out)


# ── Hand Feature Extraction ──────────────────────────────────────────────────

def extract_hand_features(pts) -> np.ndarray:
    """
    Extract 276-dimensional feature vector from 21 hand landmarks.

    Steps (matching live_inference.py exactly):
      1. Wrist-centre the landmarks
      2. Scale-normalise by the norm of landmark 5 (index MCP)
      3. Flatten joint coordinates                → 63
      4. Compute pairwise distances               → 210
      5. Compute palm normal via cross product     → 3
                                           Total  = 276
    """
    pts = np.array(pts)

    # 1. Wrist-centre
    wrist = pts[0]
    pts = pts - wrist

    # 2. Scale-normalise
    scale = np.linalg.norm(pts[5]) + 1e-6
    pts = pts / scale

    # 3. Joint coordinates (21 × 3 = 63)
    joint_coords = pts.flatten()

    # 4. Pairwise distances (C(21,2) = 210)
    pairwise = []
    for i in range(21):
        for j in range(i + 1, 21):
            pairwise.append(np.linalg.norm(pts[i] - pts[j]))
    pairwise = np.array(pairwise)

    # 5. Palm normal (cross product of MCP-index and MCP-pinky vectors)
    v1 = pts[5]
    v2 = pts[17]
    normal = np.cross(v1, v2)
    normal = normal / (np.linalg.norm(normal) + 1e-6)

    return np.concatenate([joint_coords, pairwise, normal])  # 276


# ── Model Loader ─────────────────────────────────────────────────────────────

def load_model(weights_path: str = "slr_model.pth"):
    """
    Load a trained BiLSTM checkpoint.

    Returns
    -------
    model : BiLSTM
        Model in eval mode on the appropriate device.
    class_names : list[str]
        Ordered list of gesture class names stored in the checkpoint.
    """
    checkpoint = torch.load(weights_path, map_location=DEVICE)
    class_names = checkpoint["classes"]

    model = BiLSTM(1154, len(class_names)).to(DEVICE)
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    return model, class_names
