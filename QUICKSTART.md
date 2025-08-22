# 快速启动指南

## 🚀 立即开始

### 方法1：直接运行（推荐）
```bash
python run.py
```

### 方法2：模块方式运行
```bash
python -m stamp_remover.main
```

### 方法3：安装后运行
```bash
# 安装项目
pip install -e .

# 运行
stamp-remover
```

## 📋 前置要求

确保已安装Python 3.8+和必要的依赖：

```bash
pip install -r requirements.txt
```

## 🔧 开发环境设置

### 1. 克隆项目
```bash
git clone <your-repo-url>
cd stamp-remover
```

### 2. 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 安装开发依赖
```bash
pip install -e ".[dev]"
```

## 🧪 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_basic.py

# 运行测试并显示覆盖率
pytest --cov=stamp_remover
```

## 📦 项目结构说明

```
stamp_remover/
├── stamp_remover/           # 主包目录
│   ├── __init__.py         # 包初始化
│   ├── main.py             # 主程序入口
│   ├── config.py           # 配置文件
│   ├── core/               # 核心功能模块
│   │   ├── __init__.py
│   │   ├── image_processor.py    # 图像处理核心
│   │   ├── pdf_processor.py      # PDF处理核心
│   │   └── thread_manager.py     # 线程管理
│   ├── ui/                 # 用户界面
│   │   ├── __init__.py
│   │   ├── main_window.py        # 主窗口
│   │   └── ui_main.py            # UI界面定义
│   └── utils/              # 工具函数
│       ├── __init__.py
│       └── helpers.py            # 辅助函数
├── tests/                  # 测试目录
├── docs/                   # 文档目录
├── requirements.txt        # 依赖列表
├── setup.py               # 安装配置
├── pyproject.toml         # 现代Python项目配置
└── run.py                 # 快速启动脚本
```

## 🎯 主要功能

### 单图片处理
- 支持多种图片格式（JPG, PNG, BMP, TIFF）
- 智能印章识别和去除
- 图像增强（对比度、清晰度）
- 实时预览和对比

### PDF批量处理
- 多页PDF转换
- 进度条显示
- 批量印章去除
- 导出为新的PDF

### 线程管理
- 多线程处理，避免界面卡顿
- 智能线程冲突处理
- 资源自动清理

## 🐛 故障排除

### 常见问题

1. **导入错误**
   ```bash
   pip install -r requirements.txt
   ```

2. **PySide6安装失败**
   ```bash
   # Windows
   pip install PySide6
   
   # Linux/macOS
   pip install PySide6
   ```

3. **PDF处理失败**
   - 确保PDF文件没有损坏
   - 检查文件权限
   - 验证PyMuPDF安装

4. **图像处理失败**
   - 检查图片格式是否支持
   - 验证Pillow安装
   - 检查文件路径

### 日志查看

程序运行时会生成日志文件：
- 位置：`logs/stamp_remover.log`
- 包含详细的运行信息和错误信息

## 📞 获取帮助

- 查看完整文档：`README.md`
- 提交Issue：项目GitHub页面
- 运行测试：`pytest tests/`

## 🎉 开始使用

现在你可以：
1. 运行 `python run.py`
2. 选择图片或PDF文件
3. 设置处理参数
4. 开始去除印章！

祝你使用愉快！ 🎊




