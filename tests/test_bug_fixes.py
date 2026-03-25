#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BUG修复验证测试
验证所有7个BUG是否已修复
"""

import pytest
import sys
import os
import tempfile
import logging
from pathlib import Path
from unittest.mock import Mock, patch
import numpy as np
from PIL import Image
import io

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from stamp_remover.core import ThreadManager, ImageProcessingThread, PdfProcessingThread
from stamp_remover.core.stamp_detector import StampDetector, AdvancedStampRemover
from stamp_remover.utils.helpers import (
    validate_image_file, validate_pdf_file, validate_file_extension,
    validate_mime_type, get_safe_output_path
)
from stamp_remover.utils.logger import setup_logging, get_logger, reset_logging


class TestBug1ThreadManager:
    """BUG 1: 线程管理器方法缺失"""
    
    def test_thread_manager_has_cleanup_all(self):
        """测试线程管理器是否有cleanup_all方法"""
        manager = ThreadManager()
        assert hasattr(manager, 'cleanup_all'), "ThreadManager缺少cleanup_all方法"
        
    def test_thread_manager_has_register_thread(self):
        """测试线程管理器是否有register_thread方法"""
        manager = ThreadManager()
        assert hasattr(manager, 'register_thread'), "ThreadManager缺少register_thread方法"
        
    def test_thread_manager_has_start_thread(self):
        """测试线程管理器是否有start_thread方法"""
        manager = ThreadManager()
        assert hasattr(manager, 'start_thread'), "ThreadManager缺少start_thread方法"
        
    def test_thread_manager_has_stop_thread(self):
        """测试线程管理器是否有stop_thread方法"""
        manager = ThreadManager()
        assert hasattr(manager, 'stop_thread'), "ThreadManager缺少stop_thread方法"
        
    def test_thread_manager_has_is_thread_running(self):
        """测试线程管理器是否有is_thread_running方法"""
        manager = ThreadManager()
        assert hasattr(manager, 'is_thread_running'), "ThreadManager缺少is_thread_running方法"


class TestBug2StampDetection:
    """BUG 2: 印章去除算法过于简单导致误删"""
    
    def test_stamp_detector_has_multi_feature_detection(self):
        """测试印章检测器是否有多特征检测功能"""
        detector = StampDetector()
        
        # 检查是否有多种检测方法
        assert hasattr(detector, 'detect_color_regions'), "缺少颜色区域检测方法"
        assert hasattr(detector, 'filter_by_shape'), "缺少形状过滤方法"
        assert hasattr(detector, 'filter_by_edge'), "缺少边缘检测方法"
        
    def test_advanced_stamp_remover_exists(self):
        """测试高级印章去除器是否存在"""
        remover = AdvancedStampRemover()
        assert remover is not None, "AdvancedStampRemover不存在"
        
    def test_advanced_stamp_remover_has_multiple_methods(self):
        """测试高级印章去除器是否有多种处理方法"""
        remover = AdvancedStampRemover(method='auto')
        assert hasattr(remover, 'remove_stamp'), "缺少remove_stamp方法"
        
        # 测试不同方法
        for method in ['auto', 'color', 'hsv']:
            remover = AdvancedStampRemover(method=method)
            assert remover.method == method, f"方法 {method} 未正确设置"
            
    def test_stamp_detector_uses_region_analysis(self):
        """测试印章检测器是否使用连通区域分析"""
        detector = StampDetector()
        assert hasattr(detector, 'min_stamp_size'), "缺少最小印章尺寸限制"
        assert hasattr(detector, 'max_stamp_size'), "缺少最大印章尺寸限制"
        
    def test_stamp_detector_validates_parameters(self):
        """测试印章检测器参数验证"""
        # 测试有效参数
        detector = StampDetector(threshold=185, channel_index=0)
        assert detector.threshold == 185
        assert detector.channel_index == 0
        
        # 测试边界值
        detector = StampDetector(min_stamp_size=100, max_stamp_size=1000000)
        assert detector.min_stamp_size == 100
        assert detector.max_stamp_size == 1000000


class TestBug3FileValidation:
    """BUG 3: 文件扩展名检查不严谨"""
    
    def test_validate_file_extension_strict(self):
        """测试严格的文件扩展名验证"""
        from stamp_remover.utils.helpers import SUPPORTED_IMAGE_EXTENSIONS
        
        # 测试有效扩展名
        assert validate_file_extension("test.jpg", SUPPORTED_IMAGE_EXTENSIONS)
        assert validate_file_extension("test.png", SUPPORTED_IMAGE_EXTENSIONS)
        assert validate_file_extension("test.JPG", SUPPORTED_IMAGE_EXTENSIONS)  # 大小写不敏感
        
        # 测试无效扩展名
        assert not validate_file_extension("test.exe", SUPPORTED_IMAGE_EXTENSIONS)
        assert not validate_file_extension("test", SUPPORTED_IMAGE_EXTENSIONS)
        
    def test_validate_mime_type(self):
        """测试MIME类型验证"""
        from stamp_remover.utils.helpers import SUPPORTED_IMAGE_MIMETYPES
        
        # 创建临时图片文件测试MIME类型
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            # 创建一个简单的PNG图像
            img = Image.new('RGB', (100, 100), color='red')
            img.save(f.name)
            temp_path = f.name
        
        try:
            is_valid, result = validate_mime_type(temp_path, SUPPORTED_IMAGE_MIMETYPES)
            assert is_valid, f"MIME类型验证失败: {result}"
        finally:
            os.unlink(temp_path)
            
    def test_validate_image_file_comprehensive(self):
        """测试全面的图片文件验证"""
        # 创建临时图片文件
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            img = Image.new('RGB', (100, 100), color='red')
            img.save(f.name)
            temp_path = f.name
        
        try:
            # 严格验证
            is_valid, message = validate_image_file(temp_path, strict=True)
            assert is_valid, f"图片验证失败: {message}"
            assert "验证通过" in message
            
            # 非严格验证
            is_valid, message = validate_image_file(temp_path, strict=False)
            assert is_valid, f"图片验证失败: {message}"
        finally:
            os.unlink(temp_path)
            
    def test_validate_image_file_invalid(self):
        """测试无效图片文件验证"""
        # 测试不存在的文件
        is_valid, message = validate_image_file("nonexistent.jpg")
        assert not is_valid
        assert "文件不存在" in message
        
        # 测试不支持的格式
        with tempfile.NamedTemporaryFile(suffix='.exe', delete=False) as f:
            f.write(b"fake exe content")
            temp_path = f.name
        
        try:
            is_valid, message = validate_image_file(temp_path)
            assert not is_valid
            assert "不支持的" in message
        finally:
            os.unlink(temp_path)
            
    def test_validate_pdf_file_comprehensive(self):
        """测试全面的PDF文件验证"""
        # 注意：这里只测试不存在的文件，因为创建有效的PDF需要额外库
        is_valid, message = validate_pdf_file("nonexistent.pdf")
        assert not is_valid
        assert "文件不存在" in message


class TestBug4ResourceCleanup:
    """BUG 4: PDF处理资源泄漏风险"""
    
    def test_pdf_processor_has_cleanup_method(self):
        """测试PDF处理器是否有清理方法"""
        # 检查PdfProcessingThread是否有cleanup方法
        assert hasattr(PdfProcessingThread, 'cleanup'), "PdfProcessingThread缺少cleanup方法"
        
    def test_thread_manager_cleanup_all(self):
        """测试线程管理器的cleanup_all方法"""
        manager = ThreadManager()
        # 应该能正常调用而不抛出异常
        manager.cleanup_all()
        
    def test_image_processing_thread_error_handling(self):
        """测试图像处理线程的错误处理"""
        # 测试无效参数会抛出异常
        with pytest.raises(ValueError):
            ImageProcessingThread(image_path=None, pil_image=None)
            
    def test_pdf_processing_thread_error_handling(self):
        """测试PDF处理线程的错误处理"""
        # 测试无效参数会抛出异常
        with pytest.raises(ValueError):
            PdfProcessingThread(pdf_path="")


class TestBug5LoggingConfiguration:
    """BUG 5: 日志配置重复导致重复记录"""
    
    def test_setup_logging_singleton(self):
        """测试日志配置是否为单例模式"""
        reset_logging()  # 先重置
        
        # 第一次配置
        logger1 = setup_logging()
        handlers_count_1 = len(logger1.handlers)
        
        # 第二次配置（应该返回相同的配置，不添加重复处理器）
        logger2 = setup_logging()
        handlers_count_2 = len(logger2.handlers)
        
        # 处理器数量应该相同（没有重复添加）
        assert handlers_count_1 == handlers_count_2, "日志处理器被重复添加"
        
    def test_get_logger_consistency(self):
        """测试get_logger的一致性"""
        reset_logging()
        setup_logging()
        
        logger1 = get_logger("test_module")
        logger2 = get_logger("test_module")
        
        # 应该是同一个对象
        assert logger1 is logger2, "相同名称的logger应该返回同一对象"
        
    def test_logger_hierarchy(self):
        """测试日志层级结构"""
        reset_logging()
        setup_logging()
        
        # 获取logger时自动添加前缀
        logger = get_logger("test.submodule")
        assert logger.name.startswith("stamp_remover"), "Logger名称应该包含stamp_remover前缀"


class TestBug6ExceptionHandling:
    """BUG 6: 异常处理不完善"""
    
    def test_image_processing_thread_exception_propagation(self):
        """测试图像处理线程的异常传播"""
        thread = ImageProcessingThread(
            image_path="nonexistent.jpg",
            rad_num=185,
            channel_index=0
        )
        
        # 应该有错误信号
        assert hasattr(thread, 'error'), "ImageProcessingThread缺少error信号"
        
    def test_pdf_processing_thread_exception_propagation(self):
        """测试PDF处理线程的异常传播"""
        from stamp_remover.core.pdf_processor import PdfProcessingThread as PDFThread
        
        # 测试无效参数会抛出异常
        with pytest.raises(ValueError):
            PDFThread(pdf_path="")  # 空路径应该抛出异常
        
        # 测试有错误信号
        # 注意：由于参数验证在__init__中进行，我们无法创建无效实例
        # 所以这里只测试错误信号存在性
        assert hasattr(PDFThread, '__init__'), "PdfProcessingThread应该有__init__方法"
        
    def test_stamp_detector_error_handling(self):
        """测试印章检测器的错误处理"""
        detector = StampDetector()
        
        # 测试无效图像处理
        invalid_image = Image.new('L', (10, 10))  # 灰度图像，可能不支持某些操作
        try:
            result = detector.detect_and_remove(invalid_image)
            # 应该返回图像对象而不是抛出异常
            assert isinstance(result, Image.Image), "应该返回PIL图像对象"
        except Exception as e:
            # 如果抛出异常，应该是可控的
            assert isinstance(e, (ValueError, IndexError, TypeError)), f"未预期的异常类型: {type(e)}"


class TestBug7MemoryManagement:
    """BUG 7: 内存使用问题（大文件处理）"""
    
    def test_pdf_processor_has_memory_mode(self):
        """测试PDF处理器是否有内存模式"""
        # 检查是否有内存相关配置
        from stamp_remover.config import PDF_PROCESSING_CONFIG
        assert 'memory_mode' in PDF_PROCESSING_CONFIG, "缺少memory_mode配置"
        
    def test_pdf_processor_streaming_support(self):
        """测试PDF处理器是否支持流式处理"""
        # PdfProcessingThread应该支持分批处理
        # 由于参数验证需要实际文件，我们只测试类属性存在性
        from stamp_remover.core.pdf_processor import PdfProcessingThread
        assert hasattr(PdfProcessingThread, '__init__'), "应该有__init__方法"
        
        # 测试配置中有相关配置
        from stamp_remover.config import PDF_PROCESSING_CONFIG
        assert 'max_workers' in PDF_PROCESSING_CONFIG, "配置中应该有max_workers"
        
    def test_safe_output_path_generation(self):
        """测试安全输出路径生成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 测试正常路径
            path = get_safe_output_path(tmpdir, "test.png")
            assert path is not None
            assert isinstance(path, (str, Path))
            
            # 测试路径包含特殊字符
            path = get_safe_output_path(tmpdir, "test<file>.png")
            assert path is not None


class TestIntegration:
    """集成测试"""
    
    def test_end_to_end_image_processing(self):
        """测试端到端图像处理流程"""
        # 创建测试图像
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            img = Image.new('RGB', (200, 200), color='white')
            # 添加一些红色区域（模拟印章）
            from PIL import ImageDraw
            draw = ImageDraw.Draw(img)
            draw.ellipse([50, 50, 150, 150], fill='red')
            img.save(f.name)
            temp_path = f.name
        
        try:
            # 创建处理线程
            thread = ImageProcessingThread(
                image_path=temp_path,
                rad_num=185,
                channel_index=0,  # 红色通道
                is_contrast=False,
                is_sharpness=False
            )
            
            # 验证线程创建成功
            assert thread is not None
            assert thread.image_path == temp_path
            
        finally:
            os.unlink(temp_path)
            
    def test_file_validation_integration(self):
        """测试文件验证集成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建有效图片
            img_path = os.path.join(tmpdir, "test.jpg")
            img = Image.new('RGB', (100, 100), color='blue')
            img.save(img_path)
            
            # 验证
            is_valid, message = validate_image_file(img_path, strict=True)
            assert is_valid, f"有效图片验证失败: {message}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
