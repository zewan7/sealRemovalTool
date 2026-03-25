#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF处理核心模块
"""

from PySide6.QtCore import QThread, Signal
import fitz  # PyMuPDF
import tempfile
import os
from typing import List, Optional, Tuple, Generator
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
from PIL import Image
import time
import concurrent.futures
import gc

from .stamp_detector import AdvancedStampRemover
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PdfProcessingThread(QThread):
    """PDF处理线程 - 使用流式处理避免内存溢出"""
    
    # 信号定义
    finished = Signal(list)           # 处理完成，传递图片数据列表
    progress = Signal(int, int)       # 当前进度，总页数
    error = Signal(str)               # 错误信息
    status = Signal(str)              # 状态信息

    def __init__(self, pdf_path: str, dpi: int = 150, max_pages: Optional[int] = None, 
                 max_workers: int = 4, memory_limit_mb: float = 500.0):
        super().__init__()
        self.pdf_path = pdf_path
        self.dpi = dpi
        self.max_pages = max_pages
        self.max_workers = max_workers
        self.memory_limit_mb = memory_limit_mb
        self._doc: Optional[fitz.Document] = None
        self._is_cancelled = False
        
        # 验证参数
        self._validate_parameters()

    def _validate_parameters(self):
        """验证输入参数"""
        if not self.pdf_path:
            raise ValueError("PDF路径不能为空")
        
        if not os.path.exists(self.pdf_path):
            raise ValueError(f"PDF文件不存在: {self.pdf_path}")
        
        # 严格的文件扩展名检查
        _, ext = os.path.splitext(self.pdf_path.lower())
        if ext != '.pdf':
            raise ValueError(f"不支持的文件格式: {ext}，仅支持.pdf格式")
        
        # 验证文件大小
        file_size_mb = os.path.getsize(self.pdf_path) / (1024 * 1024)
        if file_size_mb > 1024:  # 1GB限制
            logger.warning(f"PDF文件较大: {file_size_mb:.1f}MB，处理可能需要较长时间")
        
        if not (50 <= self.dpi <= 600):
            raise ValueError("DPI必须在50-600范围内")
        
        if self.max_pages is not None and self.max_pages <= 0:
            raise ValueError("最大页数必须大于0")
        
        if self.max_workers <= 0:
            raise ValueError("工作线程数必须大于0")

    def _process_single_page(self, page_num: int) -> Tuple[int, bytes]:
        """处理单个页面（用于多线程）"""
        doc = None
        try:
            # 在线程中打开文档的副本
            doc = fitz.open(self.pdf_path)
            page = doc.load_page(page_num)
            
            # 转换为图片
            pix = page.get_pixmap(dpi=self.dpi)
            
            # 将图片数据转换为字节流
            img_data = pix.tobytes("png")
            
            logger.info(f"第 {page_num + 1} 页处理完成")
            return page_num, img_data
            
        except Exception as e:
            logger.error(f"处理第 {page_num + 1} 页时出错: {e}")
            raise e
        finally:
            # 确保资源被释放
            if doc is not None:
                try:
                    doc.close()
                except:
                    pass

    def run(self):
        """执行PDF处理 - 流式处理避免内存溢出"""
        doc = None
        try:
            logger.info(f"开始处理PDF: {self.pdf_path}")
            self.status.emit("正在处理PDF...")
            
            # 打开PDF文档
            doc = fitz.open(self.pdf_path)
            total_pages = len(doc)
            
            if self.max_pages:
                total_pages = min(total_pages, self.max_pages)
            
            logger.info(f"PDF总页数: {len(doc)}, 将处理: {total_pages} 页")
            
            # 发送初始进度
            self.progress.emit(0, total_pages)
            
            # 检查是否需要流式处理（大文件）
            file_size_mb = os.path.getsize(self.pdf_path) / (1024 * 1024)
            use_streaming = file_size_mb > self.memory_limit_mb or total_pages > 50
            
            if use_streaming:
                logger.info(f"使用流式处理模式（文件大小: {file_size_mb:.1f}MB）")
                output_images = self._process_streaming(total_pages)
            else:
                logger.info("使用内存处理模式")
                output_images = self._process_in_memory(total_pages)
            
            # 按页面顺序排序结果
            output_images.sort(key=lambda x: x[0])
            image_data_list = [img_data for _, img_data in output_images]
            
            if image_data_list:
                logger.info(f"PDF处理完成，共生成 {len(image_data_list)} 张图片")
                # 发送最终进度
                self.progress.emit(total_pages, total_pages)
                # 只发送完成状态，不发送详细信息
                self.status.emit("处理完成")
                self.finished.emit(image_data_list)
            else:
                logger.warning("PDF处理完成，但没有生成任何图片")
                self.status.emit("处理完成")
                self.finished.emit([])
                
        except Exception as e:
            logger.error(f"PDF处理失败: {e}")
            self.error.emit(str(e))
            # 只发送错误状态
            self.status.emit("处理失败")
            self.finished.emit([])
            
        finally:
            # 确保资源被释放
            if doc is not None:
                try:
                    doc.close()
                    logger.info("PDF文档已关闭")
                except Exception as e:
                    logger.error(f"关闭PDF文档失败: {e}")
            
            # 强制垃圾回收
            gc.collect()

    def _process_in_memory(self, total_pages: int) -> List[Tuple[int, bytes]]:
        """内存处理模式 - 适用于小文件"""
        output_images = []
        
        if self.max_workers > 1:
            # 多线程模式
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # 提交所有任务
                future_to_page = {
                    executor.submit(self._process_single_page, i): i 
                    for i in range(total_pages)
                }
                
                # 收集结果
                for future in concurrent.futures.as_completed(future_to_page):
                    if self._is_cancelled:
                        executor.shutdown(wait=False)
                        break
                    
                    page_num = future_to_page[future]
                    try:
                        page_num, img_data = future.result()
                        output_images.append((page_num, img_data))
                        self.progress.emit(len(output_images), total_pages)
                    except Exception as e:
                        logger.error(f"处理第 {page_num + 1} 页时出错: {e}")
        else:
            # 单线程模式
            for i in range(total_pages):
                if self._is_cancelled:
                    break
                try:
                    page_num, img_data = self._process_single_page(i)
                    output_images.append((page_num, img_data))
                    self.progress.emit(i + 1, total_pages)
                except Exception as e:
                    logger.error(f"处理第 {i + 1} 页时出错: {e}")
        
        return output_images

    def _process_streaming(self, total_pages: int) -> List[Tuple[int, bytes]]:
        """流式处理模式 - 适用于大文件，分批处理"""
        output_images = []
        batch_size = 10  # 每批处理10页
        
        for batch_start in range(0, total_pages, batch_size):
            if self._is_cancelled:
                break
            
            batch_end = min(batch_start + batch_size, total_pages)
            logger.info(f"处理批次: {batch_start + 1} - {batch_end}")
            
            batch_images = []
            
            if self.max_workers > 1:
                # 多线程处理批次
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    future_to_page = {
                        executor.submit(self._process_single_page, i): i 
                        for i in range(batch_start, batch_end)
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_page):
                        page_num = future_to_page[future]
                        try:
                            page_num, img_data = future.result()
                            batch_images.append((page_num, img_data))
                        except Exception as e:
                            logger.error(f"处理第 {page_num + 1} 页时出错: {e}")
            else:
                # 单线程处理批次
                for i in range(batch_start, batch_end):
                    try:
                        page_num, img_data = self._process_single_page(i)
                        batch_images.append((page_num, img_data))
                    except Exception as e:
                        logger.error(f"处理第 {i + 1} 页时出错: {e}")
            
            # 添加到总结果
            output_images.extend(batch_images)
            self.progress.emit(len(output_images), total_pages)
            
            # 每批处理后强制垃圾回收
            gc.collect()
            logger.info(f"批次 {batch_start + 1} - {batch_end} 完成，已处理 {len(output_images)}/{total_pages} 页")
        
        return output_images

    def cancel(self):
        """取消处理"""
        self._is_cancelled = True
        logger.info("PDF处理已取消")

    def cleanup(self):
        """清理资源"""
        self.cancel()
        gc.collect()


class PdfRegenerationThread(QThread):
    """PDF重新生成线程 - 多线程印章去除 + PDF组合，支持流式处理"""
    
    # 信号定义
    finished = Signal(bool, str)      # 处理完成，成功标志和保存路径
    progress = Signal(int, int)       # 当前进度，总页数
    error = Signal(str)               # 错误信息

    def __init__(self, pdf_images_data: List[bytes], save_path: str, 
                 threshold: int = 185, channel_index: int = 0,
                 enable_contrast: bool = False, enable_sharpness: bool = False,
                 max_workers: int = 4, use_streaming: bool = False):
        super().__init__()
        self.pdf_images_data = pdf_images_data
        self.save_path = save_path
        self.threshold = threshold
        self.channel_index = channel_index
        self.enable_contrast = enable_contrast
        self.enable_sharpness = enable_sharpness
        self.max_workers = max_workers
        self.use_streaming = use_streaming
        self._is_cancelled = False
        
        # 验证参数
        self._validate_parameters()

    def _validate_parameters(self):
        """验证输入参数"""
        if not self.pdf_images_data:
            raise ValueError("PDF图片数据不能为空")
        
        if not self.save_path:
            raise ValueError("保存路径不能为空")
        
        # 严格的文件扩展名检查
        _, ext = os.path.splitext(self.save_path.lower())
        if ext != '.pdf':
            logger.warning(f"保存路径扩展名不正确: {ext}，将自动添加.pdf")
            self.save_path = self.save_path + '.pdf'
        
        if not (0 <= self.threshold <= 255):
            raise ValueError("阈值必须在0-255范围内")
        
        if self.channel_index < 0:
            raise ValueError("通道索引不能为负数")
        
        if self.max_workers <= 0:
            raise ValueError("工作线程数必须大于0")

    def _process_single_image(self, args: Tuple[int, bytes]) -> Tuple[int, Image.Image]:
        """处理单个图像（用于多线程）"""
        page_num, img_data = args
        pil_img = None
        result_image = None
        
        try:
            # 从字节数据创建PIL图像
            pil_img = Image.open(io.BytesIO(img_data))
            
            # 应用图像增强
            if self.enable_contrast:
                from PIL import ImageEnhance
                pil_img = ImageEnhance.Contrast(pil_img).enhance(2.0)
            
            if self.enable_sharpness:
                from PIL import ImageEnhance
                pil_img = ImageEnhance.Sharpness(pil_img).enhance(2.0)
            
            # 使用高级印章去除算法
            remover = AdvancedStampRemover(
                method='auto',
                threshold=self.threshold,
                channel_index=self.channel_index,
                min_stamp_size=100,
                max_stamp_size=1000000,
                color_tolerance=30,
                edge_threshold=0.1
            )
            result_image = remover.remove_stamp(pil_img)
            
            logger.info(f"第 {page_num + 1} 页印章去除完成")
            return page_num, result_image
            
        except Exception as e:
            logger.error(f"处理第 {page_num + 1} 页时出错: {e}")
            raise e
        finally:
            # 清理资源
            if pil_img is not None:
                pil_img.close()

    def run(self):
        """执行PDF重新生成"""
        try:
            total_pages = len(self.pdf_images_data)
            logger.info(f"开始PDF重新生成，共 {total_pages} 页")
            
            # 发送初始进度
            self.progress.emit(0, total_pages)
            
            # 准备图像数据
            images_data = [(i, img_data) for i, img_data in enumerate(self.pdf_images_data)]
            processed_images = []
            
            if self.use_streaming and total_pages > 20:
                # 流式处理模式
                logger.info("使用流式处理模式")
                self._process_streaming(images_data, total_pages, processed_images)
            else:
                # 内存处理模式
                if self.max_workers > 1:
                    self._process_images_multithreaded(images_data, total_pages, processed_images)
                else:
                    self._process_images_singlethreaded(images_data, total_pages, processed_images)
            
            # 按页面顺序排序结果
            processed_images.sort(key=lambda x: x[0])
            final_images = [img for _, img in processed_images]
            
            if not final_images:
                raise ValueError("没有成功处理任何图像")
            
            # 组合成PDF
            logger.info("开始组合PDF文件...")
            self._combine_images_to_pdf(final_images)
            
            # 发送完成信号
            self.finished.emit(True, self.save_path)
            logger.info(f"PDF重新生成完成: {self.save_path}")
            
        except Exception as e:
            logger.error(f"PDF重新生成失败: {e}")
            self.error.emit(str(e))
            self.finished.emit(False, self.save_path)
        finally:
            # 强制垃圾回收
            gc.collect()

    def _process_images_singlethreaded(self, images_data, total_pages, processed_images):
        """单线程处理图像"""
        for i, (page_num, img_data) in enumerate(images_data):
            if self._is_cancelled:
                break
            try:
                page_num, result_img = self._process_single_image((page_num, img_data))
                processed_images.append((page_num, result_img))
                
                # 发送进度
                self.progress.emit(i + 1, total_pages)
                logger.info(f"第 {page_num + 1} 页处理完成，进度: {i + 1}/{total_pages}")
                
            except Exception as e:
                logger.error(f"处理第 {page_num + 1} 页时出错: {e}")
                continue

    def _process_images_multithreaded(self, images_data, total_pages, processed_images):
        """多线程处理图像"""
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_page = {
                executor.submit(self._process_single_image, img_data): img_data[0] 
                for img_data in images_data
            }
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_page):
                if self._is_cancelled:
                    executor.shutdown(wait=False)
                    break
                
                page_num = future_to_page[future]
                try:
                    page_num, result_img = future.result()
                    processed_images.append((page_num, result_img))
                    
                    # 发送进度
                    self.progress.emit(len(processed_images), total_pages)
                    logger.info(f"第 {page_num + 1} 页处理完成，总进度: {len(processed_images)}/{total_pages}")
                    
                except Exception as e:
                    logger.error(f"处理第 {page_num + 1} 页时出错: {e}")

    def _process_streaming(self, images_data, total_pages, processed_images):
        """流式处理图像 - 分批处理避免内存溢出"""
        batch_size = 5  # 每批处理5页
        
        for batch_start in range(0, total_pages, batch_size):
            if self._is_cancelled:
                break
            
            batch_end = min(batch_start + batch_size, total_pages)
            batch_data = images_data[batch_start:batch_end]
            
            logger.info(f"处理批次: {batch_start + 1} - {batch_end}")
            
            batch_images = []
            
            if self.max_workers > 1:
                with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                    future_to_page = {
                        executor.submit(self._process_single_image, img_data): img_data[0] 
                        for img_data in batch_data
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_page):
                        page_num = future_to_page[future]
                        try:
                            page_num, result_img = future.result()
                            batch_images.append((page_num, result_img))
                        except Exception as e:
                            logger.error(f"处理第 {page_num + 1} 页时出错: {e}")
            else:
                for img_data in batch_data:
                    try:
                        page_num, result_img = self._process_single_image(img_data)
                        batch_images.append((page_num, result_img))
                    except Exception as e:
                        logger.error(f"处理第 {img_data[0] + 1} 页时出错: {e}")
            
            processed_images.extend(batch_images)
            self.progress.emit(len(processed_images), total_pages)
            
            # 每批处理后强制垃圾回收
            gc.collect()

    def _combine_images_to_pdf(self, images):
        """将图像组合成PDF文件"""
        try:
            # 确保所有图像都是RGB模式
            rgb_images = []
            for img in images:
                if img.mode != 'RGB':
                    rgb_images.append(img.convert('RGB'))
                else:
                    rgb_images.append(img)
            
            # 使用第一张图为基准，其他图像追加
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
                
        except Exception as e:
            logger.error(f"PDF组合失败: {e}")
            raise e

    def cancel(self):
        """取消处理"""
        self._is_cancelled = True
        logger.info("PDF重新生成已取消")

    def cleanup(self):
        """清理资源"""
        self.cancel()
        gc.collect()


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
            # 从字节数据创建PIL图像
            self._pil_image = Image.open(io.BytesIO(self.image_data))
        return self._pil_image
    
    def get_qpixmap(self):
        """获取QPixmap对象（用于Qt显示）"""
        from PySide6.QtGui import QPixmap
        from PIL.ImageQt import ImageQt
        
        pil_img = self.get_pil_image()
        # 转换为RGBA模式以确保兼容性
        if pil_img.mode != 'RGBA':
            pil_img = pil_img.convert('RGBA')
        
        # 通过PIL.ImageQt转换为QPixmap
        qimage = ImageQt(pil_img)
        return QPixmap.fromImage(qimage)
    
    def get_size(self) -> Tuple[int, int]:
        """获取图像尺寸"""
        return self.get_pil_image().size
    
    def __len__(self) -> int:
        """返回图像数据的字节数"""
        return len(self.image_data)
    
    def cleanup(self):
        """清理资源"""
        if self._pil_image is not None:
            self._pil_image.close()
            self._pil_image = None
