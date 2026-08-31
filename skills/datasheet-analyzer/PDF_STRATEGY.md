# PDF 阅读策略

## 第 0 步：先选入口点（最先做）

运行任何命令之前，先确定从哪里开始。对 100 页的 PDF 跑 `page_hints` 需要数分钟 —— 只在真正需要未知文档的结构地图时才运行。

| 场景 | 起点 | 原因 |
|-----------|----------|-----|
| **已知器件 + 1~2 个具体参数** | **Phase 3** | 已知查什么、在哪查 —— 直接用 `search` / `search_table`。`page_hints` 没有附加价值。 |
| 对同一文档的追问 | Phase 3 或 4 | 文档已摸清；重扫浪费时间。 |
| 未知 PDF、开放式分析（"介绍一下这颗芯片"） | Phase 0 | 动手前需要结构地图。 |
| 疑似或已确认的图片型 PDF | Phase 0 | 必须先确认 PDF 类型再选读取路径。 |
| 复杂 IC（充电芯片、MCU、CODEC）+ 一次要多个参数 | Phase 0–2b | 专有章节名需要定向 patterns 才能定位。 |

**回退规则：** 定向抽取失败（找不到参数、表格畸形）时，退回更早的阶段 —— 运行 `page_hints` 或 `search`，而不是猜。

---

## 核心原则

**先导航，后抽取。** 绝不盲读页面。以下各阶段是一个工具箱 —— 什么活用什么工具。

```
┌─────────────────────────────────────────────────────────────────┐
│  Phase 0: 预扫描        →  默认 patterns 扫全文，建粗粒度地图    │
│  Phase 1: 诊断          →  决定读取路径 (text vs image)          │
│  Phase 2: 器件识别      →  确认器件身份，推断要提取的参数        │
│  Phase 2b: 定向重扫     →  用推断出的关键词二次扫描，细化地图    │
│  Phase 3: 章节映射      →  精确定位各功能区的页码                │
│  Phase 4: 定向抽取      →  按器件类型执行有针对性的提取          │
└─────────────────────────────────────────────────────────────────┘
```

## 目录

