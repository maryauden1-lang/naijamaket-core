(function () {
  if (window.__NAIJASALE_HELP_CENTER_LOADED__) return;
  window.__NAIJASALE_HELP_CENTER_LOADED__ = true;

  const SUPPORT_API_URL = "/api/support-chat/";
  const WHATSAPP_NUMBER = "2348122635608";

  let isOpen = false;
  let activeTab = "directions"; // 'directions' | 'chat' | 'whatsapp'
  let stateData = null;
  let selectedStaffThreadId = null;
  let pollHandle = null;

  function getCookie(name) {
    const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
    return match ? decodeURIComponent(match[2]) : "";
  }

  function escapeHtml(str) {
    return String(str || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function buildWhatsAppUrl(topicText) {
    const msg = encodeURIComponent(
      "Hello Naijasale Customer Service, I need help with: " + topicText
    );
    return "https://wa.me/" + WHATSAPP_NUMBER + "?text=" + msg;
  }

  function injectStyles() {
    if (document.getElementById("ns-help-center-styles")) return;
    const style = document.createElement("style");
    style.id = "ns-help-center-styles";
    style.textContent = `
      #ns-help-launcher {
        position: fixed;
        right: 18px;
        bottom: 84px;
        z-index: 99990;
        background: #4C1D95;
        color: #FFFFFF;
        border: 1px solid rgba(255,255,255,0.18);
        border-radius: 999px;
        padding: 11px 16px;
        display: flex;
        align-items: center;
        gap: 8px;
        font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
        font-size: 13px;
        font-weight: 800;
        cursor: pointer;
        box-shadow: 0 10px 25px rgba(76, 29, 149, 0.35);
        transition: transform 0.2s ease, background 0.2s ease;
      }
      @media (min-width: 768px) {
        #ns-help-launcher { bottom: 24px; right: 24px; }
        #ns-help-drawer { bottom: 82px; right: 24px; }
      }
      #ns-help-launcher:hover { background: #5B21B6; transform: translateY(-2px); }
      #ns-help-badge {
        background: #EF4444;
        color: #FFFFFF;
        font-size: 11px;
        font-weight: 800;
        min-width: 19px;
        height: 19px;
        border-radius: 999px;
        display: none;
        align-items: center;
        justify-content: center;
        padding: 0 5px;
      }
      #ns-help-drawer {
        position: fixed;
        right: 14px;
        bottom: 138px;
        z-index: 99995;
        width: min(92vw, 385px);
        max-height: 76vh;
        background: #FFFFFF;
        color: #0F172A;
        border: 1px solid #E2E8F0;
        border-radius: 20px;
        box-shadow: 0 20px 45px rgba(15, 23, 42, 0.22);
        display: none;
        flex-direction: column;
        overflow: hidden;
        font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
      }
      .ns-hc-header {
        background: linear-gradient(135deg, #4C1D95 0%, #6D28D9 100%);
        color: #FFFFFF;
        padding: 15px 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
      }
      .ns-hc-tabs {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        background: #F8FAFC;
        border-bottom: 1px solid #E2E8F0;
      }
      .ns-hc-tab {
        padding: 10px 6px;
        font-size: 12px;
        font-weight: 700;
        color: #475569;
        background: transparent;
        border: none;
        border-bottom: 2px solid transparent;
        cursor: pointer;
      }
      .ns-hc-tab.active {
        color: #6D28D9;
        border-bottom-color: #6D28D9;
        background: #FFFFFF;
      }
      .ns-hc-body {
        padding: 14px;
        overflow-y: auto;
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
      .ns-guide-card {
        border: 1px solid #E2E8F0;
        border-radius: 13px;
        padding: 11px 12px;
        background: #FFFFFF;
      }
      .ns-guide-card h4 {
        margin: 0 0 4px 0;
        font-size: 13px;
        font-weight: 800;
        color: #1E293B;
      }
      .ns-guide-card p {
        margin: 0 0 8px 0;
        font-size: 12px;
        color: #64748B;
        line-height: 1.45;
      }
      .ns-guide-link {
        display: inline-block;
        font-size: 12px;
        font-weight: 700;
        color: #6D28D9;
        text-decoration: none;
      }
      .ns-wa-btn {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #16A34A;
        color: #FFFFFF;
        text-decoration: none;
        padding: 12px 14px;
        border-radius: 13px;
        font-size: 13px;
        font-weight: 800;
      }
      .ns-wa-topic {
        display: block;
        border: 1px solid #BBF7D0;
        background: #F0FDF4;
        color: #166534;
        text-decoration: none;
        padding: 10px 12px;
        border-radius: 11px;
        font-size: 12px;
        font-weight: 700;
      }
      .ns-chat-box {
        display: flex;
        flex-direction: column;
        gap: 8px;
        min-height: 210px;
        max-height: 290px;
        overflow-y: auto;
        padding: 4px 2px;
      }
      .ns-msg {
        max-width: 82%;
        padding: 9px 12px;
        border-radius: 14px;
        font-size: 12.5px;
        line-height: 1.4;
        word-break: break-word;
      }
      .ns-msg.mine {
        align-self: flex-end;
        background: #6D28D9;
        color: #FFFFFF;
        border-bottom-right-radius: 4px;
      }
      .ns-msg.theirs {
        align-self: flex-start;
        background: #F1F5F9;
        color: #0F172A;
        border-bottom-left-radius: 4px;
      }
      .ns-msg-meta {
        font-size: 10px;
        opacity: 0.75;
        margin-top: 3px;
      }
      .ns-chat-form {
        display: flex;
        flex-direction: column;
        gap: 7px;
        border-top: 1px solid #E2E8F0;
        padding-top: 10px;
      }
      .ns-chat-row {
        display: flex;
        gap: 6px;
      }
      .ns-chat-input {
        flex: 1;
        border: 1px solid #CBD5E1;
        border-radius: 11px;
        padding: 9px 11px;
        font-size: 12.5px;
        outline: none;
      }
      .ns-chat-input:focus { border-color: #6D28D9; }
      .ns-chat-send {
        background: #6D28D9;
        color: #FFFFFF;
        border: none;
        border-radius: 11px;
        padding: 0 14px;
        font-size: 12.5px;
        font-weight: 800;
        cursor: pointer;
      }
    `;
    document.head.appendChild(style);
  }

  function createUI() {
    injectStyles();

    const launcher = document.createElement("button");
    launcher.id = "ns-help-launcher";
    launcher.type = "button";
    launcher.innerHTML = `
      <span>🎧 Help & Support</span>
      <span id="ns-help-badge">0</span>
    `;
    launcher.addEventListener("click", function () {
      isOpen = !isOpen;
      drawer.style.display = isOpen ? "flex" : "none";
      if (isOpen) {
        fetchSupportState(true);
      }
    });

    const drawer = document.createElement("div");
    drawer.id = "ns-help-drawer";
    drawer.innerHTML = `
      <div class="ns-hc-header">
        <div>
          <div style="font-size:14px;font-weight:800;">Naijasale Help Center</div>
          <div style="font-size:11px;color:#DDD6FE;">Instant directions, Live Chat & WhatsApp</div>
        </div>
        <button type="button" id="ns-hc-close" style="background:transparent;border:none;color:#FFFFFF;font-size:20px;cursor:pointer;line-height:1;">&times;</button>
      </div>
      <div class="ns-hc-tabs">
        <button type="button" class="ns-hc-tab active" data-tab="directions">🧭 Directions</button>
        <button type="button" class="ns-hc-tab" data-tab="chat">💬 Live Chat</button>
        <button type="button" class="ns-hc-tab" data-tab="whatsapp">📱 WhatsApp</button>
      </div>
      <div class="ns-hc-body" id="ns-hc-body"></div>
    `;

    document.body.appendChild(launcher);
    document.body.appendChild(drawer);

    drawer.querySelector("#ns-hc-close").addEventListener("click", function () {
      isOpen = false;
      drawer.style.display = "none";
    });

    drawer.querySelectorAll(".ns-hc-tab").forEach(function (tabBtn) {
      tabBtn.addEventListener("click", function () {
        activeTab = tabBtn.getAttribute("data-tab");
        drawer.querySelectorAll(".ns-hc-tab").forEach(function (b) {
          b.classList.toggle("active", b === tabBtn);
        });
        renderBody(true);
      });
    });

    renderBody(false);
  }

  function updateBadge(count) {
    const badge = document.getElementById("ns-help-badge");
    if (!badge) return;
    if (count > 0) {
      badge.textContent = count;
      badge.style.display = "inline-flex";
    } else {
      badge.style.display = "none";
    }
  }

  function renderDirections(bodyEl) {
    bodyEl.innerHTML = `
      <div class="ns-guide-card">
        <h4>1. How to Post an Ad on Naijasale</h4>
        <p>Tap Post Ad, upload clear photos of your item, choose your State & Area, and submit for quick review.</p>
        <a class="ns-guide-link" href="/post-ad/">Go to Post Ad Page &rarr;</a>
      </div>
      <div class="ns-guide-card">
        <h4>2. How to Get Your Verified Seller Badge</h4>
        <p>Open your Profile page and submit your NIN details so buyers trust your store faster.</p>
        <a class="ns-guide-link" href="/profile/">Open Profile & Verification &rarr;</a>
      </div>
      <div class="ns-guide-card">
        <h4>3. How to Boost & Sell Faster</h4>
        <p>Open your Seller Dashboard, pick any active listing, and tap Promote to feature it at the top.</p>
        <a class="ns-guide-link" href="/dashboard/">Open My Dashboard &rarr;</a>
      </div>
      <div class="ns-guide-card">
        <h4>4. Safe Buying & Selling Tips</h4>
        <p>Always meet in open public places, inspect items thoroughly before paying, and never send delivery fees upfront.</p>
      </div>
    `;
  }

  function renderWhatsApp(bodyEl) {
    bodyEl.innerHTML = `
      <a class="ns-wa-btn" href="${buildWhatsAppUrl("General Support")}" target="_blank" rel="noopener">
        <span>Chat on WhatsApp (0812 263 5608)</span>
        <span>&rarr;</span>
      </a>
      <div style="font-size:11.5px;font-weight:700;color:#64748B;margin-top:4px;">Or choose a quick topic to start immediately:</div>
      <a class="ns-wa-topic" href="${buildWhatsAppUrl("Posting or approving my ad")}" target="_blank" rel="noopener">📦 Help with posting or approving my ad</a>
      <a class="ns-wa-topic" href="${buildWhatsAppUrl("NIN / KYC seller verification")}" target="_blank" rel="noopener">🪪 Help with NIN / Seller Verification</a>
      <a class="ns-wa-topic" href="${buildWhatsAppUrl("Ad promotion / payment")}" target="_blank" rel="noopener">🚀 Help with Ad Boost & Payment</a>
      <a class="ns-wa-topic" href="${buildWhatsAppUrl("Reporting a suspicious listing or user")}" target="_blank" rel="noopener">🛡️ Report a safety issue</a>
    `;
  }

  function renderChat(bodyEl, markReadNow) {
    if (!stateData) {
      bodyEl.innerHTML = `<div style="font-size:12px;color:#64748B;text-align:center;padding:24px 0;">Connecting to Naijasale Customer Care...</div>`;
      return;
    }

    // STAFF / ADMIN SUPPORT DESK VIEW
    if (stateData.role === "staff") {
      const threads = stateData.threads || [];
      if (threads.length === 0) {
        bodyEl.innerHTML = `<div style="font-size:12.5px;color:#64748B;text-align:center;padding:30px 10px;">No customer support messages yet. When a guest or member messages Support, it will appear right here.</div>`;
        return;
      }

      if (!selectedStaffThreadId || !threads.some((t) => t.thread_id === selectedStaffThreadId)) {
        selectedStaffThreadId = threads[0].thread_id;
      }
      const activeThread = threads.find((t) => t.thread_id === selectedStaffThreadId);

      if (markReadNow && activeThread && activeThread.unread_by_staff > 0) {
        sendPost({ action: "mark_read", thread_id: activeThread.thread_id });
      }

      const optionsHtml = threads
        .map(function (t) {
          const unreadTag = t.unread_by_staff > 0 ? ` (${t.unread_by_staff} NEW)` : "";
          const sel = t.thread_id === selectedStaffThreadId ? "selected" : "";
          return `<option value="${escapeHtml(t.thread_id)}" ${sel}>${escapeHtml(t.name)} — ${escapeHtml(t.subtitle)}${unreadTag}</option>`;
        })
        .join("");

      const msgsHtml = (activeThread.messages || [])
        .map(function (m) {
          const isMine = m.sender === "staff";
          return `
            <div class="ns-msg ${isMine ? "mine" : "theirs"}">
              <div>${escapeHtml(m.text)}</div>
              <div class="ns-msg-meta">${escapeHtml(m.sender_name)} • ${escapeHtml(m.time)}</div>
            </div>
          `;
        })
        .join("");

      bodyEl.innerHTML = `
        <div style="font-size:11px;font-weight:800;color:#6D28D9;">SUPPORT DESK (ALL GUESTS & MEMBERS)</div>
        <select id="ns-staff-thread-select" class="ns-chat-input" style="font-weight:700;">${optionsHtml}</select>
        <div class="ns-chat-box" id="ns-chat-messages">${msgsHtml}</div>
        <form class="ns-chat-form" id="ns-staff-reply-form">
          <div class="ns-chat-row">
            <input type="text" id="ns-staff-reply-input" class="ns-chat-input" placeholder="Reply to ${escapeHtml(activeThread.name)}..." required />
            <button type="submit" class="ns-chat-send">Send</button>
          </div>
        </form>
      `;

      const chatBox = bodyEl.querySelector("#ns-chat-messages");
      if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;

      bodyEl.querySelector("#ns-staff-thread-select").addEventListener("change", function (e) {
        selectedStaffThreadId = e.target.value;
        renderChat(bodyEl, true);
      });

      bodyEl.querySelector("#ns-staff-reply-form").addEventListener("submit", async function (e) {
        e.preventDefault();
        const input = bodyEl.querySelector("#ns-staff-reply-input");
        const text = input.value.trim();
        if (!text) return;
        input.value = "";
        await sendPost({ thread_id: selectedStaffThreadId, text: text });
      });
      return;
    }

    // CUSTOMER / GUEST VISITOR CHAT VIEW
    if (markReadNow && stateData.unread_count > 0) {
      sendPost({ action: "mark_read" });
    }

    const msgs = stateData.messages || [];
    const welcomeHtml = `
      <div class="ns-msg theirs">
        <div>Hello ${escapeHtml(stateData.visitor_name)}! 👋 Ask us anything about buying, selling, or verification on Naijasale.</div>
        <div class="ns-msg-meta">Naijasale Customer Care</div>
      </div>
    `;
    const msgsHtml = msgs
      .map(function (m) {
        const isMine = m.sender === "user";
        return `
          <div class="ns-msg ${isMine ? "mine" : "theirs"}">
            <div>${escapeHtml(m.text)}</div>
            <div class="ns-msg-meta">${escapeHtml(m.sender_name)} • ${escapeHtml(m.time)}</div>
          </div>
        `;
      })
      .join("");

    const guestContactField = !stateData.is_registered
      ? `<input type="text" id="ns-guest-contact" class="ns-chat-input" placeholder="Optional: Your Name or WhatsApp number" />`
      : "";

    bodyEl.innerHTML = `
      <div class="ns-chat-box" id="ns-chat-messages">${welcomeHtml}${msgsHtml}</div>
      <form class="ns-chat-form" id="ns-customer-chat-form">
        ${guestContactField}
        <div class="ns-chat-row">
          <input type="text" id="ns-customer-chat-input" class="ns-chat-input" placeholder="Type your question here..." required />
          <button type="submit" class="ns-chat-send">Send</button>
        </div>
      </form>
    `;

    const chatBox = bodyEl.querySelector("#ns-chat-messages");
    if (chatBox) chatBox.scrollTop = chatBox.scrollHeight;

    bodyEl.querySelector("#ns-customer-chat-form").addEventListener("submit", async function (e) {
      e.preventDefault();
      const input = bodyEl.querySelector("#ns-customer-chat-input");
      const contactInput = bodyEl.querySelector("#ns-guest-contact");
      const text = input.value.trim();
      if (!text) return;
      input.value = "";
      await sendPost({
        text: text,
        contact: contactInput ? contactInput.value.trim() : ""
      });
    });
  }

  function renderBody(markReadNow) {
    const bodyEl = document.getElementById("ns-hc-body");
    if (!bodyEl) return;
    if (activeTab === "directions") {
      renderDirections(bodyEl);
    } else if (activeTab === "whatsapp") {
      renderWhatsApp(bodyEl);
    } else {
      renderChat(bodyEl, markReadNow);
    }
  }

  async function sendPost(payload) {
    try {
      const res = await fetch(SUPPORT_API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": getCookie("csrftoken"),
          "X-Requested-With": "XMLHttpRequest"
        },
        credentials: "same-origin",
        body: JSON.stringify(payload)
      });
      if (!res.ok) return;
      stateData = await res.json();
      updateBadge(stateData.unread_count || 0);
      if (isOpen && activeTab === "chat") {
        renderChat(document.getElementById("ns-hc-body"), false);
      }
    } catch (err) {}
  }

  async function fetchSupportState(markReadNow) {
    if (document.hidden && !isOpen) return;
    try {
      const res = await fetch(SUPPORT_API_URL, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin"
      });
      if (!res.ok) return;
      stateData = await res.json();
      updateBadge(stateData.unread_count || 0);
      if (isOpen && activeTab === "chat") {
        renderChat(document.getElementById("ns-hc-body"), markReadNow);
      }
    } catch (err) {}
  }

  function init() {
    createUI();
    fetchSupportState(false);
    pollHandle = setInterval(function () {
      fetchSupportState(isOpen && activeTab === "chat");
    }, 6000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();