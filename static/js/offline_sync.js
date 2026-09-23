/**
 * eSavadh - Offline Inspection Storage & Auto-Synchronization Engine
 * Made by Team Avyukt
 * 
 * Features:
 * - IndexedDB & LocalStorage dual-tier offline storage
 * - Client-side UUID/sync_id idempotency to guarantee duplicate-free sync
 * - Online/Offline connectivity monitor with periodic heartbeat
 * - Auto-sync upon reconnection with UI status badge updates
 */

const DB_NAME = "eSavadhOfflineDB";
const DB_VERSION = 1;
const STORE_NAME = "pending_inspections";
const STORAGE_KEY_QUEUE = "esavadh_offline_inspections_queue";

class OfflineSyncManager {
    constructor() {
        this.db = null;
        this.isOnline = navigator.onLine;
        this.isSyncing = false;
        this.initDB().then(() => {
            this.initEventListeners();
            this.updateStatusBadge();
            if (this.isOnline) {
                this.syncPendingInspections();
            }
        });
    }

    initDB() {
        return new Promise((resolve) => {
            if (!window.indexedDB) {
                console.warn("[OfflineSync] IndexedDB not available, falling back to localStorage.");
                resolve(null);
                return;
            }

            const request = indexedDB.open(DB_NAME, DB_VERSION);
            request.onupgradeneeded = (e) => {
                const db = e.target.result;
                if (!db.objectStoreNames.contains(STORE_NAME)) {
                    db.createObjectStore(STORE_NAME, { keyPath: "sync_id" });
                }
            };

            request.onsuccess = (e) => {
                this.db = e.target.result;
                console.log("[OfflineSync] IndexedDB initialized successfully.");
                resolve(this.db);
            };

            request.onerror = (e) => {
                console.warn("[OfflineSync] IndexedDB init error, using localStorage fallback:", e);
                resolve(null);
            };
        });
    }

    async getQueue() {
        if (this.db) {
            return new Promise((resolve) => {
                try {
                    const tx = this.db.transaction(STORE_NAME, "readonly");
                    const store = tx.objectStore(STORE_NAME);
                    const req = store.getAll();
                    req.onsuccess = () => resolve(req.result || []);
                    req.onerror = () => resolve(this.getLocalStorageQueue());
                } catch (e) {
                    resolve(this.getLocalStorageQueue());
                }
            });
        }
        return this.getLocalStorageQueue();
    }

