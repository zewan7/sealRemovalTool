#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
印章去除工具主程序入口
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

# 导入统一的日志配置
from .utils.logger import setup_logging, get_logger


def main():
    """主函数"""
    # 设置统一的日志配置（确保只配置一次）
    setup_logging()
    
    # 获取日志记录器
    logger = get_logger(__name__)
    logger.info("启动印章去除工具")
    
    try:
        # 创建Qt应用
        app = QApplication(sys.argv)
        app.setApplicationName("印章去除工具")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("Stamp Remover")
        
        # 设置应用属性
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        
        # 导入主窗口
        from .ui.main_window import MainWindow
        
        # 创建主窗口
        window = MainWindow()
        window.show()
        
        logger.info("主窗口已显示")
        
        # 运行应用
        exit_code = app.exec()
        
        logger.info(f"应用程序退出，退出码: {exit_code}")
        return exit_code
        
    except Exception as e:
        logger.error(f"应用程序启动失败: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
