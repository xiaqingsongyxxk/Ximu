import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { createContext, useContext } from 'react';

const DragHandleCtx = createContext({ attributes: {}, listeners: {} });

export function useDragHandle() {
  return useContext(DragHandleCtx);
}

interface SortableItemProps {
  id: string;
  children: React.ReactNode;
}

export function SortableItem({ id, children }: SortableItemProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  };

  return (
    <DragHandleCtx.Provider value={{ attributes, listeners }}>
      <div ref={setNodeRef} style={style}>
        {children}
      </div>
    </DragHandleCtx.Provider>
  );
}
