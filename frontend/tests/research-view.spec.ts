import { expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import AnalysisResult from '../src/components/research/AnalysisResult.vue'

it('renders insufficient data without directional action styling', () => {
  const wrapper = mount(AnalysisResult, {
    props: {
      analysis: {
        status: 'INSUFFICIENT_DATA',
        market_view: 'UNCERTAIN',
        confidence: 0,
        horizon: '20 trading days',
        summary: '数据不足，无法形成可靠结论。',
        supporting_evidence: [],
        opposing_evidence: [],
        risks: ['行情数据不完整'],
        invalidation_conditions: [],
        data_cutoff: '2026-07-11T00:00:00Z',
        model_name: 'deepseek-v4-pro',
        prompt_version: 'research-v1',
        symbol: '600519.SH',
        security_name: 'Test',
        generated_at: '2026-07-11T00:01:00Z',
      },
    },
  })

  expect(wrapper.classes()).toContain('analysis-result')
  expect(wrapper.classes()).not.toContain('is-bullish')
  expect(wrapper.classes()).not.toContain('is-bearish')
  expect(wrapper.text()).toContain('数据不足')
})

it('keeps long evidence in a wrapping evidence row', () => {
  const statement = '这是一段很长的公告证据'.repeat(30)
  const wrapper = mount(AnalysisResult, {
    props: {
      analysis: {
        status: 'COMPLETE',
        market_view: 'NEUTRAL',
        confidence: 0.5,
        horizon: '20 trading days',
        summary: '中性',
        supporting_evidence: [{ evidence_id: 'e-1', statement }],
        opposing_evidence: [],
        risks: [],
        invalidation_conditions: [],
        data_cutoff: '2026-07-11T00:00:00Z',
        model_name: 'deepseek-v4-pro',
        prompt_version: 'research-v1',
        symbol: '600519.SH',
        security_name: 'Test',
        generated_at: '2026-07-11T00:01:00Z',
      },
    },
  })

  const evidence = wrapper.get('[data-testid="evidence-statement"]')
  expect(evidence.text()).toBe(statement)
  expect(evidence.classes()).toContain('evidence-statement')
})
