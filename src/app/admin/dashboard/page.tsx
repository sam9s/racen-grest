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

const COLORS = ['#03a9f4', '#4fc3f7', '#81d4fa', '#b3e5fc'];

export default function AdminDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [timeRange, setTimeRange] = useState('7d');

  useEffect(() => {
    fetchStats();
  }, [timeRange]);

  const fetchStats = async () => {
    setLoading(true);
    try {
      const res = await fetch(`/api/admin/stats?range=${timeRange}`);
      if (res.ok) {
        const data = await res.json();
        setStats(data);
      } else {
        setStats(getMockData());
      }
    } catch {
      setStats(getMockData());
    }
    setLoading(false);
  };

  const getMockData = (): DashboardStats => ({
    totalConversations: 1247,
    totalSessions: 438,
    avgResponseTime: 1.8,
    positiveRating: 94,
    conversationsByDay: [
      { date: 'Dec 5', count: 145 },
      { date: 'Dec 6', count: 198 },
      { date: 'Dec 7', count: 167 },
      { date: 'Dec 8', count: 234 },
      { date: 'Dec 9', count: 189 },
      { date: 'Dec 10', count: 256 },
      { date: 'Dec 11', count: 178 },
    ],
    topQueries: [
      { query: 'Balance Mastery program', count: 89 },
      { query: 'Pricing information', count: 67 },
      { query: 'Discovery call booking', count: 54 },
      { query: 'Elevate 360 details', count: 43 },
      { query: 'Contact information', count: 31 },
    ],
    channelDistribution: [
      { channel: 'Widget', count: 892 },
      { channel: 'Web App', count: 287 },
      { channel: 'WhatsApp', count: 68 },
    ],
  });

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-cyan-400"></div>
      </div>
    );
  }

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

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Total Conversations"
            value={stats?.totalConversations.toLocaleString() || '0'}
            change="+12.5%"
            positive={true}
            icon={
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            }
          />
          <StatCard
            title="Unique Sessions"
            value={stats?.totalSessions.toLocaleString() || '0'}
            change="+8.2%"
            positive={true}
            icon={
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
              </svg>
            }
          />
          <StatCard
            title="Avg Response Time"
            value={`${stats?.avgResponseTime.toFixed(1) || '0'}s`}
            change="-0.3s"
            positive={true}
            icon={
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
          />
          <StatCard
            title="Satisfaction Rate"
            value={`${stats?.positiveRating || 0}%`}
            change="+2.1%"
            positive={true}
            icon={
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.828 14.828a4 4 0 01-5.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            }
          />
        </div>

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
                    {stats?.channelDistribution.map((_, index) => (
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
            <div className="flex justify-center gap-4 mt-4">
              {stats?.channelDistribution.map((item, index) => (
                <div key={item.channel} className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: COLORS[index % COLORS.length] }}
                  />
                  <span className="text-sm text-gray-400">{item.channel}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl p-6 border border-gray-700/50">
            <h2 className="text-xl font-semibold text-white mb-4">Top Queries</h2>
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stats?.topQueries || []} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis type="number" stroke="#9ca3af" fontSize={12} />
                  <YAxis
                    dataKey="query"
                    type="category"
                    stroke="#9ca3af"
                    fontSize={11}
                    width={150}
                    tickFormatter={(value) =>
                      value.length > 20 ? value.substring(0, 20) + '...' : value
                    }
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1f2937',
                      border: '1px solid #374151',
                      borderRadius: '8px',
                      color: '#fff',
                    }}
                  />
                  <Bar dataKey="count" fill="#03a9f4" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl p-6 border border-gray-700/50">
            <h2 className="text-xl font-semibold text-white mb-4">Recent Activity</h2>
            <div className="space-y-4">
              {[
                { time: '2 min ago', event: 'New conversation started', type: 'info' },
                { time: '5 min ago', event: 'User asked about Balance Mastery', type: 'success' },
                { time: '12 min ago', event: 'Discovery call link shared', type: 'success' },
                { time: '18 min ago', event: 'Positive feedback received', type: 'success' },
                { time: '25 min ago', event: 'New widget session from mobile', type: 'info' },
                { time: '32 min ago', event: 'Pricing inquiry handled', type: 'success' },
              ].map((activity, index) => (
                <div
                  key={index}
                  className="flex items-center gap-4 p-3 bg-gray-700/30 rounded-lg hover:bg-gray-700/50 transition-colors"
                >
                  <div
                    className={`w-2 h-2 rounded-full ${
                      activity.type === 'success' ? 'bg-green-400' : 'bg-cyan-400'
                    }`}
                  />
                  <div className="flex-1">
                    <p className="text-sm text-white">{activity.event}</p>
                    <p className="text-xs text-gray-500">{activity.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-8 text-center text-gray-500 text-sm">
          <p>Dashboard prototype • Data shown is for demonstration purposes</p>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  change,
  positive,
  icon,
}: {
  title: string;
  value: string;
  change: string;
  positive: boolean;
  icon: React.ReactNode;
}) {
  return (
    <div className="bg-gray-800/50 backdrop-blur-sm rounded-2xl p-6 border border-gray-700/50 hover:border-cyan-500/30 transition-all hover:shadow-lg hover:shadow-cyan-500/5">
      <div className="flex items-center justify-between mb-4">
        <div className="p-3 bg-cyan-500/10 rounded-xl text-cyan-400">{icon}</div>
        <span
          className={`text-sm font-medium px-2 py-1 rounded-full ${
            positive ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
          }`}
        >
          {change}
        </span>
      </div>
      <h3 className="text-gray-400 text-sm font-medium">{title}</h3>
      <p className="text-3xl font-bold text-white mt-1">{value}</p>
    </div>
  );
}
