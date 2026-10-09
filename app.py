# -*- coding: utf-8 -*-
"""窗口透明工具：按软件设置透明度，支持常驻和鼠标感应。"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox


GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x00080000
WS_EX_APPWINDOW = 0x00040000
WS_EX_TOOLWINDOW = 0x00000080
LWA_ALPHA = 0x00000002
GA_ROOT = 2
GW_OWNER = 4
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
DWMWA_CLOAKED = 14
MAX_PATH = 32767

user32 = ctypes.WinDLL("user32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)

try:
    dwmapi = ctypes.WinDLL("dwmapi")
except OSError:
    dwmapi = None

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

user32.IsWindow.argtypes = [wintypes.HWND]
user32.IsWindow.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.IsWindowVisible.restype = wintypes.BOOL
user32.IsIconic.argtypes = [wintypes.HWND]
user32.IsIconic.restype = wintypes.BOOL
user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetWindow.restype = wintypes.HWND
user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
user32.GetAncestor.restype = wintypes.HWND
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.restype = ctypes.c_int
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.GetClassNameW.restype = ctypes.c_int
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
user32.GetCursorPos.restype = wintypes.BOOL
user32.WindowFromPoint.argtypes = [wintypes.POINT]
user32.WindowFromPoint.restype = wintypes.HWND
user32.GetLayeredWindowAttributes.argtypes = [
    wintypes.HWND,
    ctypes.POINTER(wintypes.COLORREF),
    ctypes.POINTER(wintypes.BYTE),
    ctypes.POINTER(wintypes.DWORD),
]
user32.GetLayeredWindowAttributes.restype = wintypes.BOOL
user32.SetLayeredWindowAttributes.argtypes = [
    wintypes.HWND,
    wintypes.COLORREF,
    wintypes.BYTE,
    wintypes.DWORD,
]
user32.SetLayeredWindowAttributes.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [WNDENUMPROC, wintypes.LPARAM]
user32.EnumWindows.restype = wintypes.BOOL
user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
user32.ShowWindow.restype = wintypes.BOOL
kernel32.GetConsoleWindow.argtypes = []
kernel32.GetConsoleWindow.restype = wintypes.HWND
kernel32.FreeConsole.argtypes = []
kernel32.FreeConsole.restype = wintypes.BOOL
kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE

kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]
kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL

if ctypes.sizeof(ctypes.c_void_p) == 8:
    GetWindowLongPtr = user32.GetWindowLongPtrW
    SetWindowLongPtr = user32.SetWindowLongPtrW
else:
    GetWindowLongPtr = user32.GetWindowLongW
    SetWindowLongPtr = user32.SetWindowLongW
GetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int]
GetWindowLongPtr.restype = ctypes.c_ssize_t
SetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
SetWindowLongPtr.restype = ctypes.c_ssize_t

SKIP_CLASSES = {
    "Progman",
    "WorkerW",
    "Shell_TrayWnd",
    "Shell_SecondaryTrayWnd",
    "NotifyIconOverflowWindow",
    "Windows.UI.Core.CoreWindow",
    "ForegroundStaging",
    "ApplicationManager_ImmersiveShellWindow",
    "DummyDWMListenerWindow",
    "EdgeUiInputTopWndClass",
    "TaskListOverlayWnd",
    "TaskListThumbnailWnd",
    "XamlExplorerHostIslandWindow",
}
SKIP_EXES = {
    "searchhost.exe",
    "shellexperiencehost.exe",
    "startmenuexperiencehost.exe",
    "textinputhost.exe",
    "lockapp.exe",
    "dwm.exe",
    "csrss.exe",
    "winlogon.exe",
    "sihost.exe",
}


def percent_to_alpha(percent):
    percent = max(0, min(100, int(percent)))
    return int(round(percent * 255 / 100.0))


def window_title(hwnd):
    length = user32.GetWindowTextLengthW(hwnd)
    buf = ctypes.create_unicode_buffer(length + 2)
    user32.GetWindowTextW(hwnd, buf, length + 2)
    return buf.value.strip()


def window_class(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def window_pid(hwnd):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def is_cloaked(hwnd):
    if not dwmapi:
        return False
    value = wintypes.DWORD()
    result = dwmapi.DwmGetWindowAttribute(
        hwnd,
        DWMWA_CLOAKED,
        ctypes.byref(value),
        ctypes.sizeof(value),
    )
    return result == 0 and value.value != 0


def process_path(pid):
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        size = wintypes.DWORD(MAX_PATH)
        buf = ctypes.create_unicode_buffer(MAX_PATH)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
            return buf.value
        return ""
    finally:
        kernel32.CloseHandle(handle)


def is_alt_tab_window(hwnd):
    if not user32.IsWindowVisible(hwnd):
        return False
    if is_cloaked(hwnd):
        return False
    class_name = window_class(hwnd)
    if class_name in SKIP_CLASSES:
        return False
    exstyle = GetWindowLongPtr(hwnd, GWL_EXSTYLE)
    owner = user32.GetWindow(hwnd, GW_OWNER)
    if exstyle & WS_EX_TOOLWINDOW and not (exstyle & WS_EX_APPWINDOW):
        return False
    if owner and not (exstyle & WS_EX_APPWINDOW):
        return False
    title = window_title(hwnd)
    if not title:
        return False
    return True


def enumerate_windows():
    found = []

    def callback(hwnd, _lparam):
        if is_alt_tab_window(hwnd):
            found.append(hwnd)
        return True

    user32.EnumWindows(WNDENUMPROC(callback), 0)
    return found


def root_from_point():
    point = wintypes.POINT()
    if not user32.GetCursorPos(ctypes.byref(point)):
        return None
    hwnd = user32.WindowFromPoint(point)
    if not hwnd:
        return None
    root = user32.GetAncestor(hwnd, GA_ROOT)
    return root or hwnd


class OriginalState:
    def __init__(self, exstyle, layered, alpha, flags, had_attr):
        self.exstyle = exstyle
        self.layered = layered
        self.alpha = alpha
        self.flags = flags
        self.had_attr = had_attr


class AppGroup:
    def __init__(self, key, exe_name, display_name, sample_title, pids, hwnds):
        self.key = key
        self.exe_name = exe_name
        self.display_name = display_name
        self.sample_title = sample_title
        self.pids = set(pids)
        self.hwnds = list(hwnds)


class GroupSettings:
    def __init__(self):
        self.enabled = False
        self.mode = "hover"  # hover / always
        self.away = 45
        self.hover = 100


class OpacityTool:
    def __init__(self, root):
        self.root = root
        self.own_pid = os.getpid()
        self.own_hwnds = set()
        self.settings = {}
        self.groups = {}
        self.originals = {}
        self.rows = {}
        self.failed = set()
        self._build_ui()
        self.refresh_groups(keep_settings=True)
        self.root.after(80, self.tick)
        self.root.protocol("WM_DELETE_WINDOW", self.on_minimize)
        self.root.bind("<Map>", self.remember_own_windows)
        self.root.after(300, self.remember_own_windows)
        hide_console()

    def _build_ui(self):
        self.root.title("窗口透明工具")
        self.root.geometry("820x640")
        self.root.minsize(720, 520)
        self.root.configure(bg="#f4f1ea")

        style = ttk.Style()
        try:
            style.theme_use("vista")
        except tk.TclError:
            pass
        style.configure("TFrame", background="#f4f1ea")
        style.configure("Card.TFrame", background="#fffaf3", relief="flat")
        style.configure("TLabel", background="#f4f1ea", foreground="#2b2b2b")
        style.configure("Card.TLabel", background="#fffaf3", foreground="#2b2b2b")
        style.configure("Hint.TLabel", background="#f4f1ea", foreground="#6b655c")
        style.configure("Title.TLabel", background="#f4f1ea", foreground="#1f1b16", font=("Microsoft YaHei UI", 16, "bold"))

        header = ttk.Frame(self.root)
        header.pack(fill="x", padx=18, pady=(16, 8))
        ttk.Label(header, text="窗口透明工具", style="Title.TLabel").pack(anchor="w")
        ttk.Label(
            header,
            text="选择软件后设置透明度。常驻会一直透明；鼠标感应是放上去用一档，移开用另一档。点右上角关闭会收到任务栏；只有点“退出并恢复”才会真正退出，并让窗口恢复正常。",
            style="Hint.TLabel",
            wraplength=760,
        ).pack(anchor="w", pady=(6, 0))

        actions = ttk.Frame(self.root)
        actions.pack(fill="x", padx=18, pady=(0, 8))
        ttk.Button(actions, text="刷新软件列表", command=self.manual_refresh).pack(side="left")
        ttk.Button(actions, text="全部停用并恢复", command=self.disable_all).pack(side="left", padx=(8, 0))
        ttk.Button(actions, text="退出并恢复", command=self.on_close).pack(side="right")
        ttk.Button(actions, text="收到任务栏", command=self.on_minimize).pack(side="right", padx=(0, 8))

        self.status = ttk.Label(self.root, text="准备就绪", style="Hint.TLabel")
        self.status.pack(fill="x", padx=18)

        canvas_host = ttk.Frame(self.root)
        canvas_host.pack(fill="both", expand=True, padx=18, pady=(8, 16))
        self.canvas = tk.Canvas(canvas_host, bg="#f4f1ea", highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_host, orient="vertical", command=self.canvas.yview)
        self.list_frame = ttk.Frame(self.canvas)
        self.list_frame.bind(
            "<Configure>",
            lambda _e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas_window = self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_canvas_resize(self, event):
        self.canvas.itemconfigure(self.canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def remember_own_windows(self, _event=None):
        try:
            self.own_hwnds.add(int(self.root.winfo_id()))
            for child in self.root.winfo_children():
                try:
                    self.own_hwnds.add(int(child.winfo_id()))
                except tk.TclError:
                    pass
        except tk.TclError:
            pass

    def group_key_for(self, hwnd, pid, exe_path):
        exe_name = os.path.basename(exe_path).lower() if exe_path else f"pid_{pid}.exe"
        title = window_title(hwnd)
        if exe_name in {"applicationframehost.exe", "explorer.exe"}:
            return f"{exe_name}::{title.lower()}", exe_name
        return exe_name, exe_name

    def collect_groups(self):
        grouped = {}
        for hwnd in enumerate_windows():
            pid = window_pid(hwnd)
            if pid == self.own_pid:
                continue
            if int(hwnd) in self.own_hwnds:
                continue
            path = process_path(pid)
            exe_name = os.path.basename(path).lower() if path else ""
            if exe_name in SKIP_EXES:
                continue
            key, exe_name = self.group_key_for(hwnd, pid, path)
            title = window_title(hwnd)
            display = exe_name[:-4] if exe_name.endswith(".exe") else (exe_name or "未知软件")
            item = grouped.get(key)
            if item is None:
                grouped[key] = AppGroup(key, exe_name, display, title, [pid], [hwnd])
            else:
                item.pids.add(pid)
                item.hwnds.append(hwnd)
                if title and (not item.sample_title or len(title) < len(item.sample_title)):
                    item.sample_title = title
        return dict(sorted(grouped.items(), key=lambda kv: kv[1].display_name.lower()))

    def refresh_groups(self, keep_settings=True):
        self.groups = self.collect_groups()
        if keep_settings:
            for key in list(self.settings):
                if key not in self.groups and not self.settings[key].enabled:
                    del self.settings[key]
        else:
            self.settings = {}
        for key in self.groups:
            self.settings.setdefault(key, GroupSettings())
        self.rebuild_rows()
        enabled_count = sum(1 for s in self.settings.values() if s.enabled)
        self.status.configure(
            text=f"找到 {len(self.groups)} 个软件，已启用 {enabled_count} 个。游戏或管理员窗口可能改不了。"
        )

    def manual_refresh(self):
        self.refresh_groups(keep_settings=True)

    def rebuild_rows(self):
        for child in self.list_frame.winfo_children():
            child.destroy()
        self.rows.clear()
        if not self.groups:
            ttk.Label(self.list_frame, text="现在没有可设置的窗口。打开软件后再点刷新。", style="Hint.TLabel").pack(
                anchor="w", pady=12
            )
            return
        for key, group in self.groups.items():
            self.add_row(group, self.settings[key])

    def add_row(self, group, setting):
        card = ttk.Frame(self.list_frame, style="Card.TFrame", padding=12)
        card.pack(fill="x", pady=6)

        enabled_var = tk.BooleanVar(value=setting.enabled)
        mode_var = tk.StringVar(value="鼠标感应" if setting.mode == "hover" else "常驻")
        away_var = tk.IntVar(value=setting.away)
        hover_var = tk.IntVar(value=setting.hover)

        title_row = ttk.Frame(card, style="Card.TFrame")
        title_row.pack(fill="x")
        ttk.Checkbutton(
            title_row,
            text=f"{group.display_name}  （{len(group.hwnds)} 个窗口）",
            variable=enabled_var,
            command=lambda: self.on_enabled(group.key, enabled_var),
            style="TCheckbutton",
        ).pack(side="left")
        ttk.Label(title_row, text=group.sample_title, style="Card.TLabel", foreground="#6b655c").pack(
            side="right"
        )

        controls = ttk.Frame(card, style="Card.TFrame")
        controls.pack(fill="x", pady=(8, 0))
        ttk.Label(controls, text="模式", style="Card.TLabel").grid(row=0, column=0, sticky="w")
        mode_box = ttk.Combobox(
            controls,
            textvariable=mode_var,
            values=("鼠标感应", "常驻"),
            state="readonly",
            width=12,
        )
        mode_box.grid(row=0, column=1, sticky="w", padx=(8, 18))
        mode_box.bind("<<ComboboxSelected>>", lambda _e: self.on_mode(group.key, mode_var))

        ttk.Label(controls, text="移开 / 常驻透明度", style="Card.TLabel").grid(row=0, column=2, sticky="w")
        away_scale = ttk.Scale(
            controls,
            from_=0,
            to=100,
            variable=away_var,
            command=lambda _v: self.on_away(group.key, away_var, away_label),
        )
        away_scale.grid(row=0, column=3, sticky="ew", padx=8)
        away_label = ttk.Label(controls, text=f"{setting.away}%", style="Card.TLabel", width=5)
        away_label.grid(row=0, column=4, sticky="w")

        ttk.Label(controls, text="鼠标放上透明度", style="Card.TLabel").grid(row=1, column=2, sticky="w", pady=(8, 0))
        hover_scale = ttk.Scale(
            controls,
            from_=0,
            to=100,
            variable=hover_var,
            command=lambda _v: self.on_hover(group.key, hover_var, hover_label),
        )
        hover_scale.grid(row=1, column=3, sticky="ew", padx=8, pady=(8, 0))
        hover_label = ttk.Label(controls, text=f"{setting.hover}%", style="Card.TLabel", width=5)
        hover_label.grid(row=1, column=4, sticky="w", pady=(8, 0))
        controls.columnconfigure(3, weight=1)

        hint = ttk.Label(
            card,
            text="100% 是完全不透明。建议移开时不要低于 15%，否则窗口会很难再点到。",
            style="Card.TLabel",
            foreground="#8a8378",
        )
        hint.pack(anchor="w", pady=(8, 0))

        self.rows[group.key] = {
            "enabled": enabled_var,
            "mode": mode_var,
            "away": away_var,
            "hover": hover_var,
        }

    def on_enabled(self, key, var):
        setting = self.settings[key]
        setting.enabled = bool(var.get())
        if not setting.enabled:
            self.restore_group(key)
        self.apply_all()

    def on_mode(self, key, var):
        self.settings[key].mode = "hover" if var.get() == "鼠标感应" else "always"
        self.apply_all()

    def on_away(self, key, var, label):
        value = int(round(var.get()))
        self.settings[key].away = value
        label.configure(text=f"{value}%")
        self.apply_all()

    def on_hover(self, key, var, label):
        value = int(round(var.get()))
        self.settings[key].hover = value
        label.configure(text=f"{value}%")
        self.apply_all()

    def disable_all(self):
        for key, setting in self.settings.items():
            setting.enabled = False
            row = self.rows.get(key)
            if row:
                row["enabled"].set(False)
        self.restore_all()
        self.status.configure(text="已全部停用，窗口已恢复正常。")

    def hovered_key(self):
        hwnd = root_from_point()
        if not hwnd or not user32.IsWindow(hwnd):
            return None
        if int(hwnd) in self.own_hwnds:
            return None
        pid = window_pid(hwnd)
        if pid == self.own_pid:
            return None
        path = process_path(pid)
        key, _exe = self.group_key_for(hwnd, pid, path)
        if key in self.settings and self.settings[key].enabled:
            return key
        # 同一软件的普通窗口：用 exe 匹配
        exe_name = os.path.basename(path).lower() if path else ""
        for group_key, group in self.groups.items():
            setting = self.settings.get(group_key)
            if setting and setting.enabled and group.exe_name == exe_name and exe_name not in {
                "applicationframehost.exe",
                "explorer.exe",
            }:
                return group_key
        return None

    def save_original(self, hwnd):
        if hwnd in self.originals:
            return
        exstyle = GetWindowLongPtr(hwnd, GWL_EXSTYLE)
        layered = bool(exstyle & WS_EX_LAYERED)
        alpha = wintypes.BYTE(255)
        color = wintypes.COLORREF()
        flags = wintypes.DWORD()
        had_attr = False
        if layered:
            had_attr = bool(
                user32.GetLayeredWindowAttributes(
                    hwnd, ctypes.byref(color), ctypes.byref(alpha), ctypes.byref(flags)
                )
            )
        self.originals[hwnd] = OriginalState(exstyle, layered, alpha.value, flags.value, had_attr)

    def set_opacity(self, hwnd, percent):
        if not user32.IsWindow(hwnd):
            return False
        self.save_original(hwnd)
        exstyle = GetWindowLongPtr(hwnd, GWL_EXSTYLE)
        if not (exstyle & WS_EX_LAYERED):
            SetWindowLongPtr(hwnd, GWL_EXSTYLE, exstyle | WS_EX_LAYERED)
        ok = user32.SetLayeredWindowAttributes(hwnd, 0, percent_to_alpha(percent), LWA_ALPHA)
        if not ok:
            self.failed.add(hwnd)
        return bool(ok)

    def restore_hwnd(self, hwnd):
        if hwnd not in self.originals or not user32.IsWindow(hwnd):
            self.originals.pop(hwnd, None)
            return
        state = self.originals.pop(hwnd)
        if state.layered and state.had_attr:
            SetWindowLongPtr(hwnd, GWL_EXSTYLE, state.exstyle | WS_EX_LAYERED)
            user32.SetLayeredWindowAttributes(hwnd, 0, state.alpha, state.flags or LWA_ALPHA)
        else:
            SetWindowLongPtr(hwnd, GWL_EXSTYLE, state.exstyle & ~WS_EX_LAYERED)
            SetWindowLongPtr(hwnd, GWL_EXSTYLE, state.exstyle)

    def restore_group(self, key):
        group = self.groups.get(key)
        if not group:
            return
        for hwnd in list(group.hwnds):
            self.restore_hwnd(hwnd)

    def restore_all(self):
        for hwnd in list(self.originals):
            self.restore_hwnd(hwnd)
        self.originals.clear()

    def apply_all(self):
        hovered = self.hovered_key()
        live_hwnds = set()
        for key, group in self.groups.items():
            setting = self.settings.get(key)
            if not setting or not setting.enabled:
                continue
            if setting.mode == "always":
                percent = setting.away
            else:
                percent = setting.hover if hovered == key else setting.away
            for hwnd in group.hwnds:
                live_hwnds.add(hwnd)
                self.set_opacity(hwnd, percent)
        for hwnd in list(self.originals):
            if hwnd not in live_hwnds:
                self.restore_hwnd(hwnd)

    def tick(self):
        try:
            self.apply_all()
        except Exception:
            pass
        if self.root.winfo_exists():
            self.root.after(80, self.tick)

    def on_minimize(self):
        self.root.iconify()

    def on_close(self):
        try:
            self.restore_all()
        finally:
            self.root.destroy()


def hide_console():
    try:
        hwnd = kernel32.GetConsoleWindow()
        if hwnd:
            user32.ShowWindow(hwnd, 0)
            kernel32.FreeConsole()
    except Exception:
        pass


def find_pythonw():
    import shutil
    exe_dir = os.path.dirname(sys.executable)
    candidates = [os.path.join(exe_dir, "pythonw.exe")]
    which = shutil.which("pythonw") or shutil.which("pythonw.exe")
    if which:
        candidates.append(which)
    uv_root = os.path.join(os.environ.get("APPDATA", ""), "uv", "python")
    if os.path.isdir(uv_root):
        for root, _dirs, files in os.walk(uv_root):
            if "pythonw.exe" in files:
                candidates.append(os.path.join(root, "pythonw.exe"))
                break
    seen = set()
    for item in candidates:
        if not item:
            continue
        key = os.path.normcase(os.path.abspath(item))
        if key in seen or not os.path.isfile(item):
            continue
        seen.add(key)
        # 跳过只有几十 KB 的虚拟环境跳板，它们有时会再打开带窗口的 python.exe
        try:
            if os.path.getsize(item) < 60000 and "Scripts\\pythonw.exe" in key.replace("/", "\\"):
                continue
        except OSError:
            pass
        return item
    return candidates[0] if candidates and os.path.isfile(candidates[0]) else None


def relaunch_without_console():
    pythonw = find_pythonw()
    if not pythonw:
        hide_console()
        return
    script = os.path.abspath(sys.argv[0])
    args = [pythonw, script, *sys.argv[1:]]
    DETACHED_PROCESS = 0x00000008
    CREATE_NO_WINDOW = 0x08000000
    CREATE_NEW_PROCESS_GROUP = 0x00000200
    import subprocess
    subprocess.Popen(
        args,
        cwd=os.path.dirname(script) or None,
        close_fds=True,
        creationflags=DETACHED_PROCESS | CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    os._exit(0)


def ensure_no_console():
    if os.name != "nt":
        return
    exe_name = os.path.basename(sys.executable).lower()
    if exe_name == "pythonw.exe":
        hide_console()
        return
    relaunch_without_console()


def already_running():
    ERROR_ALREADY_EXISTS = 183
    kernel32.CreateMutexW(None, True, "Local\WindowOpacityTool.SingleInstance")
    return ctypes.get_last_error() == ERROR_ALREADY_EXISTS


def main():
    if os.name != "nt":
        raise SystemExit("这个工具只能在 Windows 上使用。")
    ensure_no_console()
    if already_running():
        return
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except tk.TclError:
        pass
    OpacityTool(root)
    root.mainloop()


if __name__ == "__main__":
    main()
