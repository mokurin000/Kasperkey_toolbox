"""Kaspersky activation business logic — registry operations, file cleanup, shell commands."""

import os
import subprocess
import winreg
from collections.abc import Callable

from kaspersky_toolbox.utils import (
    AVP_BASE,
    SOFTWARE_WOW,
    check_process_running,
    delete_files,
    get_base_path_for_version,
    get_registry_value,
    set_registry_value,
)


# ── Installation detection ──────────────────────────────────────────────────


def get_kaspersky_version() -> str | None:
    """Detect the installed Kaspersky product version from the registry.

    Searches four registry locations in priority order (KES 32-bit,
    KES 64-bit, AVP 32-bit, AVP 64-bit). Returns the version subkey name
    (e.g. ``"AVP21.3"``, ``"KES.0"``) or ``None``.
    """
    possible_paths = [
        r"SOFTWARE\WOW6432Node\KasperskyLab",
        r"SOFTWARE\WOW6432Node\KasperskyLab\protected",
    ]

    for path in possible_paths:
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path)

            for i in range(100):
                try:
                    subkey = winreg.EnumKey(key, i)

                    # AVP* or KES.xx
                    if (
                        subkey.startswith("KES")
                        and len(subkey.split(".")) > 1
                        or subkey.startswith("AVP")
                    ):
                        return subkey

                except OSError:
                    break

        except OSError:
            pass

    return None


# ── Status callback shorthand ───────────────────────────────────────────────

StatusCallback = Callable[[str, str], None] | None


# ── Activation controller ───────────────────────────────────────────────────


