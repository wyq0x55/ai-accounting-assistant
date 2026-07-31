import { useEffect, useRef, useState } from 'react';
import { api, Category } from '../lib/api';
import { catIcon } from '../lib/ui';

const KEYS = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '.', '0', '⌫'];

export default function EntryPage({ onSaved }: { onSaved?: () => void }) {
  const [amount, setAmount] = useState('0');
  const [direction, setDirection] = useState<'expense' | 'income'>('expense');
  const [categories, setCategories] = useState<Category[]>([]);
  const [category, setCategory] = useState('餐饮');
  const [merchant, setMerchant] = useState('');
  const [toast, setToast] = useState('');
  const [busy, setBusy] = useState(false);
  const [pasteOpen, setPasteOpen] = useState(false);
  const [pasteText, setPasteText] = useState('');
  const recognizing = useRef(false);

  useEffect(() => {
    api.listCategories().then((r) => setCategories(r.items));
  }, []);

  function press(k: string) {
    setAmount((prev) => {
      if (k === '⌫') return prev.length <= 1 ? '0' : prev.slice(0, -1);
      if (k === '.') return prev.includes('.') ? prev : prev + '.';
      const next = prev === '0' ? k : prev + k;
      // limit to 2 decimals
      const parts = next.split('.');
      if (parts[1] && parts[1].length > 2) return prev;
      return next;
    });
  }

  function flash(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(''), 1600);
  }

  async function save() {
    const val = parseFloat(amount);
    if (!val || val <= 0) return flash('请输入金额');
    setBusy(true);
    try {
      await api.ingestManual({
        amount: val,
        category,
        direction,
        merchant: merchant.trim() || undefined,
      });
      setAmount('0');
      setMerchant('');
      flash('已记账 ✓');
      onSaved?.();
    } catch (e) {
      flash((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function submitPaste() {
    if (!pasteText.trim()) return;
    setBusy(true);
    try {
      await api.ingestText(pasteText.trim());
      setPasteText('');
      setPasteOpen(false);
      flash('已加入待确认队列');
      onSaved?.();
    } catch (e) {
      flash((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function startVoice() {
    const SR =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) {
      setPasteOpen(true);
      return flash('当前浏览器不支持语音，改用粘贴');
    }
    if (recognizing.current) return;
    const rec = new SR();
    rec.lang = 'zh-CN';
    rec.interimResults = false;
    recognizing.current = true;
    flash('🎙 请说话…');
    rec.onresult = (e: any) => {
      const text = e.results[0][0].transcript as string;
      setPasteText(text);
      setPasteOpen(true);
    };
    rec.onend = () => {
      recognizing.current = false;
    };
    rec.start();
  }

  return (
    <div className="scroll">
      <div className="amount-display">
        <span className="cur">¥</span>
        <span className="num">{amount}</span>
      </div>

      <div className="dir-toggle">
        <button
          className={direction === 'expense' ? 'active' : ''}
          onClick={() => setDirection('expense')}
        >
          支出
        </button>
        <button
          className={direction === 'income' ? 'active' : ''}
          onClick={() => setDirection('income')}
        >
          收入
        </button>
      </div>

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
        placeholder="商户（可选）"
        value={merchant}
        onChange={(e) => setMerchant(e.target.value)}
        style={{ marginBottom: 12 }}
      />

      <div className="keypad">
        {KEYS.map((k) => (
          <button key={k} className="key" onClick={() => press(k)}>
            {k}
          </button>
        ))}
      </div>

      <div className="row" style={{ marginTop: 12 }}>
        <button className="btn line" onClick={startVoice}>🎙 语音</button>
        <button className="btn line" onClick={() => setPasteOpen(true)}>📋 粘贴</button>
        <button className="btn" disabled={busy} onClick={save} style={{ flex: 2 }}>
          保存
        </button>
      </div>

      {pasteOpen && (
        <div
          style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.35)', zIndex: 60,
            display: 'flex', alignItems: 'flex-end', maxWidth: 440, margin: '0 auto',
          }}
          onClick={() => setPasteOpen(false)}
        >
          <div
            className="card"
            style={{ width: '100%', borderRadius: '20px 20px 0 0', margin: 0 }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ fontWeight: 700, marginBottom: 10 }}>粘贴支付信息，AI 自动识别</div>
            <textarea
              className="field"
              placeholder={'支付宝付款成功\n商户：永辉超市\n金额：126.58 元'}
              value={pasteText}
              onChange={(e) => setPasteText(e.target.value)}
            />
            <button className="btn" disabled={busy} onClick={submitPaste} style={{ marginTop: 12 }}>
              识别并加入队列
            </button>
          </div>
        </div>
      )}

      {toast && <div className="toast">{toast}</div>}
    </div>
  );
}
