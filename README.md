# 艺术家调色 Skill

上传照片，从十位艺术家中选择一位及其一幅真实作品，将两张图交给宿主图像编辑工具追色，再导出原尺寸照片和 3D LUT。调色完成后，由艺术家角色用第一人称解释成片与相关创作理念。

**流程：照片 → 艺术家 → 真实参考作品 → Image 双图追色 → LUT → 成片后解读。**

支持莫奈、梵高、马蒂斯、高更、霍普、罗斯科、亚当斯、莫兰迪、塞尚和夏加尔。可以自动选择，也可以点名；同图比较时，每位独立选画和拟合。

## 安装与使用

- **豆包等支持上传技能包的宿主**：下载 [豆包安装包](dist/artist-color-persona-doubao-v1.0.0.zip)，按宿主提供的技能导入方式安装、启用，再上传照片。具体操作和能力要求见[豆包执行说明](skills/artist-color-persona/references/doubao-workflow.md)。不同版本可能没有同样的工具能力；本次发布未新增豆包实机试跑。
- **Codex 等支持目录技能的宿主**：将 [artist-color-persona](skills/artist-color-persona) 文件夹安装到个人技能目录，调用 `$artist-color-persona` 并附照片。也可下载 [目录安装包](dist/artist-color-persona-v1.0.0.zip)。
- **本地 Python**：Python 3.10+，运行 `python -m pip install -r skills/artist-color-persona/scripts/requirements.txt`。技能中的图像编辑由宿主执行，本仓库不提供图像模型 API 密钥、模型服务或任意平台的工具权限。

示例：

> 给这张照片选一位合适的艺术家。用他的真实作品做参考，完成双图调色和 LUT，再解释这次配色。

> 同一张照片，请莫奈和梵高各做一版。分别展示原片、真实参考画、Image 返回和 LUT 成片，再比较两位的理念。

## 给执行能力较弱的 Agent

[Skill 入口](skills/artist-color-persona/SKILL.md) 使用明确的阶段、输入、检查和停止条件；[路由表](skills/artist-color-persona/references/routing.md)列出十位艺术家的可观察线索。辅助脚本处理依赖检查、参考作品定位和标准文件导出，减少依赖 Agent 记忆路径或重写算法：

```sh
python skills/artist-color-persona/scripts/preflight.py
python skills/artist-color-persona/scripts/artwork_library.py list --artist monet_giverny_late
```

完整准备、拟合和导出命令见[双图执行流程](skills/artist-color-persona/references/artwork-image-lut.md)。这些脚本不替代宿主的双图编辑能力。缺少图像编辑、Python 或真实返回文件时，应明确报告实际完成阶段。

## 参考作品与许可

库中保留 **10 位艺术家、80 幅作品的索引、来源及原有权利说明**。公开包附带 **3 张已标注 CC0 的莫奈作品图**；其余研究用图像不随仓库重新分发。条目存在不代表图片已打包。

Agent 可从已记录的公开图像地址按需获取选定作品，放入本机私有缓存；也可导入用户提供的对应真实作品。网络失败、来源内容变化或 PDF 中的单幅画无法可靠提取时，要求提供图片，不使用生成图冒充真画。获取参考文件不等于获得公开转载许可。详见 [ARTWORKS.md](ARTWORKS.md)。

代码和原创说明以 [MIT](LICENSE) 发布；第三方作品、图版及研究资料保留各自权利。本仓库不附个人照片、DPReview 样片、私有录屏工具、账号信息或实验大文件。

## 当前实现

- 参考画优先，人物解读后置；实际 Image 提示仅指定两张图的角色及追色要求。
- 以 Image 实际返回拟合 Oklab Gaussian optimal-transport 映射，默认保存 65³、全范围 sRGB `.cube`。
- 重新读取保存的 LUT 渲染原尺寸照片，保留相机原片的像素位置和构图。
- 鲜艳、明显色偏和局部浓色是允许的表现方向，不自动判作缺陷或减弱；审美由用户判断。
- Image 可能重绘物件或产生局部换色；全局 LUT 不能完整复制这些操作。人物对话是基于作品与资料的角色模拟，并非历史原话。

技术报告见 [IEEE 期刊版式技术报告](reports/current-version/README.md)。本次整理使用既有结果，不新增独立试跑或模型实验。
