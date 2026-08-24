// Last-Mile Delivery Tracker - Frontend Application Engine

let currentUser = null;
let authToken = localStorage.getItem("token") || "";
let calcTimeout = null;
let activeAdminSubtab = "zones";
let allZonesCache = [];
let allAgentsCache = [];

// Initialize Application
document.addEventListener("DOMContentLoaded", () => {
    if (authToken) {
        fetchCurrentUser();
    } else {
        // Auto demo login as Customer by default for smooth experience
        quickLogin("customer@example.com", "Customer@123");
    }
    loadZones();
});

// Toast Notification Handler
function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    const bg = type === "error" ? "bg-rose-600" : type === "success" ? "bg-emerald-600" : "bg-blue-600";
    toast.className = `toast text-white px-4 py-3 rounded-xl shadow-xl flex items-center justify-between gap-3 text-sm font-medium ${bg}`;
    toast.innerHTML = `
        <span>${message}</span>
        <button onclick="this.parentElement.remove()" class="text-white/80 hover:text-white font-bold">&times;</button>
    `;
    container.appendChild(toast);
    setTimeout(() => {
        if (toast.parentElement) toast.remove();
    }, 4500);
}

// Authentication & Demo Login
async function quickLogin(email, password) {
    try {
        const res = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Login failed");

        authToken = data.access_token;
        localStorage.setItem("token", authToken);
        currentUser = data.user;
        updateUserUI();
        showToast(`Logged in as ${currentUser.name} (${currentUser.role})`, "success");
        loadOrders();
        loadAgents();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function fetchCurrentUser() {
    try {
        const res = await fetch("/api/auth/me", {
            headers: { "Authorization": `Bearer ${authToken}` }
        });
        if (!res.ok) throw new Error("Session expired");
        currentUser = await res.json();
        updateUserUI();
        loadOrders();
        loadAgents();
    } catch (err) {
        logout();
    }
}

function logout() {
    authToken = "";
    currentUser = null;
    localStorage.removeItem("token");
    updateUserUI();
    showToast("Logged out successfully", "info");
    quickLogin("customer@example.com", "Customer@123");
}

function updateUserUI() {
    const userInfo = document.getElementById("userInfo");
    const logoutBtn = document.getElementById("logoutBtn");
    const adminCustomerSelectGroup = document.getElementById("adminCustomerSelectGroup");

    if (currentUser) {
        const roleColors = {
            "ADMIN": "bg-amber-500 text-slate-950",
            "CUSTOMER": "bg-blue-500 text-white",
            "AGENT": "bg-emerald-500 text-white"
        };
        userInfo.innerHTML = `
            <span class="font-semibold">${currentUser.name}</span>
            <span class="px-2 py-0.5 rounded text-xs font-extrabold ${roleColors[currentUser.role] || 'bg-slate-700'} ml-1.5">${currentUser.role}</span>
        `;
        logoutBtn.classList.remove("hidden");

        // Show Admin specific UI tabs
        const adminTabBtns = document.querySelectorAll(".admin-only");
        adminTabBtns.forEach(btn => {
            if (currentUser.role === "ADMIN") btn.classList.remove("hidden");
            else btn.classList.add("hidden");
        });

        // Show Agent self controls
        const agentSelfControls = document.getElementById("agentSelfControls");
        if (currentUser.role === "AGENT" && agentSelfControls) {
            agentSelfControls.classList.remove("hidden");
        } else if (agentSelfControls) {
            agentSelfControls.classList.add("hidden");
        }

        if (currentUser.role === "ADMIN" && adminCustomerSelectGroup) {
            adminCustomerSelectGroup.classList.remove("hidden");
            loadCustomersForAdmin();
        } else if (adminCustomerSelectGroup) {
            adminCustomerSelectGroup.classList.add("hidden");
        }
    } else {
        userInfo.textContent = "Not Logged In";
        logoutBtn.classList.add("hidden");
    }
}

async function loadCustomersForAdmin() {
    // Demo populate customer select
    const select = document.getElementById("orderCustomerSelect");
    if (!select) return;
    select.innerHTML = `
        <option value="2">Rahul Sharma (customer@example.com)</option>
        <option value="3">Acme Enterprise Corp (acme@corp.com)</option>
    `;
}

// Navigation Tabs
function switchTab(tabId) {
    document.querySelectorAll(".tab-btn").forEach(btn => {
        btn.classList.remove("active", "border-blue-600", "text-blue-600");
        btn.classList.add("border-transparent", "text-slate-600");
    });
    document.querySelectorAll(".tab-content").forEach(c => c.classList.add("hidden"));

    const activeBtn = document.getElementById(`tab-${tabId}`);
    const activeContent = document.getElementById(`content-${tabId}`);
    if (activeBtn && activeContent) {
        activeBtn.classList.add("active", "border-blue-600", "text-blue-600");
        activeBtn.classList.remove("border-transparent", "text-slate-600");
        activeContent.classList.remove("hidden");
    }

    if (tabId === "orders") loadOrders();
    if (tabId === "agents") loadAgents();
    if (tabId === "admin") loadAdminData();
    if (tabId === "create") calculateRate();
}

// Dynamic Rate Engine Calculator
function debounceCalculateRate() {
    clearTimeout(calcTimeout);
    calcTimeout = setTimeout(calculateRate, 300);
}

async function calculateRate() {
    const pickupPincode = document.getElementById("pickupPincode")?.value.trim() || "110001";
    const pickupAddress = document.getElementById("pickupAddress")?.value.trim() || "";
    const dropPincode = document.getElementById("dropPincode")?.value.trim() || "110016";
    const dropAddress = document.getElementById("dropAddress")?.value.trim() || "";
    const lengthCm = parseFloat(document.getElementById("lengthCm")?.value) || 30;
    const widthCm = parseFloat(document.getElementById("widthCm")?.value) || 20;
    const heightCm = parseFloat(document.getElementById("heightCm")?.value) || 15;
    const actualWeightKg = parseFloat(document.getElementById("actualWeightKg")?.value) || 1.5;
    const orderType = document.getElementById("orderType")?.value || "B2C";
    const paymentType = document.getElementById("paymentType")?.value || "PREPAID";

    try {
        const res = await fetch("/api/rates/calculate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                pickup_pincode: pickupPincode,
                pickup_address: pickupAddress,
                drop_pincode: dropPincode,
                drop_address: dropAddress,
                length_cm: lengthCm,
                width_cm: widthCm,
                height_cm: heightCm,
                actual_weight_kg: actualWeightKg,
                order_type: orderType,
                payment_type: paymentType
            })
        });

        if (!res.ok) return;
        const data = await res.json();

        // Update Price Breakdown UI Card
        document.getElementById("volWeightVal").textContent = `${data.volumetric_weight_kg.toFixed(2)} kg`;
        document.getElementById("actWeightVal").textContent = `${data.actual_weight_kg.toFixed(2)} kg`;
        document.getElementById("billWeightVal").textContent = `${data.billable_weight_kg.toFixed(2)} kg`;
        document.getElementById("pickupZoneVal").textContent = data.pickup_zone_name;
        document.getElementById("dropZoneVal").textContent = data.drop_zone_name;
        document.getElementById("routeBadge").textContent = `${data.route_type}-ZONE (${data.order_type})`;
        document.getElementById("baseChargeVal").textContent = `₹${data.base_charge.toFixed(2)}`;
        document.getElementById("weightChargeVal").textContent = `₹${data.weight_charge.toFixed(2)}`;
        document.getElementById("codChargeVal").textContent = `₹${data.cod_surcharge.toFixed(2)}`;
        document.getElementById("totalChargeVal").textContent = `₹${data.total_charge.toFixed(2)}`;
    } catch (err) {
        console.error("Rate calculation error:", err);
    }
}

