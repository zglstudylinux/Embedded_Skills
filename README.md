# Embedded_Skills

嵌入式开发相关 Claude Code / Codex skills 合集。每个 skill 是一个自包含文件夹，可单独下载使用。

## Skill 索引

| Skill | 功能 | 适用场景 |
|---|---|---|
| [schematic-pinmap-analyzer](skills/schematic-pinmap-analyzer/) | 把原理图 PDF/截图分析成嵌入式开发用功能引脚文件（电源架构、主控芯片、IO 分配表、驱动逻辑、待补充事项），输出与原理图同目录同名 `.md` | MCU/IoT/电机控制/传感器板等拿到原理图后要写固件的场景 |
| [datasheet-analyzer](skills/datasheet-analyzer/) | 从元器件数据手册 PDF 中抽取带页码来源的芯片参数（引脚、电压、时序、电气特性、I2C 地址等），分析结果写入与 PDF 同目录同名 `.md`；仅信 PDF 内容，缺失参数标注 `NOT SPECIFIED IN DATASHEET` 并给出获取途径 | 阅读数据手册查参数、选型对比、写驱动前收集电气规格 |
| [chip-resource-finder](skills/chip-resource-finder/) | 根据芯片型号联网检索官方开发资源（datasheet、参考手册、SDK、例程、烧录工具、开发板资料），生成分级别的 HTML 资源报告（硬件/软件/烧录三张表 + 最小下载集 + 风险项） | 拿到一颗新芯片，需要快速找齐官方资料并甄别来源可靠性 |
| [chip-driver-manual](skills/chip-driver-manual/) | 从 datasheet/参考手册/SDK 示例/寄存器头文件中提取并交叉核验驱动开发事实（协议细节、地址、寄存器表、命令集、时序、初始化序列），支持事实提取、驱动代码生成与驱动审查三类任务 | 读芯片手册写驱动、审查驱动正确性、新片 bring-up |

## 协作流水线

这几个 skill 可以串成一条「从图纸/型号到驱动」的闭环：

```text
chip-resource-finder（找齐官方资料）
        │
        ▼
datasheet-analyzer（解析 datasheet，输出带来源的参数文档）
        │
        ▼
schematic-pinmap-analyzer（解析原理图，输出功能引脚文件）
        │
        ▼
chip-driver-manual（提取驱动事实 → 生成/审查驱动代码）
```

每个 skill 也可独立使用，互不依赖。

## 安装某个 skill

先克隆仓库：

```powershell
git clone https://github.com/zglstudylinux/Embedded_Skills.git
cd Embedded_Skills
```

安装到 Claude Code（个人目录，全局可用）：

```powershell
$src = 'skills\<skill-name>'
$dst = "$env:USERPROFILE\.claude\skills\<skill-name>"
New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
Copy-Item -LiteralPath $src\* -Destination $dst -Recurse -Force
```

或安装到项目内（仅当前项目可用）：直接把 `skills\<skill-name>` 文件夹拷到 `<project-root>\.claude\skills\` 下。

安装到 Codex：

```powershell
$src = 'skills\<skill-name>'
$dst = "$env:USERPROFILE\.codex\skills\<skill-name>"
New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
Copy-Item -LiteralPath $src\* -Destination $dst -Recurse -Force
```

重启会话后即可在对话中使用（例如：`使用 $schematic-pinmap-analyzer 分析这个原理图 PDF`）。

## 只下载单个 skill（不克隆整个仓库）

方式一：在线工具下载单个目录（download-directory）：

```text
https://download-directory.github.io/?url=https://github.com/zglstudylinux/Embedded_Skills/tree/main/skills/<skill-name>
```

方式二：git sparse-checkout：

```powershell
git clone --filter=blob:none --no-checkout https://github.com/zglstudylinux/Embedded_Skills.git
cd Embedded_Skills
git sparse-checkout init --cone
git sparse-checkout set skills/<skill-name>
git checkout main
```

## 目录结构

```text
Embedded_Skills/
├── README.md
├── LICENSE
└── skills/
    └── <skill-name>/     # 每个 skill 自包含：SKILL.md、README.md、references/、examples/、scripts/ 等
```

## 添加新 skill 的约定

- 新 skill 一律放在 `skills/<skill-name>/`，`<skill-name>` 用 kebab-case，与 `SKILL.md` frontmatter 中的 `name` 保持一致
- skill 文件夹必须自包含（SKILL.md 为入口，references/、examples/、scripts/ 随文件夹携带），保证单独拷出即可使用
- 有 Python 依赖的 skill 需提供 `scripts/requirements.txt`，并在 SKILL.md frontmatter 声明 `compatibility: Requires python3 and the Python packages listed in scripts/requirements.txt.`
- 面向中文使用者，新增 skill 文档请使用中文；命令名、代码标识等保持英文
- 新增后请同步更新上面的 Skill 索引表

## License

[MIT](LICENSE)
