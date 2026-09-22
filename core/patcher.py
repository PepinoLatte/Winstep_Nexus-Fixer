"""
Winstep Nexus / Xtreme Universal Systray Unicode Patcher
Automated AOB signature scanner & dynamic binary patcher.
Fixes VB6 DBCS character corruption in mirrored tray tooltips across all Windows versions.
"""

import os
import shutil
import struct


class WinstepPatcher:
    def __init__(self, exe_path: str):
        self.exe_path = exe_path
        self.bak_path = exe_path + '.bak'

    def parse_pe_sections(self, data: bytes):
        """Extract PE sections and memory mapping."""
        e_lfanew = struct.unpack('<I', data[0x3c:0x40])[0]
        num_sections = struct.unpack('<H', data[e_lfanew+0x06:e_lfanew+0x08])[0]
        opt_hdr_size = struct.unpack('<H', data[e_lfanew+0x14:e_lfanew+0x16])[0]
        image_base = struct.unpack('<I', data[e_lfanew+0x34:e_lfanew+0x38])[0]
        sec_tbl = e_lfanew + 0x18 + opt_hdr_size

        sections = []
        for i in range(num_sections):
            sec = data[sec_tbl + i*40 : sec_tbl + (i+1)*40]
            name = sec[:8].rstrip(b'\x00').decode('latin1', errors='ignore')
            vsize, vaddr, rsize, raddr = struct.unpack('<IIII', sec[8:24])
            sections.append({
                'name': name,
                'va_start': image_base + vaddr,
                'va_end': image_base + vaddr + vsize,
                'raw_start': raddr,
                'raw_end': raddr + rsize,
                'vaddr': vaddr,
                'raddr': raddr
            })
        return image_base, sections

    def raw_to_va(self, raw: int, sections: list) -> int:
        for s in sections:
            if s['raw_start'] <= raw < s['raw_end']:
                return s['va_start'] + (raw - s['raw_start'])
        return raw + 0x400c00  # Fallback standard offset

    def va_to_raw(self, va: int, sections: list) -> int:
        for s in sections:
            if s['va_start'] <= va < s['va_end']:
                return s['raw_start'] + (va - s['va_start'])
        return va - 0x400c00  # Fallback standard offset

    def _parse_unpatched_site(self, data: bytes, call_raw: int, call_va: int, wrapper_va: int, sections: list) -> dict:
        """Parse unpatched site details dynamically: start VA, jump dest VA, hProcess, copy_iat, and routine type."""
        pre = data[call_raw-7:call_raw]
        h_proc = None
        if pre[-1] == 0x51 and pre[-7:-5] == b'\x8b\x0d':
            h_proc = int.from_bytes(pre[-5:-1], 'little')
        elif pre[-1] == 0x52 and pre[-7:-5] == b'\x8b\x15':
            h_proc = int.from_bytes(pre[-5:-1], 'little')
        elif pre[-1] == 0x50 and pre[-6] == 0xa1:
            h_proc = int.from_bytes(pre[-5:-1], 'little')

        if not h_proc:
            return None

        # Dynamically locate start_raw by scanning backward from call_raw for:
        # lea reg, [ebp - 0x54/0x50] (8d [45/4d/55] [ac/b0]) followed by push reg (50+reg)
        start_raw = None
        for off in range(call_raw - 35, call_raw - 60, -1):
            if data[off] == 0x8d and data[off+1] in (0x45, 0x4d, 0x55) and data[off+2] in (0xac, 0xb0):
                reg = (data[off+1] >> 3) & 7
                if data[off+3] == 0x50 + reg:
                    start_raw = off
                    break

        if start_raw is None:
            # Fallback: scan for line number assignment c7 45 fc ?? 00 00 00
            for off in range(call_raw - 35, call_raw - 60, -1):
                if data[off:off+3] == b'\xc7\x45\xfc' and data[off+4:off+7] == b'\x00\x00\x00':
                    start_raw = off + 7
                    break

        if start_raw is None:
            return None

        start_va = self.raw_to_va(start_raw, sections)

        p80 = data.find(b'\x68\x80\x00\x00\x00', call_raw, call_raw + 100)
        if p80 == -1:
            return None

        post_p80 = data[p80:p80+120]
        if b'\x8d\x4d\x88' in post_p80:
            rtype = 'A'
            idx = post_p80.find(b'\x8d\x4d\x88')
            copy_iat = int.from_bytes(post_p80[idx+5:idx+9], 'little')
            jump_raw = p80 + idx + 9
        elif b'\x8d\x8d\x70\xff\xff\xff' in post_p80:
            rtype = 'B'
            idx = post_p80.find(b'\x8d\x8d\x70\xff\xff\xff')
            copy_iat = int.from_bytes(post_p80[idx+8:idx+12], 'little')
            jump_raw = p80 + idx + 12
        else:
            return None

        jump_va = self.raw_to_va(jump_raw, sections)
        avail = jump_raw - start_raw

        return {
            'call_va': call_va,
            'call_raw': call_raw,
            'start_va': start_va,
            'start_raw': start_raw,
            'jump_va': jump_va,
            'jump_raw': jump_raw,
            'avail': avail,
            'type': rtype,
            'h_proc': h_proc,
            'copy_iat': copy_iat,
            'wrapper_va': wrapper_va
        }

    def _parse_patched_site(self, data: bytes, call_raw: int, call_va: int, wrapper_va: int, sections: list) -> dict:
        """Parse already-patched site details."""
        start_raw = call_raw - 21
        start_va = self.raw_to_va(start_raw, sections)
        return {
            'call_va': call_va,
            'call_raw': call_raw,
            'start_va': start_va,
            'start_raw': start_raw,
            'wrapper_va': wrapper_va
        }

    def analyze(self):
        """Analyze the target executable for tray tooltip reading routines."""
        if not os.path.exists(self.exe_path):
            return {'status': 'FILE_NOT_FOUND', 'error': f'File not found: {self.exe_path}'}

        try:
            with open(self.exe_path, 'rb') as f:
                data = f.read()
        except Exception as e:
            return {'status': 'ERROR', 'error': str(e)}

        image_base, sections = self.parse_pe_sections(data)

        # 1. Locate ReadProcessMemory API wrapper dynamically
        name_raw = data.find(b'ReadProcessMemory\x00')
        if name_raw == -1:
            return {'status': 'NOT_WINSTEP', 'error': 'ReadProcessMemory signature not found'}

        name_va = self.raw_to_va(name_raw, sections)
        ptr_raw = data.find(struct.pack('<I', name_va))
        if ptr_raw == -1:
            return {'status': 'NOT_WINSTEP', 'error': 'API struct pointer not found'}

        struct_raw = ptr_raw - 4
        struct_va = self.raw_to_va(struct_raw, sections)

        push_raw = data.find(b'\x68' + struct.pack('<I', struct_va))
        if push_raw == -1:
            return {'status': 'NOT_WINSTEP', 'error': 'API wrapper call stub not found'}

        wrapper_raw = push_raw - 11
        wrapper_va = self.raw_to_va(wrapper_raw, sections)

        # 2. Dynamically scan .text section for all calls to ReadProcessMemory wrapper
        unpatched_sites = []
        patched_sites = []

        for sec in sections:
            if sec['name'] == '.text':
                s_raw, e_raw = sec['raw_start'], sec['raw_end']
                for offset in range(s_raw, e_raw - 5):
                    if data[offset] == 0xe8:
                        rel = int.from_bytes(data[offset+1:offset+5], 'little', signed=True)
                        call_va = self.raw_to_va(offset, sections)
                        if call_va + 5 + rel == wrapper_va:
                            chunk = data[offset:offset+100]
                            if b'\x68\x80\x00\x00\x00' in chunk:
                                site_info = self._parse_unpatched_site(data, offset, call_va, wrapper_va, sections)
                                if site_info:
                                    unpatched_sites.append(site_info)
                            elif b'\x66\xc7\x81\xfe\x01\x00\x00\x00\x00' in chunk:
                                site_info = self._parse_patched_site(data, offset, call_va, wrapper_va, sections)
                                if site_info:
                                    patched_sites.append(site_info)

        if len(patched_sites) == 6:
            status = 'PATCHED'
        elif len(unpatched_sites) == 6:
            status = 'UNPATCHED'
        elif len(patched_sites) > 0 or len(unpatched_sites) > 0:
            status = 'PARTIALLY_PATCHED'
        else:
            status = 'UNKNOWN'

        return {
            'status': status,
            'image_base': image_base,
            'sections': sections,
            'wrapper_va': wrapper_va,
            'patched_count': len(patched_sites),
            'unpatched_count': len(unpatched_sites),
            'total_sites': 6,
            'patched_sites': patched_sites,
            'unpatched_sites': unpatched_sites,
            'has_backup': os.path.exists(self.bak_path),
            'bak_path': self.bak_path
        }

    def build_routine_a(self, site_va: int, jump_dest_va: int, rpm_wrapper_va: int, h_proc_va: int, copy_iat_va: int) -> bytes:
        """Machine code for Routine A (tray primary toolbars)."""
        rel_call = rpm_wrapper_va - (site_va + 21 + 5)
        rel_call_bytes = rel_call.to_bytes(4, 'little', signed=True)

        code = bytearray()
        code += bytes.fromhex('8d 45 ac')                    # lea eax, [ebp - 0x54]
        code += bytes.fromhex('50')                          # push eax
        code += bytes.fromhex('68 00 02 00 00')              # push 0x200 (512 bytes)
        code += bytes.fromhex('ff 75 a8')                    # push dword ptr [ebp - 0x58]
        code += bytes.fromhex('ff 75 a0')                    # push dword ptr [ebp - 0x60]
        code += b'\xff\x35' + h_proc_va.to_bytes(4, 'little')# push dword ptr [hProcess]
        code += b'\xe8' + rel_call_bytes                     # call ReadProcessMemory
        code += bytes.fromhex('8b 4d a8')                    # mov ecx, dword ptr [ebp - 0x58]
        code += bytes.fromhex('66 c7 81 fe 01 00 00 00 00')  # mov word ptr [ecx + 0x1fe], 0
        code += bytes.fromhex('8b 55 a8')                    # mov edx, dword ptr [ebp - 0x58]
        code += bytes.fromhex('8d 4d 88')                    # lea ecx, [ebp - 0x78]
        code += b'\xff\x15' + copy_iat_va.to_bytes(4, 'little')# call dword ptr [__vbaStrCopy]

        curr_len = len(code) + 5
        rel_jmp = jump_dest_va - (site_va + curr_len)
        code += b'\xe9' + rel_jmp.to_bytes(4, 'little', signed=True)
        return bytes(code)

    def build_routine_b(self, site_va: int, jump_dest_va: int, rpm_wrapper_va: int, h_proc_va: int, copy_iat_va: int) -> bytes:
        """Machine code for Routine B (tray overflow / secondary toolbars)."""
        rel_call = rpm_wrapper_va - (site_va + 21 + 5)
        rel_call_bytes = rel_call.to_bytes(4, 'little', signed=True)

        code = bytearray()
        code += bytes.fromhex('8d 45 b0')                    # lea eax, [ebp - 0x50]
        code += bytes.fromhex('50')                          # push eax
        code += bytes.fromhex('68 00 02 00 00')              # push 0x200 (512 bytes)
        code += bytes.fromhex('ff 75 ac')                    # push dword ptr [ebp - 0x54]
        code += bytes.fromhex('ff 75 a0')                    # push dword ptr [ebp - 0x60]
        code += b'\xff\x35' + h_proc_va.to_bytes(4, 'little')# push dword ptr [hProcess]
        code += b'\xe8' + rel_call_bytes                     # call ReadProcessMemory
        code += bytes.fromhex('8b 4d ac')                    # mov ecx, dword ptr [ebp - 0x54]
        code += bytes.fromhex('66 c7 81 fe 01 00 00 00 00')  # mov word ptr [ecx + 0x1fe], 0
        code += bytes.fromhex('8b 55 ac')                    # mov edx, dword ptr [ebp - 0x54]
        code += bytes.fromhex('8d 8d 70 ff ff ff')           # lea ecx, [ebp - 0x90]
        code += b'\xff\x15' + copy_iat_va.to_bytes(4, 'little')# call dword ptr [__vbaStrCopy]

        curr_len = len(code) + 5
        rel_jmp = jump_dest_va - (site_va + curr_len)
        code += b'\xe9' + rel_jmp.to_bytes(4, 'little', signed=True)
        return bytes(code)

    def apply_patch(self, create_backup: bool = True) -> tuple[bool, str]:
        """Apply the UTF-16 pass-through binary patch dynamically across any Winstep version."""
        info = self.analyze()
        if info['status'] == 'FILE_NOT_FOUND':
            return False, info['error']
        if info['status'] == 'PATCHED':
            return True, 'All 6 systray routines are already patched.'

        sites = info.get('unpatched_sites', [])
        if not sites:
            return False, 'No unpatched systray tooltip routines detected.'

        if create_backup and not os.path.exists(self.bak_path):
            try:
                shutil.copy2(self.exe_path, self.bak_path)
            except Exception as e:
                return False, f'Failed to create backup: {e}'

        try:
            with open(self.exe_path, 'rb') as f:
                data = bytearray(f.read())
        except Exception as e:
            return False, f'Cannot open file for writing: {e}'

        wrapper_va = info['wrapper_va']
        patched_count = 0

        for site in sites:
            sva = site['start_va']
            sraw = site['start_raw']
            jva = site['jump_va']
            jraw = site['jump_raw']
            avail = site['avail']
            rtype = site['type']
            h_proc = site['h_proc']
            copy_iat = site['copy_iat']

            builder = self.build_routine_a if rtype == 'A' else self.build_routine_b
            patch = builder(sva, jva, wrapper_va, h_proc, copy_iat)

            if len(patch) > avail:
                return False, f'Patch size ({len(patch)}) exceeds space ({avail}) at {hex(sva)}'

            full_block = patch + b'\x90' * (avail - len(patch))
            data[sraw:jraw] = full_block
            patched_count += 1

        try:
            with open(self.exe_path, 'wb') as f:
                f.write(data)
        except Exception as e:
            return False, f'Failed to write patched executable: {e}'

        return True, f'Successfully patched {patched_count}/6 systray routines!'

    def restore_backup(self) -> tuple[bool, str]:
        """Restore pristine executable from backup."""
        if not os.path.exists(self.bak_path):
            return False, f'Backup file not found: {self.bak_path}'

        try:
            shutil.copy2(self.bak_path, self.exe_path)
            return True, 'Original executable restored successfully from backup.'
        except Exception as e:
            return False, f'Failed to restore backup: {e}'
