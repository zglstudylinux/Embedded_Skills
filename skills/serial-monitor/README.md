# 串口监视与 AI 排错 Skill

`serial-monitor` 用于自动读取嵌入式开发板的串口日志并用 AI 分析排错。适合固件上板联调阶段：抓启动日志、看运行打印、排查无输出/乱码/反复复位/外设报错等问题。

## 前置条件

- **端口号与波特率必须由用户提供**（或从工程文档确认）。不同开发板的串口波特率各不相同——115200、921600、1500000 都常见，skill 不会替用户猜。
- 用户没给端口时，AI 会先用 `--list` 列出候选让用户选择；没给波特率时直接询问。
- Python 3 + pyserial：`pip install -r scripts/requirements.txt`

## 适用场景

- 烧录/复位后抓完整启动日志（先监听后复位，不丢早期打印）
- 观察运行期输出、验证某个标志是否出现、给设备发一条命令看回应
- 串口乱码定位（波特率扫描 + HEX 原始字节）
- 分析日志中的错误/警告/启动标记，结合工作区源码定位问题

不适用于：GDB/JTAG 断点调试、CAN/Modbus 等总线协议分析、逻辑分析仪时序测量。

## 快速上手

```bash
# 列出串口
python skills/serial-monitor/scripts/serial_capture.py --list

# 按用户给的端口和波特率读 5 秒
python skills/serial-monitor/scripts/serial_capture.py --port COM6 --baud 1500000 --duration 5

# 抓启动日志：脚本先监听并提示，用户复位开发板后自动记录
python skills/serial-monitor/scripts/serial_capture.py --port COM6 --baud 1500000 \
    --wait-reset --duration 8 --save logs/boot.log --timestamp

# 乱码时扫描波特率（需用户确认结果）
python skills/serial-monitor/scripts/serial_capture.py --port COM6 --baud-scan
```

完整参数表与排错手册见 [references/usage.md](references/usage.md)。

## AI 排错输出格式

AI 分析日志时按固定四段输出，每条结论引用原始日志行做证据：

1. **现象**：一句话概括（正常心跳 / 报错 / 循环重启 / 无输出 / 乱码）
2. **证据**：关键原始日志行（错误行、启动标记、重复段落）
3. **分析**：错误含义与可能原因排序；有源码时反查打印位置
4. **下一步**：按可能性排序的可执行验证动作

注意：复位原因标记（如 `LVD_RST`）或日志重复只是证据，AI 会先确认用户是否手动复位/重新上电，再判断是否真有电压、看门狗或崩溃问题。

## 返回码

- `0`：抓取成功且无错误行
- `1`：环境/连接失败、无数据或乱码
- `2`：抓到日志但发现错误相关行
