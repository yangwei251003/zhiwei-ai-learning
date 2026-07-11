# Auth Experience Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the real, responsive login and registration experience for 知微智学 using the approved “星图编辑部” design direction.

**Architecture:** Vue Router owns public/protected navigation, a Pinia user store owns authentication state, and one Axios client owns token injection and error normalization. Login and registration views share an `AuthShell`; visual motion is isolated in `BrandConstellation`, while forms remain focused and testable.

**Tech Stack:** Vue 3, TypeScript, Vue Router, Pinia, Axios, Element Plus icons, SCSS, Vitest, Vue Test Utils, Playwright browser verification, FastAPI authentication/profile APIs.

---

## File Map

- Create `frontend/src/router/index.ts`: routes, authentication guard, return URL handling.
- Create `frontend/src/stores/user.ts`: token persistence, login, registration, profile initialization, session restore.
- Modify `frontend/src/utils/http.ts`: API client, authorization header, normalized errors, `401` callback.
- Create `frontend/src/types/auth.ts`: request/response and registration form types.
- Create `frontend/src/components/auth/AuthShell.vue`: shared responsive authentication layout.
- Create `frontend/src/components/auth/BrandConstellation.vue`: branded star-map visual and focus-responsive motion.
- Create `frontend/src/components/auth/LoginForm.vue`: login fields and submission feedback.
- Create `frontend/src/components/auth/RegisterForm.vue`: account, major search, and learning-style fields.
- Create `frontend/src/views/LoginView.vue`: login orchestration and success transition.
- Create `frontend/src/views/RegisterView.vue`: registration orchestration and partial-success recovery.
- Create `frontend/src/views/WorkbenchView.vue`: protected destination reusing the current workbench content.
- Modify `frontend/src/App.vue`: router outlet and global transition only.
- Modify `frontend/src/main.ts`: install router and restore the user session before mount.
- Replace `frontend/src/styles/tokens.scss`: approved product color, spacing, typography, elevation, and theme tokens.
- Replace `frontend/src/styles/main.scss`: global reset, theme, accessibility, and authentication presentation.
- Modify `frontend/src/styles/animations.css`: constellation, shake, success curtain, and reduced-motion rules.
- Modify `frontend/vite.config.ts`: preserve `/api` when proxying to FastAPI.
- Modify `frontend/package.json`: add Vitest, Vue Test Utils, and jsdom test scripts.
- Create `frontend/src/stores/user.test.ts`: store and partial registration tests.
- Create `frontend/src/router/index.test.ts`: protected-route tests.
- Create `frontend/src/components/auth/LoginForm.test.ts`: form validation and submission tests.
- Create `frontend/src/components/auth/RegisterForm.test.ts`: major/style collection tests.

### Task 1: Test Harness and HTTP Contract

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/src/utils/http.ts`
- Create: `frontend/src/types/auth.ts`

- [ ] **Step 1: Add the frontend test commands and dependencies**

Add scripts `"test": "vitest run"` and `"test:watch": "vitest"`. Add `@vue/test-utils`, `jsdom`, and `vitest` to `devDependencies`, then run:

```powershell
npm install
```

Expected: lockfile updates and installation exits with code 0.

- [ ] **Step 2: Add a failing API client test**

Create `frontend/src/utils/http.test.ts` with a custom Axios adapter that verifies `Authorization: Bearer token-value` is attached and that a `401` invokes the registered unauthorized handler.

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest'
import http, { setAuthTokenProvider, setUnauthorizedHandler } from './http'

describe('http client', () => {
  beforeEach(() => {
    setAuthTokenProvider(() => 'token-value')
    setUnauthorizedHandler(() => undefined)
  })

  it('attaches the bearer token', async () => {
    http.defaults.adapter = async (config) => ({
      config, data: {}, headers: {}, status: 200, statusText: 'OK',
    })
    const response = await http.get('/api/auth/me')
    expect(response.config.headers.Authorization).toBe('Bearer token-value')
  })

  it('runs the unauthorized handler for 401 responses', async () => {
    const unauthorized = vi.fn()
    setUnauthorizedHandler(unauthorized)
    http.defaults.adapter = async (config) => Promise.reject({
      config, isAxiosError: true, response: { status: 401, data: { detail: '无效的 Token' } },
    })
    await expect(http.get('/api/auth/me')).rejects.toMatchObject({ message: '登录已过期，请重新登录' })
    expect(unauthorized).toHaveBeenCalledOnce()
  })
})
```