class KasperskyActivation:
    """High-level Kaspersky activation and configuration operations.

    All methods accept an optional *status_cb* to report user-facing messages.
    The class does **not** import or depend on ``tkinter``.
    """

    def __init__(
        self,
        version_key: str | None,
        status_cb: StatusCallback = None,
    ) -> None:
        self.version_key = version_key
        self.status_cb = status_cb

    # ── helpers ─────────────────────────────────────────────────────────

    def _msg(self, text: str, fg: str = "black") -> None:
        if self.status_cb is not None:
            self.status_cb(text, fg)

    def _get_base_path(self) -> str:
        """Registry base path for the detected product (AVP or KES)."""
        if self.version_key is None:
            return AVP_BASE
        return get_base_path_for_version(self.version_key)

    # ── conditions ───────────────────────────────────────────────────────

    def get_self_protection_status(self) -> int | None:
        """Read ``EnableSelfProtection`` from the registry.

        Returns ``1`` (enabled), ``0`` (disabled), or ``None`` (unknown).
        """
        if not self.version_key:
            return None
        base = self._get_base_path()
        return get_registry_value(base, f"{self.version_key}\\settings", "EnableSelfProtection")  # fmt: skip

    def check_conditions(self) -> bool:
        """Verify that Kaspersky is not running and self-protection is off.

        Sets ``status_cb`` with a warning if conditions are not met.
        Returns ``True`` when safe to proceed.
        """
        process_running = check_process_running("avpui.exe")
        self_protection = self.get_self_protection_status()

        if process_running or self_protection == 1:
            self._msg("请先关闭卡巴的自我保护并退出软件再操作", "red")
            return False
        return True

    # ── reset activation ─────────────────────────────────────────────────

    def reset_activation(self) -> None:
        """Reset the Kaspersky trial activation period.

        Handles both AVP (consumer) and KES (enterprise) products.
        A system reboot is required for changes to take effect.

        Re-detects the Kaspersky version from the registry each call
        to reflect any runtime changes in the installation state.
        """
        if not self.check_conditions():
            return

        version_key = get_kaspersky_version()
        if not version_key:
            self._msg("未检测到卡巴斯基软件，无法重置激活", "red")
            return

        try:
            if version_key.startswith("AVP"):
                self._reset_avp(version_key)
            elif version_key.startswith("KES"):
                self._reset_kes(version_key)
            else:
                self._msg("未知的卡巴斯基产品类型", "red")
                return
        except subprocess.CalledProcessError as e:
            self._msg(f"重置激活失败：{e}", "red")
            return

        self._msg("重置激活成功，即将重启电脑生效", "green")

    def _reset_avp(self, avp: str) -> None:
        program_data = os.environ["ProgramData"]

        # Delete data files
        delete_files(os.path.join(program_data, f"Kaspersky Lab\\{avp}\\Data\\*.bin"))
        delete_files(
            os.path.join(program_data, f"Kaspersky Lab\\{avp}\\Data\\cat_engine*")
        )
        delete_files(
            os.path.join(program_data, f"Kaspersky Lab\\{avp}\\Data\\certdb_v2.*.idx")
        )

        # Build and run commands
        cmds = [
            f"reg delete HKLM\\{SOFTWARE_WOW}\\KasperskyLab\\{avp}\\Data\\LicCache /f",
            f"reg delete HKLM\\{SOFTWARE_WOW}\\KasperskyLab\\{avp}\\Data\\LicensingActivationErrorStorageLogic /f",
            f"reg delete HKLM\\{SOFTWARE_WOW}\\KasperskyLab\\LicStrg /f",
            f"reg delete HKLM\\{SOFTWARE_WOW}\\KasperskyLab\\{avp}\\Data\\UPAO /f",
            r"reg delete HKLM\SOFTWARE\Microsoft\SystemCertificates\SPC /f",
            f"reg add HKLM\\{SOFTWARE_WOW}\\KasperskyLab\\{avp}\\settings /v Ins_InitMode /t REG_DWORD /d 1 /f",
            f"reg add HKLM\\{SOFTWARE_WOW}\\KasperskyLab\\{avp}\\Data\\UPAO /v UpaoState /t REG_DWORD /d 1 /f",
            f"reg add HKLM\\{SOFTWARE_WOW}\\KasperskyLab\\{avp}\\environment /v UpaoState /t REG_SZ /d 1 /f",
            f"reg add HKLM\\{SOFTWARE_WOW}\\KasperskyLab\\LicStrg /f",
            "shutdown /r /t 2",
        ]
        self._run_commands(cmds)

    def _reset_kes(self, kes: str) -> None:
        program_data = os.environ["ProgramData"]
        report_folder = os.path.join(program_data, f"Kaspersky Lab\\{kes}\\Report")
        data_kvdb = os.path.join(program_data, f"Kaspersky Lab\\{kes}\\Data\\data.kvdb")

        # Save self-protection value to restore later
        saved_sp = self.get_self_protection_status()
        if saved_sp is None:
            saved_sp = 0

        # Take ownership and delete report folder
        try:
            subprocess.run(
                f'takeown /F "{report_folder}" /R /D Y',
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(
                f'RD /S /Q "{report_folder}"',
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except subprocess.CalledProcessError as e:
            self._msg(f"删除报告文件夹时出错: {e}", "red")
            raise

        delete_files(data_kvdb)

        cmds = [
            r"reg delete HKLM\SOFTWARE\Microsoft\SystemCertificates\SPC /f",
            f"reg delete HKLM\\{SOFTWARE_WOW}\\KasperskyLab\\protected\\{kes}\\watchdog\\LicenseInfo /f",
            f"reg delete HKLM\\{SOFTWARE_WOW}\\KasperskyLab\\protected\\{kes}\\watchdog\\Ticket /f",
            f"reg delete HKLM\\{SOFTWARE_WOW}\\KasperskyLab\\protected\\LicStorage /f",
            f"reg add HKLM\\{SOFTWARE_WOW}\\KasperskyLab\\protected\\{kes}\\Data /v Install /t REG_DWORD /d 1 /f",
            f"reg add HKLM\\{SOFTWARE_WOW}\\KasperskyLab\\protected\\{kes}\\settings /v EnableSelfProtection /t REG_DWORD /d {saved_sp} /f",
            "shutdown /r /t 2",
        ]
        self._run_commands(cmds)

    @staticmethod
    def _run_commands(commands: list[str]) -> None:
        """Run a list of shell commands, stopping on the first failure."""
        for command in commands:
            subprocess.run(
                command,
                shell=True,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    # ── self-protection ──────────────────────────────────────────────────

    def disable_self_protection(self) -> tuple[str, str] | None:
        """Disable Kaspersky self-protection in the registry.

        Returns a ``(status_text, color)`` tuple for the UI to update the
        self-protection label immediately, or ``None`` if the state didn't
        change.
        """
        if not self.version_key:
            self._msg("未检测到卡巴斯基软件，无法关闭自我保护", "red")
            return None

        sp = self.get_self_protection_status()
        if sp == 0:
            self._msg("已关闭软件的自我保护功能，无需操作", "red")
            return ("已关闭", "green")
        elif sp == 1:
            base = self._get_base_path()
            ok = set_registry_value(
                base, f"{self.version_key}\\settings", "EnableSelfProtection", 0
            )
            if not ok:
                self._msg("关闭自我保护失败，请进安全模式下操作", "red")
                return None
            self._msg("操作成功，自我保护功能已关闭", "green")
            return ("已关闭", "green")
        else:
            self._msg("无法获取自我保护状态，操作失败", "red")
            return None

    # ── patch (AVP only) ─────────────────────────────────────────────────

    def get_patch(self) -> None:
        """Enable early patch access (``UpdateTarget = 200``) for AVP."""
        if not self.check_conditions():
            return

        if not self.version_key or not self.version_key.startswith("AVP"):
            self._msg("未检测到卡巴斯基家庭版软件", "red")
            return

        self._msg("正在检查获取补丁设置...", "blue")

        current = get_registry_value(
            AVP_BASE, f"{self.version_key}\\environment", "UpdateTarget"
        )
        if current is not None:
            if current == 200:
                self._msg("已开启提前获取补丁，无需操作", "red")
                return
            ok = set_registry_value(
                AVP_BASE, f"{self.version_key}\\environment", "UpdateTarget", 200
            )
            if ok:
                self._msg("操作成功，已开启提前获取补丁", "green")
            else:
                self._msg("请先关闭卡巴的自我保护并退出软件再操作", "red")
        else:
            self._msg("未检测到卡巴斯基家庭版软件", "red")

    # ── desktop protection (AVP only) ────────────────────────────────────

    def desktop_protection(self) -> None:
        """Disable the secure desktop confirmation prompt (AVP only)."""
        if not self.version_key:
            self._msg("未检测到卡巴斯基家庭版软件", "red")
            return
        if self.version_key.startswith("KES"):
            self._msg("未检测到卡巴斯基家庭版软件", "red")
            return

        subkey = f"{self.version_key}\\environment"
        current = get_registry_value(AVP_BASE, subkey, "SecuredDesktopDisabled")
        if current == "1":
            self._msg("已关闭桌面请求确认保护提示，无需操作", "red")
        else:
            ok = set_registry_value(
                AVP_BASE, subkey, "SecuredDesktopDisabled", "1", winreg.REG_SZ
            )
            if ok:
                self._msg("操作成功，已关闭桌面请求确认保护提示", "green")
            else:
                self._msg("请先关闭卡巴的自我保护并退出软件再操作", "red")

    # ── version update toggle (AVP only) ─────────────────────────────────

    def version_update(self) -> None:
        """Disable automatic version updates (AVP only)."""
        if not self.version_key or not self.version_key.startswith("AVP"):
            self._msg("未检测到卡巴斯基家庭版软件", "red")
            return

        subkey = f"{self.version_key}\\environment"
        current = get_registry_value(AVP_BASE, subkey, "IsVersionUpdateEnabled")

        if current is not None and current == 0:
            self._msg("已关闭版本更新，无需操作", "red")
            return

        ok = set_registry_value(AVP_BASE, subkey, "IsVersionUpdateEnabled", 0)
        if ok:
            self._msg("操作成功，版本自动更新已关闭", "green")
        else:
            self._msg("请先关闭卡巴的自我保护并退出软件再操作", "red")

    # ── safe mode reboot ─────────────────────────────────────────────────

    @staticmethod
    def safe_mode_reboot() -> bool:
        """Configure safe-mode (network) boot and immediately reboot.

        Returns ``True`` if the reboot was initiated successfully.
        """
        try:
            subprocess.run(
                ["bcdedit", "/set", "{current}", "safeboot", "network"],
                check=True,
                capture_output=True,
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
                capture_output=True,
            )
            subprocess.run(
                [
                    "shutdown",
                    "-r",
                    "-t",
                    "3",
                    "-c",
                    "电脑将在3秒后重启进入安全模式",
                ],
                check=True,
                capture_output=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    # ── VBScript license ops ─────────────────────────────────────────────

    @staticmethod
    def get_vbs_path() -> str:
        """Resolve the absolute path to ``Act.vbs``."""
        from kaspersky_toolbox.utils import get_vbs_path as _resolve

        return _resolve()

    def export_license(self) -> None:
        """Launch the VBScript license export helper."""
        if not self.check_conditions():
            return

        vbs_path = self.get_vbs_path()
        if os.path.exists(vbs_path):
            subprocess.Popen(["wscript", vbs_path])
            self._msg("授权导出成功，已保存在桌面", "green")
        else:
            self._msg("未找到调试文件", "red")

    def import_license(self, file_path: str) -> None:
        """Launch the VBScript license import helper with *file_path*."""
        if not self.check_conditions():
            return

        vbs_path = self.get_vbs_path()
        if os.path.exists(vbs_path):
            subprocess.Popen(f'wscript "{vbs_path}" "{file_path}"')
            self._msg("授权导入成功，即将自动重启软件", "green")
        else:
            self._msg("未找到调试文件", "red")
