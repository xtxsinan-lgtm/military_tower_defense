#!/usr/bin/env bash
# 开发环境检查（WS06-005）
# 用法：./tools/doctor/doctor.sh
# 可用环境变量指定路径：GODOT=/path/to/godot  BLENDER=/path/to/blender
#
# 退出码：0 = 必需项齐全；1 = 缺少必需项（可选项缺失只给警告）

set -u

MIN_DOTNET_MAJOR=8
MIN_GODOT_MAJOR=4
MIN_BLENDER_MAJOR=4

if [ -t 1 ]; then
  C_OK=$'\033[32m'; C_WARN=$'\033[33m'; C_ERR=$'\033[31m'; C_DIM=$'\033[2m'; C_END=$'\033[0m'
else
  C_OK=""; C_WARN=""; C_ERR=""; C_DIM=""; C_END=""
fi

missing_required=0
missing_optional=0
OS="$(uname -s)"

ok()   { printf '  %s✔%s %-14s %s\n' "$C_OK" "$C_END" "$1" "$2"; }
warn() { printf '  %s!%s %-14s %s\n' "$C_WARN" "$C_END" "$1" "$2"; missing_optional=$((missing_optional+1)); }
err()  { printf '  %s✘%s %-14s %s\n' "$C_ERR" "$C_END" "$1" "$2"; missing_required=$((missing_required+1)); }
hint() { printf '      %s→ %s%s\n' "$C_DIM" "$1" "$C_END"; }

# 取版本字符串中的主版本号，例如 "8.0.404" → 8，"Blender 4.2.1" → 4
major_of() { printf '%s' "$1" | grep -Eo '[0-9]+(\.[0-9]+)+' | head -n1 | cut -d. -f1; }

# 按顺序返回第一个存在的可执行文件
first_exec() {
  for c in "$@"; do
    [ -z "$c" ] && continue
    if command -v "$c" >/dev/null 2>&1; then command -v "$c"; return 0; fi
    if [ -x "$c" ]; then printf '%s' "$c"; return 0; fi
  done
  return 1
}

echo "《守夜》开发环境检查  ($OS)"
echo
echo "必需（M0 / M1）"

# ---------- git ----------
if command -v git >/dev/null 2>&1; then
  ok "git" "$(git --version | awk '{print $3}')"
else
  err "git" "未安装"
  [ "$OS" = "Darwin" ] && hint "xcode-select --install  或  brew install git"
fi

# ---------- git-lfs ----------
if git lfs version >/dev/null 2>&1; then
  ok "git-lfs" "$(git lfs version | awk '{print $1}' | cut -d/ -f2)"
  if ! git config --get filter.lfs.process >/dev/null 2>&1; then
    warn "git-lfs 钩子" "未初始化"
    hint "git lfs install"
  fi
else
  err "git-lfs" "未安装（美术源文件需要）"
  [ "$OS" = "Darwin" ] && hint "brew install git-lfs && git lfs install"
fi

# ---------- .NET SDK ----------
DOTNET="$(first_exec dotnet /usr/local/share/dotnet/dotnet "$HOME/.dotnet/dotnet")"
if [ -n "$DOTNET" ]; then
  best=""
  while read -r line; do
    v="$(printf '%s' "$line" | awk '{print $1}')"
    m="$(major_of "$v")"
    if [ -n "$m" ] && [ "$m" -ge "$MIN_DOTNET_MAJOR" ]; then best="$v"; fi
  done < <("$DOTNET" --list-sdks 2>/dev/null)
  if [ -n "$best" ]; then
    ok ".NET SDK" "$best"
    command -v dotnet >/dev/null 2>&1 || { warn "dotnet PATH" "$DOTNET 不在 PATH 中"; hint "把 $(dirname "$DOTNET") 加入 PATH"; }
  else
    err ".NET SDK" "需要 ≥ $MIN_DOTNET_MAJOR，当前：$("$DOTNET" --list-sdks 2>/dev/null | awk '{print $1}' | tr '\n' ' ')"
    hint "https://dotnet.microsoft.com/download  或  brew install --cask dotnet-sdk"
  fi
else
  err ".NET SDK" "未安装"
  [ "$OS" = "Darwin" ] && hint "brew install --cask dotnet-sdk"
  hint "https://dotnet.microsoft.com/download"
fi

# ---------- Godot 4 .NET ----------
godot_candidates=("${GODOT:-}" godot-mono godot4-mono godot godot4)
if [ "$OS" = "Darwin" ]; then
  for app in /Applications/Godot_mono.app /Applications/Godot.app "$HOME/Applications/Godot_mono.app" "$HOME/Applications/Godot.app"; do
    godot_candidates+=("$app/Contents/MacOS/Godot")
  done
fi
GODOT_BIN="$(first_exec "${godot_candidates[@]}")"
if [ -n "$GODOT_BIN" ]; then
  gv="$("$GODOT_BIN" --version 2>/dev/null | tail -n1)"
  gm="$(major_of "$gv")"
  if [ -z "$gm" ] || [ "$gm" -lt "$MIN_GODOT_MAJOR" ]; then
    err "Godot" "需要 Godot 4.x，当前：${gv:-未知}（$GODOT_BIN）"
  elif printf '%s' "$gv" | grep -qi 'mono'; then
    ok "Godot .NET" "$gv"
    command -v godot >/dev/null 2>&1 || command -v godot-mono >/dev/null 2>&1 || hint "可选：设置 GODOT=$GODOT_BIN 方便工具脚本调用"
  else
    err "Godot .NET" "找到的是标准版（$gv），需要 .NET（mono）版"
    hint "下载 Godot 4 .NET 版：https://godotengine.org/download"
  fi
else
  err "Godot .NET" "未找到（可用 GODOT=/path/to/godot 指定）"
  [ "$OS" = "Darwin" ] && hint "brew install --cask godot-mono"
  hint "https://godotengine.org/download （选择 .NET 版）"
fi

echo
echo "可选（M2 起需要）"

# ---------- Blender ----------
blender_candidates=("${BLENDER:-}" blender)
[ "$OS" = "Darwin" ] && blender_candidates+=(/Applications/Blender.app/Contents/MacOS/Blender "$HOME/Applications/Blender.app/Contents/MacOS/Blender")
BLENDER_BIN="$(first_exec "${blender_candidates[@]}")"
if [ -n "$BLENDER_BIN" ]; then
  bv="$("$BLENDER_BIN" --version 2>/dev/null | head -n1)"
  bm="$(major_of "$bv")"
  if [ -n "$bm" ] && [ "$bm" -ge "$MIN_BLENDER_MAJOR" ]; then
    ok "Blender" "$bv"
  else
    warn "Blender" "需要 ≥ $MIN_BLENDER_MAJOR.x，当前：${bv:-未知}"
  fi
else
  warn "Blender" "未安装（WS03-003 预渲染管线需要）"
  [ "$OS" = "Darwin" ] && hint "brew install --cask blender"
fi

# ---------- Python ----------
if command -v python3 >/dev/null 2>&1; then
  ok "python3" "$(python3 --version 2>&1 | awk '{print $2}')"
else
  warn "python3" "未安装（地图导入等辅助脚本需要）"
fi

echo
if [ "$missing_required" -eq 0 ]; then
  printf '%s必需项齐全%s' "$C_OK" "$C_END"
  [ "$missing_optional" -gt 0 ] && printf '（%d 个可选项 / 警告）' "$missing_optional"
  echo
  exit 0
else
  printf '%s缺少 %d 个必需项%s，按上面的提示安装后重新运行。\n' "$C_ERR" "$missing_required" "$C_END"
  exit 1
fi
