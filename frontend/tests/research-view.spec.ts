import { expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import ElementPlus from 'element-plus'

import ResearchForm from '../src/components/research/ResearchForm.vue'
import ResearchReport from '../src/components/research/ResearchReport.vue'
import ToolAuditTimeline from '../src/components/research/ToolAuditTimeline.vue'

it('prefills a symbol supplied by navigation', () => {
  const wrapper = mount(ResearchForm, {
    props: { running: false, initialSymbol: '510300.SH' },
    global: { plugins: [ElementPlus] },
  })

  expect(wrapper.get('input').element.value).toBe('510300.SH')
})

it('renders Markdown and removes unsafe HTML', async () => {
  const wrapper = mount(ResearchReport, {
    props: {
      markdown:
        '# 研究结论\n\n- 保持谨慎\n\n<a href="https://example.com">来源</a>' +
        '<img src=x onerror="alert(1)"><script>alert(1)</script>',
    },
  })
  await wrapper.vm.$nextTick()

  expect(wrapper.get('h1').text()).toBe('研究结论')
  expect(wrapper.get('li').text()).toBe('保持谨慎')
  expect(wrapper.html()).not.toContain('onerror')
  expect(wrapper.html()).not.toContain('<script')
  expect(wrapper.get('a').attributes('target')).toBe('_blank')
  expect(wrapper.get('a').attributes('rel')).toBe('noopener noreferrer')
})

it('shows a zero-tool audit message for a completed report', () => {
  const wrapper = mount(ToolAuditTimeline, {
    props: { phase: 'COMPLETE', events: [], toolCalls: [] },
    global: { plugins: [ElementPlus] },
  })

  expect(wrapper.text()).toContain('本次报告未使用外部行情工具')
})

it('shows live tool progress while research is running', () => {
  const wrapper = mount(ToolAuditTimeline, {
    props: {
      phase: 'RUNNING',
      events: [
        {
          event_type: 'TOOL_STARTED',
          message: 'Tool started: get_market_snapshot',
          payload: { tool_name: 'get_market_snapshot' },
        },
      ],
      toolCalls: [],
    },
    global: { plugins: [ElementPlus] },
  })

  expect(wrapper.text()).toContain('get_market_snapshot')
})
