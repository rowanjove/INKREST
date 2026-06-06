# 栖墨插件包模板

1. 将 `id` 改为唯一小写标识（与文件夹名一致更佳）
2. 修改 `plugin_type` 与 `plugin.py` 中的基类
3. 整个目录打成 zip（根目录须含 `inkrest.plugin.json`）
4. 在应用 **插件** 页点击 **载入插件** 上传

可选：`bundles` 引用包内其它 zip；`extract` 在安装时解压到 `data/` 子目录。