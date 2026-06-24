import { create } from 'zustand';

interface EditorStore {
  selectedSectionId: string | null;
  selectedItemId: string | null;
  isDragging: boolean;
  showAiChat: boolean;
  showThemeEditor: boolean;
  zoom: number;
  pendingAiMessage: string | null;

  selectSection: (id: string | null) => void;
  selectItem: (id: string | null) => void;
  setDragging: (isDragging: boolean) => void;
  toggleAiChat: () => void;
  setShowAiChat: (show: boolean) => void;
  toggleThemeEditor: () => void;
  setZoom: (zoom: number) => void;
  setPendingAiMessage: (message: string | null) => void;
  reset: () => void;
}

export const useEditorStore = create<EditorStore>((set) => ({
  selectedSectionId: null,
  selectedItemId: null,
  isDragging: false,
  showAiChat: false,
  showThemeEditor: false,
  zoom: 80,
  pendingAiMessage: null,

  selectSection: (id) => set({ selectedSectionId: id, selectedItemId: null }),
  selectItem: (id) => set({ selectedItemId: id }),
  setDragging: (isDragging) => set({ isDragging }),
  toggleAiChat: () => set((s) => ({ showAiChat: !s.showAiChat })),
  setShowAiChat: (show) => set({ showAiChat: show }),
  toggleThemeEditor: () => set((s) => ({ showThemeEditor: !s.showThemeEditor })),
  setZoom: (zoom) => set({ zoom }),
  setPendingAiMessage: (message) => set({ pendingAiMessage: message }),

  reset: () =>
    set({
      selectedSectionId: null,
      selectedItemId: null,
      isDragging: false,
      showAiChat: false,
      showThemeEditor: false,
      zoom: 80,
      pendingAiMessage: null,
    }),
}));
