'use strict';

/**
 * Actual Budget bridge.
 *
 * Exposes a small internal REST surface consumed by the Flask assistant.
 * All ledger writes go through the official @actual-app/api library, which is
 * the only supported way to create transactions in Actual Budget.
 *
 * Configuration (environment variables):
 *   ACTUAL_SERVER_URL           e.g. http://actual_server:5006
 *   ACTUAL_PASSWORD             server password
 *   ACTUAL_SYNC_ID              budget "Sync ID" (Settings -> Advanced)
 *   ACTUAL_ENCRYPTION_PASSWORD  optional, if the budget file is E2E encrypted
 *   ACTUAL_DATA_DIR             local cache dir (default: /data)
 *   BRIDGE_PORT                 default 5008
 */

const express = require('express');
const { v4: uuidv4 } = require('uuid');
const api = require('@actual-app/api');

const PORT = parseInt(process.env.BRIDGE_PORT || '5008', 10);
const CONFIG = {
  serverURL: process.env.ACTUAL_SERVER_URL || '',
  password: process.env.ACTUAL_PASSWORD || '',
  syncId: process.env.ACTUAL_SYNC_ID || '',
  encryptionPassword: process.env.ACTUAL_ENCRYPTION_PASSWORD || '',
  dataDir: process.env.ACTUAL_DATA_DIR || '/data',
};

let ready = false;
let initPromise = null;

async function ensureReady() {
  if (ready) return;
  if (!CONFIG.serverURL || !CONFIG.syncId) {
    throw new Error('ACTUAL_SERVER_URL and ACTUAL_SYNC_ID must be configured');
  }
  if (!initPromise) {
    initPromise = (async () => {
      await api.init({
        dataDir: CONFIG.dataDir,
        serverURL: CONFIG.serverURL,
        password: CONFIG.password,
      });
      const opts = CONFIG.encryptionPassword
        ? { password: CONFIG.encryptionPassword }
        : undefined;
      await api.downloadBudget(CONFIG.syncId, opts);
      ready = true;
      console.log('[bridge] Actual budget loaded:', CONFIG.syncId);
    })().catch((err) => {
      initPromise = null; // allow retry on next request
      throw err;
    });
  }
  return initPromise;
}

function toMinorUnits(amount, direction) {
  const abs = Math.round(Math.abs(Number(amount) || 0) * 100);
  // Actual stores expenses as negative integers.
  return direction === 'income' ? abs : -abs;
}

const app = express();
app.use(express.json());

app.get('/health', async (req, res) => {
  res.json({
    status: 'ok',
    ready,
    configured: Boolean(CONFIG.serverURL && CONFIG.syncId),
  });
});

app.get('/accounts', async (req, res) => {
  try {
    await ensureReady();
    await api.sync();
    const accounts = await api.getAccounts();
    res.json({ accounts });
  } catch (err) {
    res.status(502).json({ error: String(err.message || err) });
  }
});

app.get('/categories', async (req, res) => {
  try {
    await ensureReady();
    const categories = await api.getCategories();
    res.json({ categories });
  } catch (err) {
    res.status(502).json({ error: String(err.message || err) });
  }
});

app.post('/transactions', async (req, res) => {
  const {
    accountId,
    amount,
    payeeName,
    categoryName,
    date,
    notes,
    direction = 'expense',
  } = req.body || {};

  if (!accountId || amount == null || !date) {
    return res
      .status(400)
      .json({ error: 'accountId, amount and date are required' });
  }

  try {
    await ensureReady();

    // Resolve category name -> id (best effort).
    let categoryId;
    if (categoryName) {
      const cats = await api.getCategories();
      const match = cats.find((c) => c.name === categoryName);
      categoryId = match ? match.id : undefined;
    }

    const importedId = uuidv4();
    const tx = {
      date,
      amount: toMinorUnits(amount, direction),
      payee_name: payeeName || undefined,
      category: categoryId,
      notes: notes || undefined,
      imported_id: importedId,
      cleared: true,
    };

    // importTransactions de-duplicates by imported_id and auto-creates payees.
    const result = await api.importTransactions(accountId, [tx]);
    await api.sync();

    res.status(201).json({
      id: importedId,
      importedId,
      result,
    });
  } catch (err) {
    console.error('[bridge] create transaction failed:', err);
    res.status(502).json({ error: String(err.message || err) });
  }
});

const server = app.listen(PORT, '0.0.0.0', () => {
  console.log(`[bridge] listening on :${PORT}`);
});

async function shutdown() {
  console.log('[bridge] shutting down');
  try {
    if (ready) await api.shutdown();
  } catch (e) {
    /* ignore */
  }
  server.close(() => process.exit(0));
}

process.on('SIGTERM', shutdown);
process.on('SIGINT', shutdown);
