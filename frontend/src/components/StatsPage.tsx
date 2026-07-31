import { useEffect, useState } from 'react';
import { api, MonthlyReport } from '../lib/api';
import { CHART_COLORS, money } from '../lib/ui';

function currentMonth(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
}

/** SVG donut chart from category breakdown. */
function Donut({
  data,
  total,
}: {
  data: { category: string; percent: number }[];
  total: number;
}) {
  const R = 46;
  const C = 2 * Math.PI * R;
  let offset = 0;
  const segments = data.slice(0, CHART_COLORS.length).map((d, i) => {
    const len = (d.percent / 100) * C;
    const seg = (
      <circle
        key={d.category}
        cx="60"
        cy="60"
        r={R}
        fill="none"
        stroke={CHART_COLORS[i]}
        strokeWidth="14"
        strokeDasharray={`${len} ${C - len}`}
        strokeDashoffset={-offset}
        transform="rotate(-90 60 60)"
        strokeLinecap="butt"
      />
    );
    offset += len;
    return seg;
  });

  return (
    <div className="ring-wrap">
      <svg width="120" height="120" viewBox="0 0 120 120">
        <circle cx="60" cy="60" r={R} fill="none" stroke="#eef1f5" strokeWidth="14" />
        {segments}
      </svg>
      <div className="legend">
        {data.slice(0, 6).map((d, i) => (
          <div className="legend-row" key={d.category}>
            <span className="sw" style={{ background: CHART_COLORS[i] }} />
            <span>{d.category}</span>
            <span className="lp">{d.percent}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function StatsPage() {
  const [month, setMonth] = useState(currentMonth());
  const [report, setReport] = useState<MonthlyReport | null>(null);
  const [loading, setLoading] = useState(true);

  async function load(m: string) {
    setLoading(true);
    try {
      setReport(await api.monthlyReport(m));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(month);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const stats = report?.stats;
  const maxCat = stats?.category_breakdown[0]?.amount || 1;
  const maxTrend = Math.max(1, ...(stats?.trend.map((t) => t.expense) || [1]));

  return (
    <div className="scroll">
      <div className="row" style={{ margin: '6px 0 10px' }}>
        <input
          className="field"
          type="month"
          value={month}
          onChange={(e) => {
            setMonth(e.target.value);
            load(e.target.value);
          }}
        />
      </div>

      {/* AI insight */}
      {report && (
        <div className="card ai-card">
          <div className="ai-h">✨ AI 分析{report.source === 'llm' ? '' : '（离线模板）'}</div>
          <p>{report.summary}</p>
        </div>
      )}

      {loading && <div className="empty">加载中…</div>}

      {stats && (
        <>
          <div className="section-title">本月分类占比</div>
          <div className="card">
            {stats.category_breakdown.length === 0 ? (
              <div className="empty">本月暂无数据</div>
            ) : (
              <Donut data={stats.category_breakdown} total={stats.total_expense} />
            )}
          </div>

          {stats.category_breakdown.length > 0 && (
            <>
              <div className="section-title">分类明细</div>
              <div className="card">
                {stats.category_breakdown.map((c) => (
                  <div className="bar-row" key={c.category}>
                    <div className="bl">
                      <span>{c.category}</span>
                      <span>¥{money(c.amount)}</span>
                    </div>
                    <div className="bar-track">
                      <div className="bar-fill" style={{ width: `${(c.amount / maxCat) * 100}%` }} />
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {stats.trend.length > 0 && (
            <>
              <div className="section-title">消费趋势</div>
              <div className="card">
                <div style={{ display: 'flex', alignItems: 'flex-end', gap: 8, height: 120 }}>
                  {stats.trend.map((t) => (
                    <div key={t.month} style={{ flex: 1, textAlign: 'center' }}>
                      <div
                        style={{
                          height: `${(t.expense / maxTrend) * 96}px`,
                          background: 'var(--brand)',
                          borderRadius: 8,
                          minHeight: 4,
                        }}
                      />
                      <div style={{ fontSize: 10, color: 'var(--muted)', marginTop: 6 }}>
                        {t.month.slice(5)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          <div className="section-title">商户 TOP</div>
          <div className="card">
            {stats.top_merchants.length === 0 && <div className="empty">暂无数据</div>}
            {stats.top_merchants.map((m, i) => (
              <div className="tx" key={m.merchant}>
                <div className="avatar" style={{ background: '#f1f3f6' }}>{i + 1}</div>
                <div className="mid">
                  <div className="name">{m.merchant}</div>
                </div>
                <div className="amt expense">¥{money(m.amount)}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
