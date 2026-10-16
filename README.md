# Customer list cleanup (demo)

A browser tool that cleans a customer spreadsheet saved as CSV and shows every change it made. It is a demo with made-up sample data.

Live: https://casimbahadar.github.io/data-cleanup/

## What it does

- Fixes extra spaces everywhere, and fixes capitalization in names and cities that are written in all capitals or all lower case. Names that already mix upper and lower case, such as DeSouza, are left alone. Email addresses are put in lower case, and ones that can't be real addresses are flagged.
- Writes provinces in whichever style the column mostly uses: codes (ON) or names (Ontario). It knows English and French names and common short forms like "ont." and "Qc".
- Formats Canadian phone numbers as 519-555-0142 and keeps extensions. Anything that isn't a valid 10-digit number is flagged, not guessed.
- Formats postal codes as A1A 1A1 and flags codes that break Canada Post's letter rules (no D, F, I, O, Q or U, and no W or Z as the first letter).
- Formats dates as YYYY-MM-DD, including dates written with English or French month names ("March 4, 2025", "4 mars 2025", "1er février 2024"). A date like 03/04/2025 could mean either day or month first, so it is flagged unless you tell the tool which order the file uses.
- Flags empty cells in the columns you mark as required. When a file has two columns of the same kind, such as two phone columns, a row only counts as missing if both are empty.
- Recognizes common export headers, including Shopify-style customer exports and French headers like Courriel, Ville and Code postal. Files saved by Excel on Windows (semicolons, Windows-1252 text) are read correctly.
- Lists possible duplicates for a person to confirm: rows that match exactly after cleanup, rows with the same email, and rows with the same phone number or postal code and a similar name. Nothing is merged unless you choose to.
- Logs every change with the row, column, value before, value after and the rule used.

Downloads: the clean CSV, the change log and the list of issues, all as CSV. The page also offers the sample file itself, so you can see the layout or edit it.

## Privacy

Everything runs in your browser. Files are read on your device and nothing is uploaded. The only outside request is for the Schibsted Grotesk font from Google Fonts.

## Sample data

60 fictional customers. Phone numbers are in the 555-01xx range, which is reserved for fiction, and email addresses use example.com, example.org and example.net. The sample has these problems planted in it, and the tool is tested to find exactly these and nothing else:

- 42 cells to fix: 14 spacing or capitalization, 9 phone numbers, 6 postal codes, 10 dates (2 with French month names), 3 provinces
- 17 cells for a person to check: 5 missing required values, 2 invalid emails, 2 invalid phone numbers, 4 invalid postal codes, 3 ambiguous dates, 1 date that doesn't exist
- 7 duplicate pairs: 3 exact and 4 near matches
- Look-alikes that must not be flagged: two people at the same address, two Smiths on the same street, and names already written correctly

## Files

- `index.html` is the whole tool. The CSS and JavaScript are inline and there is no build step.
- `.nojekyll` tells GitHub Pages to serve the files as they are.

Built by Casim Bahadar, Kitchener-Waterloo, Ontario. https://casimbahadar.github.io/
