#!/usr/bin/env bash
# ============================================================
# BizRadar 一键部署脚本
# 使用方式：curl -fsSL https://raw.githubusercontent.com/LomaxWang/ideahunter/main/install.sh | bash
# 或者本地运行：chmod +x install.sh && ./install.sh
# ============================================================
set -e

REPO_URL="https://github.com/LomaxWang/ideahunter.git"
INSTALL_DIR="bizradar"
BOLD="\033[1m"
GREEN="\033[32m"
YELLOW="\033[33m"
RED="\033[31m"
RESET="\033[0m"

echo ""
echo -e "${BOLD}🎯 BizRadar 一键部署脚本${RESET}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 检查依赖
check_cmd() {
  if ! command -v "$1" &>/dev/null; then
    echo -e "${RED}✗ 未找到 $1，请先安装后重试${RESET}"
    exit 1
  fi
  echo -e "${GREEN}✓ $1 已安装${RESET}"
}

echo -e "${BOLD}[1/4] 检查运行环境...${RESET}"
check_cmd git
check_cmd docker

echo ""
echo -e "${BOLD}[2/4] 克隆项目...${RESET}"
if [ -d "$INSTALL_DIR" ]; then
  echo -e "${YELLOW}目录 $INSTALL_DIR 已存在，跳过克隆${RESET}"
  cd "$INSTALL_DIR"
else
  git clone "$REPO_URL" "$INSTALL_DIR"
  cd "$INSTALL_DIR"
fi

echo ""
echo -e "${BOLD}[3/4] 配置环境变量...${RESET}"
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo -e "${YELLOW}已创建 .env 文件，请填写以下必要配置：${RESET}"
  echo ""
  echo "  LLM_API_KEY    → 你的大语言模型 API Key"
  echo "  LLM_BASE_URL   → API 接口地址（默认 DeepSeek）"
  echo "  LLM_MODEL      → 模型名称（默认 deepseek-chat）"
  echo ""

  # 交互式填写（若在非交互模式下运行则跳过）
  if [ -t 0 ]; then
    read -rp "请输入 LLM_API_KEY（必填，留空跳过手动填写）: " api_key
    if [ -n "$api_key" ]; then
      sed -i.bak "s|LLM_API_KEY=\"sk-your-api-key-here\"|LLM_API_KEY=\"$api_key\"|" .env
      echo -e "${GREEN}✓ API Key 已写入 .env${RESET}"
    else
      echo -e "${YELLOW}⚠ 请稍后手动编辑 .env 文件填写 API Key${RESET}"
    fi
    rm -f .env.bak
  fi
else
  echo -e "${GREEN}✓ .env 文件已存在，跳过初始化${RESET}"
fi

echo ""
echo -e "${BOLD}[4/4] 启动 Docker 容器...${RESET}"
docker compose pull 2>/dev/null || true
docker compose up -d --build

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${GREEN}${BOLD}🎉 BizRadar 部署成功！${RESET}"
echo ""
echo -e "  📡 访问地址：${BOLD}http://localhost:8000${RESET}"
echo -e "  📂 数据目录：$(pwd)/data"
echo -e "  📄 PRD 输出：$(pwd)/output"
echo ""
echo -e "  常用命令："
echo -e "    查看日志：${BOLD}docker compose logs -f${RESET}"
echo -e "    停止服务：${BOLD}docker compose down${RESET}"
echo -e "    更新版本：${BOLD}git pull && docker compose up -d --build${RESET}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
