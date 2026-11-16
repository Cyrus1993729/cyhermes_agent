# Oral meal logging: composite dishes and eaten-part boundaries

Use this when a user orally reports several dishes, specifies that only certain ingredients were eaten, or describes servings with informal units such as bowls/chopsticks.

## Preserve what was and was not eaten

- Parse the user's wording into separate dishes and components before logging. A dish title is not permission to count every ingredient in the pot.
- Explicit limits such as “only ate the garlic shoots and lotus root” override the dish name: log those parts, exclude the other components, and make the exclusion visible in the task/result.
- Keep similarly named items separate when the user distinguishes them (e.g. a hotpot containing assorted offal versus a separately reported stir-fried tripe dish). Never transfer the amount or contents of one dish to another.
- Unmentioned food is unknown, not zero. But do not silently assume it was consumed either. In particular, the name “soup/noodle soup/hotpot” does not prove the user drank the broth. If broth intake is unspecified and materially affects totals, label a stated working assumption and/or show a concise sensitivity case; do not present the assumption as observed fact.
- For a shared pot, count only the portion the user says they personally ate, not the whole pot or serving.

## Informal portion units

- Check the user's existing piece-weight/portion reference and recent archived meals for an applicable, documented calibration before converting bowls or chopsticks.
- Do not treat “one chopstickful” as a universal gram amount: leaves, sliced meat, and slippery offal have different geometry and packing. If there is no relevant calibration, give a clearly marked estimate/range, state its basis, and keep the uncertainty visible.
- A user-provided gram amount remains authoritative for that component. Do not override it using a model's visual or generic estimate.
- Do not ask the user to determine technical conversions such as grams per chopstick. Ask only for information they can directly know if the ambiguity changes the result; otherwise calculate a transparent estimate.

## Review before saving

Before returning the receipt, compare the original utterance against the logged line items: every explicit eaten item is included, every explicit exclusion is absent, and uncertain broth/condiments/oil are not silently promoted into observed facts. Re-read the saved file and verify the per-meal and daily sums, while preserving earlier meals and leaving the day open unless the user says eating is finished.
