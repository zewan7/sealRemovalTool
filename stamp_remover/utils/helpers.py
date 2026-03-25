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
import fitz  # PyMuPDF
import mimetypes

from .logger import get_logger

logger = get_logger(__name__)


# 支持的图片格式（扩展名和MIME类型）
SUPPORTED_IMAGE_EXTENSIONS: Set[str] = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.gif', '.webp'}
SUPPORTED_IMAGE_MIMETYPES: Set[str] = {
    'image/jpeg', 'image/png', 'image/bmp', 'image/tiff', 
    'image/gif', 'image/webp'
}

# 支持的PDF格式
SUPPORTED_PDF_EXTENSIONS: Set[str] = {'.pdf'}
SUPPORTED_PDF_MIMETYPES: Set[str] = {'application/pdf'}


def get_supported_formats() -> Tuple[List[str], List[str]]:
    """获取支持的图片和PDF格式"""
    image_formats = list(SUPPORTED_IMAGE_EXTENSIONS)
    pdf_formats = list(SUPPORTED_PDF_EXTENSIONS)
    return image_formats, pdf_formats


def validate_file_extension(file_path: str, allowed_extensions: Set[str]) -> bool:
    """
    验证文件扩展名是否在允许的集合中
    
    Args:
        file_path: 文件路径
        allowed_extensions: 允许的扩展名集合
        
    Returns:
        是否有效
    """
    if not file_path:
        return False
    
    _, ext = os.path.splitext(file_path.lower())
    return ext in allowed_extensions


def validate_mime_type(file_path: str, allowed_mimetypes: Set[str]) -> Tuple[bool, str]:
    """
    验证文件的MIME类型
    
    Args:
        file_path: 文件路径
        allowed_mimetypes: 允许的MIME类型集合
        
    Returns:
        (是否有效, MIME类型或错误信息)
    """
    try:
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type is None:
            return False, "无法识别文件类型"
        
        if mime_type not in allowed_mimetypes:
            return False, f"不支持的MIME类型: {mime_type}"
        
        return True, mime_type
    except Exception as e:
        return False, f"MIME类型检测失败: {str(e)}"


def validate_image_file(file_path: str, strict: bool = True) -> Tuple[bool, str]:
    """
    验证图片文件
    
    Args:
        file_path: 文件路径
        strict: 是否进行严格验证（包括MIME类型和文件头）
        
    Returns:
        (是否有效, 验证信息)
    """
    # 检查文件是否存在
    if not os.path.exists(file_path):
        return False, "文件不存在"
    
    if not os.path.isfile(file_path):
        return False, "不是有效的文件"
    
    # 检查文件扩展名
    if not validate_file_extension(file_path, SUPPORTED_IMAGE_EXTENSIONS):
        _, ext = os.path.splitext(file_path.lower())
        return False, f"不支持的图片格式: {ext}，支持的格式: {', '.join(SUPPORTED_IMAGE_EXTENSIONS)}"
    
    # 严格验证：检查MIME类型
    if strict:
        is_valid, mime_result = validate_mime_type(file_path, SUPPORTED_IMAGE_MIMETYPES)
        if not is_valid:
            return False, mime_result
    
    # 尝试打开图片验证格式
    try:
        with Image.open(file_path) as img:
            # 验证图片模式
            if img.mode not in ['RGB', 'RGBA', 'L', 'P', 'LA']:
                return False, f"不支持的图片模式: {img.mode}"
            
            # 验证图片尺寸
            if img.size[0] <= 0 or img.size[1] <= 0:
                return False, "图片尺寸无效"
            
            # 验证图片数据完整性
            img.load()
            
            return True, f"验证通过，格式: {img.format}, 模式: {img.mode}, 尺寸: {img.size}"
    except Image.UnidentifiedImageError:
        return False, "无法识别的图片格式，文件可能已损坏"
    except Image.DecompressionBombError:
        return False, "图片尺寸过大，可能存在安全风险"
    except Exception as e:
        return False, f"图片文件损坏: {str(e)}"


