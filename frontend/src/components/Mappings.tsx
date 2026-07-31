import { useEffect, useState } from 'react';
import { api, MerchantMapping } from '../lib/api';
import { catIcon } from '../lib/ui';

export default function Mappings() {
  const [items, setItems] = useState<MerchantMapping[]>([]);

  async function load() {
    setItems((await api.listMappings()).items);
  }
  useEffect(() => {
    load();
  }, []);

  return (
    <div className="card">
      <div className="r" style={{ marginBottom: 10 }}>
        每次你修正分类，系统会记住「商户 → 分类」，相同商户下次自动分类，逐步减少 AI 调用。
      </div>
      {items.length === 0 && <div className="empty">暂无学习记录</div>}
      {items.map((m) => (
        <div className="list-row" key={m.id}>
          <span>
            {catIcon(m.category)} {m.merchant_name}
            <span className="r" style={{ marginLeft: 8 }}>
              → {m.category} · {m.hit_count}次
            </span>
          </span>
          <button
            className="link-danger"
            onClick={async () => {
              await api.deleteMapping(m.id);
              load();
            }}
          >
            删除
          </button>
        </div>
      ))}
    </div>
  );
}
