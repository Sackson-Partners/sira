import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { analyticsApi } from '../services/api';

function KPICard({ title, value, subtitle, color = 'blue' }: any) {
  const colors: any = {
    blue: 'bg-blue-50 text-blue-700 border-blue-200',
    green: 'bg-green-50 text-green-700 border-green-200',
    purple: 'bg-purple-50 text-purple-700 border-purple-200',
    orange: 'bg-orange-50 text-orange-700 border-orange-200',
    red: 'bg-red-50 text-red-700 border-red-200',
  };
  return (
    <div className={`rounded-xl border p-4 ${colors[color]}`}>
      <p className="text-xs font-medium uppercase tracking-wide opacity-70">{title}</p>
      <p className="text-3xl font-bold mt-1">{value}</p>
      {subtitle && <p className="text-xs mt-1 opacity-70">{subtitle}</p>}
    </div>
  );
}

export default function Dashboard() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => analyticsApi.dashboard().then((r) => r.data),
    refetchInterval: 30000,
  });

  if (isLoading) return <div className="flex items-center justify-center h-64 text-gray-400">Loading dashboard...</div>;
  if (!data) return null;

  const fmtUSD = (v: number) => v >= 1e9 ? `$${(v/1e9).toFixed(1)}B` : v >= 1e6 ? `$${(v/1e6).toFixed(1)}M` : `$${v.toLocaleString()}`;

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>

      {/* Top KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KPICard title="Total Projects" value={data.projects.total} subtitle={`${data.projects.active} active`} color="blue" />
        <KPICard title="Pipeline Value" value={fmtUSD(data.pipeline.total_value)} subtitle={`${data.pipeline.total_deals} deals`} color="green" />
        <KPICard title="Total Investors" value={data.investors.total} subtitle={`${data.investors.active} active`} color="purple" />
        <KPICard title="IC Pending" value={data.ic.pending} subtitle={`${data.ic.approved} approved`} color="orange" />
      </div>

      {/* Secondary KPIs */}
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        <KPICard title="Total Committed" value={fmtUSD(data.financials.total_committed_usd)} color="green" />
        <KPICard title="Win Rate" value={`${data.pipeline.win_rate}%`} subtitle={`${data.pipeline.closed_won} won / ${data.pipeline.closed_lost} lost`} color="blue" />
        <KPICard title="New Projects (30d)" value={data.projects.new_this_month} color="purple" />
      </div>

      {/* Projects by status */}
      <div className="bg-white rounded-xl border border-gray-200 p-4">
        <h2 className="font-semibold text-gray-700 mb-4">Projects by Status</h2>
        <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
          {Object.entries(data.projects.by_status).map(([status, count]: any) => (
            <div key={status} className="text-center p-3 bg-gray-50 rounded-lg">
              <p className="text-2xl font-bold text-gray-800">{count}</p>
              <p className="text-xs text-gray-500 capitalize mt-1">{status.replace('_', ' ')}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
