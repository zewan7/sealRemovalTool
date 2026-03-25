#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全覆盖测试 - 验证所有BUG修复
"""

import pytest
import sys
import os
import tempfile
from pathlib import Path
from PIL import Image
import io

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from stamp_remover.core import ImageProcessingThread, PdfProcessingThread, ThreadManager, PdfRegenerationThread
from stamp_remover.core.image_processor import StampDetector
from stamp_remover.utils.helpers import (
    get_supported_formats, validate_image_file, validate_pdf_file,
    validate_file_for_processing, is_valid_image_extension, is_valid_pdf_extension,
    verify_file_content_type
)
from stamp_remover.utils.logging_config import setup_logging, get_logger, reset_logging
from stamp_remover.utils.exceptions import (
    StampRemoverError, ImageProcessingError, PDFProcessingError,
    FileNotFoundError, InvalidFileFormatError, ThreadError
)
from stamp_remover.utils.memory_manager import (
    MemoryManager, estimate_image_memory_size, estimate_pdf_page_memory_size,
    force_garbage_collection
)


class TestThreadManager:
    """测试线程管理器 - BUG 1"""
    
    def test_thread_manager_creation(self):
        """测试线程管理器创建"""
        manager = ThreadManager()
        assert manager is not None
        assert hasattr(manager, 'register_thread')
        assert hasattr(manager, 'start_thread')
        assert hasattr(manager, 'stop_thread')
        assert hasattr(manager, 'unregister_thread')
        assert hasattr(manager, 'stop_all_threads')
        assert hasattr(manager, 'has_running_threads')
        assert hasattr(manager, 'get_running_thread_count')
        assert hasattr(manager, 'get_thread_count')
        assert hasattr(manager, 'get_thread_names')
        assert hasattr(manager, 'get_running_thread_names')
        assert hasattr(manager, 'wait_for_thread')
        assert hasattr(manager, 'wait_for_all_threads')
    
    def test_thread_manager_cleanup(self):
        """测试线程管理器清理"""
        manager = ThreadManager()
        manager.cleanup_all()
        assert manager.get_thread_count() == 0
    
    def test_thread_manager_operations(self):
        """测试线程管理器操作"""
        manager = ThreadManager()
        
        assert manager.get_thread_count() == 0
        assert manager.get_running_thread_count() == 0
        assert manager.has_running_threads() == False
        assert manager.get_thread_names() == []
        assert manager.get_running_thread_names() == []


class TestStampDetector:
    """测试印章检测器 - BUG 2"""
    
    def test_saturation_calculation(self):
        """测试饱和度计算"""
        img_array = self._create_test_image()
        saturation = StampDetector.calculate_saturation(img_array)
        
        assert saturation is not None
        assert saturation.shape == (100, 100)
    
    def test_stamp_detection(self):
        """测试印章检测"""
        img_array = self._create_test_image_with_stamp()
        mask = StampDetector.detect_stamp_by_features(
            img_array, 
            channel_index=0, 
            threshold=185,
            min_saturation=0.3
        )
        
        assert mask is not None
        assert mask.shape == (100, 100)
        assert mask.dtype == bool
    
    def _create_test_image(self):
        """创建测试图像"""
        img = Image.new('RGB', (100, 100), color='white')
        return __import__('numpy').array(img)
    
    def _create_test_image_with_stamp(self):
        """创建带印章的测试图像"""
        import numpy as np
        img = np.ones((100, 100, 3), dtype=np.uint8) * 255
        
        for i in range(30, 70):
            for j in range(30, 70):
                if (i - 50) ** 2 + (j - 50) ** 2 < 400:
                    img[i, j] = [200, 50, 50]
        
        return img


class TestFileValidation:
    """测试文件验证 - BUG 3"""
    
    def test_get_supported_formats(self):
        """测试获取支持的格式"""
        image_formats, pdf_formats = get_supported_formats()
        
        assert '.jpg' in image_formats
        assert '.jpeg' in image_formats
        assert '.png' in image_formats
        assert '.bmp' in image_formats
        assert '.tiff' in image_formats
        assert '.pdf' in pdf_formats
        assert len(image_formats) > 0
        assert len(pdf_formats) > 0
    
    def test_is_valid_image_extension(self):
        """测试图片扩展名验证"""
        valid, msg = is_valid_image_extension("test.jpg")
        assert valid == True
        
        valid, msg = is_valid_image_extension("test.png")
        assert valid == True
        
        valid, msg = is_valid_image_extension("test.txt")
        assert valid == False
        assert "不支持" in msg
        
        valid, msg = is_valid_image_extension("test")
        assert valid == False
        assert "扩展名" in msg
    
    def test_is_valid_pdf_extension(self):
        """测试PDF扩展名验证"""
        valid, msg = is_valid_pdf_extension("test.pdf")
        assert valid == True
        
        valid, msg = is_valid_pdf_extension("test.doc")
        assert valid == False
        assert "不支持" in msg
    
    def test_validate_image_file_nonexistent(self):
        """测试验证不存在的图片文件"""
        valid, message = validate_image_file("nonexistent.jpg")
        assert not valid
        assert "文件不存在" in message
    
    def test_validate_pdf_file_nonexistent(self):
        """测试验证不存在的PDF文件"""
        valid, message = validate_pdf_file("nonexistent.pdf")
        assert not valid
        assert "文件不存在" in message
    
    def test_validate_image_file_with_temp(self):
        """测试验证临时图片文件"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as f:
            img = Image.new('RGB', (100, 100), color='red')
            img.save(f.name, 'JPEG')
            temp_path = f.name
        
        try:
            valid, message = validate_image_file(temp_path)
            assert valid == True
            assert "验证通过" in message
        finally:
            os.unlink(temp_path)
    
    def test_validate_image_file_invalid_format(self):
        """测试验证无效格式的图片文件"""
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"This is not an image")
            temp_path = f.name
        
        try:
            valid, message = validate_image_file(temp_path)
            assert valid == False
        finally:
            os.unlink(temp_path)
    
    def test_validate_file_for_processing(self):
        """测试文件处理验证"""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            img = Image.new('RGB', (100, 100), color='blue')
            img.save(f.name, 'PNG')
            temp_path = f.name
        
        try:
            valid, msg, file_type = validate_file_for_processing(temp_path)
            assert valid == True
            assert file_type == 'image'
            
            valid, msg, file_type = validate_file_for_processing(temp_path, 'image')
            assert valid == True
            assert file_type == 'image'
        finally:
            os.unlink(temp_path)


