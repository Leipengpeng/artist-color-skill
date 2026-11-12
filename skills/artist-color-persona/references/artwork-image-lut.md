# 画作双图调色与 LUT

默认路线中，所选真实画作是视觉参考，Image 返回是 LUT 拟合目标，原尺寸相机照片是最终应用对象。三者不能互换。豆包另见 [执行说明](doubao-workflow.md)。

## 执行条件与路径

需要可查看照片与真画、同次双图编辑并保存实际返回的图像工具，以及能运行 Python 和交付文件的环境。脚本本身不调用生图 API，也不会给宿主增加 Image 能力。

以 Skill 文件夹作为工作目录，该目录直接有 `SKILL.md`、`scripts/`、`assets/`。下面命令均从这里运行；按实际环境使用 `python`、`python3` 或已有解释器，不照抄另一台电脑的路径。缺少依赖时：

```sh
python -m pip install -r scripts/requirements.txt
```

不确定参数时查看脚本的 `--help`。示例输入路径必须换成实际存在的附件文件。

## 取得真实作品文件

公开版保留十位艺术家、80 条作品元数据，只随包分发已确认许可的图片。缺图片与缺角色是不同状态。先读列表：

```sh
python scripts/artwork_library.py list --artist monet_giverny_late
python scripts/artwork_library.py check
```

确认所选作品准确的 `file` 名、来源和图像状态。以下 `FILE` 替换成那条记录的文件名：

```sh
python scripts/artwork_library.py fetch --artist monet_giverny_late --file FILE
```

`fetch` 从清单公开 URL 获取文件，做 HTTP、图像和哈希核验，存到私有缓存；读取实际输出路径再查看图像。公开可访问不等于允许再分发，缓存不要加入公开仓库。它不绕过登录或访问限制。来源不可取、返回网页或 PDF、校验失败时保留错误，改用用户提供的合法可用单幅真画导入：

```sh
python scripts/artwork_library.py import --artist monet_giverny_late --file FILE --image "输入/用户提供的真实画作.jpg"
```

`download-open --artist ID` 只处理清单明确符合开放下载条件的条目，不是把全部研究图公开打包的命令。PDF 封面或整页不能直接当图二，需提供清楚的单幅作品。下载／导入成功本身不证明作者和作品身份，实际使用前仍需查看核对。

用户指定参考画可直接使用其文件并记录已有来源；信息不足则记“用户提供的参考图”，不编造作者、标题和年份，不用生成图补齐真迹。

## 准备任务

每次为一张原片、一位艺术家、一幅真画创建新任务目录。示例中的参数替换为实际值：

```sh
python scripts/artwork_image_lut.py prepare --content "输入/原片.jpg" --artwork "输入/真实作品.jpg" --artist monet_giverny_late --title "作品准确标题" --reason "原片现有关系与这幅画的具体关联" --source "作品来源URL或用户提供文件" --output "任务/照片01-莫奈-T0"
```

成功后应有 `job.json`、`content.jpg`、`artwork-reference.png`、真实作品归档文件、`prompt.txt`。读取 `job.json` 确认：

- `original.path` 是本次相机照片，`artwork` 是所选真实作品。
- `image_inputs` 恰有两条实际存在的输入路径，按原片上传图、真实画作上传图排序。
- `prompt.path` 指向本次提示词，上传文件和作品归档有哈希记录。

默认两图分别保留宽高比、最长边 720，完整原片另行保存；不要覆盖相机原图。生成返回尺寸由宿主决定，保留原生文件，不把人为放大当模型原生输出。

## 在宿主中调用 Image

先查看两张实际输入图，再通过宿主提供的**同一次双图编辑**提交 `image_inputs`。工具名和参数按实际接口，不能把 Codex 参数假设为豆包参数。Codex 内置编辑工具支持本地引用时可使用 `referenced_image_paths`，其它宿主使用其等价双图方式。

发送 `prompt.txt` 原文：

```text
Image 1 is the content photo. Image 2 is the color reference. Match the colors of Image 1 to Image 2.
```

