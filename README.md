# Embedded_Skills

嵌入式开发相关 Claude Code / Codex skills 合集。每个 skill 是一个自包含文件夹，可单独下载使用。

## Skill 索引

| Skill | 功能 | 适用场景 |
|---|---|---|
| [schematic-pinmap-analyzer](skills/schematic-pinmap-analyzer/) | 把原理图 PDF/截图分析成嵌入式开发用功能引脚文件（电源架构、主控芯片、IO 分配表、驱动逻辑、待补充事项） | MCU/IoT/电机控制/传感器板等拿到原理图后要写固件的场景 |

## 安装某个 skill

先克隆仓库：

```powershell
git clone https://github.com/zglstudylinux/Embedded_Skills.git
cd Embedded_Skills
```

安装到 Claude Code（个人目录，全局可用）：

```powershell
$src = 'skills\schematic-pinmap-analyzer'
$dst = "$env:USERPROFILE\.claude\skills\schematic-pinmap-analyzer"
New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
Copy-Item -LiteralPath $src\* -Destination $dst -Recurse -Force
```

或安装到项目内（仅当前项目可用）：直接把 `skills\schematic-pinmap-analyzer` 文件夹拷到 `<project-root>\.claude\skills\` 下。

安装到 Codex：

```powershell
$src = 'skills\schematic-pinmap-analyzer'
$dst = "$env:USERPROFILE\.codex\skills\schematic-pinmap-analyzer"
New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
Copy-Item -LiteralPath $src\* -Destination $dst -Recurse -Force
```

重启会话后即可在对话中使用（例如：`使用 $schematic-pinmap-analyzer 分析这个原理图 PDF`）。

## 只下载单个 skill（不克隆整个仓库）

方式一：在线工具下载单个目录（download-directory）：

```text
https://download-directory.github.io/?url=https://github.com/zglstudylinux/Embedded_Skills/tree/main/skills/schematic-pinmap-analyzer
```

方式二：git sparse-checkout：

```powershell
git clone --filter=blob:none --no-checkout https://github.com/zglstudylinux/Embedded_Skills.git
cd Embedded_Skills
git sparse-checkout init --cone
git sparse-checkout set skills/schematic-pinmap-analyzer
git checkout main
```

## 目录结构

```text
Embedded_Skills/
├── README.md
├── LICENSE
└── skills/
    └── <skill-name>/     # 每个 skill 自包含：SKILL.md、README.md、references/、examples/ 等
```

## 添加新 skill 的约定

- 新 skill 一律放在 `skills/<skill-name>/`，`<skill-name>` 用 kebab-case，与 `SKILL.md` frontmatter 中的 `name` 保持一致
- skill 文件夹必须自包含（SKILL.md 为入口，references/、examples/ 随文件夹携带），保证单独拷出即可使用
- 新增后请同步更新上面的 Skill 索引表

## License

[MIT](LICENSE)
