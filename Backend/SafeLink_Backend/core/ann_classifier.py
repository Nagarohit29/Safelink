from __future__ import annotations

import json
import os
import pickle
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
import torch
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
    roc_curve,
    auc,
    classification_report,
)
from sklearn.model_selection import train_test_split
from torch.utils.data import DataLoader, TensorDataset
from tqdm.auto import tqdm

from config.settings import (
    DEVICE,
    MODELS_DIR,
    PLOTS_DIR,
    BATCH_SIZE,
    NUM_EPOCHS,
    LEARNING_RATE,
    WEIGHT_DECAY,
    RANDOM_SEED,
    TRAINING_PROGRESS_FILE,
    HIDDEN_DIMS,
    DROPOUT_RATE,
    EARLY_STOP_PATIENCE,
    EARLY_STOP_DELTA,
)
from core.utils import (
    load_dataset,
    prepare_features_and_labels,
    get_or_train_scaler,
    scale_features,
    SCALER_PATH,
    features_from_packet,
)

torch.manual_seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

if isinstance(DEVICE, str):
    DEVICE = torch.device(DEVICE if DEVICE != "cuda" or torch.cuda.is_available() else "cpu")


class TrainingProgressReporter:
    def __init__(self, total_epochs: int, progress_file=TRAINING_PROGRESS_FILE):
        self.total_epochs = total_epochs
        self.progress_file = Path(progress_file)
        self.started_at = time.time()
        self.update(epoch=0, train_loss=None, val_loss=None)

    def update(self, epoch: int, train_loss: float | None, val_loss: float | None):
        payload = {
            "total_epochs": self.total_epochs,
            "epoch": epoch,
            "progress": epoch / self.total_epochs if self.total_epochs else 0,
            "train_loss": train_loss,
            "val_loss": val_loss,
            "updated_at": time.time(),
            "elapsed_sec": time.time() - self.started_at,
        }
        self.progress_file.parent.mkdir(parents=True, exist_ok=True)
        with self.progress_file.open("w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)


class TabularNet(nn.Module):
    def __init__(self, input_dim, hidden_dims=None, dropout=None):
        super().__init__()
        hidden_dims = hidden_dims or HIDDEN_DIMS
        dropout = DROPOUT_RATE if dropout is None else dropout
        layers = []
        prev = input_dim
        for h in hidden_dims:
            layers.append(nn.Linear(prev, h))
            layers.append(nn.BatchNorm1d(h))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(dropout))
            prev = h
        layers.append(nn.Linear(prev, 1))
        self.net = nn.Sequential(*layers)

    def forward(self, x):
        return self.net(x).squeeze(dim=-1)

