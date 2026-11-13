# QUEUE

Work not yet done, newest first. An item says what done looks like; only Warren marks one done.

## Q-1 — Questions whose answer needs a fact the question does not name (opened 2026-11-13)

Warren: "what are events where alice can join on friday. [data has alice is vegan]... i think i'm back to a
librarian decoding the results." Rearranging the question's vector cannot find "vegan": it is not in the question
(FINDINGS 2026-11-13, unmixing). The search's job here is to return every piece the librarian needs, and the
librarian's job is to decode them.

1. **Build the evaluation first.** About 15 DEV questions shaped like Alice's, each with a gold *set* of pieces.
   Measure recall of the set at k, and model calls spent. The current set (one gold file per question, MRR) cannot
   see this.
2. **Then compare, on that set, with a plan written first:** plain cosine; the librarian splitting the question
   before searching; the librarian searching, reading and searching again (IRCoT, self-ask); and Warren's
   projection: cosine, remove the best match's direction from the question and the data, cosine again (orthogonal
   matching pursuit).
3. **Separately, with its own plan:** the librarian records facts as relations when it files (Alice, diet, vegan;
   an event's date and food), so "Friday" is a calendar query, not a vector match. This changes what is filed, so it
   is a design question, not just a new arm.

*Done when:* the evaluation exists with its plan, and each option in 2 has a ledger line on it.
