# 印章去除工具 (Stamp Remover)

一个印章去除工具，用于处理包含印章的图片和PDF文档。通过智能图像处理技术，自动识别并去除印章区域，实现文档的清洁化处理。

## ✨ 功能特性

- **单图片处理**: 支持多种图片格式，智能去除印章
- **PDF批量处理**: 批量处理多页PDF文档
- **智能颜色识别**: 支持红色、绿色、蓝色印章的精确识别
- **图像增强**: 内置对比度和清晰度增强功能
- **PDF重新生成**: 将处理后的图片按原顺序重新组合成PDF文件
- **实时预览**: 处理前后对比，效果一目了然
- **多线程处理**: 支持多线程并行处理，提升处理速度

## 🚀 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行程序

```bash
python -m stamp_remover.main
```

或者直接运行：

```bash
python stamp_remover/main.py
```

## 📦 项目结构

```
stamp-remover/
├── stamp_remover/           # 主包目录
│   ├── __init__.py
│   ├── main.py             # 主程序入口
│   ├── core/               # 核心功能模块
│   │   ├── __init__.py
│   │   ├── image_processor.py    # 图像处理核心
│   │   ├── pdf_processor.py      # PDF处理核心
│   │   └── thread_manager.py     # 线程管理
│   ├── ui/                 # 用户界面
│   │   ├── __init__.py
│   │   ├── main_window.py        # 主窗口
│   │   ├── ui_main.py            # UI界面定义
│   │   └── resources/            # 资源文件
│   ├── config.py           # 配置文件
│   └── utils/              # 工具函数
│       ├── __init__.py
│       └── helpers.py            # 辅助函数
├── tests/                  # 测试目录
├── docs/                   # 文档目录
├── requirements.txt        # 依赖列表
├── setup.py               # 安装配置
└── README.md              # 项目说明
```

## 🛠️ 技术架构

- **GUI框架**: PySide6 (Qt6)
- **图像处理**: Pillow (PIL) + NumPy
- **PDF处理**: PyMuPDF
- **多线程**: QThread + ThreadPoolExecutor
- **项目构建**: setuptools + 现代Python包结构

## 📋 系统要求

- Python 3.8+
- Windows 10/11, macOS 10.14+, Ubuntu 18.04+
- 内存: 4GB+
- 存储: 100MB可用空间

## 🔧 开发环境设置

### 克隆项目

```bash
git clone https://github.com/yourusername/stamp-remover.git
cd stamp-remover
```

### 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows
```

### 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 运行测试

```bash
pytest tests/
```

## 📖 使用说明

### 单图片处理

1. 点击"选择图片"按钮选择要处理的图片
2. 设置印章颜色（红色/绿色/蓝色）
3. 调整阈值（默认185）
4. 选择是否启用图像增强功能
5. 点击"开始执行"进行处理
6. 查看处理结果并保存

### PDF批量处理

1. 点击"选择PDF"按钮选择PDF文件
2. 等待PDF页面转换为图片
3. 在左侧列表中选择要处理的页面
4. 设置处理参数
5. 点击"开始执行"处理当前页面
6. 使用"保存到本地"将所有处理后的图片重新组合成PDF文件

## ⚙️ 配置说明

### 线程配置

在 `stamp_remover/config.py` 中可以调整以下参数：

```python
# PDF处理配置
PDF_PROCESSING_CONFIG = {
    'default_dpi': 150,           # 默认DPI
    'max_workers': 4,             # 最大工作线程数
    'enable_multithreading': True # 是否启用多线程
}

# 线程配置
THREAD_CONFIG = {
    'max_workers': 4,             # 默认线程数
    'timeout': 30000              # 超时时间（毫秒）
}
```

### 图像处理配置

```python
# 图像处理配置
IMAGE_PROCESSING_CONFIG = {
    'default_threshold': 185,     # 默认阈值
    'contrast_enhancement': 2.0,  # 对比度增强
    'sharpness_enhancement': 2.0  # 清晰度增强
}
```

## 🔍 功能详解

### 印章识别原理

工具通过分析图像的颜色通道来识别印章区域：

- **红色印章**: 分析红色通道（R通道）
- **绿色印章**: 分析绿色通道（G通道）
- **蓝色印章**: 分析蓝色通道（B通道）

当某个通道的像素值超过设定阈值时，该像素被认为是印章区域，会被替换为白色。

### 图像增强功能

- **对比度增强**: 提高图像的对比度，使印章更明显
- **清晰度增强**: 提高图像的清晰度，改善处理效果

### 多线程处理

- 支持多线程并行处理PDF页面
- 可配置的工作线程数量
- 自动任务调度和进度跟踪

### PDF重新生成

- 将处理后的图片按原始PDF的页面顺序重新组合
- 生成新的PDF文件，去除印章后的清洁版本
- 保存过程中显示进度条，实时反馈处理状态
- 保持原PDF的页面布局和顺序

## 🧪 测试

### 运行测试套件

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_image_processor.py

# 运行特定测试函数
pytest tests/test_image_processor.py::test_remove_stamp
```

### 测试覆盖率

```bash
# 生成覆盖率报告
pytest --cov=stamp_remover

# 生成HTML覆盖率报告
pytest --cov=stamp_remover --cov-report=html
```

## 📚 API文档

### 核心类

#### ImageProcessingThread

图像处理线程类，负责在后台处理图像。

```python
from stamp_remover.core.image_processor import ImageProcessingThread

thread = ImageProcessingThread(
    image_path="image.jpg",
    rad_num=185,
    channel_index=0,
    is_contrast=True,
    is_sharpness=True
)
```

#### PdfProcessingThread

PDF处理线程类，负责处理PDF文档。

```python
from stamp_remover.core.pdf_processor import PdfProcessingThread

thread = PdfProcessingThread(
    pdf_path="document.pdf",
    dpi=150,
    max_workers=4
)
```

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

### 开发规范

- 遵循PEP 8代码风格
- 添加适当的类型注解
- 编写单元测试
- 更新相关文档

## 🐛 问题反馈

如果遇到问题，请：

1. 检查是否满足系统要求
2. 查看错误日志
3. 在GitHub Issues中搜索类似问题
4. 创建新的Issue，并提供详细的错误信息

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [PySide6](https://doc.qt.io/qtforpython/) - 跨平台GUI框架
- [Pillow](https://python-pillow.org/) - 图像处理库
- [PyMuPDF](https://pymupdf.readthedocs.io/) - PDF处理库
- [NumPy](https://numpy.org/) - 数值计算库



## 📈 更新日志

### v1.1.0 (性能极限优化版)
- **极限内存优化**: 采用临时物理文件落盘策略代替内存数据缓冲，彻底解决在处理超大 PDF（如上千页文档）时引发的 OOM (Out Of Memory) 内存溢出或闪退问题。
- **真·多进程加速**: 突破 Python GIL (全局解释器锁) 以及 PyMuPDF 底层 C 语言锁的限制，将 `ThreadPoolExecutor` 升级为 `ProcessPoolExecutor`，实现真正的多核物理并行计算。
- **智能资源调度**: 自动读取当前电脑 CPU 真实核心数，智能拉起最高效的进程数量，并强制预留核心以保障系统及 UI 始终流畅不卡顿。
- **UI 交互优化**: 解除主窗口原有的尺寸锁定限制，现已支持用户自由拖拽缩放和最大化窗口，以完美适应不同分辨率显示器。

### v1.0.0
- 初始版本发布
- 支持单图片和PDF处理
- 基础多线程处理支持
- 智能印章识别

---

如果这个项目对你有帮助，请给它一个 ⭐️ 星标！

