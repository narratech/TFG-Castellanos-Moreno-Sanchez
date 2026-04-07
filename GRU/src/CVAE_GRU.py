import configparser
import os

# ============================================================
# 📦 IMPORTS
# ============================================================

import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from onehot_loader import cargar_csv_onehot

# =========================================================
# 🔹 CONFIGURACIÓN
# =========================================================

config = configparser.ConfigParser()
config.read('config.ini')

CSV_FOLDER = "dataset/"
DATASET_PATH = CSV_FOLDER + config['Dataset']['CSV_NAME']
OUTPUT_CSV = CSV_FOLDER + "generated_" + os.path.basename(DATASET_PATH)

OUTPUT_COLUMNS = list(map(str, config['Dataset']['OUTPUT_NAMES'].split(',')))

FRAME_SIZE = int(config['Dataset']['BLOCK_SIZE'])
SEQUENCE_LENGTH = int(config['Dataset']['SEQUENCE_LENGTH'])

LATENT_SIZE = int(config['Autoencoder']['LATENT_SIZE'])
HIDDEN_SIZE = int(config['Autoencoder']['HIDDEN_SIZE'])
HIDDEN_NUM = int(config['Autoencoder']['HIDDEN_NUM'])
EPOCHS = int(config['Autoencoder']['EPOCHS'])
BATCH_SIZE = int(config['Autoencoder']['BATCH_SIZE'])
LR = float(config['Autoencoder']['LEARNING_RATE'])
BETA = float(config['Autoencoder']['BETA_VAE'])
N_SYNTHETIC = int(config['Autoencoder']['N_SYNTHETIC'])

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# =========================================================
# CARGA DE DATOS
# =========================================================
def cargar_datos():
    X, Y, categorical_info, columnas = cargar_csv_onehot(
        DATASET_PATH,
        OUTPUT_COLUMNS,
        return_dataframe=False
    )
    X = torch.tensor(X, dtype=torch.float32)
    Y = torch.tensor(Y, dtype=torch.float32)

    col_to_idx = {col: i for i, col in enumerate(columnas)}

    cat_groups = []
    for cols in categorical_info.values():
        group_idx = [col_to_idx[c] for c in cols]
        cat_groups.append(group_idx)

    cat_idx = sorted([i for g in cat_groups for i in g])
    num_idx = [i for i in range(X.shape[1]) if i not in cat_idx]

    return X, Y, columnas, cat_groups, cat_idx, num_idx

# =========================================================
# CREAR SUB-SECUENCIAS
# =========================================================
def crear_subsecuencias(X, Y, frame_size, sequence_length):
    """
    Extrae sub-secuencias de longitud sequence_length dentro de bloques de tamaño frame_size.
    """
    X_frames, Y_frames = [], []

    num_samples = X.shape[0]
    num_blocks = num_samples // frame_size

    for b in range(num_blocks):
        start_block = b * frame_size
        end_block = start_block + frame_size

        X_block = X[start_block:end_block]
        Y_block = Y[start_block:end_block]

        # extraer sub-secuencias de longitud sequence_length, stride=1
        for start in range(0, frame_size - sequence_length + 1):
            end = start + sequence_length
            X_frames.append(X_block[start:end])
            Y_frames.append(Y_block[start:end])

    return torch.stack(X_frames), torch.stack(Y_frames)

