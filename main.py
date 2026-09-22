"""
Winstep Nexus Chinese Localization Fixer
Main Entry Point (Supports both GUI and CLI mode)
"""

import argparse
import os
import sys

# Ensure winstep-nexus-fixer root is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# If executed from command line with flags in windowed mode, attach to parent console
if any(arg in sys.argv for arg in ['--check', '--fix-all', '--patch-only', '--restore', '--help', '-h', '--path']):
    try:
        import ctypes
        ctypes.windll.kernel32.AttachConsole(-1)
        sys.stdout = open('CONOUT$', 'w', encoding='utf-8')
        sys.stderr = open('CONOUT$', 'w', encoding='utf-8')
    except Exception:
        pass

from core.lang_manager import WinstepLangManager
from core.patcher import WinstepPatcher
from core.process_manager import WinstepProcessManager
from core.registry_manager import WinstepRegistryManager


def run_cli(args):
    print("=" * 60)
    print("  Winstep Nexus Chinese Localization Fixer (CLI Mode)")
    print("=" * 60)

    exe_path = args.path if args.path else WinstepProcessManager.auto_detect_exe()
    if not exe_path or not os.path.exists(exe_path):
        print(f"[ERROR] Nexus.exe not found at: {exe_path}")
        sys.exit(1)

    print(f"Target executable: {exe_path}")
    patcher = WinstepPatcher(exe_path)
    reg_mgr = WinstepRegistryManager()
    lang_mgr = WinstepLangManager(exe_path)

    if args.check:
        print("\n--- Diagnostic Status ---")
        pids = WinstepProcessManager.get_nexus_pids()
        print(f"Process running: {'YES (PID ' + str(pids[0]) + ')' if pids else 'NO'}")
        p_res = patcher.analyze()
        print(f"Binary patch status: {p_res['status']} ({p_res.get('patched_count', 0)}/6 patched)")
        r_res = reg_mgr.get_status()
        print(f"Preferences tabs: {'OK (UIDarkMode=0)' if r_res['is_tabs_ok'] else 'BROKEN (UIDarkMode=1)'}")
        print(f"Dock font: {r_res['dock_font']}")
        sys.exit(0)

    if args.restore:
        print("\n[Restoring] Restoring from backup (.bak)...")
        WinstepProcessManager.stop_nexus()
        ok, msg = patcher.restore_backup()
        print(f"Result: {msg}")
        WinstepProcessManager.start_nexus(exe_path)
        sys.exit(0 if ok else 1)

    if args.fix_all or args.patch_only:
        print("\n[Patching] Stopping Nexus if running...")
        WinstepProcessManager.stop_nexus()

        print("[Patching] Applying binary patch...")
        ok, msg = patcher.apply_patch(create_backup=True)
        print(f"Binary patch: {msg}")

        if args.fix_all:
            print("[Registry] Fixing Preferences tabs (UIDarkMode=0)...")
            reg_mgr.set_dark_mode(0)
            print("[Registry] Setting Dock font to Microsoft YaHei UI...")
            reg_mgr.set_dock_font("Microsoft YaHei UI")
            print("[Languages] Deploying Chinese language packs...")
            ok_l, msg_l = lang_mgr.install_language_packs()
            print(f"Language packs: {msg_l}")

        print("[Process] Restarting Nexus on interactive desktop...")
        WinstepProcessManager.start_nexus(exe_path)
        print("\n[SUCCESS] All fixes completed successfully!")


def main():
    parser = argparse.ArgumentParser(description="Winstep Nexus Chinese Localization Fixer")
    parser.add_argument("--fix-all", action="store_true", help="Apply all fixes (binary patch, tabs, font, language packs)")
    parser.add_argument("--patch-only", action="store_true", help="Only apply binary systray tooltip patch")
    parser.add_argument("--check", action="store_true", help="Check current system and patch status")
    parser.add_argument("--restore", action="store_true", help="Restore pristine Nexus.exe from backup")
    parser.add_argument("--path", type=str, default="", help="Path to Nexus.exe")
    parser.add_argument("--gui", action="store_true", help="Force GUI mode")

    args = parser.parse_args()

    # If any CLI action is specified, run CLI; otherwise launch GUI
    if args.fix_all or args.patch_only or args.check or args.restore:
        run_cli(args)
    else:
        from gui.app import launch_gui
        launch_gui()


if __name__ == '__main__':
    main()
