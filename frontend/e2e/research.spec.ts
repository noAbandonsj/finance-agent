import { expect, test } from '@playwright/test'

test('research, chart, history, and watchlist remain usable', async ({ page }) => {
  await page.goto('/research')
  await page.getByRole('button', { name: '开始研究' }).click()
  await expect(page.getByText('量价证据相互制衡，当前维持中性判断。')).toBeVisible()

  const paintedPixels = await page.locator('canvas').first().evaluate((canvas: HTMLCanvasElement) => {
    const context = canvas.getContext('2d')
    if (!context) return 0
    const data = context.getImageData(0, 0, canvas.width, canvas.height).data
    let painted = 0
    for (let index = 3; index < data.length; index += 4) {
      if (data[index] > 0) painted += 1
    }
    return painted
  })
  expect(paintedPixels).toBeGreaterThan(100)

  await page.getByRole('link', { name: '历史' }).click()
  await page.getByRole('row').nth(1).click()
  await expect(page.getByText('量价证据相互制衡，当前维持中性判断。')).toBeVisible()

  await page.getByRole('link', { name: '自选' }).click()
  await page.getByPlaceholder('输入股票或 ETF 代码').fill('510300')
  await page.getByRole('button', { name: '添加' }).click()
  await expect(page.getByText('510300.SH')).toBeVisible()
  await page.reload()
  await expect(page.getByText('510300.SH')).toBeVisible()
})

test('insufficient data stays visually non-directional', async ({ page }) => {
  await page.goto('/research')
  await page.getByPlaceholder('证券代码，如 600519').fill('510300')
  await page.getByRole('button', { name: '开始研究' }).click()

  await expect(page.getByText('数据不足，暂不形成方向判断。')).toBeVisible()
  await expect(page.locator('.analysis-result')).not.toHaveClass(/is-bullish|is-bearish/)
})
