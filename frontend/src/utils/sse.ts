// AI2BI Phase 0 SSE 解析器 — 以空行边界解码，串联分行 data:，容错分块、未知事件和 JSON 解析失败。

export interface SseDecodeOptions {
  onEvent?: (event: { type: string; [k: string]: any }) => void
  onError?: (err: Error) => void
}

/**
 * 增量解码 SSE 字节流。
 * 返回一个可追加 chunk 的处理器；每次调用返回本次追加产生的事件列表。
 */
export function createSseDecoder(opts: SseDecodeOptions = {}) {
  let buffer = ''

  function processLine(line: string, emitter: (obj: any) => void) {
    if (line.startsWith('data:')) {
      const payload = line.slice(5).trim()
      if (!payload) return
      // 兼容后端 `data:{json}` 与标准 `data: {json}`
      if (payload.startsWith('{')) {
        try {
          const obj = JSON.parse(payload)
          emitter(obj)
        } catch (e) {
          opts.onError?.(e as Error)
        }
      }
    }
    // 忽略 event:/id:/retry: 等元行（本后端未使用）
  }

  function push(chunk: string): Array<{ type: string; [k: string]: any }> {
    buffer += chunk
    const events: Array<{ type: string; [k: string]: any }> = []
    const parts = buffer.split('\n\n')
    // 最后一个可能是未完成的帧
    buffer = parts.pop() ?? ''

    for (const frame of parts) {
      const lines = frame.split('\n')
      const dataLines: string[] = []
      for (const line of lines) {
        if (line.startsWith('data:')) {
          dataLines.push(line.slice(5).trim())
        }
      }
      if (dataLines.length === 0) continue
      const payload = dataLines.join('\n')
      if (!payload.startsWith('{')) continue
      try {
        const obj = JSON.parse(payload)
        if (obj && typeof obj.type === 'string') {
          events.push(obj)
          opts.onEvent?.(obj)
        }
      } catch (e) {
        opts.onError?.(e as Error)
      }
    }
    return events
  }

  return { push }
}

/**
 * 一次性解析完整 SSE 文本（用于测试/非流式）。
 */
export function parseSseText(text: string): Array<{ type: string; [k: string]: any }> {
  const decoder = createSseDecoder()
  return decoder.push(text)
}