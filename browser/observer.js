// browser/observer.js
(() => {
    console.log("🧭 Softlight DOM Observer initializing...");
  
    window._softlight_changed = false;
  
    function attachObserver() {
      const target = document.querySelector("body");
      if (!target) {
        console.warn("[Softlight] Body not found yet, retrying...");
        setTimeout(attachObserver, 1000);
        return;
      }
  
      const observer = new MutationObserver((mutations) => {
        const added = mutations.filter(m => m.addedNodes.length > 0).length;
        const removed = mutations.filter(m => m.removedNodes.length > 0).length;
        const attr = mutations.filter(m => m.attributeName).length;
  
        if (added || removed || attr) {
          window._softlight_changed = true;
          console.log(`[Softlight] DOM mutated (added:${added}, removed:${removed}, attr:${attr})`);
          clearTimeout(window._softlight_reset);
          window._softlight_reset = setTimeout(() => {
            window._softlight_changed = false;
          }, 1200);
        }
      });
  
      observer.observe(target, {
        childList: true,
        subtree: true,
        attributes: true,
        characterData: true,
      });
  
      console.log("[Softlight] Observer attached to <body>");
    }
  
    // Attach after small delay to let frameworks mount
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", attachObserver);
    } else {
      attachObserver();
    }
  })();
  