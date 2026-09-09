---
name: logic-analyzer
description: 当需要用 Saleae 逻辑分析仪在线采集数字波形并解码 I2C/SPI/UART/CAN 时使用，通过 Logic 2 自动化服务驱动硬件采集、添加协议解码器并导出数据。支持两条独立链路：官方 MCP server（AI 客户端直接接入）与 Python Automation API（gRPC 脚本）。
compatibility: Requires python3. gRPC 链路需 logic2-automation（见 scripts/requirements.txt）；MCP 链路仅用标准库。
---

# 逻辑分析仪采集（Saleae）

## 适用场景

- 嵌入式设备的 I2C/SPI/UART 时序需要用逻辑分析仪验证。
- 需要在线触发 Saleae 设备采集指定通道的数字波形。
- 需要对采集到的波形添加协议解码器，导出解码后的数据表（CSV）。
- 需要导出原始通道波形（CSV）做进一步分析。
- 需要让支持 MCP 的 AI 客户端（Claude Code、Codex 等）直接控制 Logic 2。

## 必要输入

- Logic 2 桌面软件已运行，且开启 automation server（Settings/Preferences → Automation，或底部状态栏 Automation 按钮；也可命令行 `Logic.exe --automation` 启动）。
- 如走 MCP 链路：另需在 Automation 弹层打开 **MCP Server** 开关（EXPERIMENTAL，端口 10530，与 gRPC 的 10430 互相独立）。
- Saleae 设备已连接（或用 Logic 2 的仿真设备测试，`--include-sim`）。
- 采集通道、采样率、持续时间。
- 解码协议时：每个解码器的协议类型与通道映射。

## 依赖

- **gRPC 链路（la_tool.py）**：`logic2-automation`（pip install logic2-automation），Logic 2 automation server 默认端口 10430。
- **MCP 链路（logic2_mcp_client.py）**：无第三方依赖（仅标准库），官方 MCP server 默认端口 10530。

## 两条链路怎么选

| | gRPC Automation API（la_tool.py） | 官方 MCP server（logic2_mcp_client.py） |
|---|---|---|
| 前置开关 | Automation Server | MCP Server（EXPERIMENTAL） |
| 端口 | 10430 | 10530 |
| 依赖 | pip install logic2-automation | 无（标准库 HTTP） |
| 优势 | 一条命令完成"采集+多解码器+导出"，参数简单，失败分类明确 | 任何 MCP 客户端即插即用（`claude mcp add --transport http logic2 http://127.0.0.1:10530`），工具带 schema 自描述 |
| 适用 | 脚本化、一次性任务 | AI 客户端长期接入、交互式控制 |

两条链路同属一个 Logic 2 后台进程，可同时开启，互不影响。探测两条链路状态：`python scripts/la_tool.py --detect`。

## 执行步骤

1. 先阅读 [references/usage.md](references/usage.md)，确认操作参数与解码器设置键。
2. 探测环境（检查包、端口、Logic 2 连通性与设备）：
   ```bash
   python scripts/la_tool.py --detect
   ```
3. 列出设备：
   ```bash
   python scripts/la_tool.py --devices
   ```
4. 采集与解码（gRPC 链路，推荐可重复的 `--analyzer`，一次采集可挂多个解码器，各自导出独立 CSV）：
   ```bash
   # 单协议：I2C（SCL=CH0, SDA=CH1）
   python scripts/la_tool.py --capture --channels 0-1 --samplerate 4M --duration 5 \
       --analyzer "i2c:scl=0,sda=1"

   # 多协议同时解码：I2C + UART + SPI
   python scripts/la_tool.py --capture --channels 0-6 --samplerate 16M --duration 5 \
       --analyzer "i2c:scl=0,sda=1" \
       --analyzer "uart:rx=2,baud=115200" \
       --analyzer "spi:clk=3,mosi=4,miso=5,cs=6"

   # CAN（单线，500kbps）
   python scripts/la_tool.py --capture --channels 0 --samplerate 4M --duration 5 \
       --analyzer "can:can=0,baud=500000"
   ```
   `--analyzer` 格式为 `协议:键=值,...`：
   - `i2c`：`scl`、`sda`（均必填）
   - `spi`：`clk`（必填），`mosi`、`miso`、`cs`（可选，未接的省略）
   - `uart`：`rx`（必填）、`baud`（默认 115200）
   - `can`：`can`（必填）、`baud`（默认 500000）

   同协议出现多次会自动按 `i2c`、`i2c2` 区分导出文件名。

5. MCP 链路（等价替代，交互式控制或 MCP 客户端接入时用）：
   ```bash
   python scripts/logic2_mcp_client.py detect        # 探测服务与版本
   python scripts/logic2_mcp_client.py list          # 列出 15 个工具
   python scripts/logic2_mcp_client.py call start_capture '{"logicDeviceConfiguration":{"logicChannels":{"digitalChannels":[1]},"digitalSampleRate":16000000},"captureConfiguration":{"timedCaptureMode":{"durationSeconds":5}}}'
   ```
   完整端到端示例与 15 个工具清单见 [references/usage.md](references/usage.md) 的 MCP 章节。

