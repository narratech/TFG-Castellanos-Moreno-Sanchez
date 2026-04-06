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
# CARGA
# =========================================================
def cargar_datos():
    X, Y, categorical_info, columnas = cargar_csv_onehot(
        DATASET_PATH,
        OUTPUT_COLUMNS,
        return_dataframe=False
    )

    X = torch.tensor(X, dtype=torch.float32)
    Y = torch.tensor(Y, dtype=torch.float32)

    # mapear columnas a índices
    col_to_idx = {col: i for i, col in enumerate(columnas)}

    cat_groups = []
    for cols in categorical_info.values():
        group_idx = [col_to_idx[c] for c in cols]
        cat_groups.append(group_idx)

    cat_idx = sorted([i for g in cat_groups for i in g])
    num_idx = [i for i in range(X.shape[1]) if i not in cat_idx]

    return X, Y, columnas, cat_groups, cat_idx, num_idx


# =========================================================
# MODELO
# =========================================================
class VAE(nn.Module):
    def __init__(self, input_dim, target_dim):
        super().__init__()

        total_dim = input_dim + target_dim

        encoder_layers = []
        in_dim = total_dim
        for _ in range(HIDDEN_NUM):
            encoder_layers.append(nn.Linear(in_dim, HIDDEN_SIZE))
            encoder_layers.append(nn.ReLU())
            in_dim = HIDDEN_SIZE
        self.encoder = nn.Sequential(*encoder_layers)

        self.fc_mu = nn.Linear(HIDDEN_SIZE, LATENT_SIZE)
        self.fc_logvar = nn.Linear(HIDDEN_SIZE, LATENT_SIZE)

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
        xy = torch.cat([x, y], dim=1)
        h = self.encoder(xy)
        return self.fc_mu(h), self.fc_logvar(h)

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def decode(self, z):
        h = self.decoder(z)

        x_logits = self.output_x(h)   # SIN sigmoid aquí
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
def loss_function(x_logits, x, y_recon, y, mu, logvar,
                  cat_groups, num_idx, beta=BETA):
    """
    x_logits: output del decoder antes de softmax/sigmoid
    x: input original
    y_recon: target continuo reconstruido
    y: target original
    cat_groups: lista de listas de índices categóricos
    num_idx: índices de columnas numéricas
    beta: factor KL
    """
    loss = 0.0

    # --- CATEGÓRICAS ---
    for group in cat_groups:
        logits = x_logits[:, group]  # [batch, n_cats]
        target = torch.argmax(x[:, group], dim=1)  # clase como entero
        loss += nn.functional.cross_entropy(logits, target, reduction='mean')

    # --- NUMÉRICAS ---
    if len(num_idx) > 0:
        x_num = x[:, num_idx]
        x_num_recon = torch.sigmoid(x_logits[:, num_idx])
        loss += nn.functional.mse_loss(x_num_recon, x_num, reduction='mean')

    # --- TARGETS ---
    loss += nn.functional.mse_loss(y_recon, y, reduction='mean')

    # --- KL ---
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

            loss = loss_function(
                x_logits, x_batch,
                y_recon, y_batch,
                mu, logvar,
                cat_groups, num_idx
            )

            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        if (epoch + 1) % 10 == 0:
            print(f"Epoch {epoch+1}/{EPOCHS}, Loss: {total_loss:.2f}")


# =========================================================
# GENERACIÓN
# =========================================================
def generar_datos(model, num_samples, cat_groups, num_idx):
    model.eval()

    z = torch.randn(num_samples, LATENT_SIZE).to(DEVICE)

    with torch.no_grad():
        x_logits, y_gen = model.decode(z)

    x_logits = x_logits.cpu()
    X_gen = torch.zeros_like(x_logits)

    # --- CATEGÓRICAS: argmax por grupo ---
    for group in cat_groups:
        probs = torch.softmax(x_logits[:, group], dim=1)
        idx = torch.argmax(probs, dim=1)

        for i, col in enumerate(group):
            X_gen[:, col] = (idx == i).float()

    # --- NUMÉRICAS ---
    if len(num_idx) > 0:
        X_gen[:, num_idx] = torch.sigmoid(x_logits[:, num_idx])

    return X_gen.numpy(), y_gen.cpu().numpy()

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

    model = VAE(X.shape[1], Y.shape[1]).to(DEVICE)

    print("Entrenando...")
    entrenar(model, X, Y, cat_groups, num_idx)

    print("Generando datos...")
    X_gen, Y_gen = generar_datos(model, N_SYNTHETIC, cat_groups, num_idx)

    data_gen = np.concatenate([X_gen, Y_gen], axis=1)

    columnas_totales = columnas + OUTPUT_COLUMNS

    df_gen = pd.DataFrame(data_gen, columns=columnas_totales)
    df_gen.to_csv(OUTPUT_CSV, index=False)

    print(f"Guardado en {OUTPUT_CSV}")

    print("Extrayendo latentes...")
    latents = extraer_latentes(model, X, Y)

    print("Plot...")
    plot_latentes(latents, Y.numpy())