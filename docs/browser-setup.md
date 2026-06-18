# Browser setup: Local Network Access (required)

This is the most common reason a correctly configured agent still won't
work: **the browser is blocking the page from reaching `127.0.0.1`.**

## Why

To stop malicious sites from poking at devices on your network, Chrome
and Edge gate any request from a public/HTTPS origin to a loopback or
local address. This started as **Private Network Access (PNA)** and is
being replaced by **Local Network Access (LNA)**, which Chrome/Edge 142
enforce by default with a permission prompt. The agent already sends the
PNA response header, but LNA puts the final decision on the *client*, so
the operator (or IT) has to allow it.

Symptom: the agent runs fine (its tray icon is green, and
`http://127.0.0.1:8765/status` works when opened directly), but the web
app reports the scale/printer as unreachable, and the browser console
shows a failed `fetch` to `127.0.0.1`.

## Fixes, by deployment type

### 1. Single machine, right now (flag)

Open the flag and set it to **Disabled**:

- Chrome: `chrome://flags/#local-network-access-check`
- Edge:   `edge://flags/#local-network-access-check`

Set it to **Disabled** and restart the browser. (Leaving it at "Default"
will start blocking once it ships on-by-default.) This is a stopgap --
the flag goes away as LNA becomes standard.

### 2. When the browser prompts (Chrome/Edge 141+)

The browser shows a Local Network Access permission prompt for the site.
Choose **Allow**. You can review/change it later under the site's
permissions in browser settings.

### 3. Managed fleet (the durable, production fix)

For a store or warehouse with managed machines, deploy the enterprise
policy so the agent's web app is exempted fleet-wide -- no per-machine
flags or prompts:

- **Policy:** `LocalNetworkAccessAllowedForUrls`
  ("Allow sites to make network requests to local devices and local
  network endpoints"), supported by both Chrome Enterprise and Edge.
- Add your web app's origin (the `ALLOWED_ORIGIN` you set in `.env`) to
  the allowlist.
- Chrome registry path:
  `HKEY_LOCAL_MACHINE\SOFTWARE\Policies\Google\Chrome\LocalNetworkAccessAllowedForUrls`
  (Edge: the equivalent `...\Microsoft\Edge\...` path), or push it via
  Group Policy / your MDM.

This is the recommended setup for real deployments: it survives browser
updates and needs no operator action.

## References

- Chrome for Developers -- New permission prompt for Local Network Access:
  https://developer.chrome.com/blog/local-network-access
- Chrome Enterprise policy `LocalNetworkAccessAllowedForUrls`:
  https://chromeenterprise.google/policies/local-network-access-allowed-for-urls/
