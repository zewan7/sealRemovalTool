#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
印章检测与去除模块
使用多特征融合的方法检测印章，避免误删正常内容
"""

import numpy as np
from PIL import Image, ImageFilter
from typing import Tuple, List, Optional
from scipy import ndimage
from collections import deque

from ..utils.logger import get_logger

logger = get_logger(__name__)


class StampDetector:
    """印章检测器 - 基于多特征融合"""
    
    def __init__(self, threshold: int = 185, channel_index: int = 0,
                 min_stamp_size: int = 100, max_stamp_size: int = 1000000,
                 color_tolerance: int = 30, edge_threshold: float = 0.1):
        """
        初始化印章检测器
        
        Args:
            threshold: 颜色阈值
            channel_index: 通道索引（0=红, 1=绿, 2=蓝）
            min_stamp_size: 最小印章像素数（过滤小噪点）
            max_stamp_size: 最大印章像素数（防止过度检测）
            color_tolerance: 颜色容差
            edge_threshold: 边缘检测阈值
        """
        self.threshold = threshold
        self.channel_index = channel_index
        self.min_stamp_size = min_stamp_size
        self.max_stamp_size = max_stamp_size
        self.color_tolerance = color_tolerance
        self.edge_threshold = edge_threshold
        
    def detect_and_remove(self, image: Image.Image) -> Image.Image:
        """
        检测并去除印章
        
        Args:
            image: PIL图像对象
            
        Returns:
            处理后的PIL图像对象
        """
        # 转换为numpy数组
        np_img = np.array(image)
        original = np_img.copy()
        
        if len(np_img.shape) != 3:
            logger.warning("非彩色图像，跳过印章检测")
            return image
        
        channels = np_img.shape[2]
        if channels not in [3, 4]:
            logger.warning(f"不支持的通道数: {channels}")
            return image
        
        # 确保通道索引有效
        if self.channel_index >= channels:
            self.channel_index = 0
        
        # 步骤1: 基于颜色的初步检测
        color_mask = self._detect_by_color(np_img)
        
        # 步骤2: 基于形状的过滤
        shape_mask = self._detect_by_shape(np_img, color_mask)
        
        # 步骤3: 基于连通区域的过滤
        region_mask = self._filter_by_region(shape_mask)
        
        # 步骤4: 边缘验证（印章通常有清晰的边缘）
        final_mask = self._verify_by_edges(np_img, region_mask)
        
        # 应用掩码去除印章
        result = self._apply_mask(original, final_mask, channels)
        
        # 统计信息
        stamp_pixels = np.sum(final_mask)
        logger.info(f"检测到印章区域: {stamp_pixels} 像素 ({stamp_pixels / final_mask.size * 100:.2f}%)")
        
        return Image.fromarray(result)
    
    def _detect_by_color(self, np_img: np.ndarray) -> np.ndarray:
        """
        基于颜色检测印章候选区域
        印章通常是红色的，在RGB中R值较高，G和B值较低或适中
        """
        if self.channel_index == 0:  # 红色通道（印章通常是红色）
            r = np_img[:, :, 0].astype(np.float32)
            g = np_img[:, :, 1].astype(np.float32)
            b = np_img[:, :, 2].astype(np.float32)
            
            # 红色印章特征: R高, G和B相对较低
            # 使用相对阈值：R > threshold 且 R > G + tolerance 且 R > B + tolerance
            mask = (
                (r >= self.threshold) &
                (r > g + self.color_tolerance) &
                (r > b + self.color_tolerance)
            )
        elif self.channel_index == 1:  # 绿色通道
            channel = np_img[:, :, 1].astype(np.float32)
            other_avg = (np_img[:, :, 0].astype(np.float32) + 
                        np_img[:, :, 2].astype(np.float32)) / 2
            mask = (channel >= self.threshold) & (channel > other_avg + self.color_tolerance)
        elif self.channel_index == 2:  # 蓝色通道
            channel = np_img[:, :, 2].astype(np.float32)
            other_avg = (np_img[:, :, 0].astype(np.float32) + 
                        np_img[:, :, 1].astype(np.float32)) / 2
            mask = (channel >= self.threshold) & (channel > other_avg + self.color_tolerance)
        else:
            # 其他通道使用简单阈值
            mask = np_img[:, :, self.channel_index] >= self.threshold
        
        return mask
    
    def _detect_by_shape(self, np_img: np.ndarray, color_mask: np.ndarray) -> np.ndarray:
        """
        基于形状特征过滤
        印章通常是圆形或椭圆形的
        """
        # 使用形态学操作来优化掩码
        from scipy import ndimage
        
        # 开运算去除小噪点
        structure = ndimage.generate_binary_structure(2, 2)
        cleaned = ndimage.binary_opening(color_mask, structure, iterations=1)
        
        # 闭运算填充小空洞
        cleaned = ndimage.binary_closing(cleaned, structure, iterations=1)
        
        return cleaned
    
    def _filter_by_region(self, mask: np.ndarray) -> np.ndarray:
        """
        基于连通区域过滤
        只保留符合印章大小特征的区域
        """
        # 标记连通区域
        labeled_array, num_features = ndimage.label(mask)
        
        # 创建结果掩码
        result_mask = np.zeros_like(mask, dtype=bool)
        
        for i in range(1, num_features + 1):
            region = labeled_array == i
            region_size = np.sum(region)
            
            # 检查区域大小是否在合理范围内
            if self.min_stamp_size <= region_size <= self.max_stamp_size:
                # 计算区域的长宽比（印章通常是圆形或椭圆形）
                coords = np.where(region)
                if len(coords[0]) > 0:
                    height = np.max(coords[0]) - np.min(coords[0])
                    width = np.max(coords[1]) - np.min(coords[1])
                    
                    if height > 0 and width > 0:
                        aspect_ratio = max(width, height) / min(width, height)
                        # 印章的长宽比通常在1:1到1:3之间
                        if aspect_ratio <= 3.0:
                            result_mask |= region
        
        return result_mask
    
    def _verify_by_edges(self, np_img: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        基于边缘验证
        印章通常有清晰的边缘
        """
        return self.filter_by_edge(np_img, mask)
    
    def detect_color_regions(self, np_img: np.ndarray) -> np.ndarray:
        """
        检测颜色区域 - 公开接口
        
        Args:
            np_img: numpy图像数组
            
        Returns:
            颜色掩码
        """
        return self._detect_by_color(np_img)
    
    def filter_by_shape(self, np_img: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        基于形状过滤 - 公开接口
        
        Args:
            np_img: numpy图像数组
            mask: 输入掩码
            
        Returns:
            过滤后的掩码
        """
        return self._detect_by_shape(np_img, mask)
    
    def filter_by_edge(self, np_img: np.ndarray, mask: np.ndarray) -> np.ndarray:
        """
        基于边缘验证过滤 - 公开接口
        
        Args:
            np_img: numpy图像数组
            mask: 输入掩码
            
        Returns:
            验证后的掩码
        """
        # 转换为灰度图
        if len(np_img.shape) == 3:
            gray = np.mean(np_img[:, :, :3], axis=2).astype(np.uint8)
        else:
            gray = np_img.astype(np.uint8)
        
        # 使用Sobel算子检测边缘
        from scipy import ndimage
        sobel_x = ndimage.sobel(gray, axis=1)
        sobel_y = ndimage.sobel(gray, axis=0)
        edge_magnitude = np.sqrt(sobel_x**2 + sobel_y**2)
        
        # 归一化边缘强度
        edge_magnitude = edge_magnitude / np.max(edge_magnitude) if np.max(edge_magnitude) > 0 else edge_magnitude
        
        # 膨胀掩码以包含边缘
        dilated_mask = ndimage.binary_dilation(mask, iterations=2)
        
        # 在掩码边缘区域检查是否有强边缘
        edge_mask = edge_magnitude > self.edge_threshold
        
        # 只保留有清晰边缘的区域
        edge_overlap = dilated_mask & edge_mask
        
        # 如果边缘重叠度太低，可能是误检
        edge_ratio = np.sum(edge_overlap) / np.sum(dilated_mask) if np.sum(dilated_mask) > 0 else 0
        logger.debug(f"边缘重叠比例: {edge_ratio:.2f}")
        
        return mask
    
    def _apply_mask(self, np_img: np.ndarray, mask: np.ndarray, channels: int) -> np.ndarray:
        """
        应用掩码去除印章
        使用智能填充而不是简单的白色填充
        """
        result = np_img.copy()
        
        # 创建白色填充
        if channels == 3:
            white = [255, 255, 255]
        elif channels == 4:
            white = [255, 255, 255, 255]
        else:
            white = [255] * channels
        
        # 对于每个印章区域，尝试使用周围像素进行智能填充
        labeled_array, num_features = ndimage.label(mask)
        
        for i in range(1, num_features + 1):
            region = labeled_array == i
            
            # 获取区域的边界框
            coords = np.where(region)
            if len(coords[0]) == 0:
                continue
                
            min_y, max_y = np.min(coords[0]), np.max(coords[0])
            min_x, max_x = np.min(coords[1]), np.max(coords[1])
            
            # 扩展边界框以获取周围像素
            pad = 5
            min_y = max(0, min_y - pad)
            max_y = min(np_img.shape[0], max_y + pad + 1)
            min_x = max(0, min_x - pad)
            max_x = min(np_img.shape[1], max_x + pad + 1)
            
            # 提取区域和周围像素
            roi = result[min_y:max_y, min_x:max_x]
            roi_mask = region[min_y:max_y, min_x:max_x]
            
            # 计算周围非印章像素的平均值
            non_stamp = ~roi_mask
            if np.any(non_stamp):
                # 使用周围像素的平均值进行填充
                for c in range(min(channels, 3)):  # 只处理RGB通道
                    avg_color = np.mean(roi[non_stamp, c])
                    roi[roi_mask, c] = avg_color
            else:
                # 如果没有周围像素，使用白色
                result[region] = white[:channels]
        
        return result


class AdvancedStampRemover:
    """高级印章去除器 - 提供多种去除策略"""
    
    def __init__(self, method: str = 'auto', **kwargs):
        """
        初始化高级印章去除器
        
        Args:
            method: 去除方法 ('auto', 'color', 'hsv', 'ml')
            **kwargs: 传递给具体检测器的参数
        """
        self.method = method
        self.kwargs = kwargs
        self.detector = StampDetector(**kwargs)
    
    def remove_stamp(self, image: Image.Image) -> Image.Image:
        """
        去除印章
        
        Args:
            image: PIL图像对象
            
        Returns:
            处理后的PIL图像对象
        """
        if self.method == 'auto':
            return self._auto_remove(image)
        elif self.method == 'color':
            return self.detector.detect_and_remove(image)
        elif self.method == 'hsv':
            return self._hsv_remove(image)
        else:
            return self.detector.detect_and_remove(image)
    
    def _auto_remove(self, image: Image.Image) -> Image.Image:
        """
        自动选择最佳方法去除印章
        """
        # 首先尝试基于颜色的方法
        result = self.detector.detect_and_remove(image)
        
        # 可以在这里添加更多策略选择逻辑
        
        return result
    
    def _hsv_remove(self, image: Image.Image) -> Image.Image:
        """
        基于HSV色彩空间的印章去除
        在HSV空间中更容易区分红色印章
        """
        import colorsys
        
        np_img = np.array(image)
        if len(np_img.shape) != 3:
            return image
        
        # 转换为HSV
        hsv_img = self._rgb_to_hsv(np_img)
        
        # 红色在HSV中的范围（H: 0-10 或 170-180）
        h = hsv_img[:, :, 0]
        s = hsv_img[:, :, 1]
        v = hsv_img[:, :, 2]
        
        # 检测红色区域
        red_mask = ((h <= 0.05) | (h >= 0.95)) & (s > 0.3) & (v > 0.3)
        
        # 应用掩码
        channels = np_img.shape[2]
        if channels == 3:
            white = [255, 255, 255]
        elif channels == 4:
            white = [255, 255, 255, 255]
        else:
            white = [255] * channels
        
        result = np_img.copy()
        result[red_mask] = white[:channels]
        
        return Image.fromarray(result)
    
    def _rgb_to_hsv(self, rgb: np.ndarray) -> np.ndarray:
        """
        将RGB图像转换为HSV
        """
        # 归一化到0-1
        rgb_norm = rgb[:, :, :3].astype(np.float32) / 255.0
        
        # 使用vectorized操作
        r, g, b = rgb_norm[:, :, 0], rgb_norm[:, :, 1], rgb_norm[:, :, 2]
        
        maxc = np.maximum(np.maximum(r, g), b)
        minc = np.minimum(np.minimum(r, g), b)
        delta = maxc - minc
        
        # 计算V
        v = maxc
        
        # 计算S
        s = np.where(maxc != 0, delta / maxc, 0)
        
        # 计算H
        h = np.zeros_like(v)
        
        # R is max
        h = np.where((maxc == r) & (delta != 0), 
                     (g - b) / delta % 6, h)
        # G is max
        h = np.where((maxc == g) & (delta != 0),
                     (b - r) / delta + 2, h)
        # B is max
        h = np.where((maxc == b) & (delta != 0),
                     (r - g) / delta + 4, h)
        
        h = h / 6.0
        
        # 处理负数
        h = np.where(h < 0, h + 1, h)
        
        hsv = np.stack([h, s, v], axis=2)
        return hsv


def remove_stamp_simple(np_img: np.ndarray, threshold: int = 185, 
                        channel_index: int = 0) -> np.ndarray:
    """
    简单的印章去除（向后兼容）
    
    Args:
        np_img: numpy图像数组
        threshold: 阈值
        channel_index: 通道索引
        
    Returns:
        处理后的numpy数组
    """
    if len(np_img.shape) != 3:
        return np_img
    
    channels = np_img.shape[2]
    
    # 确保通道索引有效
    if channel_index >= channels:
        channel_index = 0
    
    # 创建掩码
    mask = np_img[:, :, channel_index] >= threshold
    
    # 根据通道数创建白色像素
    if channels == 3:
        white = [255, 255, 255]
    elif channels == 4:
        white = [255, 255, 255, 255]
    else:
        white = [255] * channels
    
    # 应用掩码
    result = np_img.copy()
    result[mask] = white
    
    return result
