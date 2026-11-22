(function () {
  if (window.__NAIJASALE_HELP_CENTER_LOADED__) return;
  window.__NAIJASALE_HELP_CENTER_LOADED__ = true;

  const SUPPORT_API_URL = "/api/support-chat/";
  const WHATSAPP_NUMBER = "2348122635608";

  let isOpen = false;
  let activeTab = "directions"; // 'directions' | 'chat' | 'whatsapp'
  let stateData = null;
  let selectedStaffThreadId = null;
  let lastRenderedSignature = "";

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
        right: 16px;
        bottom: 88px;
        z-index: 99990;
        background: #0F172A;
        color: #FFFFFF;
        border: 1px solid rgba(255, 255, 255, 0.14);
        border-radius: 999px;
        padding: 10px 15px;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
        font-size: 12.5px;
        font-weight: 700;
        letter-spacing: -0.01em;
        cursor: pointer;
        box-shadow: 0 10px 28px rgba(15, 23, 42, 0.22);
        transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
      }
      @media (min-width: 768px) {
        #ns-help-launcher { bottom: 24px; right: 24px; }
        #ns-help-drawer { bottom: 78px; right: 24px; }
      }
      #ns-help-launcher:hover {
        background: #1E293B;
        transform: translateY(-2px);
        box-shadow: 0 14px 32px rgba(15, 23, 42, 0.28);
      }
      .ns-hc-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #22C55E;
        box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.22);
      }
      #ns-help-badge {
        background: #EF4444;
        color: #FFFFFF;
        font-size: 10.5px;
        font-weight: 800;
        min-width: 18px;
        height: 18px;
        border-radius: 999px;
        display: none;
        align-items: center;
        justify-content: center;
        padding: 0 5px;
      }
      #ns-help-drawer {
        position: fixed;
        right: 12px;
        left: 12px;
        bottom: 140px;
        margin-left: auto;
        z-index: 99995;
        width: auto;
        max-width: 390px;
        max-height: 74vh;
        background: #FFFFFF;
        color: #0F172A;
        border: 1px solid #E2E8F0;
        border-radius: 22px;
        box-shadow: 0 24px 60px rgba(15, 23, 42, 0.16), 0 4px 16px rgba(15, 23, 42, 0.06);
        display: none;
        flex-direction: column;
        overflow: hidden;
        font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
      }
      .ns-hc-header {
        background: #FFFFFF;
        color: #0F172A;
        padding: 15px 16px 12px 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid #F1F5F9;
      }
      .ns-hc-title-wrap {
        display: flex;
        align-items: center;
        gap: 10px;
      }
      .ns-hc-avatar {
        width: 34px;
        height: 34px;
        border-radius: 11px;
        background: #FFF7ED;
        color: #EA580C;
        border: 1px solid #FFEDD5;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 800;
        font-size: 15px;
      }
      .ns-hc-close-btn {
        width: 30px;
        height: 30px;
        border-radius: 999px;
        border: 1px solid #E2E8F0;
        background: #F8FAFC;
        color: #475569;
        font-size: 17px;
        line-height: 1;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .ns-hc-close-btn:hover { background: #F1F5F9; color: #0F172A; }
      .ns-hc-tabs-wrap {
        padding: 8px 12px;
        background: #FFFFFF;
        border-bottom: 1px solid #F1F5F9;
      }
      .ns-hc-tabs {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        background: #F1F5F9;
        padding: 3px;
        border-radius: 12px;
        gap: 3px;
      }
      .ns-hc-tab {
        padding: 7px 6px;
        font-size: 11.5px;
        font-weight: 700;
        color: #64748B;
        background: transparent;
        border: none;
        border-radius: 9px;
        cursor: pointer;
        transition: all 0.18s ease;
      }
      .ns-hc-tab.active {
        color: #0F172A;
        background: #FFFFFF;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.08);
      }
      .ns-hc-body {
        padding: 13px 14px 14px 14px;
        overflow-y: auto;
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 9px;
        background: #FAFAFA;
      }
      .ns-guide-card {
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 11px 13px;
        background: #FFFFFF;
        transition: border-color 0.15s ease;
      }
      .ns-guide-card:hover { border-color: #CBD5E1; }
      .ns-guide-card h4 {
        margin: 0 0 3px 0;
        font-size: 12.5px;
        font-weight: 800;
        color: #0F172A;
      }
      .ns-guide-card p {
        margin: 0 0 7px 0;
        font-size: 11.5px;
        color: #64748B;
        line-height: 1.45;
      }
      .ns-guide-link {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 11.5px;
        font-weight: 700;
        color: #EA580C;
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
        border-radius: 14px;
        font-size: 12.5px;
        font-weight: 800;
        box-shadow: 0 6px 16px rgba(22, 163, 74, 0.22);
      }
      .ns-wa-topic {
        display: flex;
        align-items: center;
        justify-content: space-between;
        border: 1px solid #E2E8F0;
        background: #FFFFFF;
        color: #1E293B;
        text-decoration: none;
        padding: 10px 12px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
      }
      .ns-wa-topic:hover { border-color: #86EFAC; background: #F0FDF4; }
      .ns-chat-box {
        display: flex;
        flex-direction: column;
        gap: 8px;
        min-height: 195px;
        max-height: 255px;
        overflow-y: auto;
        padding: 4px 2px;
      }
      .ns-msg {
        max-width: 82%;
        padding: 9px 12px;
        border-radius: 15px;
        font-size: 12.5px;
        line-height: 1.42;
        word-break: break-word;
      }
      .ns-msg.mine {
        align-self: flex-end;
        background: #0F172A;
        color: #FFFFFF;
        border-bottom-right-radius: 4px;
      }
      .ns-msg.theirs {
        align-self: flex-start;
        background: #FFFFFF;
        color: #0F172A;
        border: 1px solid #E2E8F0;
        border-bottom-left-radius: 4px;
      }
      .ns-msg-meta {
        font-size: 10px;
        opacity: 0.65;
        margin-top: 3px;
      }
      .ns-chat-form {
        display: flex;
        flex-direction: column;
        gap: 7px;
        border-top: 1px solid #E2E8F0;
        padding-top: 10px;
        background: #FAFAFA;
      }
      .ns-chat-row {
        display: flex;
        gap: 6px;
        align-items: center;
      }
      .ns-chat-input {
        flex: 1;
        border: 1px solid #CBD5E1;
        background: #FFFFFF;
        color: #0F172A;
        border-radius: 12px;
        padding: 9px 12px;
        font-size: 16px; /* Prevents iOS Safari auto-zoom & keyboard flicker */
        outline: none;
        width: 100%;
        box-sizing: border-box;
      }
      @media (min-width: 768px) {
        .ns-chat-input { font-size: 12.5px; }
      }
      .ns-chat-input:focus {
        border-color: #EA580C;
        box-shadow: 0 0 0 3px rgba(234, 88, 12, 0.12);
      }
      .ns-chat-send {
        background: #EA580C;
        color: #FFFFFF;
        border: none;
        border-radius: 12px;
        padding: 10px 14px;
        font-size: 12.5px;
        font-weight: 800;
        cursor: pointer;
        flex-shrink: 0;
      }
      .ns-chat-send:hover { background: #C2410C; }
    `;
    document.head.appendChild(style);
  }

  function createUI() {
    injectStyles();

    const launcher = document.createElement("button");
    launcher.id = "ns-help-launcher";
    launcher.type = "button";
    launcher.innerHTML = `
      <span class="ns-hc-dot"></span>
      <span>Help & Support</span>
      <span id="ns-help-badge">0</span>
    `;
    launcher.addEventListener("click", function () {
      isOpen = !isOpen;
      drawer.style.display = isOpen ? "flex" : "none";
      if (isOpen) {
        lastRenderedSignature = "";
        renderBody(true);
        fetchSupportState(true);
      }
    });

    const drawer = document.createElement("div");
    drawer.id = "ns-help-drawer";
    drawer.innerHTML = `
      <div class="ns-hc-header">
        <div class="ns-hc-title-wrap">
          <div class="ns-hc-avatar">N</div>
          <div>
            <div style="font-size:13.5px;font-weight:800;color:#0F172A;">Naijasale Support</div>
            <div style="font-size:11px;color:#16A34A;font-weight:600;">● Online • Replies fast</div>
          </div>
        </div>
        <button type="button" id="ns-hc-close" class="ns-hc-close-btn" aria-label="Close">&times;</button>
      </div>
      <div class="ns-hc-tabs-wrap">
        <div class="ns-hc-tabs">
          <button type="button" class="ns-hc-tab active" data-tab="directions">Quick Guide</button>
          <button type="button" class="ns-hc-tab" data-tab="chat">Live Chat</button>
          <button type="button" class="ns-hc-tab" data-tab="whatsapp">WhatsApp</button>
        </div>
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
        lastRenderedSignature = "";
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
        <h4>1. Post an Ad for Free</h4>
        <p>Upload clear photos, pick your State & Area, and submit for fast approval.</p>
        <a class="ns-guide-link" href="/post-ad/">Open Post Ad &rarr;</a>
      </div>
      <div class="ns-guide-card">
        <h4>2. Get Your Verified Seller Badge</h4>
        <p>Verify your NIN on your profile so buyers trust your listings immediately.</p>
        <a class="ns-guide-link" href="/profile/">Verify Profile &rarr;</a>
      </div>
      <div class="ns-guide-card">
        <h4>3. Boost Your Ad to Top Deals</h4>
        <p>Go to your Dashboard, select an active listing, and tap Promote for VIP placement.</p>
        <a class="ns-guide-link" href="/dashboard/">Go to Dashboard &rarr;</a>
      </div>
      <div class="ns-guide-card">
        <h4>4. Safe Trading Rules</h4>
        <p>Meet in open public places and inspect items before paying. Never pay before inspection.</p>
      </div>
    `;
  }

  function renderWhatsApp(bodyEl) {
    bodyEl.innerHTML = `
      <a class="ns-wa-btn" href="${buildWhatsAppUrl("General Support")}" target="_blank" rel="noopener">
        <span>Message WhatsApp (0812 263 5608)</span>
        <span>&rarr;</span>
      </a>
      <div style="font-size:11px;font-weight:700;color:#64748B;margin-top:2px;">Quick WhatsApp Topics:</div>
      <a class="ns-wa-topic" href="${buildWhatsAppUrl("Posting or approving my ad")}" target="_blank" rel="noopener"><span>Ad posting or review help</span><span>&rarr;</span></a>
      <a class="ns-wa-topic" href="${buildWhatsAppUrl("NIN / KYC seller verification")}" target="_blank" rel="noopener"><span>NIN / Seller badge help</span><span>&rarr;</span></a>
      <a class="ns-wa-topic" href="${buildWhatsAppUrl("Ad promotion / payment")}" target="_blank" rel="noopener"><span>Ad promotion & payment</span><span>&rarr;</span></a>
      <a class="ns-wa-topic" href="${buildWhatsAppUrl("Reporting a suspicious listing or user")}" target="_blank" rel="noopener"><span>Report a safety concern</span><span>&rarr;</span></a>
    `;
  }

  function updateMessagesListOnly(containerEl, msgs, isStaffMode, visitorName) {
    const welcomeHtml = !isStaffMode
      ? `
        <div class="ns-msg theirs">
          <div>Hi ${escapeHtml(visitorName || "there")}! Ask us anything about buying, selling, or verification on Naijasale.</div>
          <div class="ns-msg-meta">Naijasale Support</div>
        </div>
      `
      : "";

    const msgsHtml = (msgs || [])
      .map(function (m) {
        const isMine = isStaffMode ? m.sender === "staff" : m.sender === "user";
        return `
          <div class="ns-msg ${isMine ? "mine" : "theirs"}">
            <div>${escapeHtml(m.text)}</div>
            <div class="ns-msg-meta">${escapeHtml(m.sender_name)} • ${escapeHtml(m.time)}</div>
          </div>
        `;
      })
      .join("");

    const nextHtml = welcomeHtml + msgsHtml;
    if (containerEl.innerHTML !== nextHtml) {
      containerEl.innerHTML = nextHtml;
      containerEl.scrollTop = containerEl.scrollHeight;
    }
  }

  function renderChat(bodyEl, markReadNow) {
    if (!stateData) {
      bodyEl.innerHTML = `<div style="font-size:12px;color:#64748B;text-align:center;padding:28px 0;">Connecting to live support...</div>`;
      return;
    }

    // =========================================================
    // STAFF / ADMIN SUPPORT DESK VIEW
    // =========================================================
    if (stateData.role === "staff") {
      const threads = stateData.threads || [];
      if (threads.length === 0) {
        lastRenderedSignature = "staff_empty";
        bodyEl.innerHTML = `<div style="font-size:12px;color:#64748B;text-align:center;padding:30px 10px;">No customer support chats yet. New messages from guests and members will show here live.</div>`;
        return;
      }

      if (!selectedStaffThreadId || !threads.some((t) => t.thread_id === selectedStaffThreadId)) {
        selectedStaffThreadId = threads[0].thread_id;
      }
      const activeThread = threads.find((t) => t.thread_id === selectedStaffThreadId);

      if (markReadNow && activeThread && activeThread.unread_by_staff > 0) {
        sendPost({ action: "mark_read", thread_id: activeThread.thread_id });
      }

      const shellSig = "staff_shell_" + threads.map((t) => t.thread_id + ":" + t.unread_by_staff).join(",");
      let chatBox = bodyEl.querySelector("#ns-chat-messages");

      // Only rebuild the form/select if the shell changed AND the user is not currently typing
      const activeInput = bodyEl.querySelector("#ns-staff-reply-input");
      const isTyping = activeInput && document.activeElement === activeInput;

      if (!chatBox || (lastRenderedSignature !== shellSig && !isTyping)) {
        lastRenderedSignature = shellSig;
        const optionsHtml = threads
          .map(function (t) {
            const unreadTag = t.unread_by_staff > 0 ? ` (${t.unread_by_staff} NEW)` : "";
            const sel = t.thread_id === selectedStaffThreadId ? "selected" : "";
            return `<option value="${escapeHtml(t.thread_id)}" ${sel}>${escapeHtml(t.name)} • ${escapeHtml(t.subtitle)}${unreadTag}</option>`;
          })
          .join("");

        bodyEl.innerHTML = `
          <div style="font-size:10.5px;font-weight:800;letter-spacing:0.04em;color:#64748B;">LIVE CUSTOMER DESK</div>
          <select id="ns-staff-thread-select" class="ns-chat-input" style="font-weight:700;font-size:12px;">${optionsHtml}</select>
          <div class="ns-chat-box" id="ns-chat-messages"></div>
          <form class="ns-chat-form" id="ns-staff-reply-form">
            <div class="ns-chat-row">
              <input type="text" id="ns-staff-reply-input" class="ns-chat-input" placeholder="Write a reply..." autocomplete="off" required />
              <button type="submit" class="ns-chat-send">Send</button>
            </div>
          </form>
        `;

        bodyEl.querySelector("#ns-staff-thread-select").addEventListener("change", function (e) {
          selectedStaffThreadId = e.target.value;
          lastRenderedSignature = "";
          renderChat(bodyEl, true);
        });

        bodyEl.querySelector("#ns-staff-reply-form").addEventListener("submit", async function (e) {
          e.preventDefault();
          const input = bodyEl.querySelector("#ns-staff-reply-input");
          const text = input.value.trim();
          if (!text) return;
          input.value = "";
          input.focus();
          await sendPost({ thread_id: selectedStaffThreadId, text: text });
        });

        chatBox = bodyEl.querySelector("#ns-chat-messages");
      }

      if (chatBox) {
        updateMessagesListOnly(chatBox, activeThread.messages || [], true, "");
      }
      return;
    }

    // =========================================================
    // CUSTOMER / GUEST VISITOR CHAT VIEW
    // =========================================================
    if (markReadNow && stateData.unread_count > 0) {
      sendPost({ action: "mark_read" });
    }

    const customerShellSig = "customer_shell_" + (stateData.is_registered ? "reg" : "guest");
    let chatBox = bodyEl.querySelector("#ns-chat-messages");

    if (!chatBox || lastRenderedSignature !== customerShellSig) {
      lastRenderedSignature = customerShellSig;
      const guestContactField = !stateData.is_registered
        ? `<input type="text" id="ns-guest-contact" class="ns-chat-input" placeholder="Your name or WhatsApp (optional)" />`
        : "";

      bodyEl.innerHTML = `
        <div class="ns-chat-box" id="ns-chat-messages"></div>
        <form class="ns-chat-form" id="ns-customer-chat-form">
          ${guestContactField}
          <div class="ns-chat-row">
            <input type="text" id="ns-customer-chat-input" class="ns-chat-input" placeholder="Type your message..." autocomplete="off" required />
            <button type="submit" class="ns-chat-send">Send</button>
          </div>
        </form>
      `;

      bodyEl.querySelector("#ns-customer-chat-form").addEventListener("submit", async function (e) {
        e.preventDefault();
        const input = bodyEl.querySelector("#ns-customer-chat-input");
        const contactInput = bodyEl.querySelector("#ns-guest-contact");
        const text = input.value.trim();
        if (!text) return;
        input.value = "";
        input.focus();
        await sendPost({
          text: text,
          contact: contactInput ? contactInput.value.trim() : ""
        });
      });

      chatBox = bodyEl.querySelector("#ns-chat-messages");
    }

    if (chatBox) {
      updateMessagesListOnly(chatBox, stateData.messages || [], false, stateData.visitor_name);
    }
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
    setInterval(function () {
      fetchSupportState(isOpen && activeTab === "chat");
    }, 6000);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();