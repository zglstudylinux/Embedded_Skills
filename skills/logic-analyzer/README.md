# 逻辑分析仪采集 Skill

`logic-analyzer` 用于驱动 Saleae Logic 2 在线采集数字波形并解码 I2C/SPI/UART/CAN，把"手动开软件→点采集→拖解码器→导数据"变成 AI 可重复执行的一条命令。适合固件联调阶段验证总线时序：串口实际发的是什么字节、I2C 有没有 ACK、SPI 时序对不对，用波形说话。

## 前置条件

- **Logic 2 桌面软件已运行**，且开启 automation server（Settings/Preferences → Automation，或底部状态栏 Automation 按钮；也可 `Logic.exe --automation` 启动）。
- Saleae 设备已连接（无硬件时可用 `--include-sim` 走仿真设备测试脚本链路）。
- **通道映射是必须说清的物理接线信息**（AI 无法探测）：SCL/SDA、MOSI、RX 等谁接哪个通道，调用时必须明确。
- **采集期间务必让总线有通信**，否则解出空表。

## 依赖

两条链路互相独立、可同时开启（同属一个 Logic 2 后台进程）：

| 链路 | 依赖 | 端口 |
|---|---|---|
| gRPC Automation API（`la_tool.py`，推荐日常用） | `pip install -r scripts/requirements.txt`（logic2-automation） | 10430 |
| 官方 MCP server（`logic2_mcp_client.py`，AI 客户端接入用） | 无（仅 Python 标准库） | 10530（Logic 2 → Settings → Automation → 打开 MCP Server，EXPERIMENTAL） |

## 快速上手

```bash
# 1. 探测环境（包/端口/设备/MCP 状态一起报告）
python scripts/la_tool.py --detect

# 2. 采集并解码：I2C（SCL=CH0, SDA=CH1），4M 采样 5 秒
python scripts/la_tool.py --capture --channels 0-1 --samplerate 4M --duration 5 \
    --analyzer "i2c:scl=0,sda=1"

# 3. UART（RX=CH2，115200）
python scripts/la_tool.py --capture --channels 0-2 --samplerate 4M --duration 5 \
    --analyzer "uart:rx=2,baud=115200"

# MCP 链路（等价能力，标准 MCP 协议）
python scripts/logic2_mcp_client.py detect
python scripts/logic2_mcp_client.py list
```

导出默认落在工程根 `.captures/logic-analyzer/`（`LA_CAPTURE_DIR` 可覆盖），文件名带时间戳防覆盖。

## 典型用途

- 验证 UART 某波特率下线上真实字节（例如串口助手丢帧时，区分板端问题还是 USB 转串口适配器问题）
- 抓 I2C 看 NACK/ACK、地址是否正确
- SPI 读写时序、CPOL/CPHA 验证
- 固件回归：烧录后自动采集关键总线波形留档

## 已知坑速查

- 解码器 settings 键名必须与 Logic 2 界面文字完全一致（如 `Bit Rate (Bits/s)`），不确定就在界面上确认；
- MCP 链路 `add_analyzer` 的 settings 值必须包对象：`{"numberValue": 3000000}`；
- MCP 导出的 `radixType`：1=二进制、2=有符号十进制、3=hex，缺省 ASCII（有损，勿用于校验）；
- `--launch` 自动拉起 Logic 2 在部分环境不可靠，默认手动开软件。

完整参数表、MCP 15 个工具清单与端到端示例见 [references/usage.md](references/usage.md)。
