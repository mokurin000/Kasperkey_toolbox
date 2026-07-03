import os
import sys
import glob
import ctypes
import subprocess
import winreg
import tkinter as tk
from ctypes import wintypes
from tkinter import ttk, messagebox, filedialog

import psutil

mutex_name = "Global\\KasperskyToolboxMutex"
mutex = ctypes.windll.kernel32.CreateMutexA(None, 1, mutex_name.encode())
if ctypes.windll.kernel32.GetLastError() == 183:
    sys.exit(0)


kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

kernel32.GetCurrentProcess.argtypes = ()
kernel32.GetCurrentProcess.restype = wintypes.HANDLE

kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
kernel32.CloseHandle.restype = wintypes.BOOL

advapi32.OpenProcessToken.argtypes = (
    wintypes.HANDLE,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.HANDLE),
)
advapi32.OpenProcessToken.restype = wintypes.BOOL

advapi32.GetTokenInformation.argtypes = (
    wintypes.HANDLE,
    ctypes.c_uint,
    wintypes.LPVOID,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
)
advapi32.GetTokenInformation.restype = wintypes.BOOL


def is_admin():
    """检查当前进程是否以管理员权限（已提权）运行"""
    try:
        TOKEN_QUERY = 0x0008
        TokenElevation = 20

        handle: wintypes.HANDLE = kernel32.GetCurrentProcess()
        token = ctypes.c_void_p()
        if not advapi32.OpenProcessToken(handle, TOKEN_QUERY, ctypes.byref(token)):
            return False

        # TOKEN_ELEVATION.TokenIsElevated
        token_information = ctypes.c_uint32(0)
        needed = ctypes.c_uint32(0)

        result = advapi32.GetTokenInformation(
            token,
            TokenElevation,
            ctypes.byref(token_information),
            ctypes.sizeof(token_information),
            ctypes.byref(needed),
        )
        kernel32.CloseHandle(token)
        return result != 0 and token_information.value != 0
    except Exception:
        return False


def run_as_admin():
    """以管理员权限重新启动程序"""
    script = sys.argv[0]
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, f'"{script}"', None, 1
    )
    sys.exit(0)


def get_kaspersky_version():
    """从注册表检测卡巴斯基版本 (对应 act.vbs 的 LiRu 函数)"""
    search_paths = [
        (r"SOFTWARE\WOW6432Node\KasperskyLab", "\\protected"),
        (r"SOFTWARE\KasperskyLab", "\\protected"),
        (r"SOFTWARE\WOW6432Node\KasperskyLab", ""),
        (r"SOFTWARE\KasperskyLab", ""),
    ]
    for base_path, suffix in search_paths:
        full_path = base_path + suffix
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE, full_path, 0, winreg.KEY_READ
            )
            for i in range(100):
                try:
                    subkey = winreg.EnumKey(key, i)
                    if subkey == "KES":  # ignore empty entry
                        continue
                    env_path = f"{full_path}\\{subkey}\\environment"
                    try:
                        env_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, env_path)
                        try:
                            (product_root, _) = winreg.QueryValueEx(
                                env_key, "ProductRoot"
                            )
                            if product_root and os.path.exists(
                                os.path.join(product_root, "avp.exe")
                            ):
                                return subkey
                        finally:
                            winreg.CloseKey(env_key)
                    except FileNotFoundError:
                        pass
                except OSError:
                    break
            winreg.CloseKey(key)
        except FileNotFoundError:
            continue
    return None


version_key = get_kaspersky_version()


def get_registry_value(base_path, subkey_path, value_name):
    """从注册表读取指定值 (对应 act.vbs 的 Wsh.RegRead 调用)"""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, f"{base_path}\\{subkey_path}", 0, winreg.KEY_READ
        )
        try:
            (value, _) = winreg.QueryValueEx(key, value_name)
            return value
        finally:
            winreg.CloseKey(key)
    except FileNotFoundError:
        print(f"打开注册表 {base_path}\\{subkey_path} 失败")
        return None


def delete_files(path_pattern):
    for path in glob.glob(path_pattern):
        if os.path.isfile(path):
            try:
                os.remove(path)
            except Exception as e:
                print(f"删除文件 {path} 时出错: {e}")


