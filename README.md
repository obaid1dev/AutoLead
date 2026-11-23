# AutoLead

Find local businesses without a website, with the contact details already listed in OpenStreetMap.

![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-3776AB?logo=python&logoColor=white)
![License: MIT](https://img.shields.io/badge/license-MIT-2f6b4f)

## What it does

AutoLead takes a place name, asks OpenStreetMap where that place is, and returns the businesses inside its boundary. By default it shows only businesses with no website on record, which makes it useful for finding local shops, clinics, and restaurants that may need a hand getting online.

It uses two free, keyless services: Nominatim for geocoding and the Overpass API for business data. There is no account, no API key, no database, and no paid plan.

- Search any city, town, neighborhood, district, or country-level place.
- Filter by nine business categories, or search them all at once.
- See phone, email, address, opening hours, descriptions, and social profiles where OSM has them.
- Toggle between businesses without a website and every business.
- Download the current result set as a CSV, generated in the browser.
- Link every business back to its OpenStreetMap record.
- Responsive, keyboard-friendly interface with light and dark themes.

## Demo

<img width="1366" height="1092" alt="fullpage_snapshot_localhost_2026-11-23-12-45-23" src="https://github.com/user-attachments/assets/c4186827-826a-4e14-b837-877023068620" />
<img width="1366" height="1355" alt="fullpage_snapshot_localhost_2026-11-23-12-46-44" src="https://github.com/user-attachments/assets/49228741-12bc-421f-8029-a2f8ab424f1f" />


## Quick start

**Requirements:** Python 3.11 or newer and git.

1. Clone the repository:

   ```bash
   git clone https://github.com/obaid1dev/AutoLead.git
   ```

2. Enter the project:

   ```bash
   cd AutoLead
   ```

3. Create and activate a virtual environment.

   macOS / Linux:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

   Windows (PowerShell):

   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Start the app:

   ```bash
   python run.py
   ```

6. Open [http://localhost:8000](http://localhost:8000).

## How to use

1. Type a place in **Location**. A city, town, neighborhood, or district works best. Country-level names work too, but can return a very large area.
2. Pick a **Category**, or leave it on **All businesses**.
3. Leave **Only businesses without a website** on if you want the default lead list. Turn it off to see every business OSM knows in the area.
4. Press **Search** or hit Enter.
5. Review the table. Names link to OpenStreetMap, phone numbers open your dialer, emails open your mail app, and social labels link to the profile where a URL or handle is available.
6. Press **Download CSV** to save the results you are looking at.

Example searches:

- `Lahore`, category **Restaurant**
- `Shoreditch, London`, category **All businesses**
- `Nicosia`, category **Restaurant**

The first search in a new area can take several seconds while Overpass gathers the data. Repeat searches are cached for ten minutes.

## Understanding the results

**Has website** means OpenStreetMap has a `website`, `contact:website`, or `url` tag for that business. **No website** means none of those tags exist. It does not prove the business has no website anywhere. A shop may have a Facebook page, a Google listing, or a site that nobody added to OSM.

**Contacts are often missing.** OpenStreetMap is built by volunteers. A phone number, email, or opening time only appears if someone mapped it. Missing contact details are common, especially outside well-mapped cities.

A business can appear with no name if it has no `name` tag, but AutoLead skips those because a nameless row is not actionable.

Results are deduplicated by name and rounded coordinates, then sorted with businesses that have a phone or email first, and alphabetically within each group.

Categories are grouped from OSM tags. For example, **Shops & retail** accepts any `shop=*` value and labels rows by their specific type, such as “Bakery” or “Electronics”. **Dentist & clinic** includes dentists, doctors, clinics, pharmacies, and anything tagged with `healthcare=*`. The search also includes a tourism clause so the **Hotel** category can find `tourism=hotel` and guest houses.

**A note on coverage:** a broad category in a large city can return hundreds of rows. AutoLead asks Overpass for the whole bounding box, then keeps the first 200 after sorting. Raise the `limit` field in the API request if you need more, up to 500.

## Data source and limits

AutoLead reads public data from:

- **Nominatim** for geocoding: `https://nominatim.openstreetmap.org/search`
- **Overpass API** for business search: `https://overpass-api.de/api/interpreter`

Both are community-run services with usage limits. AutoLead sends a descriptive User-Agent, spaces Nominatim calls at least one second apart, backs off and retries briefly when Overpass is at capacity, and caches identical searches for ten minutes. Please keep it that way if you deploy your own copy.

Coverage varies a lot by region. Some neighborhoods have rich, current records; others have almost nothing. Data can be outdated: a shop may have closed, moved, or added a website since it was mapped. Treat results as a starting point to verify, not a complete list of local businesses.

OpenStreetMap data is available under the [Open Database License (ODbL)](https://opendatacommons.org/licenses/odbl/). If you use or republish these results, keep the attribution: **© OpenStreetMap contributors**. The app shows it in the interface and in the CSV export.

This is a read-only tool: it does not create OSM notes or edit map data.

## Responsible use

This tool makes outreach easier, not automatic. Do not send unsolicited bulk email, automated texts, or spam. A business having a public phone number is not consent to marketing.

Follow the rules that apply to you, including GDPR and ePrivacy rules in Europe, CAN-SPAM in the United States, and local telemarketing and data-protection laws elsewhere. Keep records minimal, contact people about something genuinely relevant to their business, make it easy to opt out, and stop when asked.

No scraping of Google Maps, no paid data brokers, no hidden enrichment step.

## Project structure

```text
AutoLead/
├── app/
│   ├── __init__.py
│   ├── main.py          FastAPI app, routes, static mount
│   ├── geo.py           Nominatim geocoding, rate limit, bbox order
│   ├── overpass.py      Query building, API call, parsing, filtering
│   ├── models.py        Pydantic request and response models
│   ├── categories.py    Category labels and OSM tag filters
│   └── static/
│       ├── index.html
│       ├── styles.css
│       └── app.js
├── tests/
│   ├── test_geo.py
│   └── test_overpass.py
├── run.py
├── requirements.txt
├── README.md
└── LICENSE
```

Dependencies are intentionally small: FastAPI, Uvicorn, httpx, and pytest. There is no build step, no Node requirement, and no frontend framework. CSS variables for color, spacing, radius, and type live at the top of `app/static/styles.css` so the interface is easy to restyle.

## Running tests

```bash
pytest
```

The tests cover Nominatim bounding-box reordering, missing locations, Overpass query construction, tag mapping, duplicate merging, website filtering, sorting, and limits. They use fixed sample responses and never call the live APIs.

## Roadmap

- Add a second data source for regions where OpenStreetMap is thin.
- Export a whole search history, not just the current result set.
- Save lists of businesses and mark outreach progress.
- Show results on a small map preview.
- Add an optional command-line client.

Next project: Daelia, coming soon.

## Contributing

Fork the repository, create a short branch such as `fix/phone-parsing`, make the change, run `pytest`, and open a pull request with a clear description. Small, focused pull requests are easiest to review. Please keep the keyless, free-data constraint intact.

## License

MIT. See [LICENSE](LICENSE).

## Made by

Obaid
Email: [obaidd.dev@gmail.com](mailto:obaidd.dev@gmail.com)
Portfolio: [https://heyobaid.xyz](https://heyobaid.xyz)
GitHub: [https://github.com/obaid1dev](https://github.com/obaid1dev)
