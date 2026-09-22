"""
Winstep Process Manager
Detects, terminates, and launches Nexus processes cleanly on the user interactive desktop.
"""

import ctypes
from ctypes import wintypes
import os
import time
import winreg


class WinstepProcessManager:
    @staticmethod
    def get_nexus_pids() -> list[int]:
        """Get all running nexus.exe PIDs."""
        kernel32 = ctypes.windll.kernel32

        class PROCESSENTRY32W(ctypes.Structure):
            _fields_ = [
                ('dwSize', wintypes.DWORD),
                ('cntUsage', wintypes.DWORD),
                ('th32ProcessID', wintypes.DWORD),
                ('th32DefaultHeapID', ctypes.c_void_p),
                ('th32ModuleID', wintypes.DWORD),
                ('cntThreads', wintypes.DWORD),
                ('th32ParentProcessID', wintypes.DWORD),
                ('pcPriClassBase', wintypes.LONG),
                ('dwFlags', wintypes.DWORD),
                ('szExeFile', ctypes.c_wchar * 260)
            ]

        hSnapshot = kernel32.CreateToolhelp32Snapshot(0x00000002, 0)
        pe = PROCESSENTRY32W()
        pe.dwSize = ctypes.sizeof(PROCESSENTRY32W)

        pids = []
        if kernel32.Process32FirstW(hSnapshot, ctypes.byref(pe)):
            while True:
                if pe.szExeFile.lower() in ('nexus.exe', 'winstep.exe', 'wshelf.exe'):
                    pids.append(pe.th32ProcessID)
                if not kernel32.Process32NextW(hSnapshot, ctypes.byref(pe)):
                    break
        kernel32.CloseHandle(hSnapshot)
        return pids

    @staticmethod
    def stop_nexus(timeout: float = 3.0) -> bool:
        """Stop running Nexus processes."""
        pids = WinstepProcessManager.get_nexus_pids()
        if not pids:
            return True

        kernel32 = ctypes.windll.kernel32
        for pid in pids:
            hProc = kernel32.OpenProcess(0x0001, False, pid)  # PROCESS_TERMINATE
            if hProc:
                kernel32.TerminateProcess(hProc, 0)
                kernel32.CloseHandle(hProc)

        start = time.time()
        while time.time() - start < timeout:
            if not WinstepProcessManager.get_nexus_pids():
                return True
            time.sleep(0.2)

        return len(WinstepProcessManager.get_nexus_pids()) == 0

    @staticmethod
    def start_nexus(exe_path: str) -> tuple[bool, str]:
        """Launch Nexus on user interactive desktop (WinSta0\\Default)."""
        if not os.path.exists(exe_path):
            return False, f'File not found: {exe_path}'

        class STARTUPINFOW(ctypes.Structure):
            _fields_ = [
                ('cb', wintypes.DWORD),
                ('lpReserved', wintypes.LPWSTR),
                ('lpDesktop', wintypes.LPWSTR),
                ('lpTitle', wintypes.LPWSTR),
                ('dwX', wintypes.DWORD),
                ('dwY', wintypes.DWORD),
                ('dwXSize', wintypes.DWORD),
                ('dwYSize', wintypes.DWORD),
                ('dwXCountChars', wintypes.DWORD),
                ('dwYCountChars', wintypes.DWORD),
                ('dwFillAttribute', wintypes.DWORD),
                ('dwFlags', wintypes.DWORD),
                ('wShowWindow', wintypes.WORD),
                ('cbReserved2', wintypes.WORD),
                ('lpReserved2', ctypes.c_void_p),
                ('hStdInput', wintypes.HANDLE),
                ('hStdOutput', wintypes.HANDLE),
                ('hStdError', wintypes.HANDLE),
            ]

        class PROCESS_INFORMATION(ctypes.Structure):
            _fields_ = [
                ('hProcess', wintypes.HANDLE),
                ('hThread', wintypes.HANDLE),
                ('dwProcessId', wintypes.DWORD),
                ('dwThreadId', wintypes.DWORD),
            ]

        si = STARTUPINFOW()
        si.cb = ctypes.sizeof(STARTUPINFOW)
        si.lpDesktop = r'WinSta0\Default'

        pi = PROCESS_INFORMATION()
        kernel32 = ctypes.windll.kernel32
        exe_dir = os.path.dirname(os.path.abspath(exe_path))

        res = kernel32.CreateProcessW(
            None, exe_path, None, None, False,
            0, None, exe_dir,
            ctypes.byref(si), ctypes.byref(pi)
        )

        if res:
            kernel32.CloseHandle(pi.hProcess)
            kernel32.CloseHandle(pi.hThread)
            return True, f'Nexus started successfully (PID {pi.dwProcessId}).'
        else:
            err = kernel32.GetLastError()
            return False, f'CreateProcess failed with error code: {err}'

    @staticmethod
    def auto_detect_exe() -> str:
        """Find nexus.exe path automatically."""
        # 1. From running process
        pids = WinstepProcessManager.get_nexus_pids()
        if pids:
            kernel32 = ctypes.windll.kernel32
            hProcess = kernel32.OpenProcess(0x0400 | 0x0010, False, pids[0])
            if hProcess:
                buf = (ctypes.c_wchar * 1024)()
                cb = wintypes.DWORD(1024)
                if ctypes.windll.kernel32.QueryFullProcessImageNameW(hProcess, 0, buf, ctypes.byref(cb)):
                    kernel32.CloseHandle(hProcess)
                    path = buf.value
                    if os.path.exists(path) and 'nexus' in os.path.basename(path).lower():
                        return path
                kernel32.CloseHandle(hProcess)

        # 2. Check standard installation directories
        candidates = [
            r'C:\Program Files (x86)\Winstep\nexus.exe',
            r'C:\Program Files\Winstep\nexus.exe',
            os.path.expandvars(r'%ProgramFiles(x86)%\Winstep\nexus.exe'),
            os.path.expandvars(r'%ProgramFiles%\Winstep\nexus.exe'),
        ]
        for c in candidates:
            if os.path.exists(c):
                return c

        # 3. Check App Paths in registry
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\Nexus.exe') as k:
                val, _ = winreg.QueryValueEx(k, '')
                if os.path.exists(val):
                    return val
        except Exception:
            pass

        return ''
