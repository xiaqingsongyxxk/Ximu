import { useState, useEffect, useRef } from 'react'
import { X, Eye, EyeOff, Loader2, ChevronDown, Settings, Cpu, Sun, Moon, Monitor } from 'lucide-react'
import { getProviderConfig, updateProviderConfig, switchProviderConfig, type ProviderType } from '../../lib/api'
import { useSettingsStore, type ThemeMode } from '../../stores/settings-store'

export interface SettingsModalProps {
  open: boolean
  onClose: () => void
}

export type SettingsTab = 'ai' | 'appearance' | 'editor'

const PROVIDER_OPTIONS: { value: ProviderType; label: string }[] = [
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Anthropic' },
]

export default function SettingsModal({ open, onClose }: SettingsModalProps) {
  const [tab, setTab] = useState<SettingsTab>('ai')
  const [loading, setLoading] = useState(false)

  const [activeProvider, setActiveProvider] = useState<ProviderType>('openai')
  const [config, setConfig] = useState<Record<ProviderType, { baseUrl: string; apiKey: string; model: string }>>({
    openai: { baseUrl: '', apiKey: '', model: '' },
    anthropic: { baseUrl: '', apiKey: '', model: '' },
  })
  const [showApiKey, setShowApiKey] = useState(false)
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const configRef = useRef(config)

  useEffect(() => {
    if (open && tab === 'ai') {
      loadConfig()
    }
  }, [open, tab])

  const loadConfig = async () => {
    setLoading(true)
    try {
      const data = await getProviderConfig()
      if (data.active) setActiveProvider(data.active)
      if (data.providers) {
        setConfig((prev) => {
          const next = {
            openai: { ...prev.openai, ...data.providers?.openai },
            anthropic: { ...prev.anthropic, ...data.providers?.anthropic },
          }
          configRef.current = next
          return next
        })
      }
    } catch (error) {
      console.error('Failed to load config:', error)
    } finally {
      setLoading(false)
    }
  }

  const saveConfig = async () => {
    const current = configRef.current[activeProvider]
    const payload: Record<string, string> = {}
    if (current.baseUrl) payload.baseUrl = current.baseUrl
    if (current.apiKey) payload.apiKey = current.apiKey
    if (current.model) payload.model = current.model

    if (Object.keys(payload).length === 0) return

    try {
      await updateProviderConfig(activeProvider, payload)
    } catch (error) {
      console.error('Failed to save config:', error)
    }
  }

  const updateCurrentProviderConfig = (field: 'baseUrl' | 'apiKey' | 'model', value: string) => {
    setConfig((prev) => {
      const next = {
        ...prev,
        [activeProvider]: {
          ...prev[activeProvider],
          [field]: value,
        },
      }
      configRef.current = next
      return next
    })

    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
    }
    saveTimeoutRef.current = setTimeout(saveConfig, 400)
  }

  const handleClose = () => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current)
    }
    onClose()
  }

  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current)
      }
    }
  }, [])

  if (!open) return null

  const currentProvider = config[activeProvider] ?? { baseUrl: '', apiKey: '', model: '' }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={handleClose} />

      <div className="relative w-[560px] bg-card rounded-2xl shadow-2xl shadow-black/20 flex flex-col">
        <div className="flex items-center justify-between px-6 pt-6 pb-4">
          <div className="flex items-center gap-2">
            <Settings className="w-5 h-5 text-muted-foreground" />
            <h2 className="text-xl font-semibold text-foreground">设置</h2>
          </div>
          <button
            onClick={handleClose}
            className="cursor-pointer text-muted-foreground hover:text-foreground transition-colors p-1"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="mx-6 mb-6 flex gap-1 rounded-lg bg-muted p-1">
          <button
            type="button"
            className={`flex-1 cursor-pointer rounded-md px-3 py-1.5 text-sm font-medium transition-colors flex items-center justify-center gap-1.5 ${
              tab === 'ai'
                ? 'bg-secondary text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => setTab('ai')}
          >
            <Cpu className="w-4 h-4" />
            AI 配置
          </button>
          <button
            type="button"
            className={`flex-1 cursor-pointer rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              tab === 'appearance'
                ? 'bg-secondary text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => setTab('appearance')}
          >
            外观
          </button>
          <button
            type="button"
            className={`flex-1 cursor-pointer rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              tab === 'editor'
                ? 'bg-secondary text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            }`}
            onClick={() => setTab('editor')}
          >
            编辑器
          </button>
        </div>

        <div className="px-6 pb-6 flex-1 overflow-y-auto">
          {tab === 'ai' ? (
            loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 text-muted-foreground animate-spin" />
              </div>
            ) : (
              <div className="space-y-5">
                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-2">
                    模型协议
                  </label>
                  <div className="relative">
                    <select
                      value={activeProvider}
                      onChange={(e) => {
                        const nextProvider = e.target.value as ProviderType
                        const prevProvider = activeProvider
                        setActiveProvider(nextProvider)
                        if (saveTimeoutRef.current) {
                          clearTimeout(saveTimeoutRef.current)
                        }
                        saveTimeoutRef.current = setTimeout(async () => {
                          try {
                            await switchProviderConfig(nextProvider)
                          } catch (error) {
                            console.error('Failed to switch provider:', error)
                            setActiveProvider(prevProvider)
                          }
                        }, 400)
                      }}
                      className="w-full px-4 py-2.5 bg-background border border-input rounded-lg text-foreground appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-pink-500/50 focus:border-pink-500/50 text-sm"
                    >
                      {PROVIDER_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                    <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground pointer-events-none" />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-2">
                    API Key
                  </label>
                  <div className="relative">
                    <input
                      type={showApiKey ? 'text' : 'password'}
                      value={currentProvider.apiKey}
                      onChange={(e) => updateCurrentProviderConfig('apiKey', e.target.value)}
                      placeholder="输入 API Key..."
                      className="w-full px-4 py-2.5 pr-10 bg-background border border-input rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-pink-500/50 focus:border-pink-500/50 text-sm"
                    />
                    <button
                      type="button"
                      onClick={() => setShowApiKey(!showApiKey)}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                    >
                      {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    </button>
                  </div>

                </div>

                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-2">
                    API 地址
                  </label>
                  <input
                    type="text"
                    value={currentProvider.baseUrl}
                    onChange={(e) => updateCurrentProviderConfig('baseUrl', e.target.value)}
                    placeholder="https://api.openai.com/v1"
                    className="w-full px-4 py-2.5 bg-background border border-input rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-pink-500/50 focus:border-pink-500/50 text-sm"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-muted-foreground mb-2">
                    默认模型
                  </label>
                  <input
                    type="text"
                    value={currentProvider.model}
                    onChange={(e) => updateCurrentProviderConfig('model', e.target.value)}
                    placeholder="gpt-4"
                    className="w-full px-4 py-2.5 bg-background border border-input rounded-lg text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-pink-500/50 focus:border-pink-500/50 text-sm"
                  />
                </div>
              </div>
            )
          ) : tab === 'appearance' ? (
            <AppearanceSettings />
          ) : (
            <div className="flex items-center justify-center py-12 text-muted-foreground text-sm">
              编辑器配置开发中...
            </div>
          )}
        </div>

        <div className="flex justify-end px-6 py-4 border-t border-border">
          <button
            onClick={handleClose}
            className="cursor-pointer px-5 py-2 rounded-lg border border-border text-muted-foreground hover:text-foreground hover:border-input transition-colors text-sm font-medium"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  )
}

