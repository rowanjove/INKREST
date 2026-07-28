<script setup lang="ts">
import { ElConfigProvider } from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import App from './App.vue'
</script>

<template>
  <el-config-provider :locale="zhCn" size="default">
    <App />
  </el-config-provider>
</template>