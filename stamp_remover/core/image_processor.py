#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图像处理核心模块
"""

from PySide6.QtCore import QThread, Signal
from PIL import Image, ImageEnhance
import numpy as np

from .stamp_detector import StampDetector, AdvancedStampRemover
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ImageProcessingThread(QThread):
    """图像处理线程"""
    
    # 信号定义
    finished = Signal(object)  # 处理完成，传递PIL图像对象
    progress = Signal(int)     # 处理进度
    error = Signal(str)        # 错误信息

    def __init__(self, image_path=None, pil_image=None, rad_num=185, channel_index=0, 
                 is_contrast=False, is_sharpness=False, use_advanced_algorithm=True):
        super().__init__()
        self.image_path = image_path
        self.pil_image = pil_image
        self.rad_num = rad_num
        self.channel_index = channel_index
        self.is_contrast = is_contrast
        self.is_sharpness = is_sharpness
        self.use_advanced_algorithm = use_advanced_algorithm
        
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
                # 直接使用PIL图像对象
                im = self.pil_image.copy()  # 创建副本避免修改原图
                logger.info(f"使用PIL图像对象: 模式={im.mode}, 尺寸={im.size}")
            else:
                # 从文件路径打开图像
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
            
            # 印章去除处理
            self.progress.emit(70)
            result_image = self._remove_stamp(im)
            self.progress.emit(90)
            
            # 发送完成信号
            self.finished.emit(result_image)
            self.progress.emit(100)
            
            logger.info("图像处理完成")
            
        except Exception as e:
            logger.error(f"图像处理失败: {e}")
            self.error.emit(str(e))
            self.finished.emit(None)

    def _remove_stamp(self, pil_image: Image.Image) -> Image.Image:
        """
        去除印章的核心算法
        
        Args:
            pil_image: PIL图像对象
            
        Returns:
            处理后的PIL图像对象
        """
        try:
            if self.use_advanced_algorithm:
                # 使用高级印章检测算法
                logger.info("使用高级印章检测算法")
                remover = AdvancedStampRemover(
                    method='auto',
                    threshold=self.rad_num,
                    channel_index=self.channel_index,
                    min_stamp_size=100,
                    max_stamp_size=1000000,
                    color_tolerance=30,
                    edge_threshold=0.1
                )
                return remover.remove_stamp(pil_image)
            else:
                # 使用简单算法（向后兼容）
                logger.info("使用简单印章检测算法")
                return self._remove_stamp_simple(pil_image)
                
        except Exception as e:
            logger.error(f"印章去除失败: {e}，回退到简单算法")
            return self._remove_stamp_simple(pil_image)
    
    def _remove_stamp_simple(self, pil_image: Image.Image) -> Image.Image:
        """
        简单的印章去除算法（向后兼容）
        """
        np_im = np.array(pil_image)
        
        if len(np_im.shape) == 3:  # 彩色图（RGB 或 RGBA）
            channels = np_im.shape[2]

            # 验证通道索引是否有效
            if self.channel_index >= channels:
                logger.warning(f"通道索引 {self.channel_index} 超出图像通道数 {channels}，使用默认通道 0")
                self.channel_index = 0

            # 确保通道索引在有效范围内
            if self.channel_index < 0:
                self.channel_index = 0
            elif self.channel_index >= channels:
                self.channel_index = channels - 1

            logger.info(f"使用通道索引: {self.channel_index} (通道数: {channels})")

            # 创建掩码
            mask = np_im[:, :, self.channel_index] >= self.rad_num

            # 统计满足条件的像素数
            mask_count = np.sum(mask)
            logger.info(f"检测到 {mask_count} 个满足条件的像素点")

            # 根据通道数创建白色像素
            if channels == 3:
                white = [255, 255, 255]
            elif channels == 4:
                white = [255, 255, 255, 255]  # 包括 alpha 通道
            else:
                raise ValueError(f"不支持的通道数: {channels}")

            # 应用掩码，将印章区域替换为白色
            np_im[mask] = white

        else:
            logger.warning("检测到灰度图像，跳过颜色通道处理")
            return Image.fromarray(np_im)

        # 转回PIL图像
        return Image.fromarray(np_im)
