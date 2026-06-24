import { useState, useRef, useEffect, useCallback, createContext, useContext } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Sparkles, Brain, Wrench, ChevronRight, ChevronDown, CheckCircle, AlertCircle, Loader2, ArrowDown } from 'lucide-react';
import { getProviderConfig, getConversationMessages, createMessage, streamResumeAssistant, type ConversationMessage, type TextBlock, type ToolUseBlock, type ToolResultBlock, type SSEEvent, type ProviderConfig } from '../../lib/api';
import { useResumeStore } from '../../stores/resume-store';
import type { ResumeSection } from '../../types/resume';

interface ToolCall {
  id: string;
  name: string;
  input: Record<string, unknown>;
  status: 'executing' | 'done';
  result: {
    isError: boolean;
    content: string;
    section_content?: Record<string, unknown>;
  } | null;
}

interface StreamingMessage {
  bubbleId: string;
  status: 'streaming' | 'done' | 'error';
  thinking: { visible: boolean; content: string } | null;
  isThinkingActive: boolean;
  text: string;
  toolCalls: ToolCall[];
}

const BUTTON_SIZE = 48;

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(value, max));

const generateUniqueId = () =>
  `msg_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;

function snakeToCamel(obj: Record<string, unknown>): Record<string, unknown> {
  if (typeof obj !== 'object' || obj === null) return obj;
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(obj)) {
    const camelKey = key.replace(/_([a-z])/g, (_, c) => c.toUpperCase());
    if (typeof value === 'object' && value !== null && !Array.isArray(value) && !(value instanceof Date)) {
      result[camelKey] = snakeToCamel(value as Record<string, unknown>);
    } else if (Array.isArray(value)) {
      result[camelKey] = value.map((item) =>
        typeof item === 'object' && item !== null ? snakeToCamel(item as Record<string, unknown>) : item
      );
    } else {
      result[camelKey] = value;
    }
  }
  return result;
}

interface Position {
  x: number;
  y: number;
}

interface AIChatContextValue {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
}

const AIChatContext = createContext<AIChatContextValue | null>(null);

export function useAIChat() {
  const ctx = useContext(AIChatContext);
  if (!ctx) {
    throw new Error('useAIChat must be used within AIChatProvider');
  }
  return ctx;
}

interface AIChatProviderProps {
  children: React.ReactNode;
}

export function AIChatProvider({ children }: AIChatProviderProps) {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <AIChatContext.Provider value={{ isOpen, setIsOpen }}>
      {children}
    </AIChatContext.Provider>
  );
}

export function DraggableAIChatButton() {
  const [position, setPosition] = useState<Position>(() => {
    // 每次进入页面重置为默认位置
    return { x: window.innerWidth - BUTTON_SIZE - 24, y: window.innerHeight - BUTTON_SIZE - 24 };
  });
  const { isOpen, setIsOpen } = useAIChat();
  const dragState = useRef({ isDragging: false, startX: 0, startY: 0, startPosX: 0, startPosY: 0 });

  const actualPosition = position;

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button !== 0) return;
    dragState.current = {
      isDragging: true,
      startX: e.clientX,
      startY: e.clientY,
      startPosX: actualPosition.x,
      startPosY: actualPosition.y,
    };
  }, [actualPosition]);

  const handleMouseMove = useCallback((e: MouseEvent) => {
    if (!dragState.current.isDragging) return;
    const deltaX = e.clientX - dragState.current.startX;
    const deltaY = e.clientY - dragState.current.startY;
    const newX = dragState.current.startPosX + deltaX;
    const newY = dragState.current.startPosY + deltaY;
    const maxX = window.innerWidth - BUTTON_SIZE;
    const maxY = window.innerHeight - BUTTON_SIZE;
    setPosition({
      x: clamp(newX, 0, maxX),
      y: clamp(newY, 0, maxY),
    });
  }, []);

  const handleMouseUp = useCallback(() => {
    dragState.current.isDragging = false;
  }, []);

  useEffect(() => {
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [handleMouseMove, handleMouseUp]);

  const handleClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    e.nativeEvent.stopImmediatePropagation();
    const movedX = e.clientX - dragState.current.startX;
    const movedY = e.clientY - dragState.current.startY;
    const distance = Math.sqrt(movedX * movedX + movedY * movedY);
    if (distance < 5) {
      setIsOpen(!isOpen);
    }
  }, [setIsOpen, isOpen]);

  return (
    <>
      <div
        style={{
          position: 'fixed',
          left: actualPosition.x,
          top: actualPosition.y,
          zIndex: 50,
        }}
      >
        <button
          type="button"
          data-ai-button
          onMouseDown={handleMouseDown}
          onClick={handleClick}
          className={`
            group relative flex h-12 w-12 items-center justify-center rounded-full
            bg-pink-500
            hover:bg-pink-600
            active:scale-95
            transition-all duration-200
            cursor-grab
          `}
        >
          <Sparkles className="h-5 w-5 text-white" />
        </button>
      </div>

      {isOpen && (
        <AIChatDialog
          position={actualPosition}
          onClose={() => setIsOpen(false)}
          onMouseDown={handleMouseDown}
        />
      )}
    </>
  );
}

interface AIChatDialogProps {
  position: Position;
  onClose: () => void;
  onMouseDown: (e: React.MouseEvent) => void;
}

function AIChatDialog({ position, onClose, onMouseDown }: AIChatDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [dialogHeight, setDialogHeight] = useState(590);
  const [currentModel, setCurrentModel] = useState('');
  const [providerConfig, setProviderConfig] = useState<ProviderConfig | null>(null);
  const [expandedMessages, setExpandedMessages] = useState<Set<string>>(new Set());
  const [expandedToolCalls, setExpandedToolCalls] = useState<Set<string>>(new Set());
  const [expandedToolResults, setExpandedToolResults] = useState<Set<string>>(new Set());
  const [messages, setMessages] = useState<ConversationMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [input, setInput] = useState('');
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [streamingMessage, setStreamingMessage] = useState<StreamingMessage | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);

  // ✅ FIX: ref 与 state 保持同步，避免在 updater 内嵌套 setMessages
  const streamingMessageRef = useRef<StreamingMessage | null>(null);

  const isDoneRef = useRef(false);
  const { currentResume } = useResumeStore();
  const conversationId = currentResume?.id;
  const eventSourceRef = useRef<EventSource | null>(null);

  // ✅ FIX: 统一更新 state + ref 的辅助函数
  const updateStreaming = useCallback(
    (updater: (prev: StreamingMessage | null) => StreamingMessage | null) => {
      setStreamingMessage((prev) => {
        const next = updater(prev);
        streamingMessageRef.current = next;
        return next;
      });
    },
    [],
  );

  const toggleThinking = (key: string) => {
    setExpandedMessages((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  };

  const toggleToolCall = (id: string) => {
    setExpandedToolCalls((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleToolResult = (id: string) => {
    setExpandedToolResults((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // ✅ 智能自动滚动控制
  const autoScrollRef = useRef(true);

  const scrollToBottom = useCallback((force = false) => {
    if (!scrollRef.current) return;
    if (force) {
      autoScrollRef.current = true;
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      return;
    }
    if (autoScrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, []);

  const handleScroll = useCallback(() => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    const isAtBottom = distanceFromBottom < 10;

    if (isAtBottom) {
      autoScrollRef.current = true;
      setShowScrollButton(false);
    } else {
      autoScrollRef.current = false;
      setShowScrollButton(distanceFromBottom > 100);
    }
  }, []);

  useEffect(() => {
    if (dialogRef.current) {
      setDialogHeight(dialogRef.current.offsetHeight);
    }
  }, []);

  useEffect(() => {
    getProviderConfig().then((config) => {
      setProviderConfig(config);
      const model = config.providers[config.active]?.model;
      if (model) {
        setCurrentModel(model);
      }
    });
  }, []);

  useEffect(() => {
    if (!conversationId) return;
    setLoading(true);
    getConversationMessages(conversationId)
      .then((data) => {
        const welcomeMessage: ConversationMessage = {
          id: -1,
          conversationId: conversationId || '',
          role: 'assistant',
          content: [{ type: 'text', text: '你好！我是你的简历优化助手。告诉我你想改进简历的哪个部分？' }],
          reasoning: null,
          createdAt: null,
        };
        setMessages([welcomeMessage, ...data]);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [conversationId]);

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingMessage, scrollToBottom]);

  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  const handleSend = useCallback(async () => {
    if (!input.trim() || !conversationId || !providerConfig) return;

    const provider = providerConfig.providers[providerConfig.active];
    if (!provider.apiKey || !provider.baseUrl || !provider.model) return;

    const userText = input.trim();
    setInput('');
    setIsStreaming(true);

    isDoneRef.current = false;

    const userMessage: ConversationMessage = {
      id: generateUniqueId() as any,
      conversationId,
      role: 'user',
      content: [{ type: 'text', text: userText }],
      reasoning: null,
      createdAt: null,
    };
    setMessages((prev) => {
      const filtered = prev.filter((msg) => {
        if (msg.role !== 'assistant') return true;
        const textBlock = msg.content.find((b) => b.type === 'text');
        if (textBlock && 'text' in textBlock && typeof textBlock.text === 'string') {
          return !textBlock.text.startsWith('❌ Error:');
        }
        return true;
      });
      return [...filtered, userMessage];
    });
    scrollToBottom(true);

    await createMessage({ conversationId, userInput: userText });

    // ✅ FIX: 用 updateStreaming 初始化
    updateStreaming(() => ({
      bubbleId: String(Date.now()),
      status: 'streaming',
      thinking: null,
      isThinkingActive: false,
      text: '',
      toolCalls: [],
    }));

    const { eventSource, cleanup } = streamResumeAssistant(
      {
        resumeId: conversationId,
        type: providerConfig.active,
        baseUrl: provider.baseUrl,
        apiKey: provider.apiKey,
        model: provider.model,
        input: userText,
      },
      (event: SSEEvent) => {
        const validTypes = ['next', 'thinking_start', 'thinking_delta', 'text_start', 'text_delta', 'tool_use', 'tool_result', 'done', 'error'];
        if (!validTypes.includes(event.type)) return;

        switch (event.type) {
          case 'next': {
            const prev = streamingMessageRef.current;
            if (!prev) break;

            const hasContent = prev.text || prev.thinking?.content || prev.toolCalls.length > 0;
            if (!hasContent) break;

            const hasToolCalls = prev.toolCalls.length > 0;
            const pendingToolCalls = prev.toolCalls.some((tc) => tc.result === null);

            if (pendingToolCalls) {
              break;
            }

            const hasToolResults =
              hasToolCalls && prev.toolCalls.some((tc) => tc.result?.content || tc.result?.section_content);

            const toolUseContent: ToolUseBlock[] = prev.toolCalls.map((tc) => ({
              type: 'tool_use' as const,
              id: tc.id,
              name: tc.name,
              input: tc.input,
            }));

            const assistantMessage: ConversationMessage = {
              id: generateUniqueId() as any,
              conversationId,
              role: 'assistant',
              content: [
                ...(prev.text ? [{ type: 'text' as const, text: prev.text }] : []),
                ...(hasToolCalls ? toolUseContent : []),
              ],
              reasoning: prev.thinking?.content || null,
              createdAt: null,
            };

            if (hasToolResults) {
              const toolResultContent: ToolResultBlock[] = prev.toolCalls
                .filter((tc) => tc.result?.content || tc.result?.section_content)
                .map((tc) => ({
                  type: 'tool_result' as const,
                  toolUseId: tc.id,
                  isError: tc.result!.isError,
                  content: tc.result!.content || '',
                }));
              const toolUserMessage: ConversationMessage = {
                id: generateUniqueId() as any,
                conversationId,
                role: 'user',
                content: toolResultContent,
                reasoning: null,
                createdAt: null,
              };
              setMessages((msgs) => [...msgs, assistantMessage, toolUserMessage]);
            } else {
              setMessages((msgs) => [...msgs, assistantMessage]);
            }

            updateStreaming(() => ({
              bubbleId: generateUniqueId(),
              status: 'streaming',
              thinking: null,
              isThinkingActive: false,
              text: '',
              toolCalls: [],
            }));
            isDoneRef.current = false;
            scrollToBottom();
            break;
          }

          case 'thinking_start':
            updateStreaming((prev) =>
              prev ? { ...prev, isThinkingActive: true, thinking: { visible: false, content: '' } } : null,
            );
            break;

          case 'thinking_delta':
            updateStreaming((prev) => {
              if (!prev) return null;
              return {
                ...prev,
                thinking: prev.thinking
                  ? { ...prev.thinking, content: prev.thinking.content + (event.data.text as string) }
                  : null,
              };
            });
            scrollToBottom();
            break;

          case 'text_start':
            updateStreaming((prev) => (prev ? { ...prev, isThinkingActive: false, text: '' } : null));
            break;

          case 'text_delta':
            updateStreaming((prev) => {
              if (!prev) return null;
              return { ...prev, text: prev.text + (event.data.text as string) };
            });
            scrollToBottom();
            break;

          case 'tool_use': {
            const newToolCall: ToolCall = {
              id: event.data.id as string,
              name: event.data.name as string,
              input: event.data.input as Record<string, unknown>,
              status: 'executing',
              result: null,
            };
            if (streamingMessageRef.current) {
              streamingMessageRef.current = {
                ...streamingMessageRef.current,
                isThinkingActive: false,
                toolCalls: [...streamingMessageRef.current.toolCalls, newToolCall],
              };
            }
            setExpandedToolCalls((s) => new Set(s).add(newToolCall.id));
            setStreamingMessage(streamingMessageRef.current);
            scrollToBottom();
            break;
          }

          case 'tool_result': {
            const toolUseId = event.data.tool_use_id as string;
            const sectionContent = event.data.section_content as Record<string, unknown> | undefined;
            const isError = event.data.is_error as boolean;
            const content = event.data.content as string;


            const toolCall = streamingMessageRef.current?.toolCalls.find((tc) => tc.id === toolUseId);
            const isUpdateSection = toolCall?.name === 'update_section';
            const isAddSection = toolCall?.name === 'add_section';

            // 同步更新 ref，确保 next 事件能立即看到更新后的状态
            if (streamingMessageRef.current) {
              streamingMessageRef.current = {
                ...streamingMessageRef.current,
                toolCalls: streamingMessageRef.current.toolCalls.map((tc) =>
                  tc.id === toolUseId
                    ? { ...tc, status: 'done' as const, result: { isError, content, section_content: sectionContent } }
                    : tc
                ),
              };
            }

            setExpandedToolResults((s) => new Set(s).add(toolUseId));
            setStreamingMessage(streamingMessageRef.current);

            // ✅ update_section 工具结果：立即更新前端 UI，不触发数据库保存
            if (isUpdateSection && !isError && sectionContent) {
              const sectionId = sectionContent.id as string;
              const rawSectionData = (sectionContent as any).data as Record<string, unknown>;
              if (sectionId && rawSectionData) {
                const sectionData = snakeToCamel(rawSectionData);
                useResumeStore.setState((state) => {
                  const sections = state.sections.map((s) =>
                    s.id === sectionId ? { ...s, content: { ...s.content, ...sectionData } } : s
                  );
                  return {
                    sections,
                    currentResume: state.currentResume ? { ...state.currentResume, sections } : null,
                    isDirty: false,
                  };
                });
              }
            } else if (isAddSection && !isError && sectionContent) {
              const newSection = snakeToCamel(sectionContent as unknown as Record<string, unknown>) as unknown as ResumeSection;
              const sectionId = newSection.id;
              const sectionType = newSection.type;
              const sectionTitle = newSection.title;
              useResumeStore.setState((state) => {
                const existingIndex = state.sections.findIndex((s) => s.id === sectionId || (s.type === sectionType && s.title === sectionTitle));
                let sections: ResumeSection[];
                if (existingIndex >= 0) {
                  sections = state.sections.map((s, i) =>
                    i === existingIndex ? { ...s, ...newSection, visible: true } : s
                  );
                } else {
                  sections = [...state.sections, { ...newSection, visible: true }];
                }
                return {
                  sections,
                  currentResume: state.currentResume ? { ...state.currentResume, sections } : null,
                  isDirty: false,
                };
              });
            }

            scrollToBottom();
            break;
          }

          // ✅ FIX: done 分支直接读 ref，setMessages 独立调用，彻底避免 updater 嵌套
          case 'done': {
            if (isDoneRef.current) break;
            isDoneRef.current = true;

            const prev = streamingMessageRef.current;

            // 先清空 streaming UI
            streamingMessageRef.current = null;
            setStreamingMessage(null);
            setIsStreaming(false);
            cleanup();

            if (!prev) break;

            const hasToolCalls = prev.toolCalls.length > 0;
            const hasToolResults =
              hasToolCalls && prev.toolCalls.some((tc) => tc.result?.content || tc.result?.section_content);

            const toolUseContent: ToolUseBlock[] = prev.toolCalls.map((tc) => ({
              type: 'tool_use' as const,
              id: tc.id,
              name: tc.name,
              input: tc.input,
            }));

            const assistantMessage: ConversationMessage = {
              id: generateUniqueId() as any,
              conversationId,
              role: 'assistant',
              content: [
                ...(prev.text ? [{ type: 'text' as const, text: prev.text }] : []),
                ...(hasToolCalls ? toolUseContent : []),
              ],
              reasoning: prev.thinking?.content || null,
              createdAt: null,
            };

            if (hasToolResults) {
              const toolResultContent: ToolResultBlock[] = prev.toolCalls
                .filter((tc) => tc.result?.content || tc.result?.section_content)
                .map((tc) => ({
                  type: 'tool_result' as const,
                  toolUseId: tc.id,
                  isError: tc.result!.isError,
                  content: tc.result!.content || '',
                }));
              const toolUserMessage: ConversationMessage = {
                id: generateUniqueId() as any,
                conversationId,
                role: 'user',
                content: toolResultContent,
                reasoning: null,
                createdAt: null,
              };
              setMessages((msgs) => [...msgs, assistantMessage, toolUserMessage]);
            } else {
              setMessages((msgs) => [...msgs, assistantMessage]);
            }
            break;
          }

          case 'error': {
            isDoneRef.current = true;
            const errorMessage = event.data.message as string;
            const errorMsg: ConversationMessage = {
              id: generateUniqueId() as any,
              conversationId,
              role: 'assistant',
              content: [{ type: 'text' as const, text: `❌ Error: ${errorMessage}` }],
              reasoning: null,
              createdAt: null,
            };
            setMessages((msgs) => [...msgs, errorMsg]);
            streamingMessageRef.current = null;
            setStreamingMessage(null);
            setIsStreaming(false);
            cleanup();
            break;
          }
        }
      },
    );

    eventSourceRef.current = eventSource;
  }, [input, conversationId, providerConfig, updateStreaming, scrollToBottom]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const dialogStyle = {
    position: 'fixed' as const,
    left: position.x + 56 - 500 - 46 + 47,
    top: position.y - dialogHeight - 5,
    zIndex: 51,
  };

  return (
    <div
      ref={dialogRef}
      style={dialogStyle}
      className="w-[500px] bg-background border border-border rounded-lg shadow-xl overflow-hidden"
    >
      <div
        role="toolbar"
        className="flex items-center justify-between border-b border-border px-4 py-2 cursor-move"
        onMouseDown={onMouseDown}
      >
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-pink-500 to-purple-600">
            <Sparkles className="h-3.5 w-3.5 text-white" />
          </div>
          <span className="font-medium text-foreground">AI 助手</span>
        </div>
        <button
          type="button"
          onClick={(e) => { e.stopPropagation(); onClose(); }}
          className="rounded-md p-1 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors"
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <title>关闭</title>
            <line x1="3" y1="8" x2="13" y2="8" />
          </svg>
        </button>
      </div>

      <div className="flex flex-col">
        <div ref={scrollRef} className="relative h-[460px] overflow-y-auto p-4 space-y-3 bg-card" onScroll={handleScroll}>
          {loading ? (
            <div className="text-center text-muted-foreground text-xs py-8">加载中...</div>
          ) : messages.length === 0 ? (
            <div className="text-center text-muted-foreground text-xs py-8">暂无消息</div>
          ) : (
            messages.map((msg, index) => {
              const isToolResultOnlyUser =
                msg.role === 'user' && msg.content.some((c) => c.type === 'tool_result');
              if (isToolResultOnlyUser) return null;

              if (msg.role === 'user') {
                const textBlockForUser = msg.content.find((c) => c.type === 'text') as TextBlock | undefined;
                const userText = textBlockForUser?.text || '消息发送成功';
                return (
                  <div key={msg.id} className="flex justify-end">
                    <div className="max-w-[85%] rounded-2xl rounded-br-md px-3 py-2 text-xs leading-relaxed bg-primary text-primary-foreground">
                      {userText}
                    </div>
                  </div>
                );
              }

              const reasoning = msg.reasoning;
              const textBlocks = msg.content.filter((c): c is TextBlock => c.type === 'text');
              const toolUseBlocks = msg.content.filter((c): c is ToolUseBlock => c.type === 'tool_use');

              const nextMsg = messages[index + 1];
              const toolResults =
                nextMsg?.role === 'user'
                  ? nextMsg.content.filter((c): c is ToolResultBlock => c.type === 'tool_result')
                  : [];

              const msgKey = `msg-${msg.id}`;

              return (
                <div key={msg.id} className="flex gap-2">
                  <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-pink-500 to-purple-600 text-white">
                    <Sparkles className="h-3 w-3" />
                  </div>
                  <div className="max-w-[85%] rounded-2xl rounded-bl-md space-y-2 px-3 py-2 text-xs leading-relaxed bg-secondary text-secondary-foreground">
                    {reasoning && (
                      <>
                        <button
                          type="button"
                          className="text-[10px] text-muted-foreground flex items-center gap-1"
                          onClick={() => toggleThinking(`${msgKey}-reasoning`)}
                        >
                          {expandedMessages.has(`${msgKey}-reasoning`) ? (
                            <ChevronDown className="h-3 w-3" />
                          ) : (
                            <ChevronRight className="h-3 w-3" />
                          )}
                          <span className="italic flex items-center gap-1">
                            <Brain className="h-3 w-3" /> 思考过程
                          </span>
                        </button>
                        {expandedMessages.has(`${msgKey}-reasoning`) && (
                          <div className="text-[10px] text-muted-foreground pl-4 border-l border-border whitespace-pre-wrap">
                            {reasoning}
                          </div>
                        )}
                      </>
                    )}
                    {textBlocks.map((block, i) => (
                      <div
                        key={`${msgKey}-text-${block.type}-${i}`}
                        className="whitespace-pre-wrap text-xs leading-relaxed text-foreground"
                      >
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            h1: ({ children }) => <h1 className="text-base font-bold text-foreground mb-1">{children}</h1>,
                            h2: ({ children }) => <h2 className="text-sm font-semibold text-foreground mb-1">{children}</h2>,
                            h3: ({ children }) => <h3 className="text-xs font-semibold text-foreground mb-1">{children}</h3>,
                            h4: ({ children }) => <h4 className="text-xs font-medium text-foreground mb-1">{children}</h4>,
                            p: ({ children }) => <p className="text-foreground mb-1">{children}</p>,
                            ul: ({ children }) => <ul className="list-disc list-inside text-foreground mb-1 space-y-0.5">{children}</ul>,
                            ol: ({ children }) => <ol className="list-decimal list-inside text-foreground mb-1 space-y-0.5">{children}</ol>,
                            li: ({ children }) => <li className="text-foreground">{children}</li>,
                            strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
                            em: ({ children }) => <em className="italic text-foreground">{children}</em>,
                            blockquote: ({ children }) => <blockquote className="border-l-2 border-border pl-2 text-muted-foreground italic mb-1">{children}</blockquote>,
                            a: ({ children }) => (
                              <span className="text-pink-400 cursor-pointer">{children}</span>
                            ),
                            table: ({ children }) => (
                              <table className="w-full text-xs border-collapse my-2">{children}</table>
                            ),
                            thead: ({ children }) => (
                              <thead className="bg-secondary text-secondary-foreground">{children}</thead>
                            ),
                            th: ({ children }) => (
                              <th className="border-border px-3 py-1 text-left font-medium text-foreground">
                                {children}
                              </th>
                            ),
                            td: ({ children }) => (
                              <td className="border-border px-3 py-1 text-foreground">{children}</td>
                            ),
                            tr: ({ children }) => (
                              <tr className="border-b border-[#3a3a3e]">{children}</tr>
                            ),
                          }}
                        >
                          {block.text}
                        </ReactMarkdown>
                      </div>
                    ))}
                    {toolUseBlocks.map((toolUse, i) => {
                      const result = toolResults[i];
                      const toolKey = `${msgKey}-tool-${i}`;
                      const resultKey = `${msgKey}-result-${i}`;
                      return (
                        <div key={toolKey} className="space-y-2">
                          <div className="rounded-lg border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-500/10 p-2 space-y-2">
                            <button
                              type="button"
                              className="text-[10px] text-indigo-700 dark:text-indigo-300 cursor-pointer hover:opacity-80 flex items-center gap-1 w-full"
                              onClick={() => toggleThinking(toolKey)}
                            >
                              {expandedMessages.has(toolKey) ? (
                                <ChevronDown className="h-3 w-3" />
                              ) : (
                                <ChevronRight className="h-3 w-3" />
                              )}
                              <Wrench className="h-3 w-3" />
                              <span>工具请求: {toolUse.name}</span>
                            </button>
                            {expandedMessages.has(toolKey) && (
                              <pre className="text-foreground whitespace-pre-wrap text-[10px] bg-muted rounded p-2 overflow-auto">
                                {JSON.stringify(toolUse.input, null, 2)}
                              </pre>
                            )}
                          </div>
                          {result && (
                            <div
                              className={`rounded-lg border p-2 space-y-2 ${result.isError
                                ? 'border-red-200 dark:border-red-500/30 bg-red-50 dark:bg-red-500/10'
                                : 'border-emerald-200 dark:border-emerald-500/30 bg-emerald-50 dark:bg-emerald-500/10'
                                }`}
                            >
                              <button
                                type="button"
                                className={`text-[10px] cursor-pointer hover:opacity-80 flex items-center gap-1 w-full ${result.isError ? 'text-red-700 dark:text-red-300' : 'text-emerald-700 dark:text-emerald-300'
                                  }`}
                                onClick={() => toggleThinking(resultKey)}
                              >
                                {expandedMessages.has(resultKey) ? (
                                  <ChevronDown className="h-3 w-3" />
                                ) : (
                                  <ChevronRight className="h-3 w-3" />
                                )}
                                {result.isError ? (
                                  <AlertCircle className="h-3 w-3" />
                                ) : (
                                  <CheckCircle className="h-3 w-3" />
                                )}
                                <span>执行结果</span>
                              </button>
                              {expandedMessages.has(resultKey) && (
                                <div
                                  className={`rounded p-2 text-[10px] ${result.isError
                                    ? 'bg-red-100 dark:bg-red-500/10 text-red-800 dark:text-red-300'
                                    : 'bg-emerald-100 dark:bg-emerald-500/10 text-emerald-800 dark:text-emerald-300'
                                    }`}
                                >
                                  {result.content}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              );
            })
          )}

          {streamingMessage && (
            <div className="flex gap-2">
              <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-pink-500 to-purple-600 text-white">
                <Sparkles className="h-3 w-3" />
              </div>
              <div className="max-w-[85%] rounded-2xl rounded-bl-md space-y-2 px-3 py-2 text-xs leading-relaxed bg-secondary text-secondary-foreground">
                {streamingMessage.thinking && (
                  <button
                    type="button"
                    className="text-[10px] text-muted-foreground flex items-center gap-1"
                    onClick={() =>
                      // ✅ FIX: 只切换 visible，不会触发任何 setMessages 副作用
                      updateStreaming((prev) =>
                        prev
                          ? {
                            ...prev,
                            thinking: prev.thinking
                              ? { ...prev.thinking, visible: !prev.thinking.visible }
                              : null,
                          }
                          : null,
                      )
                    }
                  >
                    {streamingMessage.thinking.visible ? (
                      <ChevronDown className="h-3 w-3" />
                    ) : (
                      <ChevronRight className="h-3 w-3" />
                    )}
                    <span className="italic flex items-center gap-1">
                      <Brain className="h-3 w-3" /> 思考过程
                    </span>
                    {streamingMessage.isThinkingActive && (
                      <span className="flex gap-0.5 ml-1">
                        <span className="w-1 h-1 rounded-full bg-pink-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                        <span className="w-1 h-1 rounded-full bg-pink-400 animate-bounce" style={{ animationDelay: '120ms' }} />
                        <span className="w-1 h-1 rounded-full bg-pink-400 animate-bounce" style={{ animationDelay: '240ms' }} />
                      </span>
                    )}
                  </button>
                )}
                {streamingMessage.thinking?.visible && (
                  <div className="text-[10px] text-muted-foreground pl-4 border-l border-border whitespace-pre-wrap">
                    {streamingMessage.thinking.content}
                  </div>
                )}
                {streamingMessage.text && (
                  <div className="whitespace-pre-wrap text-xs leading-relaxed text-foreground">
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm]}
                      components={{
                        h1: ({ children }) => <h1 className="text-base font-bold text-foreground mb-1">{children}</h1>,
                        h2: ({ children }) => <h2 className="text-sm font-semibold text-foreground mb-1">{children}</h2>,
                        h3: ({ children }) => <h3 className="text-xs font-semibold text-foreground mb-1">{children}</h3>,
                        h4: ({ children }) => <h4 className="text-xs font-medium text-foreground mb-1">{children}</h4>,
                        p: ({ children }) => <p className="text-foreground mb-1">{children}</p>,
                        ul: ({ children }) => <ul className="list-disc list-inside text-foreground mb-1 space-y-0.5">{children}</ul>,
                        ol: ({ children }) => <ol className="list-decimal list-inside text-foreground mb-1 space-y-0.5">{children}</ol>,
                        li: ({ children }) => <li className="text-foreground">{children}</li>,
                        strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
                        em: ({ children }) => <em className="italic text-foreground">{children}</em>,
                        blockquote: ({ children }) => <blockquote className="border-l-2 border-border pl-2 text-muted-foreground italic mb-1">{children}</blockquote>,
                        a: ({ children }) => <span className="text-pink-400 cursor-pointer">{children}</span>,
                      }}
                    >{streamingMessage.text}</ReactMarkdown>
                  </div>
                )}
                {streamingMessage.toolCalls.map((toolCall) => (
                  <div key={toolCall.id} className="space-y-2">
                    <div className="rounded-lg border border-indigo-200 dark:border-indigo-500/30 bg-indigo-50 dark:bg-indigo-500/10 p-2 space-y-2">
                      <button
                        type="button"
                        className="text-[10px] text-indigo-700 dark:text-indigo-300 cursor-pointer hover:opacity-80 flex items-center gap-1 w-full"
                        onClick={() => toggleToolCall(toolCall.id)}
                      >
                        {expandedToolCalls.has(toolCall.id) ? (
                          <ChevronDown className="h-3 w-3" />
                        ) : (
                          <ChevronRight className="h-3 w-3" />
                        )}
                        <Wrench className="h-3 w-3" />
                        <span>工具请求: {toolCall.name}</span>
                        {toolCall.status === 'executing' && (
                          <>
                            <span className="text-muted-foreground">执行中...</span>
                            <Loader2 className="h-3 w-3 animate-spin text-indigo-500 dark:text-indigo-400" />
                          </>
                        )}
                      </button>
                      {expandedToolCalls.has(toolCall.id) && (
                        <pre className="text-foreground whitespace-pre-wrap text-[10px] bg-muted rounded p-2 overflow-auto">
                          {JSON.stringify(toolCall.input, null, 2)}
                        </pre>
                      )}
                    </div>
                    {(toolCall.result || toolCall.status === 'executing') && (
                      <div
                        className={`rounded-lg border p-2 space-y-2 ${toolCall.status === 'executing'
                          ? 'border-purple-200 dark:border-purple-500/30 bg-purple-50 dark:bg-purple-500/10'
                          : toolCall.result!.isError
                            ? 'border-red-200 dark:border-red-500/30 bg-red-50 dark:bg-red-500/10'
                            : 'border-emerald-200 dark:border-emerald-500/30 bg-emerald-50 dark:bg-emerald-500/10'
                          }`}
                      >
                        <button
                          type="button"
                          className={`text-[10px] cursor-pointer hover:opacity-80 flex items-center gap-1 w-full ${toolCall.status === 'executing'
                            ? 'text-purple-700 dark:text-purple-300'
                            : toolCall.result!.isError
                              ? 'text-red-700 dark:text-red-300'
                              : 'text-emerald-700 dark:text-emerald-300'
                            }`}
                          onClick={() => toggleToolResult(toolCall.id)}
                        >
                          {expandedToolResults.has(toolCall.id) ? (
                            <ChevronDown className="h-3 w-3" />
                          ) : (
                            <ChevronRight className="h-3 w-3" />
                          )}
                          {toolCall.status === 'executing' ? (
                            <>
                              <Loader2 className="h-3 w-3 animate-spin text-purple-500 dark:text-purple-400" />
                              <span>执行中...</span>
                            </>
                          ) : toolCall.result!.isError ? (
                            <>
                              <AlertCircle className="h-3 w-3" />
                              <span>执行结果</span>
                            </>
                          ) : (
                            <>
                              <CheckCircle className="h-3 w-3" />
                              <span>执行结果</span>
                            </>
                          )}
                        </button>
                        {expandedToolResults.has(toolCall.id) && (
                          <div
                            className={`rounded p-2 text-[10px] ${toolCall.status === 'executing'
                              ? 'bg-purple-100 dark:bg-purple-500/10 text-purple-800 dark:text-purple-300'
                              : toolCall.result!.isError
                                ? 'bg-red-100 dark:bg-red-500/10 text-red-800 dark:text-red-300'
                                : 'bg-emerald-100 dark:bg-emerald-500/10 text-emerald-800 dark:text-emerald-300'
                              }`}
                          >
                            {toolCall.status === 'executing' ? '等待结果...' : toolCall.result!.content}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
                {!streamingMessage.text && !streamingMessage.thinking && streamingMessage.toolCalls.length === 0 && (
                  <div className="flex items-center gap-1 py-1">
                    <span className="w-1.5 h-1.5 rounded-full bg-pink-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-pink-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                    <span className="w-1.5 h-1.5 rounded-full bg-pink-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="relative mx-2 mb-2">
          {showScrollButton && (
            <button
              type="button"
              onClick={() => {
                scrollToBottom(true);
              }}
              className="absolute -top-10 left-1/2 -translate-x-1/2 flex h-8 w-8 items-center justify-center rounded-full bg-secondary text-secondary-foreground/90 hover:bg-secondary text-secondary-foreground text-foreground hover:text-foreground shadow-md transition-colors"
            >
              <ArrowDown className="h-4 w-4" />
            </button>
          )}
          <div className="flex flex-col rounded-2xl bg-secondary text-secondary-foreground overflow-hidden min-h-[98px]">
            <div className="flex-1 overflow-y-auto px-4 pt-3">
              <textarea
                placeholder="描述你想优化的内容..."
                rows={3}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                className="w-full bg-transparent text-foreground placeholder:text-muted-foreground border-none focus:outline-none resize-none text-xs"
              />
            </div>
            <div className="flex items-center justify-between px-4 pb-3">
              <div className="flex items-center gap-2 text-xs text-foreground">
                <span className="flex items-center gap-1">
                  <Sparkles className="h-3 w-3" />
                  {currentModel || '未配置模型'}
                </span>
              </div>
              <button
                type="button"
                onClick={handleSend}
                disabled={!input.trim() || isStreaming}
                className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-r from-pink-500 to-purple-600 text-white hover:from-pink-600 hover:to-purple-700 transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isStreaming ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <svg
                    width="14"
                    height="14"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    <title>发送</title>
                    <line x1="22" y1="2" x2="11" y2="13" />
                    <polygon points="22 2 15 22 11 13 2 9 22 2" />
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}