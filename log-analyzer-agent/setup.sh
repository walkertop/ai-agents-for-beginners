#!/bin/bash
# Log Analyzer Agent 环境初始化脚本

set -e

echo "=========================================="
echo "  Log Analyzer Agent 环境初始化"
echo "=========================================="

# 查找 Python 3.11+
find_python311() {
    # 优先查找 python3.11, python3.12, python3.13
    for py in python3.13 python3.12 python3.11; do
        if command -v $py &> /dev/null; then
            echo $py
            return
        fi
    done
    
    # 检查默认 python3 版本
    if command -v python3 &> /dev/null; then
        local version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        local major=$(echo $version | cut -d'.' -f1)
        local minor=$(echo $version | cut -d'.' -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
            echo "python3"
            return
        fi
    fi
    
    echo ""
}

PYTHON_CMD=$(find_python311)

if [ -z "$PYTHON_CMD" ]; then
    echo "❌ 错误: 需要 Python 3.11 或更高版本"
    echo ""
    echo "browser-use 包要求 Python >= 3.11"
    echo ""
    echo "请安装 Python 3.11+:"
    echo "  macOS:   brew install python@3.12"
    echo "  Ubuntu:  sudo apt install python3.12 python3.12-venv"
    echo ""
    echo "安装后重新运行此脚本"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
echo "✓ 使用 Python: $PYTHON_CMD ($PYTHON_VERSION)"

# 创建虚拟环境
if [ ! -d "venv" ]; then
    echo ""
    echo "📦 创建虚拟环境..."
    $PYTHON_CMD -m venv venv
    echo "✓ 虚拟环境已创建 (Python $PYTHON_VERSION)"
else
    echo "✓ 虚拟环境已存在"
    # 检查现有 venv 的 Python 版本
    VENV_PY_VERSION=$(./venv/bin/python --version 2>&1 | cut -d' ' -f2)
    VENV_MINOR=$(echo $VENV_PY_VERSION | cut -d'.' -f2)
    if [ "$VENV_MINOR" -lt 11 ]; then
        echo "⚠️  警告: 现有 venv 使用 Python $VENV_PY_VERSION (< 3.11)"
        echo "   建议删除并重建: rm -rf venv && ./setup.sh"
    fi
fi

# 激活虚拟环境
echo ""
echo "🔄 激活虚拟环境..."
source venv/bin/activate

# 升级 pip
echo ""
echo "📦 升级 pip..."
pip install --upgrade pip -q

# 安装依赖
echo ""
echo "📦 安装依赖..."
pip install -r requirements.txt -q

# 安装 Playwright 浏览器
echo ""
echo "🌐 安装 Playwright Chromium 浏览器..."
playwright install chromium

# 检查 .env 文件
echo ""
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件"
    echo "   请复制 .env.example 为 .env 并配置 API Key:"
    echo ""
    echo "   cp .env.example .env"
    echo "   # 然后编辑 .env 文件，填入你的 OPENAI_API_KEY"
else
    echo "✓ .env 文件已存在"
fi

echo ""
echo "=========================================="
echo "  初始化完成！"
echo "=========================================="
echo ""
echo "使用方法:"
echo "  1. 激活虚拟环境:  source venv/bin/activate"
echo "  2. 配置 API Key:  编辑 .env 文件"
echo "  3. 运行 Agent:    python browser_agent.py <EventID>"
echo ""
echo "示例:"
echo "  python browser_agent.py DJC-CF-1211212348-8RJKIC-529-425718"
echo ""
