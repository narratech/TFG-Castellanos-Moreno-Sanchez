import configparser
import argparse
import os

# ============================================================
# 📦 IMPORTS
# ============================================================

import torch
import torch.nn as nn
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from torch.utils.data import Dataset, DataLoader, random_split
from scipy.stats import pearsonr
from onehot_loader import cargar_csv_onehot

# ============================================================
# 🔧 CONFIGURACIÓN
# ============================================================

parser = argparse.ArgumentParser(description="Script para entrenar GRU")
parser.add_argument("--onehot", type=bool, default=False, help="Indica si necesita aplicar onehot")
args = parser.parse_args()

config = configparser.ConfigParser()
config.read('config.ini')

CSV_PATH = os.path.join("dataset", config['Dataset']['TESTER_CSV_NAME'])
MODEL_PATH = "models/gru_model.pth"
CSV_OUTPUT = "dataset/predicted.csv"
LOSS_PATH = "models/gru_training_log.csv"

SEQUENCE_LENGTH = int(config['Dataset']['SEQUENCE_LENGTH'])
FRAME_SIZE = int(config['Dataset']['BLOCK_SIZE'])

HIDDEN_SIZE = int(config['GRUTrain']['HIDDEN_SIZE'])
NUM_LAYERS = int(config['GRUTrain']['NUM_LAYERS'])

BATCH_SIZE = int(config['GRUTrain']['BATCH_SIZE'])
ACCURACY_THRESHOLD = float(config['GRUTrain']['ACCURACY_THRESHOLD'])
USE_CUDA = bool(config['GRUTrain']['USE_CUDA'])
ONEHOT = args.onehot

OUTPUT_COLUMNS = list(map(str, config['Dataset']['OUTPUT_NAMES'].split(',')))
OUTPUT_SIZE = len(OUTPUT_COLUMNS)

# Crea el directorio si no existe
os.makedirs("graphs", exist_ok=True)

# ============================================================
# 📊 DATASET
# ============================================================

class EmotionSequenceDataset(Dataset):
    def __init__(self, X_raw, Y_raw, sequence_length, frame_size):
        self.sequence_length = sequence_length
        self.frame_size = frame_size

        self.sequences = []
        self.targets = []

        num_samples = len(X_raw)
        num_blocks = num_samples // frame_size

        for b in range(num_blocks):
            start = b * frame_size
            end = start + frame_size

            X_block = X_raw[start:end]
            Y_block = Y_raw[start:end]

            for i in range(0, frame_size - sequence_length + 1):
                x_seq = X_block[i:i + sequence_length]
                y_seq = Y_block[i + sequence_length - 1]

                self.sequences.append(x_seq)
                self.targets.append(y_seq)

        self.sequences = torch.tensor(np.array(self.sequences), dtype=torch.float32)
        self.targets = torch.tensor(np.array(self.targets), dtype=torch.float32)

    @classmethod
    def from_csv(cls, csv_path, sequence_length, frame_size):
        df = pd.read_csv(csv_path)

        # Si existe estructura de secuencia, respetarla
        if "sequence_id" in df.columns:
            df = df.sort_values(["sequence_id", "timestep"])

        inputs = df.iloc[:, :-OUTPUT_SIZE].values
        targets = df.iloc[:, -OUTPUT_SIZE:].values

        return cls(inputs, targets, sequence_length, frame_size)

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        return self.sequences[idx], self.targets[idx]

# ============================================================
# 🧠 MODELO GRU (MISMA ESTRUCTURA)
# ============================================================

class GRUEmotionModel(nn.Module):
    def __init__(self, input_size):
        super().__init__()
        self.gru = nn.GRU(input_size, HIDDEN_SIZE, NUM_LAYERS, batch_first=True)
        self.fc = nn.Sequential(
            nn.Linear(HIDDEN_SIZE, OUTPUT_SIZE),
            nn.Sigmoid()
        )

    def forward(self, x):
        _, h = self.gru(x)
        h = h[-1]
        return self.fc(h)
    
def compute_loss(model, loader, device):
    model.eval()
    loss_fn = nn.MSELoss()
    total = 0

    with torch.no_grad():
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            total += loss_fn(model(x), y).item()

    return total / len(loader)

# ============================================================
# 📊 EVALUACIÓN
# ============================================================

