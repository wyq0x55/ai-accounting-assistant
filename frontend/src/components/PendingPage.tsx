import { useEffect, useRef, useState } from 'react';
import type { PointerEvent as ReactPointerEvent } from 'react';
import { api, Category, Transaction } from '../lib/api';
import { catIcon, money } from '../lib/ui';

const THRESHOLD = 96;

const SOURCE_LABEL: Record<string, string> = {
  mapping: '历史学习',
  rule: '规则',
  llm: 'AI',
  fallback: '未识别',
  manual: '手动',
};

/** A single swipeable inbox card. Swipe left = confirm, swipe right = edit. */
function SwipeCard({
  tx,
  onConfirm,
  onEdit,
}: {
  tx: Transaction;
  onConfirm: () => void;
  onEdit: () => void;
}) {
  const [dx, setDx] = useState(0);
  const [dragging, setDragging] = useState(false);
  const startX = useRef(0);

  function down(e: ReactPointerEvent) {
    startX.current = e.clientX;
    setDragging(true);
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }
  function move(e: ReactPointerEvent) {
    if (!dragging) return;
    setDx(Math.max(-140, Math.min(140, e.clientX - startX.current)));
  }
  function up() {
    setDragging(false);
    if (dx <= -THRESHOLD) onConfirm();
    else if (dx >= THRESHOLD) onEdit();
    setDx(0);
  }

  const conf = Math.round((tx.confidence || 0) * 100);
  const highConf = conf >= 80;

  return (
    <div className="swipe-wrap">
      <div className="swipe-bg">
        {/* left revealed when swiping right => edit */}
        <div className="right" style={{ background: 'var(--pending)' }}>修改</div>
        {/* right revealed when swiping left => confirm */}
        <div className="left" style={{ background: 'var(--brand)' }}>确认 ✓</div>
      </div>
      <div
        className={`swipe-fg ${dragging ? 'dragging' : ''}`}
        style={{ transform: `translateX(${dx}px)` }}
        onPointerDown={down}
        onPointerMove={move}
        onPointerUp={up}
        onPointerCancel={up}
      >
        <div className="inbox-top">
          <div className="avatar">{catIcon(tx.category)}</div>
          <div style={{ flex: 1 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span className="name">{tx.merchant || '未知商户'}</span>
              <span className="inbox-amt">¥{money(tx.amount)}</span>
            </div>
            <div className="inbox-meta">
              {tx.date} · {tx.pay_method || '支付'} · 来源 {SOURCE_LABEL[tx.classify_source] || tx.classify_source}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 10 }}>
          <span className={`chip ${highConf ? 'green' : 'amber'}`}>
            {catIcon(tx.category)} {tx.category}
          </span>
          <span className={`chip ${highConf ? 'green' : 'amber'}`}>置信度 {conf}%</span>
        </div>
        <div className="conf-bar">
          <div
            className="conf-fill"
            style={{ width: `${conf}%`, background: highConf ? 'var(--brand)' : 'var(--expense)' }}
          />
        </div>
      </div>
    </div>
  );
}

/** Bottom edit sheet. */
function EditSheet({
  tx,
  categories,
  onClose,
  onSaved,
}: {
  tx: Transaction;
  categories: Category[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [category, setCategory] = useState(tx.category || '其他');
  const [amount, setAmount] = useState(tx.amount ?? 0);
  const [busy, setBusy] = useState(false);

  async function save(confirm: boolean) {
    setBusy(true);
    try {
      await api.updateTransaction(tx.id, { category, amount });
      if (confirm) await api.confirmTransaction(tx.id);
      onSaved();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', zIndex: 60,
        display: 'flex', alignItems: 'flex-end', maxWidth: 440, margin: '0 auto',
      }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{ width: '100%', borderRadius: '20px 20px 0 0', margin: 0, paddingBottom: 24 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ fontWeight: 700, marginBottom: 12 }}>{tx.merchant || '未知商户'} · 修改</div>
        <div className="cat-grid">
          {categories.slice(0, 10).map((c) => (
            <button
              key={c.id}
              className={`cat-cell ${category === c.name ? 'active' : ''}`}
              onClick={() => setCategory(c.name)}
            >
              <span className="ic">{catIcon(c.name)}</span>
              {c.name}
            </button>
          ))}
        </div>
        <input
          className="field"
          type="number"
          step="0.01"
          value={amount}
          onChange={(e) => setAmount(parseFloat(e.target.value))}
          style={{ marginBottom: 12 }}
        />
        <div className="row">
          <button className="btn ghost" disabled={busy} onClick={() => save(false)}>
            仅保存
          </button>
          <button className="btn" disabled={busy} onClick={() => save(true)}>
            保存并确认
          </button>
        </div>
      </div>
    </div>
  );
}

export default function PendingPage({ onChanged }: { onChanged?: () => void }) {
  const [items, setItems] = useState<Transaction[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [editing, setEditing] = useState<Transaction | null>(null);
  const [toast, setToast] = useState('');
  const [loading, setLoading] = useState(true);

  async function load() {
    const [txs, cats] = await Promise.all([
      api.listTransactions(),
      api.listCategories(),
    ]);
    setItems(txs.items.filter((t) => t.state === 'pending_review'));
    setCategories(cats.items);
    setLoading(false);
    onChanged?.();
  }

  useEffect(() => {
    load();
  }, []);

  function flash(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(''), 1600);
  }

  async function confirm(tx: Transaction) {
    await api.confirmTransaction(tx.id);
    setItems((prev) => prev.filter((t) => t.id !== tx.id));
    flash('已确认 ✓');
    onChanged?.();
  }

  const manual = items.filter((t) => (t.confidence || 0) < 0.6).length;

  return (
    <div className="scroll">
      <div className="banner" style={{ background: 'var(--brand-weak)', color: 'var(--brand)' }}>
        <span>📥 {items.length} 条待确认{manual ? ` · ${manual} 条需留意` : ''}</span>
        <span style={{ fontWeight: 500 }}>左滑确认 · 右滑修改</span>
      </div>

      {loading && <div className="empty">加载中…</div>}
      {!loading && items.length === 0 && (
        <div className="empty">🎉 全部确认完毕，收件箱已清空</div>
      )}

      {items.map((tx) => (
        <SwipeCard
          key={tx.id}
          tx={tx}
          onConfirm={() => confirm(tx)}
          onEdit={() => setEditing(tx)}
        />
      ))}

      {editing && (
        <EditSheet
          tx={editing}
          categories={categories}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            load();
            flash('已更新');
          }}
        />
      )}
      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
