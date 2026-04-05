/*
  tracker.js — Shared Telemetry Core
  ====================================
  Drop this file into every template's  assets/js/  folder.
  Each template loads it with a plain <script> tag (NOT defer, NOT async)
  so window.PhishTracker is available immediately for template.js.

  REQUIRES: SESSION_ID, CAMPAIGN_ID, USER_ID declared as var (not const)
  in a <script> block BEFORE this file loads.
*/

(function () {
    "use strict";

    
    if (window.PhishTracker) return;

    /* ── Read globals declared in index.html ───────────────────── */
    var SID = (typeof SESSION_ID  !== "undefined" && SESSION_ID)  ? SESSION_ID  : "";
    var CID = (typeof CAMPAIGN_ID !== "undefined" && CAMPAIGN_ID) ? CAMPAIGN_ID : "";
    var UID = (typeof USER_ID     !== "undefined" && USER_ID)     ? USER_ID     : "";

    var TRACK_URL = "/track";

    if (!SID) {
        console.warn("[tracker.js] SESSION_ID is empty — tracking disabled.");
    }

    
    var startTime         = Date.now();
    var firstClickDone    = false;
    var lastActivity      = Date.now();
    var lastMouseLog      = 0;
    var lastMouseActivity = Date.now();  
    var lastKeyTime       = 0;
    var lastScrollLog     = 0;
    var idleSent          = false;
    var pageClosed        = false;       

    
    var _fieldLastKeyTime = {};
    var _fieldLastLength  = {};

 
    function buildPayload(eventType, data) {
        return JSON.stringify({
            session_id:  SID,
            campaign_id: CID,
            user_id:     UID,
            event:       eventType,
            timestamp:   Date.now() / 1000,
            data:        data || {}
        });
    }

    function sendEvent(eventType, data) {
        if (!SID) return;
        var payload = buildPayload(eventType, data);
        fetch(TRACK_URL, {
            method:    "POST",
            headers:   { "Content-Type": "application/json" },
            body:      payload,
            keepalive: true   
        }).catch(function () {});
    }

   
    function sendPageClose() {
        if (pageClosed) return;
        pageClosed = true;

        var payload = buildPayload("page_close", {});

        
        if (navigator.sendBeacon) {
            navigator.sendBeacon(TRACK_URL, payload);
        }

       
        try {
            fetch(TRACK_URL, {
                method:    "POST",
                headers:   { "Content-Type": "application/json" },
                body:      payload,
                keepalive: true
            });
        } catch (e) {}
    }

  
    window.addEventListener("load", function () {
        sendEvent("page_loaded");
        attachInputTrackers();
    });

   
    window.addEventListener("pagehide", function () {
        sendPageClose();
    });

    window.addEventListener("beforeunload", function () {
        sendPageClose();
    });

 
    document.addEventListener("mousedown", function () {
        lastMouseActivity = Date.now();
    });

    document.addEventListener("click", function (e) {
        lastMouseActivity = Date.now();
        if (!firstClickDone) {
            sendEvent("first_click", { delay: (Date.now() - startTime) / 1000 });
            firstClickDone = true;
        }
        sendEvent("click", {
            x:      e.clientX,
            y:      e.clientY,
            target: e.target.tagName || "",
            id:     e.target.id   || "",
            name:   e.target.name || ""
        });
        lastActivity = Date.now();
    });

    document.addEventListener("mousemove", function (e) {
        var now = Date.now();
        lastMouseActivity = now;
        if (now - lastMouseLog > 200) {
            sendEvent("mousemove", { x: e.clientX, y: e.clientY });
            lastMouseLog = now;
        }
        lastActivity = now;
    });


    window.addEventListener("scroll", function () {
        var now = Date.now();
        if (now - lastScrollLog > 500) {
            var depth = (window.scrollY / Math.max(document.body.scrollHeight, 1)) * 100;
            sendEvent("scroll", { depth: +depth.toFixed(2) });
            lastScrollLog = now;
        }
        lastActivity = now;
    });

  
    document.addEventListener("keydown", function (e) {
        var now = Date.now();
        sendEvent("keypress", {
            key:      e.key,
            interval: lastKeyTime ? (now - lastKeyTime) : 0
        });
        lastKeyTime  = now;
        lastActivity = now;
    });


    document.addEventListener("copy",  function () { sendEvent("copy",  {}); lastActivity = Date.now(); });
    document.addEventListener("paste", function () { sendEvent("paste", {}); lastActivity = Date.now(); });

    document.addEventListener("visibilitychange", function () {
        sendEvent(document.hidden ? "tab_hidden" : "tab_visible");
    });

    setInterval(function () {
        var idleTime = Date.now() - lastActivity;
        if (idleTime > 5000 && !idleSent) {
            sendEvent("idle", { duration: idleTime / 1000 });
            idleSent = true;
        }
        if (idleTime < 2000) idleSent = false;
    }, 2000);

    function attachInputTrackers() {
        var inputs = document.querySelectorAll("input, textarea, select");
        for (var i = 0; i < inputs.length; i++) {
            (function (input) {
                if (input._trackersAttached) return;
                input._trackersAttached = true;

                var fieldName = input.name || input.id || input.type || "field_" + i;

               
                input.addEventListener("input", function (e) {
                    sendEvent("input_change", { field: fieldName, length: e.target.value.length });
                    lastActivity = Date.now();
                });

                
                input.addEventListener("focus", function () {
                    var method = (Date.now() - lastMouseActivity < 500) ? "click" : "tab";
                    sendEvent("field_focus", { field: fieldName, method: method });
                    lastActivity = Date.now();
                });

                input.addEventListener("blur", function (e) {
                    sendEvent("field_blur", { field: fieldName, length: e.target.value.length });
                });

                
                input.addEventListener("keydown", function () {
                    _fieldLastKeyTime[fieldName] = Date.now();
                });

                _fieldLastLength[fieldName] = input.value.length;
            })(inputs[i]);
        }
    }

   
    setInterval(function () {
        var inputs = document.querySelectorAll("input, textarea");
        for (var i = 0; i < inputs.length; i++) {
            var input      = inputs[i];
            var fieldName  = input.name || input.id || input.type || "field_" + i;
            var curLen     = input.value.length;
            var prevLen    = _fieldLastLength[fieldName] || 0;
            var lastKey    = _fieldLastKeyTime[fieldName] || 0;
            var sinceKey   = Date.now() - lastKey;

            if (curLen > prevLen && sinceKey > 600) {
                sendEvent("autofill", {
                    field:  fieldName,
                    length: curLen,
                    source: curLen > 5 ? "password_manager_or_browser" : "browser_suggest"
                });
            }
            _fieldLastLength[fieldName] = curLen;
        }
    }, 500);

   
    document.addEventListener("submit", function (e) {
        sendEvent("form_submit", {
            form_id:   e.target.id   || "",
            form_name: e.target.name || "",
            method:    "native_submit"
        });
    }, true);

    
    window.PhishTracker = {
        sendEvent:           sendEvent,
        attachInputTrackers: attachInputTrackers
    };

})();
