#!/usr/bin/env bash
# after.sh.erb — waits for Jupyter to bind the port, then exits (or cleans up on timeout)

set -euo pipefail

# Host/port are exported in before/script per OOD basic helpers
: "${host:=$(hostname -f)}"
: "${port:?port is not set}"

# Make timeout configurable (default 120s instead of 60s)
WAIT_TIMEOUT="${WAIT_TIMEOUT:-120}"

echo "Waiting for Jupyter server to open port ${port} on ${host} ..."
echo "TIMING - Starting wait at: $(date)"

if wait_until_port_used "${host}:${port}" "${WAIT_TIMEOUT}"; then
  echo "Discovered Jupyter server listening on ${host}:${port}"
  echo "TIMING - Wait ended at: $(date)"

  # 小提示：把反代后的 URL 与密码（如果 before 里启用了随机密码）打印出来，便于排障
  PROXY_URL="/node/${host}/${port}/"
  echo "Proxy URL (via OOD): ${PROXY_URL}"
  if [[ -n "${password:-}" ]]; then
    echo "One-time password (also shown in connection panel): ${password}"
  fi

  # 稍等片刻，给 Jupyter 完成初始化
  sleep 2
else
  echo "Timed out waiting ${WAIT_TIMEOUT}s for ${host}:${port} to open."
  echo "TIMING - Wait ended at: $(date)"

  # 兼容 SCRIPT_PID 未设置的情况，避免 pkill 报错
  if [[ -n "${SCRIPT_PID:-}" ]]; then
    pkill -P "${SCRIPT_PID}" || true
  else
    # 兜底：尽量结束 jupyter 进程（不强制要求）
    pkill -f "jupyter.*--config=${CONFIG_FILE:-}" || true
  fi

  clean_up 1
fi
