'use client';

import { useTheme } from './ThemeProvider';

interface HeaderProps {
  onReset: () => void;
}

export function Header({ onReset }: HeaderProps) {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="sticky top-0 z-50 backdrop-blur-md bg-theme-surface/90 header-bg border-b border-primary-500/10 transition-colors duration-300">
      <div className="max-w-6xl mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          {/* Left spacer for balance */}
          <div className="w-32 hidden md:block" />
          
          {/* Centered branding */}
          <div className="flex flex-col items-center flex-1">
            <div className="flex items-center gap-4">
              <h1 className="text-3xl md:text-4xl lg:text-5xl font-extralight tracking-[0.6em] md:tracking-[0.8em] text-white uppercase">
                R<span className="text-primary-400">.</span>A<span className="text-primary-400">.</span>C<span className="text-primary-400">.</span>E<span className="text-primary-400">.</span>N
              </h1>
              {/* R Logo */}
              <div className="text-primary-400 text-4xl md:text-5xl font-light italic hidden md:block">
                R
              </div>
            </div>
            <p className="text-[10px] md:text-xs tracking-[0.4em] md:tracking-[0.5em] text-gray-400 mt-2 uppercase font-extralight">
              Real Time Advisor for Coaching, Education & Navigation
            </p>
          </div>
          
          {/* Right side buttons */}
          <div className="flex items-center gap-2">
            <button
              onClick={toggleTheme}
              className="p-2.5 rounded-xl btn-theme"
              aria-label="Toggle theme"
            >
              {theme === 'dark' ? (
                <svg
                  className="w-5 h-5 text-primary-400"
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
                  className="w-5 h-5 text-primary-600"
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
              className="flex items-center gap-2 px-4 py-2.5 text-sm font-medium rounded-xl btn-theme text-theme"
            >
              <svg 
                className="w-4 h-4" 
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
              New Chat
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
