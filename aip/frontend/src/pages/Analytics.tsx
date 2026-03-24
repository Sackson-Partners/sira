import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../services/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const COLORS = ['#3b82f6','#10b981','#f59e0b','#ef4444','#8b5cf6','#06b6d4'];

export default function Analytics() {
  const { data: dash } = useQuery({ queryKey: ['analytics-dash'], queryFn: () => analyticsApi.dashboard().then((r) => r.data) });
  const { data: funnel } = useQuery({ queryKey: ['pipeline-funnel'], queryFn: () => analyticsApi.pipelineFunnel().then((r) => r.data) });
  const { data: investors } = useQuery({ queryKey: ['investor-breakdown'], queryFn: () => analyticsApi.investorBreakdown().then((r) => r.data) });

  const fmtUSD = (v: number) => v >= 1e9 ? `$${(v/1e9).toFixed(1)}B` : v >= 1e6 ? `$${(v/1e6).toFixed(1)}M` : `$${v.toLocaleString()}`;

  const investorByTypeData = investors
    ? Object.entries(investors.by_type || {}).map(([name, value]) => ({ name, value }))
    : [];

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>

      {/* Pipeline Funnel */}
      {funnel && (
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <h2 className="font-semibold text-gray-700 mb-4">Pipeline Funnel</h2>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={funnel.slice(0, 8)} margin={{ top: 10, right: 10, bottom: 40, left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="stage" angle={-30} textAnchor="end" tick={{ fontSize: 11 }} />
              <YAxis />
              <Tooltip formatter={(v: any) => v.toLocaleString()} />
              <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Investor Breakdown */}
      {investorByTypeData.length > 0 && (
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <h2 className="font-semibold text-gray-700 mb-4">Investors by Type</h2>
          <div className="flex gap-6 items-center">
            <PieChart width={200} height={200}>
              <Pie data={investorByTypeData} cx={90} cy={90} innerRadius={50} outerRadius={80} dataKey="value">
                {investorByTypeData.map((_: any, i: number) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip />
            </PieChart>
            <div className="flex flex-col gap-2">
              {investorByTypeData.map((d: any, i: number) => (
                <div key={d.name} className="flex items-center gap-2 text-sm">
                  <span className="w-3 h-3 rounded-full shrink-0" style={{ background: COLORS[i % COLORS.length] }} />
                  <span className="capitalize text-gray-600">{d.name.replace('_', ' ')}</span>
                  <span className="font-semibold text-gray-800">{d.value}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Summary stats */}
      {dash && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-blue-50 rounded-xl p-4 border border-blue-100">
            <p className="text-xs text-blue-500 font-medium uppercase">Total Projects</p>
            <p className="text-3xl font-bold text-blue-700">{dash.projects.total}</p>
          </div>
          <div className="bg-green-50 rounded-xl p-4 border border-green-100">
            <p className="text-xs text-green-500 font-medium uppercase">Committed Capital</p>
            <p className="text-3xl font-bold text-green-700">{fmtUSD(dash.financials.total_committed_usd)}</p>
          </div>
          <div className="bg-purple-50 rounded-xl p-4 border border-purple-100">
            <p className="text-xs text-purple-500 font-medium uppercase">Win Rate</p>
            <p className="text-3xl font-bold text-purple-700">{dash.pipeline.win_rate}%</p>
          </div>
          <div className="bg-orange-50 rounded-xl p-4 border border-orange-100">
            <p className="text-xs text-orange-500 font-medium uppercase">Total AUM</p>
            <p className="text-3xl font-bold text-orange-700">{fmtUSD(investors?.total_aum || 0)}</p>
          </div>
        </div>
      )}
    </div>
  );
}
