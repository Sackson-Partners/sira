import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { integrationsApi } from '../services/api';
import toast from 'react-hot-toast';

export default function Integrations() {
  const qc = useQueryClient();
  const { data: available } = useQuery({ queryKey: ['integrations-available'], queryFn: () => integrationsApi.available().then((r) => r.data) });
  const { data: configured } = useQuery({ queryKey: ['integrations'], queryFn: () => integrationsApi.list().then((r) => r.data) });

  const testMutation = useMutation({
    mutationFn: (id: number) => integrationsApi.test(id),
    onSuccess: (data) => toast.success(data.data.message),
    onError: (err: any) => toast.error(err?.response?.data?.detail || 'Test failed'),
  });

  const configuredMap = new Map((configured || []).map((i: any) => [i.integration_type, i]));

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Integrations</h1>
      </div>

      {/* Azure AD B2C Banner */}
      <div className="bg-blue-900 text-white rounded-xl p-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-blue-700 rounded-lg flex items-center justify-center text-2xl">🔷</div>
          <div>
            <h2 className="font-bold text-lg">Azure Active Directory B2C</h2>
            <p className="text-blue-200 text-sm">Enterprise SSO — configure AZURE_AD_B2C_* environment variables to enable</p>
          </div>
        </div>
        <div className="mt-4 bg-blue-800 rounded-lg p-3 text-xs font-mono text-blue-100 space-y-1">
          <p>AZURE_AD_B2C_TENANT_NAME=vamosokohotmail</p>
          <p>AZURE_AD_B2C_CLIENT_ID=your-client-id</p>
          <p>AZURE_AD_B2C_CLIENT_SECRET=your-secret</p>
          <p>AZURE_AD_B2C_POLICY_NAME=B2C_1_signupsignin</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {(available || []).map((avail: any) => {
          const existing = configuredMap.get(avail.type);
          return (
            <div key={avail.type} className={`bg-white rounded-xl border p-4 ${existing ? 'border-green-300' : 'border-gray-200'}`}>
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="font-semibold text-gray-900">{avail.name}</h3>
                  <p className="text-sm text-gray-500 mt-1">{avail.description}</p>
                </div>
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${existing ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                  {existing ? existing.status || 'configured' : 'not configured'}
                </span>
              </div>
              {existing && (
                <div className="mt-3 flex gap-2">
                  <button
                    onClick={() => testMutation.mutate(existing.id)}
                    disabled={testMutation.isPending}
                    className="text-xs text-blue-600 border border-blue-300 px-3 py-1 rounded-lg hover:bg-blue-50"
                  >
                    Test Connection
                  </button>
                </div>
              )}
              {!existing && (
                <p className="text-xs text-gray-400 mt-3">Configure via environment variables or Admin API</p>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
