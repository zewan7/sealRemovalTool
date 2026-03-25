#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
线程管理模块
"""

import logging
from typing import Optional, Dict, Any, List
from PySide6.QtCore import QThread, QObject

from ..utils.logging_config import get_logger
logger = get_logger(__name__)


class ThreadManager(QObject):
    """线程管理器"""
    
    def __init__(self):
        super().__init__()
        self._threads: Dict[str, QThread] = {}
        self._thread_states: Dict[str, bool] = {}
        
    def register_thread(self, name: str, thread: QThread) -> None:
        """注册线程"""
        if name in self._threads:
            logger.warning(f"线程 {name} 已存在，将被替换")
            self.stop_thread(name)
            
        self._threads[name] = thread
        self._thread_states[name] = False
        
        if hasattr(thread, 'finished'):
            thread.finished.connect(lambda: self._on_thread_finished(name))
            
        logger.info(f"注册线程: {name}")
    
    def unregister_thread(self, name: str) -> bool:
        """注销线程（不停止线程，仅从管理器移除）"""
        if name not in self._threads:
            logger.warning(f"线程 {name} 未注册")
            return False
        
        if name in self._threads:
            del self._threads[name]
        if name in self._thread_states:
            del self._thread_states[name]
        logger.info(f"注销线程: {name}")
        return True
    
    def start_thread(self, name: str) -> bool:
        """启动线程"""
        if name not in self._threads:
            logger.error(f"线程 {name} 未注册")
            return False
            
        thread = self._threads[name]
        if thread.isRunning():
            logger.warning(f"线程 {name} 已在运行")
            return False
            
        try:
            thread.start()
            self._thread_states[name] = True
            logger.info(f"启动线程: {name}")
            return True
        except Exception as e:
            logger.error(f"启动线程 {name} 失败: {e}")
            return False
    
    def stop_thread(self, name: str) -> bool:
        """停止线程"""
        if name not in self._threads:
            logger.warning(f"线程 {name} 未注册")
            return False
            
        thread = self._threads[name]
        if not thread.isRunning():
            logger.info(f"线程 {name} 未在运行")
            return False
            
        try:
            thread.quit()
            thread.wait(5000)
            
            if thread.isRunning():
                thread.terminate()
                thread.wait(2000)
                
            self._thread_states[name] = False
            logger.info(f"停止线程: {name}")
            return True
        except Exception as e:
            logger.error(f"停止线程 {name} 失败: {e}")
            return False
    
    def stop_all_threads(self) -> None:
        """停止所有运行中的线程"""
        for name in list(self._threads.keys()):
            if self.is_thread_running(name):
                self.stop_thread(name)
        logger.info("已停止所有线程")
    
    def is_thread_running(self, name: str) -> bool:
        """检查线程是否在运行"""
        if name not in self._threads:
            return False
        return self._threads[name].isRunning()
    
    def has_running_threads(self) -> bool:
        """检查是否有任何线程在运行"""
        return any(thread.isRunning() for thread in self._threads.values())
    
    def get_running_thread_count(self) -> int:
        """获取正在运行的线程数量"""
        return sum(1 for thread in self._threads.values() if thread.isRunning())
    
    def get_thread_count(self) -> int:
        """获取注册的线程总数"""
        return len(self._threads)
    
    def get_thread_names(self) -> List[str]:
        """获取所有注册的线程名称"""
        return list(self._threads.keys())
    
    def get_running_thread_names(self) -> List[str]:
        """获取所有正在运行的线程名称"""
        return [name for name, thread in self._threads.items() if thread.isRunning()]
    
    def get_thread(self, name: str) -> Optional[QThread]:
        """获取线程对象"""
        return self._threads.get(name)
    
    def wait_for_thread(self, name: str, timeout_ms: int = 30000) -> bool:
        """等待线程完成"""
        if name not in self._threads:
            logger.warning(f"线程 {name} 未注册")
            return False
        
        thread = self._threads[name]
        if not thread.isRunning():
            return True
            
        return thread.wait(timeout_ms)
    
    def wait_for_all_threads(self, timeout_ms: int = 30000) -> bool:
        """等待所有线程完成"""
        all_finished = True
        for name in list(self._threads.keys()):
            if not self.wait_for_thread(name, timeout_ms):
                all_finished = False
        return all_finished
    
    def cleanup_thread(self, name: str) -> None:
        """清理线程"""
        if name in self._threads:
            self.stop_thread(name)
            thread = self._threads[name]
            
            thread.deleteLater()
            del self._threads[name]
            del self._thread_states[name]
            
            logger.info(f"清理线程: {name}")
    
    def cleanup_all(self) -> None:
        """清理所有线程"""
        thread_names = list(self._threads.keys())
        for name in thread_names:
            self.cleanup_thread(name)
        
        logger.info("清理所有线程完成")
    
    def _on_thread_finished(self, name: str) -> None:
        """线程完成回调"""
        self._thread_states[name] = False
        logger.info(f"线程 {name} 执行完成")
    
    def get_thread_status(self) -> Dict[str, Any]:
        """获取所有线程状态"""
        status = {}
        for name, thread in self._threads.items():
            status[name] = {
                'running': thread.isRunning(),
                'state': self._thread_states[name],
                'object_name': thread.objectName() or 'Unknown'
            }
        return status
    
    def __del__(self):
        """析构函数"""
        self.cleanup_all()

