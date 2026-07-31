import { useEffect, useState } from 'react';
import { api, Stats, Transaction } from '../lib/api';
import { catIcon, money } from '../lib/ui';

function currentMonth(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

export default function HomePage({ onGoPending }: { onGoPending: () => void }) {
  const [stats, setStats] = useState<Stats | null>(null);
  const [recent, setRecent] = useState<Transaction[]>([]);
  const [pendingCount, setPendingCount] = useState(0);

  async function load() {
    const [s, txs] = await Promise.all([
      api.stats(currentMonth()),
      api.listTransactions(),
    ]);
    setStats(s);
    const items = txs.items;
    setPendingCount(items.filter((t) => t.state === 'pending_review').length);
    setRecent(
      items
        .filter((t) => t.state === 'confirmed' || t.state === 'archived')
        .slice(0, 8),
    );
  }

  useEffect(() => {
    load();
  }, []);

  const balance = (stats?.total_income || 0) - (stats?.total_expense || 0);

  return (
    <div className="scroll">
      <div className="hero">
        <div className="label">本月支出</div>
        <div className="big">¥{money(stats?.total_expense)}</div>
        <div className="yoy">共 {stats?.transaction_count ?? 0} 笔消费</div>
        <div className="split">
          <div>
            <div className="k">本月收入</div>
            <div className="v">¥{money(stats?.total_income)}</div>
          </div>
          <div>
            <div className="k">结余</div>
            <div className="v">¥{money(balance)}</div>
          </div>
        </div>
      </div>

      {pendingCount > 0 && (
        <div className="banner" onClick={onGoPending} style={{ marginTop: 12, cursor: 'pointer' }}>
          <span>📥 有 {pendingCount} 条待确认账目</span>
          <span>去确认 ›</span>
        </div>
      )}

      <div className="section-title">最近消费</div>
      <div className="card">
        {recent.length === 0 && <div className="empty">还没有已确认的消费</div>}
        {recent.map((t) => (
          <div className="tx" key={t.id}>
            <div className="avatar">{catIcon(t.category)}</div>
            <div className="mid">
              <div className="name">{t.merchant || '未知商户'}</div>
              <div className="sub">
                {t.category || '未分类'} · {t.date}
              </div>
            </div>
            <div className={`amt ${t.direction === 'income' ? 'income' : 'expense'}`}>
              {t.direction === 'income' ? '+' : '-'}¥{money(t.amount)}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
