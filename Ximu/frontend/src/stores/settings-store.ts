import { create } from 'zustand';
import { applyThemeMode } from '../lib/theme';

export type AIProvider = 'openai' | 'anthropic' | 'gemini';
export type ThemeMode = 'light' | 'dark' | 'system';

interface SettingsStore {
  aiProvider: AIProvider;
  aiApiKey: string;
  aiBaseURL: string;
  aiModel: string;
  autoSave: boolean;
  autoSaveInterval: number;
  themeMode: ThemeMode;
  _hydrated: boolean;

  setAIProvider: (provider: AIProvider) => void;
  setAIApiKey: (key: string) => void;
  setAIBaseURL: (url: string) => void;
  setAIModel: (model: string) => void;
  setAutoSave: (enabled: boolean) => void;
  setAutoSaveInterval: (interval: number) => void;
  setThemeMode: (mode: ThemeMode) => void;
  hydrate: () => void;
}

const API_KEY_STORAGE_KEY = 'jade_api_key';
const PROVIDER_CONFIGS_KEY = 'jade_provider_configs';
const THEME_MODE_KEY = 'jade_theme_mode';

function loadThemeMode(): ThemeMode {
  if (typeof window === 'undefined') return 'system';
  try {
    const raw = localStorage.getItem(THEME_MODE_KEY);
    if (raw === 'light' || raw === 'dark' || raw === 'system') return raw;
    return 'system';
  } catch { return 'system'; }
}

function saveThemeMode(mode: ThemeMode) {
  if (typeof window === 'undefined') return;
  try { localStorage.setItem(THEME_MODE_KEY, mode); } catch {}
}

interface ProviderConfig {
  baseURL: string;
  model: string;
  apiKey: string;
}

const PROVIDER_DEFAULTS: Record<AIProvider, ProviderConfig> = {
  openai: { baseURL: 'https://api.openai.com/v1', model: 'gpt-4o', apiKey: '' },
  anthropic: { baseURL: 'https://api.anthropic.com', model: 'claude-sonnet-4-20250514', apiKey: '' },
  gemini: { baseURL: 'https://generativelanguage.googleapis.com/v1beta', model: 'gemini-2.0-flash', apiKey: '' },
};

function loadProviderConfigs(): Partial<Record<AIProvider, ProviderConfig>> {
  if (typeof window === 'undefined') return {};
  try {
    const raw = localStorage.getItem(PROVIDER_CONFIGS_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch { return {}; }
}

function saveProviderConfigs(configs: Partial<Record<AIProvider, ProviderConfig>>) {
  if (typeof window === 'undefined') return;
  try { localStorage.setItem(PROVIDER_CONFIGS_KEY, JSON.stringify(configs)); } catch { /* ignore */ }
}

function saveApiKeyLocally(key: string) {
  if (typeof window === 'undefined') return;
  try {
    if (key) localStorage.setItem(API_KEY_STORAGE_KEY, key);
    else localStorage.removeItem(API_KEY_STORAGE_KEY);
  } catch { /* ignore */ }
}

function loadApiKeyLocally(): string {
  if (typeof window === 'undefined') return '';
  try { return localStorage.getItem(API_KEY_STORAGE_KEY) || ''; }
  catch { return ''; }
}

export function getAIHeaders(): Record<string, string> {
  const { aiProvider, aiApiKey, aiBaseURL, aiModel } = useSettingsStore.getState();
  const headers: Record<string, string> = {};
  if (aiProvider) headers['x-provider'] = aiProvider;
  if (aiApiKey) headers['x-api-key'] = aiApiKey;
  if (aiBaseURL) headers['x-base-url'] = aiBaseURL;
  if (aiModel) headers['x-model'] = aiModel;
  return headers;
}

export const useSettingsStore = create<SettingsStore>((set, get) => ({
  aiProvider: 'openai',
  aiApiKey: '',
  aiBaseURL: 'https://api.openai.com/v1',
  aiModel: 'gpt-4o',
  autoSave: true,
  autoSaveInterval: 500,
  themeMode: loadThemeMode(),
  _hydrated: false,

  setAIProvider: (provider) => {
    const { aiProvider: prev } = get();
    const configs = loadProviderConfigs();
    configs[prev] = { baseURL: get().aiBaseURL, model: get().aiModel, apiKey: get().aiApiKey };
    saveProviderConfigs(configs);
    const cached = configs[provider];
    const defaults = PROVIDER_DEFAULTS[provider];
    const restored = cached || defaults;
    set({ aiProvider: provider, aiBaseURL: restored.baseURL, aiModel: restored.model, aiApiKey: restored.apiKey });
    saveApiKeyLocally(restored.apiKey);
  },

  setAIApiKey: (key) => {
    set({ aiApiKey: key });
    saveApiKeyLocally(key);
  },

  setAIBaseURL: (url) => set({ aiBaseURL: url }),

  setAIModel: (model) => set({ aiModel: model }),

  setAutoSave: (enabled) => set({ autoSave: enabled }),

  setAutoSaveInterval: (interval) => set({ autoSaveInterval: interval }),

  setThemeMode: (mode) => {
    set({ themeMode: mode });
    saveThemeMode(mode);
    applyThemeMode();
  },

  hydrate: () => {
    if (get()._hydrated) return;
    const apiKey = loadApiKeyLocally();
    const configs = loadProviderConfigs();
    const cached = configs[get().aiProvider];
    set({
      aiApiKey: apiKey,
      ...(cached && { aiBaseURL: cached.baseURL, aiModel: cached.model, aiApiKey: cached.apiKey }),
      _hydrated: true,
    });
  },
}));

if (typeof window !== 'undefined') {
  useSettingsStore.getState().hydrate();
}
