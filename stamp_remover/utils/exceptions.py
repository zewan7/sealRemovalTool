#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
异常定义模块
"""


class StampRemoverError(Exception):
    """印章去除工具基础异常"""
    pass


class FileNotFoundError(StampRemoverError):
    """文件未找到异常"""
    def __init__(self, file_path: str, message: str = None):
        self.file_path = file_path
        self.message = message or f"文件未找到: {file_path}"
        super().__init__(self.message)


class InvalidFileFormatError(StampRemoverError):
    """无效文件格式异常"""
    def __init__(self, file_path: str, expected_format: str = None, actual_format: str = None):
        self.file_path = file_path
        self.expected_format = expected_format
        self.actual_format = actual_format
        
        if expected_format and actual_format:
            self.message = f"文件格式错误: {file_path}，期望: {expected_format}，实际: {actual_format}"
        elif expected_format:
            self.message = f"文件格式错误: {file_path}，期望: {expected_format}"
        else:
            self.message = f"无效的文件格式: {file_path}"
        
        super().__init__(self.message)


class ImageProcessingError(StampRemoverError):
    """图像处理异常"""
    def __init__(self, message: str, original_error: Exception = None):
        self.original_error = original_error
        self.message = message
        if original_error:
            self.message = f"{message} (原始错误: {str(original_error)})"
        super().__init__(self.message)


class PDFProcessingError(StampRemoverError):
    """PDF处理异常"""
    def __init__(self, message: str, page_num: int = None, original_error: Exception = None):
        self.page_num = page_num
        self.original_error = original_error
        
        if page_num is not None:
            self.message = f"PDF处理错误 (第{page_num}页): {message}"
        else:
            self.message = f"PDF处理错误: {message}"
        
        if original_error:
            self.message = f"{self.message} (原始错误: {str(original_error)})"
        
        super().__init__(self.message)


class ThreadError(StampRemoverError):
    """线程相关异常"""
    def __init__(self, thread_name: str, message: str, original_error: Exception = None):
        self.thread_name = thread_name
        self.original_error = original_error
        self.message = f"线程 '{thread_name}' 错误: {message}"
        if original_error:
            self.message = f"{self.message} (原始错误: {str(original_error)})"
        super().__init__(self.message)


class MemoryError(StampRemoverError):
    """内存不足异常"""
    def __init__(self, required_mb: float = None, available_mb: float = None):
        self.required_mb = required_mb
        self.available_mb = available_mb
        
        if required_mb and available_mb:
            self.message = f"内存不足: 需要 {required_mb:.1f}MB，可用 {available_mb:.1f}MB"
        elif required_mb:
            self.message = f"内存不足: 需要 {required_mb:.1f}MB"
        else:
            self.message = "内存不足"
        
        super().__init__(self.message)


class ConfigurationError(StampRemoverError):
    """配置错误异常"""
    def __init__(self, config_key: str, message: str = None):
        self.config_key = config_key
        self.message = message or f"配置错误: {config_key}"
        super().__init__(self.message)


class ValidationError(StampRemoverError):
    """验证错误异常"""
    def __init__(self, field_name: str, value: any, message: str = None):
        self.field_name = field_name
        self.value = value
        self.message = message or f"验证失败: {field_name}={value}"
        super().__init__(self.message)
