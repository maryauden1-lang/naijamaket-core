(function () {
  if (window.__NAIJASALE_HELP_CENTER_LOADED__) return;
  window.__NAIJASALE_HELP_CENTER_LOADED__ = true;

  const SUPPORT_API_URL = "/api/support-chat/";
  const WHATSAPP_NUMBER = "2348122635608";

  let isOpen = false;
  let activeTab = "directions"; // 'directions' | 'chat' | 'whatsapp'
  let searchQuery = "";
  let stateData = null;
  let selectedStaffThreadId = null;
  let lastRenderedSignature = "";

  const QUICK_GUIDE_ITEMS = [
    {
      num: "1",
      title: "1. Post an Ad for Free",
      desc: "Upload clear photos, pick your State & Area, and submit for fast approval.",
      cta: "Open Post Ad",
      href: "/post-ad/",
      icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 11 18-5v12L3 14v-3z"/><path d="M11.6 16.8a3 3 0 1 1-5.8-1.6"/></svg>`
    },
    {
      num: "2",
      title: "2. Get Your Verified Seller Badge",
      desc: "Verify your NIN on your profile so buyers trust your listings immediately.",
      cta: "Verify Profile",
      href: "/profile/",
      icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2 4 5v6.09c0 5.05 3.41 9.76 8 10.91 4.59-1.15 8-5.86 8-10.91V5l-8-3zm-1.06 13.54L7.4 12l1.41-1.41 2.12 2.12 4.24-4.24 1.41 1.41-5.64 5.66z"/></svg>`
    },
    {
      num: "3",
      title: "3. Boost Your Ad to Top Deals",
      desc: "Go to your Dashboard, select an active listing, and tap Promote for VIP placement.",
      cta: "Go to Dashboard",
      href: "/dashboard/",
      icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/><path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/><path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/><path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/></svg>`
    },
    {
      num: "4",
      title: "4. Safe Trading Rules",
      desc: "Meet in open public places and inspect items before paying. Never pay before inspection.",
      cta: "Learn More",
      href: "/page/safety-tips/",
      icon: `<svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2 4 5v6.09c0 5.05 3.41 9.76 8 10.91 4.59-1.15 8-5.86 8-10.91V5l-8-3zm-1.06 13.54L7.4 12l1.41-1.41 2.12 2.12 4.24-4.24 1.41 1.41-5.64 5.66z"/></svg>`
    }
  ];

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
        background: linear-gradient(135deg, #6D28D9 0%, #5B21B6 100%);
        color: #FFFFFF;
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 999px;
        padding: 10px 16px;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
        font-size: 12.5px;
        font-weight: 800;
        letter-spacing: -0.01em;
        cursor: pointer;
        box-shadow: 0 10px 28px rgba(91, 33, 182, 0.34);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
      }
      @media (min-width: 768px) {
        #ns-help-launcher { bottom: 24px; right: 24px; }
        #ns-help-drawer { bottom: 78px; right: 24px; }
      }
      #ns-help-launcher:hover {
        transform: translateY(-2px);
        box-shadow: 0 14px 32px rgba(91, 33, 182, 0.42);
      }
      .ns-hc-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #22C55E;
        box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.28);
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
        right: 10px;
        left: 10px;
        bottom: 92px;
        margin-left: auto;
        z-index: 99995;
        width: auto;
        max-width: 410px;
        max-height: 84vh;
        background: #F6F4FF;
        color: #0F172A;
        border: 1px solid #E9E4FF;
        border-radius: 26px;
        box-shadow: 0 24px 60px rgba(30, 19, 58, 0.22), 0 4px 16px rgba(91, 33, 182, 0.08);
        display: none;
        flex-direction: column;
        overflow: hidden;
        font-family: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
      }
      .ns-hc-top-wrap {
        background: linear-gradient(180deg, #FFFFFF 0%, #F4F0FF 100%);
        padding: 14px 15px 12px 15px;
        border-bottom: 1px solid #EAE4FF;
      }
      .ns-hc-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 11px;
      }
      .ns-hc-title-wrap {
        display: flex;
        align-items: center;
        gap: 10px;
      }
      .ns-hc-brand-icon {
        width: 38px;
        height: 38px;
        border-radius: 12px;
        background: #EDE9FE;
        color: #6D28D9;
        border: 1px solid #DDD6FE;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .ns-hc-close-btn {
        width: 32px;
        height: 32px;
        border-radius: 999px;
        border: 1px solid #E9E4FF;
        background: #F5F3FF;
        color: #4C1D95;
        font-size: 18px;
        line-height: 1;
        cursor: pointer;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .ns-hc-close-btn:hover { background: #EDE9FE; }
      .ns-hc-hero-card {
        position: relative;
        background: linear-gradient(135deg, #F3EFFF 0%, #E6DEFF 100%);
        border: 1px solid #DDD6FE;
        border-radius: 20px;
        padding: 14px 14px 12px 14px;
        overflow: hidden;
      }
      .ns-hc-hero-row {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 8px;
        margin-bottom: 10px;
      }
      .ns-hc-hero-title {
        margin: 0;
        font-size: 16px;
        font-weight: 900;
        color: #0F172A;
        letter-spacing: -0.02em;
      }
      .ns-hc-hero-sub {
        margin: 4px 0 0 0;
        font-size: 11.5px;
        color: #475569;
        line-height: 1.4;
        max-width: 215px;
      }
      .ns-hc-search-wrap {
        position: relative;
        display: flex;
        align-items: center;
      }
      .ns-hc-search-icon {
        position: absolute;
        left: 13px;
        color: #475569;
        pointer-events: none;
        display: flex;
      }
      .ns-hc-search-input {
        width: 100%;
        box-sizing: border-box;
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 999px;
        padding: 9px 14px 9px 36px;
        font-size: 16px;
        font-weight: 500;
        color: #0F172A;
        outline: none;
        box-shadow: 0 2px 8px rgba(91, 33, 182, 0.05);
      }
      @media (min-width: 768px) {
        .ns-hc-search-input { font-size: 12.5px; }
      }
      .ns-hc-search-input:focus {
        border-color: #7C3AED;
        box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.12);
      }
      .ns-hc-tabs-wrap {
        padding: 10px 14px 4px 14px;
        background: #F6F4FF;
      }
      .ns-hc-tabs {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 7px;
      }
      .ns-hc-tab {
        padding: 8px 6px;
        font-size: 11.5px;
        font-weight: 800;
        color: #1E293B;
        background: #FFFFFF;
        border: 1px solid #E9E4FF;
        border-radius: 999px;
        cursor: pointer;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        gap: 5px;
        transition: all 0.18s ease;
        box-shadow: 0 2px 6px rgba(15, 23, 42, 0.03);
      }
      .ns-hc-tab.active {
        color: #FFFFFF;
        background: linear-gradient(135deg, #6D28D9 0%, #5B21B6 100%);
        border-color: #5B21B6;
        box-shadow: 0 6px 14px rgba(109, 40, 217, 0.28);
      }
      .ns-hc-body {
        padding: 10px 14px 14px 14px;
        overflow-y: auto;
        flex: 1;
        display: flex;
        flex-direction: column;
        gap: 9px;
        background: #F6F4FF;
      }
      .ns-guide-card {
        border: 1px solid #EBE6FF;
        border-radius: 18px;
        padding: 12px 13px;
        background: #FFFFFF;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 11px;
        box-shadow: 0 2px 8px rgba(91, 33, 182, 0.04);
        transition: border-color 0.15s ease, transform 0.15s ease;
      }
      .ns-guide-card:hover {
        border-color: #C4B5FD;
        transform: translateY(-1px);
      }
      .ns-guide-icon-box {
        width: 42px;
        height: 42px;
        border-radius: 14px;
        background: #F3EFFF;
        color: #6D28D9;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-shrink: 0;
      }
      .ns-guide-content {
        flex: 1;
        min-width: 0;
      }
      .ns-guide-card h4 {
        margin: 0 0 3px 0;
        font-size: 13px;
        font-weight: 800;
        color: #0F172A;
      }
      .ns-guide-card p {
        margin: 0 0 8px 0;
        font-size: 11.5px;
        color: #64748B;
        line-height: 1.4;
      }
      .ns-guide-pill-link {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: 11px;
        font-weight: 800;
        color: #6D28D9;
        background: #F3EFFF;
        padding: 4px 11px;
        border-radius: 999px;
        text-decoration: none;
        transition: background 0.15s ease;
      }
      .ns-guide-pill-link:hover { background: #EDE9FE; }
      .ns-guide-chevron {
        color: #334155;
        flex-shrink: 0;
      }
      .ns-still-help-card {
        margin-top: 2px;
        background: linear-gradient(135deg, #F3EFFF 0%, #EAE3FF 100%);
        border: 1px solid #DDD6FE;
        border-radius: 18px;
        padding: 11px 12px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
      }
      .ns-still-help-btn {
        background: linear-gradient(135deg, #6D28D9 0%, #5B21B6 100%);
        color: #FFFFFF;
        border: none;
        border-radius: 999px;
        padding: 9px 14px;
        font-size: 11.5px;
        font-weight: 800;
        display: inline-flex;
        align-items: center;
        gap: 5px;
        cursor: pointer;
        flex-shrink: 0;
        box-shadow: 0 6px 14px rgba(109, 40, 217, 0.25);
      }
      .ns-wa-btn {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #16A34A;
        color: #FFFFFF;
        text-decoration: none;
        padding: 12px 15px;
        border-radius: 16px;
        font-size: 12.5px;
        font-weight: 800;
        box-shadow: 0 6px 16px rgba(22, 163, 74, 0.22);
      }
      .ns-wa-topic {
        display: flex;
        align-items: center;
        justify-content: space-between;
        border: 1px solid #EBE6FF;
        background: #FFFFFF;
        color: #1E293B;
        text-decoration: none;
        padding: 10px 13px;
        border-radius: 14px;
        font-size: 12px;
        font-weight: 700;
      }
      .ns-wa-topic:hover { border-color: #86EFAC; background: #F0FDF4; }
      .ns-chat-box {
        display: flex;
        flex-direction: column;
        gap: 8px;
        min-height: 185px;
        max-height: 235px;
        overflow-y: auto;
        padding: 4px 2px;
      }
      .ns-msg {
        max-width: 82%;
        padding: 9px 12px;
        border-radius: 16px;
        font-size: 12.5px;
        line-height: 1.42;
        word-break: break-word;
      }
      .ns-msg.mine {
        align-self: flex-end;
        background: linear-gradient(135deg, #6D28D9 0%, #5B21B6 100%);
        color: #FFFFFF;
        border-bottom-right-radius: 4px;
      }
      .ns-msg.theirs {
        align-self: flex-start;
        background: #FFFFFF;
        color: #0F172A;
        border: 1px solid #E9E4FF;
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
        border-top: 1px solid #E9E4FF;
        padding-top: 10px;
        background: #F6F4FF;
      }
      .ns-chat-row {
        display: flex;
        gap: 6px;
        align-items: center;
      }
      .ns-chat-input {
        flex: 1;
        border: 1px solid #DDD6FE;
        background: #FFFFFF;
        color: #0F172A;
        border-radius: 14px;
        padding: 9px 12px;
        font-size: 16px;
        outline: none;
        width: 100%;
        box-sizing: border-box;
      }
      @media (min-width: 768px) {
        .ns-chat-input { font-size: 12.5px; }
      }
      .ns-chat-input:focus {
        border-color: #7C3AED;
        box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.12);
      }
      .ns-chat-send {
        background: linear-gradient(135deg, #6D28D9 0%, #5B21B6 100%);
        color: #FFFFFF;
        border: none;
        border-radius: 14px;
        padding: 10px 15px;
        font-size: 12.5px;
        font-weight: 800;
        cursor: pointer;
        flex-shrink: 0;
      }
      .ns-chat-send:hover { opacity: 0.94; }
    `;
    document.head.appendChild(style);
  }

  function switchTab(tabName) {
    activeTab = tabName;
    lastRenderedSignature = "";
    const drawer = document.getElementById("ns-help-drawer");
    if (drawer) {
      drawer.querySelectorAll(".ns-hc-tab").forEach(function (b) {
        b.classList.toggle("active", b.getAttribute("data-tab") === tabName);
      });
    }
    renderBody(true);
  }

  function createUI() {
    injectStyles();

    const launcher = document.createElement("button");
    launcher.id = "ns-help-launcher";
    launcher.type = "button";
    launcher.innerHTML = `
      <span class="ns-hc-dot"></span>
      <span>Help &amp; Support</span>
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
      <div class="ns-hc-top-wrap">
        <div class="ns-hc-header">
          <div class="ns-hc-title-wrap">
            <div class="ns-hc-brand-icon">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M18 6h-2c0-2.21-1.79-4-4-4S8 3.79 8 6H6c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm-6-2c1.1 0 2 .9 2 2h-4c0-1.1.9-2 2-2zm0 11c-1.66 0-3-1.34-3-3h2c0 .55.45 1 1 1s1-.45 1-1h2c0 1.66-1.34 3-3 3z"/></svg>
            </div>
            <div>
              <div style="font-size:15px;font-weight:900;color:#0F172A;line-height:1.15;">NaijaSale Support</div>
              <div style="font-size:11.5px;color:#16A34A;font-weight:700;margin-top:2px;">● Online • Replies fast</div>
            </div>
          </div>
          <button type="button" id="ns-hc-close" class="ns-hc-close-btn" aria-label="Close">&times;</button>
        </div>

        <div class="ns-hc-hero-card">
          <div class="ns-hc-hero-row">
            <div>
              <h3 class="ns-hc-hero-title">How can we help you?</h3>
              <p class="ns-hc-hero-sub">Find answers to common questions or get support from our team.</p>
            </div>
            <!-- Friendly Support Agent SVG Illustration -->
            <svg width="68" height="62" viewBox="0 0 80 72" fill="none" style="flex-shrink:0;">
              <rect x="6" y="10" width="22" height="16" rx="6" fill="#7C3AED"/>
              <circle cx="13" cy="18" r="1.8" fill="#FFFFFF"/>
              <circle cx="17" cy="18" r="1.8" fill="#FFFFFF"/>
              <circle cx="21" cy="18" r="1.8" fill="#FFFFFF"/>
              <circle cx="52" cy="30" r="14" fill="#6D4C41"/>
              <path d="M36 68 C36 53, 68 53, 68 68 Z" fill="#6D28D9"/>
              <path d="M38 28 C38 18, 66 18, 66 28" stroke="#4C1D95" stroke-width="4" stroke-linecap="round"/>
              <rect x="34" y="25" width="6" height="11" rx="3" fill="#7C3AED"/>
              <rect x="64" y="25" width="6" height="11" rx="3" fill="#7C3AED"/>
              <path d="M37 35 Q42 42 50 41" stroke="#312E81" stroke-width="2" stroke-linecap="round"/>
              <path d="M47 33 Q52 37 57 33" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round"/>
            </svg>
          </div>

          <div class="ns-hc-search-wrap">
            <span class="ns-hc-search-icon">
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/></svg>
            </span>
            <input type="text" id="ns-hc-search" class="ns-hc-search-input" placeholder="Search for help..." autocomplete="off" />
          </div>
        </div>
      </div>

      <div class="ns-hc-tabs-wrap">
        <div class="ns-hc-tabs">
          <button type="button" class="ns-hc-tab active" data-tab="directions">⚡ Quick Guide</button>
          <button type="button" class="ns-hc-tab" data-tab="chat">💬 Live Chat</button>
          <button type="button" class="ns-hc-tab" data-tab="whatsapp"><span style="color:#16A34A;">●</span> WhatsApp</button>
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

    drawer.querySelector("#ns-hc-search").addEventListener("input", function (e) {
      searchQuery = (e.target.value || "").trim().toLowerCase();
      if (activeTab !== "directions") {
        switchTab("directions");
      } else {
        renderBody(false);
      }
    });

    drawer.querySelectorAll(".ns-hc-tab").forEach(function (tabBtn) {
      tabBtn.addEventListener("click", function () {
        switchTab(tabBtn.getAttribute("data-tab"));
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
    const filtered = QUICK_GUIDE_ITEMS.filter(function (item) {
      if (!searchQuery) return true;
      return (
        item.title.toLowerCase().includes(searchQuery) ||
        item.desc.toLowerCase().includes(searchQuery)
      );
    });

    const cardsHtml = filtered.length
      ? filtered
          .map(function (item) {
            return `
              <div class="ns-guide-card">
                <div class="ns-guide-icon-box">${item.icon}</div>
                <div class="ns-guide-content">
                  <h4>${escapeHtml(item.title)}</h4>
                  <p>${escapeHtml(item.desc)}</p>
                  <a class="ns-guide-pill-link" href="${escapeHtml(item.href)}">${escapeHtml(item.cta)} &rarr;</a>
                </div>
                <a href="${escapeHtml(item.href)}" class="ns-guide-chevron" aria-label="${escapeHtml(item.title)}">
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>
                </a>
              </div>
            `;
          })
          .join("")
      : `<div style="text-align:center;font-size:12px;color:#64748B;padding:18px 8px;background:#FFFFFF;border-radius:16px;border:1px solid #EBE6FF;">No matching guide found. Tap <strong>Live Chat</strong> below to ask our team directly!</div>`;

    bodyEl.innerHTML = `
      ${cardsHtml}
      <div class="ns-still-help-card">
        <div style="display:flex;align-items:center;gap:10px;min-width:0;">
          <div class="ns-guide-icon-box" style="background:#FFFFFF;width:38px;height:38px;border-radius:12px;">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 18v-6a9 9 0 0 1 18 0v6"/><path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z"/></svg>
          </div>
          <div style="min-width:0;">
            <div style="font-size:12.5px;font-weight:800;color:#0F172A;">Still need help?</div>
            <div style="font-size:10.5px;color:#475569;line-height:1.35;">Chat with our support team for immediate assistance.</div>
          </div>
        </div>
        <button type="button" id="ns-still-live-chat-btn" class="ns-still-help-btn">
          <span>💬 Live Chat</span>
        </button>
      </div>
    `;

    const jumpBtn = bodyEl.querySelector("#ns-still-live-chat-btn");
    if (jumpBtn) {
      jumpBtn.addEventListener("click", function () {
        switchTab("chat");
      });
    }
  }

  function renderWhatsApp(bodyEl) {
    bodyEl.innerHTML = `
      <a class="ns-wa-btn" href="${buildWhatsAppUrl("General Support")}" target="_blank" rel="noopener">
        <span>Message WhatsApp (0812 263 5608)</span>
        <span>&rarr;</span>
      </a>
      <div style="font-size:11px;font-weight:800;color:#64748B;margin-top:2px;">Quick WhatsApp Topics:</div>
      <a class="ns-wa-topic" href="${buildWhatsAppUrl("Posting or approving my ad")}" target="_blank" rel="noopener"><span>Ad posting or review help</span><span>&rarr;</span></a>
      <a class="ns-wa-topic" href="${buildWhatsAppUrl("NIN / KYC seller verification")}" target="_blank" rel="noopener"><span>NIN / Seller badge help</span><span>&rarr;</span></a>
      <a class="ns-wa-topic" href="${buildWhatsAppUrl("Ad promotion / payment")}" target="_blank" rel="noopener"><span>Ad promotion &amp; payment</span><span>&rarr;</span></a>
      <a class="ns-wa-topic" href="${buildWhatsAppUrl("Reporting a suspicious listing or user")}" target="_blank" rel="noopener"><span>Report a safety concern</span><span>&rarr;</span></a>
    `;
  }

  function updateMessagesListOnly(containerEl, msgs, isStaffMode, visitorName) {
    const welcomeHtml = !isStaffMode
      ? `
        <div class="ns-msg theirs">
          <div>Hi ${escapeHtml(visitorName || "there")}! Ask us anything about buying, selling, or verification on NaijaSale.</div>
          <div class="ns-msg-meta">NaijaSale Support</div>
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
          <div style="font-size:10.5px;font-weight:800;letter-spacing:0.04em;color:#6D28D9;">LIVE CUSTOMER DESK</div>
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