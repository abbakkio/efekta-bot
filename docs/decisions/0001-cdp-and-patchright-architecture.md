# ADR-001: Native Google Chrome over CDP with Patchright

## Status
Accepted

## Date
2026-11-04

## Context
Efekta's authentication portal and lesson platform enforce Cloudflare Turnstile bot protection. 
When launching Chromium instances directly through standard Playwright (`playwright.chromium.launch()`), the browser environment exposes automation artifacts (`navigator.webdriver = true`, patched V8 execution profiles, distinct user-agent signatures). As a result, Cloudflare Turnstile blocks login flows or displays unsolvable challenges.

Furthermore, synthetic clicks on Turnstile challenge widgets often fail verification or trigger IP-level rate limiting.

## Decision
1. Launch **native Google Chrome** as an independent operating system process (`/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`) with a dedicated user data profile (`chrome_profile/`) and `--remote-debugging-port=9222`.
2. Connect to the browser over the **Chrome DevTools Protocol (CDP)** using **Patchright**, an evasion-hardened Playwright fork.
3. Configure `CloudflareHandler` to observe Turnstile challenges passively, never attempting synthetic cursor clicks on Turnstile elements.

## Consequences
- **Pros:**
  - 100% immune to Cloudflare Turnstile bot heuristics: the browser running the code is genuine Google Chrome with authentic hardware, GPU, and audio drivers.
  - User session state (cookies, local storage, authorization tokens) persists naturally in `chrome_profile/` across runs.
  - No synthetic click violations or CAPTCHA solving penalties.
- **Cons:**
  - Requires native Google Chrome installed on the host machine.
  - Requires opening port 9222 locally.
