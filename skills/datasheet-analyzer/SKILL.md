---
name: datasheet-analyzer
description: "当用户正在阅读或需要解析元器件数据手册/规格书（datasheet、spec sheet、PDF）以查找芯片参数时使用：引脚定义 pinout、电压、I2C 地址、时序 timing、寄存器映射 register map、电气特性 electrical characteristics。适用于 PDF+芯片参数类问题，覆盖所有 IC 类型。关键词：规格书、数据手册、芯片参数、datasheet。"
compatibility: Requires python3 and the Python packages listed in scripts/requirements.txt.
---

# EE 数据手册解析大师（EE Datasheet Master）

## 使用说明

### 第 1 步：确认输入与环境

使用 `scripts/pdf_tools.py` 前必须确认：

- 提供了有效的 PDF 路径
- 已安装 `python3`
- 已安装 `scripts/pdf_tools.py` 所需的 Python 包

如缺少依赖或输入：

- 在宣称该 skill 可用于本任务之前先停止
- 明确说明缺少什么
- 告知用户 skill 可能已安装，但在补齐该条件前当前任务被阻塞

### 第 2 步：遵守「仅限 PDF」抽取规则

所有事实性输出必须来自 PDF 本身。如果 PDF 无法提供答案，返回 `NOT SPECIFIED IN DATASHEET`，并说明获取该信息的最直接途径。

### 第 3 步：将分析结果写入 Markdown 文件（必须）

每次分析都必须以交付文件结束，而不只是对话回复：

- 将最终分析结果（遵循下文 Output Format）写入一个 `.md` 文件，位置与 PDF **同一目录**，文件名与 PDF **同名**：`XX.pdf → XX.md`（例如 `DHT11_ASAIR.pdf → DHT11_ASAIR.md`）。
- 如同名 `.md` 文件已存在，用本次最新分析覆盖。
- 写完文件后，删除分析过程中产生的临时渲染图（例如 `render_page` 输出到临时目录的 PNG）。临时渲染图不作为交付物保留。
- 同时在对话中给出简短总结和文件路径，方便用户直接打开文档。

## 铁律：只信 PDF 内容

```
所有数据必须源自 PDF。
允许：抽取 → 基于已抽取数据计算
禁止：凭先验知识 → 用猜测填补空缺
```

### 允许的推导

| 类型 | 示例 |
|------|------|
| 数学计算 | 由电压电流计算 P = V × I |
| 单位换算 | dBm → mW，二进制 → 十六进制 |
| 地址计算 | "001000x" → 0x10/0x11 |
| 计数 | 从引脚描述表统计引脚数量 |

**推导时必须给出：来源数据（页码）+ 计算步骤 + 结果**

### 禁止行为

| 行为 | 修正 |
|----------|------------|
| "我了解这个芯片……" | 去 PDF 里查 |
| "典型值一般是……" | 从 PDF 读实际值 |
| "类似芯片是……" | 本芯片可能不同 |
| 用猜测填补空缺 | 输出 `NOT SPECIFIED IN DATASHEET` + 获取途径（见下文） |

---

## 当 PDF 无法提供答案时

`NOT SPECIFIED IN DATASHEET` 不是死路。必须紧跟**如何获取缺失信息**。

### 回复模板

> "[参数] 在本数据手册中未规定（NOT SPECIFIED IN DATASHEET）。
> 获取途径：[具体方法如下]。"

如果数据手册按名称引用了应用笔记或补充文档，需引用它：
> "第 X 节引用了应用笔记 [AN-xxx] 讲解该主题 —— 请在[厂商]官网搜索。"

### 缺失参数的推理框架

参数缺失时，依次思考以下问题，给出具体可执行的路径：

