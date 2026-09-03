# serial-monitor 脚本用法

脚本：[scripts/serial_capture.py](../scripts/serial_capture.py)。依赖 `pyserial`（`pip install -r scripts/requirements.txt`）。

## 能力概览

- 列出/自动识别串口（优先 CH340/CP210x/FT232 等 USB 转串口芯片）
- 定长抓取、等待关键字符串、持续监视、先监听后复位抓启动日志
- 波特率自动扫描（乱码排错利器）、HEX+ASCII 原始字节输出
- 日志落盘（追加）、每行时间戳、可选发送一行文本
- 自动统计可打印占比、错误/警告/启动标记，给出初步状态判断

> **前置条件**：端口号与波特率必须使用开发板实际配置。不同开发板出厂默认波特率不同（115200、921600、1500000 都常见），由用户提供或从工程文档确认；`--auto` 与 `--baud-scan` 仅在用户明确要求时使用，扫描结果需用户确认后再继续。

## 参数表

| 参数 | 说明 |
| --- | --- |
| `--list` | 列出可用串口及设备类型提示 |
| `--auto` | 自动选择最可能的串口（仅用户明确要求时使用） |
| `--port` | 串口名，如 `COM6`、`/dev/ttyUSB0`（由用户提供） |
| `--baud` | 波特率（由用户提供，脚本默认 `115200` 仅为兜底） |
| `--duration` | 读取时长（秒），默认 `5`；`--monitor` 时忽略 |
| `--baud-scan` | 逐个候选波特率采样打分（仅用户明确要求时使用） |
| `--wait-reset` | 先打开串口监听，检测到新数据（用户复位）后开始记录 |
| `--reset-timeout` | 等待复位的超时秒数，默认 `30` |
| `--wait "STR"` | 日志中出现指定字符串即停 |
| `--wait-timeout` | `--wait` 超时秒数，默认 `60`，`0`=不限 |
| `--monitor` | 持续监视，`Ctrl+C` 结束 |
| `--save FILE` | 日志追加保存到文件，自动创建父目录 |
| `--timestamp` | 每行前加 `HH:MM:SS.mmm` 时间戳 |
| `--hex` | 以 `偏移 HEX ASCII` 形式输出原始字节，跳过行分析 |
| `--send "text"` | 抓取开始前发送一行文本（自动补 `\r\n`） |

返回码：`0`=抓取成功且无错误行；`1`=环境/连接失败、无数据或乱码；`2`=抓到日志但发现错误相关行。

## 常用命令

```bash
# 列出串口
python skills/serial-monitor/scripts/serial_capture.py --list

# 指定串口读 5 秒（板子正在运行）
python skills/serial-monitor/scripts/serial_capture.py --port COM6 --duration 5

# 抓启动日志：先监听，提示后手动复位开发板，保存日志
python skills/serial-monitor/scripts/serial_capture.py --port COM6 --wait-reset --duration 8 --save logs/boot.log --timestamp

# 乱码时自动扫描波特率
python skills/serial-monitor/scripts/serial_capture.py --port COM6 --baud-scan --duration 5

# 二进制/疑似乱码时看原始字节
python skills/serial-monitor/scripts/serial_capture.py --port COM6 --hex --duration 3

# 等待启动标志出现
python skills/serial-monitor/scripts/serial_capture.py --port COM6 --wait "System Start" --wait-timeout 30

# 发送命令后读回应
python skills/serial-monitor/scripts/serial_capture.py --port COM6 --send "version" --duration 3
```

## AI 排错手册（日志模式 → 判断）

| 日志表现 | 判断 | 下一步 |
| --- | --- | --- |
| 0 字节 | 无输出 | `--wait-reset` 抓启动；查波特率/TX-RX 交反/供电/共地 |
| 可打印占比 < 90% | 波特率不匹配或二进制协议 | `--baud-scan`；仍异常则 `--hex` 判断是否协议帧 |
| 同一段启动头反复出现 | 疑似反复重启：崩溃看门狗复位或断电 | **先确认用户是否手动复位/重新上电/烧录**；排除人工操作后抓完整一段，看最后几行（常是 Fault 现场），建议接调试器 |
| `HardFault`/`CFSR`/_backtrace/`Panic`/`Assertion failed` | 运行期崩溃 | 保留原文；有源码时用文本反查打印位置；建议 `debug-gdb-openocd` 类流程 |
| `timeout`/`retry`/`NACK` 集中在某总线名 | 外设通信异常 | 记录总线与器件名；查接线/上拉/地址/时钟 |
| 正常心跳但功能无响应 | 日志层正常，问题在输入侧 | `--send` 主动发命令验证交互通路 |
| 启动标记齐全且无错误 | 启动正常 | 按用户关注的功能关键词继续观察 |

## 故障排查

- **拒绝访问/打不开**：端口被串口助手、PuTTY、IDE 串口监视器占用；关闭后重试。Windows 下表现为 `Access is denied`。
- **`--baud-scan` 全部候选几乎无数据**：不是波特率问题。查 TX/RX 是否接反（对调试试）、板子是否供电、是否共地、固件是否停在中断/死循环。
- **`--wait-reset` 超时**：确认在超时窗口内按了复位；有些板子复位瞬间 USB 枚举会断开重连，此时改用普通 `--duration` 在复位前打开串口或延长 `--reset-timeout`。
- **日志每行都是乱码但占比正常**：可能是中文 GBK 输出，脚本按 UTF-8 解码显示为 `?`；内容判断以结构（行数、错误词）为准。
- **CP210x/CH340 驱动**：设备管理器里看不到 COM 口时先装厂商驱动，`--list` 才能看到。
