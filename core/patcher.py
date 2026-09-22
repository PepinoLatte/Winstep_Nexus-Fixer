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

        # 1. Locate ReadProcessMemory API wrapper
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

        # 2. Locate all candidate sites calling ReadProcessMemory
        unpatched_sites = []
        patched_sites = []

        # Known relative sites for Winstep 26.x
        known_sites = [
            (1, 0x8ef279, 0x8ef30f, 'A'),
            (2, 0x8ef60a, 0x8ef6a0, 'A'),
            (3, 0x8ef998, 0x8efa2d, 'A'),
            (4, 0x8effa5, 0x8f0047, 'B'),
            (5, 0x8f0460, 0x8f0501, 'B'),
            (6, 0x8f087a, 0x8f091c, 'B'),
        ]

        # Check the 6 known sites
        for num, sva, jva, rtype in known_sites:
            raw_s = self.va_to_raw(sva, sections)
            raw_j = self.va_to_raw(jva, sections)
            block = data[raw_s:raw_j]
            # Check for direct UTF-16 patch signature (mov word ptr [ecx + 0x1fe], 0)
            if b'\x66\xc7\x81\xfe\x01\x00\x00\x00\x00' in block:
                patched_sites.append({'id': num, 'va': sva, 'jump_va': jva, 'type': rtype, 'raw': raw_s})
            elif b'\x68\x80\x00\x00\x00' in block or b'\xff\x15' in block:
                unpatched_sites.append({'id': num, 'va': sva, 'jump_va': jva, 'type': rtype, 'raw': raw_s})

        if len(patched_sites) == 6:
            status = 'PATCHED'
        elif len(unpatched_sites) == 6:
            status = 'UNPATCHED'
        elif len(patched_sites) > 0 and len(unpatched_sites) > 0:
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
            'has_backup': os.path.exists(self.bak_path),
            'bak_path': self.bak_path
        }

    def build_routine_a(self, site_va: int, jump_dest_va: int, rpm_wrapper_va: int = 0x4cb0a4) -> bytes:
        """Machine code for Routine A (tray primary toolbars)."""
        rel_call = rpm_wrapper_va - (site_va + 21 + 5)
        rel_call_bytes = rel_call.to_bytes(4, 'little', signed=True)

        code = bytearray()
        code += bytes.fromhex('8d 45 ac')                    # lea eax, [ebp - 0x54]
        code += bytes.fromhex('50')                          # push eax
        code += bytes.fromhex('68 00 02 00 00')              # push 0x200 (512 bytes)
        code += bytes.fromhex('ff 75 a8')                    # push dword ptr [ebp - 0x58]
        code += bytes.fromhex('ff 75 a0')                    # push dword ptr [ebp - 0x60]
        code += bytes.fromhex('ff 35 c8 26 b2 00')           # push dword ptr [0xb226c8]
        code += b'\xe8' + rel_call_bytes                     # call ReadProcessMemory
        code += bytes.fromhex('8b 4d a8')                    # mov ecx, dword ptr [ebp - 0x58]
        code += bytes.fromhex('66 c7 81 fe 01 00 00 00 00')  # mov word ptr [ecx + 0x1fe], 0
        code += bytes.fromhex('8b 55 a8')                    # mov edx, dword ptr [ebp - 0x58]
        code += bytes.fromhex('8d 4d 88')                    # lea ecx, [ebp - 0x78]
        code += bytes.fromhex('ff 15 0c dc b5 00')           # call dword ptr [__vbaStrCopy]

        curr_len = len(code) + 5
        rel_jmp = jump_dest_va - (site_va + curr_len)
        code += b'\xe9' + rel_jmp.to_bytes(4, 'little', signed=True)
        return bytes(code)

    def build_routine_b(self, site_va: int, jump_dest_va: int, rpm_wrapper_va: int = 0x4cb0a4) -> bytes:
        """Machine code for Routine B (tray overflow / secondary toolbars)."""
        rel_call = rpm_wrapper_va - (site_va + 21 + 5)
        rel_call_bytes = rel_call.to_bytes(4, 'little', signed=True)

        code = bytearray()
        code += bytes.fromhex('8d 45 b0')                    # lea eax, [ebp - 0x50]
        code += bytes.fromhex('50')                          # push eax
        code += bytes.fromhex('68 00 02 00 00')              # push 0x200 (512 bytes)
        code += bytes.fromhex('ff 75 ac')                    # push dword ptr [ebp - 0x54]
        code += bytes.fromhex('ff 75 a0')                    # push dword ptr [ebp - 0x60]
        code += bytes.fromhex('ff 35 c8 26 b2 00')           # push dword ptr [0xb226c8]
        code += b'\xe8' + rel_call_bytes                     # call ReadProcessMemory
        code += bytes.fromhex('8b 4d ac')                    # mov ecx, dword ptr [ebp - 0x54]
        code += bytes.fromhex('66 c7 81 fe 01 00 00 00 00')  # mov word ptr [ecx + 0x1fe], 0
        code += bytes.fromhex('8b 55 ac')                    # mov edx, dword ptr [ebp - 0x54]
        code += bytes.fromhex('8d 8d 70 ff ff ff')           # lea ecx, [ebp - 0x90]
        code += bytes.fromhex('ff 15 0c dc b5 00')           # call dword ptr [__vbaStrCopy]

        curr_len = len(code) + 5
        rel_jmp = jump_dest_va - (site_va + curr_len)
        code += b'\xe9' + rel_jmp.to_bytes(4, 'little', signed=True)
        return bytes(code)

    def apply_patch(self, create_backup: bool = True) -> tuple[bool, str]:
        """Apply the UTF-16 pass-through binary patch."""
        info = self.analyze()
        if info['status'] == 'FILE_NOT_FOUND':
            return False, info['error']

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

        sections = info['sections']
        wrapper_va = info.get('wrapper_va', 0x4cb0a4)

        sites = [
            (1, 0x8ef279, 0x8ef30f, self.build_routine_a),
            (2, 0x8ef60a, 0x8ef6a0, self.build_routine_a),
            (3, 0x8ef998, 0x8efa2d, self.build_routine_a),
            (4, 0x8effa5, 0x8f0047, self.build_routine_b),
            (5, 0x8f0460, 0x8f0501, self.build_routine_b),
            (6, 0x8f087a, 0x8f091c, self.build_routine_b),
        ]

        patched_count = 0
        for num, sva, jva, builder in sites:
            raw_s = self.va_to_raw(sva, sections)
            raw_j = self.va_to_raw(jva, sections)
            avail = raw_j - raw_s
            patch = builder(sva, jva, wrapper_va)
            if len(patch) > avail:
                return False, f'Patch size ({len(patch)}) exceeds space ({avail}) at site {num}'

            full_block = patch + b'\x90' * (avail - len(patch))
            data[raw_s:raw_j] = full_block
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
