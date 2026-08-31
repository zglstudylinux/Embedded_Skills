# 抽取模板

数据手册分析用抽取模板。每个模板定义必需的结构与校验规则。JSON 字段名为功能性标识，保留英文。

---

## 器件信息模板（Device Info）

```json
{
    "_template": "device_info",
    "_version": "1.0",
    "manufacturer": "",
    "part_number": "",
    "full_part_number": "",
    "description": "",
    "category": "",
    "package": {
        "type": "",
        "pin_count": 0,
        "dimensions": ""
    },
    "temperature_range": {
        "operating": {"min": "", "max": ""},
        "storage": {"min": "", "max": ""}
    },
    "source": {
        "cover_page": 1,
        "pin_config_page": 0,
        "specs_page": 0
    }
}
```

**校验规则：**
- `package.pin_count` 必须与 `package.type` 中的数字一致
- 示例：`QFN-32` → `pin_count: 32`
- 抽取完成后必须填齐所有来源页码

---

## 电源域模板（Power Domains）

```json
{
    "_template": "power_domains",
    "_version": "1.0",
    "power_domains": [
        {
            "name": "",
            "pin_names": [],
            "min_voltage": "",
            "typ_voltage": "",
            "max_voltage": "",
            "current_typ": "",
            "purpose": "",
            "decoupling": ""
        }
    ],
    "ground_pins": [],
    "source_page": 0
}
```

**抽取规则：**
- 必须从引脚描述表抽取**全部**电源引脚
- 不是举例 —— 列出所有引脚及脚号
- 错误写法：`"VDD"`
- 正确写法：`"VDD (pins 1, 13, 32, 48)"`
- 检查特殊电源域：CPVDD、HPVDD、PLLVDD 等

---

## I2C 接口模板

```json
{
    "_template": "i2c_interface",
    "_version": "1.0",
    "interface_type": "I2C",
    "pins": {
        "scl": "",
        "sda": ""
    },
    "address": {
        "format_shown": "",
        "format_explanation": "",
        "address_7bit": [],
        "address_8bit_write": [],
        "address_8bit_read": [],
        "calculation_steps": ""
    },
    "max_speed": "",
    "pull_up_required": true,
    "source_page": 0
}
```

**I2C 地址计算指南：**

| 手册中的格式 | 示例 | 计算 | 7 位地址 |
|---------------------|---------|-------------|---------------|
| `001000x` | x=AD0 | 0b0010000=0x10, 0b0010001=0x11 | 0x10/0x11 |
| `11010xx` | xx=A1A0 | 0b1101000=0x68 到 0b1101011=0x6B | 0x68-0x6B |
| `0x20`（8 位写地址） | - | 0x20 >> 1 | 0x10 |
| `0xD0`（8 位写地址） | - | 0xD0 >> 1 | 0x68 |

**地址计算示例：**
```json
{
    "format_shown": "001000x",
    "format_explanation": "其中 x 等于 AD0 引脚电平",
    "address_7bit": ["0x10", "0x11"],
    "calculation_steps": [
        "AD0 = 0: 0010000 二进制 = 0x10",
        "AD0 = 1: 0010001 二进制 = 0x11"
    ]
}
```

**常见 I2C 器件地址**（校验参考 —— 用于与抽取到的地址交叉核对；未在 PDF 中核实前不得作为事实输出）：

| 器件类型 | 常见地址 |
|-------------|------------------|
| I2C EEPROM (24Cxx) | 0x50-0x57 |
| I2C RTC (DS3231, PCF8563) | 0x51, 0x68 |
| I2C 温度传感器 (LM75) | 0x48-0x4F |
| I2C ADC (ADS1115) | 0x48-0x4B |
| I2C IMU (MPU6050) | 0x68-0x69 |
| I2C IO 扩展 (MCP23017) | 0x20-0x27 |

---

## SPI 接口模板

```json
{
    "_template": "spi_interface",
    "_version": "1.0",
    "interface_type": "SPI",
    "pins": {
        "mosi": "",
        "miso": "",
        "sck": "",
        "cs": ""
    },
    "modes_supported": [],
    "max_speed": "",
    "source_page": 0
}
```

---

## 电气规格模板（Electrical Specs）

```json
{
    "_template": "electrical_specs",
    "_version": "1.0",
    "absolute_maximum": [
        {
            "parameter": "",
            "min": "",
            "max": "",
            "unit": "",
            "notes": "",
            "source": ""
        }
    ],
    "recommended_operating": [
        {
            "parameter": "",
            "min": "",
            "typ": "",
            "max": "",
            "unit": "",
            "conditions": "",
            "source": ""
        }
    ],
    "key_parameters": [
        {
            "parameter": "",
            "min": "",
            "typ": "",
            "max": "",
            "unit": "",
            "conditions": "",
            "footnotes": [],
            "source": ""
        }
    ]
}
```

**抽取规则：**
- 原样抽取数值，不做变换
- 注明列名（Min/Typ/Max）
- 记录测试条件
- 检查脚注（常含关键约束）
- 标注来源：页码和表名

---

## 原始抽取值格式

每个抽取值必须附带来源信息：

```json
{
    "parameter": "DAC SNR",
    "value": "93",
    "unit": "dB",
    "column": "Typ",
    "min": "85",
    "max": "95",
    "conditions": "A-weighted, 24-bit",
    "page": 8,
    "table_name": "DAC Performance",
    "confidence": "HIGH"
}
```

**置信度等级：**

| 等级 | 定义 | 示例 |
|-------|------------|---------|
| **HIGH** | 从清晰的表格直接读取，并经复读核验 | 从干净表格读出 "93 dB" |
| **MEDIUM** | 存在歧义（OCR 问题、合并单元格） | 略微模糊的 OCR 值 |
| **LOW** | 由上下文推断，存在多种解读 | 从曲线图估读的值 |
| **UNVERIFIED** | 已抽取但尚未核验 | 校验前的初始抽取值 |
