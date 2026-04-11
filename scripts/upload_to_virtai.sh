#!/usr/bin/env bash
# 上传项目到 VirtAI Cloud SFTP
set -e

HOST="sftp2.virtaicloud.com"
PORT="19005"
USER="mNWUfH4xrZ"
PASS="ouJnKLql1j"
LOCAL_DIR="/Users/taless/Code/CQU_BYSJ"
REMOTE_DIR="CQU_BYSJ"  # 上传到远端家目录下的 CQU_BYSJ 文件夹

echo "开始上传项目到 ${HOST}:${PORT} ..."

lftp -u "${USER},${PASS}" sftp://${HOST}:${PORT} <<EOF
set sftp:auto-confirm yes
set net:timeout 30
set net:max-retries 3
set net:reconnect-interval-base 5

# 递归镜像上传，排除不必要文件
mirror --reverse --verbose \
  --exclude-glob .git/ \
  --exclude-glob __pycache__/ \
  --exclude-glob node_modules/ \
  --exclude-glob *.egg-info/ \
  --exclude-glob .DS_Store \
  --exclude-glob uploads/ \
  --exclude-glob runs/ \
  --exclude-glob logs/ \
  --exclude-glob downloads/ \
  --exclude-glob .venv/ \
  --exclude-glob .env \
  "${LOCAL_DIR}" "${REMOTE_DIR}"

bye
EOF

echo "上传完成！"