// Order Creation Handler
async function handleCreateOrder(event) {
    event.preventDefault();
    if (!currentUser) return showToast("Please log in first.", "error");

    const pickupAddress = document.getElementById("pickupAddress").value.trim();
    const pickupPincode = document.getElementById("pickupPincode").value.trim();
    const dropAddress = document.getElementById("dropAddress").value.trim();
    const dropPincode = document.getElementById("dropPincode").value.trim();
    const lengthCm = parseFloat(document.getElementById("lengthCm").value);
    const widthCm = parseFloat(document.getElementById("widthCm").value);
    const heightCm = parseFloat(document.getElementById("heightCm").value);
    const actualWeightKg = parseFloat(document.getElementById("actualWeightKg").value);
    const orderType = document.getElementById("orderType").value;
    const paymentType = document.getElementById("paymentType").value;

    let customerId = null;
    if (currentUser.role === "ADMIN") {
        const custSelect = document.getElementById("orderCustomerSelect");
        if (custSelect) customerId = parseInt(custSelect.value);
    }

    try {
        const res = await fetch("/api/orders", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${authToken}`
            },
            body: JSON.stringify({
                pickup_address: pickupAddress,
                pickup_pincode: pickupPincode,
                drop_address: dropAddress,
                drop_pincode: dropPincode,
                length_cm: lengthCm,
                width_cm: widthCm,
                height_cm: heightCm,
                actual_weight_kg: actualWeightKg,
                order_type: orderType,
                payment_type: paymentType,
                customer_id: customerId
            })
        });

        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Order creation failed");

        let msg = `Order ${data.tracking_number} created successfully! Total: ₹${data.total_charge.toFixed(2)}.`;
        if (data.agent_name) {
            msg += ` Auto-assigned to Agent ${data.agent_name}.`;
        } else {
            msg += ` Pending Agent Assignment.`;
        }

        showToast(msg, "success");
        switchTab("orders");
    } catch (err) {
        showToast(err.message, "error");
    }
}

// Load Orders List
async function loadOrders() {
    if (!currentUser) return;

    const search = document.getElementById("filterSearch")?.value || "";
    const status = document.getElementById("filterStatus")?.value || "";
    const zoneId = document.getElementById("filterZone")?.value || "";

    let url = `/api/orders?`;
    if (search) url += `search=${encodeURIComponent(search)}&`;
    if (status) url += `status=${encodeURIComponent(status)}&`;
    if (zoneId) url += `zone_id=${encodeURIComponent(zoneId)}&`;

    try {
        const res = await fetch(url, {
            headers: { "Authorization": `Bearer ${authToken}` }
        });
        const orders = await res.json();
        const tbody = document.getElementById("ordersTableBody");
        if (!tbody) return;

        if (!orders || orders.length === 0) {
            tbody.innerHTML = `<tr><td colspan="8" class="p-8 text-center text-slate-400">No orders found matching criteria.</td></tr>`;
            return;
        }

        tbody.innerHTML = orders.map(order => {
            const statusClass = `status-${order.status}`;
            const isAgent = currentUser.role === "AGENT";
            const isAdmin = currentUser.role === "ADMIN";
            const isCustomer = currentUser.role === "CUSTOMER";

            let actionBtns = `
                <button onclick="openTimelineModal('${order.id}')" class="px-2.5 py-1 text-xs bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold rounded-lg transition" title="View Progress Timeline">
                    📍 Track
                </button>
            `;

            if (isCustomer && order.status === "FAILED") {
                actionBtns += `
                    <button onclick="openRescheduleModal('${order.id}')" class="px-2.5 py-1 text-xs bg-rose-600 hover:bg-rose-700 text-white font-bold rounded-lg shadow transition">
                        🗓️ Reschedule
                    </button>
                `;
            }

            if ((isAgent && order.agent_id === currentUser.id) || isAdmin) {
                actionBtns += `
                    <button onclick="openStatusModal('${order.id}')" class="px-2.5 py-1 text-xs bg-blue-600 hover:bg-blue-700 text-white font-bold rounded-lg transition">
                        ✏️ Update Status
                    </button>
                `;
            }

            if (isAdmin) {
                actionBtns += `
                    <button onclick="openAssignModal('${order.id}')" class="px-2.5 py-1 text-xs bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg transition" title="Assign Agent">
                        👤 Assign
                    </button>
                    <button onclick="openOverrideModal('${order.id}')" class="px-2.5 py-1 text-xs bg-amber-500 hover:bg-amber-600 text-slate-950 font-bold rounded-lg transition" title="Admin Override">
                        ⚡ Override
                    </button>
                `;
            }

            return `
                <tr class="hover:bg-slate-50 transition border-b border-slate-100">
                    <td class="p-3.5 font-bold font-mono text-blue-600">${order.tracking_number}</td>
                    <td class="p-3.5">
                        <div class="font-semibold text-slate-800">${order.order_type}</div>
                        <div class="text-xs text-slate-400">${order.payment_type}</div>
                    </td>
                    <td class="p-3.5 text-xs max-w-[200px]">
                        <div class="truncate font-medium text-slate-700" title="${order.pickup_address}">📍 ${order.pickup_address}</div>
                        <div class="truncate text-slate-400" title="${order.drop_address}">🏁 ${order.drop_address}</div>
                    </td>
                    <td class="p-3.5 font-mono text-xs">${order.billable_weight_kg.toFixed(2)} kg</td>
                    <td class="p-3.5 font-bold font-mono text-emerald-600">₹${order.total_charge.toFixed(2)}</td>
                    <td class="p-3.5 text-xs">
                        ${order.agent_name ? `<span class="font-semibold text-slate-700">🛵 ${order.agent_name}</span>` : `<span class="text-amber-600 italic">Unassigned</span>`}
                    </td>
                    <td class="p-3.5">
                        <span class="status-badge ${statusClass}">${order.status}</span>
                    </td>
                    <td class="p-3.5 text-right space-x-1 whitespace-nowrap">
                        ${actionBtns}
                    </td>
                </tr>
            `;
        }).join("");
    } catch (err) {
        console.error("Error loading orders:", err);
    }
}

// Timeline Modal & Step Progress Bar
async function openTimelineModal(orderId) {
    try {
        const res = await fetch(`/api/orders/${orderId}`, {
            headers: { "Authorization": `Bearer ${authToken}` }
        });
        const order = await res.json();

        document.getElementById("modalTrackingTitle").textContent = `Order ${order.tracking_number}`;
        document.getElementById("modalTrackingSub").textContent = `Customer: ${order.customer_name} | Pickup Zone: ${order.pickup_zone_name || 'N/A'}`;

        // Render Step Bar
        const stages = ["CREATED", "ASSIGNED", "PICKED_UP", "IN_TRANSIT", "OUT_FOR_DELIVERY", "DELIVERED"];
        const currentIdx = stages.indexOf(order.status);
        const isFailed = order.status === "FAILED";

        const progressContainer = document.getElementById("progressStepBar");
        progressContainer.innerHTML = stages.map((st, i) => {
            let stateClass = "upcoming";
            let icon = i + 1;
            if (isFailed && i === 4) { // OUT_FOR_DELIVERY -> FAILED
                stateClass = "failed";
                icon = "❌";
            } else if (order.status === "DELIVERED" || i < currentIdx) {
                stateClass = "completed";
                icon = "✓";
            } else if (i === currentIdx) {
                stateClass = "active";
            }

            return `
                <div class="flex flex-col items-center z-10">
                    <div class="step-dot ${stateClass}">${icon}</div>
                    <span class="text-[10px] font-bold mt-1 text-slate-600 tracking-tighter uppercase">${st.replace('_', ' ')}</span>
                </div>
            `;
        }).join("");

        // Show Reschedule Box if FAILED
        const resBox = document.getElementById("rescheduleAlertBox");
        if (isFailed) {
            resBox.classList.remove("hidden");
            document.getElementById("modalFailureReason").textContent = order.failure_reason || "Delivery attempt failed.";
            document.getElementById("rescheduleBtnModal").onclick = () => {
                closeModal("timelineModal");
                openRescheduleModal(order.id);
            };
        } else {
            resBox.classList.add("hidden");
        }

        // Immutable History Log Table
        const historyBody = document.getElementById("modalHistoryBody");
        historyBody.innerHTML = order.history.map(h => `
            <tr class="hover:bg-slate-50 border-b border-slate-100">
                <td class="p-2.5 text-slate-400 font-mono text-[11px]">${new Date(h.timestamp).toLocaleString()}</td>
                <td class="p-2.5 font-bold">${h.status}</td>
                <td class="p-2.5 text-slate-700">${h.actor_name} <span class="text-[10px] text-slate-400">(${h.actor_role})</span></td>
                <td class="p-2.5 text-slate-600 italic">${h.notes || '-'}</td>
            </tr>
        `).join("");

        document.getElementById("timelineModal").classList.remove("hidden");
    } catch (err) {
        showToast("Failed to load timeline details", "error");
    }
}

// Reschedule Modal
function openRescheduleModal(orderId) {
    document.getElementById("rescheduleOrderId").value = orderId;
    const tomorrow = new Date();
    tomorrow.setDate(tomorrow.getDate() + 1);
    document.getElementById("rescheduleDate").value = tomorrow.toISOString().split('T')[0];
    document.getElementById("rescheduleModal").classList.remove("hidden");
}

async function handleConfirmReschedule(event) {
    event.preventDefault();
    const orderId = document.getElementById("rescheduleOrderId").value;
    const date = document.getElementById("rescheduleDate").value;
    const notes = document.getElementById("rescheduleNotes").value;

    try {
        const res = await fetch(`/api/orders/${orderId}/reschedule`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${authToken}`
            },
            body: JSON.stringify({ rescheduled_date: date, notes: notes })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Reschedule failed");

        showToast(`Order rescheduled for ${date}! Agent reassigned automatically.`, "success");
        closeModal("rescheduleModal");
        loadOrders();
    } catch (err) {
        showToast(err.message, "error");
    }
}