- [Phase 0: 预扫描（仅未知 PDF 与开放式查询）](#phase-0-预扫描)
- [Phase 1: 诊断](#phase-1-诊断)
- [Phase 2: 器件识别](#phase-2-器件识别)
- [Phase 2b: 用推断的 patterns 定向重扫](#phase-2b-定向重扫)
- [Phase 3: 章节映射](#phase-3-章节映射)
- [Phase 4: 定向抽取](#phase-4-定向抽取)
- [器件类型抽取捷径](#器件类型抽取捷径)
- [错误恢复](#错误恢复)
- [图片型 PDF：完整工作流](#图片型-pdf完整工作流)

---

## Phase 0: 预扫描（仅未知 PDF 与开放式查询）

**目的：** 一次性建立整份文档的结构地图。还不知道去哪找时用它 —— 器件和参数都已知就直接去 Phase 3。`page_hints` 是所有操作里最慢的；只在结构地图真正影响下一步时才运行。

```bash
python scripts/pdf_tools.py info <pdf_path>
python scripts/pdf_tools.py page_hints <pdf_path>   # 扫描全部页面
```

`page_hints` 返回每页的信号和启发式标签。用它确定各章节的候选页：

| 提示标签 | 对应章节 |
|------------|---------------|
| `likely_pinout_page` | 引脚配置、引脚描述表 |
| `likely_timing_diagram` | 时序波形（几乎总是图片，用 render_page） |
| `likely_block_diagram` | 功能框图（图片，用 render_page） |
| `likely_curve_page` | 电气特性曲线（图片） |
| `likely_package_page` | 封装外形、机械尺寸 |
| `likely_register_figure` | 寄存器映射、位域描述 |
| `likely_table_page` | 电气规格表、绝对最大额定值 |

**把提示当候选，不当事实。** `score > 0.5` 且有 2 条以上 reasons 的页面才可靠。`likely_table_page` 的页面若同时命中 "Electrical Characteristics" 的 `search`，几乎可以确定无误。

### 预扫描输出（要记录）

```
PDF: <filename>
Pages: N | Type: text / image
Candidate Pages:
  - Pinout: [p12, p13]
  - Timing diagrams: [p18, p19, p22]
  - Block diagram: [p4]
  - Electrical specs tables: [p8, p9, p10]
  - Package: [p27]
  - Registers: [p30-p45]
```

---

## Phase 1: 诊断

直接使用 Phase 0 得到的 `info` 结果，无需重跑。

| `is_text_based` | 策略 |
|-----------------|----------|
| `true` | 文本抽取路径。用 `page_hints` 扫描 + 定向读取。 |
| `false` | **图片路径。** 用 `render_page` 渲染关键页面，目视阅读。 |

### 图片型 PDF 路径

```bash
# 渲染前 3 页以识别器件
python scripts/pdf_tools.py render_page <pdf_path> 1 180
python scripts/pdf_tools.py render_page <pdf_path> 2 180
python scripts/pdf_tools.py render_page <pdf_path> 3 180
```

目视阅读渲染图。交叉验证：图片中的厂商 + 型号必须与文件名/上下文一致。不一致 → 输出 `UNABLE TO VERIFY`。

图片型 PDF 的所有章节都用 `render_page`。典型流程：
1. 渲染封面 → 识别器件
2. 渲染预扫描候选页 → 确认章节位置
3. 渲染目标页 → 目视抽取规格

---

## Phase 2: 器件识别

```bash
python scripts/pdf_tools.py text <pdf_path> 1
# 若第 1 页只有封面（文本很短）：
python scripts/pdf_tools.py text <pdf_path> 2
```

提取：
1. **型号** —— 首页标题，通常是 `[A-Z]+[0-9]+` 模式
2. **厂商** —— 首页页眉/页脚
3. **器件功能** —— Features 或 Description 章节

由器件功能**推断哪些参数重要：**

| 器件类型 | 要提取的关键规格 |
|-------------|---------------------|
| **LDO / 线性稳压器** | Vout 精度、dropout 电压、静态电流、PSRR、负载调整率 |
| **DC-DC 变换器** | Vin/Vout 范围、效率、开关频率、Iq、反馈电压 |
| **电池充电芯片** | 充电电压、充电电流、终止条件、功率路径、DPM 门限 |
| **MCU / SoC** | 核心电压、IO 电压、主频、Flash/RAM 容量、外设、启动时间 |
| **ADC / DAC** | 分辨率、INL/DNL、SNR、THD+N、采样率、基准电压 |
| **音频 CODEC** | ADC/DAC SNR、THD+N、采样率、I2S 格式、PLL、模拟增益范围 |
| **传感器（IMU/温度等）** | 量程、灵敏度/分辨率、ODR、噪声密度、供电电流 |
| **Flash / EEPROM** | 容量、读写速度、擦除时间、擦写次数、数据保持 |
| **接口（USB/CAN/RS485）** | 数据速率、电压电平、总线电容、传播延迟 |
| **电源复用/负载开关** | Ron、限流、切换时间、Vgs 阈值 |
| **IO 扩展/复用器/模拟开关** | Ron、带宽、漏电流、VOH/VOL |

---

## Phase 2b: 用推断的 patterns 定向重扫

**目的：** 读完器件描述后，你已经知道这颗芯片的专有特性名、功能块和内部术语。据此构造自定义 `--patterns` JSON，重跑 `page_hints`，找出默认 patterns 漏掉的章节。

### 触发条件

器件拥有默认 patterns 覆盖不到的**领域专属子系统**时运行：
- 复杂电源 IC（充电、PMU、电量计）—— 状态机、保护模式
- MCU/SoC —— 时钟树、DMA、中断控制器、外设寄存器
- 音频 CODEC —— 信号链、mixer 路由、PLL、模拟级
- 存储器 —— 命令集、擦除架构、状态寄存器
- 接口/协议 IC —— 协议状态机、枚举流程、协商

简单器件跳过 Phase 2b：LDO、分立 MOSFET、门逻辑、运放、二极管、EEPROM（基础）、RTC。

### 如何构造 patterns

构造材料的阅读顺序：

1. **Features 列表**（第 1-2 页）：专有特性名是最好的 pattern。
   > "VINDPM tracking" → pattern: `"VINDPM"`
   > "Automatic clock switching between HSE and HSI" → pattern: `"clock switching"`
   > "On-chip FIFO with 32 levels" → pattern: `"FIFO"`

2. **目录**（如可抽取）：章节标题就是现成 pattern。
   > "4.3 Charge State Machine" → pattern: `"charge state machine"`
   > "6.2 DMA Controller" → pattern: `"DMA controller"`

3. **页面文本中看到的章节标题**（来自 Phase 0 的文本样本）：原样复用。

### Pattern 质量规则

| 好 pattern | 坏 pattern | 原因 |
|---|---|---|
| `"VINDPM"` | `"voltage"` | 专有术语，不会误命中 |
| `"charge state machine"` | `"charge"` | 短语级，匹配章节标题 |
| `"clock tree"` | `"clock"` | 对 MCU 时钟配置页有区分度 |
| `"FIFO mode"` | `"mode"` | 否则太泛 |
| `"DMA controller"` | `"memory"` | 定位特定章节 |

**pattern 保持 2~4 个词，优先用准确的子系统名而非常用词。**

### 执行

```bash
# 第 1 步：导出默认 patterns 作为基础（避免丢失默认覆盖）
python scripts/pdf_tools.py dump_patterns > /tmp/custom_patterns.json

# 第 2 步：编辑 /tmp/custom_patterns.json —— 新增带推断 patterns 的标签。
# 不要删除已有默认键。示例新增：
# {
#   ...已有默认项...,
#   "likely_charge_state_machine": ["charge state machine", "charging operation", "VINDPM"],
#   "likely_clock_config":         ["clock tree", "system clock", "PLL configuration"],
#   "likely_dma_section":          ["DMA controller", "DMA channel", "direct memory access"]
# }

# 第 3 步：用自定义 patterns 重扫
python scripts/pdf_tools.py page_hints <pdf_path> --patterns /tmp/custom_patterns.json
```

### 合并结果

Phase 2b 之后，合并两次扫描：
- Phase 0 结果 → 结构页（引脚、时序、框图、封装）
- Phase 2b 结果 → 领域专属页（状态机、时钟树、FIFO 配置）

两者合并即 Phase 3 定向抽取的完整章节地图。

---

## Phase 3: 章节映射

预扫描提示 + 定向搜索结合，建立精确的章节地图。

### 第 3a 步：标题搜索（首选）

```bash
python scripts/pdf_tools.py search_caption <pdf_path>
```

数据手册的图表标题是最可靠的章节定位器。重点找：
- `Table X. Absolute Maximum Ratings`
- `Table X. Recommended Operating Conditions`
- `Table X. Electrical Characteristics`
- `Table X. Pin Functions` / `Pin Description`
- `Figure X. Functional Block Diagram`
- `Figure X. Timing Diagram`

### 第 3b 步：关键词搜索（备选）

```bash
python scripts/pdf_tools.py search <pdf_path> "Absolute Maximum"
python scripts/pdf_tools.py search <pdf_path> "Electrical Characteristics"
python scripts/pdf_tools.py search <pdf_path> "Pin Functions"
python scripts/pdf_tools.py search <pdf_path> "Block Diagram"
```

多语言关键词：

| 章节 | 英文 | 中文 |
|---------|---------|---------|
| 绝对最大额定值 | "Absolute Maximum Ratings"、"Max Ratings" | "绝对最大额定值" |
| 电气特性 | "Electrical Characteristics"、"DC Characteristics" | "电气特性" |
| 引脚配置 | "Pin Functions"、"Pin Description"、"Pinout" | "引脚功能"、"引脚说明" |
| 时序 | "Timing Diagram"、"Timing Requirements" | "时序图"、"时序要求" |
| 封装 | "Package Information"、"Mechanical Data" | "封装信息"、"封装尺寸" |
| 应用 | "Typical Application"、"Application Circuit" | "典型应用" |

### 第 3c 步：目录（如有）

```bash
python scripts/pdf_tools.py toc <pdf_path>
```

多数数据手册没有可机读的目录。当作加分项，不作为主策略。有返回时与 Phase 0 提示的页码交叉核对。

### 确认页面

对每个候选页确认是否为目标章节：

```bash
python scripts/pdf_tools.py text <pdf_path> <page_num>
```

---

## Phase 4: 定向抽取

抽取前，考虑打开 **[TEMPLATES.md](TEMPLATES.md)** 查看结构化输出格式：
- `device_info` —— 厂商、型号、封装、温度范围
- `power_domains` —— 全部 VDD/GND 引脚及脚号
- `i2c_interface` —— 地址计算、速率、上拉
- `electrical_specs` — 绝对最大额定值 / 推荐工作条件 / 关键参数

### 4a. 电气特性表

**这是核心抽取。** 多数数据手册有 3 张必备表：

| 表 | 必有 | 搜索关键词 |
|-------|---------------|----------------|
| 绝对最大额定值 | 是 | "Absolute Maximum" |
| 推荐工作条件 | 是 | "Recommended Operating" |
| 直流电气特性 | 是 | "Electrical Characteristics"、"DC Characteristics" |

```bash
# 从定位到的页面抽取表格
python scripts/pdf_tools.py tables <pdf_path> <page_num>

# 或直接在表格中搜索
python scripts/pdf_tools.py search_table <pdf_path> "output voltage"
python scripts/pdf_tools.py search_table <pdf_path> "quiescent current"
```

**表格抽取后的 LLM 决策：**
1. 是不是正确的表？（核对表头行）
2. 哪一行是目标参数？（精确名称匹配，不要部分匹配）
3. 哪一列：Min / Typ / Max？（标称设计用 Typ，裕量分析用 Min/Max）
4. 有没有脚注？（脚注常含关键条件：温度范围、负载、频率）
5. 测试条件是什么？（查表格上方的行，或单独的 Test Conditions 列）

### 4b. 引脚描述

引脚描述表常跨多页。引脚章节的每一页都要读。

```bash
# 定位引脚章节起点
python scripts/pdf_tools.py search <pdf_path> "Pin Functions"

# 抽取该页的表格
python scripts/pdf_tools.py tables <pdf_path> <page_num>
# 对后续每页重复，直到引脚表结束（手动递增页码）
python scripts/pdf_tools.py tables <pdf_path> <next_page_num>
```

引脚图（所有 PDF 中都是图片）：
```bash
python scripts/pdf_tools.py render_page <pdf_path> <pinout_diagram_page> 200
```

### 4c. 时序图

**时序图几乎总是图片**，文本型 PDF 也不例外。绝不试图从文本抽取时序。

```bash
python scripts/pdf_tools.py render_page <pdf_path> <timing_page> 200
```

时序参数（setup/hold/脉宽）通常以表格形式配在图旁边：
```bash
python scripts/pdf_tools.py tables <pdf_path> <timing_page>
python scripts/pdf_tools.py nearby_text <pdf_path> <timing_page> "t[SHDWRCP]" 3
```

### 4d. 行内参数抽取

有些参数以行内文本出现而非表格（中文数据手册尤其常见）：

```bash
python scripts/pdf_tools.py nearby_text <pdf_path> <page_num> "output voltage" 2
python scripts/pdf_tools.py nearby_text <pdf_path> <page_num> "V[oO][uU][tT]\s*=?\s*[\d\.]+" 2
```

### 4e. 应用电路与框图

永远是图片。渲染并目视阅读：

```bash
python scripts/pdf_tools.py render_page <pdf_path> <page_num> 180
```

这些页面提供设计上下文：推荐外围元件、上电时序、PCB 布局要点。即使规格已抽完也不要跳过。

### 4f. 封装信息

```bash
python scripts/pdf_tools.py render_page <pdf_path> <package_page> 200
python scripts/pdf_tools.py tables <pdf_path> <package_page>  # 尺寸表
```

记录：封装类型、引脚数、裸露焊盘（如有）、Land pattern 参考。

---

## 器件类型抽取捷径

### 电源管理 IC（LDO、DC-DC、充电芯片）

优先级：
1. `search_table "output voltage"` → Vout 范围
2. `search_table "input voltage"` → Vin 范围
3. `search_table "quiescent"` 或 `"Iq"` → 待机电流
4. `search_table "efficiency"` → 但效率通常是**曲线** → `render_page`
5. `search_table "feedback voltage"` → Vfb（可调输出计算用）
6. 应用页 `nearby_text` → 示例电路中的 Rsense、Rfb 取值

**陷阱：** 充电 IC 有多个电流规格（预充、快充、终止）。完整充电状态机图必须 `render_page` 看。

### MCU / SoC

优先级：
1. `text page 1-2` → 内核架构、主频、Flash/RAM 容量
2. `search "Supply Voltage"` → VDD 范围
3. `search "I/O"` → GPIO 电压容忍（仅 3.3V 还是 5V tolerant）
4. `page_hints` 找寄存器章节 → 寄存器位图用 `render_page`
5. 外设电气规格（I2C、SPI、UART 时序）用 `tables`

**陷阱：** MCU 数据手册常把电气特性拆成单独文档。页数很少时可能只是简介 —— 确认是否有完整参考手册。

### 传感器（IMU、温度、压力）

优先级：
1. `search_table "sensitivity"` → 比例因子
2. `search_table "noise"` 或 `"noise density"` → 分辨率下限
3. `search_table "output data rate"` 或 `"ODR"` → 采样速度
4. `search_table "supply current"` → 工作与休眠电流
5. 有 `likely_curve_page` 提示的页 `render_page` → 噪声 vs ODR 曲线

**陷阱：** 灵敏度与量程绑定。±2g 量程下 1mg/LSB ≠ ±16g 量程下 1mg/LSB。量程-灵敏度必须成对抽取。

### 存储器（Flash、EEPROM、SRAM）

优先级：
1. `search_table "read"` → 读速度（MHz/ns）
2. `search_table "program"` 或 `"write"` → 每页/每字节写入时间
3. `search_table "erase"` → 扇区/块/整片擦除时间
4. `search_table "endurance"` → 擦写次数
5. `search_table "retention"` → 数据保持年限
6. 命令表页 `render_page`（老数据手册中常为图片）

### 接口 IC（USB、CAN、RS-485、Ethernet PHY）

优先级：
1. `search "data rate"` 或 `"bit rate"` → 最高速率
2. `search_table "propagation delay"` → 驱动器/接收器延迟
3. 时序图页 `render_page`
4. `search_table "input threshold"` → VOH/VOL、VIH/VIL
5. `search_table "bus capacitance"` → 驱动能力要求

---

## 错误恢复

### 预期表格中找不到参数

```
1. 换关键词再试 search_table：
   "SNR" → 也可试 "signal to noise"、"信噪比"
2. 在定位到的页面用 nearby_text 正则找
3. 确认参数是否在其他章节（规格可能拆在多页）
4. 全文 search
5. 确实不存在：输出 "NOT SPECIFIED IN DATASHEET"
```

### 表格抽取畸形/为空

```
1. 抽页面文本：pdf_tools.py text <pdf_path> <page>
2. 用 nearby_text 正则在文本中找值
3. render_page 目视读表
4. 标注抽取方式："Extracted from page text" 或 "Read from rendered image"
```

### 同一参数多个匹配

```
1. 确认是否一个在 "Absolute Maximum"（极限应力，非工作值）
2. 确认是否一个在 "Recommended Operating Conditions"（正常范围）
3. 电气特性表优先用于 typical/min/max 规格
4. 仍有歧义：把所有来源和不同值一起引用
```

---

## 图片型 PDF：完整工作流

```bash
# 1. 确认图片型
python scripts/pdf_tools.py info <pdf_path>
# → is_text_based: false

# 2. 渲染封面页
python scripts/pdf_tools.py render_page <pdf_path> 1 180
python scripts/pdf_tools.py render_page <pdf_path> 2 180

# 3. 目视阅读渲染图识别器件
# 交叉验证：图片中的型号 + 厂商必须与上下文一致

# 4. page_hints 预扫描（借助文本层检测，图片型 PDF 也可用）
python scripts/pdf_tools.py page_hints <pdf_path>

# 5. 渲染各章节候选页
python scripts/pdf_tools.py render_page <pdf_path> <page> 200

# 6. 从渲染图目视抽取规格
# 所有图片型抽取 → 置信度 LOW
# 交叉验证通过 → 置信度 MEDIUM
```

**图片型 PDF 的置信度：**

| 等级 | 条件 |
|-------|------------|
| `MEDIUM` | 交叉验证通过，渲染图中数值清晰可读 |
| `LOW` | 所有图片型抽取的默认值 |
| `UNVERIFIED` | 交叉验证失败（型号不一致） |
