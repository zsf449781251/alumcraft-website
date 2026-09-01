# Google Search Ads launch draft

Status: **planning and import files only**. No Google Ads account, budget, payment method, bid, or campaign has been configured by these files. Nothing in this folder can publish ads or spend money automatically.

## Objective and conversion

- Primary objective: qualified B2B inquiry submitted successfully through the website inquiry form.
- Primary Google event: `generate_lead`, dispatched from the site’s internal `alumcraft:inquiry-success` signal only after the server accepts the inquiry.
- Secondary observations: email and WhatsApp clicks. Keep these out of bidding until their lead quality is known.
- Do not send names, email addresses, company names, free-text project details, or other personal data to analytics or advertising platforms.

## Proposed campaign structure

| Campaign | Language | Market | Ad groups | Landing pages |
| --- | --- | --- | --- | --- |
| Search · EN · Custom Aluminum Blanks | English | Countries to be selected before launch; do not target “all countries” | CR80 Cards, Custom Shapes, Oversized Blanks, Round & Specialty | The four English product pages |
| Search · RO · Semifabricate Aluminiu | Romanian | Romania; confirm whether Moldova should be excluded or tested separately | Carduri CR80, Forme Personalizate, Formate Mari, Rotunde & Speciale | The four Romanian product pages under `/ro/` |
| Search · PL · Blanki Aluminiowe | Polish | Poland | Karty CR80, Kształty na Wymiar, Duże Formaty, Okrągłe & Specjalne | The four Polish product pages under `/pl/` |

Use Search Network only for the first controlled test. Keep search partners and Display expansion off until search-query quality and conversion tracking are verified. Start from the phrase and exact keywords in `google-search-keywords.csv`; do not enable broad match by default.

## Ad-group and landing-page map

| Product intent | EN landing page | RO landing page | PL landing page |
| --- | --- | --- | --- |
| CR80 aluminum card blanks | `https://yushialumcraft.coze.site/product-cr80-aluminum-cards.html` | `https://yushialumcraft.coze.site/ro/product-cr80-aluminum-cards.html` | `https://yushialumcraft.coze.site/pl/product-cr80-aluminum-cards.html` |
| Custom-shape blanks | `https://yushialumcraft.coze.site/product-custom-shape-blanks.html` | `https://yushialumcraft.coze.site/ro/product-custom-shape-blanks.html` | `https://yushialumcraft.coze.site/pl/product-custom-shape-blanks.html` |
| Oversized blanks | `https://yushialumcraft.coze.site/product-oversized-aluminum-blanks.html` | `https://yushialumcraft.coze.site/ro/product-oversized-aluminum-blanks.html` | `https://yushialumcraft.coze.site/pl/product-oversized-aluminum-blanks.html` |
| Round and specialty blanks | `https://yushialumcraft.coze.site/product-round-specialty-blanks.html` | `https://yushialumcraft.coze.site/ro/product-round-specialty-blanks.html` | `https://yushialumcraft.coze.site/pl/product-round-specialty-blanks.html` |

The ad copy intentionally emphasizes configurable size, outline, surface, edge details, holes/slots, and packaging. It does not claim certificates, production capacity, fixed lead times, prices, free samples, or a minimum order quantity.

## Import files

> **Safety-critical negative-keyword import:** `google-search-negative-keywords.csv` must be imported only through Google Ads Editor's dedicated **Campaign negative keywords** workflow. Never import it as an ordinary/positive keyword sheet. Map `campaign`, `negative_keyword`, and `negative_match_type` explicitly, then confirm every preview row is a campaign-level negative before applying the import.

- `google-search-keywords.csv`: phrase and exact keywords with product-specific final URLs. Every row has `status=Paused` and must remain paused through review.
- `google-search-negative-keywords.csv`: conservative campaign-level exclusions expanded to an explicit campaign on every row. Its deliberately negative-specific column names require explicit mapping in the dedicated flow above. Review the search-term report before adding more.
- `google-search-ads.csv`: one responsive search ad draft per language and product ad group. Each row has 8 headlines, 4 descriptions, and `status=Paused`.

Use UTF-8 when importing so Romanian and Polish diacritics remain intact. Google Ads Editor may require column-name mapping; map the semantic fields rather than renaming or dropping the localized text.

## Tracking setup

Recommended final URL suffix (configure in Google Ads, not by editing every URL):

```text
utm_source=google&utm_medium=cpc&utm_campaign={campaignid}&utm_term={keyword}&utm_content={creative}
```

Enable Google Ads auto-tagging so Google appends `gclid` automatically. Do not hand-build `gclid` in the suffix or treat it as a ValueTrack parameter.

Before launch:

1. Add the GA4 / Google tag ID to the site marketing configuration.
2. Confirm that the consent banner blocks analytics and advertising tags until the visitor grants the relevant consent.
3. Submit a test inquiry and verify exactly one successful lead event, with no personal data in the event payload.
4. Import the GA4 lead event into Google Ads or configure the equivalent Google Ads conversion action.
5. Keep email and WhatsApp clicks as secondary conversions until they are reconciled with real inquiries.

## Launch decisions still required

The owner must explicitly decide or approve all of the following in the advertising account before anything is enabled:

- English-language target countries and any excluded locations.
- Whether Romania and Poland are countrywide or limited to selected regions.
- Location option: people physically present in the target locations, rather than people merely interested in them.
- Account time zone and billing currency; these are difficult or impossible to change later.
- Daily and monthly spend limits, bid strategy, and any maximum cost-per-click guardrail.
- Ad schedule and the time zone used to answer inquiries.
- Billing profile, payment method, advertiser identity verification, tax information, and the person authorized to accept Google’s terms.
- Whether calls or other contact methods should become conversion actions.
- Final privacy/legal review for the target markets and any remarketing or audience use.

No budget is suggested in this draft because market scope, acceptable cost per qualified inquiry, currency, and billing authority have not yet been supplied. No payment information should be entered and no campaign should be switched to **Enabled** without the owner’s action-time approval.

## Safe staged rollout

1. Create all three campaigns as **Paused**.
2. Import the keyword, negative-keyword, and RSA drafts.
3. Verify language, country, URL, consent, and conversion settings.
4. Preview every ad and check that the correct localized landing page opens.
5. Launch one market at a time with an approved spend limit.
6. Review search terms frequently during the first weeks; add negatives for irrelevant consumer, design-template, equipment, employment, and educational searches.
7. Judge success by qualified inquiries, not clicks alone. Feed offline lead-quality outcomes back only after a privacy-safe process is agreed.

## Optional assets after account setup

- Sitelinks: the four product families in the campaign language.
- Callouts: Custom Sizes, Custom Surfaces, Edge Details, Holes & Slots, Packaging Options (localized per campaign).
- Structured snippet: Types — CR80 Cards, Custom Shapes, Oversized Blanks, Round Blanks.

Do not add certificate, capacity, guaranteed-delivery, price, discount, free-sample, or MOQ assets unless the business supplies verified terms and approves the exact wording.
