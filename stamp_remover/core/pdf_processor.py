#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF处理核心模块
"""

from PySide6.QtCore import QThread, Signal
import fitz  # PyMuPDF
import tempfile
import os
import logging
from typing import List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
from PIL import Image
import time
import concurrent.futures

logger = logging.getLogger(__name__)


class PdfProcessingThread(QThread):
    """PDF处理线程"""
    
    # 信号定义
    finished = Signal(list)           # 处理完成，传递图片数据列表
    progress = Signal(int, int)       # 当前进度，总页数
    error = Signal(str)               # 错误信息
    status = Signal(str)              # 状态信息

    def __init__(self, pdf_path: str, dpi: int = 150, max_pages: Optional[int] = None, 
                 max_workers: int = 4):
        super().__init__()
        self.pdf_path = pdf_path
        self.dpi = dpi
        self.max_pages = max_pages
        self.max_workers = max_workers
        self.temp_dir = None
        
        # 验证参数
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

    def _process_single_page(self, args: Tuple[int, fitz.Page]) -> Tuple[int, bytes]:
        """处理单个页面（用于多线程）"""
        page_num, page = args
        try:
            # 转换为图片
            pix = page.get_pixmap(dpi=self.dpi)
            
            # 将图片数据转换为字节流，而不是保存到文件
            img_data = pix.tobytes("png")
            
            logger.info(f"第 {page_num + 1} 页处理完成")
            return page_num, img_data
            
        except Exception as e:
            logger.error(f"处理第 {page_num + 1} 页时出错: {e}")
            raise e

    def run(self):
        """执行PDF处理"""
        try:
            logger.info(f"开始处理PDF: {self.pdf_path}")
            # 只发送一次开始状态
            self.status.emit("正在处理PDF...")
            
            # 打开PDF文档
            doc = fitz.open(self.pdf_path)
            total_pages = len(doc)
            
            if self.max_pages:
                total_pages = min(total_pages, self.max_pages)
            
            logger.info(f"PDF总页数: {len(doc)}, 将处理: {total_pages} 页")
            
            # 发送初始进度
            self.progress.emit(0, total_pages)
            
            # 准备页面数据
            pages_data = []
            for i in range(total_pages):
                page = doc.load_page(i)
                pages_data.append((i, page))
            
            output_images = []
            processed_count = 0
            
            if self.max_workers > 1:
                # 多线程模式：使用改进的进度跟踪
                self._process_multithreaded(pages_data, total_pages, output_images)
            else:
                # 单线程模式：顺序处理，进度准确
                self._process_singlethreaded(pages_data, total_pages, output_images)
            
            # 关闭文档
            doc.close()
            
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
            # 清理资源
            if hasattr(self, 'doc') and self.doc:
                try:
                    self.doc.close()
                except:
                    pass

    def _process_singlethreaded(self, pages_data, total_pages, output_images):
        """单线程处理，进度准确"""
        for i, (page_num, page) in enumerate(pages_data):
            try:
                page_num, img_data = self._process_single_page((page_num, page))
                output_images.append((page_num, img_data))
                
                # 发送准确进度
                self.progress.emit(i + 1, total_pages)
                logger.info(f"第 {page_num + 1} 页处理完成，进度: {i + 1}/{total_pages}")
                
            except Exception as e:
                logger.error(f"处理第 {page_num + 1} 页时出错: {e}")
                continue

    def _process_multithreaded(self, pages_data, total_pages, output_images):
        """多线程处理，使用改进的进度跟踪"""
        # 创建任务队列
        task_queue = pages_data.copy()
        completed_tasks = []
        active_tasks = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 初始提交任务
            for _ in range(min(self.max_workers, len(task_queue))):
                if task_queue:
                    page_data = task_queue.pop(0)
                    future = executor.submit(self._process_single_page, page_data)
                    active_tasks[future] = page_data
            
            # 处理完成的任务并提交新任务
            while active_tasks:
                # 等待任意一个任务完成
                done, _ = concurrent.futures.wait(
                    active_tasks.keys(), 
                    return_when=concurrent.futures.FIRST_COMPLETED
                )
                
                for future in done:
                    try:
                        page_num, img_data = future.result()
                        completed_tasks.append((page_num, img_data))
                        
                        # 从活动任务中移除
                        del active_tasks[future]
                        
                        # 发送进度（基于完成的任务数量）
                        progress = len(completed_tasks)
                        self.progress.emit(progress, total_pages)
                        
                        logger.info(f"第 {page_num + 1} 页处理完成，总进度: {progress}/{total_pages}")
                        
                    except Exception as e:
                        page_data = active_tasks[future]
                        page_num = page_data[0]
                        logger.error(f"处理第 {page_num + 1} 页时出错: {e}")
                        del active_tasks[future]
                    
                    # 提交新任务
                    if task_queue:
                        new_page_data = task_queue.pop(0)
                        new_future = executor.submit(self._process_single_page, new_page_data)
                        active_tasks[new_future] = new_page_data
        
        # 将完成的任务添加到输出列表
        output_images.extend(completed_tasks)

    def cleanup(self):
        """清理临时文件（现在主要用于清理其他可能的临时资源）"""
        if self.temp_dir and os.path.exists(self.temp_dir):
            try:
                import shutil
                shutil.rmtree(self.temp_dir)
                logger.info(f"清理临时目录: {self.temp_dir}")
            except Exception as e:
                logger.error(f"清理临时目录失败: {e}")

    def __del__(self):
        """析构函数，确保清理临时文件"""
        self.cleanup()


class PdfRegenerationThread(QThread):
    """PDF重新生成线程 - 多线程印章去除 + PDF组合"""
    
    # 信号定义
    finished = Signal(bool, str)      # 处理完成，成功标志和保存路径
    progress = Signal(int, int)       # 当前进度，总页数
    error = Signal(str)               # 错误信息

    def __init__(self, pdf_images_data: List[bytes], save_path: str, 
                 threshold: int = 185, channel_index: int = 0,
                 enable_contrast: bool = False, enable_sharpness: bool = False,
                 max_workers: int = 4):
        super().__init__()
        self.pdf_images_data = pdf_images_data
        self.save_path = save_path
        self.threshold = threshold
        self.channel_index = channel_index
        self.enable_contrast = enable_contrast
        self.enable_sharpness = enable_sharpness
        self.max_workers = max_workers
        
        # 验证参数
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

    def _process_single_image(self, args: Tuple[int, bytes]) -> Tuple[int, Image.Image]:
        """处理单个图像（用于多线程）"""
        page_num, img_data = args
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
            
            # 转换为NumPy数组进行印章去除
            import numpy as np
            np_img = np.array(pil_img)
            
            # 印章去除处理
            if len(np_img.shape) == 3:  # 彩色图
                channels = np_img.shape[2]
                
                # 确保通道索引有效
                if self.channel_index >= channels:
                    self.channel_index = 0
                
                # 创建掩码
                mask = np_img[:, :, self.channel_index] >= self.threshold
                
                # 根据通道数创建白色像素
                if channels == 3:
                    white = [255, 255, 255]
                elif channels == 4:
                    white = [255, 255, 255, 255]
                else:
                    white = [255] * channels
                
                # 应用掩码，将印章区域替换为白色
                np_img[mask] = white
            
            # 转回PIL图像
            result_image = Image.fromarray(np_img)
            
            logger.info(f"第 {page_num + 1} 页印章去除完成")
            return page_num, result_image
            
        except Exception as e:
            logger.error(f"处理第 {page_num + 1} 页时出错: {e}")
            raise e

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
            
            if self.max_workers > 1:
                # 多线程模式：使用改进的进度跟踪
                self._process_images_multithreaded(images_data, total_pages, processed_images)
            else:
                # 单线程模式：顺序处理
                self._process_images_singlethreaded(images_data, total_pages, processed_images)
            
            # 按页面顺序排序结果
            processed_images.sort(key=lambda x: x[0])
            final_images = [img for _, img in processed_images]
            
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

    def _process_images_singlethreaded(self, images_data, total_pages, processed_images):
        """单线程处理图像"""
        for i, (page_num, img_data) in enumerate(images_data):
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
        # 创建任务队列
        task_queue = images_data.copy()
        completed_tasks = []
        active_tasks = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 初始提交任务
            for _ in range(min(self.max_workers, len(task_queue))):
                if task_queue:
                    img_data = task_queue.pop(0)
                    future = executor.submit(self._process_single_image, img_data)
                    active_tasks[future] = img_data
            
            # 处理完成的任务并提交新任务
            while active_tasks:
                # 等待任意一个任务完成
                done, _ = concurrent.futures.wait(
                    active_tasks.keys(), 
                    return_when=concurrent.futures.FIRST_COMPLETED
                )
                
                for future in done:
                    try:
                        page_num, result_img = future.result()
                        completed_tasks.append((page_num, result_img))
                        
                        # 从活动任务中移除
                        del active_tasks[future]
                        
                        # 发送进度（基于完成的任务数量）
                        progress = len(completed_tasks)
                        self.progress.emit(progress, total_pages)
                        
                        logger.info(f"第 {page_num + 1} 页处理完成，总进度: {progress}/{total_pages}")
                        
                    except Exception as e:
                        img_data = active_tasks[future]
                        page_num = img_data[0]
                        logger.error(f"处理第 {page_num + 1} 页时出错: {e}")
                        del active_tasks[future]
                    
                    # 提交新任务
                    if task_queue:
                        new_img_data = task_queue.pop(0)
                        new_future = executor.submit(self._process_single_image, new_img_data)
                        active_tasks[new_future] = new_img_data
        
        # 将完成的任务添加到输出列表
        processed_images.extend(completed_tasks)

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

    def cleanup(self):
        """清理资源"""
        # 这里可以添加清理逻辑
        pass


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

