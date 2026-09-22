# Winstep Nexus 中文全量修复与多版本补丁工具 (Winstep Chinese Localization Fixer)

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%20Windows%2011-blue?style=flat-square&logo=windows" alt="Platform" />
  <img src="https://img.shields.io/badge/Target-Winstep%20Nexus%20%2F%20Xtreme-orange?style=flat-square" alt="Target" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python" alt="Python" />
  <img src="https://img.shields.io/badge/Status-Production%20Ready-brightgreen?style=flat-square" alt="Status" />
</p>

一键彻底解决 **Winstep Nexus / Winstep Xtreme** 在中文 Windows 环境下长期存在的**托盘气泡乱码（Clash/音量/电源/Snipaste 等）、首选项设置标签页缺失、UI按钮文本截断**以及**字体缺字**等全部顽疾。

配备现代图形化界面（GUI）与静默命令行（CLI），内置 AOB 动态特征码扫描器，兼容不同版本的 Winstep 可执行文件。

---

## 📸 修复前后效果对比 (Before vs After)

| 项目 | 修复前（官方原版在中文系统下的缺陷） | 修复后（经本工具一键深度修复） |
| :--- | :--- | :--- |
| **Clash Verge** | `订瑭 詡仱BY`（文字严重破损错位） | **`Clash Verge 2.5.4`<br>`系统代理: off`<br>`TUN: on`<br>`订阅: GO国外`** |
| **扬声器音量** | `扬声器: 静脑` / `静...` | **`扬声器: 静音` / `扬声器: 100%`** |
| **电源与电池** | `97% 可用(已接瓶遵1L` | **`96% 可用(已接通电源)`** |
| **Snipaste** | `截屏快捷㼮...` | **`Snipaste 2.10.8 免费版 (桌面版)`<br>`截屏快捷键: F1`<br>`贴图快捷键: F3`** |
| **首选项设置** | 仅显示 4 个标签页，底部按钮文字被截断 | **完整恢复全部 8 个设置标签页，按钮文字正常** |
| **Dock 标签字体**| 系统默认点阵字体，部分汉字缺失或方框 | **全局渲染为清晰平滑的微软雅黑 (Microsoft YaHei UI)** |

---

## 🔬 乱码底层原理剖析 (Technical Root Cause)

为什么即使系统语言和区域设置正确，Winstep Nexus 悬浮气泡中的特定汉字仍然必定发生乱码？

1. **VB6 运行时字符串封送陷阱：**
   Nexus 核心采用 Visual Basic 6.0 编写。作者在声明 Windows API `ReadProcessMemory` 时，将缓冲区参数定义为了 `ByVal lpBuffer As String`。
   在 VB6 运行时中，向外部 API 传递 `String` 会自动触发两步转换：
   - 调用 API 前：执行 `__vbaStrToAnsi`（分配临时 ANSI 缓冲区传给 API）；
   - API 执行后：自动调用 `__vbaStrToUnicode`（底层即 Windows `MultiByteToWideChar(CP_ACP, ...)`）。

2. **DBCS（双字节字符集）的高位吞字节崩溃：**
   64 位 Windows Explorer 给出的托盘提示信息原本是标准的 **UTF-16 Unicode 双字节原文**。
   - 在英文 Windows（CP1252）下，字节映射为 1:1，后续开发者配合 `StrConv(..., vbFromUnicode)` 可以巧合还原；
   - **但在中文系统（CP936/GBK）下，系统代码页为双字节字符集（DBCS）**。当原生 UTF-16 字节流中出现落在 `0x81 - 0xFE` 范围的高位字节（如“通”的高字节 `0x90`、“阅”的高字节 `0x96`、“音”的高字节 `0x97`）时，GBK 解码器会强行将其误判为**双字节汉字的前导字节（Lead Byte）**并吞并后面的字节。
   - 随后的字节（如 `0x00`）无法与前导字节组成合法汉字，解码器直接将该非法字符丢弃并替换为单字节 `0x3F`（ASCII 问号 `?`），造成**整个后续双字节流奇偶错位破坏**。

