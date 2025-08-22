#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基本功能测试
"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from stamp_remover.core import ImageProcessingThread, PdfProcessingThread, ThreadManager
from stamp_remover.utils.helpers import (
    get_supported_formats, validate_image_file, validate_pdf_file,
    create_temp_directory, cleanup_temp_files
)


class TestHelpers:
    """测试辅助函数"""
    
    def test_get_supported_formats(self):
        """测试获取支持的格式"""
        image_formats, pdf_formats = get_supported_formats()
        
        assert '.jpg' in image_formats
        assert '.png' in image_formats
        assert '.pdf' in pdf_formats
        assert len(image_formats) > 0
        assert len(pdf_formats) > 0
    
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


class TestThreadManager:
    """测试线程管理器"""
    
    def test_thread_manager_creation(self):
        """测试线程管理器创建"""
        manager = ThreadManager()
        assert manager is not None
        assert hasattr(manager, 'register_thread')
        assert hasattr(manager, 'start_thread')
        assert hasattr(manager, 'stop_thread')
    
    def test_thread_manager_cleanup(self):
        """测试线程管理器清理"""
        manager = ThreadManager()
        manager.cleanup_all()  # 应该不会出错
        assert True


class TestImageProcessingThread:
    """测试图像处理线程"""
    
    def test_thread_creation(self):
        """测试线程创建"""
        # 注意：这里需要提供一个有效的图片路径进行测试
        # 在实际测试中，应该创建测试图片文件
        pass
    
    def test_invalid_parameters(self):
        """测试无效参数"""
        with pytest.raises(ValueError):
            ImageProcessingThread(image_path="", rad_num=300)  # 无效路径和阈值
        
        with pytest.raises(ValueError):
            ImageProcessingThread(image_path="test.jpg", rad_num=-1)  # 无效阈值


class TestPdfProcessingThread:
    """测试PDF处理线程"""
    
    def test_thread_creation(self):
        """测试线程创建"""
        # 注意：这里需要提供一个有效的PDF路径进行测试
        # 在实际测试中，应该创建测试PDF文件
        pass
    
    def test_invalid_parameters(self):
        """测试无效参数"""
        with pytest.raises(ValueError):
            PdfProcessingThread(pdf_path="", dpi=100)  # 无效路径
        
        with pytest.raises(ValueError):
            PdfProcessingThread(pdf_path="test.pdf", dpi=1000)  # 无效DPI


if __name__ == '__main__':
    pytest.main([__file__])

