# 作品级插件开发模板 (Project Tool Starter)

本模板适用于挂载在栖墨 **作品创作侧栏** 的辅助分析工具（如伏笔跟踪、人物拓扑图、世界观检视器等）。

## 核心设计规范

1. **作品生命周期同步**：
   - `surface: "project_sidebar"` 会随作品载入自动挂载；
   - 当用户切书或返回书库时，宿主会发送 `inkrest:dispose` 信号，插件必须在 2 秒内释放内存并保存状态；
2. **读写权限隔离**：
   - 默认声明 `project_read` 权限，仅可读取当前活动作品的数据（如 `project.getInfo`、`project.getChapters`、`project.getCharacters`）；
   - 若需修改设定，需显式向用户申请 `project_write` 权限。
3. **打包上传**：
   - 将本目录内容打成 `.zip` 包；
   - 在栖墨 **扩展中心** 载入并信任启用；
   - 打开任意一部作品，即可在作品侧栏看到该插件入口。
