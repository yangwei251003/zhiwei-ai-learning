import path from 'node:path'
import { fileURLToPath } from 'node:url'

import AxeBuilder from '@axe-core/playwright'
import { expect, test } from '@playwright/test'


const e2eDir = path.dirname(fileURLToPath(import.meta.url))
const artifactDir = path.resolve(e2eDir, '..', '..', 'output', 'playwright', 'stage-5')

function uniqueLearner(prefix = 'stage5') {
  const id = `${Date.now()}${Math.floor(Math.random() * 10_000)}`
  return {
    username: `${prefix}${id}`.slice(0, 40),
    email: `${prefix}-${id}@example.com`,
    password: `Stage5!Learner${id}Aa1`,
  }
}

async function registerLearner(page, learner = uniqueLearner()) {
  await page.goto('/register')
  await page.getByLabel('用户名').fill(learner.username)
  await page.getByLabel('邮箱').fill(learner.email)
  await page.getByLabel('密码').fill(learner.password)
  await page.getByLabel('专业方向').fill('计算机科学与技术')
  await page.getByLabel('学习方式').selectOption({ label: '偏好图解与结构梳理' })
  await page.getByRole('button', { name: '创建账号并开始' }).click()
  await expect(page).toHaveURL('/')
  await expect(page.getByRole('heading', { name: '今天从哪里继续' })).toBeVisible()
  return learner
}

async function login(page, email, password) {
  await page.goto('/login')
  await page.getByLabel('邮箱').fill(email)
  await page.getByLabel('密码').fill(password)
  await page.getByRole('button', { name: '登录' }).click()
  await expect(page).toHaveURL('/')
}

async function expectAxeClean(page) {
  const accessibility = await new AxeBuilder({ page })
    .withTags(['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'])
    .analyze()
  expect(accessibility.violations).toEqual([])
}

test('public authentication pages pass the WCAG automated gate', async ({ page }) => {
  await page.goto('/login')
  await expectAxeClean(page)
  await page.goto('/register')
  await expectAxeClean(page)
})

test('learner completes registration, home, real Spark chat, and history restore', async ({
  page,
}) => {
  const consoleErrors = []
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  })
  await page.setViewportSize({ width: 1440, height: 900 })
  await registerLearner(page)

  await expect(page.getByText('可用智能体')).toBeVisible()
  await page.screenshot({ path: path.join(artifactDir, 'home-1440-light.png'), fullPage: true })
  await expectAxeClean(page)

  await page.goto('/chat')
  await page.getByLabel('给小智析析发消息').fill('请解释二叉树遍历，并说明我的薄弱点')
  await page.getByRole('button', { name: '发送' }).click()
  await expect(page.getByRole('button', { name: '停止' })).toBeVisible()
  await expect(page.getByRole('button', { name: '发送' })).toBeVisible({ timeout: 210_000 })
  await expect(page.getByRole('alert')).toHaveCount(0)
  await expect(page.locator('.message-assistant .markdown-content')).toContainText(/\S/)
  const history = page.getByRole('button', { name: /请解释二叉树遍历.*2 条消息/ })
  await expect(history).toBeVisible()
  await page.screenshot({ path: path.join(artifactDir, 'chat-real-spark-result-1440.png'), fullPage: true })

  await history.click()
  await expect(
    page.getByRole('region', { name: '当前对话' }).getByText('请解释二叉树遍历，并说明我的薄弱点'),
  ).toBeVisible()
  expect(consoleErrors).toEqual([])
})

test('learner completes real path progress and Tutor three-presentation flow', async ({
  page,
}) => {
  await registerLearner(page, uniqueLearner('loops'))

  await page.goto('/resources')
  await expect(page.getByRole('heading', { name: '全部资源还没有内容' })).toBeVisible()

  await page.goto('/path')
  await page.getByLabel('学习目标').fill('两周内掌握图的遍历算法')
  await page.getByRole('button', { name: '生成学习路径' }).click()
  await expect(page.locator('.path-summary')).toBeVisible({ timeout: 210_000 })
  await expect(page.locator('.timeline-step').first()).toBeVisible()
  await page.getByRole('button', { name: '标记完成' }).first().click()
  await expect(page.getByText('此步骤已完成').first()).toBeVisible()
  await page.screenshot({ path: path.join(artifactDir, 'path-real-result.png'), fullPage: true })

  await page.goto('/tutor')
  await page.getByLabel('学习问题').fill('我不理解梯度下降为什么沿负梯度更新')
  await page.getByRole('button', { name: '开始三段式辅导' }).click()
  await expect(page.getByRole('button', { name: '开始三段式辅导' })).toBeVisible({ timeout: 210_000 })
  await expect(page.getByRole('alert')).toHaveCount(0)
  await expect(page.locator('.answer-pane .markdown-content')).toContainText(/\S/)
  await page.getByRole('tab', { name: '结构图解' }).click()
  await expect(page.getByText('本轮没有结构图解')).toHaveCount(0)
  await expect(page.locator('.mermaid-diagram')).toBeVisible()
  await page.getByRole('tab', { name: '视频脚本' }).click()
  await expect(page.getByText('本轮没有视频脚本')).toHaveCount(0)
  await expect(page.locator('.answer-pane .markdown-content')).toContainText(/镜头|旁白|时长/)
  await page.screenshot({ path: path.join(artifactDir, 'tutor-real-three-presentations.png'), fullPage: true })
})

