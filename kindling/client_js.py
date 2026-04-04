"""Bundled LivePage browser runtime (vanilla JS)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kindling.request import Request
from kindling.response import Response

if TYPE_CHECKING:
    from kindling.app import Application

KINDLING_CLIENT_PATH = "/_kindling/client.js"

CLIENT_JS = r"""
(function () {
  function readConfig() {
    var el = document.getElementById("kindling-live-config");
    if (!el || !el.textContent) return null;
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      return null;
    }
  }

  function morphBody(html) {
    var doc = new DOMParser().parseFromString(html, "text/html");
    if (!doc || !doc.body) return;
    document.body.innerHTML = doc.body.innerHTML;
    var scripts = doc.body.querySelectorAll("script[src]");
    scripts.forEach(function (s) {
      var n = document.createElement("script");
      n.src = s.src;
      n.defer = true;
      document.body.appendChild(n);
    });
  }

  function postUrlEncoded(body) {
    return fetch(location.pathname + location.search, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "kindling-live",
      },
      body: body,
      credentials: "same-origin",
    }).then(function (r) {
      return r.text();
    });
  }

  function setupReactive(cfg) {
    if (!cfg || !cfg.reactiveUrl) return;
    try {
      var es = new EventSource(cfg.reactiveUrl);
      es.onmessage = function (ev) {
        var msg;
        try {
          msg = JSON.parse(ev.data);
        } catch (e) {
          return;
        }
        var binds = msg.binds || {};
        Object.keys(binds).forEach(function (sel) {
          var b = binds[sel];
          var el = document.querySelector(sel);
          if (!el || !b) return;
          if (b.mode === "text") el.textContent = String(b.value);
          else if (b.mode === "html") el.innerHTML = String(b.value);
          else
            el.textContent =
              typeof b.value === "string" ? b.value : JSON.stringify(b.value);
        });
        if (msg.live && Object.keys(msg.live).length) {
          window.dispatchEvent(
            new CustomEvent("kindling-live", { detail: msg.live })
          );
        }
      };
    } catch (e) {}
  }

  function attach(cfg) {
    if (!cfg) return;
    var bindings = cfg.bindings || {};
    setupReactive(cfg);

    document.addEventListener(
      "submit",
      function (e) {
        var form = e.target;
        if (!(form instanceof HTMLFormElement)) return;
        if (form.method.toLowerCase() !== "post") return;
        var actionUrl;
        try {
          actionUrl = new URL(form.getAttribute("action") || "", location.href);
        } catch (err) {
          return;
        }
        if (actionUrl.pathname !== location.pathname) return;

        if (form.id && bindings[form.id] && bindings[form.id].indexOf("submit") !== -1) {
          e.preventDefault();
          var params = new URLSearchParams(new FormData(form));
          params.set("kindling_target", form.id);
          params.set("kindling_event", "submit");
          postUrlEncoded(params.toString()).then(morphBody);
          return;
        }

        e.preventDefault();
        var params2 = new URLSearchParams(new FormData(form));
        postUrlEncoded(params2.toString()).then(morphBody);
      },
      true
    );

    document.addEventListener(
      "click",
      function (e) {
        var t = e.target;
        if (!t) return;

        var btn = t.closest && t.closest("[data-kindling-action]");
        if (btn) {
          e.preventDefault();
          var name = btn.getAttribute("data-kindling-action");
          if (name) postUrlEncoded("action=" + encodeURIComponent(name)).then(morphBody);
          return;
        }

        var n = t;
        while (n && n !== document) {
          if (n.id && bindings[n.id] && bindings[n.id].indexOf("click") !== -1) {
            e.preventDefault();
            postUrlEncoded(
              "kindling_target=" +
                encodeURIComponent(n.id) +
                "&kindling_event=click"
            ).then(morphBody);
            return;
          }
          n = n.parentElement;
        }
      },
      true
    );
  }

  attach(readConfig());
})();
""".strip()


def mount_kindling_client(app: Application) -> None:
    """Register GET /_kindling/client.js once per application."""
    if getattr(app, "_kindling_client_mounted", False):
        return
    app._kindling_client_mounted = True  # type: ignore[attr-defined]

    @app.get(KINDLING_CLIENT_PATH)
    def _kindling_client_js(_req: Request) -> Response:
        data = CLIENT_JS.encode("utf-8")
        return Response(
            status=200,
            headers=(
                ("Content-Type", "application/javascript; charset=utf-8"),
                ("Content-Length", str(len(data))),
            ),
            body=data,
        )
