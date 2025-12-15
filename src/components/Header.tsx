'use client';

import { useTheme } from './ThemeProvider';

interface HeaderProps {
  onReset: () => void;
}

export function Header({ onReset }: HeaderProps) {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="sticky top-0 z-50 backdrop-blur-md bg-theme-surface/90 header-bg border-b border-primary-500/10 transition-colors duration-300">
      <div className="max-w-6xl mx-auto px-2 md:px-4 py-1.5 md:py-2">
        <div className="flex items-center justify-between">
          <div className="w-20 md:w-24 hidden md:block">
          </div>
          
          <div className="flex flex-col items-center flex-1">
            <h1 className="text-2xl md:text-3xl font-medium tracking-wider text-white">
              GRESTA
            </h1>
            <p className="hidden md:block text-[10px] md:text-xs tracking-wide text-gray-400 mt-0.5">
              Your GREST Tech Assistant
            </p>
          </div>
          
          <div className="flex items-center gap-1 md:gap-2">
            <button
              onClick={toggleTheme}
              className="p-2 md:p-2 rounded-lg btn-theme min-w-[44px] min-h-[44px] flex items-center justify-center"
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? (
                <svg
                  className="w-4 h-4 text-primary-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
                  />
                </svg>
              ) : (
                <svg
                  className="w-4 h-4 text-primary-600"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
                  />
                </svg>
              )}
            </button>
            
            <button
              onClick={onReset}
              className="flex items-center gap-1 md:gap-1.5 px-2 md:px-3 py-2 md:py-1.5 text-xs font-medium rounded-lg btn-theme text-theme min-h-[44px]"
            >
              <svg 
                className="w-4 h-4 md:w-3.5 md:h-3.5" 
                fill="none" 
                stroke="currentColor" 
                viewBox="0 0 24 24"
              >
                <path 
                  strokeLinecap="round" 
                  strokeLinejoin="round" 
                  strokeWidth={2} 
                  d="M12 4v16m8-8H4" 
                />
              </svg>
              <span className="hidden md:inline">New Chat</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