- [ ] **Step 3: Run the HTTP tests and verify failure**

```powershell
npm test -- src/utils/http.test.ts
```

Expected: FAIL because the handler registration exports do not exist.

- [ ] **Step 4: Implement the typed API client**

Define `AuthToken`, `User`, `Credentials`, `LearningStyle`, and `RegistrationInput` in `types/auth.ts`. In `http.ts`, export `ApiError`, `setAuthTokenProvider`, and `setUnauthorizedHandler`; attach the bearer token in a request interceptor and normalize Axios failures into Chinese `ApiError` messages. Do not trigger the unauthorized handler for `/api/auth/login` or `/api/auth/register`.

- [ ] **Step 5: Preserve API paths in Vite and run the tests**

Remove the proxy `rewrite` callback so `/api/auth/login` reaches FastAPI unchanged.

```powershell
npm test -- src/utils/http.test.ts
```

Expected: 2 tests PASS.

- [ ] **Step 6: Commit the API foundation**

```powershell
git add frontend/package.json frontend/package-lock.json frontend/vite.config.ts frontend/src/types/auth.ts frontend/src/utils/http.ts frontend/src/utils/http.test.ts
git commit -m "feat: add authenticated frontend API client"
```

### Task 2: Authentication Store and Router Guard

**Files:**
- Create: `frontend/src/stores/user.ts`
- Create: `frontend/src/stores/user.test.ts`
- Create: `frontend/src/router/index.ts`
- Create: `frontend/src/router/index.test.ts`

- [ ] **Step 1: Write failing user-store tests**

Mock `http.post`, `http.get`, and `http.patch`. Verify login stores the token and user, restore removes an invalid token, and registration keeps the token when profile initialization fails.

```ts
it('keeps the account session when profile initialization fails', async () => {
  vi.mocked(http.post).mockResolvedValueOnce({ data: { access_token: 'new-token' } } as never)
  vi.mocked(http.get).mockResolvedValueOnce({ data: { id: 7, username: 'yang', role: 'student' } } as never)
  vi.mocked(http.patch).mockRejectedValueOnce(new ApiError('画像资料保存失败', 500))
  const store = useUserStore()
  const result = await store.register({ username: 'yang', password: 'password123', major: '软件工程', learningStyle: 'visual' })
  expect(result.profileSaved).toBe(false)
  expect(store.token).toBe('new-token')
  expect(store.user?.username).toBe('yang')
})
```

- [ ] **Step 2: Run store tests and verify failure**

```powershell
npm test -- src/stores/user.test.ts
```

Expected: FAIL because `useUserStore` does not exist.

- [ ] **Step 3: Implement the user store**

Use the local storage key `zhiwei.auth.token`. Implement `login`, `register`, `restoreSession`, `saveProfile`, and `logout`. `register` must call `/api/auth/register`, then `/api/auth/me`, then `/api/profile/current` with `{ major, cognitive_style }`, returning `{ profileSaved: boolean }` without discarding a valid account when the final request fails.

- [ ] **Step 4: Write failing router tests**

Export `createAppRouter()` and `installAuthGuard(router, pinia)`. Verify `/workbench` redirects to `/login?redirect=/workbench` when signed out and allows navigation after authentication.

- [ ] **Step 5: Implement routes and guard**

Define `/login` and `/register` with `meta.public = true`; define `/workbench` with `meta.requiresAuth = true`; redirect `/` based on authenticated state. The guard must call session restore once and retain the full target path in `redirect`.

- [ ] **Step 6: Run store and router tests**

```powershell
npm test -- src/stores/user.test.ts src/router/index.test.ts
```

Expected: all authentication and navigation tests PASS.

- [ ] **Step 7: Commit authentication state and navigation**

```powershell
git add frontend/src/stores/user.ts frontend/src/stores/user.test.ts frontend/src/router/index.ts frontend/src/router/index.test.ts
git commit -m "feat: add authentication state and route protection"
```

### Task 3: Shared Authentication Shell and Visual System

**Files:**
- Create: `frontend/src/components/auth/AuthShell.vue`
- Create: `frontend/src/components/auth/BrandConstellation.vue`
- Modify: `frontend/src/styles/tokens.scss`
- Modify: `frontend/src/styles/main.scss`
- Modify: `frontend/src/styles/animations.css`

- [ ] **Step 1: Replace generic purple tokens with approved brand tokens**