    getLocalStorageQueue() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY_QUEUE);
            return raw ? JSON.parse(raw) : [];
        } catch (e) {
            return [];
        }
    }

    async saveRecord(record) {
        if (this.db) {
            return new Promise((resolve) => {
                try {
                    const tx = this.db.transaction(STORE_NAME, "readwrite");
                    const store = tx.objectStore(STORE_NAME);
                    store.put(record);
                    tx.oncomplete = () => {
                        this.updateStatusBadge();
                        resolve(true);
                    };
                    tx.onerror = () => {
                        this.saveLocalStorageRecord(record);
                        this.updateStatusBadge();
                        resolve(false);
                    };
                } catch (e) {
                    this.saveLocalStorageRecord(record);
                    this.updateStatusBadge();
                    resolve(false);
                }
            });
        }
        this.saveLocalStorageRecord(record);
        this.updateStatusBadge();
    }

    saveLocalStorageRecord(record) {
        const queue = this.getLocalStorageQueue().filter(r => r.sync_id !== record.sync_id);
        queue.push(record);
        localStorage.setItem(STORAGE_KEY_QUEUE, JSON.stringify(queue));
    }

    async removeRecord(sync_id) {
        if (this.db) {
            try {
                const tx = this.db.transaction(STORE_NAME, "readwrite");
                const store = tx.objectStore(STORE_NAME);
                store.delete(sync_id);
            } catch (e) {}
        }
        const queue = this.getLocalStorageQueue().filter(r => r.sync_id !== sync_id);
        localStorage.setItem(STORAGE_KEY_QUEUE, JSON.stringify(queue));
        this.updateStatusBadge();
    }

    initEventListeners() {
        window.addEventListener("online", () => {
            this.isOnline = true;
            this.updateStatusBadge();
            console.log("[OfflineSync] Online event detected. Triggering auto-sync...");
            this.syncPendingInspections();
        });

        window.addEventListener("offline", () => {
            this.isOnline = false;
            this.updateStatusBadge();
            console.warn("[OfflineSync] Device went OFFLINE. Switched to local offline mode.");
        });

        // Periodic connectivity heartbeat every 20 seconds
        setInterval(() => {
            this.checkConnectivity();
        }, 20000);
    }

    async checkConnectivity() {
        if (!navigator.onLine) {
            if (this.isOnline) {
                this.isOnline = false;
                this.updateStatusBadge();
            }
            return;
        }

        try {
            const res = await fetch("/static/manifest.json?_hb=" + Date.now(), { method: "HEAD", cache: "no-store" });
            const onlineNow = res.ok;
            if (onlineNow !== this.isOnline) {
                this.isOnline = onlineNow;
                this.updateStatusBadge();
                if (this.isOnline) this.syncPendingInspections();
            }
        } catch (e) {
            if (this.isOnline) {
                this.isOnline = false;
                this.updateStatusBadge();
            }
        }
    }

    async enqueueInspection(formData) {
        const sync_id = "OFFLINE-" + Date.now() + "-" + Math.random().toString(36).substr(2, 7).toUpperCase();
        const record = {
            sync_id: sync_id,
            timestamp: new Date().toISOString(),
            data: formData,
            status: "PENDING_SYNC"
        };

        await this.saveRecord(record);
        console.log(`[OfflineSync] Enqueued offline dossier (${sync_id}) with status PENDING_SYNC.`);
        
        if (this.isOnline) {
            this.syncPendingInspections();
        }
        return sync_id;
    }

    async syncPendingInspections() {
        if (this.isSyncing || !this.isOnline) return;

        const queue = await this.getQueue();
        if (!queue || queue.length === 0) {
            this.updateStatusBadge();
            return;
        }

        this.isSyncing = true;
        const dot = document.getElementById("sync-status-dot");
        const text = document.getElementById("sync-status-text");
        if (dot) dot.className = "sync-dot syncing";
        if (text) text.innerText = `Syncing (${queue.length})...`;

        try {
            const response = await fetch("/api/sync", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ items: queue })
            });

            if (response.ok) {
                const result = await response.json();
                console.log("[OfflineSync] Sync confirmation received from server:", result);

                // Remove successfully processed items from queue
                for (const item of queue) {
                    await this.removeRecord(item.sync_id);
                }

                if (dot) dot.className = "sync-dot";
                if (text) text.innerText = `Synced \u2713 (${result.processed_count || queue.length})`;

                if (window.showToast) {
                    window.showToast(`Auto-sync completed: ${result.processed_count || queue.length} offline inspection(s) synchronized.`, "success");
                }
            } else {
                console.warn("[OfflineSync] Server sync responded with non-200:", response.status);
            }
        } catch (err) {
            console.warn("[OfflineSync] Network error during background sync, will retry later:", err);
        } finally {
            this.isSyncing = false;
            this.updateStatusBadge();
        }
    }

    async updateStatusBadge() {
        const dot = document.getElementById("sync-status-dot");
        const text = document.getElementById("sync-status-text");
        if (!dot || !text) return;

        const queue = await this.getQueue();
        const pendingCount = queue.length;

        if (!this.isOnline) {
            dot.className = "sync-dot offline";
            text.innerText = pendingCount > 0 ? `Offline (${pendingCount} Pending Sync)` : "Offline Mode";
        } else {
            if (this.isSyncing) {
                dot.className = "sync-dot syncing";
                text.innerText = `Syncing (${pendingCount})...`;
            } else if (pendingCount > 0) {
                dot.className = "sync-dot syncing";
                text.innerText = `${pendingCount} Pending Sync`;
            } else {
                dot.className = "sync-dot";
                text.innerText = "Online & Synced";
            }
        }
    }
}

// Global initialization
window.offlineSync = new OfflineSyncManager();
