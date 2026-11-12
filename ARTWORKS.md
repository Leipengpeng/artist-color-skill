# 参考作品的来源与分发

`skills/artist-color-persona/assets/artworks/index.json` 指向十份清单，各含八条真实作品记录。每条保留作品名、时期、来源网页、图像地址、研究图哈希与当时收集的权利说明。这些说明是出处记录，不是本项目对第三方作品作出的许可授权。

本次公开仅附带清单中明确标注 CC0 的三张 Cleveland Museum of Art 莫奈图版：`1953.155`、`1916.1044`、`1960.81`。该馆开放获取政策见 <https://www.clevelandart.org/open-access>。其余原有本地研究副本均不放入仓库与安装包。

## 使用缺失的真实参考图

从技能目录运行：

```sh
python scripts/artwork_library.py list --artist hopper_urban_light
python scripts/artwork_library.py fetch --artist hopper_urban_light --file 05-46345-early-sunday-morning.jpg
```

`fetch` 只访问清单所记载的 HTTPS 图像地址，校对已有源文件哈希并写入本机私有缓存，不修改公开图库。来源已变化、被限制访问或不是可直接读取的单幅图时，会停止。不要绕过网站限制或更换为另一幅画；可检查原作品页后，由用户提供对应的合法可用图像：

```sh
python scripts/artwork_library.py import --artist hopper_urban_light --file 05-46345-early-sunday-morning.jpg --image /path/to/actual-artwork.jpg
```

导入后用 `list` 获取 `local_path`，查看图片确认是记录的作品，再用于 `prepare --artwork`。用户提供库外作品时，可直接把实际文件、标题和来源交给 `prepare`，不用强行匹配已有条目。

默认缓存为用户主目录的 `.cache/artist-color-persona`，可用 `ARTIST_COLOR_CACHE` 指定其它私有目录。请勿将缓存放进发布目录或把它自动提交 Git。公开展示照片或画作图版时，仍需按各自来源条件处理；代码的 MIT 许可不覆盖它们。
