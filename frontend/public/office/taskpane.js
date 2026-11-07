/* global Office */
(function () {
  "use strict";

  function el(id) {
    return document.getElementById(id);
  }

  function say(text) {
    el("status").textContent = text;
  }

  function init() {
    var sheet = window.CiteAlphaSheet;
    say(sheet.getKey() ? "A key is saved for this add-in on this device." : "No key saved yet.");

    el("save").addEventListener("click", function () {
      var value = el("key").value.trim();
      if (!value) {
        say("Paste a key first.");
        return;
      }
      sheet.setKey(value);
      el("key").value = "";
      say("Checking the key…");
      sheet.lookup("INFY", "", true).then(
        function (row) {
          if (row.gci === null || row.gci === undefined) {
            say("Key saved and accepted.");
            return;
          }
          say("Key works. " + row.name + ": GCI " + row.gci + ", data as of " + row.as_of + ".");
        },
        function (err) {
          say((err && err.message) || "The key could not be checked.");
        }
      );
    });

    el("clear").addEventListener("click", function (event) {
      event.preventDefault();
      sheet.clearKey();
      say("Key removed. GCI functions show #N/A until a key is saved.");
    });
  }

  if (typeof Office !== "undefined" && Office.onReady) {
    Office.onReady(init);
  } else {
    document.addEventListener("DOMContentLoaded", init);
  }
})();
