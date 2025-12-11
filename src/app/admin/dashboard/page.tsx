'use client';

import { useState, useEffect } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

interface DashboardStats {
  totalConversations: number;
  totalSessions: number;
  avgResponseTime: number;
  positiveRating: number;
  conversationsByDay: { date: string; count: number }[];
  topQueries: { query: string; count: number }[];
  channelDistribution: { channel: string; count: number }[];
}

interface ChatSession {
  sessionId: string;
  userName: string;
  userEmail: string | null;
  channel: string;
  messageCount: number;
  firstMessage: string;
  createdAt: string;
  lastActivity: string;
}

interface ChatMessage {
  id: number;
  userQuestion: string;
  botAnswer: string;
  timestamp: string;
  safetyFlagged: boolean;
  responseTimeMs: number | null;
}

interface ConversationDetail {
  session: {
    sessionId: string;
    userName: string;
    userEmail: string | null;
    channel: string;
    createdAt: string;
    lastActivity: string;
  };
  messages: ChatMessage[];
}

const COLORS = ['#03a9f4', '#4fc3f7', '#81d4fa', '#b3e5fc'];

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState<'analytics' | 'conversations'>('analytics');
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('7d');
  
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [conversationDetail, setConversationDetail] = useState<ConversationDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  useEffect(() => {
    if (activeTab === 'analytics') {
      fetchStats();
    } else {
      fetchSessions();
    }
  }, [timeRange, activeTab]);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/admin/stats?range=${timeRange}`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      }
    } catch (error) {
      console.error('Failed to fetch stats:', error);
    }
    setLoading(false);
  };

  const fetchSessions = async () => {
    setSessionsLoading(true);
    try {
      const res = await fetch(`/api/admin/conversations?range=${timeRange}`);
      if (res.ok) {
        const data = await res.json();
        setSessions(data.sessions || []);
      }
    } catch (error) {
      console.error('Failed to fetch sessions:', error);
    }
    setSessionsLoading(false);
  };

  const fetchConversationDetail = async (sessionId: string) => {
    setDetailLoading(true);
    setSelectedSession(sessionId);
    try {
      const res = await fetch(`/api/admin/conversations/${encodeURIComponent(sessionId)}`);
      if (res.ok) {
        const data = await res.json();
        setConversationDetail(data);
      }
    } catch (error) {
      console.error('Failed to fetch conversation:', error);
    }
    setDetailLoading(false);
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getChannelBadgeColor = (channel: string) => {
    switch (channel.toLowerCase()) {
      case 'widget':
        return 'bg-purple-500/20 text-purple-400';
      case 'whatsapp':
        return 'bg-green-500/20 text-green-400';
      case 'instagram':
        return 'bg-pink-500/20 text-pink-400';
      default:
        return 'bg-cyan-500/20 text-cyan-400';
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 p-6">
      <div className="max-w-7xl mx-auto">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-white">Jovee Analytics</h1>
            <p className="text-gray-400 mt-1">Real-time chatbot performance dashboard</p>
          </div>
          <div className="flex gap-2">
            {['24h', '7d', '30d'].map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  timeRange === range
                    ? 'bg-cyan-500 text-white shadow-lg shadow-cyan-500/30'
                    : 'bg-gray-800 text-gray-400 hover:bg-gray-700 hover:text-white'
                }`}
              >
                {range === '24h' ? 'Last 24h' : range === '7d' ? 'Last 7 days' : 'Last 30 days'}
              </button>
            ))}
          </div>
        </div>

        <div className="flex gap-4 mb-8">
          <button
            onClick={() => setActiveTab('analytics')}
            className={`px-6 py-3 rounded-xl font-medium transition-all flex items-center gap-2 ${
              activeTab === 'analytics'
                ? 'bg-cyan-500 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
            </svg>
            Analytics
          </button>
          <button
            onClick={() => setActiveTab('conversations')}
            className={`px-6 py-3 rounded-xl font-medium transition-all flex items-center gap-2 ${
              activeTab === 'conversations'
                ? 'bg-cyan-500 text-white'
                : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
            }`}
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            Conversations
          </button>
        </div>

        {activeTab === 'analytics' ? (
          <AnalyticsView stats={stats} loading={loading} />
        ) : (
          <ConversationsView
            sessions={sessions}
            sessionsLoading={sessionsLoading}
            selectedSession={selectedSession}
            conversationDetail={conversationDetail}
            detailLoading={detailLoading}
            onSelectSession={fetchConversationDetail}
            formatDate={formatDate}
            getChannelBadgeColor={getChannelBadgeColor}
          />
        )}
      </div>
    </div>
  );
}

function AnalyticsView({ stats, loading }: { stats: DashboardStats | null; loading: boolean }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-cyan-400"></div>
      </div>
    );
  }

  const hasData = stats && (stats.totalConversations > 0 || stats.totalSessions > 0);

  return (
    <>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Total Conversations"
          value={stats?.totalConversations?.toLocaleString() || '0'}
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
          }
        />
        <StatCard
          title="Unique Sessions"
          value={stats?.totalSessions?.toLocaleString() || '0'}
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          }
        />
        <StatCard
          title="Avg Response Time"
          value={`${stats?.avgResponseTime?.toFixed(1) || '0'}s`}
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
        <StatCard
          title="Satisfaction Rate"
          value={stats?.positiveRating ? `${stats.positiveRating}%` : 'N/A'}
          icon={
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          }
        />
      </div>

      {!hasData ? (
        <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl p-12 border border-gray-700/50 text-center">
          <svg className="w-16 h-16 mx-auto text-gray-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <h3 className="text-xl font-semibold text-white mb-2">No Data Yet</h3>
          <p className="text-gray-400">Start chatting with Jovee to see analytics here.</p>
        </div>
      ) : (
        <>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
            <div className="lg:col-span-2 bg-gray-800/50 backdrop-blur-sm rounded-2xl p-6 border border-gray-700/50">
              <h2 className="text-xl font-semibold text-white mb-4">Conversation Trends</h2>
              <div className="h-80">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={stats?.conversationsByDay || []}>
                    <defs>
                      <linearGradient id="colorCount" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#03a9f4" stopOpacity={0.4} />
                        <stop offset="95%" stopColor="#03a9f4" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis dataKey="date" stroke="#9ca3af" fontSize={12} />
                    <YAxis stroke="#9ca3af" fontSize={12} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1f2937',
                        border: '1px solid #374151',
                        borderRadius: '8px',
                        color: '#fff',
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="count"
                      stroke="#03a9f4"
                      strokeWidth={2}
                      fillOpacity={1}
                      fill="url(#colorCount)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl p-6 border border-gray-700/50">
              <h2 className="text-xl font-semibold text-white mb-4">Channel Distribution</h2>
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={stats?.channelDistribution || []}
                      cx="50%"
                      cy="50%"
                      innerRadius={60}
                      outerRadius={90}
                      paddingAngle={5}
                      dataKey="count"
                    >
                      {stats?.channelDistribution?.map((_, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1f2937',
                        border: '1px solid #374151',
                        borderRadius: '8px',
                        color: '#fff',
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="flex justify-center gap-4 mt-4 flex-wrap">
                {stats?.channelDistribution?.map((item, index) => (
                  <div key={item.channel} className="flex items-center gap-2">
                    <div
                      className="w-3 h-3 rounded-full"
                      style={{ backgroundColor: COLORS[index % COLORS.length] }}
                    />
                    <span className="text-sm text-gray-400">{item.channel} ({item.count})</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}

function ConversationsView({
  sessions,
  sessionsLoading,
  selectedSession,
  conversationDetail,
  detailLoading,
  onSelectSession,
  formatDate,
  getChannelBadgeColor,
}: {
  sessions: ChatSession[];
  sessionsLoading: boolean;
  selectedSession: string | null;
  conversationDetail: ConversationDetail | null;
  detailLoading: boolean;
  onSelectSession: (sessionId: string) => void;
  formatDate: (date: string) => string;
  getChannelBadgeColor: (channel: string) => string;
}) {
  if (sessionsLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-cyan-400"></div>
      </div>
    );
  }

  if (sessions.length === 0) {
    return (
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl p-12 border border-gray-700/50 text-center">
        <svg className="w-16 h-16 mx-auto text-gray-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
        </svg>
        <h3 className="text-xl font-semibold text-white mb-2">No Conversations Yet</h3>
        <p className="text-gray-400">Conversations will appear here once users start chatting with Jovee.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl border border-gray-700/50 overflow-hidden">
        <div className="p-4 border-b border-gray-700/50">
          <h2 className="text-lg font-semibold text-white">Chat Sessions ({sessions.length})</h2>
        </div>
        <div className="max-h-[600px] overflow-y-auto">
          {sessions.map((session) => (
            <button
              key={session.sessionId}
              onClick={() => onSelectSession(session.sessionId)}
              className={`w-full p-4 text-left border-b border-gray-700/30 hover:bg-gray-700/30 transition-colors ${
                selectedSession === session.sessionId ? 'bg-cyan-500/10 border-l-2 border-l-cyan-500' : ''
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center text-white text-sm font-medium">
                    {session.userName.charAt(0).toUpperCase()}
                  </div>
                  <div>
                    <p className="text-white font-medium text-sm">{session.userName}</p>
                    {session.userEmail && (
                      <p className="text-gray-500 text-xs">{session.userEmail}</p>
                    )}
                  </div>
                </div>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${getChannelBadgeColor(session.channel)}`}>
                  {session.channel}
                </span>
              </div>
              <p className="text-gray-400 text-sm line-clamp-2 mb-2">{session.firstMessage || 'No messages'}</p>
              <div className="flex items-center justify-between text-xs text-gray-500">
                <span>{session.messageCount} messages</span>
                <span>{formatDate(session.lastActivity)}</span>
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl border border-gray-700/50 overflow-hidden">
        {!selectedSession ? (
          <div className="h-full flex items-center justify-center p-12 text-center">
            <div>
              <svg className="w-16 h-16 mx-auto text-gray-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
              </svg>
              <p className="text-gray-400">Select a conversation to view details</p>
            </div>
          </div>
        ) : detailLoading ? (
          <div className="h-full flex items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-cyan-400"></div>
          </div>
        ) : conversationDetail ? (
          <>
            <div className="p-4 border-b border-gray-700/50">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-white">{conversationDetail.session.userName}</h2>
                  <p className="text-sm text-gray-400">
                    {conversationDetail.session.userEmail || 'Anonymous user'} • {conversationDetail.session.channel}
                  </p>
                </div>
                <div className="text-right text-sm text-gray-500">
                  <p>Started: {formatDate(conversationDetail.session.createdAt)}</p>
                  <p>Last active: {formatDate(conversationDetail.session.lastActivity)}</p>
                </div>
              </div>
            </div>
            <div className="p-4 max-h-[520px] overflow-y-auto space-y-4">
              {conversationDetail.messages.map((msg) => (
                <div key={msg.id} className="space-y-3">
                  <div className="flex justify-end">
                    <div className="max-w-[80%] bg-cyan-500/20 rounded-2xl rounded-tr-sm px-4 py-3">
                      <p className="text-white text-sm">{msg.userQuestion}</p>
                      <p className="text-xs text-gray-500 mt-1 text-right">{formatDate(msg.timestamp)}</p>
                    </div>
                  </div>
                  <div className="flex justify-start">
                    <div className="max-w-[80%] bg-gray-700/50 rounded-2xl rounded-tl-sm px-4 py-3">
                      <p className="text-gray-200 text-sm whitespace-pre-wrap">{msg.botAnswer}</p>
                      <div className="flex items-center gap-2 mt-1">
                        {msg.safetyFlagged && (
                          <span className="text-xs bg-red-500/20 text-red-400 px-2 py-0.5 rounded">Safety flagged</span>
                        )}
                        {msg.responseTimeMs && (
                          <span className="text-xs text-gray-500">{(msg.responseTimeMs / 1000).toFixed(1)}s</span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon,
}: {
  title: string;
  value: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl p-6 border border-gray-700/50 hover:border-cyan-500/30 transition-all hover:shadow-lg hover:shadow-cyan-500/5">
      <div className="flex items-center justify-between mb-4">
        <div className="p-3 bg-cyan-500/10 rounded-xl text-cyan-400">{icon}</div>
      </div>
      <h3 className="text-gray-400 text-sm font-medium">{title}</h3>
      <p className="text-3xl font-bold text-white mt-1">{value}</p>
    </div>
  );
}
