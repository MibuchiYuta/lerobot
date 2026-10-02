# SO-101 安全セットアップと最小テレオペ

この手順は SO-101 リーダー/フォロワー用です。GPU 学習機と USB 接続機は同一の **miburia (RTX 5070 Ti)** を使用します。`/dev/ttyACM*` を扱うため、実行 OS は miburia の Ubuntu 側ホスト **`mibuntu-desk`** です。依頼中の `minuria` はマシン台帳にないため、本手順では `miburia` として扱います。実機を接続する前に、ユーザーは対象ホストが miburia であることを確認してください。

> [!WARNING]
> ソフトウェア監視だけでは USB 抜去、ホスト停止、SIGKILL、電源断を確実に止められません。無人・夜間運転は、テスト済みの物理 E-stop と、モーター電源を遮断できる独立したリレー/電源スイッチが設置されるまで禁止です。トルクオフ時はアームが重力で落下し得るため、機械的支持も必要です。

## 0. セットアップ検証（モーターは未接続）

```bash
uv sync --extra feetech
uv run lerobot-find-port --help
uv run lerobot-calibrate --help
uv run python scripts/so101_safe_teleop.py --help
```

`lerobot-find-port` と `lerobot-calibrate` はこの fork の公式エントリポイントです。最後のコマンドはハードウェアを動かしません。

## 1. USB の識別

🔌 **ユーザーの物理操作:** フォロワーだけを USB 接続し、電源はまだ入れません。次を実行し、表示後に指示どおり一度 USB を抜いて Enter、再接続します。

```bash
uv run lerobot-find-port
```

同じ作業をリーダー単独でも行い、得られた `/dev/ttyACM*` を記録します。番号は再起動で変わるため、恒久運用では USB シリアル番号に基づく udev symlink を管理者が設定してください。以下は照合用で、ルールの適用は管理者操作です。

```bash
udevadm info --query=property --name=/dev/ttyACM0
```

🔌 **ユーザーの物理操作:** 安定した台に両アームを固定し、可動範囲に人・物を置かず、物理 E-stop と電源遮断を一度試験します。

## 2. 読み取り専用診断

モーター電源を入れ、各アームを個別に確認します。診断はゴール位置・トルクを変更しません。

```bash
uv run python scripts/so101_diagnose.py /dev/ttyACM0
uv run python scripts/so101_diagnose.py /dev/ttyACM1
```

6 個の位置値が返らない、または通信例外が出る場合は停止し、配線・モーター ID・電源を確認します。正常と見なして先へ進めてはいけません。

## 3. キャリブレーション

🔌 **ユーザーの物理操作:** 画面の指示に従い、各アームを中立位置、次に各関節の安全な全可動域へゆっくり動かします。指やケーブルを挟まないでください。実行中に異常を感じたら物理 E-stop を押します。

```bash
uv run lerobot-calibrate --robot.type=so101_follower --robot.port=/dev/ttyACM0 --robot.id=so101_follower
uv run lerobot-calibrate --teleop.type=so101_leader --teleop.port=/dev/ttyACM1 --teleop.id=so101_leader
```

ID は校正ファイルのキーなので、以降のコマンドで変えません。リポジトリの `scripts/teleoperate_so101.sh` と `scripts/record_so101.sh` もこの `so101_follower` / `so101_leader` を使用します。例のポート割当も同じです。`/dev/ttyACM*` の番号は挿抜順で変わるため、検出結果が異なる場合は、校正・安全テレオペ・既存スクリプトのポートを一貫して更新してから実行してください。

## 4. 立会い最小テレオペ

最初は低速・無負荷・非常停止担当者を別に置いて実行します。`--arm` は E-stop 試験済みの明示確認です。異常、通信断、NaN/欠落値、制御周期超過、過大な関節指令差でフォロワーの各モーターにトルク無効化を試み、同一プロセス内では自動復帰しません。

```bash
uv run python scripts/so101_safe_teleop.py \
  --follower-port /dev/ttyACM0 --leader-port /dev/ttyACM1 --arm \
  --fps 15 --max-cycle-s 0.25 --max-position-step 20
```

衝突/トルク異常は、STS3215 の `Present_Current` の単位・ノイズ・通常最大値を実機で記録してからのみ有効にします。値が確定したら `--max-present-current <measured-limit>` を追加します。テレメトリー読取り失敗・欠損・NaN・しきい値超過は停止します。値が未検証の間、およびこのオプションなしの間は無人・夜間運転を禁止します。USB 通信断後にソフトウェアがトルクオフを書き込めない場合があるため、無人・夜間運転の安全停止は物理 E-stop と電源遮断に依存します。
