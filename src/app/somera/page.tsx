'use client';

import { useState, useRef, useEffect } from 'react';
import { Send, RotateCcw, Heart } from 'lucide-react';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: { source: string; topic: string }[];
  timestamp: Date;
}

export default function SomeraPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => `somera_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: input.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    const assistantMessageId = `msg_${Date.now()}_assistant`;

    try {
      const response = await fetch('/api/somera/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: userMessage.content,
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        throw new Error('Stream request failed');
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No reader available');
      }

      const decoder = new TextDecoder();
      let streamedContent = '';
      let sources: { source: string; topic: string }[] = [];
      let messageAdded = false;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              if (data.type === 'content') {
                streamedContent += data.content;
                
                if (!messageAdded) {
                  setMessages((prev) => [...prev, {
                    id: assistantMessageId,
                    role: 'assistant',
                    content: streamedContent,
                    sources: [],
                    timestamp: new Date(),
                  }]);
                  messageAdded = true;
                  setIsLoading(false);
                } else {
                  setMessages((prev) => 
                    prev.map((msg) => 
                      msg.id === assistantMessageId 
                        ? { ...msg, content: streamedContent }
                        : msg
                    )
                  );
                }
              } else if (data.type === 'done') {
                sources = data.sources || [];
                const finalContent = data.full_response || streamedContent;
                setMessages((prev) => 
                  prev.map((msg) => 
                    msg.id === assistantMessageId 
                      ? { ...msg, content: finalContent, sources }
                      : msg
                  )
                );
              } else if (data.type === 'error') {
                if (!messageAdded) {
                  setMessages((prev) => [...prev, {
                    id: assistantMessageId,
                    role: 'assistant',
                    content: data.error || 'I apologize, but I encountered an issue. Please try again.',
                    timestamp: new Date(),
                  }]);
                }
              }
            } catch {
            }
          }
        }
      }

      if (!messageAdded) {
        setMessages((prev) => [...prev, {
          id: assistantMessageId,
          role: 'assistant',
          content: streamedContent || 'I apologize, but I encountered an issue. Please try again.',
          sources,
          timestamp: new Date(),
        }]);
      }
    } catch (error) {
      console.error('Error sending message:', error);
      const errorMessage: Message = {
        id: `msg_${Date.now()}_error`,
        role: 'assistant',
        content: 'I apologize, but I encountered a connection issue. Please try again.',
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const resetConversation = () => {
    setMessages([]);
  };

  return (
    <main className="flex min-h-screen flex-col bg-gradient-to-b from-purple-50 to-white">
      <header className="sticky top-0 z-10 backdrop-blur-md bg-white/80 border-b border-purple-100">
        <div className="max-w-3xl mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
              <Heart className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-purple-900">SOMERA</h1>
              <p className="text-xs text-purple-600">Empathetic Coaching Assistant</p>
            </div>
          </div>
          <button
            onClick={resetConversation}
            className="p-2 rounded-full hover:bg-purple-100 transition-colors"
            title="Start new conversation"
          >
            <RotateCcw className="w-5 h-5 text-purple-600" />
          </button>
        </div>
      </header>
      
      <div className="flex-1 flex flex-col max-w-3xl mx-auto w-full px-4">
        <div className="flex-1 overflow-y-auto py-6 space-y-4">
          {messages.length === 0 && (
            <div className="flex-1 flex items-center justify-center min-h-[60vh]">
              <div className="text-center max-w-md px-4">
                <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center">
                  <Heart className="w-8 h-8 text-white" />
                </div>
                <h2 className="text-2xl font-light text-purple-900 mb-2">
                  Hi, I'm SOMERA
                </h2>
                <p className="text-purple-600 mb-6">
                  Your empathetic coaching companion, inspired by Shweta's wisdom
                </p>
                <div className="text-left text-sm text-purple-700 space-y-2 bg-purple-50 rounded-lg p-4">
                  <p className="font-medium text-purple-800 mb-2">I'm here to support you with:</p>
                  <p>• Understanding procrastination patterns</p>
                  <p>• Finding inner peace and balance</p>
                  <p>• Navigating life's challenges</p>
                  <p>• Gentle, empathetic guidance</p>
                </div>
                <p className="text-sm mt-6 text-purple-500">
                  What's on your mind today?
                </p>
              </div>
            </div>
          )}
          
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div
                className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                  message.role === 'user'
                    ? 'bg-purple-600 text-white rounded-br-sm'
                    : 'bg-white border border-purple-100 text-gray-800 rounded-bl-sm shadow-sm'
                }`}
              >
                <p className="whitespace-pre-wrap">{message.content}</p>
                {message.sources && message.sources.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-purple-200">
                    <p className="text-xs text-purple-400">
                      Inspired by: {message.sources.map(s => s.source).join(', ')}
                    </p>
                  </div>
                )}
              </div>
            </div>
          ))}
          
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-white border border-purple-100 rounded-2xl rounded-bl-sm px-4 py-3 shadow-sm">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-purple-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
          
          <div ref={messagesEndRef} />
        </div>
        
        <div className="sticky bottom-0 pb-6 pt-4 bg-gradient-to-t from-white via-white to-transparent">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
              placeholder="Share what's on your mind..."
              disabled={isLoading}
              className="flex-1 px-4 py-3 rounded-full border border-purple-200 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent bg-white disabled:opacity-50"
            />
            <button
              onClick={sendMessage}
              disabled={isLoading || !input.trim()}
              className="p-3 rounded-full bg-purple-600 text-white hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </main>
  );
}