def train_model_from_csv(csv_path, model_out_path=None):
    model_out_path = model_out_path or (MODELS_DIR / "ann_model.pt")
    df = load_dataset(csv_path)
    X, y, numeric_cols = prepare_features_and_labels(df)
    # train/test/deploy split
    x_temp, x_deploy, y_temp, y_deploy = train_test_split(X, y, test_size=0.1, random_state=RANDOM_SEED, stratify=y)
    x_train, x_test, y_train, y_test = train_test_split(x_temp, y_temp, test_size=0.111111, random_state=RANDOM_SEED, stratify=y_temp)  # results in 0.8/0.1/0.1

    scaler = get_or_train_scaler(x_train)
    x_train_s = scale_features(x_train, scaler)
    x_test_s = scale_features(x_test, scaler)
    x_deploy_s = scale_features(x_deploy, scaler)

    # convert to torch
    X_train_t = torch.tensor(x_train_s, dtype=torch.float32)
    y_train_t = torch.tensor(y_train, dtype=torch.float32)
    X_test_t = torch.tensor(x_test_s, dtype=torch.float32)
    y_test_t = torch.tensor(y_test, dtype=torch.float32)
    X_deploy_t = torch.tensor(x_deploy_s, dtype=torch.float32)
    y_deploy_t = torch.tensor(y_deploy, dtype=torch.float32)

    train_ds = TensorDataset(X_train_t, y_train_t)
    test_ds = TensorDataset(X_test_t, y_test_t)
    deploy_ds = TensorDataset(X_deploy_t, y_deploy_t)

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, drop_last=False)
    test_loader = DataLoader(test_ds, batch_size=BATCH_SIZE, shuffle=False)
    deploy_loader = DataLoader(deploy_ds, batch_size=BATCH_SIZE, shuffle=False)

    model = TabularNet(
        input_dim=X_train_t.shape[1],
        hidden_dims=HIDDEN_DIMS,
        dropout=DROPOUT_RATE,
    ).to(DEVICE)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=3, factor=0.5)

    reporter = TrainingProgressReporter(total_epochs=NUM_EPOCHS)

    history = {"train_loss": [], "val_loss": []}
    best_val_loss = float("inf")
    no_improve_epochs = 0
    epoch_bar = tqdm(range(1, NUM_EPOCHS + 1), desc="Epochs", unit="epoch")
    for epoch in epoch_bar:
        model.train()
        epoch_loss = 0.0
        batch_bar = tqdm(train_loader, desc="Train", unit="batch", leave=False)
        for xb, yb in batch_bar:
            xb = xb.to(DEVICE)
            yb = yb.to(DEVICE)
            optimizer.zero_grad()
            out = model(xb)
            loss = criterion(out, yb)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item() * xb.size(0)
            batch_bar.set_postfix(loss=loss.item())

        avg_train_loss = epoch_loss / len(train_loader.dataset)
        # validation
        model.eval()
        val_loss = 0.0
        preds = []
        trues = []
        with torch.no_grad():
            for xb, yb in test_loader:
                xb = xb.to(DEVICE)
                yb = yb.to(DEVICE)
                out = model(xb)
                loss = criterion(out, yb)
                val_loss += loss.item() * xb.size(0)
                probs = torch.sigmoid(out).cpu().numpy()
                preds.extend(probs.tolist())
                trues.extend(yb.cpu().numpy().tolist())
        avg_val_loss = val_loss / len(test_loader.dataset)
        history["train_loss"].append(avg_train_loss)
        history["val_loss"].append(avg_val_loss)
        scheduler.step(avg_val_loss)
        current_lr = optimizer.param_groups[0]["lr"]
        epoch_bar.set_postfix(train_loss=avg_train_loss, val_loss=avg_val_loss, lr=current_lr)
        reporter.update(epoch=epoch, train_loss=avg_train_loss, val_loss=avg_val_loss)

        # save best
        if avg_val_loss < (best_val_loss - EARLY_STOP_DELTA):
            best_val_loss = avg_val_loss
            torch.save({
                "model_state": model.state_dict(),
                "scaler": scaler,
                "numeric_cols": numeric_cols,
                "hidden_dims": list(HIDDEN_DIMS),
                "dropout": DROPOUT_RATE,
            }, str(model_out_path))
            print(f"Saved best model to {model_out_path}")
            no_improve_epochs = 0
        else:
            no_improve_epochs += 1
            if no_improve_epochs >= EARLY_STOP_PATIENCE:
                print("Early stopping triggered due to no validation loss improvement.")
                break

    # After training: evaluate on test and deploy sets, compute metrics and plots
    checkpoint = torch.load(str(model_out_path), map_location=DEVICE, weights_only=False)
    model.load_state_dict(checkpoint["model_state"])
    scaler = checkpoint.get("scaler", scaler)
    numeric_cols = checkpoint.get("numeric_cols", numeric_cols)

    def eval_loader(loader):
        model.eval()
        all_probs = []
        all_true = []
        with torch.no_grad():
            for xb, yb in loader:
                xb = xb.to(DEVICE)
                out = model(xb)
                probs = torch.sigmoid(out).cpu().numpy()
                all_probs.extend(probs.tolist())
                all_true.extend(yb.numpy().tolist())
        preds_bin = [1 if p>=0.5 else 0 for p in all_probs]
        acc = accuracy_score(all_true, preds_bin)
        prec, recall, f1, _ = precision_recall_fscore_support(all_true, preds_bin, average="binary", zero_division=0)
        cm = confusion_matrix(all_true, preds_bin)
        fpr, tpr, _ = roc_curve(all_true, all_probs)
        roc_auc = auc(fpr, tpr)
        return {"acc": acc, "prec": prec, "recall": recall, "f1": f1, "cm": cm, "fpr": fpr, "tpr": tpr, "auc": roc_auc, "probs": all_probs, "true": all_true}

    test_metrics = eval_loader(test_loader)
    deploy_metrics = eval_loader(deploy_loader)

    # Persist probabilities for downstream threshold analysis
    np.save(MODELS_DIR / "test_probs.npy", np.array(test_metrics["probs"], dtype=np.float32))
    np.save(MODELS_DIR / "test_true.npy", np.array(test_metrics["true"], dtype=np.float32))
    np.save(MODELS_DIR / "deploy_probs.npy", np.array(deploy_metrics["probs"], dtype=np.float32))
    np.save(MODELS_DIR / "deploy_true.npy", np.array(deploy_metrics["true"], dtype=np.float32))

    def summarize_thresholds(probs: list[float], true_labels: list[float], split_name: str):
        thresholds = np.linspace(0.1, 0.9, num=17)
        rows = []
        best_row = None
        best_f1 = -1.0
        y_true = np.array(true_labels, dtype=int)
        y_scores = np.array(probs, dtype=float)
        for thr in thresholds:
            y_pred = (y_scores >= thr).astype(int)
            acc = accuracy_score(y_true, y_pred)
            prec, rec, f1, _ = precision_recall_fscore_support(
                y_true,
                y_pred,
                average="binary",
                zero_division=0,
            )
            rows.append({
                "threshold": float(np.round(thr, 4)),
                "accuracy": acc,
                "precision": prec,
                "recall": rec,
                "f1": f1,
            })
            if f1 > best_f1:
                best_f1 = f1
                best_row = rows[-1]
        if rows:
            pd.DataFrame(rows).to_csv(MODELS_DIR / f"threshold_metrics_{split_name}.csv", index=False)
        return best_row or {"threshold": 0.5, "accuracy": None, "precision": None, "recall": None, "f1": None}

    best_test_threshold = summarize_thresholds(test_metrics["probs"], test_metrics["true"], "test")
    best_deploy_threshold = summarize_thresholds(deploy_metrics["probs"], deploy_metrics["true"], "deploy")

    print("Test metrics:", test_metrics["acc"], test_metrics["prec"], test_metrics["recall"], test_metrics["f1"], "AUC:", test_metrics["auc"])
    print("Deploy metrics:", deploy_metrics["acc"], deploy_metrics["prec"], deploy_metrics["recall"], deploy_metrics["f1"], "AUC:", deploy_metrics["auc"])

    # Save plots
    # 1) Loss curve
    plt.figure(figsize=(8,5))
    plt.plot(history["train_loss"], label="train_loss")
    plt.plot(history["val_loss"], label="val_loss")
    plt.legend()
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.title("Training Loss")
    plt.grid(True)
    plt.savefig(PLOTS_DIR / "loss_curve.png", bbox_inches="tight")
    plt.close()

    # 2) Confusion matrix (test)
    plt.figure(figsize=(6,5))
    sns.heatmap(test_metrics["cm"], annot=True, fmt="d", cmap="Blues")
    plt.title("Confusion Matrix (test)")
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.savefig(PLOTS_DIR / "confusion_matrix_test.png", bbox_inches="tight")
    plt.close()

    # 2b) Confusion matrix (deploy)
    plt.figure(figsize=(6,5))
    sns.heatmap(deploy_metrics["cm"], annot=True, fmt="d", cmap="Greens")
    plt.title("Confusion Matrix (deploy)")
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.savefig(PLOTS_DIR / "confusion_matrix_deploy.png", bbox_inches="tight")
    plt.close()

    # 3) ROC curve (test)
    plt.figure(figsize=(6,5))
    plt.plot(test_metrics["fpr"], test_metrics["tpr"], label=f"AUC={test_metrics['auc']:.4f}")
    plt.plot([0,1],[0,1],"--")
    plt.xlabel("FPR")
    plt.ylabel("TPR")
    plt.title("ROC Curve (test)")
    plt.legend()
    plt.grid(True)
    plt.savefig(PLOTS_DIR / "roc_test.png", bbox_inches="tight")
    plt.close()

    # 3b) ROC curve (deploy)
    plt.figure(figsize=(6,5))
    plt.plot(deploy_metrics["fpr"], deploy_metrics["tpr"], label=f"AUC={deploy_metrics['auc']:.4f}")
    plt.plot([0,1],[0,1],"--")
    plt.xlabel("FPR")
    plt.ylabel("TPR")
    plt.title("ROC Curve (deploy)")
    plt.legend()
    plt.grid(True)
    plt.savefig(PLOTS_DIR / "roc_deploy.png", bbox_inches="tight")
    plt.close()

    # Save final evaluation summary
    summary = {
        "test": {
            "acc": test_metrics["acc"],
            "prec": test_metrics["prec"],
            "recall": test_metrics["recall"],
            "f1": test_metrics["f1"],
            "auc": test_metrics["auc"],
            "best_threshold_f1": best_test_threshold,
        },
        "deploy": {
            "acc": deploy_metrics["acc"],
            "prec": deploy_metrics["prec"],
            "recall": deploy_metrics["recall"],
            "f1": deploy_metrics["f1"],
            "auc": deploy_metrics["auc"],
            "best_threshold_f1": best_deploy_threshold,
        },
    }
    with open(MODELS_DIR / "training_summary.pkl", "wb") as f:
        pickle.dump(summary, f)

    # Save human-readable evaluation artifacts
    #  - JSON summary (metrics and confusion matrices)
    eval_summary = {
        "test": {
            **summary["test"],
            "confusion_matrix": test_metrics["cm"].tolist(),
        },
        "deploy": {
            **summary["deploy"],
            "confusion_matrix": deploy_metrics["cm"].tolist(),
        },
    }
    with open(MODELS_DIR / "evaluation_summary.json", "w", encoding="utf-8") as fjson:
        json.dump(eval_summary, fjson, indent=2)

    #  - Classification reports (test and deploy)
    test_report = classification_report(
        test_metrics["true"],
        [1 if p >= 0.5 else 0 for p in test_metrics["probs"]],
        zero_division=0,
    )
    deploy_report = classification_report(
        deploy_metrics["true"],
        [1 if p >= 0.5 else 0 for p in deploy_metrics["probs"]],
        zero_division=0,
    )
    with open(MODELS_DIR / "classification_report_test.txt", "w", encoding="utf-8") as fr:
        fr.write(test_report)
    with open(MODELS_DIR / "classification_report_deploy.txt", "w", encoding="utf-8") as fr:
        fr.write(deploy_report)

    #  - Confusion matrices as CSV (test and deploy)
    pd.DataFrame(test_metrics["cm"], index=["Actual_0", "Actual_1"], columns=["Pred_0", "Pred_1"]).to_csv(
        MODELS_DIR / "confusion_matrix_test.csv",
        index=True,
    )
    pd.DataFrame(deploy_metrics["cm"], index=["Actual_0", "Actual_1"], columns=["Pred_0", "Pred_1"]).to_csv(
        MODELS_DIR / "confusion_matrix_deploy.csv",
        index=True,
    )

    if history["train_loss"] and history["val_loss"]:
        reporter.update(
            epoch=NUM_EPOCHS,
            train_loss=history["train_loss"][-1],
            val_loss=history["val_loss"][-1],
        )

    print("Training finished. Plots & model saved to:", MODELS_DIR, PLOTS_DIR)
    return model_out_path

