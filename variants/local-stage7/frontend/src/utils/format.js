export function formatDate(value) {
  if (!value) return '尚未记录'
  return new Intl.DateTimeFormat('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value))
}

export const resourceLabels = {
  document: '讲解文档',
  mindmap: '思维导图',
  quiz: '练习题',
  video: '视频脚本',
  code: '代码案例',
}
