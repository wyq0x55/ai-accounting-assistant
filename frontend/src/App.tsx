import { useEffect, useState } from 'react';
import { api } from './lib/api';
import HomePage from './components/HomePage';
import PendingPage from './components/PendingPage';
import EntryPage from './components/EntryPage';
import StatsPage from './components/StatsPage';
import MinePage from './components/MinePage';

type Tab = 'home' | 'pending' | 'entry' | 'stats' | 'mine';

const TABS: { key: Tab; label: string; icon: string; center?: boolean }[] = [
  { key: 'home', label: '首页', icon: '🏠' },
  { key: 'pending', label: '待确认', icon: '📥' },
  { key: 'entry', label: '记账', icon: '＋', center: true },
  { key: 'stats', label: '统计', icon: '📊' },
  { key: 'mine', label: '我的', icon: '👤' },
];

const TITLES: Record<Tab, string> = {
  home: '概览',
  pending: '待确认',
  entry: '记一笔',
  stats: '统计',
  mine: '我的',
};

export default function App() {
  const [tab, setTab] = useState<Tab>('home');
  const [pending, setPending] = useState(0);
  const [health, setHealth] = useState<{ llm: boolean; bridge: boolean }>({
    llm: false,
    bridge: false,
  });

  async function refreshMeta() {
    try {
      const [h, all] = await Promise.all([api.health(), api.listTransactions()]);
      setHealth({
        llm: Boolean((h as Record<string, unknown>).llm_enabled),
        bridge: Boolean((h as Record<string, unknown>).bridge_reachable),
      });
      setPending(all.items.filter((t) => t.state === 'pending_review').length);
    } catch {
      /* offline: ignore */
    }
  }

  useEffect(() => {
    refreshMeta();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  return (
    <div className="phone">
      <div className="nav">
        <h1>{TITLES[tab]}</h1>
        <div className="status">
          <span className={`dot ${health.llm ? 'on' : ''}`}>AI {health.llm ? '在线' : '规则'}</span>
          <span className={`dot ${health.bridge ? 'on' : ''}`}>Actual</span>
        </div>
      </div>

      {tab === 'home' && <HomePage onGoPending={() => setTab('pending')} />}
      {tab === 'pending' && <PendingPage onChanged={refreshMeta} />}
      {tab === 'entry' && <EntryPage onSaved={refreshMeta} />}
      {tab === 'stats' && <StatsPage />}
      {tab === 'mine' && <MinePage />}

      <nav className="tabbar">
        {TABS.map((t) => (
          <button
            key={t.key}
            className={`tab ${t.center ? 'center' : ''} ${tab === t.key ? 'active' : ''}`}
            onClick={() => setTab(t.key)}
          >
            <span className="ic" style={{ position: 'relative' }}>
              {t.icon}
              {t.key === 'pending' && pending > 0 && (
                <span
                  style={{
                    position: 'absolute', top: -4, right: -10, background: 'var(--pending)',
                    color: '#fff', fontSize: 9, borderRadius: 999, padding: '1px 5px', fontWeight: 700,
                  }}
                >
                  {pending}
                </span>
              )}
            </span>
            {t.label}
          </button>
        ))}
      </nav>
    </div>
  );
}
