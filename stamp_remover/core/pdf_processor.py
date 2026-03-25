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
    page_processed = Signal(int, bytes)  # 单页处理完成信号（用于流式处理）

    def __init__(self, pdf_path: str, dpi: int = 150, max_pages: Optional[int] = None, 
                 max_workers: int = 4, stream_mode: bool = False, 
                 page_batch_size: int = 10):
        super().__init__()
        self.pdf_path = pdf_path
        self.dpi = dpi
        self.max_pages = max_pages
        self.max_workers = max_workers
        self.stream_mode = stream_mode  # 流式处理模式，大文件时使用
        self.page_batch_size = page_batch_size  # 批处理大小
        self.temp_dir = None
        self._is_running = True
        
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
        pix = None
        try:
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
            # 确保pixmap资源被释放
            if pix is not None:
                try:
                    del pix
                except:
                    pass

    def run(self):
        """执行PDF处理"""
        doc = None
        try:
            logger.info(f"开始处理PDF: {self.pdf_path}")
            self.status.emit("正在处理PDF...")
            
            # 检查文件大小，确定处理模式
            file_size_mb = os.path.getsize(self.pdf_path) / (1024 * 1024)
            if file_size_mb > 100:  # 大于100MB自动启用流式处理
                self.stream_mode = True
                logger.info(f"文件较大({file_size_mb:.1f}MB)，自动启用流式处理模式")
            
            # 打开PDF文档
            doc = fitz.open(self.pdf_path)
            total_pages = len(doc)
            
            if self.max_pages:
                total_pages = min(total_pages, self.max_pages)
            
            logger.info(f"PDF总页数: {len(doc)}, 将处理: {total_pages} 页")
            self.progress.emit(0, total_pages)
            
            if self.stream_mode:
                # 流式处理：分批处理，减少内存占用
                output_images = self._process_streaming(doc, total_pages)
            else:
                # 正常模式：加载所有页面数据
                pages_data = []
                for i in range(total_pages):
                    if not self._is_running:
                        break
                    page = doc.load_page(i)
                    pages_data.append((i, page))
                
                output_images = []
                if self.max_workers > 1:
                    self._process_multithreaded(pages_data, total_pages, output_images)
                else:
                    self._process_singlethreaded(pages_data, total_pages, output_images)
            
            # 按页面顺序排序结果
            output_images.sort(key=lambda x: x[0])
            image_data_list = [img_data for _, img_data in output_images]
            
            if image_data_list:
                logger.info(f"PDF处理完成，共生成 {len(image_data_list)} 张图片")
                self.progress.emit(total_pages, total_pages)
                self.status.emit("处理完成")
                self.finished.emit(image_data_list)
            else:
                logger.warning("PDF处理完成，但没有生成任何图片")
                self.status.emit("处理完成")
                self.finished.emit([])
                
        except MemoryError:
            error_msg = "内存不足，PDF文件过大"
            logger.error(error_msg)
            self.error.emit(error_msg)
            self.status.emit("处理失败")
            self.finished.emit([])
        except Exception as e:
            logger.error(f"PDF处理失败: {e}")
            self.error.emit(str(e))
            self.status.emit("处理失败")
            self.finished.emit([])
            
        finally:
            # 确保文档正确关闭
            if doc is not None:
                try:
                    doc.close()
                    logger.debug("PDF文档已关闭")
                except Exception as e:
                    logger.warning(f"关闭PDF文档时出错: {e}")

    def _process_streaming(self, doc, total_pages):
        """流式处理大PDF文件，减少内存占用"""
        output_images = []
        batch_size = self.page_batch_size
        
        for start_idx in range(0, total_pages, batch_size):
            if not self._is_running:
                break
                
            end_idx = min(start_idx + batch_size, total_pages)
            logger.info(f"处理批次: 第 {start_idx + 1}-{end_idx} 页")
            
            # 加载当前批次的页面
            batch_pages = []
            for i in range(start_idx, end_idx):
                page = doc.load_page(i)
                batch_pages.append((i, page))
            
            # 处理当前批次
            batch_results = []
            if self.max_workers > 1:
                self._process_multithreaded(batch_pages, total_pages, batch_results)
            else:
                self._process_singlethreaded(batch_pages, total_pages, batch_results)
            
            # 保存结果并释放当前批次资源
            output_images.extend(batch_results)
            
            # 发送批次进度
            self.progress.emit(min(end_idx, total_pages), total_pages)
            
            # 显式释放内存
            for _, page in batch_pages:
                try:
                    del page
                except:
                    pass
            
            # 清理结果中的重复数据（仅保留数据）
            for result in batch_results:
                self.page_processed.emit(result[0], result[1])
            
            import gc
            gc.collect()
        
        return output_images
    
    def stop(self):
        """停止处理"""
        self._is_running = False
        logger.info("请求停止PDF处理")
    
    def _process_singlethreaded(self, pages_data, total_pages, output_images):
        """单线程处理，进度准确"""
        for i, (page_num, page) in enumerate(pages_data):
            if not self._is_running:
                break
                
            try:
                page_num, img_data = self._process_single_page((page_num, page))
                output_images.append((page_num, img_data))
                
                # 发送准确进度（仅在非流式模式下）
                if not self.stream_mode:
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
                 max_workers: int = 4, page_batch_size: int = 10):
        super().__init__()
        self.pdf_images_data = pdf_images_data
        self.save_path = save_path
        self.threshold = threshold
        self.channel_index = channel_index
        self.enable_contrast = enable_contrast
        self.enable_sharpness = enable_sharpness
        self.max_workers = max_workers
        self.page_batch_size = page_batch_size  # 批处理大小，减少内存占用
        self._is_running = True
        self._temp_files = []  # 临时文件列表，用于清理
        
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
            
            # 使用改进的印章去除算法
            result_image = self._remove_stamp_from_image(np_img)
            
            logger.info(f"第 {page_num + 1} 页印章去除完成")
            return page_num, result_image
            
        except MemoryError:
            error_msg = f"第 {page_num + 1} 页内存不足，跳过该页"
            logger.error(error_msg)
            return page_num, pil_img  # 返回原始图像
        except Exception as e:
            logger.error(f"处理第 {page_num + 1} 页时出错: {e}")
            raise e
    
    def _remove_stamp_from_image(self, np_im):
        """改进的印章去除算法（与ImageProcessingThread一致）"""
        if len(np_im.shape) != 3:  # 非彩色图
            return Image.fromarray(np_im)
        
        channels = np_im.shape[2]
        height, width = np_im.shape[:2]
        channel_index = max(0, min(self.channel_index, channels - 1))
        
        # ========== 步骤1: 多通道颜色分析，生成初步掩码 ==========
        if channels >= 3:
            R = np_im[:, :, 0].astype(np.int16)
            G = np_im[:, :, 1].astype(np.int16)
            B = np_im[:, :, 2].astype(np.int16)
            
            # 红色印章特征
            red_dominance = R - np.maximum(G, B)
            is_red_like = (R > self.threshold) & (red_dominance > 20)
            
            if channel_index == 0:  # 红色通道
                color_mask = is_red_like
            elif channel_index == 2:  # 蓝色通道
                blue_dominance = B - np.maximum(R, G)
                color_mask = (B > self.threshold) & (blue_dominance > 20)
            else:  # 其他通道
                channel_vals = np_im[:, :, channel_index]
                color_mask = channel_vals >= self.threshold
        else:
            channel_vals = np_im[:, :, channel_index]
            color_mask = channel_vals >= self.threshold
        
        # ========== 步骤2: 形态学清理，去除噪声 ==========
        color_mask_clean = self._morphological_clean(color_mask)
        
        # ========== 步骤3: 连通区域分析，筛选印章区域 ==========
        stamp_mask = self._find_stamp_regions(color_mask_clean, height, width)
        
        # ========== 步骤4: 应用掩码，将印章区域替换为白色 ==========
        if channels == 3:
            white = [255, 255, 255]
        elif channels == 4:
            white = [255, 255, 255, 255]
        else:
            white = [255] * channels
        
        stamp_mask_expanded = np.expand_dims(stamp_mask, axis=-1)
        stamp_mask_expanded = np.repeat(stamp_mask_expanded, channels, axis=-1)
        
        np_im = np.where(stamp_mask_expanded, white, np_im)
        
        return Image.fromarray(np_im.astype(np.uint8))
    
    def _morphological_clean(self, mask):
        """形态学清理：去除小噪声点"""
        cleaned = mask.copy()
        height, width = mask.shape
        kernel_size = 3
        pad = kernel_size // 2
        
        for i in range(height):
            for j in range(width):
                if mask[i, j]:
                    i_start = max(0, i - pad)
                    i_end = min(height, i + pad + 1)
                    j_start = max(0, j - pad)
                    j_end = min(width, j + pad + 1)
                    
                    neighborhood = mask[i_start:i_end, j_start:j_end]
                    density = np.mean(neighborhood)
                    
                    if density < 0.3:
                        cleaned[i, j] = False
        
        return cleaned
    
    def _find_stamp_regions(self, mask, img_height, img_width):
        """寻找印章区域"""
        visited = np.zeros_like(mask, dtype=bool)
        stamp_mask = np.zeros_like(mask, dtype=bool)
        total_area = img_height * img_width
        min_area_ratio = 0.001
        max_area_ratio = 0.3
        
        for i in range(img_height):
            for j in range(img_width):
                if mask[i, j] and not visited[i, j]:
                    region = self._flood_fill(mask, i, j, visited)
                    
                    if region:
                        ys, xs = zip(*region)
                        y_min, y_max = min(ys), max(ys)
                        x_min, x_max = min(xs), max(xs)
                        
                        region_area = len(region)
                        region_width = x_max - x_min + 1
                        region_height = y_max - y_min + 1
                        aspect_ratio = region_width / max(region_height, 1)
                        area_ratio = region_area / total_area
                        density = region_area / max(region_width * region_height, 1)
                        
                        # 判断是否为印章区域
                        area_valid = (min_area_ratio <= area_ratio <= max_area_ratio)
                        ratio_valid = (0.3 <= aspect_ratio <= 3.0)
                        density_valid = (density >= 0.2)
                        
                        is_stamp = area_valid and ratio_valid and density_valid
                        
                        if is_stamp:
                            for (y, x) in region:
                                stamp_mask[y, x] = True
        
        return stamp_mask
    
    def _flood_fill(self, mask, start_y, start_x, visited):
        """洪水填充算法"""
        height, width = mask.shape
        region = []
        stack = [(start_y, start_x)]
        
        while stack:
            y, x = stack.pop()
            
            if (0 <= y < height and 0 <= x < width and 
                mask[y, x] and not visited[y, x]):
                
                visited[y, x] = True
                region.append((y, x))
                
                # 添加8邻域
                for dy in [-1, 0, 1]:
                    for dx in [-1, 0, 1]:
                        if dy != 0 or dx != 0:
                            stack.append((y + dy, x + dx))
        
        return region

    def run(self):
        """执行PDF重新生成"""
        try:
            total_pages = len(self.pdf_images_data)
            logger.info(f"开始PDF重新生成，共 {total_pages} 页")
            
            self.progress.emit(0, total_pages)
            
            # 判断是否需要批处理（页面多或数据量大时使用
            use_batch_processing = total_pages > 50
            
            if use_batch_processing:
                logger.info(f"页面数较多({total_pages})，使用批处理模式")
                processed_images = self._process_images_batch(total_pages)
            else:
                # 准备图像数据
                images_data = [(i, img_data) for i, img_data in enumerate(self.pdf_images_data)]
                processed_images = []
                
                if self.max_workers > 1:
                    self._process_images_multithreaded(images_data, total_pages, processed_images)
                else:
                    self._process_images_singlethreaded(images_data, total_pages, processed_images)
            
            # 按页面顺序排序结果
            processed_images.sort(key=lambda x: x[0])
            final_images = [img for _, img in processed_images]
            
            # 组合成PDF
            logger.info("开始组合PDF文件...")
            self._combine_images_to_pdf(final_images)
            
            self.finished.emit(True, self.save_path)
            logger.info(f"PDF重新生成完成: {self.save_path}")
            
        except MemoryError:
            error_msg = "内存不足，请尝试减少批处理大小或工作线程数"
            logger.error(error_msg)
            self.error.emit(error_msg)
            self.finished.emit(False, self.save_path)
        except Exception as e:
            logger.error(f"PDF重新生成失败: {e}")
            self.error.emit(str(e))
            self.finished.emit(False, self.save_path)
        finally:
            # 清理临时资源
            self.cleanup()
    
    def stop(self):
        """停止处理"""
        self._is_running = False
        logger.info("请求停止PDF重新生成")
    
    def _process_images_batch(self, total_pages):
        """批处理图像（内存优化）"""
        processed_images = []
        batch_size = self.page_batch_size
        
        for start_idx in range(0, total_pages, batch_size):
            if not self._is_running:
                break
                
            end_idx = min(start_idx + batch_size, total_pages)
            logger.info(f"处理批次: 第 {start_idx + 1}-{end_idx} 页")
            
            # 准备当前批次数据
            batch_data = [(i, self.pdf_images_data[i]) for i in range(start_idx, end_idx)]
            batch_results = []
            
            if self.max_workers > 1:
                self._process_images_multithreaded(batch_data, total_pages, batch_results)
            else:
                self._process_images_singlethreaded(batch_data, total_pages, batch_results)
            
            processed_images.extend(batch_results)
            
            # 显式释放内存
            import gc
            gc.collect()
        
        return processed_images

    def _process_images_singlethreaded(self, images_data, total_pages, processed_images):
        """单线程处理图像"""
        for i, (page_num, img_data) in enumerate(images_data):
            if not self._is_running:
                logger.info(f"处理已停止，在第 {page_num + 1} 页")
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
        rgb_images = []
        try:
            # 确保所有图像都是RGB模式
            for img in images:
                if img.mode != 'RGB':
                    rgb_img = img.convert('RGB')
                    rgb_images.append(rgb_img)
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
        finally:
            # 释放图像资源
            for img in rgb_images:
                try:
                    img.close()
                except:
                    pass

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

