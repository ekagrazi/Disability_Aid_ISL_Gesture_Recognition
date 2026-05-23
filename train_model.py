import os
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from glob import glob
from sklearn.model_selection import train_test_split

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
DATASET_DIR = "dataset"
MAX_LEN = 40


class SLRDataset(Dataset):
    def __init__(self, X, y):
        self.X = X
        self.y = y

    def __len__(self): return len(self.X)

    def __getitem__(self, idx):
        return torch.tensor(self.X[idx], dtype=torch.float32), \
               torch.tensor(self.y[idx], dtype=torch.long)


def pad(seq):
    if len(seq) >= MAX_LEN:
        return seq[:MAX_LEN]
    pad = np.zeros((MAX_LEN-len(seq), seq.shape[1]))
    return np.vstack([seq, pad])


seqs = []
labels = []
classes = sorted(os.listdir(DATASET_DIR))

for label, word in enumerate(classes):
    for f in glob(f"{DATASET_DIR}/{word}/*.npy"):
        seq = np.load(f)
        seq = pad(seq)
        seqs.append(seq)
        labels.append(label)

X = np.array(seqs)
y = np.array(labels)

print("Feature size:", X.shape)  # MUST be (..., 40, 1154)

Xtr, Xv, ytr, yv = train_test_split(
    X, y, test_size=0.2, stratify=y)

train_loader = DataLoader(
    SLRDataset(Xtr,ytr),16,True)

val_loader = DataLoader(
    SLRDataset(Xv,yv),16)


class BiLSTM(nn.Module):
    def __init__(self,input_size,nc):
        super().__init__()
        self.lstm = nn.LSTM(input_size,128,
                            num_layers=2,
                            batch_first=True,
                            bidirectional=True)
        self.fc = nn.Linear(256,nc)

    def forward(self,x):
        out,_ = self.lstm(x)
        out = out[:,-1,:]
        return self.fc(out)


model = BiLSTM(1154, len(classes)).to(DEVICE)
opt = torch.optim.Adam(model.parameters(), lr=0.001)
loss_fn = nn.CrossEntropyLoss(label_smoothing=0.1)

for epoch in range(50):

    model.train()
    correct = total = 0

    for xb,yb in train_loader:
        xb,yb = xb.to(DEVICE), yb.to(DEVICE)

        opt.zero_grad()
        out = model(xb)
        loss = loss_fn(out,yb)
        loss.backward()
        opt.step()

        pred = out.argmax(1)
        correct += (pred==yb).sum().item()
        total += yb.size(0)

    train_acc = correct/total

    model.eval()
    correct = total = 0
    with torch.no_grad():
        for xb,yb in val_loader:
            xb,yb = xb.to(DEVICE), yb.to(DEVICE)
            out = model(xb)
            pred = out.argmax(1)
            correct += (pred==yb).sum().item()
            total += yb.size(0)

    val_acc = correct/total

    print(f"Epoch {epoch+1} | Train {train_acc:.3f} | Val {val_acc:.3f}")

torch.save({
    "model_state": model.state_dict(),
    "classes": classes
}, "slr_model.pth")