不加人物对白、生平、预写解释、长篇“稳定／自然／保真”约束，不因局部颜色强烈而自动减弱。两图不能拆成彼此无关联的两次生成。记录实际输入、提示词和返回文件；工具确实成功并给出可保存图像才记为生成完成。

实际返回另存为新文件，保留工具原始文件；查看颜色变化和可能的重绘。原片、参考画或其它版本不能冒充本次返回。

## 从实际返回拟合 LUT

```sh
python scripts/artwork_image_lut.py finish --job "任务/照片01-莫奈-T0/job.json" --styled "生成结果/本次实际返回.png"
```

脚本核对输入与提示词、归档 Image，用原片上传图和实际返回做 MKL/Oklab 全局颜色拟合，保存 `.cube`，重读该 LUT 并应用到转正后的原尺寸照片。亚当斯角色使用黑白作品并导出中性黑白 LUT；若实际生成带色，如实区分彩色样稿与中性黑白成片。

完成后读取 `result.json`，确认 `image_return.path`、`lut.path`、`render.path` 指向存在且可打开的文件；核对 `render.size` 与原片转正尺寸。不能因为命令“似乎运行了”就编造链接或称为完成。

`geometry` 辅助检查结构差异，**不是美学分数**。当前拟合使用整体颜色统计；Image 新增的云、笔触、物件和局部独立染色不能由全局 LUT 保证复现。几何失败时保留实际返回并说明差异，不偷偷换图。鲜艳、明显色偏、局部浓色可以保留，不单独视为失败。

LUT 重读回放一致性只验证该 LUT 与导出照片一致，不代表 LUT 与 Image 逐像素相同。PSNR、SSIM 或其它数值只有实际计算过才报告，也不能冒充人工美学评价。

## 后置人物解释与交付

最终 LUT 图已生成、查看后，读 [voice.md](voice.md)。将 `persona_input`、实际文件和拟合记录交给角色，解释本次成片，不声称角色事先把这些理由交给 Image。

展示顺序：00 原片、01 真实参考画、02 Image 生成效果、03 原尺寸 LUT 成片、04 对应 `.cube`。用以下命令复制有序交付文件，保留原任务记录：

```sh
python scripts/export_delivery.py --job "任务/照片01-莫奈-T0/job.json" --output "交付/照片01-莫奈"
```

成功应产生五个有序文件和 `delivery.json`。脚本核对输入哈希，不覆盖内容不同的既有交付。后置人物说明单独附在交付目录，另给作品出处、实际提示词和对应成片。

比较任务每位各建目录，例如 `照片01-莫奈-T0` 与 `照片01-梵高-T0`；原片字节相同，真实画作、Image、LUT 分别保存，全部完成后才写对话。

## 中断与失败处理

| 已有状态或错误 | 下一步及可交付内容 |
| --- | --- |
| 原片或作品无法查看 | 取得实际图，保留已有选择记录；明确缺哪张，不凭文件名假装识图。 |
| 作品未随包附带 | 从清单 `fetch` 或导入真画，检查实际文件；不自动删除此角色。 |
| 已有 `job.json`，未生成 | 核对当前原片、作品与提示词后继续双图编辑；不重复 `prepare` 覆盖目录。可交付准备文件。 |
| 只支持单图或只有文字返回 | 停在准备阶段，说明缺真实双图能力，不用单图冒充本路线。 |
| 可见 Image 无法保存 | 取得实际文件后再拟合；目前只称可见样稿，不用截图或自造图冒充原返回。 |
| 有实际 Image，未拟合 | 对原 `job.json` 使用这个返回执行 `finish`。可交付前三张图。 |
| 缺 Python、依赖或写权限 | 在可用环境补齐，或交付已有文件与命令，明确 LUT 未完成。 |
| 哈希、输入或已有结果不匹配 | 不绕过核验、改记录伪造一致。核对文件；更换输入或返回时建新目录。 |
| 已有 `result.json` | 核对实际文件；完整则继续解读，不再生成同一版。缺失或损坏则记录并恢复相应步骤。 |

修正一次明确的路径、格式或依赖问题后再继续；同一外部访问或宿主能力错误重复出现时保存状态并说明缺少条件，不无限重试。直接统计追色、纯生图或文字解释不能冒充默认完整路线。
