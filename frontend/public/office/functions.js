/* global CustomFunctions */
/*
 * GCI by CiteAlpha — Excel custom functions (=CITEALPHA.GCI and friends).
 * Runs in the shared runtime with taskpane.html, so both read the same saved key.
 * Every value comes from GET /api/v1/sheet, which returns the dossier's published level.
 */
(function () {
  "use strict";

  var KEY_STORAGE = "citealpha.apiKey";
  var MAX_BATCH = 50;
  var BATCH_DELAY_MS = 40;
  var CACHE_MS = 10 * 60 * 1000;
  var TIER_WORDS = { provisional: "Provisional", established: "Established", deep: "Deep" };

  var cache = {};
  var inflight = {};
  var queue = {};
  var timer = null;

  function sheetError(kind, message) {
    if (typeof CustomFunctions === "undefined") return new Error(message);
    var code = kind === "invalid" ? CustomFunctions.ErrorCode.invalidValue : CustomFunctions.ErrorCode.notAvailable;
    return new CustomFunctions.Error(code, message);
  }

  function getKey() {
    try {
      return window.localStorage.getItem(KEY_STORAGE) || "";
    } catch (e) {
      return "";
    }
  }

  function setKey(value) {
    window.localStorage.setItem(KEY_STORAGE, String(value || "").trim());
    cache = {};
  }

  function clearKey() {
    window.localStorage.removeItem(KEY_STORAGE);
    cache = {};
  }

  // Excel passes a date cell as its serial number (days since 30 Dec 1899).
  function normaliseDate(value) {
    if (value === null || value === undefined) return "";
    var s = String(value).trim();
    if (/^\d{5}(\.\d+)?$/.test(s)) {
      var ms = Date.UTC(1899, 11, 30) + Math.floor(Number(s)) * 86400000;
      return new Date(ms).toISOString().slice(0, 10);
    }
    return s;
  }

  function cacheKey(ticker, asOf) {
    return asOf + "|" + ticker.toUpperCase();
  }

  function httpFailure(status, body) {
    var detail = body && typeof body.detail === "string" ? body.detail : "";
    if (status === 401) return sheetError("na", "Add your CiteAlpha API key: Home, CiteAlpha, GCI key.");
    if (status === 403) return sheetError("na", detail || "This CiteAlpha key cannot read the API.");
    if (status === 429) {
      var wait = body && body.retry_after_sec ? body.retry_after_sec : 60;
      return sheetError("na", "CiteAlpha rate limit reached. Recalculate in " + wait + " seconds.");
    }
    if (status === 422) return sheetError("invalid", detail || "CiteAlpha could not read these arguments.");
    return sheetError("na", "CiteAlpha did not answer (HTTP " + status + ").");
  }

  function settle(waiters, outcome, isError) {
    waiters.forEach(function (w) {
      if (isError) w.reject(outcome);
      else w.resolve(outcome);
    });
  }

  function fetchBatch(asOf, tickers, waitersByTicker, key) {
    var url = window.location.origin + "/api/v1/sheet?tickers=" + encodeURIComponent(tickers.join(","));
    if (asOf) url += "&as_of=" + encodeURIComponent(asOf);
    return fetch(url, { headers: { "X-API-Key": key, Accept: "application/json" } })
      .then(function (res) {
        return res
          .json()
          .catch(function () {
            return null;
          })
          .then(function (body) {
            if (!res.ok) throw httpFailure(res.status, body);
            return body;
          });
      })
      .then(function (body) {
        var rows = (body && body.data && body.data.rows) || [];
        var byQuery = {};
        rows.forEach(function (row) {
          byQuery[String(row.query || "").toUpperCase()] = row;
        });
        tickers.forEach(function (t) {
          var row = byQuery[t.toUpperCase()];
          var waiters = waitersByTicker[t.toUpperCase()] || [];
          if (!row) {
            settle(waiters, sheetError("na", "CiteAlpha returned no row for " + t + "."), true);
            return;
          }
          cache[cacheKey(t, asOf)] = { at: Date.now(), row: row };
          settle(waiters, row, false);
        });
      })
      .catch(function (err) {
        var e = !err || err instanceof TypeError ? sheetError("na", "CiteAlpha could not be reached.") : err;
        tickers.forEach(function (t) {
          settle(waitersByTicker[t.toUpperCase()] || [], e, true);
        });
      })
      .then(function () {
        tickers.forEach(function (t) {
          delete inflight[cacheKey(t, asOf)];
        });
      });
  }

  function flush() {
    timer = null;
    var pending = queue;
    queue = {};
    var key = getKey();
    Object.keys(pending).forEach(function (asOf) {
      var waitersByTicker = pending[asOf];
      var tickers = Object.keys(waitersByTicker).map(function (upper) {
        return waitersByTicker[upper][0].ticker;
      });
      if (!key) {
        tickers.forEach(function (t) {
          settle(waitersByTicker[t.toUpperCase()], httpFailure(401, null), true);
          delete inflight[cacheKey(t, asOf)];
        });
        return;
      }
      for (var i = 0; i < tickers.length; i += MAX_BATCH) {
        fetchBatch(asOf, tickers.slice(i, i + MAX_BATCH), waitersByTicker, key);
      }
    });
  }

  function lookup(ticker, asOf, fresh) {
    var t = String(ticker === null || ticker === undefined ? "" : ticker).trim();
    if (!t) return Promise.reject(sheetError("invalid", "Give a ticker, e.g. \"INFY\"."));
    var day = normaliseDate(asOf);
    var k = cacheKey(t, day);
    var hit = cache[k];
    if (!fresh && hit && Date.now() - hit.at < CACHE_MS) return Promise.resolve(hit.row);
    if (!fresh && inflight[k]) return inflight[k];
    var p = new Promise(function (resolve, reject) {
      var group = queue[day] || (queue[day] = {});
      (group[t.toUpperCase()] || (group[t.toUpperCase()] = [])).push({ ticker: t, resolve: resolve, reject: reject });
      if (!timer) timer = setTimeout(flush, BATCH_DELAY_MS);
    });
    inflight[k] = p;
    return p;
  }

  function found(ticker, asOf) {
    return lookup(ticker, asOf).then(function (row) {
      if (!row.found) throw sheetError("invalid", "No listed company with ticker " + String(ticker).trim() + ".");
      return row;
    });
  }

  function noLevel(row) {
    return sheetError("na", "No published GCI. " + (row.coverage_reason || ""));
  }

  function gci(ticker, asOf) {
    return found(ticker, asOf).then(function (row) {
      if (row.gci === null || row.gci === undefined) throw noLevel(row);
      return row.gci;
    });
  }

  function tier(ticker, asOf) {
    return found(ticker, asOf).then(function (row) {
      if (!row.confidence_tier) throw noLevel(row);
      return TIER_WORDS[row.confidence_tier] || row.confidence_tier;
    });
  }

  function asof(ticker, asOf) {
    return found(ticker, asOf).then(function (row) {
      if (!row.as_of) throw noLevel(row);
      return row.as_of;
    });
  }

  function record(ticker) {
    return found(ticker, "").then(function (row) {
      return row.record || row.coverage_reason || "No published GCI yet.";
    });
  }

  function link(ticker) {
    return found(ticker, "").then(function (row) {
      return row.dossier_url;
    });
  }

  window.CiteAlphaSheet = { getKey: getKey, setKey: setKey, clearKey: clearKey, lookup: lookup };

  if (typeof CustomFunctions !== "undefined") {
    CustomFunctions.associate("GCI", gci);
    CustomFunctions.associate("TIER", tier);
    CustomFunctions.associate("ASOF", asof);
    CustomFunctions.associate("RECORD", record);
    CustomFunctions.associate("LINK", link);
  }
})();
