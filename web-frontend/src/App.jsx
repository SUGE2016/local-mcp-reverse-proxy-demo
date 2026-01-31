import { useState, useRef, useEffect } from 'react'

function App() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [tools, setTools] = useState([])
  const messagesEndRef = useRef(null)

  // 滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 获取工具列表
  useEffect(() => {
    fetch('/api/tools')
      .then(res => res.json())
      .then(data => setTools(data.tools || []))
      .catch(err => console.error('获取工具列表失败:', err))
  }, [])

  // 发送消息
  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    setLoading(true)

    // 添加用户消息
    setMessages(prev => [...prev, { type: 'user', content: userMessage }])

    try {
      const response = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage })
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      let currentAssistantMessage = null

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n')

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') continue

            try {
              const event = JSON.parse(data)

              if (event.type === 'tool_call') {
                setMessages(prev => [...prev, {
                  type: 'tool_call',
                  tool: event.tool,
                  arguments: event.arguments
                }])
              } else if (event.type === 'tool_result') {
                setMessages(prev => [...prev, {
                  type: 'tool_result',
                  tool: event.tool,
                  result: event.result
                }])
              } else if (event.type === 'message') {
                setMessages(prev => [...prev, {
                  type: 'assistant',
                  content: event.content
                }])
              } else if (event.type === 'error') {
                setMessages(prev => [...prev, {
                  type: 'error',
                  content: event.content
                }])
              }
            } catch (e) {
              console.error('解析事件失败:', e)
            }
          }
        }
      }
    } catch (err) {
      console.error('发送消息失败:', err)
      setMessages(prev => [...prev, {
        type: 'error',
        content: '发送消息失败: ' + err.message
      }])
    } finally {
      setLoading(false)
    }
  }

  // 处理按键
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="min-h-screen bg-gray-100 flex flex-col">
      {/* 头部 */}
      <header className="bg-white shadow-sm p-4">
        <div className="max-w-4xl mx-auto flex justify-between items-center">
          <h1 className="text-xl font-bold text-gray-800">MCP Bridge Demo</h1>
          <div className="text-sm text-gray-500">
            可用工具: {tools.length}
          </div>
        </div>
      </header>

      {/* 消息列表 */}
      <main className="flex-1 overflow-auto p-4">
        <div className="max-w-4xl mx-auto space-y-4">
          {messages.length === 0 && (
            <div className="text-center text-gray-500 py-8">
              <p>开始对话吧！</p>
              {tools.length > 0 && (
                <div className="mt-4 text-left bg-white rounded-lg p-4 shadow">
                  <p className="font-medium mb-2">可用工具:</p>
                  <ul className="text-sm space-y-1">
                    {tools.map((tool, i) => (
                      <li key={i} className="text-gray-600">
                        <span className="font-mono bg-gray-100 px-1 rounded">{tool.name}</span>
                        <span className="ml-2 text-gray-400">{tool.description?.slice(0, 50)}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {messages.map((msg, i) => (
            <MessageItem key={i} message={msg} />
          ))}

          {loading && (
            <div className="flex items-center space-x-2 text-gray-500">
              <div className="animate-spin w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full"></div>
              <span>思考中...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* 输入框 */}
      <footer className="bg-white border-t p-4">
        <div className="max-w-4xl mx-auto flex space-x-4">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="输入消息..."
            className="flex-1 resize-none border rounded-lg p-3 focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={1}
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            发送
          </button>
        </div>
      </footer>
    </div>
  )
}

// 消息组件
function MessageItem({ message }) {
  const { type, content, tool, arguments: args, result } = message

  if (type === 'user') {
    return (
      <div className="flex justify-end">
        <div className="bg-blue-500 text-white rounded-lg px-4 py-2 max-w-[80%]">
          {content}
        </div>
      </div>
    )
  }

  if (type === 'assistant') {
    return (
      <div className="flex justify-start">
        <div className="bg-white shadow rounded-lg px-4 py-2 max-w-[80%]">
          <pre className="whitespace-pre-wrap font-sans">{content}</pre>
        </div>
      </div>
    )
  }

  if (type === 'tool_call') {
    return (
      <div className="flex justify-start">
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-2 max-w-[80%]">
          <div className="text-sm text-yellow-700 font-medium">调用工具: {tool}</div>
          <pre className="text-xs text-gray-600 mt-1 overflow-auto">
            {JSON.stringify(args, null, 2)}
          </pre>
        </div>
      </div>
    )
  }

  if (type === 'tool_result') {
    return (
      <div className="flex justify-start">
        <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-2 max-w-[80%]">
          <div className="text-sm text-green-700 font-medium">工具结果: {tool}</div>
          <pre className="text-xs text-gray-600 mt-1 overflow-auto max-h-40">
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      </div>
    )
  }

  if (type === 'error') {
    return (
      <div className="flex justify-start">
        <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-2 max-w-[80%]">
          <div className="text-sm text-red-700">{content}</div>
        </div>
      </div>
    )
  }

  return null
}

export default App
