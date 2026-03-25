#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
印章去除工具主程序入口
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from .ui.main_window import MainWindow
from .utils.logging_config import setup_logging, get_logger


def main():
    """主函数"""
    setup_logging()
    
    logger = get_logger(__name__)
    logger.info("启动印章去除工具")
    
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("印章去除工具")
        app.setApplicationVersion("1.0.0")
        app.setOrganizationName("Stamp Remover")
        
        app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        
        window = MainWindow()
        window.show()
        
        logger.info("主窗口已显示")
        
        exit_code = app.exec()
        
        logger.info(f"应用程序退出，退出码: {exit_code}")
        return exit_code
        
    except Exception as e:
        logger.error(f"应用程序启动失败: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