def validate_pdf_file(file_path: str, strict: bool = True) -> Tuple[bool, str]:
    """
    验证PDF文件
    
    Args:
        file_path: 文件路径
        strict: 是否进行严格验证
        
    Returns:
        (是否有效, 验证信息)
    """
    # 检查文件是否存在
    if not os.path.exists(file_path):
        return False, "文件不存在"
    
    if not os.path.isfile(file_path):
        return False, "不是有效的文件"
    
    # 检查文件扩展名
    if not validate_file_extension(file_path, SUPPORTED_PDF_EXTENSIONS):
        _, ext = os.path.splitext(file_path.lower())
        return False, f"不支持的PDF格式: {ext}，仅支持.pdf格式"
    
    # 严格验证：检查MIME类型
    if strict:
        is_valid, mime_result = validate_mime_type(file_path, SUPPORTED_PDF_MIMETYPES)
        if not is_valid:
            return False, mime_result
    
    # 尝试打开PDF验证格式
    doc = None
    try:
        doc = fitz.open(file_path)
        page_count = len(doc)
        
        if page_count <= 0:
            return False, "PDF文件没有有效页面"
        
        # 检查PDF是否加密
        if doc.is_encrypted:
            return False, "PDF文件已加密，无法处理"
        
        return True, f"验证通过，共 {page_count} 页"
        
    except fitz.FileDataError:
        return False, "PDF文件格式错误或已损坏"
    except fitz.EmptyFileError:
        return False, "PDF文件为空"
    except Exception as e:
        return False, f"PDF文件损坏: {str(e)}"
    finally:
        if doc is not None:
            try:
                doc.close()
            except:
                pass


def sanitize_filename(filename: str) -> str:
    """
    清理文件名，移除非法字符
    
    Args:
        filename: 原始文件名
        
    Returns:
        清理后的文件名
    """
    # Windows非法字符: < > : " / \ | ? *
    illegal_chars = '<>:"/\\|?*'
    for char in illegal_chars:
        filename = filename.replace(char, '_')
    
    # 移除控制字符
    filename = ''.join(char for char in filename if ord(char) >= 32)
    
    # 限制长度
    if len(filename) > 200:
        name, ext = os.path.splitext(filename)
        filename = name[:200 - len(ext)] + ext
    
    return filename.strip()


def get_safe_output_path(input_path: str, suffix: str = "_processed", 
                         output_dir: Optional[str] = None) -> str:
    """
    生成安全的输出路径
    
    Args:
        input_path: 输入文件路径
        suffix: 文件名后缀
        output_dir: 输出目录（可选）
        
    Returns:
        安全的输出路径
    """
    input_path = Path(input_path)
    
    # 确定输出目录
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    else:
        output_dir = input_path.parent
    
    # 生成输出文件名
    stem = input_path.stem
    suffix = sanitize_filename(suffix)
    ext = input_path.suffix
    
    output_name = f"{stem}{suffix}{ext}"
    output_path = output_dir / output_name
    
    # 如果文件已存在，添加序号
    counter = 1
    while output_path.exists():
        output_name = f"{stem}{suffix}_{counter}{ext}"
        output_path = output_dir / output_name
        counter += 1
    
    return str(output_path)


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
                'channels': len(img.mode) if img.mode in ['RGB', 'RGBA'] else 1,
                'file_size_mb': get_file_size_mb(image_path)
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
            'file_size_mb': get_file_size_mb(pdf_path),
            'is_encrypted': doc.is_encrypted
        }
        return info
    except Exception as e:
        logger.error(f"获取PDF信息失败: {e}")
        return {}
    finally:
        if doc is not None:
            try:
                doc.close()
            except:
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


def check_disk_space(path: str, required_mb: float = 100.0) -> Tuple[bool, str]:
    """
    检查磁盘空间
    
    Args:
        path: 路径
        required_mb: 需要的空间（MB）
        
    Returns:
        (是否足够, 信息)
    """
    try:
        import shutil
        total, used, free = shutil.disk_usage(path)
        free_mb = free / (1024 * 1024)
        
        if free_mb < required_mb:
            return False, f"磁盘空间不足，需要 {required_mb:.1f}MB，可用 {free_mb:.1f}MB"
        
        return True, f"磁盘空间充足，可用 {free_mb:.1f}MB"
    except Exception as e:
        return False, f"检查磁盘空间失败: {str(e)}"


def safe_remove_file(file_path: str) -> bool:
    """
    安全地删除文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        是否成功
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"删除文件: {file_path}")
            return True
        return True  # 文件不存在也算成功
    except Exception as e:
        logger.error(f"删除文件失败 {file_path}: {e}")
        return False
