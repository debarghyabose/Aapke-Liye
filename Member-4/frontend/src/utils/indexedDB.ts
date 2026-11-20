// src/utils/indexedDB.ts
// Offline IndexedDB queue & local storage for zero-connectivity disaster relief

import { ClaimOut, SealedClaimEnvelope, Household, VaultDocument } from '../types/api';

export type QueueItemType = 'claim_create' | 'text' | 'audio' | 'photo' | 'mesh_relay';

export interface QueueItem {
  id: string;
  type: QueueItemType;
  claimId: string;
  blob?: Blob;
  text?: string;
  payload?: any;
  metadata?: Record<string, any>;
  createdAt: number;
}

const DB_NAME = 'AapkeLiyeOfflineDB';
const DB_VERSION = 2;
const QUEUE_STORE = 'offline_queue';
const CLAIMS_STORE = 'offline_claims';
const MESH_STORE = 'mesh_envelopes';
const VAULT_STORE = 'household_vault';

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    if (typeof window === 'undefined' || !window.indexedDB) {
      reject(new Error('IndexedDB not supported'));
      return;
    }
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = (event) => {
      const db = request.result;
      if (!db.objectStoreNames.contains(QUEUE_STORE)) {
        db.createObjectStore(QUEUE_STORE, { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains(CLAIMS_STORE)) {
        db.createObjectStore(CLAIMS_STORE, { keyPath: 'id' });
      }
      if (!db.objectStoreNames.contains(MESH_STORE)) {
        db.createObjectStore(MESH_STORE, { keyPath: 'claim_id' });
      }
      if (!db.objectStoreNames.contains(VAULT_STORE)) {
        db.createObjectStore(VAULT_STORE, { keyPath: 'id' });
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

// ---------- Offline Queue API ----------

export async function queueOfflineItem(item: Omit<QueueItem, 'id' | 'createdAt'>): Promise<string> {
  const db = await openDB();
  const id = `${item.type}_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
  const fullItem: QueueItem = {
    ...item,
    id,
    createdAt: Date.now(),
  };

  return new Promise((resolve, reject) => {
    const tx = db.transaction(QUEUE_STORE, 'readwrite');
    const store = tx.objectStore(QUEUE_STORE);
    const req = store.add(fullItem);
    req.onsuccess = () => resolve(id);
    req.onerror = () => reject(req.error);
  });
}

export async function getOfflineQueue(): Promise<QueueItem[]> {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(QUEUE_STORE, 'readonly');
      const store = tx.objectStore(QUEUE_STORE);
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  } catch (e) {
    console.warn('Could not read offline queue', e);
    return [];
  }
}

export async function removeQueueItem(id: string): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(QUEUE_STORE, 'readwrite');
    const store = tx.objectStore(QUEUE_STORE);
    const req = store.delete(id);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

export async function clearOfflineQueue(): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(QUEUE_STORE, 'readwrite');
    const store = tx.objectStore(QUEUE_STORE);
    const req = store.clear();
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

export async function updateQueueClaimId(oldId: string, newId: string): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(QUEUE_STORE, 'readwrite');
    const store = tx.objectStore(QUEUE_STORE);
    const req = store.getAll();
    req.onsuccess = () => {
      const items: QueueItem[] = req.result || [];
      items.forEach((item) => {
        if (item.claimId === oldId) {
          item.claimId = newId;
          store.put(item);
        }
      });
      resolve();
    };
    req.onerror = () => reject(req.error);
  });
}

// ---------- Offline Claim Drafts API ----------

export async function saveOfflineClaim(claim: ClaimOut): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(CLAIMS_STORE, 'readwrite');
    const store = tx.objectStore(CLAIMS_STORE);
    const req = store.put(claim);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

export async function getOfflineClaim(id: string): Promise<ClaimOut | null> {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(CLAIMS_STORE, 'readonly');
      const store = tx.objectStore(CLAIMS_STORE);
      const req = store.get(id);
      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => reject(req.error);
    });
  } catch {
    return null;
  }
}

export async function getAllOfflineClaims(): Promise<ClaimOut[]> {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(CLAIMS_STORE, 'readonly');
      const store = tx.objectStore(CLAIMS_STORE);
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  } catch {
    return [];
  }
}

export async function deleteOfflineClaim(id: string): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(CLAIMS_STORE, 'readwrite');
    const store = tx.objectStore(CLAIMS_STORE);
    const req = store.delete(id);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

// ---------- Mesh Relay Store ----------

export async function saveMeshEnvelope(envelope: SealedClaimEnvelope): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(MESH_STORE, 'readwrite');
    const store = tx.objectStore(MESH_STORE);
    const req = store.put(envelope);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

export async function getMeshEnvelopes(): Promise<SealedClaimEnvelope[]> {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(MESH_STORE, 'readonly');
      const store = tx.objectStore(MESH_STORE);
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  } catch {
    return [];
  }
}

export async function removeMeshEnvelope(claimId: string): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(MESH_STORE, 'readwrite');
    const store = tx.objectStore(MESH_STORE);
    const req = store.delete(claimId);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

// ---------- Household Vault Store ----------

export async function saveLocalHousehold(household: Household): Promise<void> {
  const db = await openDB();
  return new Promise((resolve, reject) => {
    const tx = db.transaction(VAULT_STORE, 'readwrite');
    const store = tx.objectStore(VAULT_STORE);
    const req = store.put(household);
    req.onsuccess = () => resolve();
    req.onerror = () => reject(req.error);
  });
}

export async function getLocalHousehold(id: string): Promise<Household | null> {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(VAULT_STORE, 'readonly');
      const store = tx.objectStore(VAULT_STORE);
      const req = store.get(id);
      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => reject(req.error);
    });
  } catch {
    return null;
  }
}

export async function getAllLocalHouseholds(): Promise<Household[]> {
  try {
    const db = await openDB();
    return new Promise((resolve, reject) => {
      const tx = db.transaction(VAULT_STORE, 'readonly');
      const store = tx.objectStore(VAULT_STORE);
      const req = store.getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
    });
  } catch {
    return [];
  }
}