// Agent Status Update Modal
function openStatusModal(orderId) {
    document.getElementById("updateStatusOrderId").value = orderId;
    document.getElementById("statusModal").classList.remove("hidden");
    toggleFailureReasonInput();
}

function toggleFailureReasonInput() {
    const st = document.getElementById("updateStatusSelect").value;
    const grp = document.getElementById("failureReasonGroup");
    if (st === "FAILED") grp.classList.remove("hidden");
    else grp.classList.add("hidden");
}

async function handleConfirmStatusUpdate(event) {
    event.preventDefault();
    const orderId = document.getElementById("updateStatusOrderId").value;
    const status = document.getElementById("updateStatusSelect").value;
    const failureReason = document.getElementById("updateFailureReason").value;
    const notes = document.getElementById("updateStatusNotes").value;

    try {
        const res = await fetch(`/api/orders/${orderId}/status`, {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${authToken}`
            },
            body: JSON.stringify({
                status: status,
                failure_reason: failureReason,
                notes: notes
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Status update failed");

        showToast(`Order status updated to ${data.status}`, "success");
        closeModal("statusModal");
        loadOrders();
    } catch (err) {
        showToast(err.message, "error");
    }
}

// Admin Assign Modal
async function openAssignModal(orderId) {
    document.getElementById("assignOrderId").value = orderId;
    const select = document.getElementById("agentSelectModal");

    try {
        const res = await fetch("/api/agents", {
            headers: { "Authorization": `Bearer ${authToken}` }
        });
        const agents = await res.json();
        select.innerHTML = agents.map(a => `
            <option value="${a.user_id}">${a.user_name} (${a.status} - Workload: ${a.current_workload})</option>
        `).join("");

        document.getElementById("assignAgentModal").classList.remove("hidden");
    } catch (err) {
        showToast("Failed to load agent list", "error");
    }
}

async function handleConfirmAssignAgent(event) {
    event.preventDefault();
    const orderId = document.getElementById("assignOrderId").value;
    const agentId = document.getElementById("agentSelectModal").value;

    try {
        const res = await fetch(`/api/agents/assign-manual/${orderId}`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${authToken}`
            },
            body: JSON.stringify({ agent_id: parseInt(agentId) })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Assignment failed");

        showToast(data.message, "success");
        closeModal("assignAgentModal");
        loadOrders();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function triggerAutoAssignModal() {
    const orderId = document.getElementById("assignOrderId").value;
    try {
        const res = await fetch(`/api/agents/auto-assign/${orderId}`, {
            method: "POST",
            headers: { "Authorization": `Bearer ${authToken}` }
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Auto assignment failed");

        showToast(data.message, "success");
        closeModal("assignAgentModal");
        loadOrders();
    } catch (err) {
        showToast(err.message, "error");
    }
}

// Admin Override Modal
function openOverrideModal(orderId) {
    document.getElementById("overrideOrderId").value = orderId;
    document.getElementById("overrideModal").classList.remove("hidden");
}

async function handleConfirmOverride(event) {
    event.preventDefault();
    const orderId = document.getElementById("overrideOrderId").value;
    const newStatus = document.getElementById("overrideStatusSelect").value;
    const notes = document.getElementById("overrideNotes").value;

    try {
        const res = await fetch(`/api/orders/${orderId}/override?new_status=${encodeURIComponent(newStatus)}&notes=${encodeURIComponent(notes)}`, {
            method: "PUT",
            headers: { "Authorization": `Bearer ${authToken}` }
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Override failed");

        showToast(`Status overridden to ${data.status} by Admin`, "success");
        closeModal("overrideModal");
        loadOrders();
    } catch (err) {
        showToast(err.message, "error");
    }
}

// Delivery Agents Hub
async function loadAgents() {
    try {
        const res = await fetch("/api/agents", {
            headers: { "Authorization": `Bearer ${authToken}` }
        });
        if (!res.ok) return;
        const agents = await res.json();
        allAgentsCache = agents;
        const grid = document.getElementById("agentsGrid");
        if (!grid) return;

        grid.innerHTML = agents.map(a => `
            <div class="bg-slate-50 border border-slate-200 p-4 rounded-xl flex flex-col justify-between">
                <div>
                    <div class="flex justify-between items-start mb-2">
                        <h4 class="font-bold text-slate-800 text-sm">🛵 ${a.user_name}</h4>
                        <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase ${a.status === 'AVAILABLE' ? 'bg-emerald-100 text-emerald-800' : a.status === 'ON_DELIVERY' ? 'bg-blue-100 text-blue-800' : 'bg-slate-200 text-slate-700'}">${a.status}</span>
                    </div>
                    <p class="text-xs text-slate-500 font-mono">${a.user_email} | ${a.user_phone || 'No phone'}</p>
                    <p class="text-xs text-slate-600 mt-2 font-medium">Active Zone: <span class="text-blue-600 font-bold">${a.active_zone_name || 'All Zones'}</span></p>
                </div>
                <div class="mt-4 pt-3 border-t border-slate-200 flex justify-between items-center text-xs">
                    <span class="text-slate-500 font-semibold">Active Workload: <span class="font-bold text-slate-900">${a.current_workload} orders</span></span>
                    <span class="text-slate-400 font-mono text-[10px]">(${a.current_lat.toFixed(4)}, ${a.current_lng.toFixed(4)})</span>
                </div>
            </div>
        `).join("");
    } catch (err) {
        console.error("Error loading agents:", err);
    }
}

async function updateMyAgentStatus() {
    const st = document.getElementById("agentMyStatus").value;
    try {
        const res = await fetch("/api/agents/me", {
            method: "PUT",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${authToken}`
            },
            body: JSON.stringify({ status: st })
        });
        if (!res.ok) throw new Error("Failed to update status");
        showToast(`Agent availability set to ${st}`, "success");
        loadAgents();
    } catch (err) {
        showToast(err.message, "error");
    }
}

// Admin Configuration Center
async function loadAdminData() {
    loadZones();
    loadRateCards();
    loadCODSurcharges();
    loadNotificationLogs();
}

function switchAdminSubTab(subtab) {
    activeAdminSubtab = subtab;
    document.querySelectorAll(".admin-subtab").forEach(btn => {
        btn.classList.remove("bg-blue-600", "text-white", "font-bold");
        btn.classList.add("text-slate-600", "font-medium");
    });
    document.querySelectorAll(".admin-subcontent").forEach(c => c.classList.add("hidden"));

    const btn = document.getElementById(`subtab-${subtab}`);
    const content = document.getElementById(`admin-subcontent-${subtab}`);
    if (btn && content) {
        btn.classList.add("bg-blue-600", "text-white", "font-bold");
        btn.classList.remove("text-slate-600", "font-medium");
        content.classList.remove("hidden");
    }
}

async function loadZones() {
    try {
        const res = await fetch("/api/zones");
        const zones = await res.json();
        allZonesCache = zones;

        // Populate Zone Filter Select
        const filterZone = document.getElementById("filterZone");
        if (filterZone) {
            filterZone.innerHTML = `<option value="">All Zones</option>` + zones.map(z => `
                <option value="${z.id}">${z.name} (${z.code})</option>
            `).join("");
        }

        // Populate Zones List Container in Admin
        const container = document.getElementById("zonesListContainer");
        if (!container) return;

        container.innerHTML = zones.map(z => `
            <div class="bg-white p-5 rounded-xl border border-slate-200 shadow-sm">
                <div class="flex justify-between items-center border-b pb-3 mb-3">
                    <div>
                        <h4 class="font-bold text-slate-900">${z.name} <span class="text-xs font-mono text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-200">${z.code}</span></h4>
                        <p class="text-xs text-slate-500">${z.description || 'No description'}</p>
                    </div>
                </div>
                <div>
                    <h5 class="text-xs font-bold uppercase text-slate-500 mb-2">Mapped Areas & Pincodes (${z.areas.length})</h5>
                    <div class="flex flex-wrap gap-2 mb-3">
                        ${z.areas.map(a => `
                            <span class="bg-slate-100 text-slate-800 px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center gap-1 border">
                                ${a.area_name} (${a.pincode})
                                <button onclick="removeAreaMapping('${a.id}')" class="text-slate-400 hover:text-rose-600 font-bold ml-1">&times;</button>
                            </span>
                        `).join("") || `<span class="text-xs text-slate-400 italic">No areas mapped yet.</span>`}
                    </div>
                    <form onsubmit="handleAddAreaToZone(event, '${z.id}')" class="flex gap-2">
                        <input type="text" placeholder="Area Name" required class="p-1.5 text-xs border rounded-lg flex-1">
                        <input type="text" placeholder="Pincode" required class="p-1.5 text-xs border rounded-lg w-28">
                        <button type="submit" class="bg-slate-900 text-white font-bold text-xs px-3 py-1.5 rounded-lg hover:bg-slate-800">Add Area</button>
                    </form>
                </div>
            </div>
        `).join("");
    } catch (err) {
        console.error("Error loading zones:", err);
    }
}

async function handleCreateZone(event) {
    event.preventDefault();
    const name = document.getElementById("newZoneName").value.trim();
    const code = document.getElementById("newZoneCode").value.trim();

    try {
        const res = await fetch("/api/zones", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${authToken}`
            },
            body: JSON.stringify({ name, code })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Zone creation failed");

        showToast(`Zone '${name}' created successfully`, "success");
        loadZones();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function handleAddAreaToZone(event, zoneId) {
    event.preventDefault();
    const inputs = event.target.querySelectorAll("input");
    const areaName = inputs[0].value.trim();
    const pincode = inputs[1].value.trim();

    try {
        const res = await fetch(`/api/zones/${zoneId}/areas`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${authToken}`
            },
            body: JSON.stringify({ area_name: areaName, pincode: pincode })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.detail || "Area mapping failed");

        showToast(`Area '${areaName}' mapped to zone`, "success");
        loadZones();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function removeAreaMapping(areaId) {
    try {
        const res = await fetch(`/api/zones/areas/${areaId}`, {
            method: "DELETE",
            headers: { "Authorization": `Bearer ${authToken}` }
        });
        if (!res.ok) throw new Error("Failed to delete area mapping");
        showToast("Area mapping removed", "info");
        loadZones();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function loadRateCards() {
    try {
        const res = await fetch("/api/rates/cards");
        const cards = await res.json();
        const container = document.getElementById("rateCardsContainer");
        if (!container) return;

        container.innerHTML = cards.map(c => `
            <div class="bg-slate-50 border border-slate-200 p-4 rounded-xl">
                <div class="flex justify-between items-center mb-3">
                    <span class="font-bold text-sm text-slate-800">${c.order_type} (${c.route_type}-ZONE)</span>
                    <span class="text-xs bg-blue-100 text-blue-800 font-bold px-2 py-0.5 rounded">Active</span>
                </div>
                <form onsubmit="handleSaveRateCard(event, '${c.order_type}', '${c.route_type}')" class="space-y-2 text-xs">
                    <div class="flex justify-between items-center">
                        <span class="text-slate-600">Base Rate (₹):</span>
                        <input type="number" step="0.5" value="${c.base_rate}" required class="w-24 p-1 border rounded text-right font-mono">
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-slate-600">Per Kg Rate (₹):</span>
                        <input type="number" step="0.5" value="${c.per_kg_rate}" required class="w-24 p-1 border rounded text-right font-mono">
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-slate-600">Min Charge (₹):</span>
                        <input type="number" step="0.5" value="${c.min_charge}" required class="w-24 p-1 border rounded text-right font-mono">
                    </div>
                    <button type="submit" class="w-full mt-2 py-1.5 bg-blue-600 hover:bg-blue-700 text-white font-bold rounded transition">
                        Update Rate Card
                    </button>
                </form>
            </div>
        `).join("");
    } catch (err) {
        console.error("Error loading rate cards:", err);
    }
}

async function handleSaveRateCard(event, orderType, routeType) {
    event.preventDefault();
    const inputs = event.target.querySelectorAll("input");
    const baseRate = parseFloat(inputs[0].value);
    const perKgRate = parseFloat(inputs[1].value);
    const minCharge = parseFloat(inputs[2].value);

    try {
        const res = await fetch("/api/rates/cards", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${authToken}`
            },
            body: JSON.stringify({
                order_type: orderType,
                route_type: routeType,
                base_rate: baseRate,
                per_kg_rate: perKgRate,
                min_charge: minCharge
            })
        });
        if (!res.ok) throw new Error("Failed to update rate card");
        showToast(`Rate Card for ${orderType} ${routeType} updated!`, "success");
        loadRateCards();
        calculateRate();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function loadCODSurcharges() {
    try {
        const res = await fetch("/api/rates/cod");
        const cods = await res.json();
        const container = document.getElementById("codContainer");
        if (!container) return;

        container.innerHTML = cods.map(c => `
            <div class="bg-slate-50 border border-slate-200 p-4 rounded-xl">
                <h4 class="font-bold text-sm text-slate-800 mb-3">${c.order_type} COD Surcharge Rules</h4>
                <form onsubmit="handleSaveCOD(event, '${c.order_type}')" class="space-y-2 text-xs">
                    <div class="flex justify-between items-center">
                        <span class="text-slate-600">Fixed Fee (₹):</span>
                        <input type="number" step="0.5" value="${c.fixed_fee}" required class="w-24 p-1 border rounded text-right font-mono">
                    </div>
                    <div class="flex justify-between items-center">
                        <span class="text-slate-600">Percentage Surcharge (%):</span>
                        <input type="number" step="0.1" value="${c.percentage_fee}" required class="w-24 p-1 border rounded text-right font-mono">
                    </div>
                    <button type="submit" class="w-full mt-2 py-1.5 bg-amber-600 hover:bg-amber-700 text-white font-bold rounded transition">
                        Update COD Surcharge
                    </button>
                </form>
            </div>
        `).join("");
    } catch (err) {
        console.error("Error loading COD surcharges:", err);
    }
}

async function handleSaveCOD(event, orderType) {
    event.preventDefault();
    const inputs = event.target.querySelectorAll("input");
    const fixedFee = parseFloat(inputs[0].value);
    const percentageFee = parseFloat(inputs[1].value);

    try {
        const res = await fetch("/api/rates/cod", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${authToken}`
            },
            body: JSON.stringify({
                order_type: orderType,
                fixed_fee: fixedFee,
                percentage_fee: percentageFee
            })
        });
        if (!res.ok) throw new Error("Failed to update COD surcharge");
        showToast(`COD Surcharge for ${orderType} updated!`, "success");
        loadCODSurcharges();
        calculateRate();
    } catch (err) {
        showToast(err.message, "error");
    }
}

async function loadNotificationLogs() {
    try {
        const res = await fetch("/api/orders/notifications/logs", {
            headers: { "Authorization": `Bearer ${authToken}` }
        });
        if (!res.ok) return;
        const logs = await res.json();
        const tbody = document.getElementById("notificationLogsBody");
        if (!tbody) return;

        tbody.innerHTML = logs.map(l => `
            <tr class="hover:bg-slate-50 border-b border-slate-100">
                <td class="p-2.5 font-mono text-[11px] text-slate-400">${new Date(l.sent_at).toLocaleString()}</td>
                <td class="p-2.5 font-bold text-blue-600">${l.channel}</td>
                <td class="p-2.5">${l.recipient_email}</td>
                <td class="p-2.5 font-semibold text-slate-700">${l.subject}</td>
                <td class="p-2.5 text-slate-500 max-w-xs truncate" title="${l.message}">${l.message}</td>
                <td class="p-2.5"><span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-emerald-100 text-emerald-800">${l.status}</span></td>
            </tr>
        `).join("");
    } catch (err) {
        console.error("Error loading notification logs:", err);
    }
}

function closeModal(modalId) {
    document.getElementById(modalId)?.classList.add("hidden");
}
