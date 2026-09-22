# Winstep Nexus 中文与乱码修复补丁 (Winstep Chinese Localization Fixer)

用于修复 Winstep Nexus / Winstep Xtreme 在中文 Windows 系统下的系统托盘气泡乱码、首选项设置标签页缺失、UI 按钮文本截断以及中文字体显示缺陷的补丁工具。

提供图形界面（GUI）与命令行（CLI）两种运行方式，采用特征码匹配（AOB Scan）定位目标例程，可适配不同版本的 Winstep 可执行文件。





## 修复内容说明

| 模块 | 原版现象（中文系统下） | 修复后状态 |
| :--- | :--- | :--- |
| **系统托盘气泡 (Clash / 代理)** | 悬浮提示中汉字错位（如 `订瑭 詡仱BY`） | 完整显示 UTF-16 文本（如 `订阅: GO国外`） |
| **系统托盘气泡 (音量 / 扬声器)** | 提示尾字乱码（如 `扬声器: 静脑` / `静...`） | 正常显示（如 `扬声器: 静音` 或音量百分比） |
| **系统托盘气泡 (电源 / 电池)** | 状态乱码（如 `97% 可用(已接瓶遵1L`） | 正常显示（如 `XX% 可用(已接通电源)`） |
| **首选项设置面板 (Preferences)** | 深色模式下 8 个标签页缺失折叠为 4 个，底部按钮截断 | 恢复完整的 8 个设置页，按钮文字正常对齐 |
| **Dock 栏图标标签字体** | 系统默认字体部分汉字缺字、重影或显示为方框 | 自动配置为清晰的微软雅黑（Microsoft YaHei UI） |
| **官方中文语言文件** | 旧版翻译遗漏、时间戳导致的部分词条无法加载 | 部署完整覆盖的规范化 GB18030 语言文件 |





## 乱码技术原理分析

Winstep Nexus 核心基于 Visual Basic 6.0 开发。经过逆向分析，托盘气泡乱码的根本原因是 VB6 运行时在处理外部 API 字符串封送时的机制缺陷：

1. **API 参数封送陷阱**  
   程序在声明 Win32 API `ReadProcessMemory` 时，接收缓冲区参数被定义为 `ByVal lpBuffer As String`。在 VB6 运行时规范中，将 `String` 按值传递给外部 DLL 时，会自动插入两步转换：
   - 调用 API 前：执行 `__vbaStrToAnsi`（分配临时 ANSI 缓冲区传给 API）；
   - API 返回后：自动调用 `__vbaStrToUnicode`（即 `MultiByteToWideChar(CP_ACP, ...)`）。

2. **DBCS（双字节字符集）的高位吞字节**  
   64 位 Windows Explorer 的托盘工具栏（`ToolbarWindow32`）传出的悬浮文本为 UTF-16 LE 双字节文本。
   - 在英文 Windows（代码页 1252）下，每个单字节与宽字符为 1:1 映射，后续配合 `StrConv(..., vbFromUnicode)` 可以巧合还原；
   - 在中文 Windows（代码页 936 / GBK）下，系统代码页属于 DBCS 双字节字符集。当 UTF-16 字节流中出现落在 `0x81 - 0xFE` 范围的字节（如“通”的高字节 `0x90`、“阅”的高字节 `0x96`、“音”的高字节 `0x97`）时，GBK 解析器会将其视作**双字节前导字节（Lead Byte）**并强制吞并后面的字节。
   - 由于紧邻的字节往往无法与其构成有效汉字，系统将其替换为单字节 `0x3F`（问号 `?`），造成后续所有字节奇偶对齐错位，最终引发文本乱码。

3. **修复方案**  
   本工具通过分析 PE 结构与特征码扫描定位可执行文件中的 6 处托盘读取例程，将原有的 ANSI/Unicode 往返转换旁路切断，直接将预分配的 BSTR 缓冲区指针（`StrPtr`）传递给 `ReadProcessMemory` 进行 UTF-16 原生直读，从而保持 Unicode 字节流完整无损。





## 使用方法

### 方式 1：直接运行独立执行程序（推荐）

1. 在 GitHub Releases 页面下载 `WinstepFixer.exe`。
2. 双击运行 `WinstepFixer.exe`。
3. 程序会自动检测当前运行中或默认路径下的 `Nexus.exe`。如未找到，可点击“浏览”手动指定路径。
4. 点击界面上的 **【一键全量深度修复】** 按钮。
5. 工具会自动完成进程关闭、备份原文件、写入二进制补丁、配置注册表及重启生效。

> **备份机制**：修补时会自动在 `Nexus.exe` 同目录下生成原始文件的备份（`Nexus.exe.bak`）。若需还原，可点击界面中的“还原官方原版备份”。

### 方式 2：从源码运行

要求安装 Python 3.10 或更高版本（仅使用标准库，无需安装额外依赖包）：

```bash
git clone https://github.com/PepinoLatte/Winstep_Nexus-Fixer.git
cd winstep-nexus-fixer

# 启动图形界面
python main.py

# 或使用命令行一键全量修复
python main.py --fix-all
```



## 命令行参数 (CLI)

适用于装机脚本、批量部署或包管理器静默调用：

```text
用法: main.py [-h] [--fix-all] [--patch-only] [--check] [--restore] [--path PATH] [--gui]

参数:
  -h, --help    显示帮助信息
  --fix-all     执行全量修复（包含二进制补丁、注册表、字体及语言包）
  --patch-only  仅对 Nexus.exe 写入二进制补丁
  --check       检查当前 Nexus 进程、补丁状态及设置项
  --restore     从 .bak 文件还原原版 Nexus.exe
  --path PATH   手动指定 Nexus.exe 所在路径
  --gui         强制以图形界面启动
```





## 自行编译单文件 EXE

如需自行打包发布独立可执行程序，可使用随附的 `build.bat`：

```cmd
pip install pyinstaller
build.bat
```

构建完成后可在 `dist/WinstepFixer.exe` 获得独立执行文件。





## 项目结构

```text
winstep-nexus-fixer/
├── core/
│   ├── patcher.py           # PE 分析与 AOB 特征码扫描、补丁生成
│   ├── process_manager.py   # Nexus 进程检测、安全退出与交互桌面重启
│   ├── registry_manager.py  # 首选项 UIDarkMode 与 Dock 字体注册表管理
│   └── lang_manager.py      # 中文语言包安装与同步
├── gui/
│   └── app.py               # Tkinter 图形化界面实现
├── Languages/               # 规范化中文语言包（NeXuS / Update Manager / Xtreme）
├── assets/screenshots/      # 修复前缺陷截图
├── main.py                  # 双模式入口
├── build.bat                # 打包脚本
├── LICENSE                  # MIT 许可证
└── README.md
```





## 许可证

本项目基于 [MIT License](LICENSE) 许可协议开源发布。仅用于个人学习、无障碍阅读及系统本地化兼容性修复，相关软件版权归原开发商所有。
