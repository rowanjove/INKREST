# 提示词双树

- `prompts/defaults/` 是随仓库发布的模板。新建作品时复制到该书的 `prompts/`。
- 仓库根目录的 `prompts/*.md` 是开发默认稿，应与 `defaults/` 保持同名文件一致。
- 每本书的 `projects/<id>/prompts/` 可以单独改，不回写仓库模板。
- 以代码加载路径为准：项目目录有角色文件就用项目文件，否则回落到 `prompts/defaults/`。
