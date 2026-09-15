<script setup lang="ts">
import { ref } from 'vue'

defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const close = () => emit('update:visible', false)
const activeTab = ref('quickstart')

const pluginTypeHints = [
  { value: 'pipeline_hook', tip: '在流水线各阶段前后插入逻辑（改大纲、润色稿等）' },
  { value: 'quality_guard', tip: '章节质量检查、规则校验' },
  { value: 'exporter', tip: '导出 Word / Markdown 等格式' },
  { value: 'event_listener', tip: '监听任务完成、章节保存等事件' },
  { value: 'prompt_enhancer', tip: '增强或改写发给模型的 Prompt' },
  { value: 'rules_extension', tip: '扩展写作规则资产' },
  { value: 'sensitive_scanner', tip: '敏感词扫描' },
  { value: '…', tip: '其余类型见插件页筛选列表；须与清单 plugin_type 一致' },
]

const manifestExample = `{
  "id": "my-plugin",
  "version": "1.0.0",
  "display_name": "我的插件",
  "description": "简要说明用途",
  "author": "作者名",
  "plugin_type": "pipeline_hook",
  "entry": "plugin:PLUGIN_CLASS",
  "min_core_version": "1.0.0",
  "requires": [],
  "capabilities": ["project_read", "project_write", "model_access"],
  "config_schema": {
    "type": "object",
    "properties": {
      "enabled_feature": {
        "type": "boolean",
        "title": "启用扩展功能",
        "default": true
      }
    }
  }
}`

const pluginPyExample = `from novel_agent.plugins.base import PipelineHookPlugin, PluginMeta, PluginType

class MyPlugin(PipelineHookPlugin):
    def get_meta(self) -> PluginMeta:
        return PluginMeta(
            name="my-plugin",
            display_name="我的插件",
            version="1.0.0",
            plugin_type=PluginType.PIPELINE_HOOK,
        )

    def after_outline(self, outline):
        # self.context.config 读取用户在「配置」里保存的参数
        return outline

PLUGIN_CLASS = MyPlugin`
</script>

