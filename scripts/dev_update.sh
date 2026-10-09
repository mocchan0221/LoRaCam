#!/bin/bash
# LoRaCam 開発機用 更新スクリプト
#   GitHub から最新コードを取得し、必要ならライブラリを更新してサービスを再起動する
#   使い方: bash scripts/dev_update.sh [--force-pip]
#     --force-pip : requirements.txt に変更がなくても pip install を実行する

set -euo pipefail

SERVICES=(LoRaCam.service WebMonitor.service)

# pull でこのファイル自体が書き換わっても安全なよう、全体を関数にして先に読み込ませる
main() {
    local force_pip=0
    [[ "${1:-}" == "--force-pip" ]] && force_pip=1

    # sudo で実行すると git や venv のファイルが root 所有になるため禁止
    if [[ $EUID -eq 0 ]]; then
        echo "sudo を付けずに実行してください" >&2
        exit 1
    fi

    cd "$(dirname "${BASH_SOURCE[0]}")/.."
    echo "LoRaCam 更新スクリプト ($(pwd))"

    # 追跡中のファイルに未コミットの変更があると pull で衝突するので中断
    if [[ -n "$(git status --porcelain --untracked-files=no)" ]]; then
        echo "未コミットの変更があります。退避または破棄してから再実行してください:" >&2
        git status --short --untracked-files=no >&2
        exit 1
    fi

    echo "[1/4] 最新コードの取得"
    local old_rev new_rev
    old_rev=$(git rev-parse HEAD)
    git pull --ff-only origin main
    new_rev=$(git rev-parse HEAD)
    if [[ "$old_rev" == "$new_rev" ]]; then
        echo "  既に最新です: $(git log -1 --format='%h %s')"
    else
        git log --oneline "$old_rev..$new_rev" | sed 's/^/  /'
    fi

    echo "[2/4] ライブラリの更新"
    if [[ $force_pip -eq 1 ]] || ! git diff --quiet "$old_rev" "$new_rev" -- requirements.txt; then
        .venv/bin/pip install -r requirements.txt
    else
        echo "  requirements.txt に変更なし (強制するには --force-pip)"
    fi

    echo "[3/4] サービスファイルの更新"
    local svc
    for svc in "${SERVICES[@]}"; do
        sudo install -m 644 "services/$svc" /etc/systemd/system/
    done
    sudo systemctl daemon-reload

    echo "[4/4] サービスの再起動"
    sudo systemctl restart "${SERVICES[@]}"
    sleep 3
    local failed=0 state
    for svc in "${SERVICES[@]}"; do
        state=$(systemctl is-active "$svc" || true)
        echo "  $svc: $state"
        if [[ "$state" != "active" ]]; then
            failed=1
            sudo journalctl -u "$svc" -n 20 --no-pager
        fi
    done

    if [[ $failed -ne 0 ]]; then
        echo "起動に失敗したサービスがあります" >&2
        exit 1
    fi
    echo "更新が完了しました"
}

main "$@"
exit
