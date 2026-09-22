/**
 * eSavadh - Main Client Scripting
 * Made by Team Avyukt
 */

// 1. Toast Notification Utility (Available globally immediately)
window.showToast = function(message, type = "info") {
    let container = document.getElementById("toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.style.cssText = "position: fixed; top: 20px; right: 20px; z-index: 99999; max-width: 380px; pointer-events: none;";
        document.body.appendChild(container);
    }
    const toast = document.createElement("div");
    toast.className = `flash-message ${type}`;
    toast.style.cssText = "margin-bottom: 0.5rem; box-shadow: 0 4px 12px rgba(0,0,0,0.25); animation: fadeIn 0.2s ease; pointer-events: auto; padding: 0.75rem 1rem; border-radius: 4px; font-size: 0.85rem; font-weight: 500;";
    toast.innerText = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.remove();
    }, 4500);
};

// 2. Quick Fill Demo Login
window.fillLogin = function(email, password) {
    const emailEl = document.getElementById("email");
    const passEl = document.getElementById("password");
    if (emailEl && passEl) {
        emailEl.value = email;
        passEl.value = password;
        window.showToast(`Selected role credentials for ${email}`, "info");
    }
};

// 3. Tab Navigation
window.switchTab = function(tabId) {
    document.querySelectorAll(".tab-pane").forEach(pane => {
        pane.style.display = "none";
    });
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.classList.remove("active");
    });

    const targetPane = document.getElementById(tabId);
    if (targetPane) {
        targetPane.style.display = "block";
    }
    const targetBtn = document.querySelector(`.tab-btn[data-tab="${tabId}"]`);
    if (targetBtn) {
        targetBtn.classList.add("active");
    }
};

// 4. Human-in-the-loop AJAX Confirm / Deny Handlers
window.handleDeclarationDecision = async function(declId, action, value) {
    try {
        const response = await fetch(`/api/declarations/${declId}/review`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: action, confirmed_value: value })
        });
        const res = await response.json();
        if (res.success) {
            const card = document.getElementById(`declaration-card-${declId}`);
            if (card) {
                card.className = `declaration-card ${action === 'confirm' ? 'confirmed' : 'denied'}`;
                const statusBadge = card.querySelector(".inspector-decision-status");
                if (statusBadge) {
                    statusBadge.innerHTML = action === 'confirm' 
                        ? `<span class="status-badge status-compliant">&#10003; Confirmed: ${value || 'Verified'}</span>`
                        : `<span class="status-badge status-non-compliant">&#10007; Denied by Officer</span>`;
                }
            }
            window.showToast(`Decision recorded: ${action.toUpperCase()}`, "success");
        }
    } catch (e) {
        console.error("Error submitting declaration decision:", e);
        window.showToast("Network error while submitting decision.", "error");
    }
};

// 5. Button Click Helper for HITL Reviews
window.handleDeclClick = function(btn) {
    if (!btn) return;
    const id = btn.getAttribute("data-id");
    const action = btn.getAttribute("data-action");
    const val = btn.getAttribute("data-value") || "";
    if (id) {
        window.handleDeclarationDecision(id, action, val);
    }
};

// 6. DOM Initialization
document.addEventListener("DOMContentLoaded", () => {
    // Add interactive click support for tab buttons
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const tab = btn.getAttribute("data-tab");
            if (tab) window.switchTab(tab);
        });
    });
});
