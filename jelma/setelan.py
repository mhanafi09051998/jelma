"""Setelan pengguna di %APPDATA%\\Jelma\\setelan.json, plus terjemahan teks pintasan <-> RegisterHotKey."""
import json
import os
from pathlib import Path

BAWAAN = {"pintasan": "ctrl+alt+j", "jeda": False}

MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_WIN, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x8, 0x4000
# urutan kanonik saat menulis teks pintasan
_MODIFIER = (("ctrl", MOD_CONTROL), ("alt", MOD_ALT), ("shift", MOD_SHIFT), ("win", MOD_WIN))
_SINONIM_MOD = {"control": "ctrl", "ctl": "ctrl", "menu": "alt", "windows": "win", "super": "win"}

_TOMBOL: dict[str, int] = {
    **{chr(c).lower(): c for c in range(ord("A"), ord("Z") + 1)},
    **{str(d): 0x30 + d for d in range(10)},
    **{f"f{n}": 0x6F + n for n in range(1, 25)},
    "space": 0x20, "enter": 0x0D, "tab": 0x09, "esc": 0x1B, "backspace": 0x08,
    "insert": 0x2D, "delete": 0x2E, "home": 0x24, "end": 0x23, "pageup": 0x21, "pagedown": 0x22,
    "left": 0x25, "up": 0x26, "right": 0x27, "down": 0x28, "pause": 0x13,
    ";": 0xBA, "=": 0xBB, ",": 0xBC, "-": 0xBD, ".": 0xBE, "/": 0xBF, "`": 0xC0,
    "[": 0xDB, "\\": 0xDC, "]": 0xDD, "'": 0xDE,
}
_SINONIM_TOMBOL = {"spasi": "space", "return": "enter", "escape": "esc", "del": "delete", "ins": "insert",
                   "pgup": "pageup", "pgdn": "pagedown", "prior": "pageup", "next": "pagedown"}
_NAMA_VK = {vk: nama for nama, vk in _TOMBOL.items()}
VK_MODIFIER = {0x10, 0x11, 0x12, 0x5B, 0x5C, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5}


def _berkas() -> Path:
    dasar = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
    return Path(dasar) / "Jelma" / "setelan.json"


def muat() -> dict:
    """Setelan tersimpan digabung ke bawaan; berkas rusak/hilang = bawaan."""
    hasil = dict(BAWAAN)
    try:
        data = json.loads(_berkas().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return hasil
    if isinstance(data, dict):
        hasil.update({k: v for k, v in data.items() if k in BAWAAN and isinstance(v, type(BAWAAN[k]))})
    return hasil


def simpan(setelan: dict) -> None:
    berkas = _berkas()
    berkas.parent.mkdir(parents=True, exist_ok=True)
    sementara = berkas.with_suffix(".tmp")
    sementara.write_text(json.dumps(setelan, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(sementara, berkas)


def urai_pintasan(teks: str) -> tuple[int, int]:
    """"ctrl+alt+j" -> (MOD_CONTROL|MOD_ALT, 0x4A). Wajib >= 1 modifier dan tepat satu tombol biasa."""
    if not isinstance(teks, str) or not teks.strip():
        raise ValueError("pintasan kosong")
    bagian = teks.replace(" ", "").lower().split("+")
    mods, vk = 0, None
    for b in bagian:
        b = _SINONIM_MOD.get(b, b)
        mod = dict(_MODIFIER).get(b)
        if mod:
            if mods & mod:
                raise ValueError(f"modifier ganda: {b}")
            mods |= mod
            continue
        b = _SINONIM_TOMBOL.get(b, b)
        if b not in _TOMBOL:
            raise ValueError(f"tombol tidak dikenal: {b!r}")
        if vk is not None:
            raise ValueError("hanya satu tombol selain modifier")
        vk = _TOMBOL[b]
    if vk is None:
        raise ValueError("tombol utama tidak ada")
    if not mods:
        raise ValueError("butuh minimal satu modifier (Ctrl/Alt/Shift/Win)")
    return mods, vk


def format_pintasan(mods: int, vk: int) -> str:
    """Kebalikan `urai_pintasan`; MOD_NOREPEAT diabaikan."""
    if vk not in _NAMA_VK:
        raise ValueError(f"kode tombol tidak didukung: {vk:#x}")
    nama = [n for n, m in _MODIFIER if mods & m]
    if not nama:
        raise ValueError("butuh minimal satu modifier (Ctrl/Alt/Shift/Win)")
    return "+".join([*nama, _NAMA_VK[vk]])


def tampilan(teks: str) -> str:
    """"ctrl+alt+j" -> "Ctrl+Alt+J" untuk ditampilkan."""
    return "+".join(b.upper() if len(b) == 1 else b.capitalize() for b in teks.split("+"))
