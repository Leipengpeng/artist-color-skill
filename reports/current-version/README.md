# 当前版本技术报告

- [阅读 PDF](artist-color-skill-report.pdf)
- [LaTeX 主文件](report.tex)
- [正文源文件](report-body.tex)
- [既有结果的脱敏汇总](existing-results-summary.json)

采用 `IEEEtran` 的 `journal` 双栏模板，中文正文与数字编号参考文献。文稿是当前版本的工程技术报告，不表示已经在 IEEE 期刊发表或通过同行评审。文中只使用已有输出记录，本次没有新增独立试跑。

在本目录使用 XeLaTeX 编译两遍：

```sh
xelatex -interaction=nonstopmode -halt-on-error report.tex
xelatex -interaction=nonstopmode -halt-on-error report.tex
```

需要 IEEEtran、xeCJK、fontspec、amsmath、amssymb、balance 和 hyperref。默认字体为 Windows 的 Times New Roman、SimSun、Microsoft YaHei、Consolas；其他系统可以在 `report.tex` 中替换为本机可用的西文字体与 CJK 字体。正文没有受限画作或用户照片像素。

IEEE 模板入口：<https://template-selector.ieee.org/>。IEEEtran 类文件使用其自身许可，非本项目 MIT 许可；可通过 TeX 发行版安装。本源码包不重新分发类文件。