**1. 为什么缺失？**
- *文档不对* —— 这是产品简介/数据手册；完整参考手册或应用笔记里才有 → 说出正确文档的名称
- *测试条件不匹配* —— 规格存在但不是用户所需条件（负载、频率、温度）→ 说明条件差异及对数值的影响
- *依赖应用场景* —— 数值取决于用户掌控的外围元件或 PCB 布局 → 说明由什么决定、如何计算或仿真
- *厂商掌握* —— 数据来自 Qualification 测试，未公开 → 指出正确的联系渠道

**2. 用户要它做什么？**
- 设计裕量校核 → 近似值或最坏情况上界可能就够
- 故障调试 → 在实际电路中直接测量比手册值更可靠
- 认证/合规 → 只有厂商提供的数据可接受

**3. 综合以上，最直接的路径是什么？**
针对具体参数和场景给出建议：密闭高温环境里 LDO 的热阻问题，与信号链运放的同一问题，答案路径完全不同。思考：什么设备能测到它、什么文档包含它、或什么公式能从用户可测/可控的量推导出来。

## 6 阶段工作流

```
┌─────────────────────────────────────────────────────────────┐
│  Phase 0: 预扫描          →  全文扫描，建结构地图            │
│  Phase 1: 诊断            →  text vs image PDF 决策         │
│  Phase 2: 器件识别        →  确认器件，推断关键参数          │
│  Phase 2b: 定向重扫       →  推断 patterns，二次精准扫描     │
│  Phase 3: 章节映射        →  定位各功能区页码               │
│  Phase 4: 定向抽取        →  精准提取 + TEMPLATES 结构化输出 │
└─────────────────────────────────────────────────────────────┘
```

**详见 [PDF_STRATEGY.md](PDF_STRATEGY.md) 的入口决策表与详细工作流。先读那个文件 —— 它告诉你在运行任何命令之前从哪个阶段开始。**

### 快速参考

**最常见场景 —— 已知器件、只问 1~2 个具体参数（从这里开始）：**
```bash
# Phase 3: 直接搜索用户问的参数
python scripts/pdf_tools.py search_table <pdf_path> "<parameter>"   # 例如 "quiescent current"、"dropout voltage"
python scripts/pdf_tools.py search <pdf_path> "<parameter>"         # 第一次没结果就换措辞再试

# Phase 4: 读取定位到的页面
python scripts/pdf_tools.py text <pdf_path> <page_num>
python scripts/pdf_tools.py tables <pdf_path> <page_num>
```

**较少见 —— 未知 PDF、开放式分析、复杂多参数抽取：**
```bash
# Phase 0: 预扫描（较慢 —— 只在需要结构地图时使用）
python scripts/pdf_tools.py info <pdf_path>
python scripts/pdf_tools.py page_hints <pdf_path>        # 扫描全部页面 → 大文档需数分钟

# Phase 2: 识别器件（仅在器件未知时）
python scripts/pdf_tools.py text <pdf_path> 1

# Phase 2b: 定向重扫（仅复杂 IC —— 充电芯片、MCU、CODEC）
python scripts/pdf_tools.py dump_patterns > /tmp/custom_patterns.json
python scripts/pdf_tools.py page_hints <pdf_path> --patterns /tmp/custom_patterns.json

# Phase 3: 基于标题的章节映射
python scripts/pdf_tools.py search_caption <pdf_path>    # 查找 Figure/Table 标题
python scripts/pdf_tools.py search <pdf_path> "Electrical Characteristics"
```

---

## 参数推断（LLM 决策）

### 通用参数（仅完整分析类查询需要）

当用户要求完整分析或总览时，提取以下 5 项基线参数。**单参数定向查询跳过此表** —— 用户问 "dropout voltage 是多少"，就去查那个，不用管封装外形。

| 参数 | 搜索关键词 | 备注 |
|-----------|----------------|-------|
| **厂商** | 首页页眉/页脚 | 公司名称 |
| **型号** | 首页标题 | 完整型号 |
| **封装** | "Package"、"封装" | 必须含引脚数（如 QFN-32） |
| **工作电压** | "VDD"、"VCC"、"Supply Voltage"、"电源电压" | 范围：min 到 max |
| **工作温度** | "Operating Temperature"、"工作温度" | 范围：min 到 max |

