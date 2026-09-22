# Winstep Chinese Localization Fixer

A universal patching utility to fix systray tooltip mojibake, missing preferences tabs, UI button clipping, and Chinese font fallback glitches in Winstep Nexus / Winstep Xtreme on Windows.

Supports both GUI and CLI modes, using pattern matching (AOB Scan) to locate target routines across different versions of Winstep executables.

---

## Issues Addressed

| Component | Default Behavior (on Chinese Windows) | Patched Behavior |
| :--- | :--- | :--- |
| **Systray Tooltips (Clash / Proxies)** | Shifted/corrupted characters (e.g. `订瑭 詡仱BY`) | Clean UTF-16 text (e.g. `订阅: GO国外`) |
| **Systray Tooltips (Volume)** | Corrupted trailing character (e.g. `扬声器: 静脑`) | Clean text (e.g. `扬声器: 静音`) |
| **Systray Tooltips (Battery / Power)**| Corrupted status text (e.g. `97% 可用(已接瓶遵1L`) | Clean text (e.g. `96% 可用(已接通电源)`) |
| **Preferences Dialog** | Broken Dark Mode collapses 8 tabs into 4; clipped buttons | Restores all 8 preference tabs and button text |
| **Dock Label Fonts** | System fallback font shows boxes or missing glyphs | Configures smooth Microsoft YaHei UI font |
| **Official Language Files** | Missing strings or encoding conflicts | Deploys standardized GB18030 language packs |

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

1. Download `WinstepFixer.exe` from the Releases page.
2. Run `WinstepFixer.exe`.
3. The utility automatically detects the path to `Nexus.exe`. You can also click "Browse..." to select it manually.
4. Click **"一键全量深度修复 (One-Click Deep Fix)"**.
5. The tool will stop Nexus, back up the original binary to `Nexus.exe.bak`, apply binary patches, update registry entries, and restart Nexus.

### Option 2: Run from Source

Requires Python 3.10+ (standard library only, no third-party packages required):

```bash
git clone https://github.com/PepinoLatte/Winstep_Nexus-Fixer.git
cd winstep-nexus-fixer

# Launch GUI
python main.py

# Or apply all fixes via CLI
python main.py --fix-all
```

---

## Command Line Interface (CLI)

```text
usage: main.py [-h] [--fix-all] [--patch-only] [--check] [--restore] [--path PATH] [--gui]

options:
  -h, --help    show this help message and exit
  --fix-all     apply all fixes (binary patch, tabs, font, language packs)
  --patch-only  apply only the binary systray tooltip patch
  --check       check current Nexus process and patch status
  --restore     restore original Nexus.exe from .bak backup
  --path PATH   specify custom path to Nexus.exe
  --gui         force launch GUI mode
```

---

## Building Standalone Executable

```cmd
pip install pyinstaller
build.bat
```

The output executable will be placed in `dist/WinstepFixer.exe`.

---

## Project Structure

```text
winstep-nexus-fixer/
├── core/
│   ├── patcher.py           # PE analyzer and binary patcher
│   ├── process_manager.py   # Process lifecycle management
│   ├── registry_manager.py  # Preferences and font registry settings
│   └── lang_manager.py      # Language pack installation
├── gui/
│   └── app.py               # Tkinter GUI implementation
├── Languages/               # Optimized Chinese language files
├── assets/screenshots/      # Reference screenshots
├── main.py                  # Entry point
├── build.bat                # PyInstaller build script
├── LICENSE                  # MIT License
└── README.md
```

---

## License

Released under the [MIT License](LICENSE).
