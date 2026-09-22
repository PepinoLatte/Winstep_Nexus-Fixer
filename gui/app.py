"""
Winstep Nexus Chinese Localization Fixer - Modern Adaptive Tkinter GUI
High-DPI aware, multi-resolution adaptive scaling for 1080p / 2K / 4K and various Windows DPI scale factors.
"""

import ctypes
from ctypes import wintypes
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from core.lang_manager import WinstepLangManager
from core.patcher import WinstepPatcher
from core.process_manager import WinstepProcessManager
from core.registry_manager import WinstepRegistryManager


def init_high_dpi():
    """Initialize Windows High-DPI awareness context."""
    if sys.platform != 'win32':
        return
    try:
        # Windows 10 Creators Update (1703)+ : Per-Monitor V2
        ctypes.windll.user32.SetProcessDpiAwarenessContext(-4)
    except Exception:
        try:
            # Windows 8.1+ : Per-Monitor V1
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                # Windows Vista+ : System DPI Aware
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass


class DPIScaler:
    """Manages DPI detection and resolution-proportional dimension scaling."""
    def __init__(self, root: tk.Tk):
        self.dpi = 96
        self.scale_factor = 1.0

        if sys.platform == 'win32':
            try:
                hdc = ctypes.windll.user32.GetDC(0)
                dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
                ctypes.windll.user32.ReleaseDC(0, hdc)
                if dpi and dpi > 0:
                    self.dpi = dpi
                    self.scale_factor = max(1.0, dpi / 96.0)
            except Exception:
                pass

        # Configure Tkinter internal font point-to-pixel scaling (72 points = 1 inch)
        try:
            root.tk.call('tk', 'scaling', self.dpi / 72.0)
        except Exception:
            pass

    def s(self, px: int) -> int:
        """Scale a raw pixel value based on the DPI scale factor."""
        return max(1, int(round(px * self.scale_factor)))


class ModernFixerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.scaler = DPIScaler(root)

        self.root.title("Winstep Nexus 中文与乱码一键修复工具 v1.0")

        self.reg_mgr = WinstepRegistryManager()
        self.exe_path_var = tk.StringVar(value=WinstepProcessManager.auto_detect_exe())

        self.setup_geometry()
        self.setup_styles()
        self.build_ui()
        self.refresh_status()

    def setup_geometry(self):
        """Calculate responsive window size and center on screen."""
        self.root.update_idletasks()
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        # Target base size designed for standard scaling (800x630)
        base_w = 820
        base_h = 630

        win_w = min(self.scaler.s(base_w), int(screen_w * 0.94))
        win_h = min(self.scaler.s(base_h), int(screen_h * 0.90))

        pos_x = max(0, (screen_w - win_w) // 2)
        pos_y = max(0, (screen_h - win_h) // 2)

        self.root.geometry(f"{win_w}x{win_h}+{pos_x}+{pos_y}")

        # Minimum resize constraints
        min_w = min(self.scaler.s(700), int(screen_w * 0.85))
        min_h = min(self.scaler.s(520), int(screen_h * 0.75))
        self.root.minsize(min_w, min_h)

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use('clam')

        self.bg_color = "#f5f6fa"
        self.card_bg = "#ffffff"
        self.text_color = "#2f3640"
        self.accent_color = "#27ae60"
        self.accent_hover = "#2ecc71"
        self.info_color = "#2980b9"
        self.danger_color = "#c0392b"

        self.root.configure(bg=self.bg_color)

        # Scale fonts
        font_family = 'Microsoft YaHei UI'
        f_title = (font_family, 14, 'bold')
        f_subtitle = (font_family, 9)
        f_card_title = (font_family, 10, 'bold')
        f_normal = (font_family, 9)
        f_btn_large = (font_family, 11, 'bold')
        f_btn_small = (font_family, 9)

        pad_card = self.scaler.s(10)
        pad_btn_pri = self.scaler.s(8)
        pad_btn_sec = self.scaler.s(5)

        self.style.configure('TFrame', background=self.bg_color)
        self.style.configure('Card.TFrame', background=self.card_bg, relief='flat')
        self.style.configure('TLabel', background=self.bg_color, foreground=self.text_color, font=f_normal)
        self.style.configure('Card.TLabel', background=self.card_bg, foreground=self.text_color, font=f_normal)
        self.style.configure('Header.TLabel', background=self.bg_color, foreground="#1e272e", font=f_title)
        self.style.configure('SubHeader.TLabel', background=self.bg_color, foreground="#718093", font=f_subtitle)
        self.style.configure('CardTitle.TLabel', background=self.card_bg, foreground="#2f3640", font=f_card_title)

        self.style.configure(
            'Primary.TButton',
            font=f_btn_large,
            foreground='#ffffff',
            background=self.accent_color,
            borderwidth=0,
            padding=pad_btn_pri
        )
        self.style.map('Primary.TButton', background=[('active', self.accent_hover), ('disabled', '#dcdde1')])

        self.style.configure(
            'Secondary.TButton',
            font=f_btn_small,
            foreground='#ffffff',
            background=self.info_color,
            borderwidth=0,
            padding=pad_btn_sec
        )
        self.style.map('Secondary.TButton', background=[('active', '#3498db')])

        self.style.configure(
            'Danger.TButton',
            font=f_btn_small,
            foreground='#ffffff',
            background=self.danger_color,
            borderwidth=0,
            padding=pad_btn_sec
        )
        self.style.map('Danger.TButton', background=[('active', '#e74c3c')])

    def build_ui(self):
        s = self.scaler.s
        pad_outer = f"{s(14)} {s(10)} {s(14)} {s(10)}"
        main_frame = ttk.Frame(self.root, padding=pad_outer)
        main_frame.pack(fill='both', expand=True)

        # 1. Header Area
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill='x', pady=(0, s(8)))
        ttk.Label(header_frame, text="Winstep Nexus 中文与乱码修复工具", style='Header.TLabel').pack(anchor='w')
        ttk.Label(header_frame, text="一键修复托盘气泡乱码 (Clash/音量/电源/Snipaste)、首选项标签页缺失、UI截断及字体显示问题", style='SubHeader.TLabel').pack(anchor='w', pady=(s(2), 0))

        # 2. Path Selection Card
        path_card = ttk.Frame(main_frame, style='Card.TFrame', padding=s(8))
        path_card.pack(fill='x', pady=(0, s(8)))

        ttk.Label(path_card, text="程序路径 (Nexus.exe):", style='CardTitle.TLabel').pack(anchor='w')
        path_box = ttk.Frame(path_card, style='Card.TFrame')
        path_box.pack(fill='x', pady=(s(4), 0))

        self.entry_path = ttk.Entry(path_box, textvariable=self.exe_path_var, font=('Microsoft YaHei UI', 9))
        self.entry_path.pack(side='left', fill='x', expand=True, padx=(0, s(6)))

        btn_browse = ttk.Button(path_box, text="浏览...", command=self.on_browse)
        btn_browse.pack(side='left', padx=(0, s(4)))

        btn_detect = ttk.Button(path_box, text="自动检测", command=self.on_auto_detect)
        btn_detect.pack(side='left')

        # 3. Status Grid Card
        status_card = ttk.Frame(main_frame, style='Card.TFrame', padding=s(8))
        status_card.pack(fill='x', pady=(0, s(8)))

        ttk.Label(status_card, text="系统与组件检测状态", style='CardTitle.TLabel').pack(anchor='w', pady=(0, s(4)))

        grid_frame = ttk.Frame(status_card, style='Card.TFrame')
        grid_frame.pack(fill='x')
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)

        self.lbl_proc_status = ttk.Label(grid_frame, text="进程: 检测中...", style='Card.TLabel')
        self.lbl_proc_status.grid(row=0, column=0, sticky='w', pady=s(2))

        self.lbl_patch_status = ttk.Label(grid_frame, text="托盘补丁: 检测中...", style='Card.TLabel')
        self.lbl_patch_status.grid(row=0, column=1, sticky='w', pady=s(2))

        self.lbl_tabs_status = ttk.Label(grid_frame, text="首选项标签页: 检测中...", style='Card.TLabel')
        self.lbl_tabs_status.grid(row=1, column=0, sticky='w', pady=s(2))

        self.lbl_font_status = ttk.Label(grid_frame, text="Dock字体: 检测中...", style='Card.TLabel')
        self.lbl_font_status.grid(row=1, column=1, sticky='w', pady=s(2))

        # 4. Action Buttons Card
        act_card = ttk.Frame(main_frame, style='Card.TFrame', padding=s(8))
        act_card.pack(fill='x', pady=(0, s(8)))

        self.btn_full_fix = ttk.Button(
            act_card,
            text="一键全量深度修复 (推荐)",
            style='Primary.TButton',
            command=self.on_full_fix
        )
        self.btn_full_fix.pack(fill='x', pady=(0, s(6)))

        # 2-row adaptive sub-actions grid
        sub_grid = ttk.Frame(act_card, style='Card.TFrame')
        sub_grid.pack(fill='x')
        sub_grid.columnconfigure(0, weight=1)
        sub_grid.columnconfigure(1, weight=1)
        sub_grid.columnconfigure(2, weight=1)

        ttk.Button(sub_grid, text="仅修补托盘补丁", style='Secondary.TButton', command=self.on_patch_only).grid(row=0, column=0, sticky='ew', padx=(0, s(4)), pady=s(2))
        ttk.Button(sub_grid, text="修复首选项标签页", style='Secondary.TButton', command=self.on_fix_tabs_only).grid(row=0, column=1, sticky='ew', padx=s(2), pady=s(2))
        ttk.Button(sub_grid, text="安装优化语言包", style='Secondary.TButton', command=self.on_install_lang_only).grid(row=0, column=2, sticky='ew', padx=(s(4), 0), pady=s(2))

        ttk.Button(sub_grid, text="重启 Nexus", style='Secondary.TButton', command=self.on_restart_nexus).grid(row=1, column=0, columnspan=2, sticky='ew', padx=(0, s(4)), pady=(s(2), 0))
        ttk.Button(sub_grid, text="还原官方原版备份", style='Danger.TButton', command=self.on_restore_backup).grid(row=1, column=2, sticky='ew', padx=(s(4), 0), pady=(s(2), 0))

        # 5. Log Console
        log_frame = ttk.Frame(main_frame)
        log_frame.pack(fill='both', expand=True)

        ttk.Label(log_frame, text="执行日志:", font=('Microsoft YaHei UI', 9, 'bold')).pack(anchor='w', pady=(0, s(3)))

        self.log_text = tk.Text(
            log_frame,
            bg='#2f3640',
            fg='#f5f6fa',
            insertbackground='white',
            font=('Consolas', 9),
            wrap='word',
            relief='flat',
            padx=s(6),
            pady=s(6),
            height=6
        )
        self.log_text.pack(side='left', fill='both', expand=True)

        scrollbar = ttk.Scrollbar(log_frame, orient='vertical', command=self.log_text.yview)
        scrollbar.pack(side='right', fill='y')
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self.log_text.tag_config('INFO', foreground='#00d2d3')
        self.log_text.tag_config('SUCCESS', foreground='#1dd1a1')
        self.log_text.tag_config('WARN', foreground='#feca57')
        self.log_text.tag_config('ERROR', foreground='#ff6b6b')

        self.log(f"工具已就绪 (检测到屏幕 DPI: {self.scaler.dpi}, 缩放系数: {self.scaler.scale_factor:.2f}x)。", "INFO")

    def log(self, message: str, level: str = "INFO"):
        timestamp = time.strftime("[%H:%M:%S] ")
        self.log_text.insert('end', timestamp, 'INFO')
        self.log_text.insert('end', f"[{level}] {message}\n", level)
        self.log_text.see('end')

    def refresh_status(self):
        exe_path = self.exe_path_var.get()

        # 1. Process Status
        pids = WinstepProcessManager.get_nexus_pids()
        if pids:
            self.lbl_proc_status.configure(text=f"● 进程状态: 运行中 (PID: {pids[0]})", foreground="#27ae60")
        else:
            self.lbl_proc_status.configure(text="○ 进程状态: 未运行", foreground="#7f8c8d")

        # 2. Binary Patch
        if exe_path and os.path.exists(exe_path):
            patcher = WinstepPatcher(exe_path)
            res = patcher.analyze()
            status = res.get('status')
            if status == 'PATCHED':
                self.lbl_patch_status.configure(text="✓ 托盘补丁: 已修补 (原生 UTF-16)", foreground="#27ae60")
            elif status == 'UNPATCHED':
                self.lbl_patch_status.configure(text="✗ 托盘补丁: 未修补 (存在乱码)", foreground="#c0392b")
            elif status == 'PARTIALLY_PATCHED':
                self.lbl_patch_status.configure(text="⚠ 托盘补丁: 部分修补", foreground="#e67e22")
            else:
                self.lbl_patch_status.configure(text="? 托盘补丁: 未知文件", foreground="#7f8c8d")
        else:
            self.lbl_patch_status.configure(text="✗ 托盘补丁: 文件不存在", foreground="#c0392b")

        # 3. Preferences Tabs
        reg_status = self.reg_mgr.get_status()
        if reg_status['is_tabs_ok']:
            self.lbl_tabs_status.configure(text="✓ 首选项界面: 完整 8 标签页 (UIDarkMode=0)", foreground="#27ae60")
        else:
            self.lbl_tabs_status.configure(text="⚠ 首选项界面: 深色模式异常 (标签页缺失)", foreground="#e67e22")

        # 4. Dock Font
        if reg_status['is_font_ok']:
            self.lbl_font_status.configure(text=f"✓ Dock字体: {reg_status['dock_font']}", foreground="#27ae60")
        else:
            font_show = reg_status['dock_font'] if reg_status['dock_font'] else '默认'
            self.lbl_font_status.configure(text=f"⚠ Dock字体: {font_show} (建议微软雅黑)", foreground="#e67e22")

    def on_browse(self):
        p = filedialog.askopenfilename(
            title="选择 Nexus.exe",
            filetypes=[("Nexus Executable", "Nexus.exe"), ("Executable", "*.exe"), ("All Files", "*.*")]
        )
        if p:
            self.exe_path_var.set(p)
            self.refresh_status()

    def on_auto_detect(self):
        p = WinstepProcessManager.auto_detect_exe()
        if p:
            self.exe_path_var.set(p)
            self.log(f"自动检测到程序位置: {p}", "SUCCESS")
        else:
            self.log("未能自动检测到 Nexus 路径，请点击“浏览...”手动选择。", "WARN")
        self.refresh_status()

    def run_async(self, target_func):
        t = threading.Thread(target=target_func, daemon=True)
        t.start()

    def on_full_fix(self):
        exe_path = self.exe_path_var.get()
        if not exe_path or not os.path.exists(exe_path):
            messagebox.showerror("错误", "请先选择有效的 Nexus.exe 文件路径！")
            return

        def task():
            self.log(">>> 开始执行一键全量深度修复流程...", "INFO")

            # 1. Stop Nexus
            pids = WinstepProcessManager.get_nexus_pids()
            if pids:
                self.log(f"正在安全退出当前运行的 Nexus (PID {pids[0]})...", "INFO")
                if WinstepProcessManager.stop_nexus():
                    self.log("Nexus 进程已安全停止。", "SUCCESS")
                else:
                    self.log("警告: 强制关闭 Nexus 失败，文件可能被占用。", "WARN")
                time.sleep(1)

            # 2. Binary Patch
            self.log("正在分析并修补二进制文件 (核心托盘字符集 Bug 修复)...", "INFO")
            patcher = WinstepPatcher(exe_path)
            ok, msg = patcher.apply_patch(create_backup=True)
            if ok:
                self.log(f"二进制修补完成: {msg}", "SUCCESS")
            else:
                self.log(f"二进制修补失败: {msg}", "ERROR")

            # 3. Registry Fix
            self.log("正在修复注册表首选项 Dark Mode 标签页设置 (UIDarkMode=0)...", "INFO")
            ok_reg, msg_reg = self.reg_mgr.set_dark_mode(0)
            if ok_reg:
                self.log(f"注册表首选项设置完成: {msg_reg}", "SUCCESS")
            else:
                self.log(f"注册表写入失败: {msg_reg}", "ERROR")

            # 4. Dock Font
            self.log("正在配置 Dock 显示字体为 Microsoft YaHei UI...", "INFO")
            ok_font, msg_font = self.reg_mgr.set_dock_font('Microsoft YaHei UI')
            if ok_font:
                self.log(f"字体设置完成: {msg_font}", "SUCCESS")

            # 5. Language Packs
            self.log("正在安装并覆盖优化版中文语言包...", "INFO")
            lang_mgr = WinstepLangManager(exe_path)
            ok_lang, msg_lang = lang_mgr.install_language_packs()
            if ok_lang:
                self.log(f"语言包部署完成: {msg_lang}", "SUCCESS")
            else:
                self.log(f"语言包安装提示: {msg_lang}", "WARN")

            # 6. Restart Nexus
            self.log("正在交互桌面重新启动 Nexus...", "INFO")
            ok_start, msg_start = WinstepProcessManager.start_nexus(exe_path)
            if ok_start:
                self.log(f"Nexus 启动成功: {msg_start}", "SUCCESS")
            else:
                self.log(f"Nexus 启动失败: {msg_start}", "WARN")

            self.root.after(500, self.refresh_status)
            self.log(">>> 全量修复操作全部完成！鼠标悬浮托盘图标即可查看无乱码中文。", "SUCCESS")
            messagebox.showinfo(
                "完成",
                "全量深度修复已完成！\n\n"
                "1. 托盘气泡乱码已彻底修复 (Clash/音量/电源等)\n"
                "2. 首选项 8 个设置标签页已完整恢复\n"
                "3. 微软雅黑清晰字体已配置\n"
                "4. 优化中文语言包已就绪"
            )

        self.run_async(task)

    def on_patch_only(self):
        exe_path = self.exe_path_var.get()
        if not exe_path or not os.path.exists(exe_path):
            messagebox.showerror("错误", "请先选择有效的 Nexus.exe 文件路径！")
            return

        def task():
            pids = WinstepProcessManager.get_nexus_pids()
            if pids:
                self.log("正在停止 Nexus 以进行二进制写入...", "INFO")
                WinstepProcessManager.stop_nexus()
                time.sleep(1)

            patcher = WinstepPatcher(exe_path)
            ok, msg = patcher.apply_patch(create_backup=True)
            if ok:
                self.log(f"补丁写入成功: {msg}", "SUCCESS")
                WinstepProcessManager.start_nexus(exe_path)
            else:
                self.log(f"补丁写入失败: {msg}", "ERROR")
            self.root.after(500, self.refresh_status)

        self.run_async(task)

    def on_fix_tabs_only(self):
        ok, msg = self.reg_mgr.set_dark_mode(0)
        self.reg_mgr.set_dock_font('Microsoft YaHei UI')
        if ok:
            self.log("首选项界面设置已成功优化 (恢复完整 8 标签页)。", "SUCCESS")
            messagebox.showinfo("提示", "首选项标签页已修复！重新打开 Nexus 首选项即可生效。")
        else:
            self.log(f"修改失败: {msg}", "ERROR")
        self.refresh_status()

    def on_install_lang_only(self):
        exe_path = self.exe_path_var.get()
        lang_mgr = WinstepLangManager(exe_path)
        ok, msg = lang_mgr.install_language_packs()
        if ok:
            self.log(f"语言包安装成功: {msg}", "SUCCESS")
            messagebox.showinfo("提示", "优化中文语言包安装完成！")
        else:
            self.log(f"语言包安装失败: {msg}", "ERROR")
        self.refresh_status()

    def on_restart_nexus(self):
        exe_path = self.exe_path_var.get()
        if not exe_path or not os.path.exists(exe_path):
            messagebox.showerror("错误", "找不到 Nexus.exe 路径！")
            return

        def task():
            self.log("正在重启 Nexus...", "INFO")
            WinstepProcessManager.stop_nexus()
            time.sleep(1)
            ok, msg = WinstepProcessManager.start_nexus(exe_path)
            if ok:
                self.log(f"重启成功: {msg}", "SUCCESS")
            else:
                self.log(f"启动失败: {msg}", "ERROR")
            self.root.after(500, self.refresh_status)

        self.run_async(task)

    def on_restore_backup(self):
        exe_path = self.exe_path_var.get()
        if not exe_path:
            return

        patcher = WinstepPatcher(exe_path)
        if not os.path.exists(patcher.bak_path):
            messagebox.showwarning("警告", "未找到备份文件 (.bak)！")
            return

        if not messagebox.askyesno("确认", "确定要还原官方未修改的原始 Nexus.exe 吗？"):
            return

        def task():
            self.log("正在停止 Nexus 并还原官方备份文件...", "INFO")
            WinstepProcessManager.stop_nexus()
            time.sleep(1)
            ok, msg = patcher.restore_backup()
            if ok:
                self.log(f"备份还原成功: {msg}", "SUCCESS")
                WinstepProcessManager.start_nexus(exe_path)
            else:
                self.log(f"还原失败: {msg}", "ERROR")
            self.root.after(500, self.refresh_status)

        self.run_async(task)


def launch_gui():
    init_high_dpi()
    root = tk.Tk()
    app = ModernFixerApp(root)
    root.mainloop()


if __name__ == '__main__':
    launch_gui()