def reset_activation():
    if not check_conditions():
        return

    result = messagebox.askyesno("确认", "是否重置试用，系统将重启生效")
    if not result:
        return

    version_key = get_kaspersky_version()
    if not version_key:
        status_label.config(
            text="未检测到卡巴斯基软件，无法重置激活",
            fg="red",
        )
        return

    if version_key.startswith("AVP"):
        base_path = r"SOFTWARE\WOW6432Node\KasperskyLab"
        software = r"SOFTWARE\WOW6432Node"
        avp = version_key

        delete_files(
            os.path.join(
                os.environ["ProgramData"],
                f"Kaspersky Lab\\{avp}\\Data\\*.bin",
            )
        )

        delete_files(
            os.path.join(
                os.environ["ProgramData"],
                f"Kaspersky Lab\\{avp}\\Data\\cat_engine*",
            )
        )

        delete_files(
            os.path.join(
                os.environ["ProgramData"],
                f"Kaspersky Lab\\{avp}\\Data\\certdb_v2.*.idx",
            )
        )

        commands = [
            f"reg delete HKLM\\{software}\\KasperskyLab\\{avp}\\Data\\LicCache /f",
            f"reg delete HKLM\\{software}\\KasperskyLab\\{avp}\\Data\\LicensingActivationErrorStorageLogic /f",
            f"reg delete HKLM\\{software}\\KasperskyLab\\LicStrg /f",
            f"reg delete HKLM\\{software}\\KasperskyLab\\{avp}\\Data\\UPAO /f",
            r"reg delete HKLM\SOFTWARE\Microsoft\SystemCertificates\SPC /f",
            f"reg add HKLM\\{software}\\KasperskyLab\\{avp}\\settings /v Ins_InitMode /t REG_DWORD /d 1 /f",
            f"reg add HKLM\\{software}\\KasperskyLab\\{avp}\\Data\\UPAO /v UpaoState /t REG_DWORD /d 1 /f",
            f"reg add HKLM\\{software}\\KasperskyLab\\{avp}\\environment /v UpaoState /t REG_SZ /d 1 /f",
            f"reg add HKLM\\{software}\\KasperskyLab\\LicStrg /f",
            "shutdown /r /t 2",
        ]

    elif version_key.startswith("KES"):
        base_path = r"SOFTWARE\WOW6432Node\KasperskyLab\protected"
        software = r"SOFTWARE\WOW6432Node"
        kes = version_key

        self_protection_value = get_registry_value(
            base_path,
            f"{kes}\\settings",
            "EnableSelfProtection",
        )

        if self_protection_value is None:
            self_protection_value = 0

        report_folder = os.path.join(
            os.environ["ProgramData"],
            f"Kaspersky Lab\\{kes}\\Report",
        )

        data_kvdb_path = os.path.join(
            os.environ["ProgramData"],
            f"Kaspersky Lab\\{kes}\\Data\\data.kvdb",
        )

        try:
            takeown_command = f'takeown /F "{report_folder}" /R /D Y'

            rd_command = f'RD /S /Q "{report_folder}"'

            subprocess.run(
                takeown_command,
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            subprocess.run(
                rd_command,
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

        except subprocess.CalledProcessError as e:
            status_label.config(
                text=f"删除报告文件夹时出错: {e}",
                fg="red",
            )
            return

        delete_files(data_kvdb_path)

        commands = [
            r"reg delete HKLM\SOFTWARE\Microsoft\SystemCertificates\SPC /f",
            f"reg delete HKLM\\{software}\\KasperskyLab\\protected\\{kes}\\watchdog\\LicenseInfo /f",
            f"reg delete HKLM\\{software}\\KasperskyLab\\protected\\{kes}\\watchdog\\Ticket /f",
            f"reg delete HKLM\\{software}\\KasperskyLab\\protected\\LicStorage /f",
            f"reg add HKLM\\{software}\\KasperskyLab\\protected\\{kes}\\Data /v Install /t REG_DWORD /d 1 /f",
            f"reg add HKLM\\{software}\\KasperskyLab\\protected\\{kes}\\settings /v EnableSelfProtection /t REG_DWORD /d {self_protection_value} /f",
            "shutdown /r /t 2",
        ]

    for command in commands:
        try:
            subprocess.run(
                command,
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as e:
            status_label.config(
                text=f"重置激活失败：{e}",
                fg="red",
            )
            return

    status_label.config(
        text="重置激活成功，即将重启电脑生效",
        fg="green",
    )


def check_process_running(process_name: str):
    """检查进程是否运行"""

    return any(
        proc.info["name"] == process_name for proc in psutil.process_iter(["name"])
    )


def exit_app():
    """退出程序"""
    root.destroy()
    sys.exit()


def check_conditions():
    process_running = check_process_running("avpui.exe")

    if version_key:
        if version_key.startswith("AVP"):
            base_path = "SOFTWARE\\WOW6432Node\\KasperskyLab"
        elif version_key.startswith("KES"):
            base_path = "SOFTWARE\\WOW6432Node\\KasperskyLab\\protected"
        else:
            base_path = "SOFTWARE\\WOW6432Node\\KasperskyLab"
        self_protection = get_registry_value(
            base_path, f"{version_key}\\settings", "EnableSelfProtection"
        )
        self_protection_status = self_protection == 1
    else:
        self_protection_status = False
    if process_running or self_protection_status:
        status_label.config(text="请先关闭卡巴的自我保护并退出软件再操作", fg="red")
        return False
    return True


def get_patch():
    if check_conditions():
        status_label.config(text="正在检查获取补丁设置...", fg="blue")

        if version_key and version_key.startswith("AVP"):
            base_path = "SOFTWARE\\WOW6432Node\\KasperskyLab"
            subkey_path = f"{version_key}\\environment"
            value_name = "UpdateTarget"
            update_target = get_registry_value(base_path, subkey_path, value_name)
            if update_target is not None:
                if update_target == 200:
                    status_label.config(text="已开启提前获取补丁，无需操作", fg="red")
                else:
                    try:
                        key = winreg.OpenKey(
                            winreg.HKEY_LOCAL_MACHINE,
                            base_path + "\\" + subkey_path,
                            0,
                            winreg.KEY_SET_VALUE,
                        )
                        winreg.SetValueEx(key, value_name, 0, winreg.REG_DWORD, 200)
                        winreg.CloseKey(key)
                        status_label.config(
                            text="操作成功，已开启提前获取补丁", fg="green"
                        )
                    except Exception:
                        status_label.config(
                            text="请先关闭卡巴的自我保护并退出软件再操作", fg="red"
                        )

            else:
                status_label.config(text="未检测到卡巴斯基家庭版软件", fg="red")
        else:
            status_label.config(text="未检测到卡巴斯基家庭版软件", fg="red")


def desktop_protection():

    if version_key.startswith("KES"):
        status_label.config(text="未检测到卡巴斯基家庭版软件", fg="red")
        return
    base_path = "SOFTWARE\\WOW6432Node\\KasperskyLab"
    try:
        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE,
            f"{base_path}\\{version_key}\\environment",
            0,
            winreg.KEY_ALL_ACCESS,
        )
        try:
            (value, _) = winreg.QueryValueEx(key, "SecuredDesktopDisabled")
            if value == "1":
                status_label.config(
                    text="已关闭桌面请求确认保护提示，无需操作", fg="red"
                )
            else:
                winreg.SetValueEx(key, "SecuredDesktopDisabled", 0, winreg.REG_SZ, "1")
                status_label.config(
                    text="操作成功，已关闭桌面请求确认保护提示", fg="green"
                )
        except FileNotFoundError:
            winreg.SetValueEx(key, "SecuredDesktopDisabled", 0, winreg.REG_SZ, "1")
            status_label.config(text="操作成功，已关闭桌面请求确认保护提示", fg="green")
        else:
            winreg.CloseKey(key)
    except Exception:
        status_label.config(text="请先关闭卡巴的自我保护并退出软件再操作", fg="red")


def get_vbs_path():
    if getattr(sys, "frozen", False):
        base_dir = (
            sys._MEIPASS
            if hasattr(sys, "_MEIPASS")
            else os.path.dirname(sys.executable)
        )
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "Act.vbs")


def export_license():
    if check_conditions():
        toggle_buttons_state("disabled")
        status_label.config(text="正在导出许可授权...", fg="blue")
        root.update()
        root.after(3000, perform_export)


def perform_export():
    try:
        try:
            vbs_path = get_vbs_path()
            if os.path.exists(vbs_path):
                subprocess.Popen(["wscript", vbs_path])
                status_label.config(text="授权导出成功，已保存在桌面", fg="green")
            else:
                status_label.config(text="未找到调试文件", fg="red")
        except Exception as e:
            try:
                status_label.config(text=f"导出授权时出错: {str(e)}", fg="red")
            finally:
                e = None
                del e

    finally:
        toggle_buttons_state("normal")


def import_license():
    if check_conditions():
        toggle_buttons_state("disabled")
        file_path = filedialog.askopenfilename(filetypes=[("授权文件", "*.lic;*.dat")])
        if not file_path:
            status_label.config(text="未选择任何授权文件", fg="red")
            toggle_buttons_state("normal")
            return
        status_label.config(text="已选择授权文件，正在导入授权...", fg="blue")
        root.update()
        root.after(3000, lambda: perform_import(file_path))


def perform_import(file_path):
    try:
        try:
            vbs_path = get_vbs_path()
            if os.path.exists(vbs_path):
                subprocess.Popen(f'wscript "{vbs_path}" "{file_path}"')
                status_label.config(text="授权导入成功，即将自动重启软件", fg="green")
            else:
                status_label.config(text="未找到调试文件", fg="red")
        except Exception as e:
            try:
                status_label.config(text=f"导入授权时出错: {str(e)}", fg="red")
            finally:
                e = None
                del e

    finally:
        toggle_buttons_state("normal")


def toggle_buttons_state(state):
    for child in button_frame.winfo_children():
        if isinstance(child, ttk.Button):
            child.state(["!disabled" if state == "normal" else "disabled"])

    for child in new_button_frame.winfo_children():
        if isinstance(child, ttk.Button):
            child.state(["!disabled" if state == "normal" else "disabled"])
        root.protocol(
            "WM_DELETE_WINDOW", lambda: None if state == "disabled" else exit_app()
        )


def disable_self_protection():

    if not version_key:
        status_label.config(text="未检测到卡巴斯基软件，无法关闭自我保护", fg="red")
        return
    if version_key.startswith("AVP"):
        base_path = "SOFTWARE\\WOW6432Node\\KasperskyLab"
    elif version_key.startswith("KES"):
        base_path = "SOFTWARE\\WOW6432Node\\KasperskyLab\\protected"
    else:
        base_path = "SOFTWARE\\WOW6432Node\\KasperskyLab"
    self_protection = get_registry_value(
        base_path, f"{version_key}\\settings", "EnableSelfProtection"
    )
    if self_protection == 0:
        status_label.config(text="已关闭软件的自我保护功能，无需操作", fg="red")
    elif self_protection == 1:
        try:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                f"{base_path}\\{version_key}\\settings",
                0,
                winreg.KEY_SET_VALUE,
            )
            winreg.SetValueEx(key, "EnableSelfProtection", 0, winreg.REG_DWORD, 0)
            winreg.CloseKey(key)
            status_label.config(text="操作成功，自我保护功能已关闭", fg="green")
            self_protection_status = "已关闭"
            self_protection_color = "green"
            self_protection_value.config(
                text=self_protection_status, fg=self_protection_color
            )
        except Exception:
            status_label.config(text="关闭自我保护失败，请进安全模式下操作", fg="red")

    else:
        status_label.config(text="无法获取自我保护状态，操作失败", fg="red")


