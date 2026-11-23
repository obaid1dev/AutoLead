"use strict";

const $ = (selector) => document.querySelector(selector);
const form = $("#search-form"), locationInput = $("#location"), categorySelect = $("#category");
const withoutWebsite = $("#only-without-website"), searchButton = $("#search-button"), statusEl = $("#status");
const resultsHeading = $("#results-heading"), tableWrap = $("#table-wrap"), tableBody = $("#results-body");
const emptyState = $("#empty-state"), emptyTitle = $("#empty-title"), emptyText = $("#empty-text");
const downloadButton = $("#download"), examples = $("#examples");
const SOCIAL_BASES = {
  "Facebook": "https://facebook.com/", "Instagram": "https://instagram.com/", "Twitter / X": "https://x.com/",
  "YouTube": "https://youtube.com/@", "LinkedIn": "https://linkedin.com/in/", "TikTok": "https://tiktok.com/@",
  "WhatsApp": "https://wa.me/", "Telegram": "https://t.me/", "Mastodon": "https://mastodon.social/@",
};
let results = [], lastLocation = "";

function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function link(href, text, className, external = false) {
  const anchor = el("a", className, text);
  anchor.href = href;
  if (external) Object.assign(anchor, { target: "_blank", rel: "noopener" });
  return anchor;
}
function td(content, className) {
  const node = el("td", className);
  if (content instanceof Node) node.append(content);
  else if (content) node.textContent = content;
  else node.append(el("span", "dash", "-"));
  return node;
}
function emailLink(address) {
  const anchor = el("a");
  anchor.href = `mailto:${address}`;
  const at = address.lastIndexOf("@");
  if (at > 0) anchor.append(document.createTextNode(address.slice(0, at + 1)), el("wbr"), document.createTextNode(address.slice(at + 1)));
  else anchor.textContent = address;
  return anchor;
}
function safeHttpUrl(value) {
  if (typeof value !== "string" || !value.trim()) return null;
  const text = value.trim();
  const candidate = /^https?:\/\//i.test(text) ? text : `https://${text.replace(/^\/+/, "")}`;
  try {
    const url = new URL(candidate);
    return /^https?:$/.test(url.protocol) ? url.href : null;
  } catch { return null; }
}
function socialHref(label, value) {
  const text = String(value).trim();
  const looksLikeUrl = /^(https?:\/\/|www\.)/i.test(text) || /^[\w.-]+\.[a-z]{2,}\//i.test(text);
  if (looksLikeUrl) return safeHttpUrl(text);
  const base = SOCIAL_BASES[label];
  if (!base) return null;
  const handle = text.replace(/^@/, "").replace(/^\/+/, "");
  if (!handle) return null;
  const encoded = label === "WhatsApp" ? handle.replace(/\D/g, "") : encodeURIComponent(handle);
  return encoded ? `${base}${encoded}` : null;
}
async function loadCategories() {
  try {
    const response = await fetch("/api/categories");
    if (!response.ok) return;
    for (const category of await response.json()) {
      if (category.key !== "all") categorySelect.add(new Option(category.label, category.key));
    }
  } catch {
    // The "All businesses" option still works without the category list.
  }
}
function setStatus(message, state = "") {
  statusEl.dataset.state = state;
  statusEl.replaceChildren();
  if (state === "loading") statusEl.append(el("span", "spinner"));
  statusEl.append(document.createTextNode(message));
}
function setBusy(busy) {
  searchButton.disabled = busy;
  searchButton.textContent = busy ? "Searching..." : "Search";
  form.setAttribute("aria-busy", String(busy));
}
function websiteFlag(business) {
  if (!business.has_website) return el("span", "flag flag-no", "No website");
  const href = safeHttpUrl(business.website);
  return href ? link(href, "Has website", "flag flag-yes", true) : el("span", "flag flag-yes", "Has website");
}
function shortPlace(displayName) {
  return displayName.split(",")[0].trim() || displayName;
}
function buildRow(business) {
  const row = el("tr");
  const name = td(link(business.osm_url, business.name, "row-name", true));
  if (business.description) {
    const description = el("p", "cell-note", business.description);
    description.title = business.description;
    name.append(description);
  }
  const phoneNumber = business.phone?.split(/[;,]/)[0].trim();
  const phone = phoneNumber ? link(`tel:${phoneNumber.replace(/[^\d+]/g, "")}`, business.phone) : null;
  const singlePhone = business.phone && !/[;,]/.test(business.phone);
  const emailAddress = business.email?.replace(/^mailto:/i, "");
  const email = emailAddress ? emailLink(emailAddress) : null;
  const address = td(business.address);
  if (business.opening_hours) {
    const hours = el("span", "cell-note", `Hours: ${business.opening_hours}`);
    hours.title = business.opening_hours;
    address.append(hours);
  }
  const socials = td(null);
  const socialLinks = Object.entries(business.socials || {}).map(([label, value]) => {
    const href = socialHref(label, value);
    return href ? link(href, label, "", true) : document.createTextNode(label);
  });
  if (socialLinks.length) {
    const wrap = el("div", "socials");
    wrap.append(...socialLinks);
    socials.replaceChildren(wrap);
  }
  row.append(
    name, td(business.category), td(phone, singlePhone ? "nowrap" : ""), td(email), address,
    td(websiteFlag(business)), socials, td(link("https://www.openstreetmap.org/copyright", "OpenStreetMap", "source", true)),
  );
  return row;
}
function renderResults(data) {
  results = data.results;
  lastLocation = shortPlace(data.location_resolved);
  resultsHeading.textContent = lastLocation;
  resultsHeading.title = data.location_resolved;
  const noun = data.count === 1 ? "business" : "businesses";
  const filter = withoutWebsite.checked ? "without a listed website" : "including those with a website";
  setStatus(data.count ? `${data.count} ${noun} ${filter}.` : "No businesses found.");
  downloadButton.disabled = data.count === 0;
  if (data.count === 0) {
    tableWrap.hidden = true;
    emptyState.hidden = false;
    emptyTitle.textContent = "No matches in this patch";
    emptyText.textContent = withoutWebsite.checked
      ? "No businesses without a website were found here. Turn the filter off to include every business, or try a wider category."
      : "Try a wider category, or a nearby larger town.";
    return;
  }
  const fragment = document.createDocumentFragment();
  for (const business of results) fragment.append(buildRow(business));
  tableBody.replaceChildren(fragment);
  tableWrap.scrollLeft = 0;
  tableWrap.scrollTop = 0;
  emptyState.hidden = true;
  tableWrap.hidden = false;
}
function showError(message) {
  results = [];
  resultsHeading.textContent = "Results";
  setStatus(message, "error");
  downloadButton.disabled = true;
  tableWrap.hidden = true;
  emptyState.hidden = false;
  emptyTitle.textContent = "Search failed";
  emptyText.textContent = "Check the place name, then try again.";
}
async function runSearch() {
  if (!form.reportValidity()) return;
  setBusy(true);
  setStatus("Searching OpenStreetMap...", "loading");
  tableWrap.hidden = true;
  emptyState.hidden = true;
  try {
    const response = await fetch("/api/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        location: locationInput.value.trim(),
        category: categorySelect.value,
        only_without_website: withoutWebsite.checked,
        limit: 200,
      }),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "Something went wrong. Try again.");
    renderResults(data);
  } catch (error) {
    showError(error instanceof Error ? error.message : "Something went wrong. Try again.");
  } finally {
    setBusy(false);
  }
}
function csvCell(value) {
  let text = String(value ?? "");
  if (/^[=@\t\r]/.test(text)) text = `'${text}`;
  return `"${text.replace(/"/g, '""')}"`;
}
function downloadCsv() {
  if (!results.length) return;
  const headers = ["Name", "Category", "Description", "Phone", "Email", "Address", "Opening hours", "Website", "Has website", "Socials", "OSM URL", "Source"];
  const rows = results.map((business) => [
    business.name, business.category, business.description, business.phone, business.email,
    business.address, business.opening_hours, business.website, business.has_website ? "Yes" : "No",
    Object.entries(business.socials || {}).map(([label, value]) => `${label}: ${value}`).join("; "),
    business.osm_url, "OpenStreetMap",
  ]);
  const csv = [headers, ...rows].map((row) => row.map(csvCell).join(",")).join("\r\n");
  const slug = lastLocation.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 60) || "search";
  const anchor = el("a");
  const url = URL.createObjectURL(new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8" }));
  Object.assign(anchor, { href: url, download: `autolead-${slug}-${new Date().toISOString().slice(0, 10)}.csv` });
  document.body.append(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

form.addEventListener("submit", (event) => {
  event.preventDefault();
  runSearch();
});
examples.addEventListener("click", (event) => {
  const button = event.target.closest("[data-example]");
  if (!button) return;
  locationInput.value = button.dataset.example;
  form.requestSubmit();
});
downloadButton.addEventListener("click", downloadCsv);
loadCategories();
