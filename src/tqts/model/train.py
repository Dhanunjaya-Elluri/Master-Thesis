#!/usr/bin/env python
# coding: utf-8

"""Training module for the Transformer model.

Modelling for next character prediction."""

__author__ = "Dhanunjaya Elluri"
__mail__ = "dhanunjaya.elluri@tu-dortmund.de"

import os
import time
import argparse

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split

from tqts.model.transformer import Transformer
from tqts.utils.dataloader import CharDataset, collate_fn
from tqts.utils.config import load_config


def load_and_split_dataset(file_path: str, seq_len: int, batch_size: int) -> tuple:
    """Load and split the dataset into train and test sets.

    Args:
        file_path (str): Path to the text file.
        seq_len (int): Sequence length.
        batch_size (int): Batch size.

    Returns:
        tuple: Tuple containing train and test data loaders.
    """
    dataset = CharDataset(file_path, seq_len)
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True, collate_fn=collate_fn
    )
    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=True, collate_fn=collate_fn
    )
    return train_loader, val_loader


def init_model(
    vocab_size: int,
    d_model: int,
    num_heads: int,
    num_encoder_layers: int,
    num_decoder_layers: int,
    dim_feedforward: int,
    dropout: float,
    seq_len: int,
    activation: str,
) -> nn.Module:
    """Initialize the Transformer model.

    Args:
        vocab_size (int): Size of the vocabulary.
        d_model (int): Embedding dimension.
        num_heads (int): Number of attention heads.
        num_encoder_layers (int): Number of encoder layers.
        num_decoder_layers (int): Number of decoder layers.
        dim_feedforward (int): Feed forward dimension.
        dropout (float): Dropout probability.
        seq_len (int): Sequence length.
        activation (str): Activation function.


    Returns:
        nn.Module: Transformer model.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = Transformer(
        vocab_size,
        d_model,
        num_heads,
        num_encoder_layers,
        num_decoder_layers,
        dim_feedforward,
        dropout,
        activation,
    ).to(device)
    return model


def evaluate(model: nn.Module, val_loader: DataLoader) -> float:
    """Evaluate the model on the validation set.

    Args:
        model (nn.Module): Transformer model.
        val_loader (DataLoader): Validation data loader.

    Returns:
        float: Validation loss.
    """
    model.eval()
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    criterion = nn.CrossEntropyLoss()
    total_loss = 0.0
    with torch.no_grad():
        for src, tgt in val_loader:
            src = src.to(device)
            tgt = tgt.to(device)
            output = model(src, tgt)
            loss = criterion(
                output.transpose(1, 2), tgt
            )  # output.view(-1, output.size(-1)), tgt.view(-1)
            total_loss += loss.item()
    return total_loss / len(val_loader)


def train(
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    epochs: int,
    lr: float,
    log_interval: int,
    save_path: str,
) -> None:
    """Train the model.

    Args:
        model (nn.Module): Transformer model.
        train_loader (DataLoader): Train data loader.
        val_loader (DataLoader): Validation data loader.
        epochs (int): Number of epochs.
        lr (float): Learning rate.
        log_interval (int): Log interval.
        save_path (str): Path to save the model.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    best_val_loss = float("inf")
    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        start_time = time.time()
        for src, tgt in train_loader:
            src = src.to(device)
            tgt = tgt.to(device)
            optimizer.zero_grad()
            output = model(src, tgt)
            loss = criterion(
                output.transpose(1, 2), tgt
            )  # output.view(-1, output.size(-1)), tgt.view(-1)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        val_loss = evaluate(model, val_loader)
        elapsed_time = time.time() - start_time
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save(model.state_dict(), save_path)
        if epoch % log_interval == 0:
            print(
                f"Epoch: {epoch}, Train Loss: {total_loss / len(train_loader):.4f}, Val Loss: {val_loss:.4f}, Time: {elapsed_time:.2f}s"
            )


def main(config_path: str) -> None:
    """Main function.

    Args:
        config_path (str): Path to the config file.

    Returns:
        None
    """
    config = load_config(config_path)
    train_loader, val_loader = load_and_split_dataset(
        config["data"]["file_path"],
        config["data"]["seq_len"],
        config["data"]["batch_size"],
    )
    model = init_model(
        config["model"]["vocab_size"],
        config["model"]["d_model"],
        config["model"]["num_heads"],
        config["model"]["num_encoder_layers"],
        config["model"]["num_decoder_layers"],
        config["model"]["dim_feedforward"],
        config["model"]["dropout"],
        config["data"]["seq_len"],
        config["model"]["activation"],
    )
    train(
        model,
        train_loader,
        val_loader,
        config["training"]["epochs"],
        config["optimizer"]["lr"],
        config["training"]["log_interval"],
        os.path.join(config["training"]["save_dir"], "model.pt"),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Training module for the Transformer.")
    parser.add_argument(
        "-c",
        "--config",
        type=str,
        default="config.yaml",
        help="Path to the config file.",
    )
    args = parser.parse_args()
    main(args.config)