<template>
  <el-dialog
    :model-value="visible"
    title="扩展帮助"
    width="720px"
    align-center
    class="plugin-help-dialog"
    @update:model-value="emit('update:visible', $event)"
  >
    <el-tabs v-model="activeTab" class="help-tabs" aria-label="扩展帮助子页">
      <el-tab-pane label="快速开始" name="quickstart">
        <div class="help-scroll">
          <el-alert type="info" :closable="false" show-icon>
            <template #title>先看清楚，再启用</template>
            载入插件后先核对来源、内容摘要和权限；信任与启用是两步，帮助页不会执行插件。
          </el-alert>
          <section class="help-block">
            <h3>推荐流程</h3>
            <ol>
              <li>点击「载入插件」上传 <code>.zip</code>，安装后默认未信任、未启用。</li>
              <li>查看内容摘要和权限，确认来源后只建立信任。</li>
              <li>再次确认后打开启用开关；代码或权限变化后需要重新确认。</li>
              <li>改动本地插件后点「重新扫描」，不要直接让未检查的代码运行。</li>
            </ol>
          </section>
          <section class="help-block">
            <h3>ZIP 最小结构</h3>
            <p><code>inkrest.plugin.json</code> 与 <code>plugin.py</code> 放在压缩包根目录，或唯一的顶层文件夹内。</p>
            <p class="muted">需要更多字段和 Python 示例时，切换到“开发参考”。</p>
          </section>
          <section class="help-block">
            <h3>新手可从官方示例插件开始</h3>
            <p>
              源码环境下可复制 <code>plugins/examples/</code> 中的
              <code>hello_guard.py</code> 到项目 <code>plugins/</code> 目录，再回到扩展中心扫描、信任并启用。
            </p>
            <p class="muted">完整说明见 <code>plugins/examples/README.md</code>，也可切换到“官方示例”查看操作步骤。</p>
          </section>
        </div>
      </el-tab-pane>

      <el-tab-pane label="官方示例" name="examples">
        <div class="help-scroll">
          <el-alert type="warning" :closable="false" show-icon title="源码环境示例">
            官方示例位于源码目录 <code>plugins/examples/</code>。桌面安装包不保证包含这个目录；示例是兼容格式，启用前会按本地代码权限处理。
          </el-alert>
          <section class="help-block">
            <h3><code>hello_guard.py</code></h3>
            <p>质量门禁示例：演示如何拦截低分章节。</p>
            <ol>
              <li>源码环境下复制到项目的 <code>plugins/</code> 目录。</li>
              <li>回到本页点击「重新扫描」，找到 Hello Guard。</li>
              <li>先查看摘要与权限，再建立信任，最后单独打开启用。</li>
              <li>只有你明确开始一章生产后，才会看到它对门禁报告的影响。</li>
            </ol>
          </section>
          <section class="help-block">
            <h3><code>txt_export_hook.py</code></h3>
            <p>导出钩子示例：演示如何追加自定义 TXT 导出。</p>
            <p class="muted">它同样不会自动启用；使用前请确认本地代码权限和目标项目。</p>
          </section>
          <p class="muted">完整字段、权限和打包方式见 <code>docs/plugins/PLUGIN_AUTHOR.md</code>。示例页面只提供说明，不会自动复制、信任、启用或运行插件。</p>
        </div>
      </el-tab-pane>

      <el-tab-pane label="开发参考" name="developer">
        <div class="help-scroll">

      <section class="help-block">
        <h3>1. ZIP 包结构</h3>
        <p>压缩包根目录（或<strong>唯一</strong>顶层文件夹）须包含：</p>
        <ul>
          <li><code>inkrest.plugin.json</code>（也支持旧名 <code>plugin.json</code>）— 插件清单</li>
          <li><code>plugin.py</code> 或 <code>__init__.py</code> — 实现代码，并导出 <code>PLUGIN_CLASS</code></li>
        </ul>
        <p class="muted">可选：<code>bundles</code> 内嵌 zip（安装时解压到 <code>data/&lt;名&gt;/</code>）；<code>extract</code> 自定义解压规则。单包上限约 20MB。</p>
      </section>

      <section class="help-block">
        <h3>2. 清单字段（inkrest.plugin.json）</h3>
        <ul class="field-list">
          <li><code>id</code> — 必填，小写字母开头，2–64 位（字母/数字/<code>_</code>/<code>-</code>）</li>
          <li><code>plugin_type</code> — 必填，与基类类型一致（见下方常用类型）</li>
          <li><code>entry</code> — 入口，默认 <code>plugin:PLUGIN_CLASS</code></li>
          <li><code>version</code> / <code>display_name</code> / <code>description</code> / <code>author</code></li>
          <li><code>min_core_version</code> — 要求的栖墨核心版本，当前为 <code>1.0.0</code></li>
          <li><code>requires</code> — 依赖的其他插件 id 数组</li>
          <li><code>capabilities</code> — 权限数组；未知或重复值会被拒绝，省略时按类型推导</li>
          <li><code>config_schema</code> — JSON Schema，用于设置页「配置」表单</li>
        </ul>
        <pre class="code-sample">{{ manifestExample }}</pre>
      </section>

      <section class="help-block">
        <h3>3. 权限值</h3>
        <p>
          支持 <code>project_read</code>、<code>project_write</code>、
          <code>model_access</code>、<code>network_access</code>、
          <code>file_export</code>、<code>web_routes</code> 和
          <code>command_execution</code>。应用会补齐插件类型的最低权限，
          并为所有本地插件标记 <code>local_code</code>。
        </p>
      </section>

      <section class="help-block">
        <h3>4. entry 写法</h3>
        <ul>
          <li><code>plugin:PLUGIN_CLASS</code> — 从 <code>plugin.py</code> 或包 <code>__init__.py</code> 加载类</li>
          <li><code>package:子模块路径:类名</code> — 例如 <code>package:hooks.writer:WriterHook</code></li>
        </ul>
      </section>

      <section class="help-block">
        <h3>5. Python 最小示例（plugin.py）</h3>
        <p class="muted">继承类型须与 <code>plugin_type</code> 匹配，例如流水线钩子继承 <code>PipelineHookPlugin</code>。</p>
        <pre class="code-sample">{{ pluginPyExample }}</pre>
      </section>

      <section class="help-block">
        <h3>6. 常用 plugin_type</h3>
        <table class="type-table">
          <thead>
            <tr>
              <th>类型值</th>
              <th>用途</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in pluginTypeHints" :key="row.value">
              <td><code>{{ row.value }}</code></td>
              <td>{{ row.tip }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section class="help-block">
        <h3>7. 安装、信任与配置</h3>
        <ol>
          <li>点击「载入插件」上传 <code>.zip</code>，安装后默认<strong>未信任、未启用</strong></li>
          <li>核对来源、内容摘要与权限，明确确认后仅建立信任</li>
          <li>再单独打开启用开关；代码或权限变化后必须重新确认</li>
          <li>点「配置」编辑参数，保存到 <code>config/plugins.yaml</code></li>
          <li>改代码后点「重新扫描」或重启应用以重新加载</li>
        </ol>
      </section>

      <section class="help-block">
        <h3>8. 本地打包（可选）</h3>
        <p>项目内提供模板目录 <code>templates/plugin-starter/</code>，可用脚本打包：</p>
        <pre class="code-sample">.\scripts\package-plugin.ps1 -PluginDir .\templates\plugin-starter</pre>
        <p class="muted">更完整的说明见仓库 <code>docs/plugins/PLUGIN_AUTHOR.md</code>。</p>
      </section>
        </div>
      </el-tab-pane>
    </el-tabs>
    <template #footer>
      <el-button type="primary" @click="close">知道了</el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.help-tabs { min-height: 0; }
.help-tabs :deep(.el-tabs__nav-wrap) { margin-bottom: 8px; }
.help-tabs :deep(.el-tabs__item) { font-size: 13px; }
.help-scroll {
  max-height: min(68vh, 640px);
  overflow-y: auto;
  display: grid;
  gap: 18px;
  padding-right: 4px;
}

.help-block h3 {
  margin: 0 0 8px;
  font-size: 15px;
  font-weight: 750;
  color: var(--color-text-strong);
}

.help-block p,
.help-block li {
  margin: 0 0 6px;
  font-size: 13px;
  line-height: 1.55;
  color: var(--color-text);
}

.help-block ul,
.help-block ol {
  margin: 0;
  padding-left: 1.25rem;
}

.muted {
  color: var(--color-text-muted);
  font-size: 12px;
}

.field-list code,
.help-block code {
  font-size: 12px;
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--color-bg-surface-muted);
  color: var(--color-text-strong);
}

.code-sample {
  margin: 8px 0 0;
  padding: 12px 14px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border);
  background: var(--color-bg-surface-muted);
  font-family: ui-monospace, Consolas, 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.45;
  color: var(--color-text-strong);
  white-space: pre-wrap;
  word-break: break-word;
}

.type-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.type-table th,
.type-table td {
  border: 1px solid var(--color-border-subtle);
  padding: 8px 10px;
  text-align: left;
  vertical-align: top;
}

.type-table th {
  background: var(--color-bg-surface-muted);
  font-weight: 650;
  color: var(--color-text-strong);
}

.type-table code {
  font-size: 11px;
}
</style>
