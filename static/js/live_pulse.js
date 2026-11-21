(function () {
  if (window.__NAIJASALE_LIVE_PULSE_LOADED__) return;
  window.__NAIJASALE_LIVE_PULSE_LOADED__ = true;

  const PULSE_URL = "/api/live-pulse/";
  const POLL_INTERVAL_MS = 5000;
  let baseline = null;
  let pollTimer = null;

  function ensureToastContainer() {
    let container = document.getElementById("ns-live-toast-container");
    if (!container) {
      container = document.createElement("div");
      container.id = "ns-live-toast-container";
      container.style.cssText = [
        "position:fixed",
        "top:16px",
        "left:50%",
        "transform:translateX(-50%)",
        "z-index:99999",
        "display:flex",
        "flex-direction:column",
        "gap:10px",
        "width:min(92vw, 420px)",
        "pointer-events:none",
        "font-family:'Plus Jakarta Sans',system-ui,-apple-system,sans-serif"
      ].join(";");
      document.body.appendChild(container);
    }
    return container;
  }

  function showLiveToast({ badge, title, body, actionText, actionUrl, onAction, variant }) {
    const container = ensureToastContainer();
    const isDanger = variant === "danger";
    const card = document.createElement("div");
    card.style.cssText = [
      "pointer-events:auto",
      isDanger ? "background:#450A0A" : "background:#1E1B4B",
      "color:#FFFFFF",
      isDanger ? "border:1px solid rgba(248,113,113,0.55)" : "border:1px solid rgba(167,139,250,0.45)",
      "border-radius:16px",
      "padding:13px 15px",
      "box-shadow:0 14px 30px rgba(15,23,42,0.28)",
      "display:flex",
      "align-items:center",
      "justify-content:space-between",
      "gap:12px",
      "transition:all 0.25s ease",
      "opacity:0",
      "transform:translateY(-10px)"
    ].join(";");

    const left = document.createElement("div");
    left.style.cssText = "min-width:0;flex:1;";

    const badgeEl = document.createElement("div");
    badgeEl.textContent = badge;
    badgeEl.style.cssText = [
      "font-size:10px",
      "font-weight:800",
      "letter-spacing:0.6px",
      "text-transform:uppercase",
      isDanger ? "color:#FCA5A5" : "color:#FBBF24",
      "margin-bottom:2px"
    ].join(";");

    const titleEl = document.createElement("div");
    titleEl.textContent = title;
    titleEl.style.cssText =
      "font-size:13px;font-weight:800;color:#FFFFFF;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;";

    left.appendChild(badgeEl);
    left.appendChild(titleEl);

    if (body) {
      const bodyEl = document.createElement("div");
      bodyEl.textContent = body;
      bodyEl.style.cssText =
        "font-size:12px;color:#CBD5E1;margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;";
      left.appendChild(bodyEl);
    }

    const actions = document.createElement("div");
    actions.style.cssText = "display:flex;align-items:center;gap:8px;flex-shrink:0;";

    if (actionText) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.textContent = actionText;
      btn.style.cssText = [
        isDanger ? "background:#DC2626" : "background:#FF8A00",
        "color:#FFFFFF",
        "border:none",
        "border-radius:10px",
        "padding:7px 12px",
        "font-size:12px",
        "font-weight:800",
        "cursor:pointer",
        "white-space:nowrap"
      ].join(";");
      btn.addEventListener("click", function () {
        if (typeof onAction === "function") {
          onAction();
        } else if (actionUrl) {
          window.location.href = actionUrl;
        }
      });
      actions.appendChild(btn);
    }

    const closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.innerHTML = "&times;";
    closeBtn.setAttribute("aria-label", "Close notification");
    closeBtn.style.cssText =
      "background:transparent;border:none;color:#94A3B8;font-size:18px;line-height:1;cursor:pointer;padding:2px 4px;";
    closeBtn.addEventListener("click", function () {
      dismissToast(card);
    });
    actions.appendChild(closeBtn);

    card.appendChild(left);
    card.appendChild(actions);
    container.appendChild(card);

    requestAnimationFrame(function () {
      card.style.opacity = "1";
      card.style.transform = "translateY(0)";
    });

    setTimeout(function () {
      dismissToast(card);
    }, 10000);
  }

  function dismissToast(el) {
    if (!el || !el.parentNode) return;
    el.style.opacity = "0";
    el.style.transform = "translateY(-10px)";
    setTimeout(function () {
      if (el.parentNode) el.parentNode.removeChild(el);
    }, 250);
  }

  function updateDomBadges(data) {
    if (typeof data.unread_msg_count === "number") {
      document.querySelectorAll("[data-live-unread-messages]").forEach(function (el) {
        el.textContent = data.unread_msg_count > 0 ? data.unread_msg_count : "";
        el.style.display = data.unread_msg_count > 0 ? "" : "none";
      });
    }
  }

  async function checkPulse() {
    if (document.hidden) return;

    try {
      const res = await fetch(PULSE_URL, {
        headers: { "X-Requested-With": "XMLHttpRequest" },
        credentials: "same-origin"
      });
      if (!res.ok) return;
      const data = await res.json();

      if (!baseline) {
        baseline = data;
        return;
      }

      // 1. New listing went live on the marketplace
      if (
        data.latest_listing_id &&
        baseline.latest_listing_id &&
        data.latest_listing_id > baseline.latest_listing_id
      ) {
        const isHome = window.location.pathname === "/";
        showLiveToast({
          badge: "✨ New Ad Just Posted",
          title: data.latest_listing_title || "Fresh listing on Naijasale",
          body: isHome ? "Tap refresh to see the newest listings at the top." : "Tap to view this new item now.",
          actionText: isHome ? "Refresh" : "View",
          actionUrl: data.latest_listing_url || "/",
          onAction: isHome
            ? function () {
                window.location.reload();
              }
            : null
        });
      }

      // 2. Staff / Admin instant moderation queue alerts
      if (data.is_staff) {
        if (data.pending_ads_count > (baseline.pending_ads_count || 0)) {
          showLiveToast({
            badge: "🛡️ Moderation Alert",
            title: "New ad submitted for review",
            body: data.pending_ads_count + " pending ad(s) waiting in queue.",
            actionText: "Review",
            actionUrl: "/workspace/"
          });
        }
        if (data.pending_kyc_count > (baseline.pending_kyc_count || 0)) {
          showLiveToast({
            badge: "🪪 KYC Verification",
            title: "New seller NIN verification submitted",
            body: data.pending_kyc_count + " KYC request(s) pending.",
            actionText: "Inspect",
            actionUrl: "/workspace/"
          });
        }
        if (data.unresolved_reports_count > (baseline.unresolved_reports_count || 0)) {
          showLiveToast({
            badge: "⚠️ Safety Report",
            title: "New listing report submitted",
            body: data.unresolved_reports_count + " unresolved report(s).",
            actionText: "Open",
            actionUrl: "/workspace/"
          });
        }
      }

      // 3. Regular user alerts (messages, offers, ad approvals, ad rejections, CEO broadcasts)
      if (data.authenticated && !data.is_staff) {
        updateDomBadges(data);
        const isDashboard = window.location.pathname.startsWith("/dashboard");

        const isChatPage = window.location.pathname.startsWith("/chat/");
        if (!isChatPage && data.latest_msg_id && data.latest_msg_id > (baseline.latest_msg_id || 0)) {
          const isOffer = data.latest_msg_type === "offer";
          showLiveToast({
            badge: isOffer ? "🤝 New Price Offer" : "💬 New Message",
            title: (data.latest_msg_sender || "Someone") + (isOffer ? " sent an offer" : " messaged you"),
            body: data.latest_msg_text || "Tap to reply now",
            actionText: "Reply",
            actionUrl: data.latest_msg_url || "/inbox/"
          });
        }

        if (data.latest_notif_id && data.latest_notif_id > (baseline.latest_notif_id || 0)) {
          showLiveToast({
            badge: "📢 Official Naijasale Notice",
            title: data.latest_notif_title || "New announcement",
            body: data.latest_notif_message || "",
            actionText: "View",
            actionUrl: data.latest_notif_link || "/dashboard/"
          });
        }

        if (data.my_active_ads_count > (baseline.my_active_ads_count || 0)) {
          showLiveToast({
            badge: "🎉 Ad Approved & Live!",
            title: data.latest_my_approved_title || "Your ad is now live on Naijasale",
            body: "Buyers across Nigeria can now see and message you.",
            actionText: "View Ad",
            actionUrl: data.latest_my_approved_url || "/dashboard/"
          });
          if (isDashboard) {
            setTimeout(function () {
              window.location.reload();
            }, 1800);
          }
        }

        if (data.my_rejected_ads_count > (baseline.my_rejected_ads_count || 0)) {
          showLiveToast({
            variant: "danger",
            badge: "⚠️ Ad Needs Changes",
            title: (data.latest_my_rejected_title || "Your ad") + " was not approved",
            body: "Tap Edit to review feedback and update your listing.",
            actionText: "Edit Ad",
            actionUrl: data.latest_my_rejected_url || "/dashboard/"
          });
          if (isDashboard) {
            setTimeout(function () {
              window.location.reload();
            }, 2200);
          }
        }
      }

      baseline = data;
    } catch (err) {
      // Fail silently on temporary network drops
    }
  }

  function startPulse() {
    if (pollTimer) clearInterval(pollTimer);
    checkPulse();
    pollTimer = setInterval(checkPulse, POLL_INTERVAL_MS);
  }

  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) {
      checkPulse();
    }
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", startPulse);
  } else {
    startPulse();
  }
})();