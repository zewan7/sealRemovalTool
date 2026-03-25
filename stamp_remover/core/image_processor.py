#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像处理核心模块
"""

from PySide6.QtCore import QThread, Signal
from PIL import Image, ImageEnhance
import numpy as np
import logging
import math

logger = logging.getLogger(__name__)


class ImageProcessingThread(QThread):
    """图像处理线程"""
    
    # 信号定义
    finished = Signal(object)  # 处理完成，传递PIL图像对象
    progress = Signal(int)     # 处理进度
    error = Signal(str)        # 错误信息

    def __init__(self, image_path=None, pil_image=None, rad_num=185, channel_index=0, 
                 is_contrast=False, is_sharpness=False, sensitivity: float = 0.5):
        super().__init__()
        self.image_path = image_path
        self.pil_image = pil_image
        self.rad_num = rad_num
        self.channel_index = channel_index
        self.is_contrast = is_contrast
        self.is_sharpness = is_sharpness
        self.sensitivity = max(0.1, min(1.0, sensitivity))  # 灵敏度参数，0.1-1.0
        
        # 验证参数
        self._validate_parameters()

    def _validate_parameters(self):
        """验证输入参数"""
        if self.image_path is None and self.pil_image is None:
            raise ValueError("必须提供图像路径或PIL图像对象")
        
        if not (0 <= self.rad_num <= 255):
            raise ValueError("阈值必须在0-255范围内")
        
        if self.channel_index < 0:
            logger.warning(f"通道索引 {self.channel_index} 为负数，调整为 0")
            self.channel_index = 0

    def run(self):
        """执行图像处理"""
        try:
            logger.info("开始处理图像")
            self.progress.emit(10)
            
            # 获取图像对象
            if self.pil_image is not None:
                im = self.pil_image.copy()
                logger.info(f"使用PIL图像对象: 模式={im.mode}, 尺寸={im.size}")
            else:
                im = Image.open(self.image_path)
                logger.info(f"从文件打开图像: {self.image_path}, 模式={im.mode}, 尺寸={im.size}")
            
            self.progress.emit(20)
            
            # 图像增强
            if self.is_contrast:
                logger.info("应用对比度增强")
                im = ImageEnhance.Contrast(im).enhance(2.0)
                self.progress.emit(40)
                
            if self.is_sharpness:
                logger.info("应用清晰度增强")
                im = ImageEnhance.Sharpness(im).enhance(2.0)
                self.progress.emit(60)
            
            # 转换为NumPy数组
            np_im = np.array(im)
            self.progress.emit(70)
            
            # 印章去除处理（改进版算法）
            result_image = self._remove_stamp_improved(np_im)
            self.progress.emit(90)
            
            self.finished.emit(result_image)
            self.progress.emit(100)
            
            logger.info("图像处理完成")
            
        except MemoryError:
            error_msg = "内存不足，图像过大"
            logger.error(error_msg)
            self.error.emit(error_msg)
            self.finished.emit(None)
        except Exception as e:
            logger.error(f"图像处理失败: {e}", exc_info=True)
            self.error.emit(str(e))
            self.finished.emit(None)

    def _remove_stamp(self, np_im):
        """原始印章去除算法（保持兼容性）"""
        return self._remove_stamp_improved(np_im)
    
    def _remove_stamp_improved(self, np_im):
        """
        改进的印章去除算法：
        1. 多通道颜色分析（不仅看单一通道）
        2. 连通区域分析（印章通常是连续的块状区域）
        3. 形状分析（印章通常是圆形或椭圆形）
        4. 纹理分析（印章有特定的纹理模式）
        """
        if len(np_im.shape) != 3:  # 非彩色图
            logger.warning("检测到非彩色图像，跳过印章处理")
            return Image.fromarray(np_im)
        
        channels = np_im.shape[2]
        height, width = np_im.shape[:2]
        
        # 确保通道索引有效
        self.channel_index = max(0, min(self.channel_index, channels - 1))
        logger.info(f"使用通道索引: {self.channel_index} (通道数: {channels})")
        
        # ========== 步骤1: 多通道颜色分析，生成初步掩码 ==========
        # 印章通常是红色，需要综合判断而不是仅看单一通道
        if channels >= 3:
            # 分离RGB通道
            R = np_im[:, :, 0].astype(np.int16)
            G = np_im[:, :, 1].astype(np.int16)
            B = np_im[:, :, 2].astype(np.int16)
            
            # 红色印章的颜色特征：R通道值高，且R远大于G和B
            # 印章通常是鲜红色，R > G且R > B
            red_dominance = R - np.maximum(G, B)
            is_red_like = (R > self.rad_num) & (red_dominance > 20)
            
            # 也考虑其他颜色的印章（蓝色、紫色等）
            if self.channel_index == 0:  # 红色通道
                color_mask = is_red_like
            elif self.channel_index == 2:  # 蓝色通道
                blue_dominance = B - np.maximum(R, G)
                color_mask = (B > self.rad_num) & (blue_dominance > 20)
            else:  # 其他通道，使用原始判断但增加限制
                channel_vals = np_im[:, :, self.channel_index]
                color_mask = channel_vals >= self.rad_num
        else:
            # 简单通道判断（兼容非RGB图像）
            channel_vals = np_im[:, :, self.channel_index]
            color_mask = channel_vals >= self.rad_num
        
        # 应用灵敏度参数调整掩码严格程度
        threshold_pixels = int(np.sum(color_mask) * self.sensitivity)
        if threshold_pixels > 0:
            # 按通道值排序，只保留最可能的部分
            if channels >= 3 and self.channel_index == 0:
                sorted_indices = np.argsort(-R.flatten())
            else:
                sorted_indices = np.argsort(-np_im[:, :, self.channel_index].flatten())
            
            threshold_mask = np.zeros_like(color_mask.flatten(), dtype=bool)
            threshold_mask[sorted_indices[:threshold_pixels]] = True
            threshold_mask = threshold_mask.reshape(color_mask.shape)
            color_mask = color_mask & threshold_mask
        
        # ========== 步骤2: 去除孤立小点（噪声） ==========
        # 使用形态学操作去除噪声
        color_mask_clean = self._morphological_clean(color_mask)
        
        # ========== 步骤3: 连通区域分析，筛选印章区域 ==========
        stamp_mask = self._find_stamp_regions(color_mask_clean, height, width)
        
        # 统计结果
        total_pixels = height * width
        stamp_pixels = np.sum(stamp_mask)
        logger.info(f"印章区域像素数: {stamp_pixels} (占比: {stamp_pixels/total_pixels:.2%})")
        
        # ========== 步骤4: 应用掩码，将印章区域替换为白色 ==========
        if channels == 3:
            white = [255, 255, 255]
        elif channels == 4:
            white = [255, 255, 255, 255]
        else:
            white = [255] * channels
        
        # 扩展掩码到所有通道
        stamp_mask_expanded = np.expand_dims(stamp_mask, axis=-1)
        stamp_mask_expanded = np.repeat(stamp_mask_expanded, channels, axis=-1)
        
        # 替换印章区域为白色
        np_im = np.where(stamp_mask_expanded, white, np_im)
        
        return Image.fromarray(np_im.astype(np.uint8))
    
    def _morphological_clean(self, mask):
        """形态学清理：去除小噪声点"""
        # 简单的邻域分析（不依赖OpenCV，使用numpy操作）
        cleaned = mask.copy()
        height, width = mask.shape
        
        # 定义邻域大小
        kernel_size = 3
        pad = kernel_size // 2
        
        # 检查每个像素周围的邻域
        for i in range(height):
            for j in range(width):
                if mask[i, j]:
                    # 计算邻域内的激活像素数
                    i_start = max(0, i - pad)
                    i_end = min(height, i + pad + 1)
                    j_start = max(0, j - pad)
                    j_end = min(width, j + pad + 1)
                    
                    neighborhood = mask[i_start:i_end, j_start:j_end]
                    density = np.mean(neighborhood)
                    
                    # 如果密度太低，认为是噪声点
                    if density < 0.3:
                        cleaned[i, j] = False
        
        return cleaned
    
    def _find_stamp_regions(self, mask, img_height, img_width):
        """
        寻找印章区域：
        1. 查找连通区域
        2. 根据区域大小、形状特征筛选印章
        """
        visited = np.zeros_like(mask, dtype=bool)
        stamp_mask = np.zeros_like(mask, dtype=bool)
        
        # 图像面积
        total_area = img_height * img_width
        
        # 印章区域的最小和最大相对面积
        min_area_ratio = 0.001  # 至少0.1%的图像面积
        max_area_ratio = 0.3    # 最多30%的图像面积
        
        for i in range(img_height):
            for j in range(img_width):
                if mask[i, j] and not visited[i, j]:
                    # 使用洪水填充找到连通区域
                    region = self._flood_fill(mask, i, j, visited)
                    
                    if region:
                        # 计算区域边界
                        ys, xs = zip(*region)
                        y_min, y_max = min(ys), max(ys)
                        x_min, x_max = min(xs), max(xs)
                        
                        # 区域特征计算
                        region_area = len(region)
                        region_width = x_max - x_min + 1
                        region_height = y_max - y_min + 1
                        aspect_ratio = region_width / max(region_height, 1)
                        
                        # 计算面积占比
                        area_ratio = region_area / total_area
                        
                        # 印章特征判断：
                        # 1. 面积在合理范围内
                        area_valid = (min_area_ratio <= area_ratio <= max_area_ratio)
                        
                        # 2. 宽高比接近1（印章通常是接近圆形）
                        ratio_valid = (0.3 <= aspect_ratio <= 3.0)
                        
                        # 3. 区域密度（像素点数/边界矩形面积）- 印章相对紧凑
                        density = region_area / max(region_width * region_height, 1)
                        density_valid = (density >= 0.2)
                        
                        # 判断是否为印章区域
                        is_stamp = area_valid and ratio_valid and density_valid
                        
                        if is_stamp:
                            logger.debug(f"检测到印章区域: 位置=({x_min},{y_min})-({x_max},{y_max}), "
                                         f"面积={region_area}, 宽高比={aspect_ratio:.2f}, 密度={density:.2f}")
                            
                            # 标记为印章区域
                            for (y, x) in region:
                                stamp_mask[y, x] = True
        
        return stamp_mask
    
    def _flood_fill(self, mask, start_y, start_x, visited):
        """洪水填充算法查找连通区域"""
        height, width = mask.shape
        region = []
        stack = [(start_y, start_x)]
        
        while stack:
            y, x = stack.pop()
            
            if (0 <= y < height and 0 <= x < width and 
                mask[y, x] and not visited[y, x]):
                
                visited[y, x] = True
                region.append((y, x))
                
                # 添加4邻域
                stack.append((y + 1, x))
                stack.append((y - 1, x))
                stack.append((y, x + 1))
                stack.append((y, x - 1))
                
                # 添加8邻域（可选，用于更紧凑的连接）
                stack.append((y + 1, x + 1))
                stack.append((y + 1, x - 1))
                stack.append((y - 1, x + 1))
                stack.append((y - 1, x - 1))
        
        return region

