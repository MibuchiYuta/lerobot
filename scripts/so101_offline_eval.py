#!/usr/bin/env python3
"""Evaluate an SO-101 policy against recorded data without accessing hardware.

This intentionally uses only ``LeRobotDataset`` and a local policy checkpoint.
It neither imports robot/camera modules nor opens serial or video devices.
"""

from __future__ import annotations

import argparse
import json
import os
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import torch

from lerobot.configs.policies import PreTrainedConfig
from lerobot.datasets.lerobot_dataset import LeRobotDataset, LeRobotDatasetMetadata
from lerobot.policies.factory import get_policy_class, make_pre_post_processors
from lerobot.utils.constants import ACTION


def masked_error_sums(
    prediction: torch.Tensor, target: torch.Tensor, is_pad: torch.Tensor | None = None
) -> tuple[float, float, int]:
    """Return absolute-error sum, squared-error sum, and valid scalar count."""
    if prediction.shape != target.shape:
        raise ValueError(f"prediction shape {prediction.shape} differs from target shape {target.shape}")
    valid = torch.ones_like(target, dtype=torch.bool)
    if is_pad is not None:
        valid &= ~is_pad.to(dtype=torch.bool).unsqueeze(-1)
    errors = prediction - target
    count = int(valid.sum().item())
    return (
        float(errors.abs().masked_select(valid).sum().item()),
        float(errors.square().masked_select(valid).sum().item()),
        count,
    )


def _parse_episodes(value: str) -> list[int]:
    episodes = [int(item) for item in value.split(",") if item]
    if not episodes:
        raise argparse.ArgumentTypeError("at least one hold-out episode is required")
    return episodes


def _mean_action(
    dataset: LeRobotDataset, batch_size: int, max_batches: int | None = None
) -> torch.Tensor:
    total: torch.Tensor | None = None
    count = 0
    loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    for batches, batch in enumerate(loader, start=1):
        actions = batch[ACTION].float()
        pad = batch.get("action_is_pad")
        valid = torch.ones_like(actions, dtype=torch.bool)
        if pad is not None:
            valid &= ~pad.to(dtype=torch.bool).unsqueeze(-1)
        action_sum = actions.masked_fill(~valid, 0).sum(dim=tuple(range(actions.ndim - 1)))
        total = action_sum if total is None else total + action_sum
        count += int(valid.sum().item() // actions.shape[-1])
        if max_batches is not None and batches >= max_batches:
            break
    if total is None or count == 0:
        raise ValueError("hold-out dataset has no valid actions")
    return total / count


def _write_metrics(output: Path, metrics: dict[str, Any], overwrite: bool) -> None:
    """Atomically persist metrics, without silently replacing an existing file."""
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() and not overwrite:
        raise FileExistsError(f"output already exists (pass --overwrite to replace it): {output}")

    lock = output.with_name(f".{output.name}.lock")
    try:
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise FileExistsError(f"output is being written by another evaluator: {output}") from error

    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    try:
        with os.fdopen(lock_fd, "w"):
            pass
        if output.exists() and not overwrite:
            raise FileExistsError(f"output already exists (pass --overwrite to replace it): {output}")
        with temporary.open("w", encoding="utf-8") as file:
            file.write(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, output)
    finally:
        temporary.unlink(missing_ok=True)
        lock.unlink(missing_ok=True)


def evaluate(
    checkpoint: Path,
    dataset_repo_id: str,
    holdout_episodes: Iterable[int],
    output: Path,
    batch_size: int,
    device: str,
    video_backend: str,
    max_batches: int | None,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Run a checkpoint over hold-out dataset episodes and persist JSON metrics."""
    if not checkpoint.is_dir():
        raise FileNotFoundError(f"checkpoint directory does not exist: {checkpoint}")
    if max_batches is not None and max_batches <= 0:
        raise ValueError("max_batches must be positive when provided")
    config = PreTrainedConfig.from_pretrained(checkpoint)
    config.device = device
    metadata = LeRobotDatasetMetadata(dataset_repo_id)
    delta_timestamps = {ACTION: [index / metadata.fps for index in config.action_delta_indices]}
    dataset = LeRobotDataset(
        dataset_repo_id,
        episodes=list(holdout_episodes),
        delta_timestamps=delta_timestamps,
        video_backend=video_backend,
    )
    mean_action = _mean_action(dataset, batch_size, max_batches)
    policy_class = get_policy_class(config.type)
    policy = policy_class.from_pretrained(checkpoint, config=config, strict=True)
    preprocessor, _ = make_pre_post_processors(config, pretrained_path=str(checkpoint))
    loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=False, num_workers=0)

    loss_total = 0.0
    l1_total = 0.0
    batches = 0
    zero_abs = zero_sq = mean_abs = mean_sq = 0.0
    scalar_count = 0
    # ACT computes its VAE loss only in training mode; inference remains
    # gradient-free below and no environment or hardware is involved.
    policy.train()
    with torch.inference_mode():
        for raw_batch in loader:
            actions = raw_batch[ACTION].float()
            pad = raw_batch.get("action_is_pad")
            absolute, squared, count = masked_error_sums(torch.zeros_like(actions), actions, pad)
            zero_abs += absolute
            zero_sq += squared
            scalar_count += count
            absolute, squared, _ = masked_error_sums(
                mean_action.to(actions).view(*([1] * (actions.ndim - 1)), -1).expand_as(actions),
                actions,
                pad,
            )
            mean_abs += absolute
            mean_sq += squared
            batch = preprocessor(raw_batch)
            loss, details = policy(batch)
            loss_total += float(loss.item())
            l1_total += float((details or {}).get("l1_loss", loss.item()))
            batches += 1
            if max_batches is not None and batches >= max_batches:
                break

    if batches == 0 or scalar_count == 0:
        raise ValueError("hold-out dataset produced no batches")
    metrics = {
        "checkpoint": str(checkpoint.resolve()),
        "dataset_repo_id": dataset_repo_id,
        "holdout_episodes": list(dataset.episodes or []),
        "batches": batches,
        "policy_loss_mean": loss_total / batches,
        "policy_l1_loss_mean": l1_total / batches,
        "raw_action_baselines": {
            "zero": {"mae": zero_abs / scalar_count, "mse": zero_sq / scalar_count},
            "holdout_mean": {"mae": mean_abs / scalar_count, "mse": mean_sq / scalar_count},
        },
        "hardware_access": False,
    }
    _write_metrics(output, metrics, overwrite)
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--dataset.repo_id", dest="dataset_repo_id", required=True)
    parser.add_argument("--holdout-episodes", type=_parse_episodes, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--overwrite", action="store_true", help="replace an existing output atomically")
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--video-backend", "--dataset.video_backend", dest="video_backend", default="pyav")
    parser.add_argument("--max-batches", type=int, default=None)
    args = parser.parse_args()
    print(json.dumps(evaluate(**vars(args)), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
