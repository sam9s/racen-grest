'use client';

import { useState, useRef, useEffect } from 'react';
import { ChatMessage } from '@/components/ChatMessage';
import { ChatInput } from '@/components/ChatInput';
import { Header } from '@/components/Header';
import { TypingIndicator } from '@/components/TypingIndicator';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
  timestamp: Date;
  feedbackGiven?: 'up' | 'down' | null;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>('');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setSessionId(`guest_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const sendMessage = async (content: string, captchaAnswer?: string) => {
    if (!content.trim() || isLoading) return;

    const userMessage: Message = {
      id: `msg_${Date.now()}`,
      role: 'user',
      content: content.trim(),
      timestamp: new Date(),
    };

    if (!captchaAnswer) {
      setMessages((prev) => [...prev, userMessage]);
    }
    setIsLoading(true);

    const assistantMessageId = `msg_${Date.now()}_assistant`;

    try {
      const requestBody: Record<string, unknown> = {
        message: content.trim(),
        session_id: sessionId,
        conversation_history: messages.map((m) => ({
          role: m.role,
          content: m.content,
        })),
        user: null,
      };
      
      if (captchaAnswer) {
        requestBody.captcha_answer = captchaAnswer;
      }

      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      if (response.status === 429) {
        const errorData = await response.json();
        if (errorData.captcha_required && errorData.captcha) {
          const userAnswer = prompt(errorData.captcha.question);
          if (userAnswer) {
            setIsLoading(false);
            await sendMessage(content, userAnswer);
            return;
          }
        }
        throw new Error(errorData.error || 'Too many requests. Please wait.');
      }

      if (response.status === 400) {
        const errorData = await response.json();
        if (errorData.captcha_failed) {
          const userAnswer = prompt('Incorrect answer. Please try again: What is the sum?');
          if (userAnswer) {
            setIsLoading(false);
            await sendMessage(content, userAnswer);
            return;
          }
        }
        throw new Error(errorData.error || 'Request failed');
      }

      if (!response.ok) {
        throw new Error('Stream request failed');
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No reader available');
      }

      const decoder = new TextDecoder();
      let streamedContent = '';
      let sources: string[] = [];
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
                    feedbackGiven: null,
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
                    content: data.content || 'I apologize, but I encountered an issue. Please try again.',
                    timestamp: new Date(),
                    feedbackGiven: null,
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
          feedbackGiven: null,
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

  const handleFeedback = async (messageId: string, feedback: 'up' | 'down', comment?: string) => {
    try {
      await fetch('/api/feedback', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          session_id: sessionId,
          message_id: messageId,
          feedback,
          comment,
        }),
      });

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === messageId ? { ...msg, feedbackGiven: feedback } : msg
        )
      );
    } catch (error) {
      console.error('Error submitting feedback:', error);
    }
  };

  const resetConversation = async () => {
    try {
      await fetch('/api/chat/reset', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ session_id: sessionId }),
      });
      setMessages([]);
      setSessionId(`guest_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
    } catch (error) {
      console.error('Error resetting conversation:', error);
    }
  };

  return (
    <main className="flex min-h-screen flex-col bg-theme transition-colors duration-300">
      <Header onReset={resetConversation} />
      
      <div className="flex-1 flex flex-col max-w-3xl mx-auto w-full px-2 md:px-4">
        <div className="flex-1 overflow-y-auto py-3 md:py-6 space-y-3 md:space-y-4">
          {messages.length === 0 && (
            <div className="flex-1 flex items-center justify-center min-h-[50vh] md:min-h-[60vh]">
              <div className="text-center max-w-md px-4">
                <p className="text-xl font-light text-theme-muted">
                  Hi, I'm GRESTA
                </p>
                <p className="text-sm mt-2 text-theme-muted opacity-80">
                  Your trusted tech advisor at GREST
                </p>
                <div className="mt-6 text-left text-sm text-theme-muted opacity-70 space-y-1">
                  <p className="font-medium opacity-90 mb-2">I can help you with:</p>
                  <p>• Refurbished iPhones (iPhone 11 to 16 Pro Max)</p>
                  <p>• Refurbished MacBooks</p>
                  <p>• Pricing, warranty & quality checks</p>
                  <p>• Finding the right device for you</p>
                </div>
                <p className="text-sm mt-6 text-theme-muted opacity-60">
                  Aap kya dhundh rahe hain? / What are you looking for?
                </p>
              </div>
            </div>
          )}
          
          {messages.map((message) => (
            <ChatMessage
              key={message.id}
              message={message}
              onFeedback={handleFeedback}
            />
          ))}
          
          {isLoading && <TypingIndicator />}
          
          <div ref={messagesEndRef} />
        </div>
        
        <div className="sticky bottom-0 pb-3 md:pb-6 pt-2 md:pt-4 bg-gradient-to-t from-theme via-theme to-transparent">
          <ChatInput onSend={sendMessage} disabled={isLoading} />
        </div>
      </div>
    </main>
  );
}
