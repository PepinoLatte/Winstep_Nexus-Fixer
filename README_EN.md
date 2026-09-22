# Winstep Nexus Localization Fixer

[English](README_EN.md) | [简体中文](README.md)

An automated patching tool designed to resolve system tray tooltip character corruption (mojibake), multi-language list encoding conflicts, missing preferences tabs, UI button clipping, and font display defects in Winstep Nexus and Winstep Xtreme under non-English (especially East Asian) Windows environments.

Provides both Graphical User Interface (GUI) and Command-Line Interface (CLI) modes, utilizing Array of Bytes (AOB) pattern scanning to locate target routines across different versions of Winstep executables.

---

## Issues Addressed

| Component | Default Behavior (Chinese Windows) | Patched Behavior |
| :--- | :--- | :--- |
| **Systray Tooltips** | Shifted, missing, or corrupted text (e.g. proxies, volume, battery status) | Full, native UTF-16 LE text display |
| **Language Selection** | Non-ASCII native language endonyms corrupted due to code page collisions | Sanitized language headers; clearly marked Chinese options |
| **Preferences Panel** | Dark Mode bug collapses 8 tabs into 4; bottom buttons clipped | All 8 preference tabs restored; layout properly aligned |
| **Dock Item Fonts** | Default system font exhibits missing glyphs or blurred rendering | Automatically configured to Microsoft YaHei UI |
| **Official Language Files** | Incomplete strings or timestamp parsing issues | Standardized GB18030 language packs deployed |

---

## Downloads & Version Selection

The target binary (`Nexus.exe`) is inherently a 32-bit (x86) PE executable, running natively on 32-bit Windows and via WOW64 on 64-bit Windows. The patch operates on x86 machine instructions and is compatible with both 32-bit and 64-bit platforms.

Choose the standalone package matching your environment:

| Priority | Filename | Target OS | Architecture | Description |
| :---: | :--- | :--- | :--- | :--- |
| Mainstream | `WinstepFixer-v1.0.0-x64-Win10-Win11.zip` | Windows 10 / 11 | 64-bit (x64) | Primary choice for modern 64-bit systems; supports Per-Monitor V2 High-DPI scaling |
| Secondary | `WinstepFixer-v1.0.0-x86-Win10-Win11.zip` | Windows 10 / 11 | 32-bit (x86) | For 32-bit Windows 10/11 or running in 32-bit mode on 64-bit systems |
| Legacy | `WinstepFixer-v1.0.0-x86-Win7-Win8-Legacy.zip` | Windows 7 / 8 / 8.1 / 10 / 11 | 32-bit (x86) | Built with Python 3.8 x86 for legacy environments including Windows 7 SP1 |

Pre-built binaries can be downloaded from the [Releases Page](https://github.com/PepinoLatte/Winstep_Nexus-Fixer/releases).

---

## Usage

### Option 1: Standalone Executable (Recommended)

1. Download and extract the appropriate ZIP package from Releases.
2. Run `WinstepFixer.exe`.
3. The tool automatically detects the path to `Nexus.exe`. If not found, click "Browse" to locate it manually.
4. Click **"一键全量深度修复 (One-Click Deep Fix)"**.
5. The tool stops the running process, backs up the original executable to `Nexus.exe.bak`, applies the binary patch, updates registry settings, deploys language files, and restarts Nexus.

To restore the original binary, click "还原官方原版备份 (Restore Original Backup)" or use the `--restore` command-line option.

### Option 2: Run from Source

Requirements: Python 3.8+ (Standard library only; no external dependencies required).

```bash
git clone https://github.com/PepinoLatte/Winstep_Nexus-Fixer.git
cd winstep-nexus-fixer

# Launch GUI
python main.py

# CLI full fix
python main.py --fix-all
```

---

## CLI Options

Suitable for automation scripts and unattended deployments:

```text
Usage: main.py [-h] [--fix-all] [--patch-only] [--check] [--restore] [--path PATH] [--gui]

Options:
  -h, --help    Show help message
  --fix-all     Execute full fix (binary patch, registry, font, and language files)
  --patch-only  Apply binary patch to Nexus.exe only
  --check       Inspect Nexus process state, patch status, and configuration
  --restore     Restore original Nexus.exe from backup file
  --path PATH   Manually specify path to Nexus.exe
  --gui         Launch graphical interface
```

---

## Technical Background

Winstep Nexus is built with Visual Basic 6.0. Reverse engineering indicates that tray tooltip character corruption is caused by VB6 runtime string marshaling during Win32 API calls:

1. **API String Marshaling Pitfall**  
   The program declares `ReadProcessMemory` with `ByVal lpBuffer As String`. In VB6, passing a `String` by value to an external DLL implicitly executes `__vbaStrToAnsi` prior to the call (allocating a temporary ANSI buffer) and `__vbaStrToUnicode` (`MultiByteToWideChar(CP_ACP, ...)`) upon return.
2. **DBCS Lead Byte Swallowing**  
   The Windows Explorer tray toolbar (`ToolbarWindow32`) provides UTF-16 LE text. Under DBCS code pages (such as CP936 / GBK), when a UTF-16 byte falls within `0x81 - 0xFE`, the decoder misinterprets it as a DBCS Lead Byte and consumes the subsequent byte. Unmappable sequences are replaced with `0x3F` (`?`), disrupting byte alignment and resulting in unrecoverable corruption.
3. **Patch Implementation**  
   This utility uses pattern scanning (AOB Scan) to identify all tray reading routines in the binary, bypasses the ANSI/Unicode round-trip conversions, and passes the allocated BSTR pointer directly to `ReadProcessMemory` for native UTF-16 reading.

---

## Project Structure

```text
winstep-nexus-fixer/
├── .github/workflows/
│   └── build-releases.yml  # GitHub Actions multi-architecture build workflow
├── core/
│   ├── patcher.py           # PE analysis, AOB scanning, and binary patching
│   ├── process_manager.py   # Process detection and lifecycle management
│   ├── registry_manager.py  # Dark mode and font registry settings
│   └── lang_manager.py      # Language pack deployment and encoding fixes
├── gui/
│   └── app.py               # Tkinter High-DPI adaptive user interface
├── Languages/               # Standardized Chinese language packs
├── assets/screenshots/      # Defect and comparison screenshots
├── main.py                  # CLI / GUI entry point
├── build.bat                # Local packaging script
├── LICENSE                  # MIT License
├── README.md                # Chinese documentation
└── README_EN.md             # English documentation
```

---

## License

This project is licensed under the [MIT License](LICENSE). For educational, accessibility, and localization compatibility purposes only. All copyrights belong to their respective owners.