Define deep green canvas/surface/ink values, fluorescent yellow action values, status colors, radii no greater than 8px for cards, and corresponding `.dark` overrides. Use `"Aptos Display", "Microsoft YaHei", sans-serif` for display and `"IBM Plex Sans", "Microsoft YaHei", sans-serif` for body with local fallbacks.

- [ ] **Step 2: Implement `BrandConstellation`**

Render semantic decorative layers with CSS grid lines, three orbital rings, labeled nodes for `画像`, `资源`, and `路径`, the existing `/assets/mascot-hero.png`, and the literal brand statement `学习，从被理解开始`. Accept a Boolean `focused` prop to increase only node density and glow, and mark decorative elements `aria-hidden="true"`.

- [ ] **Step 3: Implement `AuthShell`**

Expose default and `footer` slots. Render a theme icon button, the 45/55 desktop grid, compact mobile brand strip, and the three product facts `多智能体`, `个性化`, `即时生成`. Use the existing mascot logo as a first-viewport brand signal.

- [ ] **Step 4: Add purposeful motion and accessibility rules**

Implement `constellation-drift`, `node-pulse`, `auth-shake`, `mascot-celebrate`, and `success-curtain`. Under `@media (prefers-reduced-motion: reduce)`, set animation duration to `0.01ms` and disable smooth scrolling. Keep focus outlines visible and ensure all 390px-wide content fits without horizontal scrolling.

- [ ] **Step 5: Run the frontend build**

```powershell
npm run build
```

Expected: Vue TypeScript and Vite build complete with no errors.

- [ ] **Step 6: Commit the shared visual system**

```powershell
git add frontend/src/components/auth/AuthShell.vue frontend/src/components/auth/BrandConstellation.vue frontend/src/styles/tokens.scss frontend/src/styles/main.scss frontend/src/styles/animations.css
git commit -m "feat: add constellation authentication shell"
```

### Task 4: Login Form and Page

**Files:**
- Create: `frontend/src/components/auth/LoginForm.vue`
- Create: `frontend/src/components/auth/LoginForm.test.ts`
- Create: `frontend/src/views/LoginView.vue`

- [ ] **Step 1: Write failing login-form tests**

Mount the form and verify empty submission shows both required messages, password visibility changes the input type, and valid submission emits `{ username, password, remember }`.

```ts
it('emits valid credentials', async () => {
  const wrapper = mount(LoginForm)
  await wrapper.get('[name="username"]').setValue('learner')
  await wrapper.get('[name="password"]').setValue('password123')
  await wrapper.get('form').trigger('submit')
  expect(wrapper.emitted('submit')?.[0]?.[0]).toEqual({ username: 'learner', password: 'password123', remember: false })
})
```

- [ ] **Step 2: Run the form test and verify failure**

```powershell
npm test -- src/components/auth/LoginForm.test.ts
```

Expected: FAIL because `LoginForm.vue` does not exist.

- [ ] **Step 3: Implement `LoginForm`**

Use native labels and inputs, a lucide-equivalent Element Plus `View/Hide` icon button with tooltip, checkbox for “保持登录”, and stable submit button. Accept `loading` and `serverError`; emit focus changes so the constellation can respond. Add `autocomplete="username"` and `autocomplete="current-password"`.

- [ ] **Step 4: Implement `LoginView`**

Call `userStore.login`, display normalized errors, apply one shake animation per failed attempt, switch the mascot to `/assets/mascot-celebrate.png` on success, wait only for the 420ms curtain transition, then navigate to the validated same-origin `redirect` route or `/workbench`.

- [ ] **Step 5: Run focused tests and build**

```powershell
npm test -- src/components/auth/LoginForm.test.ts
npm run build
```

Expected: tests PASS and production build completes.

- [ ] **Step 6: Commit login experience**

```powershell
git add frontend/src/components/auth/LoginForm.vue frontend/src/components/auth/LoginForm.test.ts frontend/src/views/LoginView.vue
git commit -m "feat: build branded login experience"
```

### Task 5: Registration Form and Page

**Files:**
- Create: `frontend/src/components/auth/RegisterForm.vue`
- Create: `frontend/src/components/auth/RegisterForm.test.ts`
- Create: `frontend/src/views/RegisterView.vue`

- [ ] **Step 1: Write failing registration tests**

