# Ubuntu 24.04 ML 環境構築ガイド

対象: Ubuntu 24.04 + RTX 5070 Ti（Blackwell）+ ROS2 Jazzy + LeRobot

---

## 環境概要

| 項目 | バージョン |
| --- | --- |
| OS | Ubuntu 24.04 LTS |
| GPU | RTX 5070 Ti（Blackwell / sm_100） |
| ROS2 | Jazzy |
| CUDA | 12.8（推奨） |
| PyTorch | 2.6 以上 |
| Python | 3.12（システム） / 3.10〜3.12（venv） |

---

## インストール順序（重要）

```
1. NVIDIA ドライバ（570+）
2. CUDA Toolkit 12.8
3. ROS2 Jazzy
4. Python 仮想環境（venv または conda）
5. PyTorch 2.6+（CUDA ビルド）
6. LeRobot
```

ROS2 と LeRobot は**Python 環境を分離**することが鉄則。

---

## Step 1: NVIDIA ドライバ（570+）

```bash
# ubuntu-drivers で自動選択（推奨）
sudo ubuntu-drivers install

# または明示的に指定
sudo apt install nvidia-driver-570

# 再起動後に確認
nvidia-smi
```

**注意:** `sudo apt install nvidia-driver-xxx` で入るドライバが 570 未満の場合は
NVIDIA 公式リポジトリを追加してから再実行する。

---

## Step 2: CUDA Toolkit 12.8（NVIDIA 公式リポジトリ経由）

```bash
# ❌ apt の標準リポジトリは古いので使わない
# sudo apt install cuda  ← NG

# ✅ NVIDIA 公式リポジトリを追加
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt update
sudo apt install cuda-toolkit-12-8

# パスを通す（~/.bashrc に追記）
echo 'export PATH=/usr/local/cuda-12.8/bin:$PATH' >> ~/.bashrc
echo 'export LD_LIBRARY_PATH=/usr/local/cuda-12.8/lib64:$LD_LIBRARY_PATH' >> ~/.bashrc
source ~/.bashrc

# 確認
nvcc --version
```

---

## Step 3: ROS2 Jazzy

```bash
# ROS2 公式手順通り
sudo apt install software-properties-common
sudo add-apt-repository universe
sudo apt update && sudo apt install curl -y
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
  -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] \
  http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" \
  | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
sudo apt update
sudo apt install ros-jazzy-desktop
```

---

## Step 4: Python 仮想環境（LeRobot 用）

ROS2 はシステム Python（3.12）を使うので、LeRobot 用には**必ず分離した環境**を作る。

### conda / miniforge（推奨）

```bash
# miniforge インストール
wget https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash Miniforge3-Linux-x86_64.sh

# LeRobot 用環境作成
conda create -n lerobot python=3.11
conda activate lerobot
```

### venv（シンプル派向け）

```bash
python3.11 -m venv ~/.venv/lerobot
source ~/.venv/lerobot/bin/activate
```

---

## Step 5: PyTorch 2.6+（CUDA ビルド）

```bash
# conda/venv を activate した状態で実行
# CUDA 12.6 ビルド（安定版）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126

# CUDA 12.8 ビルドが出ていれば
# pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128

# 動作確認
python -c "import torch; print(torch.__version__); print(torch.cuda.is_available()); print(torch.cuda.get_device_name(0))"
```

期待する出力:
```
2.6.x+cu126
True
NVIDIA GeForce RTX 5070 Ti
```

---

## Step 6: LeRobot

```bash
# conda/venv を activate した状態で
pip install lerobot

# または最新 main から（推奨）
git clone https://github.com/huggingface/lerobot.git
cd lerobot
pip install -e ".[all]"
```

---

## ROS2 と LeRobot の共存

```
システム Python 3.12
  └── ROS2 Jazzy（source /opt/ros/jazzy/setup.bash）

conda env: lerobot（Python 3.11）
  └── PyTorch + LeRobot（conda activate lerobot）
```

**ターミナルの使い分け:**
- ROS2 用ターミナル: `source /opt/ros/jazzy/setup.bash`
- LeRobot 用ターミナル: `conda activate lerobot`
- **同一ターミナルで両方 source しない**（Python 環境が壊れる）

---

## トラブルシューティング

### `torch.cuda.is_available()` が False になる

```bash
# ドライバとCUDAのバージョン確認
nvidia-smi          # ドライババージョン確認
nvcc --version      # CUDAバージョン確認
python -c "import torch; print(torch.version.cuda)"  # PyTorchが見ているCUDA

# よくある原因: PyTorch の CPU 版が入っている
pip uninstall torch torchvision torchaudio
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
```

### RTX 5070 Ti が認識されない（sm_100 エラー）

PyTorch 2.5 以前を使っている場合に発生。PyTorch 2.6 以上にアップグレードする。

```bash
pip install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
```

---

## 今後の検討

- **学習の高速化**: RTX 5070 Ti は VRAM 16GB。LeRobot の Diffusion Policy や ACT は十分動く。
- **ROS2 との統合**: 学習済みモデルを ROS2 ノードから呼び出す設計が必要（別途検討）
- **データ収集**: LeRobot の teleoperation でロボットを動かして学習データを収集
