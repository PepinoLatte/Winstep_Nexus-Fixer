"""
Winstep Registry Configuration Manager
Handles Dark Mode tabs fix, UI font configuration, and language settings in registry.
"""

import winreg


class WinstepRegistryManager:
    SHARED_KEY = r'Software\WinSTEP2000\Shared'
    DOCKS_KEY = r'Software\WinSTEP2000\NeXuS\Docks'
    LANG_KEY = r'Software\WinSTEP2000\NeXuS'

    def get_dark_mode(self) -> int:
        """Get UIDarkMode value (0=Normal, 1=Broken Dark Mode, 2=Alt)."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.SHARED_KEY) as k:
                val, _ = winreg.QueryValueEx(k, 'UIDarkMode')
                return int(val)
        except Exception:
            return 0

    def set_dark_mode(self, mode: int = 0) -> tuple[bool, str]:
        """Set UIDarkMode (0 restores all 8 tabs and prevents button truncation)."""
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.SHARED_KEY) as k:
                winreg.SetValueEx(k, 'UIDarkMode', 0, winreg.REG_DWORD, mode)
            return True, f'UIDarkMode set to {mode} (Preferences tabs restored).'
        except Exception as e:
            return False, f'Failed to write UIDarkMode: {e}'

    def get_dock_font(self) -> str:
        """Get Dock font name."""
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.DOCKS_KEY) as k:
                val, _ = winreg.QueryValueEx(k, 'DockFontName1')
                return str(val)
        except Exception:
            return ''

    def set_dock_font(self, font_name: str = 'Microsoft YaHei UI') -> tuple[bool, str]:
        """Set Dock font to clear Chinese font (Microsoft YaHei UI)."""
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, self.DOCKS_KEY) as k:
                winreg.SetValueEx(k, 'DockFontName1', 0, winreg.REG_SZ, font_name)
            return True, f'Dock font set to "{font_name}".'
        except Exception as e:
            return False, f'Failed to write Dock font: {e}'

    def get_status(self) -> dict:
        """Query current configuration status."""
        dark_mode = self.get_dark_mode()
        dock_font = self.get_dock_font()

        return {
            'dark_mode': dark_mode,
            'is_tabs_ok': dark_mode != 1,
            'dock_font': dock_font,
            'is_font_ok': font_is_chinese(dock_font)
        }


def font_is_chinese(font_name: str) -> bool:
    fn = font_name.lower()
    return any(k in fn for k in ['yahei', 'microsoft yahei', 'simsun', 'simhei', 'pingfang', 'dengxian', '苹方', '微软雅黑', '黑体'])
