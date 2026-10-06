# LeRobot Workspace Instructions

この VS Code Dev Container では、personal-kb を必ず追加コンテキストとして参照する。

- personal-kb mount: `/workspaces/personal-kb`
- Claude Code instructions: `/workspaces/personal-kb/CLAUDE.md`
- Codex instructions: `/workspaces/personal-kb/AGENTS.md`

作業前に上記のファイルを読み、ユーザー固有の環境・運用ルール・作業方針に従うこと。
personal-kb は read-only mount なので、LeRobot 作業中に誤って更新しない。

## SO-101 運用記録

SO-101 の現行構成・実機手順・安全境界の正本は personal-kb の
`projects/lerobot.md` に置く。このリポジトリには実装に必要なラッパーと、
その最小限の利用説明だけを置き、同内容の project 文書を新設しない。

`scripts/so101_safe_teleop.py` は、操作者による `KeyboardInterrupt` での終了を
終了コード 130 と INFO ログで記録する。通信・処理・安全監視の失敗は終了コード 1
と例外情報付きの ERROR ログで記録する。