test('learner generates and renders all five real resource types', async ({ page }) => {
  await registerLearner(page, uniqueLearner('resources'))
  await page.goto('/chat')
  await page
    .getByLabel('给小智析析发消息')
    .fill('请为二叉树遍历生成五类学习资源，包含可渲染思维导图和可运行 Python 代码')
  await page.getByRole('button', { name: '发送' }).click()
  await expect(page.getByRole('button', { name: '停止' })).toBeVisible()
  await expect(page.getByRole('button', { name: '发送' })).toBeVisible({ timeout: 330_000 })
  await expect(page.getByRole('alert')).toHaveCount(0)
  await expect(page.locator('.created-resources a')).toHaveCount(5)

  await page.goto('/resources')
  await expect(page.locator('.resource-item')).toHaveCount(5)
  for (const label of ['讲解文档', '思维导图', '练习题', '视频脚本', '代码案例']) {
    await expect(page.locator('.resource-grid').getByText(label, { exact: true })).toHaveCount(1)
  }

  await page.locator('.resource-grid').getByText('思维导图', { exact: true }).locator('..').click()
  await expect(page.locator('.mermaid-diagram')).toBeVisible({ timeout: 30_000 })
  await page.getByRole('button', { name: '关闭资源详情' }).click()

  await page.locator('.resource-grid').getByText('代码案例', { exact: true }).locator('..').click()
  await expect(
    page.locator('.el-drawer pre code').filter({ hasText: /def |print\(|class / }).first(),
  ).toBeVisible()
  await page.screenshot({ path: path.join(artifactDir, 'resources-real-five-types.png'), fullPage: true })
})

test('admin bootstrap account manages knowledge, users, and safe settings', async ({ page }) => {
  await login(
    page,
    process.env.XZX_E2E_ADMIN_EMAIL,
    process.env.XZX_E2E_ADMIN_PASSWORD,
  )
  await page.goto('/admin')
  await expect(page.getByRole('heading', { name: '管理后台' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '知识库文档' })).toBeVisible()

  await page.locator('input[type="file"]').setInputFiles({
    name: 'stage-5-evidence.txt',
    mimeType: 'text/plain',
    buffer: Buffer.from('二叉树前序遍历按照根节点、左子树、右子树的顺序。'),
  })
  await expect(page.getByRole('status')).toContainText('已完成入库', { timeout: 210_000 })
  await expect(page.getByText('stage-5-evidence.txt', { exact: true })).toBeVisible()

  await page.getByRole('button', { name: '用户管理' }).click()
  const userManagement = page.getByLabel('用户管理')
  await expect(userManagement.getByText('stage5admin')).toBeVisible()
  await expect(userManagement.getByText('管理员')).toBeVisible()

  await page.getByRole('button', { name: '系统配置' }).click()
  await page.getByLabel('默认模型等级').selectOption('high')
  await page.getByLabel('Temperature').fill('0.4')
  await page.getByRole('button', { name: '保存配置' }).click()
  await expect(page.getByRole('status')).toContainText('系统配置已保存')
  await expectAxeClean(page)
  await page.screenshot({ path: path.join(artifactDir, 'admin-1440.png'), fullPage: true })
})

test('responsive themes, keyboard focus, and reduced motion remain usable', async ({ page }) => {
  await registerLearner(page, uniqueLearner('visual'))
  const chatLink = page.getByRole('link', { name: '开始学习对话' })
  await chatLink.focus()
  await expect(chatLink).toBeFocused()
  await page.keyboard.press('Enter')
  await expect(page).toHaveURL('/chat')

  await page.setViewportSize({ width: 1024, height: 768 })
  await expect(page.locator('html')).toHaveJSProperty('scrollWidth', 1024)
  await page.screenshot({ path: path.join(artifactDir, 'chat-1024-light.png'), fullPage: true })

  await page.setViewportSize({ width: 360, height: 800 })
  await expect(page.locator('html')).toHaveJSProperty('scrollWidth', 360)
  await page.screenshot({ path: path.join(artifactDir, 'chat-360-light.png'), fullPage: true })

  await page.setViewportSize({ width: 1440, height: 900 })
  await expectAxeClean(page)

  await page.goto('/resources')
  await expectAxeClean(page)
  const allResourcesTab = page.getByRole('tab', { name: '全部资源' })
  await allResourcesTab.focus()
  await page.keyboard.press('End')
  await expect(page.getByRole('tab', { name: '代码案例' })).toBeFocused()
  await expect(page.getByRole('tab', { name: '代码案例' })).toHaveAttribute('aria-selected', 'true')

  await page.goto('/tutor')
  await expectAxeClean(page)
  await page.getByRole('tab', { name: '文字讲解' }).focus()
  await page.keyboard.press('ArrowRight')
  await expect(page.getByRole('tab', { name: '结构图解' })).toBeFocused()
  await expect(page.getByRole('tab', { name: '结构图解' })).toHaveAttribute('aria-selected', 'true')

  await page.goto('/path')
  await expectAxeClean(page)

  await page.goto('/chat')
  await page.getByRole('button', { name: '切换到深色模式' }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.screenshot({ path: path.join(artifactDir, 'chat-1440-dark.png'), fullPage: true })

  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/')
  await expect(page.locator('.hero-visual > img')).toHaveCSS('animation-name', 'none')
  await page.screenshot({ path: path.join(artifactDir, 'home-reduced-motion.png'), fullPage: true })
})
