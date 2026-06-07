#!/bin/bash
# TRIANIUMA ARK - SYSTEM ROLLOUT SCRIPT (Delta Force)
set -e

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo ">>> [INIT] Запуск холодной сборки рантайма Ковчега..."

# 1. Верификация виртуального окружения Python
./venv/bin/python -c "import yaml; print('>>> [PYTHON] Зависимости PyYAML: OK')"

# 2. Верификация селф-теста валидатора контрактов Фазы А
SELFTEST=$(./venv/bin/python scripts/task_spec_validator.py --self-test)
echo ">>> [VALIDATOR] $SELFTEST"

# 3. Проверка готовности Node.js окружения MCP
if [ -d "mcp_server" ]; then
    echo ">>> [NODEJS] Директория mcp_server обнаружена."
else
    echo ">>> [ERROR] mcp_server отсутствует!" && exit 1
fi

# 4. Перезапуск диспетчера процессов PM2
echo ">>> [PM2] Пересборка федерации процессов..."
pm2 delete all || true
pm2 start ecosystem.config.js
pm2 save

echo ">>> [SUCCESS] Экосистема RADRILONIUMA успешно развернута и защищена в dump.pm2."
pm2 status
