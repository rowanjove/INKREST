# 双区域插件套件模板 (Dual-Region Starter)

本模板适用于同时需要在 **书库侧栏（全局）** 和 **作品侧栏（单书）** 提供不同面板的复合套件插件。

## 核心设计规范

1. **显式声明双入口（禁止 `both` 伪配置）**：
   - 必须在 `contributes.navigation` 中分别声明 2 项：
     - 项 1：`surface: "library_sidebar"`，对应全局管理面板；
     - 项 2：`surface: "project_sidebar"`，对应单书关联面板；
   - 严禁将 surface 设为 `"both"`，清单校验器会严格拒绝。
2. **正交权限解耦**：
   - 全局入口仅绑定 `project_catalog_read`；
   - 作品入口绑定 `project_read`；
   - 两者互不越权，保障多书数据隔离安全。