const THEME_OPTIONS: { value: ThemeMode; label: string; icon: React.ElementType }[] = [
  { value: 'light', label: '亮色', icon: Sun },
  { value: 'dark', label: '暗色', icon: Moon },
  { value: 'system', label: '跟随系统', icon: Monitor },
]

function AppearanceSettings() {
  const themeMode = useSettingsStore((s) => s.themeMode)
  const setThemeMode = useSettingsStore((s) => s.setThemeMode)

  return (
    <div className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-muted-foreground mb-3">主题模式</label>
        <div className="grid grid-cols-3 gap-3">
          {THEME_OPTIONS.map((option) => {
            const Icon = option.icon
            const active = themeMode === option.value
            return (
              <button
                key={option.value}
                type="button"
                onClick={() => setThemeMode(option.value)}
                className={`cursor-pointer rounded-xl border px-4 py-4 text-sm font-medium transition-all flex flex-col items-center justify-center gap-2 ${
                  active
                    ? 'border-foreground bg-secondary text-foreground shadow-sm'
                    : 'border-border bg-background text-muted-foreground hover:border-muted-foreground hover:text-foreground'
                }`}
              >
                <Icon className="w-5 h-5" />
                {option.label}
              </button>
            )
          })}
        </div>
      </div>
    </div>
  )
}
