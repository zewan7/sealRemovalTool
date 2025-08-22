#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
主窗口类
"""

import os
import sys
import logging
from datetime import datetime
from typing import Optional

from PySide6.QtCore import Qt, Slot, QThread, Signal
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QMessageBox, 
    QProgressBar, QLabel, QVBoxLayout, QHBoxLayout, QWidget,
    QListWidgetItem
)
from PySide6.QtGui import QPixmap, QIcon

from PIL import Image
from PIL.ImageQt import ImageQt

from ..core import ImageProcessingThread, PdfProcessingThread, ThreadManager, PdfRegenerationThread
from .ui_main import Ui_MainWindow
from ..config import PDF_PROCESSING_CONFIG, THREAD_CONFIG

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow, Ui_MainWindow):
    """主窗口类"""
    
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.setFixedSize(self.size())
        self.setWindowIcon(QIcon("stamp_remover/ico/f.ico"))
        self._init_ui()
        self._init_thread_manager()
        self._init_variables()
        
        # 设置日志
        self._setup_logging()
        
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
    def _init_ui(self):
        """初始化UI"""
        # 设置图像标签的缩放属性
        self.label_3.setScaledContents(True)
        self.label_4.setScaledContents(True)
        self.label_5.setScaledContents(True)
        self.label_6.setScaledContents(True)
        
        # 连接信号
        self.listWidget.itemClicked.connect(self.on_listWidget_itemClicked)
        self.comboBox.currentIndexChanged.connect(self.on_color_changed)
        self.comboBox_2.currentIndexChanged.connect(self.on_pdf_color_changed)
        
        # 添加进度条到PDF处理区域
        self._add_progress_bar()
        
        # 设置窗口标题
        self.setWindowTitle("印章去除工具 v1.0.0")
        
    def _add_progress_bar(self):
        """添加进度条到PDF处理区域"""
        # 创建进度条容器
        progress_widget = QWidget()
        progress_layout = QVBoxLayout(progress_widget)
        
        # 进度条标签
        self.progress_label = QLabel("准备就绪")
        progress_layout.addWidget(self.progress_label)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel("")
        progress_layout.addWidget(self.status_label)
        
        # 尝试添加到合适的布局中
        self._add_progress_to_layout(progress_widget)
        
    def _add_progress_to_layout(self, progress_widget):
        """尝试将进度条添加到合适的布局中"""
        # 尝试多个可能的布局名称
        layout_names = ['verticalLayout_4', 'verticalLayout_2', 'horizontalLayout_1']
        
        for layout_name in layout_names:
            if hasattr(self, layout_name):
                layout = getattr(self, layout_name)
                try:
                    layout.addWidget(progress_widget)
                    print(f"进度条已添加到 {layout_name}")
                    return
                except Exception as e:
                    print(f"无法添加到 {layout_name}: {e}")
                    continue
        
        # 如果都失败了，尝试添加到主布局
        try:
            if hasattr(self, 'centralwidget'):
                central_layout = self.centralwidget.layout()
                if central_layout:
                    central_layout.addWidget(progress_widget)
                    print("进度条已添加到主布局")
                else:
                    print("警告: 无法找到合适的布局位置")
        except Exception as e:
            print(f"添加进度条失败: {e}")
        
    def _init_thread_manager(self):
        """初始化线程管理器"""
        self.thread_manager = ThreadManager()
        
    def _init_variables(self):
        """初始化变量"""
        self.file_name: Optional[str] = None
        self.processed_image: Optional[Image.Image] = None
        self.pdf_processing_thread: Optional[PdfProcessingThread] = None
        self.is_processing_pdf_image = False
        self.processed_images: list = []  # 存储所有处理后的图片
        
    ###########################################################################
    # 单图片处理
    ###########################################################################
    
    @Slot()
    def on_pushButton_clicked(self):
        """选择图片"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "选择图片",
            "",
            "图片文件 (*.jpg *.jpeg *.png *.bmp *.tiff);;所有文件 (*)"
        )

        if file_name:
            logger.info(f"选择的图片: {file_name}")
            self.file_name = file_name
            
            # 显示图片
            pixmap = QPixmap(self.file_name)
            self.label_3.setPixmap(
                pixmap.scaled(self.label_3.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            
            # 显示图像信息
            self._show_image_info(file_name)
        else:
            logger.info("用户取消了选择图片")

    def _show_image_info(self, image_path: str):
        """显示图像信息"""
        try:
            with Image.open(image_path) as img:
                mode = img.mode
                size = img.size
                logger.info(f"图像信息: 模式={mode}, 尺寸={size}")
                
                # 根据图像模式设置可用的颜色通道
                if mode in ['RGB', 'RGBA']:
                    channels = len(mode)
                    logger.info(f"图像有 {channels} 个通道: {mode}")
                    
                    # 更新颜色选择提示
                    if channels == 3:
                        logger.info("可用颜色: 红色(0), 绿色(1), 蓝色(2)")
                    elif channels == 4:
                        logger.info("可用颜色: 红色(0), 绿色(1), 蓝色(2), Alpha(3)")
                else:
                    logger.warning(f"图像模式 {mode} 不支持颜色通道处理")
        except Exception as e:
            logger.error(f"无法读取图像信息: {e}")

    @Slot()
    def on_pushButton_2_clicked(self):
        """开始执行图像处理"""
        if not self.file_name:
            QMessageBox.information(self, "提示", "请先选择图片")
            return

        # 获取处理参数
        channel_index = self.comboBox.currentIndex()
        threshold = self.spinBox.value() if self.spinBox.value() > 0 else 185
        is_contrast = self.checkBox.isChecked()
        is_sharpness = self.checkBox_2.isChecked()
        
        # 创建并启动图像处理线程
        thread = ImageProcessingThread(
            image_path=self.file_name,
            rad_num=threshold,
            channel_index=channel_index,
            is_contrast=is_contrast,
            is_sharpness=is_sharpness
        )
        
        # 注册线程
        self.thread_manager.register_thread("image_processing", thread)
        
        # 连接信号
        thread.finished.connect(self.on_image_processed)
        thread.progress.connect(self._on_image_progress)
        thread.error.connect(self._on_image_error)
        
        # 启动线程
        if self.thread_manager.start_thread("image_processing"):
            logger.info("图像处理线程已启动")
        else:
            QMessageBox.critical(self, "错误", "启动图像处理线程失败")

    def _on_image_progress(self, progress: int):
        """图像处理进度回调"""
        logger.info(f"图像处理进度: {progress}%")

    def _on_image_error(self, error_msg: str):
        """图像处理错误回调"""
        logger.error(f"图像处理错误: {error_msg}")
        QMessageBox.critical(self, "处理错误", f"图像处理失败:\n{error_msg}")

    @Slot()
    def on_image_processed(self, processed_image: Image.Image):
        """图像处理完成"""
        self.processed_image = processed_image
        
        if self.processed_image is not None:
            # 将PIL图像转换为QPixmap并显示
            pixmap = QPixmap.fromImage(ImageQt(self.processed_image.convert("RGBA")))
            self.label_4.setPixmap(
                pixmap.scaled(self.label_4.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            logger.info("图像处理完成")
        else:
            logger.error("图像处理失败")
            QMessageBox.warning(self, "警告", "图像处理失败")

    @Slot()
    def on_pushButton_3_clicked(self):
        """保存处理后的图片"""
        if not self.processed_image:
            QMessageBox.information(self, "提示", "没有可保存的处理后图片")
            return

        # 生成建议的文件名
        original_file_name = os.path.basename(self.file_name)
        name, ext = os.path.splitext(original_file_name)
        current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        suggested_file_name = f"{name}_processed_{current_time_str}"
        
        # 选择保存路径
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "保存图片",
            suggested_file_name,
            "PNG 文件 (*.png);;JPEG 文件 (*.jpg *.jpeg);;BMP 文件 (*.bmp);;TIFF 文件 (*.tiff);;所有文件 (*)"
        )
        
        if file_name:
            try:
                # 根据文件扩展名选择格式
                if file_name.lower().endswith(('.jpg', '.jpeg')):
                    format = 'JPEG'
                elif file_name.lower().endswith('.png'):
                    format = 'PNG'
                elif file_name.lower().endswith('.bmp'):
                    format = 'BMP'
                elif file_name.lower().endswith('.tiff'):
                    format = 'TIFF'
                else:
                    format = 'PNG'
                
                # 保存图片
                self.processed_image.save(file_name, format=format)
                logger.info(f"图片已保存至: {file_name}")
                QMessageBox.information(self, "成功", f"图片已保存:\n{file_name}")
                
            except Exception as e:
                logger.error(f"保存图片失败: {e}")
                QMessageBox.critical(self, "保存失败", f"保存图片失败:\n{str(e)}")

    @Slot()
    def on_pushButton_7_clicked(self):
        """重置阈值"""
        self.spinBox.setValue(185)

    ###########################################################################
    # PDF处理
    ###########################################################################
    
    @Slot()
    def on_pushButton_5_clicked(self):
        """选择PDF文件"""
        input_pdf_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择PDF文件",
            "",
            "PDF文件 (*.pdf);;所有文件 (*)"
        )
        
        if input_pdf_path:
            logger.info(f"选择的PDF: {input_pdf_path}")
            self._start_pdf_processing(input_pdf_path)

    def _start_pdf_processing(self, pdf_path: str):
        """开始PDF处理"""
        # 只显示进度条，隐藏所有文字标签
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.progress_label.setVisible(False)  # 隐藏进度标签
        self.status_label.setVisible(False)    # 隐藏状态标签
        
        # 从配置文件读取设置
        max_workers = PDF_PROCESSING_CONFIG.get('max_workers', 4)
        enable_multithreading = PDF_PROCESSING_CONFIG.get('enable_multithreading', True)
        
        # 创建PDF处理线程
        if enable_multithreading:
            self.pdf_processing_thread = PdfProcessingThread(
                pdf_path=pdf_path,
                dpi=PDF_PROCESSING_CONFIG.get('default_dpi', 150),
                max_workers=max_workers
            )
            logger.info(f"使用多线程处理PDF，工作线程数: {max_workers}")
        else:
            # 单线程模式
            self.pdf_processing_thread = PdfProcessingThread(
                pdf_path=pdf_path,
                dpi=PDF_PROCESSING_CONFIG.get('default_dpi', 150),
                max_workers=1
            )
            logger.info("使用单线程处理PDF")
        
        # 连接信号
        self.pdf_processing_thread.finished.connect(self.on_pdf_processed)
        self.pdf_processing_thread.progress.connect(self._on_pdf_progress)
        self.pdf_processing_thread.status.connect(self._on_pdf_status)
        self.pdf_processing_thread.error.connect(self._on_pdf_error)
        
        # 启动线程
        self.pdf_processing_thread.start()

    def _on_pdf_progress(self, current: int, total: int):
        """PDF处理进度回调"""
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        # 不显示任何进度文字，只更新进度条

    def _on_pdf_status(self, status: str):
        """PDF处理状态回调"""
        # 不显示状态信息，只记录日志
        logger.info(f"PDF处理状态: {status}")

    def _on_pdf_error(self, error_msg: str):
        """PDF处理错误回调"""
        logger.error(f"PDF处理错误: {error_msg}")
        QMessageBox.critical(self, "PDF处理错误", f"PDF处理失败:\n{error_msg}")
        
        # 隐藏进度条
        self.progress_bar.setVisible(False)

    @Slot()
    def on_pdf_processed(self, output_images: list):
        """PDF处理完成"""
        # 隐藏进度条
        self.progress_bar.setVisible(False)
        
        # 清空列表
        self.listWidget.clear()
        
        if output_images:
            # 存储图片数据到内存
            self.pdf_images_data = output_images
            
            # 添加图片到列表（显示页码）
            for i, img_data in enumerate(output_images):
                page_name = f"第 {i + 1} 页"
                item = QListWidgetItem(page_name)
                item.setData(Qt.UserRole, i)  # 存储索引而不是文件路径
                self.listWidget.addItem(item)
            
            logger.info(f"成功处理了{len(output_images)}页")
            
            # 不显示任何状态信息，只记录日志
            if hasattr(self, 'pdf_processing_thread'):
                mode = "多线程" if self.pdf_processing_thread.max_workers > 1 else "单线程"
                thread_count = self.pdf_processing_thread.max_workers
                logger.info(f"使用{mode}模式处理，线程数: {thread_count}")
        else:
            logger.warning("PDF处理完成，但没有生成任何图片")
            self.pdf_images_data = []

    @Slot()
    def on_listWidget_itemClicked(self, item):
        """PDF页面点击事件"""
        # 如果正在处理，先取消
        if self.is_processing_pdf_image:
            self._cancel_pdf_image_processing()
        
        # 获取图片索引
        image_index = item.data(Qt.UserRole)
        if image_index is None or not hasattr(self, 'pdf_images_data'):
            return
            
        # 从内存中获取图片数据
        if 0 <= image_index < len(self.pdf_images_data):
            img_data = self.pdf_images_data[image_index]
            
            # 将字节数据转换为QPixmap
            from PIL import Image
            import io
            from PIL.ImageQt import ImageQt
            
            # 从字节数据创建PIL图像
            pil_img = Image.open(io.BytesIO(img_data))
            # 转换为RGBA模式以确保兼容性
            if pil_img.mode != 'RGBA':
                pil_img = pil_img.convert('RGBA')
            
            # 转换为QPixmap
            qimage = ImageQt(pil_img)
            pixmap = QPixmap.fromImage(qimage)
            
            # 显示原始图片
            self.label_5.setPixmap(
                pixmap.scaled(self.label_5.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            
            # 显示处理状态
            self.label_6.setText("正在处理中...")
            
            # 开始处理（传递PIL图像对象）
            self._start_pdf_image_processing_from_pil(pil_img)
        else:
            logger.error(f"图片索引超出范围: {image_index}")

    def _start_pdf_image_processing_from_pil(self, pil_image):
        """从PIL图像开始处理PDF图片"""
        self.is_processing_pdf_image = True
        
        # 创建处理线程（支持PIL图像输入）
        thread = ImageProcessingThread(
            pil_image=pil_image,  # 传递PIL图像对象
            rad_num=self.spinBox_2.value(),
            channel_index=self.comboBox_2.currentIndex(),
            is_contrast=self.checkBox_3.isChecked(),
            is_sharpness=self.checkBox_4.isChecked()
        )
        
        # 注册线程
        self.thread_manager.register_thread("pdf_image_processing", thread)
        
        # 连接信号
        thread.finished.connect(self.on_pdf_image_processed)
        thread.error.connect(self._on_pdf_image_error)
        
        # 启动线程
        if self.thread_manager.start_thread("pdf_image_processing"):
            logger.info("PDF图片处理线程已启动")
        else:
            QMessageBox.critical(self, "错误", "启动PDF图片处理线程失败")

    def _cancel_pdf_image_processing(self):
        """取消PDF图片处理"""
        if self.thread_manager.is_thread_running("pdf_image_processing"):
            self.thread_manager.stop_thread("pdf_image_processing")
            self.is_processing_pdf_image = False
            logger.info("取消之前的PDF图片处理")

    @Slot()
    def on_pdf_image_processed(self, processed_image: Image.Image):
        """PDF图片处理完成"""
        self.is_processing_pdf_image = False
        
        if processed_image is not None:
            # 显示处理后的图片
            pixmap = QPixmap.fromImage(ImageQt(processed_image.convert("RGBA")))
            self.label_6.setPixmap(
                pixmap.scaled(self.label_6.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
            
            # 存储处理后的图片
            self.processed_images.append(processed_image)
            
            logger.info("PDF图片处理完成")
        else:
            logger.error("PDF图片处理失败")
            self.label_6.setText("处理失败")

    def _on_pdf_image_error(self, error_msg: str):
        """PDF图片处理错误"""
        logger.error(f"PDF图片处理错误: {error_msg}")
        self.label_6.setText(f"处理失败: {error_msg}")
        self.is_processing_pdf_image = False
        
        # 显示错误对话框
        QMessageBox.critical(self, "处理错误", f"PDF图片处理失败:\n{error_msg}")
        
        # 清理状态
        self.label_6.clear()

    @Slot()
    def on_pushButton_6_clicked(self):
        """开始执行PDF图片处理"""
        # 获取当前选中的项目
        current_item = self.listWidget.currentItem()
        if current_item:
            self.on_listWidget_itemClicked(current_item)
        else:
            QMessageBox.information(self, "提示", "请先选择一个PDF页面")

    @Slot()
    def on_pushButton_4_clicked(self):
        """重置PDF处理阈值"""
        self.spinBox_2.setValue(185)
    
    @Slot()
    def on_pushButton_8_clicked(self):
        """导出所有处理后的图像为PDF"""
        if not hasattr(self, 'pdf_images_data') or not self.pdf_images_data:
            QMessageBox.information(self, "提示", "没有可导出的PDF图片数据")
            return
        
        # 选择保存路径
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存PDF",
            "processed_document.pdf",
            "PDF文件 (*.pdf)"
        )
        
        if save_path:
            # 开始PDF重新生成过程
            self._start_pdf_regeneration(save_path)

    def _start_pdf_regeneration(self, save_path: str):
        """开始PDF重新生成过程"""
        try:
            # 显示进度条
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)
            self.progress_label.setVisible(True)
            self.progress_label.setText("正在重新生成PDF...")
            
            # 获取当前的印章去除参数
            threshold = self.spinBox_2.value()
            channel_index = self.comboBox_2.currentIndex()
            enable_contrast = self.checkBox_3.isChecked()
            enable_sharpness = self.checkBox_4.isChecked()
            
            # 从配置文件读取线程数
            max_workers = PDF_PROCESSING_CONFIG.get('max_workers', 4)
            
            # 创建PDF重新生成线程
            self.pdf_regeneration_thread = PdfRegenerationThread(
                pdf_images_data=self.pdf_images_data,
                save_path=save_path,
                threshold=threshold,
                channel_index=channel_index,
                enable_contrast=enable_contrast,
                enable_sharpness=enable_sharpness,
                max_workers=max_workers
            )
            
            # 连接信号
            self.pdf_regeneration_thread.finished.connect(self.on_pdf_regeneration_finished)
            self.pdf_regeneration_thread.progress.connect(self._on_pdf_regeneration_progress)
            self.pdf_regeneration_thread.error.connect(self._on_pdf_regeneration_error)
            
            # 启动线程
            self.pdf_regeneration_thread.start()
            
            logger.info(f"开始重新生成PDF: {save_path}")
            logger.info(f"参数: 阈值={threshold}, 通道={channel_index}, 对比度={enable_contrast}, 清晰度={enable_sharpness}, 线程数={max_workers}")
            
        except Exception as e:
            logger.error(f"启动PDF重新生成失败: {e}")
            QMessageBox.critical(self, "错误", f"启动PDF重新生成失败:\n{str(e)}")
            self._hide_pdf_regeneration_progress()

    def _on_pdf_regeneration_progress(self, current: int, total: int):
        """PDF重新生成进度回调"""
        progress = int((current / total) * 100)
        self.progress_bar.setValue(progress)
        
        # 根据进度显示不同的状态信息
        if current == 0:
            self.progress_label.setText("正在准备处理...")
        elif current < total:
            self.progress_label.setText(f"正在处理图像: {current}/{total} 页 ({progress}%)")
        else:
            self.progress_label.setText("正在组合PDF文件...")

    def _on_pdf_regeneration_error(self, error_msg: str):
        """PDF重新生成错误回调"""
        logger.error(f"PDF重新生成错误: {error_msg}")
        QMessageBox.critical(self, "PDF重新生成错误", f"PDF重新生成失败:\n{error_msg}")
        self._hide_pdf_regeneration_progress()

    def on_pdf_regeneration_finished(self, success: bool, save_path: str):
        """PDF重新生成完成"""
        self._hide_pdf_regeneration_progress()
        
        if success:
            QMessageBox.information(self, "成功", f"PDF重新生成成功:\n{save_path}")
            logger.info(f"PDF重新生成成功: {save_path}")
        else:
            QMessageBox.critical(self, "失败", "PDF重新生成失败")
            logger.error("PDF重新生成失败")

    def _hide_pdf_regeneration_progress(self):
        """隐藏PDF重新生成进度条"""
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)

    ###########################################################################
    # 颜色选择事件
    ###########################################################################
    
    def on_color_changed(self, index: int):
        """单图片处理颜色选择变化"""
        color_names = ["红色", "绿色", "蓝色"]
        if 0 <= index < len(color_names):
            logger.info(f"单图片处理选择颜色: {color_names[index]} (通道 {index})")
        else:
            logger.warning(f"无效的颜色索引: {index}")

    def on_pdf_color_changed(self, index: int):
        """PDF处理颜色选择变化"""
        color_names = ["红色", "绿色", "蓝色"]
        if 0 <= index < len(color_names):
            logger.info(f"PDF处理选择颜色: {color_names[index]} (通道 {index})")
        else:
            logger.warning(f"无效的颜色索引: {index}")

    ###########################################################################
    # 窗口事件
    ###########################################################################
    
    def closeEvent(self, event):
        """窗口关闭事件"""
        logger.info("正在关闭应用程序...")
        
        try:
            # 清理所有线程
            if hasattr(self, 'thread_manager'):
                self.thread_manager.cleanup_all()
            
            # 清理PDF处理线程的临时文件
            if hasattr(self, 'pdf_processing_thread') and self.pdf_processing_thread:
                try:
                    self.pdf_processing_thread.cleanup()
                except Exception as e:
                    logger.error(f"清理PDF处理线程失败: {e}")
            
            # 清理PDF重新生成线程的临时文件
            if hasattr(self, 'pdf_regeneration_thread') and self.pdf_regeneration_thread:
                try:
                    self.pdf_regeneration_thread.cleanup()
                except Exception as e:
                    logger.error(f"清理PDF重新生成线程失败: {e}")
            
            logger.info("资源清理完成")
            
        except Exception as e:
            logger.error(f"关闭时清理资源失败: {e}")
        
        event.accept()
        logger.info("应用程序已关闭")
