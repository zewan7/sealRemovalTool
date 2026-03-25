#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF处理核心模块
"""

from PySide6.QtCore import QThread, Signal
import fitz
import tempfile
import os
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
from PIL import Image
import gc

from ..utils.logging_config import get_logger
from ..utils.memory_manager import MemoryManager, estimate_pdf_page_memory_size, force_garbage_collection

logger = get_logger(__name__)

DEFAULT_BATCH_SIZE = 10
MAX_MEMORY_MB = 500.0


class PdfProcessingThread(QThread):
    """PDF处理线程"""
    
    finished = Signal(list)
    progress = Signal(int, int)
    error = Signal(str)
    status = Signal(str)

    def __init__(self, pdf_path: str, dpi: int = 150, max_pages: Optional[int] = None, 
                 max_workers: int = 4, batch_size: int = DEFAULT_BATCH_SIZE):
        super().__init__()
        self.pdf_path = pdf_path
        self.dpi = dpi
        self.max_pages = max_pages
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.temp_dir = None
        self._is_cancelled = False
        self._doc = None
        self._memory_manager = MemoryManager(max_memory_mb=MAX_MEMORY_MB)
        
        self._validate_parameters()

    def _validate_parameters(self):
        """验证输入参数"""
        if not self.pdf_path:
            raise ValueError("PDF路径不能为空")
        
        if not os.path.exists(self.pdf_path):
            raise ValueError(f"PDF文件不存在: {self.pdf_path}")
        
        if not (50 <= self.dpi <= 600):
            raise ValueError("DPI必须在50-600范围内")
        
        if self.max_pages is not None and self.max_pages <= 0:
            raise ValueError("最大页数必须大于0")
        
        if self.max_workers <= 0:
            raise ValueError("工作线程数必须大于0")
        
        if self.batch_size <= 0:
            raise ValueError("批处理大小必须大于0")

    def _process_single_page(self, page_num: int, doc_ref) -> Tuple[int, Optional[bytes]]:
        """处理单个页面"""
        if self._is_cancelled:
            return page_num, None
            
        pix = None
        try:
            page = doc_ref.load_page(page_num)
            pix = page.get_pixmap(dpi=self.dpi)
            img_data = pix.tobytes("png")
            
            logger.info(f"第 {page_num + 1} 页处理完成")
            return page_num, img_data
            
        except Exception as e:
            logger.error(f"处理第 {page_num + 1} 页时出错: {e}")
            return page_num, None
        finally:
            if pix is not None:
                try:
                    del pix
                except Exception:
                    pass

    def run(self):
        """执行PDF处理"""
        doc = None
        try:
            logger.info(f"开始处理PDF: {self.pdf_path}")
            self.status.emit("正在处理PDF...")
            
            doc = fitz.open(self.pdf_path)
            self._doc = doc
            total_pages = len(doc)
            
            if self.max_pages:
                total_pages = min(total_pages, self.max_pages)
            
            logger.info(f"PDF总页数: {len(doc)}, 将处理: {total_pages} 页")
            
            self.progress.emit(0, total_pages)
            
            output_images = []
            
            for batch_start in range(0, total_pages, self.batch_size):
                if self._is_cancelled:
                    logger.info("PDF处理被取消")
                    break
                
                batch_end = min(batch_start + self.batch_size, total_pages)
                logger.info(f"处理批次: {batch_start + 1} - {batch_end} 页")
                
                self._memory_manager.reset()
                
                for i in range(batch_start, batch_end):
                    if self._is_cancelled:
                        break
                        
                    try:
                        page = doc.load_page(i)
                        rect = page.rect
                        estimated_size = estimate_pdf_page_memory_size(
                            rect.width, rect.height, self.dpi
                        )
                        
                        if not self._memory_manager.can_allocate(estimated_size):
                            logger.warning(f"内存不足，跳过第 {i + 1} 页")
                            self.progress.emit(i + 1, total_pages)
                            continue
                        
                        self._memory_manager.allocate(estimated_size)
                        
                        page_num, img_data = self._process_single_page(i, doc)
                        if img_data is not None:
                            output_images.append((page_num, img_data))
                            self._memory_manager.release(estimated_size * 0.5)
                        
                        self.progress.emit(i + 1, total_pages)
                        logger.info(f"第 {i + 1} 页处理完成，进度: {i + 1}/{total_pages}")
                        
                    except Exception as e:
                        logger.error(f"处理第 {i + 1} 页时出错: {e}")
                        continue
                
                force_garbage_collection()
            
            output_images.sort(key=lambda x: x[0])
            image_data_list = [img_data for _, img_data in output_images if img_data is not None]
            
            if image_data_list:
                logger.info(f"PDF处理完成，共生成 {len(image_data_list)} 张图片")
                self.progress.emit(total_pages, total_pages)
                self.status.emit("处理完成")
                self.finished.emit(image_data_list)
            else:
                logger.warning("PDF处理完成，但没有生成任何图片")
                self.status.emit("处理完成")
                self.finished.emit([])
                
        except Exception as e:
            logger.error(f"PDF处理失败: {e}")
            self.error.emit(str(e))
            self.status.emit("处理失败")
            self.finished.emit([])
            
        finally:
            self._cleanup_resources()

    def _cleanup_resources(self):
        """清理资源"""
        if self._doc is not None:
            try:
                self._doc.close()
            except Exception:
                pass
            self._doc = None
        
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
                logger.info(f"清理临时目录: {self.temp_dir}")
            except Exception as e:
                logger.error(f"清理临时目录失败: {e}")
        
        self._memory_manager.reset()
        force_garbage_collection()

    def cancel(self):
        """取消处理"""
        self._is_cancelled = True

    def cleanup(self):
        """清理临时文件"""
        self._cleanup_resources()

    def __del__(self):
        """析构函数，确保清理临时文件"""
        self._cleanup_resources()


class PdfRegenerationThread(QThread):
    """PDF重新生成线程 - 多线程印章去除 + PDF组合"""
    
    finished = Signal(bool, str)
    progress = Signal(int, int)
    error = Signal(str)

    def __init__(self, pdf_images_data: List[bytes], save_path: str, 
                 threshold: int = 185, channel_index: int = 0,
                 enable_contrast: bool = False, enable_sharpness: bool = False,
                 max_workers: int = 4, batch_size: int = DEFAULT_BATCH_SIZE):
        super().__init__()
        self.pdf_images_data = pdf_images_data
        self.save_path = save_path
        self.threshold = threshold
        self.channel_index = channel_index
        self.enable_contrast = enable_contrast
        self.enable_sharpness = enable_sharpness
        self.max_workers = max_workers
        self.batch_size = batch_size
        self._is_cancelled = False
        self._memory_manager = MemoryManager(max_memory_mb=MAX_MEMORY_MB)
        
        self._validate_parameters()

    def _validate_parameters(self):
        """验证输入参数"""
        if not self.pdf_images_data:
            raise ValueError("PDF图片数据不能为空")
        
        if not self.save_path:
            raise ValueError("保存路径不能为空")
        
        if not (0 <= self.threshold <= 255):
            raise ValueError("阈值必须在0-255范围内")
        
        if self.channel_index < 0:
            raise ValueError("通道索引不能为负数")
        
        if self.max_workers <= 0:
            raise ValueError("工作线程数必须大于0")

    def _process_single_image(self, page_num: int, img_data: bytes) -> Tuple[int, Optional[Image.Image]]:
        """处理单个图像"""
        if self._is_cancelled:
            return page_num, None
            
        pil_img = None
        result_img = None
        try:
            pil_img = Image.open(io.BytesIO(img_data))
            
            if self.enable_contrast:
                from PIL import ImageEnhance
                pil_img = ImageEnhance.Contrast(pil_img).enhance(2.0)
            
            if self.enable_sharpness:
                from PIL import ImageEnhance
                pil_img = ImageEnhance.Sharpness(pil_img).enhance(2.0)
            
            import numpy as np
            np_img = np.array(pil_img)
            
            if len(np_img.shape) == 3:
                channels = np_img.shape[2]
                
                if self.channel_index >= channels:
                    channel_idx = 0
                else:
                    channel_idx = self.channel_index
                
                mask = np_img[:, :, channel_idx] >= self.threshold
                
                if channels == 3:
                    white = [255, 255, 255]
                elif channels == 4:
                    white = [255, 255, 255, 255]
                else:
                    white = [255] * channels
                
                np_img[mask] = white
            
            result_img = Image.fromarray(np_img)
            
            logger.info(f"第 {page_num + 1} 页印章去除完成")
            return page_num, result_img
            
        except Exception as e:
            logger.error(f"处理第 {page_num + 1} 页时出错: {e}")
            return page_num, None
        finally:
            if pil_img is not None:
                try:
                    pil_img.close()
                except Exception:
                    pass

    def run(self):
        """执行PDF重新生成"""
        try:
            total_pages = len(self.pdf_images_data)
            logger.info(f"开始PDF重新生成，共 {total_pages} 页")
            
            self.progress.emit(0, total_pages)
            
            processed_images = []
            
            for batch_start in range(0, total_pages, self.batch_size):
                if self._is_cancelled:
                    logger.info("PDF重新生成被取消")
                    break
                
                batch_end = min(batch_start + self.batch_size, total_pages)
                logger.info(f"处理批次: {batch_start + 1} - {batch_end} 页")
                
                self._memory_manager.reset()
                
                for i in range(batch_start, batch_end):
                    if self._is_cancelled:
                        break
                        
                    try:
                        img_data = self.pdf_images_data[i]
                        estimated_size = len(img_data) / (1024 * 1024) * 3
                        
                        if not self._memory_manager.can_allocate(estimated_size):
                            logger.warning(f"内存不足，跳过第 {i + 1} 页")
                            self.progress.emit(i + 1, total_pages)
                            continue
                        
                        self._memory_manager.allocate(estimated_size)
                        
                        page_num, result_img = self._process_single_image(i, img_data)
                        if result_img is not None:
                            processed_images.append((page_num, result_img))
                            self._memory_manager.release(estimated_size * 0.5)
                        
                        self.progress.emit(i + 1, total_pages)
                        logger.info(f"第 {i + 1} 页处理完成，进度: {i + 1}/{total_pages}")
                        
                    except Exception as e:
                        logger.error(f"处理第 {i + 1} 页时出错: {e}")
                        continue
                
                force_garbage_collection()
            
            processed_images.sort(key=lambda x: x[0])
            final_images = [img for _, img in processed_images if img is not None]
            
            logger.info("开始组合PDF文件...")
            self._combine_images_to_pdf(final_images)
            
            self.finished.emit(True, self.save_path)
            logger.info(f"PDF重新生成完成: {self.save_path}")
            
        except Exception as e:
            logger.error(f"PDF重新生成失败: {e}")
            self.error.emit(str(e))
            self.finished.emit(False, self.save_path)
        finally:
            self._memory_manager.reset()
            force_garbage_collection()

    def _combine_images_to_pdf(self, images):
        """将图像组合成PDF文件"""
        rgb_images = []
        try:
            for img in images:
                if img is None:
                    continue
                if img.mode != 'RGB':
                    rgb_images.append(img.convert('RGB'))
                else:
                    rgb_images.append(img)
            
            if rgb_images:
                first_image = rgb_images[0]
                other_images = rgb_images[1:]
                
                first_image.save(
                    self.save_path,
                    save_all=True,
                    append_images=other_images,
                    author="Stamp Remover",
                    title="Processed Document"
                )
                
                logger.info(f"PDF文件保存成功: {self.save_path}")
            else:
                raise ValueError("没有可用的图像数据")
                
        finally:
            for img in rgb_images:
                try:
                    img.close()
                except Exception:
                    pass

    def cancel(self):
        """取消处理"""
        self._is_cancelled = True

    def cleanup(self):
        """清理资源"""
        self._memory_manager.reset()
        force_garbage_collection()

    def __del__(self):
        """析构函数"""
        self.cleanup()


class PdfPageData:
    """PDF页面数据类，用于在内存中存储图片数据"""
    
    def __init__(self, page_num: int, image_data: bytes, dpi: int = 150):
        self.page_num = page_num
        self.image_data = image_data
        self.dpi = dpi
        self._pil_image = None
    
    def get_pil_image(self) -> Image.Image:
        """获取PIL图像对象"""
        if self._pil_image is None:
            self._pil_image = Image.open(io.BytesIO(self.image_data))
        return self._pil_image
    
    def get_qpixmap(self):
        """获取QPixmap对象（用于Qt显示）"""
        from PySide6.QtGui import QPixmap
        from PIL.ImageQt import ImageQt
        
        pil_img = self.get_pil_image()
        if pil_img.mode != 'RGBA':
            pil_img = pil_img.convert('RGBA')
        
        qimage = ImageQt(pil_img)
        return QPixmap.fromImage(qimage)
    
    def get_size(self) -> Tuple[int, int]:
        """获取图像尺寸"""
        return self.get_pil_image().size
    
    def clear_cache(self):
        """清除缓存的PIL图像"""
        if self._pil_image is not None:
            try:
                self._pil_image.close()
            except Exception:
                pass
            self._pil_image = None
    
    def __len__(self) -> int:
        """返回图像数据的字节数"""
        return len(self.image_data)
    
    def __del__(self):
        """析构函数"""
        self.clear_cache()
