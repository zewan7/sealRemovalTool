#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辅助工具函数
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import List, Tuple, Optional
from PIL import Image
import fitz  # PyMuPDF
import logging

logger = logging.getLogger(__name__)


def get_supported_formats() -> Tuple[List[str], List[str]]:
    """获取支持的图片和PDF格式"""
    image_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif']
    pdf_formats = ['.pdf']
    return image_formats, pdf_formats


def validate_image_file(file_path: str) -> Tuple[bool, str]:
    """验证图片文件"""
    if not os.path.exists(file_path):
        return False, "文件不存在"
    
    if not os.path.isfile(file_path):
        return False, "不是有效的文件"
    
    # 检查文件大小
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        return False, "文件为空"
    
    # 严格检查文件扩展名（包括大小写变体）
    file_path_lower = file_path.lower()
    image_formats, _ = get_supported_formats()
    
    # 检查是否有支持的扩展名
    has_valid_ext = False
    for ext in image_formats:
        if file_path_lower.endswith(ext):
            has_valid_ext = True
            break
    
    if not has_valid_ext:
        _, ext = os.path.splitext(file_path)
        return False, f"不支持的图片格式: {ext}"
    
    # 尝试打开图片验证格式（更严格的内容验证）
    try:
        with Image.open(file_path) as img:
            # 验证图片模式
            if img.mode not in ['RGB', 'RGBA', 'L', 'P']:
                return False, f"不支持的图片模式: {img.mode}"
            
            # 验证图片尺寸
            if img.size[0] <= 0 or img.size[1] <= 0:
                return False, "图片尺寸无效"
            
            # 验证图片尺寸限制（防止超大图片）
            max_dimension = 20000  # 最大20000像素
            if img.size[0] > max_dimension or img.size[1] > max_dimension:
                return False, f"图片尺寸过大: {img.size}（最大支持{max_dimension}像素）"
            
            # 尝试验证图片完整性
            try:
                img.verify()
            except Exception:
                return False, "图片文件损坏或不完整"
            
            return True, "验证通过"
    except Exception as e:
        return False, f"图片文件验证失败: {str(e)}"


def validate_pdf_file(file_path: str) -> Tuple[bool, str]:
    """验证PDF文件"""
    if not os.path.exists(file_path):
        return False, "文件不存在"
    
    if not os.path.isfile(file_path):
        return False, "不是有效的文件"
    
    # 检查文件大小
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        return False, "文件为空"
    
    # 严格检查文件扩展名（包括大小写变体）
    file_path_lower = file_path.lower()
    _, pdf_formats = get_supported_formats()
    
    has_valid_ext = False
    for ext in pdf_formats:
        if file_path_lower.endswith(ext):
            has_valid_ext = True
            break
    
    if not has_valid_ext:
        _, ext = os.path.splitext(file_path)
        return False, f"不支持的PDF格式: {ext}"
    
    # 验证PDF文件头（防止伪装的PDF文件）
    try:
        with open(file_path, 'rb') as f:
            header = f.read(5)
            if header != b'%PDF-':
                return False, "不是有效的PDF文件格式"
    except Exception as e:
        return False, f"读取文件头失败: {str(e)}"
    
    # 尝试打开PDF验证格式
    try:
        doc = fitz.open(file_path)
        page_count = len(doc)
        
        if page_count <= 0:
            doc.close()
            return False, "PDF文件没有有效页面"
        
        # 检查每个页面是否可访问
        for i in range(min(page_count, 10)):  # 只检查前10页
            try:
                page = doc.load_page(i)
                _ = page.get_text()  # 尝试读取页面内容
            except Exception as e:
                doc.close()
                return False, f"PDF第{i+1}页损坏: {str(e)}"
        
        doc.close()
        return True, f"验证通过，共 {page_count} 页"
    except Exception as e:
        return False, f"PDF文件验证失败: {str(e)}"


def create_temp_directory(prefix: str = "stamp_remover_") -> str:
    """创建临时目录"""
    try:
        temp_dir = tempfile.mkdtemp(prefix=prefix)
        logger.info(f"创建临时目录: {temp_dir}")
        return temp_dir
    except Exception as e:
        logger.error(f"创建临时目录失败: {e}")
        raise


def cleanup_temp_files(temp_dir: str) -> bool:
    """清理临时文件"""
    if not temp_dir or not os.path.exists(temp_dir):
        return True
    
    try:
        shutil.rmtree(temp_dir)
        logger.info(f"清理临时目录: {temp_dir}")
        return True
    except Exception as e:
        logger.error(f"清理临时目录失败: {e}")
        return False


def get_file_size_mb(file_path: str) -> float:
    """获取文件大小（MB）"""
    try:
        size_bytes = os.path.getsize(file_path)
        return size_bytes / (1024 * 1024)
    except Exception:
        return 0.0


def is_large_file(file_path: str, threshold_mb: float = 100.0) -> bool:
    """检查是否为大文件"""
    size_mb = get_file_size_mb(file_path)
    return size_mb > threshold_mb


def get_image_info(image_path: str) -> dict:
    """获取图片信息"""
    try:
        with Image.open(image_path) as img:
            return {
                'mode': img.mode,
                'size': img.size,
                'format': img.format,
                'width': img.width,
                'height': img.height,
                'channels': len(img.mode) if img.mode in ['RGB', 'RGBA'] else 1
            }
    except Exception as e:
        logger.error(f"获取图片信息失败: {e}")
        return {}


def get_pdf_info(pdf_path: str) -> dict:
    """获取PDF信息"""
    try:
        doc = fitz.open(pdf_path)
        info = {
            'page_count': len(doc),
            'metadata': doc.metadata,
            'file_size_mb': get_file_size_mb(pdf_path)
        }
        doc.close()
        return info
    except Exception as e:
        logger.error(f"获取PDF信息失败: {e}")
        return {}


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小显示"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"

