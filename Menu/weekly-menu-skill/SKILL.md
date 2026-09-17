---
name: weekly-menu
description: Build a balanced weekly meal plan (Monday-Sunday, lunch and dinner) from a Meals.numbers file, plus the shopping list of ingredients for that week, and write both to a .numbers file with days as columns and Lunch/Dinner as rows. Use when the user asks for a weekly menu, meal plan, "menú semanal", next week's meals, a grocery/shopping list, or wants to regenerate a menu avoiding last week's dishes.
---

# Weekly menu

Generates a week of meals from `Meals.numbers` and saves a `.numbers` file with
two sheets:

- **Weekly Menu** — days of the week as columns, Lunch and Dinner as rows.
- **Shopping List** — every ingredient the week needs, with columns
  `Section` / `Ingredient` / `Used in`.

## Input file

`Meals.numbers` has one sheet per category — **Vegetables, Carbohydrates,
Proteins, Legumes** — each with a table whose columns are:

| Meal | Ingredients | Lunch or Dinner |
|---|---|---|

`Lunch or Dinner` may say `Lunch`, `Dinner`, or both (on two lines) meaning the
meal works for either.

## Rules the menu must satisfy

1. **14 slots**: Monday–Sunday, lunch and dinner.
2. **Fixed slots** (never change, never excluded by the no-repeat rule):
   - Tuesday dinner → `American Eggs`
   - Thursday dinner → `Ham & Cheese Rolls`
3. **Balanced across categories.** Weekly quota, tuned to what the data supports
   (Legumes are lunch-only; very few Carbohydrates meals are dinner-eligible):
   - Lunches: 3 Carbohydrates, 2 Proteins, 1 Legumes, 1 Vegetables
   - Dinners: 3 Proteins (2 of them fixed), 3 Vegetables, 1 Carbohydrates
4. **At least 2 meat days and 2 fish days.** A day counts if either of its meals
   is meat- or fish-based — judged by the meal name or the first three
   ingredients, so a ham garnish on a broccoli dish does not make it a meat day.
5. **No meal repeats within the week**, lunch and dinner on the same day come
   from different categories, and they never share a main ingredient.
6. **No repeats from last week**: if the folder holds a file whose name starts
   with `previous_menu` (`.numbers`, `.csv`, `.txt`, `.md`), every meal in it is
   excluded — except the two fixed dinners.

## Shopping list

Built from the `Ingredients` column of the 14 chosen meals:

- **Deduplicated** — an ingredient used by several meals appears once, and the
  `Used in` column names the meals that need it.
- **Merged spellings** — plurals collapse onto the singular whenever the sheet
  also uses the singular (`Potatos`/`Potato`, `Eggs`/`Egg`), and known variants
  are unified through `INGREDIENT_ALIASES` (`Mozarella` → `Mozzarella`,
  `Soja` → `Soy`).
- **Grouped by aisle** — Fish & Seafood, Meat, Dairy & Eggs, Bakery & Pastry,
  Produce, Pantry, Other; in that order, alphabetical within each group.

No quantities: the source sheet does not record them, so the list is a
what-to-buy checklist, not amounts.

## How to run

```bash
python3 ~/.claude/skills/weekly-menu/scripts/generate_menu.py --folder "<folder with Meals.numbers>"
```

Options: `--meals PATH` (if the meals file is elsewhere), `--out PATH`
(default `Menu_<next-Monday>.numbers` in the folder, never overwriting an
existing file), `--seed N` for a reproducible menu.

The default folder is the current directory. The user's meals file normally
lives in `/Users/JC/Documents/JC/Job/Claude/Menu`.

Requires the `numbers-parser` package (`pip3 install numbers-parser`), which both
reads and writes `.numbers` files — no need to drive Numbers.app.

## After running

The script prints the full week, the category balance, which days count as meat
and fish, and the shopping list grouped by aisle. Relay the menu table and the
shopping list to the user, and mention the output path. If it printed a `NOTE:`
line, a pool ran dry (usually because `previous_menu` excluded too much) and a
rule was relaxed for some slots — say so explicitly.

If the user wants a different week, re-run with a different `--seed`. If they
want to swap one dish, edit the output file rather than regenerating the week.

## Adjusting the rules

Everything tunable sits at the top of `scripts/generate_menu.py`: `FIXED` for the
locked slots, `QUOTA` for the category balance, `MEAT_WORDS` / `FISH_WORDS` for
the meat and fish classification, and `SECTIONS`, `SECTION_OVERRIDES` and
`INGREDIENT_ALIASES` for the shopping list. Change those rather than the search
or grouping logic.
