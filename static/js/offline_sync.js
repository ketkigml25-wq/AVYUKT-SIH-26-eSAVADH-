/**
 * eSavadh - Offline Inspection Storage & Auto-Synchronization Engine
 * Made by Team Avyukt
 * 
 * Features:
 * - LocalStorage / IndexedDB offline queue
 * - Idempotency key duplicate prevention
 * - Network status monitoring & auto-sync upon connection recovery
 */

const STORAGE_KEY_QUEUE = "esavadh_offline_inspections_queue";
const STORAGE_KEY_SYNCED = "esavadh_synced_records_cache";

class OfflineSyncManager {
    constructor() {
        this.queue = this.loadQueue();
        this.isOnline = navigator.onLine;
        this.initEventListeners();
        this.updateStatusBadge();
    }

    loadQueue() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY_QUEUE);
            return raw ? JSON.parse(raw) : [];
        } catch (e) {
            console.error("[OfflineSync] Error reading queue:", e);
            return [];
        }
    }

    saveQueue() {
        localStorage.setItem(STORAGE_KEY_QUEUE, JSON.stringify(this.queue));
        this.updateStatusBadge();
    }

    initEventListeners() {
        window.addEventListener("online", () => {
            this.isOnline = true;
            this.updateStatusBadge();
            console.log("[OfflineSync] Connection restored. Initiating automatic sync...");
            this.syncPendingInspections();
        });

        window.addEventListener("offline", () => {
            this.isOnline = false;
            this.updateStatusBadge();
            console.warn("[OfflineSync] Device went OFFLINE. Switched to local storage queue.");
        });
    }

    enqueueInspection(inspectionData) {
        // Generate client-side idempotency sync_id
        const sync_id = "OFFLINE-LOCAL-" + Date.now() + "-" + Math.random().toString(36).substr(2, 6);
        const record = {
            sync_id: sync_id,
            timestamp: new Date().toISOString(),
            data: inspectionData,
            status: "pending_sync"
        };

        this.queue.push(record);
        this.saveQueue();
        console.log(`[OfflineSync] Queued offline inspection dossier (${sync_id}). Total pending: ${this.queue.length}`);
        
        if (this.isOnline) {
            this.syncPendingInspections();
        }
        return sync_id;
    }

    async syncPendingInspections() {
        if (!this.isOnline || this.queue.length === 0) {
            this.updateStatusBadge();
            return;
        }

        const dot = document.getElementById("sync-status-dot");
        const text = document.getElementById("sync-status-text");
        if (dot) dot.className = "sync-dot syncing";
        if (text) text.innerText = `Syncing (${this.queue.length})...`;

        const pendingItems = [...this.queue];
        try {
            const response = await fetch("/api/sync", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ items: pendingItems })
            });

            if (response.ok) {
                const result = await response.json();
                console.log("[OfflineSync] Sync successful. Server processed:", result);
                
                // Clear successfully synced items
                this.queue = [];
                this.saveQueue();
                
                if (text) text.innerText = `Synced (${result.processed_count || 0})`;
                if (dot) dot.className = "sync-dot";
                
                // Show notification banner if inspections were synced
                if (result.processed_count > 0 && window.showToast) {
                    window.showToast(`Successfully synchronized ${result.processed_count} offline field inspection(s).`, "success");
                }
            } else {
                console.error("[OfflineSync] Server error during sync:", response.statusText);
                this.updateStatusBadge();
            }
        } catch (err) {
            console.error("[OfflineSync] Network error during sync retry:", err);
            this.updateStatusBadge();
        }
    }

    updateStatusBadge() {
        const dot = document.getElementById("sync-status-dot");
        const text = document.getElementById("sync-status-text");
        if (!dot || !text) return;

        if (!this.isOnline) {
            dot.className = "sync-dot offline";
            text.innerText = `Offline (${this.queue.length} Pending)`;
        } else {
            if (this.queue.length > 0) {
                dot.className = "sync-dot syncing";
                text.innerText = `${this.queue.length} Pending Sync`;
            } else {
                dot.className = "sync-dot";
                text.innerText = "Online & Synced";
            }
        }
    }
}

// Global instance
window.offlineSync = new OfflineSyncManager();