def evaluate(model, loader, device):
    model.eval()
    preds, targets = [], []

    with torch.no_grad():
        for x, y in loader:
            x = x.to(device)
            preds.append(model(x).cpu().numpy())
            targets.append(y.numpy())

    preds = np.vstack(preds)
    targets = np.vstack(targets)

    # ---------- PRECISIÓN ----------
    accuracy = np.mean(np.abs(preds - targets) < ACCURACY_THRESHOLD)
    print(f"\n✅ Precisión (tolerancia ±{ACCURACY_THRESHOLD}): {accuracy:.4f}")

    # ---------- CORRELACIÓN ----------
    correlations = []

    print("\n📈 Correlación por emoción:")
    for i, name in enumerate(OUTPUT_COLUMNS):
        if np.std(targets[:, i]) == 0:
            print(f"  ⚠️ {name}: constante (correlación no definida)")
            correlations.append(np.nan)
        else:
            corr, _ = pearsonr(targets[:, i], preds[:, i])
            correlations.append(corr)
            print(f"  {name}: {corr:.4f}")

    valid_corrs = [c for c in correlations if not np.isnan(c)]
    if valid_corrs:
        print(f"\n📊 Correlación media: {np.mean(valid_corrs):.4f}")
    else:
        print("\n📊 Correlación media: no definida")


def save_predictions_csv(model, loader, device):
    model.eval()
    all_inputs, all_preds = [], []

    with torch.no_grad():
        for x, y in loader:
            x = x.to(device).float()
            y_hat = model(x).cpu().numpy()

            all_preds.append(y_hat)
            all_inputs.append(x.cpu().numpy())

    all_inputs = np.concatenate(all_inputs, axis=0)  # [N, seq_len, features]
    all_preds = np.vstack(all_preds)

    # último timestep de cada secuencia
    all_inputs_last = all_inputs[:, -1, :]

    df = pd.DataFrame(
        np.concatenate([all_inputs_last, all_preds], axis=1),
        columns=[f"Input_{i+1}" for i in range(all_inputs_last.shape[1])] + OUTPUT_COLUMNS
    )

    df.to_csv(CSV_OUTPUT, index=False)
    print(f"✅ Predicciones guardadas en {CSV_OUTPUT}")

def analyze_training_loss():
    if not os.path.exists(LOSS_PATH):
        print("⚠️ No se encontró el archivo de losses")
        return

    df = pd.read_csv(LOSS_PATH)

    losses = df["loss"].values

    print("\n📉 Análisis de convergencia (training):")

    print(f"Loss inicial: {losses[0]:.6f}")
    print(f"Loss final:   {losses[-1]:.6f}")

    # ↓ tendencia general
    if losses[-1] < losses[0]:
        print("✅ El modelo ha aprendido (loss decreciente)")
    else:
        print("⚠️ El modelo no está convergiendo correctamente")

    # ↓ estabilidad (últimas épocas)
    last_losses = losses[-10:] if len(losses) >= 10 else losses
    std_dev = np.std(last_losses)

    print(f"Variación últimas épocas: {std_dev:.6f}")

    if std_dev < 1e-4:
        print("✅ Convergencia estable")
    else:
        print("⚠️ El modelo aún oscila (posible falta de convergencia)")

    plt.figure()
    plt.plot(losses)
    plt.title("Training Loss (Convergencia)")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.savefig("graphs/Convergence.png")

def diagnose_model(model, train_loader, val_loader, device):

    train_loss = compute_loss(model, train_loader, device)
    val_loss = compute_loss(model, val_loader, device)

    print("\n📉 Diagnóstico del modelo:")

    print(f"Train loss: {train_loss:.6f}")
    print(f"Val loss:   {val_loss:.6f}")
    if val_loss > train_loss * 1.2:
        print("⚠️ POSIBLE OVERFITTING: el modelo no generaliza bien")

    # Underfitting
    elif train_loss > 0.05 and val_loss > 0.05:
        print("⚠️ POSIBLE UNDERFITTING: el modelo no aprende bien")

    # Buen modelo
    else:
        print("✅ Modelo con buen equilibrio")

# ============================================================
# 🏁 MAIN
# ============================================================

if __name__ == "__main__":
    device = torch.device("cuda" if USE_CUDA and torch.cuda.is_available() else "cpu")
    print(f"🖥️ Usando dispositivo: {device}")

    # Dataset
    dataset = None
    if(ONEHOT):
        X_raw, Y_raw, categorical_info, feature_columns = cargar_csv_onehot(
            ruta_csv=CSV_PATH,
            columnas_target=OUTPUT_COLUMNS
        )
        dataset = EmotionSequenceDataset(X_raw, Y_raw, SEQUENCE_LENGTH, FRAME_SIZE)
    else:
        dataset = EmotionSequenceDataset.from_csv(
            CSV_PATH,
            SEQUENCE_LENGTH,
            FRAME_SIZE
        )

    dataset_size = len(dataset)

    train_size = int(0.8 * dataset_size)
    val_size = dataset_size - train_size

    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=False)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)

    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=False)

    # Modelo
    input_size = dataset.sequences.shape[2]
    model = GRUEmotionModel(input_size).to(device)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=device))
    print("✅ Modelo GRU cargado correctamente")

    # Evaluación
    evaluate(model, loader, device)
    diagnose_model(model, train_loader, val_loader, device)
    analyze_training_loss()
    save_predictions_csv(model, loader, device)
