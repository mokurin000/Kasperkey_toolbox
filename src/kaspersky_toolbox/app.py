"""Tkinter GUI for the Kaspersky Toolbox application."""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from kaspersky_toolbox.activation import KasperskyActivation, get_kaspersky_version
from kaspersky_toolbox.utils import (
    check_process_running,
    get_base_path_for_version,
    get_registry_value,
)

BUTTONS = [
    (
        "重置激活",
        "reset_activation",
        "重置卡巴斯基家庭版【暂时只支持21.14以前的版本】及企业版【KES】的试用激活",
    ),
    ("导出授权", "_export_license", "导出备份卡巴斯基的许可授权文件"),
    ("导入授权", "_import_license", "导入许可授权文件激活卡巴斯基软件"),
    ("安全模式", "_safe_mode_reboot", "快速重启计算机进安全模式"),
]
BUTTON_COLORS = ["#FFB6C1", "#98FB98", "#87CEFA", "#FFD700"]

NEW_BUTTONS = [
    (
        "关闭自保",
        "_disable_self_protection",
        "关闭卡巴斯基的自我保护功能，在特殊无法关闭情况下使用，需进安全模式下操作",
    ),
    ("版本更新", "_version_update", "禁止卡巴斯基家庭版软件版本自动更新."),
    ("获取补丁", "_get_patch", "提前获取卡巴斯基家庭版软件的最新补丁"),
    ("桌面保护", "_desktop_protection", "关闭卡巴斯基家庭版软件的桌面请求确认保护提示"),
]
NEW_BUTTON_COLORS = ["#FFA07A", "#7FFFD4", "#DDA0DD", "#FFFF00"]