def safe_mode_reboot():
    try:
        if messagebox.askyesno("确认", "是否要重启电脑进入安全模式"):
            subprocess.run(
                ["bcdedit", "/set", "{current}", "safeboot", "network"], check=True
            )
            subprocess.run(
                [
                    "reg",
                    "add",
                    "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\RunOnce",
                    "/v",
                    "*UndoSB",
                    "/t",
                    "REG_SZ",
                    "/d",
                    "bcdedit /deletevalue {current} safeboot",
                    "/f",
                ],
                check=True,
            )
            subprocess.run(
                ["shutdown", "-r", "-t", "3", "-c", "电脑将在3秒后重启进入安全模式"],
                check=True,
            )
            status_label.config(text="正在重启进入安全模式...", fg="#4CAF50")
    except subprocess.CalledProcessError as e:
        status_label.config(text=f"安全模式启动失败：{str(e)}", fg="#e53935")


def version_update():

    if version_key and version_key.startswith("AVP"):
        base_path = "SOFTWARE\\WOW6432Node\\KasperskyLab"
        subkey_path = f"{version_key}\\environment"
        value_name = "IsVersionUpdateEnabled"
        is_update_enabled = get_registry_value(base_path, subkey_path, value_name)
        if is_update_enabled is not None:
            if is_update_enabled == 0:
                status_label.config(text="已关闭版本更新，无需操作", fg="red")
            else:
                try:
                    key = winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE,
                        base_path + "\\" + subkey_path,
                        0,
                        winreg.KEY_SET_VALUE,
                    )
                    winreg.SetValueEx(key, value_name, 0, winreg.REG_DWORD, 0)
                    winreg.CloseKey(key)
                    status_label.config(text="操作成功，版本自动更新已关闭", fg="green")
                except Exception:
                    try:
                        status_label.config(
                            text="请先关闭卡巴的自我保护并退出软件再操作", fg="red"
                        )
                    finally:
                        e = None
                        del e

        else:
            try:
                key = winreg.OpenKey(
                    winreg.HKEY_LOCAL_MACHINE,
                    base_path + "\\" + subkey_path,
                    0,
                    winreg.KEY_SET_VALUE,
                )
                winreg.SetValueEx(key, value_name, 0, winreg.REG_DWORD, 0)
                winreg.CloseKey(key)
                status_label.config(text="操作成功，版本自动更新已关闭", fg="green")
            except Exception:
                try:
                    status_label.config(
                        text="请先关闭卡巴的自我保护并退出软件再操作", fg="red"
                    )
                finally:
                    e = None
                    del e

    else:
        status_label.config(text="未检测到卡巴斯基家庭版软件", fg="red")


