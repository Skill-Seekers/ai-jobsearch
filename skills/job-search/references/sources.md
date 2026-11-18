# Source reference

**Prerequisite, outside this suite:** you connect the sources yourself (Apify for LinkedIn, Glassdoor and Dice; the Indeed connector). The suite creates no accounts and holds no credentials. Actors and limits change, so confirm an actor's input schema before every call. Notes below are from testing in 2026 and may be out of date.

## LinkedIn (Apify: `curious_coder/linkedin-jobs-scraper`)

- Input that worked: `{"urls": [...], "count": 25, "scrapeCompany": false}`; use 5 to 6 URLs per call. `scrapeCompany` may default to true and slows each row, so pass false.
- Classic URL filters such as `f_E` and `f_WT` may be converted into keywords by the actor, so do not rely on them to narrow results; `f_TPR` (date) and company terms are kept.
- The result limit is honored, but the run summary's item count can lag the dataset; count rows from the dataset.
- Output fields: `id, title, companyName, location, postedAt, applicantsCount, salary, seniorityLevel, employmentType, link, descriptionText`. The public search returns no work mode; the dashboard shows it blank rather than guessing.
- `jobsearch extract` strips tracking parameters from `link`; the job id stays in the path.
- Concurrency limits depend on your Apify plan; launch batches within the limit.
- Datasets are large (descriptions are most of it). Fetch with a field projection that leaves out the description, and read one description at a time.
- LinkedIn usually yields the most usable rows. Company-specific queries (`queries` prints them) find roles the general queries miss.

## Indeed (connector)

- Parameters: search text, location, country, job type. Run the config's searches in parallel.
- Yield is usually low and often reposts; still useful for salary data. Parse long-form dates ("September 09, 2026") before comparing to the window. Apply the sanity check in the skill (sequential ids, all rows outside the window, shortener URLs mean low confidence).
- Keep the `jk=` id in the link; it is how the same posting is recognised across runs.

## Glassdoor (Apify: `bebity/glassdoor-jobs-scraper`)

- Few usable rows. Its value is salary bands that LinkedIn leaves blank.

## Dice (Apify: `shahidirfan/Dice-Job-Scraper`)

- `posted_date` takes `all|24h|3d|7d|30d`. Often mostly third-party contract listings; low priority. Disabled in the example config.

## Google Jobs

- Free-plan actors returned sample data in testing. Treat any result as unusable unless real posting URLs and descriptions are present. Disabled in the example config.

## Employers that rarely appear on aggregators

List target employers that returned nothing, with their careers pages, in the summary. Do not imply coverage that did not happen.

## Dates and counts

Compare posted dates to the run date, computed in code. "200+ applicants" becomes 200; unknown becomes 0.