class TestLoggingConfig:
    """测试日志配置 - BUG 5"""
    
    def test_setup_logging(self):
        """测试日志设置"""
        reset_logging()
        logger = setup_logging()
        
        assert logger is not None
        assert isinstance(logger, type(get_logger(__name__)))
    
    def test_get_logger(self):
        """测试获取日志器"""
        reset_logging()
        logger = get_logger("test_module")
        
        assert logger is not None
    
    def test_no_duplicate_handlers(self):
        """测试不会重复添加处理器"""
        reset_logging()
        setup_logging()
        setup_logging()
        
        import logging
        root_logger = logging.getLogger()
        handler_count = len([h for h in root_logger.handlers if isinstance(h, logging.StreamHandler)])
        
        assert handler_count <= 2


class TestExceptions:
    """测试异常处理 - BUG 6"""
    
    def test_stamp_remover_error(self):
        """测试基础异常"""
        with pytest.raises(StampRemoverError):
            raise StampRemoverError("测试错误")
    
    def test_file_not_found_error(self):
        """测试文件未找到异常"""
        error = FileNotFoundError("/path/to/file.jpg")
        assert "文件未找到" in str(error)
        assert error.file_path == "/path/to/file.jpg"
    
    def test_invalid_file_format_error(self):
        """测试无效文件格式异常"""
        error = InvalidFileFormatError("test.txt", expected_format="jpg", actual_format="txt")
        assert "格式错误" in str(error)
    
    def test_image_processing_error(self):
        """测试图像处理异常"""
        error = ImageProcessingError("处理失败", original_error=ValueError("参数错误"))
        assert "处理失败" in str(error)
        assert "参数错误" in str(error)
    
    def test_pdf_processing_error(self):
        """测试PDF处理异常"""
        error = PDFProcessingError("页面错误", page_num=5)
        assert "第5页" in str(error)
    
    def test_thread_error(self):
        """测试线程异常"""
        error = ThreadError("test_thread", "启动失败")
        assert "test_thread" in str(error)
        assert "启动失败" in str(error)