def update_status():
    process_running = check_process_running("avpui.exe")

    process_status = "运行中" if process_running else "已退出"
    process_color = "red" if process_running else "green"
    process_value.config(text=process_status, fg=process_color)
    if version_key:
        if version_key.startswith("AVP"):
            base_path = "SOFTWARE\\WOW6432Node\\KasperskyLab"
        elif version_key.startswith("KES"):
            base_path = "SOFTWARE\\WOW6432Node\\KasperskyLab\\protected"
        else:
            base_path = "SOFTWARE\\WOW6432Node\\KasperskyLab"
        self_protection = get_registry_value(
            base_path, f"{version_key}\\settings", "EnableSelfProtection"
        )
        self_protection_status = (
            "已开启"
            if self_protection == 1
            else "已关闭"
            if self_protection == 0
            else "未检测到"
        )
        self_protection_color = (
            "red"
            if self_protection == 1
            else "red"
            if self_protection is None
            else "green"
        )
        self_protection_value.config(
            text=self_protection_status, fg=self_protection_color
        )
    root.after(1000, update_status)


if __name__ == "__main__":
    if not is_admin():
        run_as_admin()

    root = tk.Tk()
    root.withdraw()
    root.title("卡巴斯基工具箱  by huawei_518")
    if getattr(sys, "frozen", False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_path, "k.ico")
    try:
        root.iconbitmap(icon_path)
    except tk.TclError:
        print("未能找到图标文件。")
    else:
        style = ttk.Style()
        style.map(
            "TButton",
            foreground=[("disabled", "gray")],
            background=[("disabled", "#d9d9d9")],
        )
        root.resizable(False, False)
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        (window_width, window_height) = (600, 380)
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        root.configure(bg="#f0f0f0")
        root.columnconfigure(0, weight=1)
        root.rowconfigure(4, weight=1)
        title_frame = tk.Frame(root, bg="#87CEEB")
        title_frame.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=10)
        title_label = tk.Label(
            title_frame,
            text="卡巴斯基工具箱",
            font=("Segoe UI", 20),
            bg="#87CEEB",
            fg="purple",
        )
        title_label.pack(pady=5, anchor=(tk.CENTER))
        info_frame = tk.Frame(root, bg="#f0f0f0")
        info_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=10)
        info_frame.columnconfigure(0, weight=1)
        info_frame.columnconfigure(1, weight=1)

        product_name_prefix = tk.Label(
            info_frame,
            text="产品名称：",
            font=("Segoe UI", 12),
            fg="darkblue",
            bg="#f0f0f0",
        )
        product_name_prefix.grid(row=0, column=0, sticky="e", padx=5)
        product_name_value = tk.Label(
            info_frame, text="", font=("Segoe UI", 12), bg="#f0f0f0"
        )
        product_name_value.grid(row=0, column=1, sticky="w", padx=5)
        product_version_prefix = tk.Label(
            info_frame,
            text="产品版本：",
            font=("Segoe UI", 12),
            fg="darkblue",
            bg="#f0f0f0",
        )
        product_version_prefix.grid(row=1, column=0, sticky="e", padx=5)
        product_version_value = tk.Label(
            info_frame, text="", font=("Segoe UI", 12), bg="#f0f0f0"
        )
        product_version_value.grid(row=1, column=1, sticky="w", padx=5)
        self_protection_prefix = tk.Label(
            info_frame,
            text="自我保护：",
            font=("Segoe UI", 12),
            fg="darkblue",
            bg="#f0f0f0",
        )
        self_protection_prefix.grid(row=3, column=0, sticky="e", padx=5)
        self_protection_value = tk.Label(
            info_frame, text="", font=("Segoe UI", 12), bg="#f0f0f0"
        )
        self_protection_value.grid(row=3, column=1, sticky="w", padx=5)
        if not version_key:
            status_text = "未检测到卡巴斯基软件"
            product_name_value.config(text="未检测到", fg="red")
            product_version_value.config(text="未检测到", fg="red")
            self_protection_value.config(text="未检测到", fg="red")
            root.after(3000, exit_app)
        else:
            print("检测到卡巴斯基！")
            if version_key.startswith("AVP"):
                base_path = "SOFTWARE\\WOW6432Node\\KasperskyLab"
            elif version_key.startswith("KES"):
                base_path = "SOFTWARE\\WOW6432Node\\KasperskyLab\\protected"
            else:
                base_path = "SOFTWARE\\WOW6432Node\\KasperskyLab"
            product_name = get_registry_value(
                base_path, f"{version_key}\\environment", "ProductName"
            )
            product_name_value.config(
                text=(product_name or "未检测到"),
                fg=("green" if product_name else "red"),
            )
            product_version = get_registry_value(
                base_path, f"{version_key}\\environment", "Ins_ProductVersion"
            )
            product_version_value.config(
                text=(product_version or "未检测到"),
                fg=("green" if product_version else "red"),
            )
        process_prefix = tk.Label(
            info_frame,
            text="产品进程：",
            font=("Segoe UI", 12),
            fg="darkblue",
            bg="#f0f0f0",
        )
        process_prefix.grid(row=2, column=0, sticky="e", padx=5)
        process_running = check_process_running("avpui.exe")
        process_status = "运行中" if process_running else "已退出"
        process_color = "red" if process_running else "green"
        process_value = tk.Label(
            info_frame,
            text=process_status,
            font=("Segoe UI", 12),
            fg=process_color,
            bg="#f0f0f0",
        )
        process_value.grid(row=2, column=1, sticky="w", padx=5)
        if version_key:
            if version_key.startswith("AVP"):
                base_path = "SOFTWARE\\WOW6432Node\\KasperskyLab"
            elif version_key.startswith("KES"):
                base_path = "SOFTWARE\\WOW6432Node\\KasperskyLab\\protected"
            else:
                base_path = "SOFTWARE\\WOW6432Node\\KasperskyLab"
            self_protection = get_registry_value(
                base_path, f"{version_key}\\settings", "EnableSelfProtection"
            )
            self_protection_status = (
                "已开启"
                if self_protection == 1
                else "已关闭"
                if self_protection == 0
                else "未检测到"
            )
            self_protection_color = (
                "red"
                if self_protection == 1
                else "red"
                if self_protection is None
                else "green"
            )
            self_protection_value.config(
                text=self_protection_status, fg=self_protection_color
            )
        button_frame = tk.Frame(root, bg="#f0f0f0")
        button_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=10)
        for i in range(4):
            button_frame.columnconfigure(i, weight=1)

        buttons = ["重置激活", "导出授权", "导入授权", "安全模式"]
        button_colors = ["#FFB6C1", "#98FB98", "#87CEFA", "#FFD700"]

        def show_function_info(event, info):
            status_label.config(text=info)

        def hide_function_info(event):
            status_label.config(text="就绪")

        function_info = [
            "重置卡巴斯基家庭版【暂时只支持21.14以前的版本】及企业版【KES】的试用激活",
            "导出备份卡巴斯基的许可授权文件",
            "导入许可授权文件激活卡巴斯基软件",
            "快速重启计算机进安全模式",
        ]
        for i, btn_text in enumerate(buttons):
            if btn_text == "重置激活":
                btn = ttk.Button(
                    button_frame,
                    text=btn_text,
                    style=f"{i}.TButton",
                    command=reset_activation,
                )
            elif btn_text == "导出授权":
                btn = ttk.Button(
                    button_frame,
                    text=btn_text,
                    style=f"{i}.TButton",
                    command=export_license,
                )
            elif btn_text == "导入授权":
                btn = ttk.Button(
                    button_frame,
                    text=btn_text,
                    style=f"{i}.TButton",
                    command=import_license,
                )
            elif btn_text == "安全模式":
                btn = ttk.Button(
                    button_frame,
                    text=btn_text,
                    style=f"{i}.TButton",
                    command=safe_mode_reboot,
                )
            style = ttk.Style()
            style.configure(
                f"{i}.TButton", background=(button_colors[i]), font=("Segoe UI", 12)
            )
            btn.grid(row=0, column=i, padx=10, sticky="nsew")
            btn.bind(
                "<Enter>", lambda e, info=function_info[i]: show_function_info(e, info)
            )
            btn.bind("<Leave>", hide_function_info)

        new_buttons = ["关闭自保", "版本更新", "获取补丁", "桌面保护"]
        new_button_colors = ["#FFA07A", "#7FFFD4", "#DDA0DD", "#FFFF00"]
        new_function_info = [
            "关闭卡巴斯基的自我保护功能，在特殊无法关闭情况下使用，需进安全模式下操作",
            "禁止卡巴斯基家庭版软件版本自动更新.",
            "提前获取卡巴斯基家庭版软件的最新补丁",
            "关闭卡巴斯基家庭版软件的桌面请求确认保护提示",
        ]
        new_button_frame = tk.Frame(root, bg="#f0f0f0")
        new_button_frame.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=10)
        for i in range(4):
            new_button_frame.columnconfigure(i, weight=1)

        for i, btn_text in enumerate(new_buttons):
            if btn_text == "版本更新":
                btn = ttk.Button(
                    new_button_frame,
                    text=btn_text,
                    style=f"new_{i}.TButton",
                    command=version_update,
                )
            elif btn_text == "获取补丁":
                btn = ttk.Button(
                    new_button_frame,
                    text=btn_text,
                    style=f"new_{i}.TButton",
                    command=get_patch,
                )
            elif btn_text == "桌面保护":
                btn = ttk.Button(
                    new_button_frame,
                    text=btn_text,
                    style=f"new_{i}.TButton",
                    command=desktop_protection,
                )
            elif btn_text == "关闭自保":
                btn = ttk.Button(
                    new_button_frame,
                    text=btn_text,
                    style=f"new_{i}.TButton",
                    command=disable_self_protection,
                )
            else:
                btn = ttk.Button(
                    new_button_frame, text=btn_text, style=f"new_{i}.TButton"
                )
            style = ttk.Style()
            style.configure(
                f"new_{i}.TButton",
                background=(new_button_colors[i]),
                font=("Segoe UI", 12),
            )
            btn.grid(row=0, column=i, padx=10, sticky="nsew")
            btn.bind(
                "<Enter>",
                lambda e, info=new_function_info[i]: show_function_info(e, info),
            )
            btn.bind("<Leave>", hide_function_info)

        status_frame = tk.Frame(root, bg="#f0f0f0", bd=1, relief=(tk.SUNKEN))
        status_frame.grid(row=4, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        status_label = tk.Label(
            status_frame,
            text="就绪",
            font=("Segoe UI", 12),
            fg="green",
            bg="#f0f0f0",
            anchor="w",
        )
        status_label.pack(pady=(5, 5), padx=10, fill=(tk.BOTH), expand=True)
        if not version_key:
            status_label.config(text=status_text, fg="red")
        root.after(1000, update_status)
        root.deiconify()
        root.mainloop()
