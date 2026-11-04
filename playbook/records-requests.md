# Records requests (drafts only; Nick sends, nothing has been sent)

## OABCC: active alcohol license list (Nick, 2026-10-27: "Not now")

The Office of the Alcoholic Beverage Control Commissioner (oabcc.delaware.gov) publishes no licensee list or search. Its Facts & Figures
page says an active list is available on request. If Nick wants "Serves alcohol" in the app, this is the request; it goes from his own
address, and nothing is sent without his yes.

> To: the Office of the Alcoholic Beverage Control Commissioner (address from oabcc.delaware.gov's Facts & Figures / Contact page)
> Subject: Request for the current list of active on-premise alcohol licenses
>
> Hello,
>
> I build a free restaurant guide for Delaware (Delaware Eats, delaware.eatsranked.com). Your Facts & Figures page says a list of
> active licensees is available on request. Could you send the current list of active licenses, ideally as a spreadsheet with the
> licensee's trade name, premises address, license type and status? I'd use it only to show whether a restaurant holds an on-premise
> license, and I'd credit the OABCC as the source.
>
> Thank you,
> Nick Soderstrom
> nick@eatsranked.com

Once a list arrives: save it under `data/raw/official/oabcc/` (git-ignored), add a loader to `pipeline/official.py`, and match by trade
name at the premises address (the same agreement rules as DPH and Revenue). Until then the app shows "—" for alcohol.
