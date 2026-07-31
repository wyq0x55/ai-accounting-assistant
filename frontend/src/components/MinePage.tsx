import { useEffect, useState } from 'react';
import { api } from '../lib/api';
import Categories from './Categories';
import Mappings from './Mappings';

type Panel = 'none' | 'categories' | 'mappings';

export default function MinePage() {
  const [health, setHealth] = useState<Record<string, unknown>>({});
  const [panel, setPanel] = useState<Panel>('none');
  const [syncMsg, setSyncMsg] = useState('');

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth({}));
  }, []);

  async function retrySync() {
    const r = await api.retrySync();
    setSyncMsg(`重试 ${r.attempted} 条，成功同步 ${r.synced} 条`);
    setTimeout(() => setSyncMsg(''), 2400);
  }

  const llm = Boolean(health.llm_enabled);
  const bridge = Boolean(health.bridge_reachable);

  return (
    <div className="scroll">
      <div className="section-title">系统状态</div>
      <div className="card">
        <div className="list-row">
          <span>本地 LLM</span>
          <span className="r">{llm ? '在线' : '规则模式（离线）'}</span>
        </div>
        <div className="list-row">
          <span>Actual Budget</span>
          <span className="r">{bridge ? '已连接' : '未连接'}</span>
        </div>
        <div className="list-row">
          <span>待同步账目</span>
          <button className="link" onClick={retrySync}>立即重试</button>
        </div>
        {syncMsg && <div className="r" style={{ paddingTop: 6 }}>{syncMsg}</div>}
      </div>

      <div className="section-title">数据与设置</div>
      <div className="card">
        <div className="list-row" onClick={() => setPanel(panel === 'categories' ? 'none' : 'categories')}>
          <span>🏷️ 分类管理</span>
          <span className="r">{panel === 'categories' ? '收起' : '›'}</span>
        </div>
        {panel === 'categories' && <Categories />}
        <div className="list-row" onClick={() => setPanel(panel === 'mappings' ? 'none' : 'mappings')}>
          <span>🧠 商户映射（自学习）</span>
          <span className="r">{panel === 'mappings' ? '收起' : '›'}</span>
        </div>
        {panel === 'mappings' && <Mappings />}
      </div>

      <div className="section-title">账本</div>
      <div className="card">
        <a
          className="list-row"
          href={`${window.location.protocol}//${window.location.hostname}:5006`}
          target="_blank"
          rel="noreferrer"
          style={{ textDecoration: 'none', color: 'inherit' }}
        >
          <span>📒 打开 Actual Budget（预算/报表/家庭共享）</span>
          <span className="r">›</span>
        </a>
      </div>

      <div className="empty">本地优先 · 数据自托管 · 支持离线</div>
    </div>
  );
}
