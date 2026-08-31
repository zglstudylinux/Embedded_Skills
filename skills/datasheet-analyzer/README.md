# EE 数据手册解析大师（EE Datasheet Master）

一个从电子元器件数据手册中抽取规格并完整标注来源的 skill。所有数据必须源自 PDF —— 不用先验知识、不做猜测。

## 支持的器件类型

电源管理 · MCU/SoC · ADC/DAC/CODEC · 传感器（IMU、温度、压力） · Flash/EEPROM · 接口（USB、Ethernet、CAN、RS-485） · 分立器件（MOSFET、二极管、门逻辑） · 时钟/PLL · IO 扩展 · 电池充电/电量计

针对英文和中文数据手册优化。其他语言准确率会下降。

---

## 工作流总览

```
Phase 0   → page_hints（全部页面，默认 patterns） → 粗粒度结构地图
Phase 1   → info                                       → text vs image PDF
Phase 2   → text page 1-2                             → 器件识别 + 参数推断
Phase 2b  → page_hints --patterns（推断的关键词）      → 细粒度章节地图
Phase 3   → search_caption + search                    → 确认页码
Phase 4   → tables / search_table / nearby_text        → 抽取数值
           render_page                                 → 时序图/框图页
```

完整工作流与决策规则见 [PDF_STRATEGY.md](PDF_STRATEGY.md)。

---

## 依赖

`scripts/pdf_tools.py` 需要以下 Python 包：

```bash
pip install -r scripts/requirements.txt
```

| 包 | 作用 | 是否必需 |
|---------|------|-----------|
| `pymupdf` | 主 PDF 引擎：文本、表格、页面渲染、CID 字体处理 | **是** |
| `pdfplumber` | 边缘案例兜底 | **是** |
| `pypdfium2` | 页面渲染兜底（`render_page`） | **是** |

### 为什么选 pymupdf？

pymupdf (MuPDF) 作为主引擎，因为：
- **支持 CID 编码字体** —— 部分数据手册使用 pdfplumber 无法解码的自定义字体编码
- **性能更快** —— MuPDF 引擎高度优化
- **API 统一** —— 文本、表格、渲染一个包搞定
- **覆盖面广** —— 已在 101 份数据手册上测试，文本抽取成功率 100%

---

## 工具（`scripts/pdf_tools.py`）

| 命令 | 用途 |
|---------|---------|
| `info` | 页数、text vs image 检测 |
| `page_hints [page] [--patterns json]` | 每页结构信号 + 启发式章节标签 |
| `page_stats [page]` | 原始指标：字符/单词/图片/矩形/线条/曲线/表格计数 |
| `dump_patterns` | 打印默认 patterns JSON（`--patterns` 定制的基础） |
| `text <page>` | 抽取某页文本 |
| `search <keyword>` | 跨全部页面带上下文查找关键词 |
| `search_caption [keyword]` | 查找 Figure/Table 标题（中英文） |
| `nearby_text <page> <regex>` | 正则匹配并带上下文行 |
| `tables <page>` | 抽取某页全部表格 |
| `search_table <keyword>` | 查找包含关键词的表格行 |
| `toc` | 抽取目录（如有） |
| `render_page <page> [dpi] [out]` | 页面渲染为 PNG（pymupdf → pypdfium2 兜底） |

### `--patterns` 用法

`page_hints --patterns` 接受自定义 JSON，会**替换**默认 pattern 集。用于器件识别后的定向二次扫描：

1. `dump_patterns > /tmp/p.json` —— 获取默认集作为基础
2. 参照 Features 列表中的专有术语新增器件专属标签（如 `"VINDPM"`、`"clock tree"`、`"DMA controller"`）
3. 重跑 `page_hints --patterns /tmp/p.json` 定位领域专属章节

pattern 应该是**章节标题短语或专有特性名**，不是泛用词。好：`"charge state machine"`。坏：`"charge"`。

---

## 已知限制

### CID 编码字体
部分数据手册使用 CID（Character ID）字体编码，字符映射为数字 ID 而非 Unicode。pymupdf 能自动处理，但极老或非标准编码仍可能产生部分乱码。检查 `info` 输出中的 `cid_ratio` 警告。

### 图片型 PDF
当 `is_text_based: false` 时，文本抽取完全失效。用 `render_page` 将页面渲染为 PNG 并目视阅读。**必须交叉验证**：渲染图中的厂商 + 型号必须与上下文一致。不一致 → 输出 `UNABLE TO VERIFY`。图片型 PDF 的所有抽取默认 `LOW` 置信度。

### 复杂表格结构
合并单元格、多行表头、旋转文本可能抽取错误。兜底：用 `text` 取页面文本，或 `render_page` 目视阅读。注明 "Extracted from page text / rendered image"。

### 图表数据
特性曲线上的数值无法精确抽取。找随附的数据表。没有则注明 "Approximate — read from curve"（近似值，读自曲线）。

### 多型号数据手册
覆盖产品家族的数据手册（如 STM32F103C**x**T6）可能有型号专属表格。务必确认适用列对应的型号。

### `page_hints` 误报
提示是启发式的。`"sequence"`、`"efficiency"` 之类的泛用词会在很多页面命中。`score` + `reasons` 要一起看 —— 单条低分命中不可靠。用 `search_caption` 或 `search` 交叉确认。

---

## 本 skill 不能做的事

| 任务 | 原因 |
|------|--------|
| 保证 100% 准确 | LLM 抽取存在固有局限 |
| 解密带密码的 PDF | 不支持 |
| 抽取 3D 模型 / CAD 数据 | 仅支持文本和表格 |
| 分析电路行为 | 只抽取元件值，不做仿真 |
| 读取非文本矢量图形 | 渲染页面后目视阅读 |

---

## 文件参考

| 文件 | 用途 |
|------|---------|
| `SKILL.md` | skill 触发规则、铁律、快速参考 |
| `PDF_STRATEGY.md` | 完整 6 阶段工作流、决策树、器件类型捷径 |
| `TEMPLATES.md` | JSON 抽取模板（器件信息、电源域、I2C、电气规格） |
| `scripts/pdf_tools.py` | PDF 抽取工具 —— 全部命令见上表 |
