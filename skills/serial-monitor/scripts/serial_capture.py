#!/usr/bin/env python
"""串口日志抓取与初步分析工具。

为 serial-monitor skill 提供可重复调用的执行入口：
- 列出/自动识别串口
- 定长抓取、等待关键字符串、先监听后复位抓启动日志
- 波特率自动扫描（乱码排错）、HEX 原始字节输出
- 日志落盘、时间戳、错误/警告/启动标记的初步分析

返回码：0=抓取成功且无错误行；1=环境/连接失败或无数据/乱码；2=抓到日志但发现错误行。
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime
from pathlib import Path

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

try:
    import serial as pyserial
    from serial.tools import list_ports

    SERIAL_IMPORT_ERROR = None
except ImportError as exc:  # pragma: no cover
    pyserial = None
    list_ports = None
    SERIAL_IMPORT_ERROR = exc

DEFAULT_BAUD = 115200
DEFAULT_DURATION = 5
RESET_TIMEOUT = 30
WAIT_TIMEOUT = 60

BAUD_CANDIDATES = [115200, 9600, 57600, 38400, 19200, 230400, 460800, 921600, 4800, 74880]

ANSI_ESCAPE = re.compile(r"\033\[[0-9;]*m")
ERROR_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\[error\]", r"\berror\b", r"\bfault\b", r"\bpanic\b", r"\bassert\w*\b",
        r"\bexception\b", r"\bfail(?:ed|ure)?\b", r"hardfault", r"\boops\b",
        r"traceback", r"\babort\b", r"\btimeout\b",
    ]
]
WARNING_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [r"\[warn(?:ing)?\]", r"\bwarning\b", r"\bwarn\b", r"\bretry\b", r"\bretries\b"]
]
STARTUP_PATTERNS = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"system start", r"\bboot\b", r"reset reason", r"firmware version", r"build:",
        r"starting", r"\bready\b", r"\binit\b", r"banner", r"\bstartup\b",
    ]
]
# 部分固件用 <NAME> value 形式转储配置参数（如 <RETRY> 3），不是警告
CONFIG_TAG = re.compile(r"^\s*<[A-Za-z_][A-Za-z0-9_]*>")


class Stats:
    def __init__(self) -> None:
        self.bytes = 0
        self.printable = 0

    def feed(self, data: bytes) -> None:
        self.bytes += len(data)
        self.printable += sum(1 for b in data if b in (9, 10, 13) or 0x20 <= b <= 0x7E)

    @property
    def ratio(self) -> float:
        return self.printable / self.bytes if self.bytes else 0.0


def require_pyserial() -> bool:
    if pyserial is not None:
        return True
    print("❌ 未安装 pyserial，请先执行：pip install pyserial")
    if SERIAL_IMPORT_ERROR is not None:
        print(f"   导入错误: {SERIAL_IMPORT_ERROR}")
    return False


def device_label(description: str) -> str:
    d = description.upper()
    if "CH340" in d or "CH341" in d:
        return "USB 转串口(CH340)"
    if "CP210" in d:
        return "USB 转串口(CP210x)"
    if "FT232" in d:
        return "USB 转串口(FT232)"
    if "CMSIS-DAP" in d or "DAPLINK" in d:
        return "CMSIS-DAP"
    if "STLINK" in d or "ST-LINK" in d:
        return "ST-Link"
    if "J-LINK" in d or "JLINK" in d:
        return "J-Link"
    if "MODEM" in d:
        return "AT 口/Modem"
    return ""


def cmd_list_ports() -> list[str]:
    if not require_pyserial():
        return []
    ports = list(list_ports.comports())
    if not ports:
        print("❌ 未找到可用串口")
        return []
    print("📡 可用串口：")
    devices = []
    for i, p in enumerate(ports, 1):
        label = device_label(p.description)
        extra = f"  [{label}]" if label else ""
        print(f"  {i}. {p.device}: {p.description}{extra}")
        devices.append(p.device)
    return devices


def auto_detect_port() -> str | None:
    if not require_pyserial():
        return None

    def prio(desc: str) -> int:
        d = desc.upper()
        if "CH340" in d or "CH341" in d or "CP210" in d or "FT232" in d:
            return 1
        if "CMSIS-DAP" in d or "DAPLINK" in d or "STLINK" in d or "J-LINK" in d:
            return 2
        if "USB" in d:
            return 3
        return 9

    candidates = sorted((prio(p.description), p.device) for p in list_ports.comports())
    return candidates[0][1] if candidates else None


def open_port(port: str, baud: int):
    if not require_pyserial():
        return None
    try:
        ser = pyserial.Serial(
            port=port, baudrate=baud, timeout=0.1,
            bytesize=pyserial.EIGHTBITS, parity=pyserial.PARITY_NONE,
            stopbits=pyserial.STOPBITS_ONE,
        )
        time.sleep(0.1)
        return ser
    except pyserial.SerialException as exc:
        print(f"❌ 无法打开串口 {port}: {exc}")
        if "PermissionError" in type(exc).__name__ or "拒绝访问" in str(exc) or "Access is denied" in str(exc):
            print("   串口可能被占用：请关闭串口助手/IDE 等其他占用该端口的程序。")
        return None


def baud_scan(port: str, seconds: float = 0.8) -> int | None:
    """逐个候选波特率短促采样，按可打印字符占比打分，返回最可能的波特率。"""
    print(f"🔍 开始波特率扫描（每个候选采样 {seconds:.1f} 秒）...")
    results = []
    for baud in BAUD_CANDIDATES:
        ser = open_port(port, baud)
        if ser is None:
            return None
        stats = Stats()
        deadline = time.time() + seconds
        try:
            while time.time() < deadline:
                n = ser.in_waiting
                if n:
                    stats.feed(ser.read(n))
                time.sleep(0.01)
        finally:
            ser.close()
        results.append((baud, stats.bytes, stats.ratio))
        flag = ""
        if stats.bytes >= 20 and stats.ratio >= 0.95:
            flag = "  ← 疑似正确"
        print(f"   {baud:>7} baud: {stats.bytes:>6} 字节, 可打印占比 {stats.ratio * 100:5.1f}%{flag}")

    scored = [(ratio, baud) for baud, n, ratio in results if n >= 20]
    if not scored:
        print("⚠️ 所有波特率下几乎无数据，先检查接线/供电/复位状态，而不是波特率。")
        return None
    scored.sort(reverse=True)
    best_ratio, best_baud = scored[0]
    if best_ratio < 0.95:
        print(f"⚠️ 最佳候选 {best_baud} 可打印占比仅 {best_ratio * 100:.1f}%，可能为二进制协议或加密输出。")
        return None
    print(f"✅ 波特率扫描选定: {best_baud}")
    return best_baud


def wait_for_reset(ser, timeout: float) -> bool:
    if ser.in_waiting > 0:
        ser.reset_input_buffer()
        time.sleep(0.05)
    print(f"⏳ 已打开串口并开始监听，请在 {timeout:.0f} 秒内复位开发板（或触发烧录复位）...")
    deadline = time.time() + timeout
    while time.time() < deadline:
        if ser.in_waiting > 0:
            print("✅ 检测到串口数据，开始记录...")
            return True
        time.sleep(0.01)
    print(f"⚠️ {timeout:.0f} 秒内未检测到新数据，将继续抓取当前输出。")
    return False


def hex_dump(data: bytes) -> str:
    lines = []
    for off in range(0, len(data), 16):
        chunk = data[off:off + 16]
        hexpart = " ".join(f"{b:02X}" for b in chunk)
        ascpart = "".join(chr(b) if 0x20 <= b <= 0x7E else "." for b in chunk)
        lines.append(f"{off:08X}  {hexpart:<47}  |{ascpart}|")
    return "\n".join(lines)


def capture(
    ser,
    duration: int,
    wait_pattern: str | None,
    wait_timeout: int,
    save_file: str | None,
    show_ts: bool,
    hex_mode: bool,
    send_text: str | None,
) -> tuple[list[tuple[str, str, float]], bytes]:
    """抓取主循环，返回 (完整行列表, 全部原始字节)。"""
    logs: list[tuple[str, str, float]] = []  # (clean, raw, ts)
    raw_all = bytearray()
    stats = Stats()
    start = time.time()
    line_buf = ""
    save_handle = None

    if save_file:
        save_path = Path(save_file)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        save_handle = save_path.open("a", encoding="utf-8", errors="replace")

    if send_text:
        payload = send_text if send_text.endswith(("\n", "\r")) else send_text + "\r\n"
        ser.write(payload.encode("utf-8", errors="replace"))
        ser.flush()
        print(f"📤 已发送: {send_text!r}")

    print(f"📖 开始读取 {ser.port} @ {ser.baudrate} baud，持续 {duration} 秒。")
    print("=" * 70)

    try:
        while True:
            elapsed = time.time() - start
            if duration >= 0 and elapsed >= duration:
                break
            if wait_pattern and elapsed >= wait_timeout:
                print(f"\n⚠️ 等待 {wait_timeout} 秒未出现关键字符串: {wait_pattern}")
                break

            n = ser.in_waiting
            if n:
                data = ser.read(n)
                stats.feed(data)
                raw_all.extend(data)

                if hex_mode:
                    block = hex_dump(data)
                    print(block)
                    if save_handle:
                        save_handle.write(block + "\n")
                        save_handle.flush()
                    continue

                text = data.decode("utf-8", errors="replace")
                for ch in text:
                    if ch in ("\r", "\n"):
                        if not line_buf.strip():
                            line_buf = ""
                            continue
                        clean = ANSI_ESCAPE.sub("", line_buf).rstrip()
                        stamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        shown = f"[{stamp}] {clean}" if show_ts else clean
                        print(shown)
                        logs.append((clean, line_buf, time.time()))
                        if save_handle:
                            save_handle.write(f"{shown}\n")
                            save_handle.flush()
                        if wait_pattern and wait_pattern in clean:
                            print(f"\n✅ 检测到关键字符串: {wait_pattern}")
                            return logs, bytes(raw_all)
                        line_buf = ""
                    else:
                        line_buf += ch
            else:
                time.sleep(0.002)
    except KeyboardInterrupt:
        print("\n⚠️ 用户中断")
    finally:
        if save_handle:
            save_handle.close()

    print("=" * 70)
    return logs, bytes(raw_all)


def matches(patterns, text: str) -> bool:
    return any(p.search(text) for p in patterns)


def analyze(logs, stats: Stats) -> int:
    errors, warnings = [], []
    for line, _, _ in logs:
        if CONFIG_TAG.match(line) and not re.search(r"\[(?:error|warn)", line, re.I):
            continue  # <NAME> value 配置转储行，不算警告
        if matches(ERROR_PATTERNS, line):
            errors.append(line)
        elif matches(WARNING_PATTERNS, line):
            warnings.append(line)
    startup = [line for line, _, _ in logs if matches(STARTUP_PATTERNS, line)]

    print("📊 分析结果")
    if stats.bytes == 0:
        print("  状态: ⚠️ 无数据（串口已打开但未收到任何字节）")
        print("  排查: 1) 波特率是否匹配 2) TX/RX 是否接反 3) 板子是否在运行/复位 4) 是否共地")
        return 1

    garbled = stats.ratio < 0.90 and stats.bytes >= 50
    if garbled:
        print(f"  状态: ⚠️ 疑似乱码（{stats.bytes} 字节，可打印占比仅 {stats.ratio * 100:.1f}%）")
        print("  排查: 大概率波特率不匹配 → 用 --baud-scan 自动扫描；也可能为二进制协议 → 用 --hex 看原始字节")
        return 1
    if errors:
        print(f"  状态: ❌ 检测到 {len(errors)} 条错误相关日志")
    elif warnings:
        print(f"  状态: ⚠️ 检测到 {len(warnings)} 条警告相关日志")
    elif logs:
        print(f"  状态: ✅ 串口日志正常（共 {len(logs)} 行，{stats.bytes} 字节）")
    else:
        print(f"  状态: ⚠️ 收到 {stats.bytes} 字节但没有完整行（可能输出未换行或抓取时长太短）")
        return 1

    print(f"  统计: 行数={len(logs)}  字节={stats.bytes}  可打印占比={stats.ratio * 100:.1f}%  "
          f"错误行={len(errors)}  警告行={len(warnings)}  启动标记={'有' if startup else '无'}")

    if startup:
        print("  启动标记样例:")
        for line in startup[:3]:
            print(f"    {line}")
    if errors:
        print("  ❌ 错误样例:")
        for line in errors[:5]:
            print(f"    {line}")
        if len(errors) > 5:
            print(f"    ... 还有 {len(errors) - 5} 条")
    if warnings:
        print("  ⚠️ 警告样例:")
        for line in warnings[:5]:
            print(f"    {line}")
    return 2 if errors else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="嵌入式串口日志抓取与初步分析工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s --list
  %(prog)s --port COM6 --duration 5
  %(prog)s --port COM6 --wait-reset --duration 8 --save logs/boot.log
  %(prog)s --port COM6 --baud-scan
  %(prog)s --port COM6 --hex --duration 3
  %(prog)s --port COM6 --wait "System Start" --wait-timeout 30
        """,
    )
    parser.add_argument("--port", help="串口名，如 COM6 / /dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD, help=f"波特率，默认 {DEFAULT_BAUD}")
    parser.add_argument("--duration", type=int, default=DEFAULT_DURATION, help="读取时长（秒），--monitor 时忽略")
    parser.add_argument("--list", action="store_true", help="列出可用串口")
    parser.add_argument("--auto", action="store_true", help="自动选择最可能的串口")
    parser.add_argument("--baud-scan", action="store_true", help="自动扫描候选波特率并选出最可能值")
    parser.add_argument("--wait-reset", action="store_true", help="先监听，等复位后抓启动日志")
    parser.add_argument("--reset-timeout", type=int, default=RESET_TIMEOUT, help=f"等待复位的超时秒数，默认 {RESET_TIMEOUT}")
    parser.add_argument("--wait", help="等待指定字符串出现即停")
    parser.add_argument("--wait-timeout", type=int, default=WAIT_TIMEOUT, help=f"--wait 的超时秒数，默认 {WAIT_TIMEOUT}，0=不限")
    parser.add_argument("--monitor", action="store_true", help="持续监视直到 Ctrl+C")
    parser.add_argument("--save", help="保存日志到文件（追加）")
    parser.add_argument("--timestamp", action="store_true", help="每行加时间戳")
    parser.add_argument("--hex", action="store_true", help="以 HEX+ASCII 形式输出原始字节")
    parser.add_argument("--send", help="抓取开始前发送一行文本（自动补 \\r\\n）")
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.list:
        cmd_list_ports()
        return 0

    if not require_pyserial():
        return 1

    port = args.port
    if args.auto or not port:
        port = auto_detect_port()
        if not port:
            print("❌ 无法自动检测串口，请用 --list 查看后用 --port 指定。")
            return 1
        print(f"✅ 自动检测到串口: {port}")

    baud = args.baud
    if args.baud_scan:
        best = baud_scan(port)
        if best is None:
            return 1
        baud = best

    ser = open_port(port, baud)
    if ser is None:
        cmd_list_ports()
        return 1

    print(f"✅ 串口已打开: {ser.port} @ {ser.baudrate} baud")
    if args.wait_reset:
        wait_for_reset(ser, args.reset_timeout)

    duration = -1 if args.monitor else args.duration
    try:
        logs, raw = capture(
            ser,
            duration=duration,
            wait_pattern=args.wait,
            wait_timeout=args.wait_timeout if args.wait_timeout > 0 else 10**9,
            save_file=args.save,
            show_ts=args.timestamp,
            hex_mode=args.hex,
            send_text=args.send,
        )
        if args.hex:
            print(f"📊 HEX 模式：共收到 {len(raw)} 字节，行级分析已跳过")
            return 0 if raw else 1
        stats = Stats()
        stats.feed(raw)
        if not logs and stats.bytes == 0:
            print("📊 分析结果")
            print("  状态: ⚠️ 无数据（未收到任何字节；可能波特率不匹配或设备未输出）")
            print("  排查: 1) --baud-scan 扫描波特率 2) --hex 查看原始字节 3) 复位开发板")
            return 1
        return analyze(logs, stats)
    finally:
        ser.close()
        print(f"🔌 串口已关闭: {ser.port}")


if __name__ == "__main__":
    sys.exit(main())
