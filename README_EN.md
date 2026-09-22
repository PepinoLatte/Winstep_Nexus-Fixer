# Winstep Nexus Universal Chinese Localization & Mojibake Fixer

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%20Windows%2011-blue?style=flat-square&logo=windows" alt="Platform" />
  <img src="https://img.shields.io/badge/Target-Winstep%20Nexus%20%2F%20Xtreme-orange?style=flat-square" alt="Target" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="License" />
  <img src="https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square&logo=python" alt="Python" />
</p>

An all-in-one universal GUI/CLI patcher that permanently fixes **systray tooltip mojibake (garbled text on Clash, Volume, Battery, Snipaste, etc.)**, **Preferences tab truncation (UIDarkMode glitch)**, and **missing Chinese font glyphs** in **Winstep Nexus / Winstep Xtreme** on Windows.

---

## 🔬 Root Cause Analysis

Even when system regional settings are configured correctly, tooltips in Winstep Nexus displayed severe mojibake on Chinese Windows systems:

1. **VB6 String Marshaling Pitfall:**
   Winstep Nexus is built with Visual Basic 6.0. The developer declared the Win32 API `ReadProcessMemory` using `ByVal lpBuffer As String`. In VB6 runtime, passing a `String` by value forces automatic ANSI conversion:
   - Before API call: `__vbaStrToAnsi` (allocates an ANSI buffer).
   - After API call: `__vbaStrToUnicode` (converts ANSI back to Unicode via `MultiByteToWideChar(CP_ACP, ...)`).

2. **DBCS Byte Swallow & Misalignment:**
   Explorer's 64-bit tray toolbar provides raw **UTF-16 Unicode bytes**.
   - On English Windows (Code Page 1252), every byte maps 1:1, so a subsequent `StrConv(..., vbFromUnicode)` restores the original bytes by coincidence.
   - On Chinese Windows (Code Page 936 / GBK), the code page is a Double Byte Character Set (DBCS).
   - When UTF-16 bytes contain values in the range `0x81 - 0xFE` (such as `0x90` in "通", `0x96` in "阅", `0x97` in "音"), the GBK decoder misinterprets them as a DBCS Lead Byte, consuming the next byte. Because the resulting pair is invalid (e.g., paired with `0x00`), the character is dropped and replaced with `0x3F` ('?'), permanently destroying the byte alignment and text.

3. **Our Solution:**
   This tool uses an AOB signature scanner to locate all 6 systray tooltip reading routines across different Winstep builds, bypassing `__vbaStrToAnsi` / `__vbaStrToUnicode` and injecting direct **UTF-16 Unicode pass-through pointers** straight into `ReadProcessMemory`.

---

## 🚀 Quick Start

### Option 1: Standalone Binary (Recommended)
Download the standalone `WinstepFixer.exe` from [Releases](../../releases) and click **"一键全量深度修复 (One-Click Deep Fix)"**.

### Option 2: Run from Source
```bash
git clone https://github.com/your-username/winstep-nexus-fixer.git
cd winstep-nexus-fixer
python main.py
```

### Option 3: Command Line
```bash
# Check status
python main.py --check

# Apply all fixes silently
python main.py --fix-all

# Restore pristine original binary
python main.py --restore
```

---

## 📄 License
Released under the [MIT License](LICENSE).
