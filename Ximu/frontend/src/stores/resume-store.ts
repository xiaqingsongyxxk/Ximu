import { create } from 'zustand';
import type { Resume, ResumeSection, SectionContent, ThemeConfig } from '@/types/resume';
import { AUTOSAVE_DELAY } from '@/lib/constants';
import { generateId } from '@/lib/utils';
import { useSettingsStore } from '@/stores/settings-store';
import { updateResumeSection, deleteResumeSection, updateResume } from '@/lib/api';

interface ResumeStore {
  currentResume: Resume | null;
  sections: ResumeSection[];
  isDirty: boolean;
  isSaving: boolean;
  _saveTimeout: ReturnType<typeof setTimeout> | null;
  _originalSectionIds: Set<string>;
  _dirtySections: Set<string>;
  _pendingDeletions: Set<string>; // 只保存被修改的 sections

  setResume: (resume: Resume) => void;
  updateSection: (sectionId: string, content: Partial<SectionContent>) => void;
  updateSectionTitle: (sectionId: string, title: string) => void;
  addSection: (section: ResumeSection) => void;
  removeSection: (sectionId: string) => void;
  reorderSections: (sections: ResumeSection[]) => void;
  toggleSectionVisibility: (sectionId: string) => void;
  setTemplate: (template: string) => void;
  setThemeConfig: (themeConfig: Partial<ThemeConfig>) => void;
  setTitle: (title: string) => void;
  save: () => Promise<void>;
  _scheduleSave: () => void;
  reset: () => void;
}

