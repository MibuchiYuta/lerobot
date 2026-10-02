# SO-101 imitation-learning workflow

This project uses the repository's `LeRobotDataset` v3 workflow: synchronized
camera video is written as MP4 shards and state/action frames as Parquet
shards. Dataset metadata stores the feature schema, FPS, episode boundaries,
and task descriptions. The scripts below are wrappers around the maintained
`lerobot-*` commands, rather than a parallel dataset implementation.

## Connection boundary

`scripts/so101_env.sh` is the only hardware-specific configuration file. It
exports defaults for the SO-101 follower/leader ports, IDs, cameras, and Rerun
display endpoint. Subproject 1's connection layer can supply its resolved
values as `SO101_ROBOT_*`, `SO101_TELEOP_*`, `SO101_CAMERAS`, and
`SO101_DISPLAY_*` environment variables without changing collection, training,
or replay scripts.

The current defaults preserve the established setup: follower `/dev/ttyACM1`,
leader `/dev/ttyACM0`, top camera `/dev/video0`, and wrist camera
`/dev/video4`. No device discovery is performed by the wrappers.

## Offline verification

Every hardware-facing wrapper accepts `--dry-run`. It constructs and prints
the exact `lerobot-*` invocation without importing LeRobot, authenticating,
opening a device, reading a dataset, or using the network. This is the
supported no-robot check while hardware is unavailable.

```bash
TASK_DESCRIPTION="Pick up the black cube" scripts/record_so101.sh --dry-run
DATASET_REPO_ID=my-org/so101_cube POLICY=act scripts/train_so101.sh --dry-run
POLICY_PATH=outputs/train/act_so101/checkpoints/last/pretrained_model \
  DATASET_REPO_ID=my-org/eval_so101_cube TASK_DESCRIPTION="Pick up the black cube" \
  scripts/eval_so101.sh --dry-run
DATASET_REPO_ID=my-org/so101_cube scripts/replay_so101.sh --dry-run
```

## Operational commands

After the connection layer is confirmed and the robot has been calibrated:

```bash
# Teleoperate and collect episodes. PUSH_TO_HUB=false keeps the dataset local.
TASK_DESCRIPTION="Pick up the black cube" DATASET_REPO_ID=my-org/so101_cube \
  PUSH_TO_HUB=false scripts/record_so101.sh

# Train either POLICY=act (default) or POLICY=diffusion. Upload is opt-in.
DATASET_REPO_ID=my-org/so101_cube POLICY=act POLICY_DEVICE=cuda \
  scripts/train_so101.sh

# Execute a policy on the real robot while recording evaluation episodes.
# The eval_ prefix prevents mixing these episodes with demonstration data.
POLICY_PATH=outputs/train/act_so101/checkpoints/last/pretrained_model \
  DATASET_REPO_ID=my-org/eval_so101_cube TASK_DESCRIPTION="Pick up the black cube" \
  PUSH_TO_HUB=false scripts/eval_so101.sh

# Replay a demonstrator episode; set EPISODE to choose another one.
DATASET_REPO_ID=my-org/so101_cube EPISODE=0 scripts/replay_so101.sh
```

`eval_so101.sh` intentionally uses `lerobot-record --policy.path`, because
`lerobot-eval` targets simulation environments. `replay_so101.sh` instead
replays stored action vectors and should only be used after confirming the
robot's clear workspace and calibration.

Actual recording, model training, Hub uploads, and real-robot motion are not
part of offline validation and require the normal hardware and operational
approval process.
