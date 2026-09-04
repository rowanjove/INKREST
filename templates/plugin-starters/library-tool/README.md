# 书库级插件开发模板 (Library Tool Starter)

本模板适用于挂载在栖墨 **书库侧栏（全局视图）** 的工具扩展（如作品模版库、题材市场、写作数据统计等）。

## 核心设计规范

1. **工作区解耦**：
   - `surface: "library_sidebar"` 严禁依赖作品上下文；
   - 默认仅声明 `project_catalog_read`（访问作品元数据清单：ID、书名、修改时间），不得索取未授权的 `all_projects_read` 或 `all_projects_write`。
2. **安全隔离**：
   - UI 运行在安全的沙箱环境中；
   - 通过受控的 RPC 接口通信（如 `catalog.listProjects`）。
3. **打包上传**：
   - 将本目录内容打成 `.zip` 包；
   - 进入栖墨客户端 **扩展中心** -> **载入插件**；
   - 用户审查权限并同意信任后，即可在书库侧栏看到插件入口。