# =========================================================
# MODELO VAE
# =========================================================
class VAE(nn.Module):
    def __init__(self, input_dim, target_dim):
        super().__init__()
        total_dim = input_dim + target_dim

        # Encoder
        encoder_layers = []
        in_dim = total_dim
        for _ in range(HIDDEN_NUM):
            encoder_layers.append(nn.Linear(in_dim, HIDDEN_SIZE))
            encoder_layers.append(nn.ReLU())
            in_dim = HIDDEN_SIZE
        self.encoder = nn.Sequential(*encoder_layers)
        self.fc_mu = nn.Linear(HIDDEN_SIZE, LATENT_SIZE)
        self.fc_logvar = nn.Linear(HIDDEN_SIZE, LATENT_SIZE)

        # Decoder
        decoder_layers = []
        in_dim = LATENT_SIZE
        for _ in range(HIDDEN_NUM):
            decoder_layers.append(nn.Linear(in_dim, HIDDEN_SIZE))
            decoder_layers.append(nn.ReLU())
            in_dim = HIDDEN_SIZE
        self.decoder = nn.Sequential(*decoder_layers)

        self.output_x = nn.Linear(HIDDEN_SIZE, input_dim)
        self.output_y = nn.Linear(HIDDEN_SIZE, target_dim)

    def encode(self, x, y):
        xy = torch.cat([x, y], dim=2) if x.ndim == 3 else torch.cat([x, y], dim=1)
        h = self.encoder(xy)
        return self.fc_mu(h), self.fc_logvar(h)

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def decode(self, z):
        # si z es [batch, latent] o [batch, seq_len, latent]
        h = self.decoder(z)
        x_logits = self.output_x(h)
        y = torch.sigmoid(self.output_y(h))
        return x_logits, y

    def forward(self, x, y):
        mu, logvar = self.encode(x, y)
        z = self.reparameterize(mu, logvar)
        x_logits, y_recon = self.decode(z)
        return x_logits, y_recon, mu, logvar

# =========================================================
# LOSS
# =========================================================
def loss_function(x_logits, x, y_recon, y, cat_groups, num_idx, beta=BETA):
    loss = 0.0
    # Categoricas
    for group in cat_groups:
        logits = x_logits[:, :, group] if x.ndim == 3 else x_logits[:, group]
        target = torch.argmax(x[:, :, group], dim=2) if x.ndim == 3 else torch.argmax(x[:, group], dim=1)
        logits = logits.reshape(-1, logits.shape[-1])
        target = target.reshape(-1)
        loss += nn.functional.cross_entropy(logits, target)
    # Numéricas
    if len(num_idx) > 0:
        x_num = x[:, :, num_idx] if x.ndim == 3 else x[:, num_idx]
        x_num_recon = torch.sigmoid(x_logits[:, :, num_idx] if x.ndim == 3 else x_logits[:, num_idx])
        loss += nn.functional.mse_loss(x_num_recon, x_num)
    # Targets
    loss += nn.functional.mse_loss(y_recon, y)
    # KL
    mu, logvar = 0, 0
    if hasattr(x_logits, 'mu') and hasattr(x_logits, 'logvar'):
        mu, logvar = x_logits.mu, x_logits.logvar
    else:
        mu, logvar = torch.zeros(1), torch.zeros(1)
    KLD = -0.5 * torch.mean(1 + logvar - mu.pow(2) - logvar.exp())
    return loss + beta * KLD

# =========================================================
# ENTRENAMIENTO
# =========================================================
def entrenar(model, X, Y, cat_groups, num_idx):
    optimizer = optim.Adam(model.parameters(), lr=LR)
    dataset = torch.utils.data.TensorDataset(X, Y)
    loader = torch.utils.data.DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)
    model.train()
    for epoch in range(EPOCHS):
        total_loss = 0
        for x_batch, y_batch in loader:
            x_batch = x_batch.to(DEVICE)
            y_batch = y_batch.to(DEVICE)
            optimizer.zero_grad()
            x_logits, y_recon, mu, logvar = model(x_batch, y_batch)
            loss = loss_function(x_logits, x_batch, y_recon, y_batch, cat_groups, num_idx)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1}/{EPOCHS}, Loss: {total_loss:.2f}")

