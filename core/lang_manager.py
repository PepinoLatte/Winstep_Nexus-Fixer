"""
Winstep Language Pack Manager
Deploys optimized GB18030 Simplified/Traditional Chinese language packs.
"""

import os
import shutil


class WinstepLangManager:
    DEFAULT_PROGRAMDATA_LANG = r'C:\ProgramData\WinStep\Languages'

    def __init__(self, exe_path: str = None, repo_languages_dir: str = None):
        self.exe_path = exe_path
        if repo_languages_dir and os.path.exists(repo_languages_dir):
            self.repo_languages_dir = repo_languages_dir
        else:
            # Look relative to current file or exe
            cur_dir = os.path.dirname(os.path.abspath(__file__))
            candidate = os.path.join(os.path.dirname(cur_dir), 'Languages')
            self.repo_languages_dir = candidate if os.path.exists(candidate) else None

    def get_destination_dirs(self) -> list[str]:
        """Find all valid destination directories for language packs."""
        dirs = []
        if os.path.exists(self.DEFAULT_PROGRAMDATA_LANG):
            dirs.append(self.DEFAULT_PROGRAMDATA_LANG)

        if self.exe_path:
            exe_dir = os.path.dirname(os.path.abspath(self.exe_path))
            app_lang_dir = os.path.join(exe_dir, 'Languages')
            if app_lang_dir not in dirs and os.path.exists(app_lang_dir):
                dirs.append(app_lang_dir)

        return dirs

    def install_language_packs(self) -> tuple[bool, str]:
        """Deploy bundled optimized Chinese language packs."""
        if not self.repo_languages_dir or not os.path.exists(self.repo_languages_dir):
            return False, 'Bundled Languages folder not found.'

        dest_dirs = self.get_destination_dirs()
        if not dest_dirs:
            # Try to create ProgramData lang dir if parent exists
            pd_parent = r'C:\ProgramData\WinStep'
            if os.path.exists(pd_parent):
                os.makedirs(self.DEFAULT_PROGRAMDATA_LANG, exist_ok=True)
                dest_dirs.append(self.DEFAULT_PROGRAMDATA_LANG)
            else:
                return False, 'No Winstep Languages destination folder found.'

        installed_count = 0
        for dest_root in dest_dirs:
            for sub in ['NeXuS', 'Update Manager', 'Xtreme']:
                src_sub = os.path.join(self.repo_languages_dir, sub)
                if not os.path.exists(src_sub):
                    continue
                dest_sub = os.path.join(dest_root, sub)
                os.makedirs(dest_sub, exist_ok=True)

                for f in os.listdir(src_sub):
                    if f.lower().endswith('.ini'):
                        shutil.copy2(os.path.join(src_sub, f), os.path.join(dest_sub, f))
                        installed_count += 1

        return True, f'Successfully installed {installed_count} Chinese language files.'
