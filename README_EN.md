# Winstep Chinese Localization Fixer

A universal patching utility to fix systray tooltip mojibake, missing preferences tabs, UI button clipping, multi-language dropdown character corruption, and Chinese font fallback glitches in Winstep Nexus / Winstep Xtreme on Windows.

Supports both GUI and CLI modes, using pattern matching (AOB Scan) to locate target routines across different versions of Winstep executables.

---

## Issues Addressed

| Component | Default Behavior (on Chinese Windows) | Patched Behavior |
| :--- | :--- | :--- |
| **Systray Tooltips (Clash / Proxies)** | Shifted/corrupted characters (e.g. `订瑭 詡仱BY`) | Clean UTF-16 text (e.g. `订阅: GO国外`) |
| **Systray Tooltips (Volume)** | Corrupted trailing character (e.g. `扬声器: 静脑`) | Clean text (e.g. `扬声器: 静音`) |
| **Systray Tooltips (Battery / Power)**| Corrupted status text (e.g. `97% 可用(已接瓶遵1L`) | Clean text (e.g. `96% 可用(已接通电源)`) |
| **Multi-Language Dropdown List** | Non-ASCII native endonyms corrupted into garbage (e.g. `龙脖囵梠?`, `薈磧ina`, `Fran鏃is`, `擔柿皈`) | Sanitized headers preventing ANSI collisions; clearly labels `Chinese Simplified (简体中文)` and Traditional Chinese |
| **Preferences Dialog** | Broken Dark Mode collapses 8 tabs into 4; clipped buttons | Restores all 8 preference tabs and button text |
| **Dock Label Fonts** | System fallback font shows boxes or missing glyphs | Configures smooth Microsoft YaHei UI font |
| **Official Language Files** | Missing strings or encoding conflicts | Deploys standardized GB18030 language packs |

---

## Operating Systems & Architecture Support (x86 / x64)

### 1. Architecture Compatibility
- **Target Application (Nexus.exe)**: Winstep Nexus was developed in Visual Basic 6.0 and is inherently a **32-bit (x86)** PE binary. Even on 64-bit Windows, it executes via the WOW64 subsystem. The binary patch operates directly on x86 machine instructions, making it **100% compatible across both 32-bit and 64-bit Windows**.
- **Fixer Client (GUI / CLI)**: Pre-built binaries are provided for various Windows architectures and release tiers.

### 2. Available Release Packages

### Release Matrix & Priority Guide

| Priority | Package Name | Target OS | Target Architecture | Description |
| :---: | :--- | :--- | :--- | :--- |
| **🥇 Primary** | **`WinstepFixer-v1.0.0-x64-Win10-Win11.zip`** | Windows 10 / Windows 11 | 64-bit (x64) | **Recommended**. Mainstream choice for modern 64-bit Windows with Per-Monitor V2 High-DPI support |
| **🥈 32-bit** | **`WinstepFixer-v1.0.0-x86-Win10-Win11.zip`** | Windows 10 / Windows 11 | 32-bit (x86) | Runs natively on 32-bit Windows 10/11 and via WOW64 on 64-bit systems |
| **🥉 Legacy** | **`WinstepFixer-v1.0.0-x86-Win7-Win8-Legacy.zip`** | Windows 7 SP1 / 8 / 8.1 / 10 / 11 | 32-bit (x86) | Ultimate legacy compatibility built with Python 3.8 x86 for older machines |

---

## Technical Background

Winstep Nexus is built with Visual Basic 6.0. Reverse engineering revealed that the systray tooltip mojibake stems from VB6 runtime string marshaling:

1. **API String Marshaling Pitfall**  
   The program declares the Win32 API `ReadProcessMemory` with `ByVal lpBuffer As String`. In VB6, passing a `String` by value to an API automatically inserts:
   - Before API call: `__vbaStrToAnsi` (allocating a temporary ANSI buffer).
   - After API call: `__vbaStrToUnicode` (calling `MultiByteToWideChar(CP_ACP, ...)`).

2. **DBCS Lead Byte Swallow & Byte Stream Misalignment**  
   Explorer's 64-bit tray toolbar provides raw UTF-16 LE text.
   - On English Windows (Code Page 1252), byte mapping is 1:1, allowing a subsequent `StrConv(..., vbFromUnicode)` to restore bytes by coincidence.
   - On Chinese Windows (Code Page 936 / GBK), the code page is DBCS. When UTF-16 bytes fall into the `0x81 - 0xFE` range (such as high byte `0x90` in `通`, `0x96` in `阅`, `0x97` in `音`), the decoder misinterprets them as DBCS Lead Bytes and swallows the following byte.
   - Unmappable pairs are replaced with single byte `0x3F` ('?'), permanently misaligning the byte stream and producing mojibake.

3. **Patch Implementation**  
   This tool locates all 6 tray reading routines in the binary, bypasses the ANSI/Unicode roundtrip conversion, and passes the preallocated BSTR buffer pointer directly to `ReadProcessMemory` for native UTF-16 pass-through.

---

## Usage

### Option 1: Standalone Binary (Recommended)

1. Download the appropriate ZIP package for your OS from the GitHub Releases page.
2. Extract and run `WinstepFixer.exe`.
3. The utility automatically detects the path to `Nexus.exe`. You can also click "Browse..." to select it manually.
4. Click **"一键全量深度修复 (One-Click Deep Fix)"**.
5. The tool will stop Nexus, back up the original binary to `Nexus.exe.bak`, apply binary patches, update registry entries, deploy language packs, and restart Nexus.

### Option 2: Run from Source

Requires Python 3.8+ (standard library only, no third-party packages required):

```bash
git clone https://github.com/PepinoLatte/Winstep_Nexus-Fixer.git
cd winstep-nexus-fixer

# Launch GUI
python main.py

# Or run full fix via CLI
python main.py --fix-all
```

---

## CLI Options

```text
Usage: main.py [-h] [--fix-all] [--patch-only] [--check] [--restore] [--path PATH] [--gui]

Options:
  -h, --help    Show help message
  --fix-all     Run full fix (binary patch, registry, font, language packs)
  --patch-only  Apply binary patch to Nexus.exe only
  --check       Check status of Nexus process, patch, and settings
  --restore     Restore original Nexus.exe from .bak backup
  --path PATH   Specify path to Nexus.exe manually
  --gui         Launch interactive GUI
```

---

## Project Structure

```text
winstep-nexus-fixer/
├── .github/
│   └── workflows/
│       └── build-releases.yml  # GitHub Actions automated multi-architecture CI/CD
├── core/
│   ├── patcher.py           # PE parsing, AOB scanning, and binary patching
│   ├── process_manager.py   # Nexus process lifecycle management
│   ├── registry_manager.py  # Preferences UIDarkMode and font registry manager
│   └── lang_manager.py      # Chinese pack deployment and language header sanitization
├── gui/
│   └── app.py               # Tkinter High-DPI adaptive user interface
├── Languages/               # Optimized Chinese language packs
├── assets/screenshots/      # Visual comparison screenshots
├── main.py                  # CLI/GUI unified entry point
├── build.bat                # Standalone PyInstaller build script
├── LICENSE                  # MIT License
└── README.md
```

---

## License

This project is licensed under the [MIT License](LICENSE).
