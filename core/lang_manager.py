"""
Winstep Language Pack Manager
Deploys optimized GB18030 Simplified/Traditional Chinese language packs
and normalizes all foreign language headers to prevent ANSI code page garbled text.
"""

import os
import re
import shutil


class WinstepLangManager:
    DEFAULT_PROGRAMDATA_LANG = r'C:\ProgramData\WinStep\Languages'

    # Clean display names to prevent ANSI code page (e.g. CP936) decode collisions
    # on non-ASCII foreign language native endonyms.
    CLEAN_LANG_MAP = {
        'Arabic': 'Arabic',
        'Bulgarian': 'Balgarski',
        'Catalan': 'Catala',
        'Chinese Simplified': 'Chinese Simplified (简体中文)',
        'Chinese Traditional HK': 'Chinese Traditional HK (繁体中文 - 香港)',
        'Chinese Traditional': 'Chinese Traditional (繁体中文)',
        'Croatian': 'Hrvatski',
        'Czech': 'Cesky',
        'Danish': 'Dansk',
        'Dutch': 'Nederlands',
        'English': 'English',
        'Farsi': 'Farsi (Persian)',
        'Finnish': 'Suomi',
        'French': 'Francais',
        'German': 'Deutsch',
        'Greek': 'Greek',
        'Hungarian': 'Magyar',
        'Indonesian': 'Bahasa Indonesia',
        'Italian': 'Italiano',
        'Japanese': 'Japanese (日语)',
        'Korean': 'Korean (韩语)',
        'Lithuanian': 'Lietuviu',
        'Norwegian': 'Norsk (Bokmal)',
        'Polish': 'Polski',
        'Portuguese (Brazil)': 'Portugues (Brazil)',
        'Portuguese': 'Portugues',
        'Romanian': 'Romanian',
        'Russian': 'Russkiy',
        'Serbian': 'Srpski',
        'Slovak': 'Slovensky',
        'Spanish': 'Espanol',
        'Swedish': 'Svenska',
        'Turkish': 'Turkce',
    }

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

    def sanitize_language_headers(self, dest_root: str) -> int:
        """
        Normalize [Language] header in all INI files so that non-ASCII native names
        (e.g. Cyrillic, Greek, Shift-JIS, Windows-1252) do not display as garbled
        nonsense Chinese characters under Windows CP936 ANSI code page.
        """
        fixed_count = 0
        for sub in ['NeXuS', 'Update Manager', 'Xtreme']:
            sub_dir = os.path.join(dest_root, sub)
            if not os.path.exists(sub_dir):
                continue

            for fname in os.listdir(sub_dir):
                if not fname.lower().endswith('.ini'):
                    continue

                base_name = os.path.splitext(fname)[0]
                if base_name not in self.CLEAN_LANG_MAP:
                    continue

                clean_target = self.CLEAN_LANG_MAP[base_name]
                file_path = os.path.join(sub_dir, fname)

                try:
                    with open(file_path, 'rb') as fp:
                        content = fp.read()

                    m = re.search(rb'(?m)^Language=(.*)$', content)
                    if m:
                        old_raw = m.group(1).strip()
                        new_target_bytes = clean_target.encode('gb18030')
                        if old_raw != new_target_bytes:
                            new_content = content[:m.start()] + b'Language=' + new_target_bytes + content[m.end():]
                            with open(file_path, 'wb') as fp:
                                fp.write(new_content)
                            fixed_count += 1
                except Exception:
                    continue

        return fixed_count

    def install_language_packs(self) -> tuple[bool, str]:
        """Deploy bundled optimized Chinese language packs and sanitize language headers."""
        if not self.repo_languages_dir or not os.path.exists(self.repo_languages_dir):
            return False, 'Bundled Languages folder not found.'

        dest_dirs = self.get_destination_dirs()
        if not dest_dirs:
            pd_parent = r'C:\ProgramData\WinStep'
            if os.path.exists(pd_parent):
                os.makedirs(self.DEFAULT_PROGRAMDATA_LANG, exist_ok=True)
                dest_dirs.append(self.DEFAULT_PROGRAMDATA_LANG)
            else:
                return False, 'No Winstep Languages destination folder found.'

        installed_count = 0
        total_sanitized = 0
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

            total_sanitized += self.sanitize_language_headers(dest_root)

        return True, f'已成功安装 {installed_count} 个优化中文语言包，并修复规范化 {total_sanitized} 处多国语言列表标题防乱码。'