### 器件专属参数（由 LLM 推断）

识别器件后，推断哪些规格重要：

```
1. 读器件描述（前 3 页）
2. 理解：这个器件是干什么的？
3. 推断：哪些规格对它重要？
4. 搜索：用 pdf_tools 定位这些规格
```

完整的「器件类型 → 关键规格」对照表和各器件抽取捷径见 **[PDF_STRATEGY.md → Phase 2 与器件类型捷径](PDF_STRATEGY.md)**。

**核心思想：** 器件描述告诉你该测什么。不要套用固定清单。

---

## 输出格式

最终分析必须保存为 PDF 旁边的 `.md` 文件（`XX.pdf → XX.md`，见第 3 步）。文档严格使用以下结构：

```markdown
# [Part Number] Datasheet Analysis

## Summary
[1-2 句]

## Key Specifications
| Parameter | Min | Typ | Max | Unit | Source | Notes |
|-----------|-----|-----|-----|------|--------|-------|
| ... | ... | ... | ... | ... | Page X, "Table Name" | |
| [无法获得的参数] | — | — | — | ... | NOT SPECIFIED | Measure: [方法] |

## Pin Configuration
- Package: [类型]-[引脚数]
- Power Domains: [列出全部电源域及引脚号]
- Interfaces: [I2C/SPI/UART 及地址]

## Critical Design Considerations
1. [问题 + 指导]

## Common Pitfalls
- [坑]：[如何避免]
```

---

## 常见错误

| 错误 | 示例 | 修正 |
|---------|---------|------------|
| 缺引脚数 | "QFN package" | "QFN-32 package" |
| 电源域不全 | 只写 "VDD" | "VDD (pins 1, 13, 32)" |
| I2C 地址算错 | "0x18" | 展示由位格式推算的过程 |
| 缺来源 | "SNR: 93 dB" | "SNR: 93 dB (Page 8, Typ)" |
| 编造规格 | 任何无来源的值 | 一律标注页码和表名 |

---

## 故障排查

错误：`ModuleNotFoundError: fitz` 或 `No module named 'pdfplumber'`
原因：Python 依赖未安装。
解决：先运行 `pip install -r scripts/requirements.txt` 再继续。

错误：`File not found` 或 PDF 路径不存在
原因：未提供 PDF 或路径写错。
解决：让用户提供确切的 PDF 路径。不要凭记忆或网络常识回答。

错误：`is_text_based: false` 或抽取文本乱码
原因：PDF 是图片型，或字体编码异常。
解决：用 `render_page` 渲染页面、目视阅读，并降低置信度。若无法从渲染页确认厂商或型号，输出 `UNABLE TO VERIFY`。

错误：目标参数不在数据手册中
原因：该文档确实没有，或提供的文档不对。
解决：返回 `NOT SPECIFIED IN DATASHEET` 并给出最直接的获取途径。

错误：工具命令持续失败
原因：Python 环境损坏、PDF 边缘案例或文件损坏。
解决：报告失败的命令，并归类为依赖问题、文件完整性问题或抽取质量问题。不得把猜测当抽取事实呈现。

---

## 红灯信号 —— 停下来核实

如果你冒出以下念头：
- "我了解这个芯片……"
- "这个值一般是……"
- "凭我的经验……"
- "类似芯片都是……"

**停下 → 重读 PDF → 从源头抽取**

---

## 参考文件

| 文件 | 用途 |
|------|------|
| [PDF_STRATEGY.md](PDF_STRATEGY.md) | 6 阶段工作流、器件类型抽取捷径 |
| [TEMPLATES.md](TEMPLATES.md) | 结构化输出模板：device_info、power_domains、I2C、SPI、electrical_specs |
| [scripts/pdf_tools.py](scripts/pdf_tools.py) | PDF 抽取工具 |
