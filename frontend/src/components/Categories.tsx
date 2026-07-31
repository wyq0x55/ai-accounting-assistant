import { useEffect, useState } from 'react';
import { api, Category } from '../lib/api';
import { catIcon } from '../lib/ui';

export default function Categories() {
  const [items, setItems] = useState<Category[]>([]);
  const [name, setName] = useState('');
  const [err, setErr] = useState('');

  async function load() {
    setItems((await api.listCategories()).items);
  }
  useEffect(() => {
    load();
  }, []);

  async function add() {
    if (!name.trim()) return;
    setErr('');
    try {
      await api.createCategory(name.trim());
      setName('');
      load();
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  return (
    <div className="card">
      <div className="row" style={{ marginBottom: 12 }}>
        <input className="field" placeholder="新增分类" value={name} onChange={(e) => setName(e.target.value)} />
        <button className="btn" style={{ flex: '0 0 88px' }} onClick={add}>
          添加
        </button>
      </div>
      {err && <div className="error">{err}</div>}
      {items.map((c) => (
        <div className="list-row" key={c.id}>
          <span>
            {catIcon(c.name)} {c.name}
          </span>
          {c.is_default ? (
            <span className="r">默认</span>
          ) : (
            <button
              className="link-danger"
              onClick={async () => {
                await api.deleteCategory(c.id);
                load();
              }}
            >
              删除
            </button>
          )}
        </div>
      ))}
    </div>
  );
}
