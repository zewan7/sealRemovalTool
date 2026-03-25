#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
辅助工具函数
"""

import os
import tempfile
import shutil
from pathlib import Path
from typing import List, Tuple, Optional, Set
from PIL import Image
import fitz
import logging

from .logging_config import get_logger
logger = get_logger(__name__)

_SUPPORTED_IMAGE_EXTENSIONS: Set[str] = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif'}
_SUPPORTED_PDF_EXTENSIONS: Set[str] = {'.pdf'}
_SUPPORTED_IMAGE_MIME_TYPES: Set[str] = {'jpeg', 'png', 'bmp', 'tiff'}


def _detect_image_type(file_path: str) -> Optional[str]:
    """通过文件头检测图片类型（替代已废弃的imghdr模块）"""
    try:
        with open(file_path, 'rb') as f:
            header = f.read(32)
        
        if header.startswith(b'\x89PNG\r\n\x1a\n'):
            return 'png'
        elif header.startswith(b'\xff\xd8\xff'):
            return 'jpeg'
        elif header.startswith(b'BM'):
            return 'bmp'
        elif header.startswith(b'II') or header.startswith(b'MM'):
            return 'tiff'
        elif header.startswith(b'GIF'):
            return 'gif'
        elif header.startswith(b'%PDF'):
            return 'pdf'
        
        return None
    except Exception:
        return None


def get_supported_formats() -> Tuple[List[str], List[str]]:
    """获取支持的图片和PDF格式"""
    return list(_SUPPORTED_IMAGE_EXTENSIONS), list(_SUPPORTED_PDF_EXTENSIONS)


def normalize_extension(ext: str) -> str:
    """规范化文件扩展名"""
    if not ext:
        return ''
    ext = ext.lower().strip()
    if not ext.startswith('.'):
        ext = '.' + ext
    return ext


def is_valid_image_extension(file_path: str) -> Tuple[bool, str]:
    """检查文件扩展名是否为支持的图片格式"""
    _, ext = os.path.splitext(file_path.lower())
    ext = normalize_extension(ext)
    
    if not ext:
        return False, "文件没有扩展名"
    
    if ext not in _SUPPORTED_IMAGE_EXTENSIONS:
        supported = ', '.join(_SUPPORTED_IMAGE_EXTENSIONS)
        return False, f"不支持的图片扩展名: {ext}，支持的格式: {supported}"
    
    return True, "扩展名有效"


def is_valid_pdf_extension(file_path: str) -> Tuple[bool, str]:
    """检查文件扩展名是否为支持的PDF格式"""
    _, ext = os.path.splitext(file_path.lower())
    ext = normalize_extension(ext)
    
    if not ext:
        return False, "文件没有扩展名"
    
    if ext not in _SUPPORTED_PDF_EXTENSIONS:
        supported = ', '.join(_SUPPORTED_PDF_EXTENSIONS)
        return False, f"不支持的PDF扩展名: {ext}，支持的格式: {supported}"
    
    return True, "扩展名有效"


def verify_file_content_type(file_path: str, expected_type: str) -> Tuple[bool, str]:
    """验证文件实际内容类型（防止扩展名伪造）"""
    if not os.path.exists(file_path):
        return False, "文件不存在"
    
    try:
        if expected_type == 'image':
            detected_type = _detect_image_type(file_path)
            if detected_type is None:
                return False, "无法识别文件格式，可能不是有效的图片文件"
            
            if detected_type == 'pdf':
                return False, "文件实际是PDF格式，不是图片"
            
            if detected_type in _SUPPORTED_IMAGE_MIME_TYPES:
                return True, f"检测到有效的图片格式: {detected_type}"
            else:
                return False, f"检测到不支持的图片格式: {detected_type}"
                
        elif expected_type == 'pdf':
            with open(file_path, 'rb') as f:
                header = f.read(5)
                if header == b'%PDF-':
                    return True, "检测到有效的PDF格式"
                else:
                    return False, "文件不是有效的PDF格式"
        
        return False, f"未知的预期类型: {expected_type}"
        
    except Exception as e:
        return False, f"验证文件内容失败: {str(e)}"


def validate_image_file(file_path: str, verify_content: bool = True) -> Tuple[bool, str]:
    """验证图片文件"""
    if not file_path:
        return False, "文件路径为空"
    
    if not os.path.exists(file_path):
        return False, "文件不存在"
    
    if not os.path.isfile(file_path):
        return False, "不是有效的文件"
    
    valid_ext, ext_msg = is_valid_image_extension(file_path)
    if not valid_ext:
        return False, ext_msg
    
    if verify_content:
        valid_content, content_msg = verify_file_content_type(file_path, 'image')
        if not valid_content:
            return False, content_msg
    
    try:
        with Image.open(file_path) as img:
            img.verify()
        
        with Image.open(file_path) as img:
            if img.mode not in ['RGB', 'RGBA', 'L', 'P', 'LA']:
                return False, f"不支持的图片模式: {img.mode}"
            
            if img.size[0] <= 0 or img.size[1] <= 0:
                return False, "图片尺寸无效"
            
            return True, "验证通过"
            
    except Exception as e:
        return False, f"图片文件损坏或格式无效: {str(e)}"


def validate_pdf_file(file_path: str, verify_content: bool = True) -> Tuple[bool, str]:
    """验证PDF文件"""
    if not file_path:
        return False, "文件路径为空"
    
    if not os.path.exists(file_path):
        return False, "文件不存在"
    
    if not os.path.isfile(file_path):
        return False, "不是有效的文件"
    
    valid_ext, ext_msg = is_valid_pdf_extension(file_path)
    if not valid_ext:
        return False, ext_msg
    
    if verify_content:
        valid_content, content_msg = verify_file_content_type(file_path, 'pdf')
        if not valid_content:
            return False, content_msg
    
    doc = None
    try:
        doc = fitz.open(file_path)
        page_count = len(doc)
        
        if page_count <= 0:
            return False, "PDF文件没有有效页面"
        
        return True, f"验证通过，共 {page_count} 页"
        
    except Exception as e:
        return False, f"PDF文件损坏或格式无效: {str(e)}"
        
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass


def validate_file_for_processing(file_path: str, file_type: str = 'auto') -> Tuple[bool, str, str]:
    """验证文件是否可以处理
    
    Args:
        file_path: 文件路径
        file_type: 文件类型 ('image', 'pdf', 'auto')
    
    Returns:
        (是否有效, 消息, 检测到的文件类型)
    """
    if not file_path:
        return False, "文件路径为空", ""
    
    if not os.path.exists(file_path):
        return False, "文件不存在", ""
    
    if not os.path.isfile(file_path):
        return False, "不是有效的文件", ""
    
    _, ext = os.path.splitext(file_path.lower())
    ext = normalize_extension(ext)
    
    detected_type = ""
    
    if file_type == 'auto':
        if ext in _SUPPORTED_IMAGE_EXTENSIONS:
            detected_type = 'image'
        elif ext in _SUPPORTED_PDF_EXTENSIONS:
            detected_type = 'pdf'
        else:
            supported = ', '.join(_SUPPORTED_IMAGE_EXTENSIONS | _SUPPORTED_PDF_EXTENSIONS)
            return False, f"不支持的文件格式: {ext}，支持的格式: {supported}", ""
    elif file_type == 'image':
        detected_type = 'image'
        if ext not in _SUPPORTED_IMAGE_EXTENSIONS:
            return False, f"不是有效的图片格式: {ext}", ""
    elif file_type == 'pdf':
        detected_type = 'pdf'
        if ext not in _SUPPORTED_PDF_EXTENSIONS:
            return False, f"不是有效的PDF格式: {ext}", ""
    else:
        return False, f"未知的文件类型参数: {file_type}", ""
    
    if detected_type == 'image':
        valid, msg = validate_image_file(file_path)
        return valid, msg, detected_type
    elif detected_type == 'pdf':
        valid, msg = validate_pdf_file(file_path)
        return valid, msg, detected_type
    
    return False, "未知错误", ""


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
    doc = None
    try:
        doc = fitz.open(pdf_path)
        info = {
            'page_count': len(doc),
            'metadata': doc.metadata,
            'file_size_mb': get_file_size_mb(pdf_path)
        }
        return info
    except Exception as e:
        logger.error(f"获取PDF信息失败: {e}")
        return {}
    finally:
        if doc is not None:
            try:
                doc.close()
            except Exception:
                pass


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