export const useResumeStore = create<ResumeStore>((set, get) => ({
  currentResume: null,
  sections: [],
  isDirty: false,
  isSaving: false,
  _saveTimeout: null,
  _originalSectionIds: new Set(),
  _dirtySections: new Set(),
  _pendingDeletions: new Set(),

  setResume: (resume) => {
    const { _saveTimeout } = get();
    if (_saveTimeout) clearTimeout(_saveTimeout);

    const sections = (resume.sections || []).map((s) => {
      const content = s.content as unknown as Record<string, unknown>;
      if (Array.isArray(content?.items)) {
        content.items = (content.items as any[]).map((item) =>
          typeof item === 'object' && item !== null && !item.id
            ? { ...item, id: generateId() }
            : item
        );
      }
      if (Array.isArray(content?.categories)) {
        content.categories = (content.categories as any[]).map((cat) =>
          typeof cat === 'object' && cat !== null && !cat.id
            ? { ...cat, id: generateId() }
            : cat
        );
      }
      return { ...s, content: content as unknown as typeof s.content };
    });

    set({
      currentResume: { ...resume, sections },
      sections,
      isDirty: false,
      _saveTimeout: null,
      _originalSectionIds: new Set((resume.sections || []).map((s) => s.id)),
      _dirtySections: new Set(),
      _pendingDeletions: new Set(),
    });
  },

  updateSection: (sectionId, content) => {
    set((state) => {
      const sections = state.sections.map((s) =>
        s.id === sectionId ? { ...s, content: { ...s.content, ...content } as SectionContent } : s
      );
      const _dirtySections = new Set(state._dirtySections);
      _dirtySections.add(sectionId);
      return {
        sections,
        currentResume: state.currentResume ? { ...state.currentResume, sections } : null,
        isDirty: true,
        _dirtySections,
      };
    });
    get()._scheduleSave();
  },

  updateSectionTitle: (sectionId, title) => {
    set((state) => {
      const sections = state.sections.map((s) =>
        s.id === sectionId ? { ...s, title } : s
      );
      const _dirtySections = new Set(state._dirtySections);
      _dirtySections.add(sectionId);
      return {
        sections,
        currentResume: state.currentResume ? { ...state.currentResume, sections } : null,
        isDirty: true,
        _dirtySections,
      };
    });
    get()._scheduleSave();
  },

  addSection: (section) => {
    set((state) => {
      const sections = [...state.sections, section];
      const _dirtySections = new Set(state._dirtySections);
      _dirtySections.add(section.id);
      return {
        sections,
        currentResume: state.currentResume ? { ...state.currentResume, sections } : null,
        isDirty: true,
        _dirtySections,
      };
    });
    get()._scheduleSave();
  },

  removeSection: (sectionId) => {
    set((state) => {
      const sections = state.sections.filter((s) => s.id !== sectionId);
      const _pendingDeletions = new Set(state._pendingDeletions);
      _pendingDeletions.add(sectionId);
      return {
        sections,
        currentResume: state.currentResume ? { ...state.currentResume, sections } : null,
        isDirty: true,
        _pendingDeletions,
      };
    });
    get()._scheduleSave();
  },

  reorderSections: (sections) => {
    set((state) => {
      const _dirtySections = new Set(state._dirtySections);
      sections.forEach((s) => _dirtySections.add(s.id));
      return {
        sections,
        currentResume: state.currentResume ? { ...state.currentResume, sections } : null,
        isDirty: true,
        _dirtySections,
      };
    });
    get()._scheduleSave();
  },

  toggleSectionVisibility: (sectionId) => {
    set((state) => {
      const sections = state.sections.map((s) =>
        s.id === sectionId ? { ...s, visible: !s.visible } : s
      );
      const _dirtySections = new Set(state._dirtySections);
      _dirtySections.add(sectionId);
      return {
        sections,
        currentResume: state.currentResume ? { ...state.currentResume, sections } : null,
        isDirty: true,
        _dirtySections,
      };
    });
    get()._scheduleSave();
  },

  setTemplate: (template) => {
    const { currentResume } = get();
    set((state) => ({
      currentResume: state.currentResume
        ? { ...state.currentResume, template }
        : null,
    }));
    if (currentResume?.id) {
      updateResume({ id: currentResume.id, template });
    }
  },

  setThemeConfig: (themeConfig: Partial<ThemeConfig>) => {
    const { currentResume } = get();
    set((state) => ({
      currentResume: state.currentResume
        ? { ...state.currentResume, themeConfig: { ...state.currentResume.themeConfig, ...themeConfig } }
        : null,
    }));
    if (currentResume?.id) {
      updateResume({ id: currentResume.id, themeConfig: { ...currentResume.themeConfig, ...themeConfig } });
    }
  },

  setTitle: (title) => {
    set((state) => ({
      currentResume: state.currentResume
        ? { ...state.currentResume, title }
        : null,
      isDirty: true,
    }));
    get()._scheduleSave();
  },

  save: async () => {
    const { currentResume, sections, isDirty, _dirtySections, _pendingDeletions } = get();
    if (!currentResume || !isDirty) return;

    set({ isSaving: true });
    try {
      const deletePromises = [..._pendingDeletions].map((id) =>
        deleteResumeSection(id).catch((err) => {
          console.error('删除区块失败:', id, err);
        }),
      );

      const savePromises: Promise<void>[] = [];
      const dirtyIds = new Set(_dirtySections);

      for (let i = 0; i < sections.length; i++) {
        const s = sections[i];
        if (!dirtyIds.has(s.id)) continue;

        const payload = {
          id: s.id,
          resumeId: currentResume.id,
          type: s.type,
          title: s.title,
          sortOrder: i,
          visible: s.visible,
          content: s.content,
        };

        savePromises.push(
          updateResumeSection(payload).then(() => { }).catch((err) => {
            console.error('保存区块失败:', s.type, s.id, err);
          }),
        );
      }

      await Promise.all([...deletePromises, ...savePromises]);
      const currentSectionIds = new Set(sections.map((s) => s.id));
      set({
        isDirty: false,
        _dirtySections: new Set(),
        _pendingDeletions: new Set(),
        _originalSectionIds: currentSectionIds,
      });
    } catch (error) {
      console.error('Failed to save resume:', error);
    } finally {
      set({ isSaving: false });
    }
  },

  _scheduleSave: () => {
    const { _saveTimeout } = get();
    if (_saveTimeout) clearTimeout(_saveTimeout);

    const { autoSave, autoSaveInterval, _hydrated } = useSettingsStore.getState();

    if (_hydrated && !autoSave) {
      set({ _saveTimeout: null });
      return;
    }

    const delay = _hydrated ? autoSaveInterval : AUTOSAVE_DELAY;
    const timeout = setTimeout(() => {
      get().save();
    }, delay);

    set({ _saveTimeout: timeout });
  },

  reset: () => {
    const { _saveTimeout } = get();
    if (_saveTimeout) clearTimeout(_saveTimeout);
    set({
      currentResume: null,
      sections: [],
      isDirty: false,
      isSaving: false,
      _saveTimeout: null,
      _dirtySections: new Set(),
      _pendingDeletions: new Set(),
    });
  },
}));