Verify the searchable major list filters Chinese labels, password shorter than eight characters blocks submit, selecting `动手型` emits `hands_on`, and learning style may be omitted.

```ts
it('collects major and hands-on learning style', async () => {
  const wrapper = mount(RegisterForm)
  await wrapper.get('[name="username"]').setValue('learner')
  await wrapper.get('[name="password"]').setValue('password123')
  await wrapper.get('[name="major"]').setValue('软件工程')
  await wrapper.get('[data-style="hands_on"]').trigger('click')
  await wrapper.get('form').trigger('submit')
  expect(wrapper.emitted('submit')?.[0]?.[0]).toMatchObject({ major: '软件工程', learningStyle: 'hands_on' })
})
```

- [ ] **Step 2: Run the registration tests and verify failure**

```powershell
npm test -- src/components/auth/RegisterForm.test.ts
```

Expected: FAIL because `RegisterForm.vue` does not exist.

- [ ] **Step 3: Implement `RegisterForm`**

Provide a local list of common university majors plus free text entry. Use a semantic combobox/listbox pattern and a four-option segmented radio group for `visual`, `auditory`, `hands_on`, and `theoretical`. Validate username, eight-character password, and major before emit.

- [ ] **Step 4: Implement `RegisterView`**

Call `userStore.register`. On full success show `欢迎加入！我是小智析析，准备好一起学习了吗？`; on partial success show `账户已创建，画像资料暂未保存` with a `重试保存画像` command that calls `saveProfile`. Never re-run account creation during retry.

- [ ] **Step 5: Run focused tests and build**

```powershell
npm test -- src/components/auth/RegisterForm.test.ts src/stores/user.test.ts
npm run build
```

Expected: tests PASS and production build completes.

- [ ] **Step 6: Commit registration experience**

```powershell
git add frontend/src/components/auth/RegisterForm.vue frontend/src/components/auth/RegisterForm.test.ts frontend/src/views/RegisterView.vue
git commit -m "feat: build personalized registration experience"
```

### Task 6: Application Integration and End-to-End Verification

**Files:**
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/main.ts`
- Create: `frontend/src/views/WorkbenchView.vue`
- Delete: `frontend/src/components/HelloWorld.vue`
- Delete: `frontend/src/style.css`

- [ ] **Step 1: Move the current workbench into a protected view**

Move the existing workbench template and health-store integration from `App.vue` into `WorkbenchView.vue`. Add a compact user menu with logout; do not redesign the workbench during this authentication stage.

- [ ] **Step 2: Install router and simplify the app root**

Register the router in `main.ts`, connect the HTTP token provider and unauthorized handler to the user store, await `restoreSession`, then mount. Replace `App.vue` with a `RouterView` inside a keyed fade transition and a global `aria-live="polite"` notification region.

- [ ] **Step 3: Run all automated checks**

```powershell
npm test
npm run build
python -m pytest tests/test_auth.py -q
```

Expected: all Vitest tests pass, Vite production build succeeds, and backend auth tests pass.

- [ ] **Step 4: Start backend and frontend servers**

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
npm run dev -- --host 127.0.0.1
```

Expected: FastAPI is reachable on port 8000 and Vite prints its local URL without proxy errors.

- [ ] **Step 5: Verify the real authentication path in a browser**

At 1440×900 and 390×844: register a unique user, choose 软件工程 and 视觉型, verify welcome feedback, logout, log back in, refresh, and confirm session restoration. Navigate directly to `/workbench` while logged out and verify return to the same route after login. Repeat with dark/light mode and reduced motion.

- [ ] **Step 6: Inspect visual evidence**

Capture login and registration screenshots at both viewport sizes. Inspect them with `view_image` for: first-viewport brand prominence, 45/55 desktop ratio, mobile text fit, form focus visibility, mascot/background rendering, no nested cards, no overlap, and stable button/input dimensions. Check console output for errors and network panel for `/api/auth/*` plus `/api/profile/current` success.

- [ ] **Step 7: Commit integrated authentication stage**

```powershell
git add frontend/src/App.vue frontend/src/main.ts frontend/src/views/WorkbenchView.vue frontend/src/components/HelloWorld.vue frontend/src/style.css
git commit -m "feat: integrate protected learning workbench"
```

- [ ] **Step 8: Record verification evidence**

Add the final test commands, viewport results, screenshot paths, and any intentional deviations to the implementation summary. Do not claim completion if any real authentication request, target viewport, or screenshot inspection is missing.