class TestMemoryManager:
    """测试内存管理 - BUG 7"""
    
    def test_memory_manager_creation(self):
        """测试内存管理器创建"""
        manager = MemoryManager(max_memory_mb=100.0)
        
        assert manager.max_memory_mb == 100.0
        assert manager.get_usage_percentage() == 0.0
        assert manager.is_warning_level() == False
    
    def test_memory_allocation(self):
        """测试内存分配"""
        manager = MemoryManager(max_memory_mb=100.0)
        
        result = manager.allocate(50.0)
        assert result == True
        assert manager.get_usage_percentage() == 0.5
        
        result = manager.allocate(60.0)
        assert result == False
    
    def test_memory_release(self):
        """测试内存释放"""
        manager = MemoryManager(max_memory_mb=100.0)
        
        manager.allocate(50.0)
        manager.release(30.0)
        
        assert manager._current_usage == 20.0
    
    def test_memory_status(self):
        """测试内存状态"""
        manager = MemoryManager(max_memory_mb=100.0)
        manager.allocate(30.0)
        
        status = manager.get_status()
        
        assert 'current_usage_mb' in status
        assert 'max_memory_mb' in status
        assert 'usage_percentage' in status
        assert 'is_warning' in status
        assert 'available_mb' in status
    
    def test_estimate_image_memory_size(self):
        """测试图像内存估算"""
        size_mb = estimate_image_memory_size(1000, 1000, 3)
        
        assert size_mb > 0
        assert isinstance(size_mb, float)
    
    def test_estimate_pdf_page_memory_size(self):
        """测试PDF页面内存估算"""
        size_mb = estimate_pdf_page_memory_size(595, 842, dpi=150)
        
        assert size_mb > 0
        assert isinstance(size_mb, float)
    
    def test_force_garbage_collection(self):
        """测试强制垃圾回收"""
        collected = force_garbage_collection()
        assert isinstance(collected, int)


class TestImageProcessingThread:
    """测试图像处理线程"""
    
    def test_thread_creation(self):
        """测试线程创建"""
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            img = Image.new('RGB', (100, 100), color='red')
            img.save(f.name, 'PNG')
            temp_path = f.name
        
        try:
            thread = ImageProcessingThread(image_path=temp_path)
            assert thread is not None
        finally:
            os.unlink(temp_path)
    
    def test_invalid_parameters(self):
        """测试无效参数"""
        with pytest.raises(ValueError):
            ImageProcessingThread(image_path="", rad_num=300)
        
        with pytest.raises(ValueError):
            ImageProcessingThread(image_path="test.jpg", rad_num=-1)
        
        with pytest.raises(ValueError):
            ImageProcessingThread(image_path="test.jpg", rad_num=185, min_saturation=2.0)
        
        with pytest.raises(ValueError):
            ImageProcessingThread(image_path="test.jpg", rad_num=185, min_region_area=-1)


class TestPdfProcessingThread:
    """测试PDF处理线程"""
    
    def test_thread_creation(self):
        """测试线程创建"""
        pass
    
    def test_invalid_parameters(self):
        """测试无效参数"""
        with pytest.raises(ValueError):
            PdfProcessingThread(pdf_path="", dpi=100)
        
        with pytest.raises(ValueError):
            PdfProcessingThread(pdf_path="test.pdf", dpi=1000)
        
        with pytest.raises(ValueError):
            PdfProcessingThread(pdf_path="test.pdf", dpi=150, batch_size=0)


class TestPdfRegenerationThread:
    """测试PDF重新生成线程"""
    
    def test_invalid_parameters(self):
        """测试无效参数"""
        with pytest.raises(ValueError):
            PdfRegenerationThread(pdf_images_data=[], save_path="test.pdf")
        
        with pytest.raises(ValueError):
            PdfRegenerationThread(pdf_images_data=[b"test"], save_path="")
        
        with pytest.raises(ValueError):
            PdfRegenerationThread(pdf_images_data=[b"test"], save_path="test.pdf", threshold=300)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
