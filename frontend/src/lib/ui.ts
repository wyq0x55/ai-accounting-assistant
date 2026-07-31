// Shared UI helpers: currency formatting and category icons.

export function money(n: number | null | undefined): string {
  const v = Number(n || 0);
  return v.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// Emoji icon per category (falls back to a generic tag).
export const CATEGORY_ICONS: Record<string, string> = {
  餐饮: '🍜',
  交通: '🚌',
  购物: '🛒',
  日用品: '🧻',
  医疗: '💊',
  教育: '📚',
  娱乐: '🎮',
  数码电子: '💻',
  宠物: '🐾',
  人情往来: '🎁',
  通讯: '📱',
  房租住房: '🏠',
  投资理财: '📈',
  其他: '🏷️',
};

export function catIcon(name: string | null | undefined): string {
  if (!name) return '🏷️';
  return CATEGORY_ICONS[name] || '🏷️';
}

// Donut chart colors (brand-led, soft palette).
export const CHART_COLORS = [
  '#2bc673',
  '#3b82f6',
  '#f59e0b',
  '#a78bfa',
  '#ef4444',
  '#14b8a6',
  '#f472b6',
  '#64748b',
];
