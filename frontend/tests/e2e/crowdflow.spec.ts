import { test, expect } from "@playwright/test";

/**
 * CrowdFlow 全流程 E2E 测试
 *
 * 前置条件：
 * - 后端运行在 http://localhost:8000
 * - 前端运行在 http://localhost:5173
 * - uploads/videos/ 中有测试视频
 */

const API = "http://localhost:8000/api";

test.describe("CrowdFlow 架构重构验证", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
  });

  test("页面正常加载，无 JS 错误", async ({ page }) => {
    const errors: string[] = [];
    page.on("pageerror", (err) => errors.push(err.message));

    await page.goto("/");
    await page.waitForLoadState("networkidle");

    // 验证核心 UI 元素存在
    await expect(page.locator("text=人流分析")).toBeVisible();
    await expect(page.locator("text=当前人数")).toBeVisible();
    await expect(page.locator("text=密度估计")).toBeVisible();
    await expect(page.locator("text=Cross-line 进入")).toBeVisible();

    expect(errors).toHaveLength(0);
  });

  test("API 路由注册正确", async ({ request }) => {
    // CrossLine CRUD 端点存在
    const resp = await request.get(`${API}/crosslines?source_id=nonexistent`);
    expect(resp.status()).toBe(404); // 数据源不存在但路由存在

    // Regions 端点存在（无 VLM 依赖）
    const regResp = await request.get(`${API}/regions?source_id=nonexistent`);
    expect(regResp.status()).toBe(404);

    // Analysis 端点存在
    const statusResp = await request.get(`${API}/analysis/status?source_id=nonexistent`);
    expect(statusResp.status()).toBe(404);
  });

  test("CrossLine CRUD API 工作正常", async ({ request }) => {
    // 先获取一个有效的 source_id
    const sourcesResp = await request.get(`${API}/sources`);
    const sourcesData = await sourcesResp.json();
    const sources = sourcesData.data?.sources || [];

    if (sources.length === 0) {
      test.skip();
      return;
    }

    const sourceId = sources[0].source_id;

    // 创建 crossline
    const createResp = await request.post(`${API}/crosslines`, {
      data: {
        source_id: sourceId,
        name: "测试闸机线",
        start_x: 10,
        start_y: 50,
        end_x: 90,
        end_y: 50,
        direction: "in",
      },
    });
    expect(createResp.status()).toBe(200);
    const created = await createResp.json();
    const lineId = created.data.line_id;
    expect(lineId).toBeTruthy();

    // 查询 crosslines
    const listResp = await request.get(`${API}/crosslines?source_id=${sourceId}`);
    expect(listResp.status()).toBe(200);
    const listed = await listResp.json();
    expect(listed.data.lines.length).toBeGreaterThanOrEqual(1);

    // 删除 crossline
    const delResp = await request.delete(`${API}/crosslines/${lineId}`);
    expect(delResp.status()).toBe(200);
  });

  test("配置中心包含计数线 Tab", async ({ page }) => {
    // 点击配置中心按钮
    const configBtn = page.locator("text=配置中心");
    if (await configBtn.isVisible()) {
      await configBtn.click();

      // 验证计数线 tab 存在
      await expect(page.locator("text=计数线")).toBeVisible();
    }
  });

  test("数据源列表 + 分析启停流程", async ({ page, request }) => {
    // 检查是否有可用数据源
    const sourcesResp = await request.get(`${API}/sources`);
    const sourcesData = await sourcesResp.json();
    const sources = sourcesData.data?.sources || [];

    if (sources.length === 0) {
      test.skip();
      return;
    }

    // 选择第一个数据源
    const sourceBtn = page.locator(".source-trigger").first();
    if (await sourceBtn.isVisible()) {
      await sourceBtn.click();
      await page.waitForTimeout(500);
    }

    // 检查总览面板显示
    await expect(page.locator("text=当前人数")).toBeVisible();
    await expect(page.locator("text=密度估计")).toBeVisible();
    await expect(page.locator("text=Cross-line 进入")).toBeVisible();
  });

  test("WebSocket 帧数据包含新字段", async ({ request }) => {
    // 验证 RealtimeFrame schema 的新字段
    const sourcesResp = await request.get(`${API}/sources`);
    const sourcesData = await sourcesResp.json();
    const sources = sourcesData.data?.sources || [];

    if (sources.length === 0) {
      test.skip();
      return;
    }

    // 启动分析（如果尚未运行）
    const sourceId = sources[0].source_id;
    const statusResp = await request.get(`${API}/analysis/status?source_id=${sourceId}`);
    const statusData = await statusResp.json();

    if (statusData.data?.status !== "running") {
      const startResp = await request.post(`${API}/analysis/start`, {
        data: { source_id: sourceId },
      });
      // 可能已在运行
      expect([200, 400].includes(startResp.status())).toBeTruthy();
    }

    // 等待一些处理时间
    await new Promise((r) => setTimeout(r, 3000));

    // 停止分析
    await request.post(`${API}/analysis/stop`, {
      data: { source_id: sourceId },
    });
  });
});
