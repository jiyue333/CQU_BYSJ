import { test, expect, type APIRequestContext } from "@playwright/test";

/**
 * Stage-1 region-only E2E smoke coverage.
 *
 * Default assumptions:
 * - backend API: http://127.0.0.1:8000/api
 * - frontend dev server: http://127.0.0.1:${FRONTEND_PORT:-3000}
 */

const API_ORIGIN = process.env.PLAYWRIGHT_API_ORIGIN ?? "http://127.0.0.1:8000";
const API = `${API_ORIGIN}/api`;

type SourceRecord = { source_id: string; name: string };
type RegionRecord = { region_id: string; name: string };

async function getFirstSource(request: APIRequestContext) {
  const response = await request.get(`${API}/sources`);
  expect(response.ok()).toBeTruthy();
  const payload = await response.json();
  const sources = (payload.data?.sources ?? []) as SourceRecord[];
  return sources[0] ?? null;
}

async function getRegions(request: APIRequestContext, sourceId: string) {
  const response = await request.get(`${API}/regions?source_id=${encodeURIComponent(sourceId)}`);
  expect(response.ok()).toBeTruthy();
  const payload = await response.json();
  return (payload.data?.regions ?? []) as RegionRecord[];
}

test.describe("CrowdFlow region-only frontend", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
    await page.waitForLoadState("networkidle");
  });

  test("loads the primary region-only surface without runtime errors", async ({ page }) => {
    const errors: string[] = [];
    const crosslineRequests: string[] = [];
    page.on("pageerror", (error) => errors.push(error.message));
    page.on("request", (request) => {
      if (request.url().includes("/api/crosslines")) {
        crosslineRequests.push(request.url());
      }
    });

    await page.reload();
    await page.waitForLoadState("networkidle");

    await expect(page.getByRole("heading", { name: "人流分析" })).toBeVisible();
    await expect(page.getByText("区域监测")).toBeVisible();
    await expect(page.getByRole("heading", { name: "数据查询" })).toBeVisible();
    await expect(page.getByRole("heading", { name: "趋势" })).toBeVisible();

    await expect(page.getByText("计数线")).toHaveCount(0);
    await expect(page.getByText("Cross-line")).toHaveCount(0);
    expect(errors).toHaveLength(0);
    expect(crosslineRequests).toHaveLength(0);
  });

  test("configuration drawer keeps region management and removes crossline management", async ({ page }) => {
    await page.getByRole("button", { name: "配置中心" }).click();

    await expect(page.getByRole("button", { name: "区域", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "阈值", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "模板", exact: true })).toBeVisible();
    await expect(page.getByRole("button", { name: "计数线" })).toHaveCount(0);
  });

  test("region APIs stay reachable for the stage-1 cutover", async ({ request }) => {
    const source = await getFirstSource(request);

    if (!source) {
      test.skip();
      return;
    }

    const regions = await getRegions(request, source.source_id);
    expect(Array.isArray(regions)).toBeTruthy();

    const statusResponse = await request.get(
      `${API}/analysis/status?source_id=${encodeURIComponent(source.source_id)}`
    );
    expect(statusResponse.ok()).toBeTruthy();
  });

  test("history query accepts region-scoped requests when a region exists", async ({ request }) => {
    const source = await getFirstSource(request);

    if (!source) {
      test.skip();
      return;
    }

    const regions = await getRegions(request, source.source_id);
    if (!regions.length) {
      test.skip();
      return;
    }

    const to = new Date();
    const from = new Date(to.getTime() - 30 * 60 * 1000);
    const region = regions[0];

    const historyResponse = await request.get(
      `${API}/history?source_id=${encodeURIComponent(source.source_id)}&region_id=${encodeURIComponent(region.region_id)}&from=${encodeURIComponent(from.toISOString())}&to=${encodeURIComponent(to.toISOString())}&interval=5m`
    );

    expect(historyResponse.ok()).toBeTruthy();
    const payload = await historyResponse.json();
    expect(Array.isArray(payload.data?.series ?? [])).toBeTruthy();
  });

  test("query and history toolbars expose region selectors instead of crossline selectors", async ({ page, request }) => {
    const source = await getFirstSource(request);
    if (!source) {
      test.skip();
      return;
    }

    const regions = await getRegions(request, source.source_id);
    if (!regions.length) {
      test.skip();
      return;
    }

    const selectors = page.locator("select.field--select");
    await expect(selectors).toHaveCount(4);
    await expect(page.locator(`select.field--select option[value="${regions[0].region_id}"]`)).toHaveCount(2);
    await expect(page.locator('select.field--select option[value=""]')).toHaveCount(2);
    await expect(page.getByRole("option", { name: "全局汇总" })).toHaveCount(1);
    await expect(page.getByRole("option", { name: "全部计数线" })).toHaveCount(0);
  });
});