3. **本补丁的解决策略：**
   本工具利用逆向工程与 AOB 动态模式匹配，定位并重写了二进制中的全部 6 处托盘读取例程：
   - 彻底切断破坏性的 `__vbaStrToAnsi` 与 `__vbaStrToUnicode` 转换链路；
   - 将预分配的 BSTR 真实内存指针（`StrPtr`）直接注入 `ReadProcessMemory`，实现 **Explorer 原生 UTF-16 Unicode 直读直通**；
   - 末尾安全截断并经由 `__vbaStrCopy` 转交 `StripNull`，全流程 100% 保持 Unicode 零损耗。

---

## 🚀 快速使用 (Quick Start)

### 方式一：直接运行独立程序 (推荐，无需安装 Python)

1. 前往本仓库的 [Releases](../../releases) 页面，下载最新的 `WinstepFixer.exe`。
2. 双击运行 `WinstepFixer.exe`。
3. 点击主界面上的 **【🚀 一键全量深度修复 (推荐)】** 按钮。
4. 程序将自动安全退出 Nexus、创建备份、修补二进制、修复注册表、部署语言包并在桌面上重新启动 Nexus。
5. 悬浮鼠标于 Dock 栏上的托盘图标即可见证完美中文！

### 方式二：从源码运行 (适合开发者)

```bash
# 1. 克隆本仓库
git clone https://github.com/your-username/winstep-nexus-fixer.git
cd winstep-nexus-fixer

# 2. 启动图形化界面 (标准 Python 3.10+，零第三方依赖)
python main.py

# 3. 或者使用命令行静默一键修复
python main.py --fix-all
```

---

## 🛠️ CLI 命令行模式

本工具内置了完整的命令行支持，方便系统管理员、装机脚本或包管理器（Scoop / Chocolatey）自动化执行：

| 命令 | 描述 |
| :--- | :--- |
| `python main.py --check` | 检查当前 Nexus 进程状态、二进制补丁状态及首选项配置 |
| `python main.py --fix-all` | 一键执行全量修复（二进制补丁 + 注册表标签页 + 字体 + 语言包） |
| `python main.py --patch-only` | 仅修补二进制可执行文件中的托盘字符集 Bug |
| `python main.py --restore` | 从备份文件（`Nexus.exe.bak`）恢复官方未修改的原版程序 |
| `python main.py --path "C:\Path\Nexus.exe"` | 手动指定 Nexus.exe 的安装路径 |

---

## 📦 自行打包单文件 EXE

项目根目录下提供了全自动打包脚本 `build.bat`：

```cmd
# 确保已安装 pyinstaller
pip install pyinstaller

# 运行一键构建脚本
build.bat
```
打包成功后，可在 `dist/WinstepFixer.exe` 获取独立的便携式执行程序。

---

## 📂 项目结构

```
winstep-nexus-fixer/
├── core/
│   ├── patcher.py           # 核心二进制 PE 分析器、AOB 签名扫描器与补丁生成引擎
│   ├── process_manager.py   # 跨桌面会话（WinSta0\Default）进程生命周期管理
│   ├── registry_manager.py  # 首选项深色模式、标签页配置与字体注册表管理
│   └── lang_manager.py      # 规范 GB18030 中文语言包部署管理
├── gui/
│   └── app.py               # 现代化 Tkinter GUI 界面与实时日志控制台
├── Languages/               # 修复与补齐后的规范化官方多组件语言包
│   ├── NeXuS/               # 简体中文、繁体中文、香港繁体
│   ├── Update Manager/
│   └── Xtreme/
├── assets/
│   └── screenshots/         # 修复前后对比实测截图
├── main.py                  # CLI 与 GUI 双模式主入口
├── build.bat                # PyInstaller 单文件打包编译脚本
├── LICENSE                  # MIT 开源许可证
└── README.md                # 中文使用文档
```

---

## 🛡️ 安全与还原保障

- **零破坏性：** 首次修补时，工具会在同目录下自动生成原版备份文件 `Nexus.exe.bak`。
- **随时可逆：** 任何时候只要点击界面中的 **【还原官方原版备份】** 或运行 `python main.py --restore`，即可瞬间无损还原所有官方原始文件。

---

## 📄 开源许可证

本项目基于 [MIT License](LICENSE) 开源发布。仅供个人学习、辅助定制与本地化修复使用。Winstep 与 Nexus 为其各自软件著作权人所有。