# =========================================================
# GENERACIÓN DE DATOS
# =========================================================
def generar_datos(model, n_sequences, seq_len, cat_groups, num_idx):
    """
    Genera secuencias completas [n_sequences, seq_len, features] para GRU.
    """
    model.eval()
    X_gen_list, Y_gen_list = [], []

    with torch.no_grad():
        for _ in range(n_sequences):
            # z por secuencia
            z = torch.randn(seq_len, LATENT_SIZE).to(DEVICE)  # [seq_len, latent_size]
            x_logits, y_gen = model.decode(z)                 # x_logits: [seq_len, n_features]

            x_logits = x_logits.cpu()
            X_seq = torch.zeros_like(x_logits)

            # --- Categoricas ---
            for group in cat_groups:
                probs = torch.softmax(x_logits[:, group], dim=1)
                idx = torch.argmax(probs, dim=1)             # [seq_len]
                for i, col in enumerate(group):
                    X_seq[:, col] = (idx == i).float()      # ✅ asignación correcta

            # --- Numéricas ---
            if len(num_idx) > 0:
                X_seq[:, num_idx] = torch.sigmoid(x_logits[:, num_idx])

            X_gen_list.append(X_seq.numpy())
            Y_gen_list.append(y_gen.cpu().numpy())

    X_gen = np.stack(X_gen_list)  # [n_sequences, seq_len, n_features]
    Y_gen = np.stack(Y_gen_list)  # [n_sequences, seq_len, n_targets]

    return X_gen, Y_gen

# =========================================================
# GUARDAR CSV
# =========================================================
def guardar_csv_secuencias(X_gen, Y_gen, columnas, output_columns, output_path):
    """
    Guarda secuencias generadas en CSV, un time step por fila.
    """
    n_seq, seq_len, n_features = X_gen.shape
    n_targets = Y_gen.shape[2]
    data = np.concatenate([X_gen, Y_gen], axis=2)
    data_flat = data.reshape(n_seq * seq_len, n_features + n_targets)
    df = pd.DataFrame(data_flat, columns=columnas + output_columns)
    df.to_csv(output_path, index=False)
    print(f"CSV generado en {output_path}")

def extraer_latentes(model, X, Y):
    model.eval()

    latents = []

    with torch.no_grad():
        for i in range(0, len(X), 256):
            x_batch = X[i:i+256].to(DEVICE)
            y_batch = Y[i:i+256].to(DEVICE)

            mu, logvar = model.encode(x_batch, y_batch)
            latents.append(mu.cpu().numpy())

    return np.vstack(latents)

from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

def plot_latentes(latents, Y):
    # Reducir a 2D
    pca = PCA(n_components=2)
    latents_2d = pca.fit_transform(latents)

    plt.figure(figsize=(8,6))

    # Si hay múltiples targets, usa el primero
    color = Y[:, 0] if Y.shape[1] > 0 else None

    scatter = plt.scatter(
        latents_2d[:, 0],
        latents_2d[:, 1],
        c=color,
        alpha=0.7
    )

    if color is not None:
        plt.colorbar(scatter, label="Target")

    plt.title("Espacio latente (PCA)")
    plt.xlabel("Componente 1")
    plt.ylabel("Componente 2")

    plt.show()

# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    X, Y, columnas, cat_groups, cat_idx, num_idx = cargar_datos()

    X_input, Y_input = crear_subsecuencias(X, Y, FRAME_SIZE, SEQUENCE_LENGTH)

    model = VAE(X_input.shape[2], Y_input.shape[2]).to(DEVICE)

    print("Entrenando...")
    entrenar(model, X_input, Y_input, cat_groups, num_idx)

    print("Generando datos...")
    X_gen, Y_gen = generar_datos(model, N_SYNTHETIC, SEQUENCE_LENGTH, cat_groups, num_idx)

    guardar_csv_secuencias(X_gen, Y_gen, columnas, OUTPUT_COLUMNS, OUTPUT_CSV)

    print("Extrayendo latentes...")
    latents = extraer_latentes(model, X, Y)

    print("Plot...")
    plot_latentes(latents, Y.numpy())