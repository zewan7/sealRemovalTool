#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
印章去除工具启动脚本
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from stamp_remover.main import main
    sys.exit(main())
except ImportError as e:
    print(f"导入错误: {e}")
    print("请确保已安装所有依赖: pip install -r requirements.txt")
    sys.exit(1)
except Exception as e:
    print(f"启动失败: {e}")
    sys.exit(1)

