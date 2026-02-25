import React, { createContext, useContext, useState, useCallback } from 'react';

type IntroContextType = {
  showIntro: boolean;
  triggerIntro: () => void;
  hideIntro: () => void;
};

const IntroContext = createContext<IntroContextType | null>(null);

export function IntroProvider({ children }: { children: React.ReactNode }) {
  const [showIntro, setShowIntro] = useState(true);

  const triggerIntro = useCallback(() => {
    setShowIntro(true);
  }, []);

  const hideIntro = useCallback(() => {
    setShowIntro(false);
  }, []);

  return (
    <IntroContext.Provider value={{ showIntro, triggerIntro, hideIntro }}>
      {children}
    </IntroContext.Provider>
  );
}

export function useIntro() {
  const ctx = useContext(IntroContext);
  if (!ctx) throw new Error('useIntro must be used within IntroProvider');
  return ctx;
}
