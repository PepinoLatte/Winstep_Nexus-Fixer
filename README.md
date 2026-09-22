# Winstep Nexus Localization Fixer

[简体中文](README.md) | [English](README_EN.md)

用于修复 Winstep Nexus 与 Winstep Xtreme 在中文 Windows 环境下的系统托盘气泡乱码、多国语言列表乱码、首选项设置标签页缺失、UI 按钮截断以及字体显示异常的自动化补丁工具。

提供图形界面（GUI）与命令行（CLI）两种模式，通过特征码匹配（AOB Scan）定位目标指令，适配不同版本的 Winstep 可执行文件。

---

## 修复项目

| 模块 | 原版现象（中文环境） | 修复后状态 |
| :--- | :--- | :--- |
| **系统托盘气泡** | 代理节点、音量、电池等提示汉字错位或乱码 | 原生 UTF-16 文本完整显示 |
| **首选项语言列表** | 非 ASCII 语种自称乱码（代码页冲突引发） | 规范化命名，明确标注简体中文与繁体中文 |
| **首选项设置面板** | 深色模式下 8 个标签页折叠缺失为 4 个，底部按钮截断 | 恢复完整 8 个标签页，按钮布局正常 |
| **图标标签字体** | 系统默认字体部分汉字缺字、重影或显示为方框 | 自动配置为微软雅黑（Microsoft YaHei UI） |
| **官方语言文件** | 翻译遗漏或时间戳异常导致词条无法加载 | 部署标准化 GB18030 语言文件 |

---

## 下载与版本选择

补丁核心针对 32 位（x86）PE 程序修补，在 32 位和 64 位 Windows 下通用适配。请根据当前操作系统的版本选择对应的工具版本：

| 推荐顺序 | 文件名称 | 适用系统 | 架构 | 说明 |
| :---: | :--- | :--- | :--- | :--- |
| 主流推荐 | `WinstepFixer-v1.0.0-x64-Win10-Win11.zip` | Windows 10 / 11 | 64 位 (x64) | 现代 64 位系统首选，支持 Per-Monitor V2 高分屏自适应 |
| 次选兼容 | `WinstepFixer-v1.0.0-x86-Win10-Win11.zip` | Windows 10 / 11 | 32 位 (x86) | 适用于 32 位系统，或在 64 位系统上以 32 位原生模式运行 |
| 老机专用 | `WinstepFixer-v1.0.0-x86-Win7-Win8-Legacy.zip` | Windows 7 / 8 / 8.1 / 10 / 11 | 32 位 (x86) | 针对老旧系统构建，基于兼容 Win7 的 Python 3.8 x86 运行时 |

最新编译包可在 [Releases 页面](https://github.com/PepinoLatte/Winstep_Nexus-Fixer/releases) 获取。

---

## 使用方法

### 方式一：运行可执行文件（推荐）

1. 下载对应系统的 ZIP 压缩包并解压。
2. 运行 `WinstepFixer.exe`。
3. 程序会自动检测 `Nexus.exe` 路径；如未检测到，可点击“浏览”手动指定。
4. 点击 **【一键全量深度修复】**。
5. 工具会自动关闭相关进程、备份原文件至 `Nexus.exe.bak`、打入补丁、配置注册表、部署语言包并重启 Nexus。

若需还原，可点击界面中的“还原官方原版备份”或使用命令行参数 `--restore`。

### 方式二：通过源码运行

环境要求：Python 3.8+（仅依赖标准库，无需安装额外第三方包）。

```bash
git clone https://github.com/PepinoLatte/Winstep_Nexus-Fixer.git
cd winstep-nexus-fixer

# 启动图形界面
python main.py

# 命令行全量修复
python main.py --fix-all
```

---

## 命令行参数

适用于脚本集成与静默部署：

```text
用法: main.py [-h] [--fix-all] [--patch-only] [--check] [--restore] [--path PATH] [--gui]

参数:
  -h, --help    显示帮助信息
  --fix-all     执行全量修复（补丁、注册表、字体及语言包）
  --patch-only  仅对 Nexus.exe 应用二进制补丁
  --check       检查进程运行状态、补丁状态及配置项
  --restore     从备份文件恢复原始 Nexus.exe
  --path PATH   手动指定 Nexus.exe 文件路径
  --gui         启动图形界面
```

---

## 技术原理

Winstep Nexus 核心基于 Visual Basic 6.0 开发。托盘气泡乱码的根本原因是 VB6 运行时处理 API 字符串封送时的机制缺陷：

1. **API 参数封送缺陷**  
   程序声明 Win32 API `ReadProcessMemory` 时，将缓冲区参数定义为 `ByVal lpBuffer As String`。VB6 在按值传递字符串给外部 DLL 时，会在调用前通过 `__vbaStrToAnsi` 转为临时 ANSI 缓冲区，调用后再通过 `__vbaStrToUnicode`（即 `MultiByteToWideChar(CP_ACP, ...)`）转回 Unicode。
2. **DBCS 代码页吞字节**  
   Explorer 托盘工具栏（`ToolbarWindow32`）传出的文本为 UTF-16 LE 双字节流。在中文系统（代码页 936 / GBK）下，当 UTF-16 高字节落在 `0x81 - 0xFE` 范围（如“通”的高字节 `0x90`、“音”的高字节 `0x97`）时，GBK 解析器会将其误认为双字节前导字节（Lead Byte）并强制吞并后续字节。无法映射的字节被替换为 `0x3F`（`?`），造成后续字节对齐错位并引发乱码。
3. **修复方案**  
   本工具通过特征码扫描（AOB Scan）定位可执行文件中的托盘读取例程，绕过 ANSI/Unicode 往返转换，直接将预分配的 BSTR 指针传给 `ReadProcessMemory` 进行原生 UTF-16 读取，保证字节流完整。

---

## 项目结构

```text
winstep-nexus-fixer/
├── .github/workflows/
│   └── build-releases.yml  # GitHub Actions 多架构自动构建
├── core/
│   ├── patcher.py           # PE 分析、特征码扫描与二进制修补
│   ├── process_manager.py   # Nexus 进程检测与生命周期管理
│   ├── registry_manager.py  # 深色模式与字体注册表管理
│   └── lang_manager.py      # 语言包部署与编码规范化
├── gui/
│   └── app.py               # Tkinter 高分屏自适应界面
├── Languages/               # 规范化中文语言包
├── assets/screenshots/      # 修复前后对比图
├── main.py                  # CLI / GUI 统一入口
├── build.bat                # 本地打包脚本
├── LICENSE                  # MIT 许可证
├── README.md                # 中文说明文档
└── README_EN.md             # 英文说明文档
```

---

## 开源协议

本项目基于 [MIT License](LICENSE) 开源发布。仅用于学习研究与系统本地化兼容性修复，相关软件版权归原开发商所有。
