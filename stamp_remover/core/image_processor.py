#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像处理核心模块
"""

from PySide6.QtCore import QThread, Signal
from PIL import Image, ImageEnhance, ImageFilter
import numpy as np
import logging
from typing import Tuple, Optional

from ..utils.logging_config import get_logger
logger = get_logger(__name__)


class StampDetector:
    """印章检测器 - 基于多种特征检测印章区域"""
    
    @staticmethod
    def calculate_saturation(np_im: np.ndarray) -> np.ndarray:
        """计算图像饱和度"""
        if len(np_im.shape) != 3 or np_im.shape[2] < 3:
            return np.zeros((np_im.shape[0], np_im.shape[1]))
        
        r, g, b = np_im[:, :, 0].astype(float), np_im[:, :, 1].astype(float), np_im[:, :, 2].astype(float)
        max_val = np.maximum(np.maximum(r, g), b)
        min_val = np.minimum(np.minimum(r, g), b)
        
        diff = max_val - min_val
        saturation = np.where(max_val > 0, diff / max_val, 0)
        return saturation
    
    @staticmethod
    def detect_circular_regions(mask: np.ndarray, min_area: int = 100, 
                                 circularity_threshold: float = 0.4) -> np.ndarray:
        """检测近似圆形的区域"""
        try:
            from scipy import ndimage
            labeled, num_features = ndimage.label(mask)
            
            refined_mask = np.zeros_like(mask)
            
            for i in range(1, num_features + 1):
                region_mask = (labeled == i)
                area = np.sum(region_mask)
                
                if area < min_area:
                    continue
                
                y_coords, x_coords = np.where(region_mask)
                if len(y_coords) == 0:
                    continue
                    
                center_y, center_x = np.mean(y_coords), np.mean(x_coords)
                
                distances = np.sqrt((y_coords - center_y)**2 + (x_coords - center_x)**2)
                radius = np.mean(distances)
                
                perimeter_estimate = 2 * np.pi * radius
                actual_perimeter = area * 0.1
                
                if perimeter_estimate > 0:
                    circularity = 4 * np.pi * area / (perimeter_estimate ** 2)
                else:
                    circularity = 0
                
                if circularity > circularity_threshold or area > 5000:
                    refined_mask[region_mask] = True
            
            return refined_mask
            
        except ImportError:
            logger.warning("scipy未安装，跳过圆形区域检测")
            return mask
    
    @staticmethod
    def detect_stamp_by_features(np_im: np.ndarray, channel_index: int, 
                                  threshold: int, 
                                  min_saturation: float = 0.3,
                                  min_intensity: int = 100) -> np.ndarray:
        """基于多种特征检测印章区域"""
        if len(np_im.shape) != 3:
            return np.zeros((np_im.shape[0], np_im.shape[1]), dtype=bool)
        
        channels = np_im.shape[2]
        if channel_index >= channels:
            channel_index = 0
        
        channel_mask = np_im[:, :, channel_index] >= threshold
        
        saturation = StampDetector.calculate_saturation(np_im)
        saturation_mask = saturation >= min_saturation
        
        intensity = np.mean(np_im[:, :, :3], axis=2) if channels >= 3 else np_im[:, :, 0]
        intensity_mask = (intensity >= min_intensity) & (intensity <= 250)
        
        combined_mask = channel_mask & saturation_mask & intensity_mask
        
        try:
            from scipy import ndimage
            labeled, num_features = ndimage.label(combined_mask)
            
            refined_mask = np.zeros_like(combined_mask)
            
            for i in range(1, num_features + 1):
                region_mask = (labeled == i)
                area = np.sum(region_mask)
                
                if area >= 50:
                    refined_mask[region_mask] = True
            
            return refined_mask
            
        except ImportError:
            return combined_mask
    
    @staticmethod
    def apply_morphology(mask: np.ndarray, operation: str = 'close', 
                         kernel_size: int = 3) -> np.ndarray:
        """应用形态学操作"""
        try:
            from scipy import ndimage
            kernel = np.ones((kernel_size, kernel_size))
            
            if operation == 'close':
                mask = ndimage.binary_dilation(mask, structure=kernel)
                mask = ndimage.binary_erosion(mask, structure=kernel)
            elif operation == 'open':
                mask = ndimage.binary_erosion(mask, structure=kernel)
                mask = ndimage.binary_dilation(mask, structure=kernel)
            elif operation == 'dilate':
                mask = ndimage.binary_dilation(mask, structure=kernel)
            elif operation == 'erode':
                mask = ndimage.binary_erosion(mask, structure=kernel)
            
            return mask
            
        except ImportError:
            return mask


class ImageProcessingThread(QThread):
    """图像处理线程"""
    
    finished = Signal(object)
    progress = Signal(int)
    error = Signal(str)

    def __init__(self, image_path=None, pil_image=None, rad_num=185, channel_index=0, 
                 is_contrast=False, is_sharpness=False,
                 enable_advanced_detection: bool = True,
                 min_saturation: float = 0.3,
                 min_region_area: int = 50):
        super().__init__()
        self.image_path = image_path
        self.pil_image = pil_image
        self.rad_num = rad_num
        self.channel_index = channel_index
        self.is_contrast = is_contrast
        self.is_sharpness = is_sharpness
        self.enable_advanced_detection = enable_advanced_detection
        self.min_saturation = min_saturation
        self.min_region_area = min_region_area
        
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
        
        if not (0 <= self.min_saturation <= 1):
            raise ValueError("最小饱和度必须在0-1范围内")
        
        if self.min_region_area < 0:
            raise ValueError("最小区域面积不能为负数")

    def run(self):
        """执行图像处理"""
        try:
            logger.info("开始处理图像")
            self.progress.emit(10)
            
            if self.pil_image is not None:
                im = self.pil_image.copy()
                logger.info(f"使用PIL图像对象: 模式={im.mode}, 尺寸={im.size}")
            else:
                im = Image.open(self.image_path)
                logger.info(f"从文件打开图像: {self.image_path}, 模式={im.mode}, 尺寸={im.size}")
            
            self.progress.emit(20)
            
            if self.is_contrast:
                logger.info("应用对比度增强")
                im = ImageEnhance.Contrast(im).enhance(2.0)
                self.progress.emit(40)
                
            if self.is_sharpness:
                logger.info("应用清晰度增强")
                im = ImageEnhance.Sharpness(im).enhance(2.0)
                self.progress.emit(60)
            
            np_im = np.array(im)
            self.progress.emit(70)
            
            result_image = self._remove_stamp(np_im)
            self.progress.emit(90)
            
            self.finished.emit(result_image)
            self.progress.emit(100)
            
            logger.info("图像处理完成")
            
        except Exception as e:
            logger.error(f"图像处理失败: {e}")
            self.error.emit(str(e))
            self.finished.emit(None)

    def _remove_stamp(self, np_im: np.ndarray) -> Image.Image:
        """去除印章的核心算法 - 改进版"""
        if len(np_im.shape) == 3:
            channels = np_im.shape[2]

            if self.channel_index >= channels:
                logger.warning(f"通道索引 {self.channel_index} 超出图像通道数 {channels}，使用默认通道 0")
                self.channel_index = 0

            if self.channel_index < 0:
                self.channel_index = 0
            elif self.channel_index >= channels:
                self.channel_index = channels - 1

            logger.info(f"使用通道索引: {self.channel_index} (通道数: {channels})")

            if self.enable_advanced_detection:
                mask = StampDetector.detect_stamp_by_features(
                    np_im, 
                    self.channel_index, 
                    self.rad_num,
                    min_saturation=self.min_saturation,
                    min_intensity=self.rad_num
                )
                
                try:
                    mask = StampDetector.apply_morphology(mask, operation='close', kernel_size=3)
                except Exception:
                    pass
                
                logger.info("使用高级印章检测算法（基于颜色、饱和度、形状特征）")
            else:
                mask = np_im[:, :, self.channel_index] >= self.rad_num
                logger.info("使用简单阈值检测算法")

            mask_count = np.sum(mask)
            logger.info(f"检测到 {mask_count} 个满足条件的像素点")

            if channels == 3:
                white = [255, 255, 255]
            elif channels == 4:
                white = [255, 255, 255, 255]
            else:
                raise ValueError(f"不支持的通道数: {channels}")

            np_im[mask] = white

        else:
            logger.warning("检测到灰度图像，跳过颜色通道处理")
            return Image.fromarray(np_im)

        return Image.fromarray(np_im)

