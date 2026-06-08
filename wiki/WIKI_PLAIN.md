# cirro-search — Plain English Guide

> For product managers, designers, and investors. No coding knowledge required.
> If a technical term appears, it is explained right away in plain language.

---

## Table of Contents

1. [What is cirro-search?](#1-what-is-cirro-search)
2. [The three things you can search for](#2-the-three-things-you-can-search-for)
3. [How the system is built (the three parts)](#3-how-the-system-is-built-the-three-parts)
4. [What happens when you type](#4-what-happens-when-you-type)
5. [What happens when you press Enter](#5-what-happens-when-you-press-enter)
6. [The search cards — what each one shows](#6-the-search-cards--what-each-one-shows)
7. [Relevance scoring — why some results appear first](#7-relevance-scoring--why-some-results-appear-first)
8. [The "show debug" panel — what it tells you](#8-the-show-debug-panel--what-it-tells-you)
9. [The detail page — what each section means](#9-the-detail-page--what-each-section-means)
10. [Recent searches — how it works](#10-recent-searches--how-it-works)
11. [Trending searches](#11-trending-searches)
12. [Match highlighting](#12-match-highlighting)
13. [The search pipeline — plain English](#13-the-search-pipeline--plain-english)
14. [How the data got there](#14-how-the-data-got-there)
15. [What the system does NOT do](#15-what-the-system-does-not-do)

---

## 1. What is cirro-search?

cirro-search is a search engine built specifically for aviation — airports, flights, and gates. You type something into a search box (a word, a code, a city name, or even a typo), and the system figures out what you're looking for and shows you the best matching results within milliseconds. It was built as a research project to test and prove out better search technology for the Cirrostrats iOS app, and to fix several known search problems in that app — for example, typing "las" should find Las Vegas airport, but the old system missed it. cirro-search fixes that and dozens of similar problems by using a more sophisticated search engine called Elasticsearch [a database specially designed to find things quickly in large collections of text] combined with smart aviation-specific logic built on top of it.

---

## 2. The three things you can search for

| Type | What it means | Real examples you can type |
|---|---|---|
| **Airport** | Any airport in the world — by its code, name, or city | `EWR`, `heathrow`, `charles de gaulle`, `cdg`, `denver`, `hong kong`, `KEWR`, `LFPG` |
| **Flight** | A specific scheduled flight by its airline code and number | `UA44`, `ba117`, `united 44`, `UAL44`, `delta 1`, `4433` |
| **Gate** | A departure gate at an airport | `C101`, `B7`, `A1`, `ewr c101` (gate C101 at Newark) |

You don't need to know which type you're looking for — cirro-search figures that out automatically.

---

## 3. How the system is built (the three parts)

Think of it as a business with three departments:

```
[You, the user]
      │
      │  You type in the search box
      ▼
[The website]           ← the part you see in your browser
  React application       The search box, the result cards, the
  at localhost:3000        debug panel, the detail page.
      │
      │  Your query is sent to the brain
      ▼
[The brain]             ← the server that processes your query
  FastAPI server          Figures out what you mean, expands your
  at port 8000            query, asks the filing cabinet, sorts results.
      │
      │  The brain asks the filing cabinet to find matching records
      ▼
[The filing cabinet]    ← where all the data is stored
  Elasticsearch           Contains 85,000+ airports, thousands of flights
  at port 9200            and gates. Organised for lightning-fast search.
```

**A simple analogy:** You go to a library (the website). You ask the librarian (the brain) for books about "heathrow." The librarian knows that "heathrow" means London Heathrow Airport (LHR), looks it up in the card catalogue (Elasticsearch — the filing cabinet), retrieves the right record, and hands it to you — all within 20 milliseconds.

---

## 4. What happens when you type

Let's follow the word "ua4" as you type it one letter at a time.

**1.** You type **"u"**
The system waits 200 milliseconds (about as long as a blink) to see if you're going to type more. It doesn't search yet.

**2.** You type **"ua"**
Again, a 200 millisecond wait begins. The previous wait is cancelled. No search yet.

**3.** You type **"ua4"** — and stop typing for 200ms
Now the system sends "ua4" to the brain as a *suggestion* request (different from a full search — faster, prioritises prefix matches like codes that start with "UA4").

**4.** The brain receives "ua4"
It cleans it up ("ua4" is already clean), then figures out what you're probably looking for. "ua4" starts with "UA" which is United Airlines' code — followed by "4" which looks like the beginning of a flight number. The brain expands this to also search for "UAL4" (United's other code used by pilots).

**5.** The filing cabinet is searched
It finds all flights whose codes start with "UA4", "UAL4", etc. — things like UA4, UA40, UA44, UA400, UA4433, and so on.

**6.** Results appear below the search box
You see suggestion cards for UA4, UA40, UA44, etc. These are shown immediately as you type — no need to press Enter.

---

## 5. What happens when you press Enter

Same example, but now with "ewr" (Newark Liberty International Airport's code):

**1.** You press Enter with "ewr" typed
The system immediately cancels any pending suggestion timer.

**2.** Smart check: "did we already find this?"
The system checks if it already loaded suggestion results while you were typing. If one of those results has the code "EWR" exactly — it uses that result right away, skipping a round-trip to the server. This makes Enter feel instant in the common case.

**3.** If no cached match — full search fires
The brain runs a more thorough search: `GET /api/v1/search?q=ewr`.

**4.** The brain recognises "EWR" as a 3-letter airport code (called an IATA code — the codes printed on boarding passes)
It narrows the search to airports only — no point looking through flights and gates.

**5.** Results come back sorted by relevance
Newark Liberty International Airport appears first because "EWR" is an exact match for its IATA code — the strongest possible signal.

**6.** The result cards appear
You see one or more airport cards below the search box.

---

## 6. The search cards — what each one shows

### Airport card

```
🇺🇸  EWR       Newark Liberty International Airport
     KEWR      Newark, US
               [iata] [searchable_text]
```

- **Flag emoji** — the country where the airport is. Generated automatically from the country code.
- **EWR** — the IATA code. This is the code on your boarding pass.
- **KEWR** — the ICAO code (smaller text below). Used by air traffic controllers and flight planning systems. Most passengers never need to know this.
- **Newark Liberty International Airport** — the full official name.
- **Newark, US** — city and country.
- **[iata] [searchable_text]** — green tags showing which parts of the airport's record matched your search query.

### Flight card

```
✈   UA44      United Airlines
               Flight 44
               [iata_flight]
```

- **✈** — flight type indicator.
- **UA44** — the IATA flight identifier (airline code + number).
- **United Airlines** — full airline name, looked up automatically from the 2-letter code "UA".
- **Flight 44** — the numeric flight number only (44).
- **[iata_flight]** — the field where the match was found.

### Gate card

```
▣   C101      EWR — Newark Liberty International Airport
               Newark
```

- **▣** — gate type indicator.
- **C101** — the gate identifier.
- **EWR — Newark Liberty International Airport** — which airport this gate belongs to.
- **Newark** — city.

---

## 7. Relevance scoring — why some results appear first

When cirro-search finds 10 results for your search, it has to decide which one to show first. It gives each result a score — like a points system — and sorts by score from highest to lowest. Here are the signals it uses and what they mean:

| Signal | What it means | Points awarded | Example |
|---|---|---|---|
| **Text relevance** | How closely the result's text matches your query, based on word frequency | Variable (from Elasticsearch) | Searching "newark" — airport with "newark" in its name scores higher |
| **Exact IATA code match** | You typed exactly the 3-letter airport code | +200 points | You typed "CDG" and this result's IATA code is "CDG" — perfect match |
| **Exact ICAO code match** | You typed exactly the 4-letter airport code | +200 points | You typed "LFPG" and this result is Paris CDG |
| **Exact flight code match** | You typed exactly the flight identifier | +200 points | You typed "UA44" and this result is United Airlines flight 44 |
| **Exact gate match** | You typed exactly the gate identifier | +200 points | You typed "C101" and this result is gate C101 |
| **Exact flight number match** | The number-only part of your query exactly matches | +100 points | You typed "44" and this flight's number is "44" |
| **Correct result type** | The result type matches what your query looks like | +50 points | Your query looks like a flight number, and this result is a flight |
| **Known alias match** | You used a recognised common name | +1000 points | You typed "heathrow" — the system knows this is London Heathrow Airport (LHR) and gives it the maximum possible boost |
| **Flight number digits match** | You typed just a number and it matches exactly | +75 points | You typed "4433" and this flight's number is "4433" |
| **Name or text match** | Your search term appears somewhere in the result's full text | +25 points | Searching "charles" — airports with "Charles" in their name get a small bonus |
| **Popularity boost** | This result has been selected many times before | Small variable bonus | A major airport like JFK gets a tiny extra boost because it's frequently searched |

The final score is the sum of all these signals. The alias boost (+1000) is intentionally much larger than all others combined — when you type a known name like "heathrow" or "newark", the system should be completely confident and return the right answer immediately.

---

## 8. The "show debug" panel — what it tells you

After a search, there's a small "show debug" button in the results area. Clicking it reveals a panel that explains exactly how the system processed your query. Here's what each row means:

| Row label | Technical name | What it actually means | Example |
|---|---|---|---|
| **Raw query** | Query | The exact text you typed, unchanged | "ua44" |
| **Understood as** | Query type | What kind of aviation thing the system thinks you're searching for | "Flight number (airline code + number, e.g. UA44, BA117)" |
| **Searched only** | Entity type filter | Whether the system narrowed the search to one category (airports, flights, or gates) | "flights — cirro-search was confident enough to narrow the search to one type" |
| **Alias recognised** | Alias | Whether your text matched a known common name | "heathrow" → resolved directly to London Heathrow Airport (LHR) |
| **Terms searched** | Expansions | All the different versions of your query that were searched simultaneously | "ua44 · UAL44 · GJS44 · UCA44 — cirro-search expanded to cover IATA/ICAO variants" |
| **Fallback triggered** | Fallback | Whether the system had to broaden its search | "No results with type filter — cirro-search retried across all types" |
| **Total time** | Pipeline time | How long the whole thing took from your keystroke to results on screen | "12 ms" |
| **Elasticsearch** | Provider time | How long the database search itself took | "8 ms — time inside the search engine" |
| **Pipeline overhead** | Python time | How long the non-database parts took (figuring out your query, sorting results) | "4 ms — query classification, ranking, alias lookup" |

The debug panel is designed for developers and product people who want to understand why a particular result appeared, or why the system interpreted a query in a certain way.

---

## 9. The detail page — what each section means

When you click any result card, you go to a full detail page. It has four sections:

### "What you searched" section

This explains how the system interpreted your query before it started searching. For example:

- **Query type** — "You typed a 3-letter airport code (IATA format). These are the codes you see on boarding passes — CDG for Paris, LHR for London Heathrow, JFK for New York."
- **Normalised to** — The cleaned-up version of what you typed (spaces removed, lowercased). Most of the time this is identical to what you typed.
- **Type filter applied** — Whether the system restricted results to one category. "cirro-search was confident your query refers to an airport, so it restricted results to that type only. This improves precision."
- **Alias resolved** — If you typed a well-known name, this shows what entity it was mapped to.
- **Search terms used** — All the variants that were searched. For a flight query "UA44", this might show "UA44 · UAL44 · GJS44 · UCA44 · SKW44" — cirro-search searched all of United's operating carriers at once.
- **Fallback triggered** — If the precise search found nothing, cirro-search retried with a broader search. This row explains that.

### "Why this result ranked here" section

This explains why this specific result appeared at the top (or wherever it appeared). For each ranking signal that applied, you see two lines:

- A **technical label** (for engineers): e.g. "Keyword field exact match on iata — boost +200"
- A **plain English explanation** (for everyone): e.g. "The 3-letter IATA code matched your query exactly. This is the strongest signal for airport lookups."

**Relevance score** at the top is the total number of points this result scored. Higher = more relevant.

### "Where in the document the match was found" section

When Elasticsearch finds a match, it tells us exactly which field of the record contained your query. This section shows those fields. For example:

- `iata` — your query matched the 3-letter code field exactly
- `searchable_text` — your query appeared somewhere in the combined name/city/alias text blob

### "Performance" section

Three timing measurements:

- **Total pipeline time** — end-to-end time from when the API call was made to when ranked results were returned. Typically 10–50ms.
- **Elasticsearch time** — time spent inside the database executing the search query. Typically 2–20ms.
- **Pipeline overhead** — the difference (total minus ES time) — time spent in Python doing classification, alias lookup, and re-ranking. Typically <10ms.

---

## 10. Recent searches — how it works

Every time you click on a result card, the system saves that result in your browser's **local storage** [a small private storage space on your own computer — like a sticky note that only your browser can read]. This information never leaves your computer and is never sent to any server.

Next time you open cirro-search, your recent results appear at the top of the page (before you type anything), so you can quickly get back to airports or flights you were looking at before.

Details about how recent searches work:
- **Up to 10 recent searches** are kept at a time. When you hit 10, the oldest one is removed to make room.
- **No duplicates** — if you search for EWR twice, it only appears once in recents (the most recent version).
- **Per-browser only** — if you open cirro-search on a different computer or in a different browser, you'll see a fresh empty recents list.
- **Remove any entry** — click the × button next to any recent item to remove it.

---

## 11. Trending searches

The system counts how many times each query has been searched since the server last started up. The most popular searches appear in the **Trending** section (visible on the home page before you type anything).

This counter is kept **in memory** [in the computer's working memory, not written to any permanent storage]. This means:
- It **resets every time the server restarts**. If the server is restarted (e.g. for a software update), all trending counts go back to zero.
- It **accumulates while the server is running**. The longer the server has been up and the more people have searched, the more accurate the trending list becomes.
- It is **not per-user** — it reflects total searches from everyone using the playground.

---

## 12. Match highlighting

When your search term appears inside a result's name or code, that part is shown in **bright blue**. For example:

- You search "EWR" → the letters "EWR" in the result's code are highlighted in blue
- You search "charles" → the word "Charles" in "Charles de Gaulle Airport" is highlighted

This highlighting works by finding the first occurrence of your search text anywhere inside the result's text, letter by letter. It handles unusual characters safely (like if you accidentally type a parenthesis or asterisk in your search) — it will still try to highlight, or simply show no highlight if there's no match.

---

## 13. The search pipeline — plain English

Think of the search pipeline as an **assembly line in a factory**. Your query is the raw material that enters at one end. At each station along the line, something is done to it before it moves to the next station. By the end, you have a finished product: sorted, relevant results.

**Station 1 — Cleaning (Normalisation)**

The first station cleans up your input. Extra spaces are removed. Multiple spaces between words collapse into one. Nothing else changes — the actual words are preserved exactly as you typed them. This is like a worker dusting off a raw part before it enters the machine.

*Example:* `"  ua  44 "` → `"ua  44"` (extra leading/trailing spaces removed)

**Station 2 — Classification**

This is the smart station. It looks at your cleaned query and figures out what *type* of thing you're searching for. It checks a series of rules in order:

1. Does it look like a 4-letter airport code starting with K or C (like KEWR or CYYZ)? → Airport
2. Does it start with a known airline code followed by numbers (like UA44 or BA117)? → Flight
3. Is it all digits (like 4433)? → Probably a flight number
4. Is it exactly 3 letters but not a known airline code (like EWR or CDG)? → Airport
5. Is it a letter followed by 1–4 digits (like C101 or B7)? → Gate
6. Does it say something like "united 44" (airline name + number)? → Flight
7. Does it have multiple words or is it a long word? → Text search
8. None of the above → Broad keyword search

*Example:* `"ua44"` → classified as **Flight** (UA = United Airlines, 44 = flight number)

**Station 3 — Expansion**

For flights, the system knows that the same flight can appear in the database under different codes (IATA and ICAO codes — two different coding systems used in aviation). It also knows that United Airlines flights can be operated by other airlines like GoJet or SkyWest. So it generates a list of all the code variations to search for simultaneously.

*Example:* `"ua44"` → generates search terms: `[ua44, UAL44, GJS44, UCA44, SKW44, RPA44, OO44]`

**Station 4 — Alias Check**

Before searching, the system checks if your query is a well-known name or phrase that maps directly to a specific entity. It has a list of about 50 such mappings: "heathrow" → London Heathrow, "ewr c101" → gate C101 at Newark, "united 4433" → flight UA4433.

If your query is on the list, the corresponding entity gets a massive score boost (+1000 points) to make sure it appears first.

**Station 5 — Search**

All the terms from the expansion step are sent to Elasticsearch simultaneously. Elasticsearch searches through 85,000+ airports, thousands of flights and gates, and returns matching records.

**Station 6 — Ranking**

The raw results come back from Elasticsearch in its own order (based on text similarity). The pipeline then applies the additional scoring signals (exact code match, type alignment, popularity, etc.) to re-sort the results into the final order you see.

**Total time: typically 10–50 milliseconds** — faster than the blink of an eye.

---

## 14. How the data got there

Before the search works, data has to be loaded into the filing cabinet. This process is called **seeding** — like planting seeds before a harvest.

cirro-search includes three types of data:

**Airports (~85,545 records)**
The full global airport database from a project called OurAirports, which publishes free, regularly updated data for every airport in the world. The dataset was filtered to include only large, medium, and small airports (excluding heliports, seaplane bases, and closed facilities). A script called `convert_airports.py` converts this raw data into the format cirro-search needs.

**Flights (synthetic)**
There is no free real-time flight database available, so the flight records are synthetic (artificially generated). A script creates flight records for about 35 major airlines, generating 59 different flight numbers for each (1–50 plus some specific numbers used for testing, like flight 4433). These flights are not real scheduled services — they're placeholder records designed to make the search logic testable.

**Gates (generated)**
Gate records are also generated automatically from the airport data. Large airports (like JFK, LAX, EWR) get 4 terminals (A, B, C, D) with gates 1–30. Terminal C also gets gate numbers 100–120, which covers the famous C101 demo case. Medium airports get 2 terminals with gates 1–15. Small airports get 1 terminal with gates 1–8.

**Aliases (hand-curated)**
The alias list — "heathrow" → London Heathrow, "newark" → EWR, "ewr c101" → gate C101 at Newark — was hand-written. It contains about 50 entries and covers the most common natural-language names that don't match the standard code formats.

To load all this data into Elasticsearch, you run one command: `python -m app.seed`. It reads the JSON files, converts each record into the right format, and bulk-uploads everything in one batch. On a standard laptop, this takes about 30–60 seconds.

---

## 15. What the system does NOT do

It's important to be honest about cirro-search's limitations:

**Trending resets when the server restarts**
The popularity counters are kept in the server's working memory, not saved to a file or database. Every time the server is restarted (for a software update, a crash, etc.), the trending list goes back to empty. This is fine for a research project but would need to be fixed for production use.

**No real-time flight data**
The flights in cirro-search are synthetic placeholder records, not real scheduled services. Searching "UA44" will find a United Airlines flight 44 record, but it won't tell you departure time, gate assignment, delays, or any live information. The system is designed to test search *logic*, not to provide flight information.

**Gate data is limited to demo airports**
Gates are only generated for airports with a popularity score above 50 (roughly medium and large airports). Small regional airports that fall below this threshold have no gate records in the system.

**No user accounts**
Recent searches are stored only in your own browser. There are no user accounts, no login, no cloud sync. If you open cirro-search in a different browser or on a different device, your recent searches won't be there.

**Analytics reset on restart**
Like trending, the analytics data (total searches, top queries, zero-result queries) is all in-memory. It gives useful insights while the server is running, but is lost on every restart.

**The search is a research tool, not a product**
cirro-search is a laboratory for validating search approaches and fixing known problems in Cirrostrats. It is not designed for end-user deployment as-is. It has no authentication, no rate limiting, no data privacy controls, and an open CORS policy (any website can call its API). These are intentional trade-offs for a development tool, not oversights.
