// PROTOTYPE (issue #36) screenshot helper. Needs puppeteer-core and Chrome: npm i puppeteer-core@24 in a scratch dir.
// usage: node screenshot.mjs out.png "variant=A&place=Forum%20z17&chrome=off" [width height dpr]
import puppeteer from "puppeteer-core";
const [, , out, qs, w = 1280, h = 800, dpr = 1] = process.argv;
const browser = await puppeteer.launch({ executablePath: "/usr/bin/google-chrome", headless: true,
  args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"] });
const page = await browser.newPage();
const logs = [];
page.on("console", (m) => logs.push(`${m.type()}: ${m.text()} ${JSON.stringify(m.location())}`));
page.on("requestfailed", (r) => logs.push("reqfail " + r.url()));
page.on("response", (r) => { if (r.status() >= 400) logs.push(r.status() + " " + r.url()); });
page.on("pageerror", (e) => logs.push(`pageerror: ${e.message}`));
await page.setViewport({ width: +w, height: +h, deviceScaleFactor: +dpr });
await page.goto(`http://localhost:8036/?${qs}`, { waitUntil: "load" });
await page.waitForFunction(() => window.__map && window.__map.loaded() && window.__map.areTilesLoaded(), { timeout: 60000 }).catch(() => logs.push("timeout waiting for map"));
await new Promise((r) => setTimeout(r, 2500));
await page.screenshot({ path: out });
console.log(logs.filter((l) => !l.includes("favicon")).slice(0, 15).join("\n"));
await browser.close();
