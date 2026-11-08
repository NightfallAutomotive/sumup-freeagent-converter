# Statement Bridge

Turn a [SumUp](https://www.sumup.com/) transactions export into a bank
statement CSV for FreeAgent, QuickBooks Online, Sage Accounting or Xero.

**Live tool: [sumupconvert.nightfalltools.co.uk](https://sumupconvert.nightfalltools.co.uk/)**

Everything runs in your browser. The file you choose is read into memory in
that tab and never uploaded; the page blocks all network requests with a
Content Security Policy, works offline, and stores nothing. Close the tab and
the data is gone.

## How it works

Set up a bank account called "SumUp" in your accounts software and import
the converted file into it. Each SumUp transaction becomes lines that bring that account back
to zero:

| Line | Amount | Explain it as |
|---|---|---|
| `SumUp sale <id> <description>` | + full sale | Sales income, or match to the invoice |
| `SumUp fee <id>` | − card fee | Bank charges or merchant fees |
| `SumUp held back from payout` | − amount kept back | Cash advance or loan repayment |
| `Transfer to bank <payout id>` | − payout | Transfer to your main bank account |

Failed and cancelled payments are skipped. Dates are `dd/mm/yyyy`, money in
is positive and money out negative, with no currency symbols or thousands
separators.

### Output formats

| Software | Layout | Notes |
|---|---|---|
| FreeAgent | `Date,Amount,Description`, no header row | [FreeAgent CSV format](https://support.freeagent.com/hc/en-gb/articles/115001222564-Format-a-CSV-file-to-upload-a-bank-statement) |
| QuickBooks Online | Header `Date,Description,Amount` (3-column) | Symbols such as `. , ( ) # :` are removed from descriptions, as [QuickBooks asks](https://quickbooks.intuit.com/learn-support/en-uk/help-article/bank-transactions/format-csv-files-excel-get-bank-transactions/L4BjLWckq_GB_en_GB). Choose the single Amount column and `dd/MM/yyyy` when uploading. |
| Sage Accounting | Header `Date,Description,Amount` (3-column template) | [Sage bank statement import](https://gb-kb.sage.com/portal/app/portlets/results/viewsolution.jsp?solutionid=222001000100087). Not Sage 50 desktop, which needs nominal codes. |
| Xero | Header `Date,Amount,Payee,Description,Reference` | Payee is `SumUp`; Reference is the SumUp transaction or payout ID. [Xero CSV import](https://help.xero.com/BankAccounts_Details_ImportTransCSV) |

### Money SumUp holds back

If you have a SumUp cash advance, SumUp keeps a percentage of each sale
before paying out. The page has a switch to turn these lines on or off, and a
percentage setting (15% by default):

- **Detailed export** (has `Transaction type` and `Payout ID` columns): SumUp's
  exact held-back amounts are used, and any sale that doesn't match your
  percentage is listed.
- **Shorter export** (has `Transaction code` and `Fee amount` columns): it
  doesn't say what was held back, so the percentage is used to work it out.

## Running it yourself

It's one HTML file with no build step and no dependencies. Download
`index.html` and open it in any browser.

There is also a command-line version for the detailed export (FreeAgent format only):

```sh
python3 sumup_to_freeagent.py transactions-report.csv
```

## Deploying

Deployed as a Cloudflare Workers static site from `wrangler.jsonc`. Files
listed in `.assetsignore` are not uploaded, including any `*.csv`, so a
SumUp export left in the folder can never be published. `_headers` sets the
same no-network Content Security Policy as the page.

## Disclaimer

An independent tool from Nightfall Automotive, not made by or affiliated with
SumUp or FreeAgent. Check the totals against your SumUp payouts before
reconciling, and ask your accountant if you're unsure how to explain a line.

## License

[MIT](LICENSE)
