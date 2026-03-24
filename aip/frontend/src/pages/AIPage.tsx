import React, { useState, useRef, useEffect } from 'react';
import { aiApi, pisApi, pestelApi, einApi } from '../services/api';
import toast from 'react-hot-toast';

interface Message { role: 'user' | 'assistant'; content: string; }

export default function AIPage() {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'Hello! I\'m the AIP AI assistant. I can help you analyze projects, generate PIS/PESTEL/EIN reports, and answer investment questions. How can I help?' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [projectId, setProjectId] = useState('');
  const [genLoading, setGenLoading] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);

  const send = async () => {
    if (!input.trim()) return;
    const q = input.trim();
    setInput('');
    setMessages((m) => [...m, { role: 'user', content: q }]);
    setLoading(true);
    try {
      const { data } = await aiApi.chat(q);
      setMessages((m) => [...m, { role: 'assistant', content: data.answer }]);
    } catch {
      setMessages((m) => [...m, { role: 'assistant', content: 'Error: AI service unavailable. Check ANTHROPIC_API_KEY configuration.' }]);
    } finally { setLoading(false); }
  };

  const generate = async (type: 'pis' | 'pestel' | 'ein') => {
    if (!projectId) { toast.error('Enter a Project ID first'); return; }
    setGenLoading(type);
    try {
      const api = type === 'pis' ? pisApi : type === 'pestel' ? pestelApi : einApi;
      await api.generateAI(Number(projectId));
      toast.success(`${type.toUpperCase()} generated for Project #${projectId}`);
    } catch (err: any) {
      toast.error(err?.response?.data?.detail || `Failed to generate ${type.toUpperCase()}`);
    } finally { setGenLoading(null); }
  };

  return (
    <div className="space-y-4 h-full flex flex-col">
      <h1 className="text-2xl font-bold text-gray-900">AI Engine</h1>

      {/* AI Generate Actions */}
      <div className="bg-blue-50 rounded-xl border border-blue-200 p-4">
        <h2 className="font-semibold text-blue-800 mb-3">Auto-Generate Reports with AI</h2>
        <div className="flex items-center gap-3 flex-wrap">
          <input
            type="number"
            placeholder="Project ID"
            value={projectId}
            onChange={(e) => setProjectId(e.target.value)}
            className="border rounded-lg px-3 py-2 text-sm w-32"
          />
          {(['pis', 'pestel', 'ein'] as const).map((type) => (
            <button
              key={type}
              onClick={() => generate(type)}
              disabled={genLoading === type}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {genLoading === type ? 'Generating...' : `Generate ${type.toUpperCase()}`}
            </button>
          ))}
        </div>
        <p className="text-xs text-blue-600 mt-2">Enter a project ID and click to auto-generate the analysis using AI</p>
      </div>

      {/* Chat */}
      <div className="flex-1 bg-white rounded-xl border border-gray-200 flex flex-col min-h-0">
        <div className="p-3 border-b">
          <h2 className="font-medium text-gray-700 text-sm">AI Investment Assistant</h2>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3 max-h-96">
          {messages.map((m, i) => (
            <div key={i} className={`flex ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm ${m.role === 'user' ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-800'}`}>
                <pre className="whitespace-pre-wrap font-sans">{m.content}</pre>
              </div>
            </div>
          ))}
          {loading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-2xl px-4 py-2 text-sm text-gray-500">Thinking...</div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
        <div className="p-3 border-t flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
            placeholder="Ask about projects, deals, investors..."
            className="flex-1 border rounded-lg px-3 py-2 text-sm"
          />
          <button onClick={send} disabled={loading || !input.trim()} className="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium disabled:opacity-50">
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