class KasperskyToolboxApp:
    """Main application window for the Kaspersky Toolbox."""

    def __init__(self) -> None:
        self.version_key = get_kaspersky_version()

        # Activation controller (no tkinter dependency)
        self.activation = KasperskyActivation(
            self.version_key, status_cb=self._on_status
        )

        # ── Build UI ────────────────────────────────────────────────────
        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("卡巴斯基工具箱  by huawei_518")
        self._set_icon()
        self.root.resizable(False, False)

        # Center on screen
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width, window_height = 600, 380
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.configure(bg="#f0f0f0")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(4, weight=1)

        self._build_ui()

        # Exit if no Kaspersky detected
        if not self.version_key:
            self.status_label.config(text="未检测到卡巴斯基软件", fg="red")
            self.root.after(3000, self.exit_app)
        else:
            print("检测到卡巴斯基！")

        # Start periodic status polling
        self.root.after(1000, self._update_status)
        self.root.deiconify()

    # ── Window lifecycle ────────────────────────────────────────────────

    def run(self) -> None:
        self.root.mainloop()

    def exit_app(self) -> None:
        self.root.destroy()
        sys.exit(0)

    # ── Icon ────────────────────────────────────────────────────────────

    def _set_icon(self) -> None:
        if getattr(sys, "frozen", False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(base_path, "k.ico")
        try:
            self.root.iconbitmap(icon_path)
        except tk.TclError:
            pass

    # ── Status callback (used by activation) ────────────────────────────

    def _on_status(self, text: str, fg: str) -> None:
        self.status_label.config(text=text, fg=fg)

    # ── UI construction ─────────────────────────────────────────────────

    def _build_ui(self) -> None:
        style = ttk.Style()
        style.map(
            "TButton",
            foreground=[("disabled", "gray")],
            background=[("disabled", "#d9d9d9")],
        )

        # ── Title ───────────────────────────────────────────────────────
        title_frame = tk.Frame(self.root, bg="#87CEEB")
        title_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=10)
        title_label = tk.Label(
            title_frame,
            text="卡巴斯基工具箱",
            font=("Segoe UI", 20),
            bg="#87CEEB",
            fg="purple",
        )
        title_label.pack(pady=5)

        # ── Info frame ──────────────────────────────────────────────────
        info_frame = tk.Frame(self.root, bg="#f0f0f0")
        info_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=10)
        info_frame.columnconfigure(0, weight=1)
        info_frame.columnconfigure(1, weight=1)

        # Product name
        tk.Label(
            info_frame,
            text="产品名称：",
            font=("Segoe UI", 12),
            fg="darkblue",
            bg="#f0f0f0",
        ).grid(row=0, column=0, sticky="e", padx=5)
        self.product_name_value = tk.Label(
            info_frame,
            text="",
            font=("Segoe UI", 12),
            bg="#f0f0f0",
        )
        self.product_name_value.grid(row=0, column=1, sticky="w", padx=5)

        # Product version
        tk.Label(
            info_frame,
            text="产品版本：",
            font=("Segoe UI", 12),
            fg="darkblue",
            bg="#f0f0f0",
        ).grid(row=1, column=0, sticky="e", padx=5)
        self.product_version_value = tk.Label(
            info_frame,
            text="",
            font=("Segoe UI", 12),
            bg="#f0f0f0",
        )
        self.product_version_value.grid(row=1, column=1, sticky="w", padx=5)

        # Process status
        tk.Label(
            info_frame,
            text="产品进程：",
            font=("Segoe UI", 12),
            fg="darkblue",
            bg="#f0f0f0",
        ).grid(row=2, column=0, sticky="e", padx=5)
        self.process_value = tk.Label(
            info_frame,
            text="",
            font=("Segoe UI", 12),
            bg="#f0f0f0",
        )
        self.process_value.grid(row=2, column=1, sticky="w", padx=5)

        # Self-protection
        tk.Label(
            info_frame,
            text="自我保护：",
            font=("Segoe UI", 12),
            fg="darkblue",
            bg="#f0f0f0",
        ).grid(row=3, column=0, sticky="e", padx=5)
        self.self_protection_value = tk.Label(
            info_frame,
            text="",
            font=("Segoe UI", 12),
            bg="#f0f0f0",
        )
        self.self_protection_value.grid(row=3, column=1, sticky="w", padx=5)

        # Populate product info if version detected
        if self.version_key:
            base = get_base_path_for_version(self.version_key)
            product_name = get_registry_value(
                base, f"{self.version_key}\\environment", "ProductName"
            )
            self.product_name_value.config(
                text=product_name or "未检测到",
                fg="green" if product_name else "red",
            )
            product_version = get_registry_value(
                base, f"{self.version_key}\\environment", "Ins_ProductVersion"
            )
            self.product_version_value.config(
                text=product_version or "未检测到",
                fg="green" if product_version else "red",
            )
        else:
            self.product_name_value.config(text="未检测到", fg="red")
            self.product_version_value.config(text="未检测到", fg="red")
            self.self_protection_value.config(text="未检测到", fg="red")

        # ── Row 1 buttons ──────────────────────────────────────────────
        self.button_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.button_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=10)
        for i in range(4):
            self.button_frame.columnconfigure(i, weight=1)

        for idx, (text, cmd_name, tooltip) in enumerate(BUTTONS):
            style_name = f"btn_{idx}.TButton"
            style.configure(
                style_name,
                background=BUTTON_COLORS[idx],
                font=("Segoe UI", 12),
            )
            btn = ttk.Button(
                self.button_frame,
                text=text,
                style=style_name,
                command=getattr(self, cmd_name),
            )
            btn.grid(row=0, column=idx, padx=10, sticky="nsew")
            btn.bind("<Enter>", lambda _e, t=tooltip: self._on_status(t, "black"))
            btn.bind("<Leave>", lambda _e: self._on_status("就绪", "green"))

        # ── Row 2 buttons ──────────────────────────────────────────────
        self.new_button_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.new_button_frame.grid(
            row=3, column=0, columnspan=2, sticky="nsew", pady=10
        )
        for i in range(4):
            self.new_button_frame.columnconfigure(i, weight=1)

        for idx, (text, cmd_name, tooltip) in enumerate(NEW_BUTTONS):
            style_name = f"new_btn_{idx}.TButton"
            style.configure(
                style_name,
                background=NEW_BUTTON_COLORS[idx],
                font=("Segoe UI", 12),
            )
            btn = ttk.Button(
                self.new_button_frame,
                text=text,
                style=style_name,
                command=getattr(self, cmd_name),
            )
            btn.grid(row=0, column=idx, padx=10, sticky="nsew")
            btn.bind("<Enter>", lambda _e, t=tooltip: self._on_status(t, "black"))
            btn.bind("<Leave>", lambda _e: self._on_status("就绪", "green"))

        # ── Status bar ──────────────────────────────────────────────────
        status_frame = tk.Frame(self.root, bg="#f0f0f0", bd=1, relief=tk.SUNKEN)
        status_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        self.status_label = tk.Label(
            status_frame,
            text="就绪",
            font=("Segoe UI", 12),
            fg="green",
            bg="#f0f0f0",
            anchor="w",
        )
        self.status_label.pack(pady=(5, 5), padx=10, fill=tk.BOTH, expand=True)

    # ── Button state management ─────────────────────────────────────────

    def toggle_buttons_state(self, state: str) -> None:
        """Enable (``"normal"``) or disable (``"disabled"``) all buttons."""
        disabled = state != "normal"
        for child in self.button_frame.winfo_children():
            if isinstance(child, ttk.Button):
                child.state(["disabled" if disabled else "!disabled"])
        for child in self.new_button_frame.winfo_children():
            if isinstance(child, ttk.Button):
                child.state(["disabled" if disabled else "!disabled"])
        if disabled:
            self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        else:
            self.root.protocol("WM_DELETE_WINDOW", self.exit_app)

    # ── Status polling ──────────────────────────────────────────────────

    def _update_status(self) -> None:
        running = check_process_running("avpui.exe")
        self.process_value.config(
            text="运行中" if running else "已退出",
            fg="red" if running else "green",
        )

        if self.version_key:
            sp = self.activation.get_self_protection_status()
            if sp == 1:
                self.self_protection_value.config(text="已开启", fg="red")
            elif sp == 0:
                self.self_protection_value.config(text="已关闭", fg="green")
            else:
                self.self_protection_value.config(text="未检测到", fg="red")

        self.root.after(1000, self._update_status)

    # ── Activation wrapper methods ──────────────────────────────────────

    def reset_activation(self) -> None:
        if not messagebox.askyesno("确认", "是否重置试用，系统将重启生效"):
            return
        self.activation.reset_activation()

    def _export_license(self) -> None:
        if not self.activation.check_conditions():
            return
        self.toggle_buttons_state("disabled")
        self._on_status("正在导出许可授权...", "blue")
        self.root.update()
        self.root.after(3000, self._perform_export)

    def _perform_export(self) -> None:
        try:
            self.activation.export_license()
        except Exception as e:
            self._on_status(f"导出授权时出错: {e}", "red")
        finally:
            self.toggle_buttons_state("normal")

    def _import_license(self) -> None:
        if not self.activation.check_conditions():
            return
        self.toggle_buttons_state("disabled")
        file_path = filedialog.askopenfilename(filetypes=[("授权文件", "*.lic;*.dat")])
        if not file_path:
            self._on_status("未选择任何授权文件", "red")
            self.toggle_buttons_state("normal")
            return
        self._on_status("已选择授权文件，正在导入授权...", "blue")
        self.root.update()
        self.root.after(3000, lambda: self._perform_import(file_path))

    def _perform_import(self, file_path: str) -> None:
        try:
            self.activation.import_license(file_path)
        except Exception as e:
            self._on_status(f"导入授权时出错: {e}", "red")
        finally:
            self.toggle_buttons_state("normal")

    def _safe_mode_reboot(self) -> None:
        if not messagebox.askyesno("确认", "是否要重启电脑进入安全模式"):
            return
        ok = self.activation.safe_mode_reboot()
        if ok:
            self._on_status("正在重启进入安全模式...", "#4CAF50")
        else:
            self._on_status("安全模式启动失败", "#e53935")

    def _disable_self_protection(self) -> None:
        result = self.activation.disable_self_protection()
        # If disable_self_protection returned a status, update the label immediately
        if result is not None:
            status_text, color = result
            self.self_protection_value.config(text=status_text, fg=color)

    def _version_update(self) -> None:
        self.activation.version_update()

    def _get_patch(self) -> None:
        self.activation.get_patch()

    def _desktop_protection(self) -> None:
        self.activation.desktop_protection()
