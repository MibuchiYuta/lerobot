# SO-101 知覚パイプライン（土台）

実機なしで試せる、HSV 色検出 → YOLO 自己ラベル → CPU 学習の最小パイプラインです。Ollama への
薄い VLM クライアントも含みます。カメラ制御やロボット制御は行いません。

## 依存関係

OpenCV は LeRobot の通常依存です。YOLO 学習だけは optional extra を入れます。

```bash
pip install -e '.[perception]'
```

`ultralytics` は AGPL-3.0 または Enterprise License の対象です。利用・配布形態は導入前に確認してください。

## 実機不要の一連の確認

```bash
python3 -m lerobot.perception.synthetic_data /tmp/so101-images --count 8
python3 -m lerobot.perception.yolo_self_label label /tmp/so101-images /tmp/so101-labels \
  --lower 170 100 100 --upper 10 255 255
python3 -m lerobot.perception.yolo_self_label split /tmp/so101-images /tmp/so101-labels /tmp/so101-yolo
python3 -m lerobot.perception.yolo_self_label train /tmp/so101-yolo/dataset.yaml --dry-run
```

`--dry-run` は Ultralytics の import、重み取得、学習を行いません。本当に CPU 学習する場合は
`--dry-run` を外し、`--epochs 1` から始めます。初回の `yolo11n.pt` は外部ダウンロードを伴う可能性があります。

## 色検出だけを試す

```bash
python3 -m lerobot.perception.color_detection IMAGE.png \
  --lower 170 100 100 --upper 10 255 255 --annotated-output /tmp/boxes.png
```

Hue の下限が上限より大きい指定は赤の 179→0 の折り返しを表します。出力は JSON の pixel bounding box です。

## Ollama VLM

Ollama には画像対応の Qwen 系モデルを事前にローカルで用意してください。既定名は、開発環境に
導入済みの画像対応モデル `qwen2.5vl:7b` です。別の画像対応モデルを使う場合だけ、次のように
明示します。

```python
from pathlib import Path
from lerobot.perception.vlm_client import OllamaVLMClient

answer = OllamaVLMClient(model="<your-qwen-vision-model>").classify(Path("frame.png"))
print(answer)
```

Ollama API は既定で `http://127.0.0.1:11434/api/chat` だけを使います。接続失敗や非対応レスポンスは例外として
返し、検出結果を黙って偽装しません。

## 実機接続後

`scripts/record_so101.sh` の top camera は `/dev/video0`, 640x480, MJPG です。録画済みデータセットから
フレームを画像ディレクトリへエクスポートし、この手順の input にします。録画中に同じ `/dev/video0` をこの
パイプラインから二重に開かないでください。ライブ統合をする場合も、取得済み BGR frame を `detect_color` に渡す
だけに留め、検出の成否をロボット動作へ直結しないことから始めます。