class ANNDetector:
    def __init__(self, model_path=None, device=DEVICE):
        model_path = model_path or (MODELS_DIR / "ann_model.pt")
        self.model_path = model_path
        device_obj = torch.device(device) if isinstance(device, str) else device
        checkpoint = torch.load(str(model_path), map_location=device_obj, weights_only=False)
        numeric_cols = checkpoint["numeric_cols"]
        self.numeric_cols = numeric_cols
        self.scaler = checkpoint.get("scaler", None)
        # instantiate model
        input_dim = len(numeric_cols)
        self.input_size = input_dim
        hidden_dims = checkpoint.get("hidden_dims", list(HIDDEN_DIMS))
        dropout = checkpoint.get("dropout", DROPOUT_RATE)
        self.model = TabularNet(input_dim=input_dim, hidden_dims=hidden_dims, dropout=dropout)
        self.model.load_state_dict(checkpoint["model_state"])
        self.model.to(device_obj)
        self.model.eval()
        self.device = device_obj
        
        # For incremental learning
        self.optimizer = None
        self.criterion = None

    def predict(self, X):
        """
        X: 2D numpy array or 1D vector of numeric columns in same order
        returns (predicted_label_int, probability)
        """
        arr = np.array(X, dtype=float)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        if self.scaler is not None:
            arr = self.scaler.transform(arr)
        tensor = torch.tensor(arr, dtype=torch.float32).to(self.device)
        with torch.no_grad():
            out = self.model(tensor)
            prob = torch.sigmoid(out).cpu().numpy().flatten()[0]
            pred = 1 if prob >= 0.5 else 0
        return pred, float(prob)
    
    def predict_batch(self, X_batch):
        """
        Batch prediction for multiple samples.
        
        Args:
            X_batch: 2D numpy array (n_samples, n_features)
        
        Returns:
            List of tuples (predicted_label, probability) for each sample
        """
        arr = np.array(X_batch, dtype=float)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        
        if self.scaler is not None:
            arr = self.scaler.transform(arr)
        
        tensor = torch.tensor(arr, dtype=torch.float32).to(self.device)
        
        with torch.no_grad():
            out = self.model(tensor)
            probs = torch.sigmoid(out).cpu().numpy().flatten()
            preds = (probs >= 0.5).astype(int)
        
        # Return list of (prediction, probability) tuples
        return [(int(pred), float(prob)) for pred, prob in zip(preds, probs)]

    def predict_from_scapy(self, pkt):
        # convert packet to feature vector
        fv = features_from_packet(pkt, self.numeric_cols)
        return self.predict(fv)
    
    def predict_from_scapy_batch(self, packets):
        """
        Batch prediction from Scapy packets.
        
        Args:
            packets: List of Scapy packets
        
        Returns:
            List of tuples (predicted_label, probability) for each packet
        """
        # Extract features from all packets
        feature_vectors = []
        for pkt in packets:
            fv = features_from_packet(pkt, self.numeric_cols)
            feature_vectors.append(fv)
        
        if not feature_vectors:
            return []
        
        # Batch prediction
        X_batch = np.array(feature_vectors, dtype=float)
        return self.predict_batch(X_batch)
    
    def prepare_for_training(self, learning_rate=0.0001):
        """
        Prepare model for incremental training.
        Sets up optimizer and criterion with low learning rate.
        """
        if self.optimizer is None:
            self.criterion = nn.BCEWithLogitsLoss()
            self.optimizer = optim.Adam(
                self.model.parameters(), 
                lr=learning_rate,
                weight_decay=0.0001  # Light regularization
            )
        return self.optimizer, self.criterion
    
    def incremental_update(self, X_batch, y_batch, num_epochs=3):
        """
        Perform incremental update on a batch of new data.
        
        Args:
            X_batch: numpy array of features (n_samples, n_features)
            y_batch: numpy array of labels (n_samples,)
            num_epochs: number of training epochs (default 3 for online learning)
        
        Returns:
            dict with training metrics
        """
        from torch.utils.data import TensorDataset, DataLoader
        
        # Ensure optimizer is ready
        optimizer, criterion = self.prepare_for_training()
        
        # Prepare data
        if self.scaler is not None:
            X_batch = self.scaler.transform(X_batch)
        
        X_tensor = torch.tensor(X_batch, dtype=torch.float32).to(self.device)
        y_tensor = torch.tensor(y_batch, dtype=torch.float32).to(self.device)
        
        dataset = TensorDataset(X_tensor, y_tensor)
        dataloader = DataLoader(dataset, batch_size=32, shuffle=True)
        
        # Training mode
        self.model.train()
        
        total_loss = 0
        correct = 0
        total = 0
        
        for epoch in range(num_epochs):
            epoch_loss = 0
            for batch_X, batch_y in dataloader:
                optimizer.zero_grad()
                outputs = self.model(batch_X)
                loss = criterion(outputs, batch_y)
                loss.backward()
                optimizer.step()
                
                epoch_loss += loss.item()
                
                # Calculate accuracy
                probs = torch.sigmoid(outputs)
                preds = (probs >= 0.5).float()
                total += batch_y.size(0)
                correct += (preds == batch_y).sum().item()
            
            total_loss += epoch_loss
        
        # Back to eval mode
        self.model.eval()
        
        accuracy = 100 * correct / total if total > 0 else 0
        avg_loss = total_loss / num_epochs if num_epochs > 0 else 0
        
        return {
            'loss': avg_loss,
            'accuracy': accuracy,
            'samples': len(X_batch)
        }
    
    def save_checkpoint(self, path=None):
        """Save current model state (for backups during continuous learning)"""
        save_path = path or self.model_path
        checkpoint = {
            "model_state": self.model.state_dict(),
            "scaler": self.scaler,
            "numeric_cols": self.numeric_cols,
            "hidden_dims": list(self.model.net[0].out_features) if hasattr(self.model, 'net') else HIDDEN_DIMS,
            "dropout": DROPOUT_RATE,
        }
        torch.save(checkpoint, str(save_path))
        return save_path
    
    def reload_model(self):
        """Reload model from checkpoint (after continuous learning update)"""
        checkpoint = torch.load(str(self.model_path), map_location=self.device, weights_only=False)
        self.model.load_state_dict(checkpoint["model_state"])
        self.scaler = checkpoint.get("scaler", self.scaler)
        self.numeric_cols = checkpoint.get("numeric_cols", self.numeric_cols)
        self.model.eval()

