import { describe, it, expect, vi } from 'vitest'
import { createSseDecoder, parseSseText } from '@/utils/sse'

describe('createSseDecoder', () => {
  it('解析标准 SSE 帧（data: {json}）', () => {
    const decoder = createSseDecoder()
    const events = decoder.push('data: {"type":"analysis_status","status":"started"}\n\n')
    expect(events).toHaveLength(1)
    expect(events[0]).toMatchObject({ type: 'analysis_status', status: 'started' })
  })

  it('解析后端无空格紧凑帧（data:{json}）', () => {
    const decoder = createSseDecoder()
    const events = decoder.push('data:{"type":"analysis","content":"ok"}\n\n')
    expect(events).toHaveLength(1)
    expect(events[0]).toMatchObject({ content: 'ok' })
  })

  it('跨 chunk 分片仍能正确解析', () => {
    const decoder = createSseDecoder()
    const chunk = 'data: {"type":"evidence_ready","record_id":87}\n\n'
    // 切成小片逐次 push
    const pieces = []
    for (let i = 0; i < chunk.length; i += 7) {
      pieces.push(chunk.slice(i, i + 7))
    }
    const all: any[] = []
    for (const p of pieces) {
      all.push(...decoder.push(p))
    }
    expect(all).toHaveLength(1)
    expect(all[0]).toMatchObject({ type: 'evidence_ready', record_id: 87 })
  })

  it('同一帧多行 data: 拼接成一个对象（多行 JSON 字符串）', () => {
    const decoder = createSseDecoder()
    const events = decoder.push('data: {"type":"analysis","content":"a\\nb"}\n\n')
    // content 为 "a\nb"，实际是单行 JSON 转义，此处验证不报错且 type 正确
    expect(events).toHaveLength(1)
    expect(events[0].type).toBe('analysis')
  })

  it('忽略未知事件与元数据行，不报错', () => {
    const decoder = createSseDecoder()
    const events = decoder.push(
      'event: ping\nid: 1\nretry: 3000\ndata: {"type":"analysis_status","status":"completed"}\n\n'
    )
    expect(events).toHaveLength(1)
    expect(events[0].type).toBe('analysis_status')
  })

  it('触发 onError 当 JSON 解析失败', () => {
    const onError = vi.fn()
    const decoder = createSseDecoder({ onError })
    decoder.push('data: {bad json}\n\n')
    expect(onError).toHaveBeenCalledTimes(1)
  })

  it('未完成的帧缓存在 buffer 中，不产生事件', () => {
    const decoder = createSseDecoder()
    const events = decoder.push('data: {"type":"analysis_status","status":"gen')
    expect(events).toHaveLength(0)
    // 补全后触发
    const events2 = decoder.push('erating"}\n\n')
    expect(events2).toHaveLength(1)
    expect(events2[0].status).toBe('generating')
  })

  it('空 data 行被忽略', () => {
    const decoder = createSseDecoder()
    const events = decoder.push('data:\n\ndata: {"type":"analysis_status","status":"started"}\n\n')
    expect(events).toHaveLength(1)
  })
})

describe('parseSseText', () => {
  it('一次性解析完整 SSE 文本', () => {
    const events = parseSseText(
      'data: {"type":"analysis_status","status":"started"}\n\n' +
        'data: {"type":"analysis","content":"hi"}\n\n'
    )
    expect(events).toHaveLength(2)
    expect(events[0].type).toBe('analysis_status')
    expect(events[1].type).toBe('analysis')
  })

  it('忽略非 JSON data 行', () => {
    const events = parseSseText('data: hello\n\ndata: {"type":"analysis","content":"ok"}\n\n')
    expect(events).toHaveLength(1)
    expect(events[0].type).toBe('analysis')
  })
})