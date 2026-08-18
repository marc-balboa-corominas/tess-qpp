# HELDOUT guard

No HELDOUT synthetic dataset exists at F3B.1 freeze.

This directory intentionally contains only this guard document. HELDOUT noise,
periods, phases and flux arrays must not be generated or accessed before an
exact `FINAL_RULE_FREEZE`.

The held-out set is single-use. A failed held-out validation cannot be followed
by tuning and a second attempt on the same held-out identities.
