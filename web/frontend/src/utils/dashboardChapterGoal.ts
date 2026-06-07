export function buildChapterGoalTemplate(options: {
  chapterId: string
  outline: Record<string, any> | null
  outlineTheme: string
  projectName?: string
  projectDescription?: string
}) {
  const { chapterId, outline, outlineTheme, projectName, projectDescription } = options
  const protagonist = outline?.protagonist?.name || '主角'
  const theme = outlineTheme || projectDescription || projectName || '主线'
  const conflict = outline?.conflict || outline?.core_theme || theme
  const numericId = Number.parseInt(chapterId, 10)
  const chapterLabel = Number.isNaN(numericId) ? chapterId : `第 ${numericId} 章`
  return `${chapterLabel}：围绕「${theme}」推进主线，让${protagonist}面对「${conflict}」中的关键阻力，制造清晰冲突、人物变化和结尾钩子。`
}