6. 输出位置：默认存到工程根 `.captures/logic-analyzer/`，文件名带时间戳防覆盖（如 `i2c_20260625_201048.csv`）。
   - 可用环境变量 `LA_CAPTURE_DIR` 覆盖默认目录。
   - 单解码器时可用 `--output 路径` 指定文件；相对路径相对默认目录，绝对路径原样。
   - 数值进制用 `--radix hex|dec|bin|ascii`（默认 hex）。

### 自然语言提示词模板

让 AI 调用本 skill 时，**通道映射是必须说清的物理接线信息**（AI 无法探测），SCL/SDA、CLK 等谁接哪个通道要明确。模板（填空即用）：

- I2C：`抓 I2C，SCL=通道5，SDA=通道6，采集20秒`
- SPI：`抓 SPI，CLK=通道3，MOSI=通道4，MISO=通道5，CS=通道6，采集10秒`
- UART：`抓 UART，RX=通道2，波特率115200，采集10秒`
- CAN：`抓 CAN，信号接通道0，波特率500k，采集10秒`
- 多协议：`同时抓 I2C(SCL=5,SDA=6) 和 UART(RX=2,波特率115200)，采集15秒`

可省略项（不说则用默认）：采样率（I2C/UART/CAN 用 4M 足够，SPI 高速建议 16M~24M）、时长（默认 5 秒）、端口/地址（默认 10430 / 本机，无需指定）。
**采集期间务必让总线有通信**，否则解出空表。

### 自动启动 Logic 2（`--launch`，实验性）

脚本支持 `--launch` 自动拉起 Logic 2（用完自动关闭），省去手动开软件。但在部分环境（如从 git bash 后台启动 GUI）实测不可靠——进程无法维持、端口起不来。**默认仍建议手动打开 Logic 2 并开启 automation server，用普通连接模式。** 仅在确认本机环境支持时使用 `--launch`。

### 向后兼容（旧式单协议写法，仍可用）

```bash
python scripts/la_tool.py --capture --channels 0-1 --samplerate 4M --duration 5 \
    --decode i2c --i2c-scl 0 --i2c-sda 1
```
新代码优先用 `--analyzer`；`--decode` 仅在未提供 `--analyzer` 时生效。

### 扩展新协议

支持新协议（如 1-Wire、LIN、Manchester 等）只需在 [scripts/la_tool.py](scripts/la_tool.py) 的 `ANALYZER_NAMES` 与 `ANALYZER_SPECS` 各加一条：协议短名 → Logic 2 解码器名、短键到 settings 键的映射、必填键列表。解析、采集、导出逻辑全部自动复用，无需改函数体（CAN 即按此方式加入）。

**关键**：`settings` 键名必须与 Logic 2 界面里该解码器的设置项**完全一致**。不要凭猜——最可靠的做法是在 Logic 2 运行时用 API 试探：对一个临时采集反复 `add_analyzer(name, settings=...)`，成功的那组键名即为正确值。

## 失败分流

- `tool-missing`：logic2-automation 未安装（仅 gRPC 链路；MCP 链路无此问题）。
- `connection-failure`：连不上 Logic 2 自动化服务（软件未运行或未开启 automation server）。
- `mcp-not-enabled`：10530 端口未监听。到 Logic 2 → Settings → Automation 打开 MCP Server 开关；用 `python scripts/logic2_mcp_client.py detect` 复测。
- `no-device`：未发现已连接的 Saleae 设备。
- `capture-failure`：采集启动或过程出错。
- `decode-error`：协议解码器添加失败（通常是设置键或通道映射不匹配）。
- MCP 报 `should be object`：settings 值必须包对象，如 `{"Bit Rate (Bits/s)":{"numberValue":3000000}}`，见 [references/usage.md](references/usage.md) MCP 已知坑。

## 输出约定

示例输出格式：

```
结果: ✅ 采集完成 5.0s，2 个解码器: i2c, uart
  连接: 127.0.0.1:10430 ch=[0, 1, 2] 16000000Hz 5.0s
  📄 输出: E:\work\project\.captures\logic-analyzer\i2c_20260625_201643.csv
  📄 输出: E:\work\project\.captures\logic-analyzer\uart_20260625_201643.csv
```

导出的 CSV 列：`name,type,start_time,duration,ack,address,read,data`（随协议略有差异）。
data 列按 `--radix` 指定进制显示（默认十六进制，如 `0x2C`）。
MCP 链路导出注意：`radixType` 1=二进制/2=有符号十进制/3=hex，缺省为 ASCII（有损）；时间戳缺省 ISO8601，`iso8601Timestamp:false` 时为相对秒。

## 实测记录

- 2026-09-09，Logic 2.4.46：gRPC 链路 10 s UART 采集解码 7283 字节；MCP 链路 5 s 采集经帧级 CRC 校验 50/50 全对。两链路统计一致，`--detect` 能正确报告 10430/10530 双端口状态。

## 交接关系

- 从 `build-keil` / `build-platformio` 烧录固件后，用此 skill 验证总线时序。
- 与 `serial-monitor` 互补：serial-monitor 查看串口调试输出，logic-analyzer 做信号级时序验证（串口适配器超规格丢帧时，用本 skill 抓线上的波形可区分板端问题还是适配器问题）。
- 与 `visa-debug` 互补：visa-debug 用示波器测模拟量，logic-analyzer 解数字协议。
