#!/usr/bin/env python3
"""Generate a balanced weekly menu (Mon-Sun, lunch + dinner) from Meals.numbers.

Reads one sheet per category (Vegetables, Carbohydrates, Proteins, Legumes), each
with columns Meal / Ingredients / "Lunch or Dinner", and writes a .numbers file
with the days of the week as columns and Lunch/Dinner as rows.
"""

import argparse
import datetime as dt
import random
import re
import sys
from pathlib import Path

from numbers_parser import Document

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
SLOTS = ["Lunch", "Dinner"]

# (day, slot) -> meal that must always be served there.
FIXED = {
    ("Tuesday", "Dinner"): "American Eggs",
    ("Thursday", "Dinner"): "Ham & Cheese Rolls",
}

CATEGORIES = ["Vegetables", "Carbohydrates", "Proteins", "Legumes"]

# Weekly category quota. Sums to 7 lunches + 7 dinners. Legumes are lunch-only
# in practice, and dinners lean on Vegetables/Proteins because few
# Carbohydrates meals are marked as dinner.
QUOTA = {
    "Lunch": {"Carbohydrates": 3, "Proteins": 2, "Legumes": 1, "Vegetables": 1},
    "Dinner": {"Proteins": 3, "Vegetables": 3, "Carbohydrates": 1},
}

MEAT_WORDS = [
    "chicken", "beef", "steak", "pork", "ham", "sausage", "sausages", "mince",
    "bacon", "lamb", "veal", "turkey", "chorizo", "pancetta", "burger",
    "tenderloin", "meat", "bbq", "ragu",
]
FISH_WORDS = [
    "fish", "salmon", "tuna", "anchovies", "anchovy", "hake", "cod", "squid",
    "shrimp", "prawn", "clams", "mussels", "octopus", "sardine", "sea bass",
    "seafood", "gulas", "surimi", "trout", "sushi",
]

# Meals whose meat/fish keyword is only a garnish are handled by the
# "first 3 ingredients or in the name" rule below, not by an exception list.
PRIMARY_INGREDIENTS = 3

# Shopping-list aisles, checked in order; first keyword hit wins.
SECTIONS = [
    ("Fish & Seafood", [
        "salmon", "tuna", "anchovy", "anchovies", "hake", "cod", "squid",
        "shrimp", "prawn", "clam", "mussel", "octopus", "sardine", "sea bass",
        "seafood", "gulas", "surimi", "trout", "fish",
    ]),
    ("Meat", [
        "ham", "chicken", "beef", "steak", "pork", "sausage", "bacon", "mince",
        "burger", "tenderloin", "lamb", "veal", "turkey", "chorizo", "bbq",
    ]),
    ("Dairy & Eggs", [
        "milk", "cheese", "mozzarella", "mozarella", "mascarpone", "ricotta",
        "cream", "butter", "egg", "yoghurt", "yogurt", "béchamel", "bechamel",
    ]),
    ("Bakery & Pastry", [
        "bread", "breadcrumb", "pitta", "pastry", "tortilla", "roll", "dough",
        "crouton", "toast",
    ]),
    ("Produce", [
        "broccoli", "potato", "garlic", "onion", "tomato", "pumpkin", "zucchini",
        "spinach", "mushroom", "eggplant", "carrot", "pepper", "corn", "endive",
        "cucumber", "lemon", "orange", "lime", "pineapple", "cherry", "cherries",
        "avocado", "leek", "apple", "parsley", "cilantro", "ginger", "dill",
        "dell", "pea", "lettuce", "cabbage", "banana", "pear", "beet",
    ]),
    ("Pantry", [
        "rice", "pasta", "spaghetti", "noodle", "cannelloni", "lasagna",
        "gnocchi", "cous cous", "flour", "oil", "soy", "soja", "mustard",
        "honey", "vinegar", "salt", "sugar", "paprika", "cumin", "nutmeg",
        "sesame", "walnut", "cashew", "seed", "nut", "olive", "caper",
        "tabasco", "mayonnaise", "broth", "miso", "marmelade", "marmalade",
        "sauce", "rum", "yeast", "seaweed", "bean", "chickpea", "lentil",
        "raisin", "croquete", "empanadilla", "wine", "stock", "spice", "curry",
    ]),
]


def norm(text):
    return re.sub(r"\s+", " ", str(text or "")).strip()


def key(text):
    """Loose key for matching meal names across files."""
    return re.sub(r"[^a-z0-9]", "", str(text or "").lower())


class Meal:
    def __init__(self, name, ingredients, slot_text, category):
        self.name = norm(name)
        self.ingredients = norm(ingredients)
        self.category = category
        low = str(slot_text or "").lower()
        self.lunch = "lunch" in low
        self.dinner = "dinner" in low
        if not (self.lunch or self.dinner):  # unspecified -> usable anywhere
            self.lunch = self.dinner = True

        parts = [p.strip().lower() for p in self.ingredients.split(",") if p.strip()]
        head = " , ".join(parts[:PRIMARY_INGREDIENTS])
        name_low = self.name.lower()
        self.is_meat = self._match(MEAT_WORDS, name_low, head)
        self.is_fish = self._match(FISH_WORDS, name_low, head)

    @staticmethod
    def _match(words, name_low, head):
        return any(re.search(r"\b" + re.escape(w) + r"\b", name_low) or
                   re.search(r"\b" + re.escape(w) + r"\b", head) for w in words)

    def fits(self, slot):
        return self.lunch if slot == "Lunch" else self.dinner

    def main_ingredient(self):
        parts = [p.strip().lower() for p in self.ingredients.split(",") if p.strip()]
        return parts[0] if parts else ""

    def __repr__(self):
        return f"<{self.name} [{self.category}]>"


def load_meals(path):
    doc = Document(str(path))
    meals = []
    for sheet in doc.sheets:
        category = norm(sheet.name)
        for table in sheet.tables:
            rows = list(table.rows(values_only=True))
            if not rows:
                continue
            header = [str(c or "").strip().lower() for c in rows[0]]
            try:
                i_meal = next(i for i, h in enumerate(header) if h.startswith("meal"))
            except StopIteration:
                continue
            i_ing = next((i for i, h in enumerate(header) if "ingredient" in h), None)
            i_slot = next((i for i, h in enumerate(header)
                           if "lunch" in h or "dinner" in h), None)
            for row in rows[1:]:
                name = norm(row[i_meal] if i_meal < len(row) else "")
                if not name:
                    continue
                ing = row[i_ing] if i_ing is not None and i_ing < len(row) else ""
                slot = row[i_slot] if i_slot is not None and i_slot < len(row) else ""
                meals.append(Meal(name, ing, slot, category))
    return meals


def load_previous(folder, meals):
    """Return (set of meal keys to avoid, source file path or None)."""
    candidates = [p for p in Path(folder).iterdir()
                  if p.is_file() and p.name.lower().startswith("previous_menu")
                  and not p.name.startswith(".")]
    if not candidates:
        return set(), None
    src = sorted(candidates)[0]
    text_blobs = []
    if src.suffix.lower() == ".numbers":
        doc = Document(str(src))
        for sheet in doc.sheets:
            for table in sheet.tables:
                for row in table.rows(values_only=True):
                    text_blobs.extend(norm(c) for c in row if c is not None)
    else:
        raw = src.read_text(encoding="utf-8", errors="replace")
        for line in raw.splitlines():
            text_blobs.extend(norm(part) for part in re.split(r"[,;\t|]", line))

    # Strip day/slot labels so "Monday Lunch: Gnocchi" still matches "Gnocchi".
    label = re.compile(r"^\s*(" + "|".join(DAYS + SLOTS) + r")\b[\s:\-–]*", re.I)
    blobs = []
    for t in text_blobs:
        t = norm(t)
        prev = None
        while t and t != prev:
            prev, t = t, norm(label.sub("", t))
        if t:
            blobs.append(t)

    blob_keys = {key(b) for b in blobs}
    blobs_low = [b.lower() for b in blobs]
    avoid = set()
    for meal in meals:
        k = key(meal.name)
        if not k:
            continue
        if k in blob_keys:
            avoid.add(k)
            continue
        # Multi-word names are distinctive enough to look for inside free text;
        # single-word names ("Fish", "Soup") would match far too much.
        if len(meal.name.split()) >= 2:
            pattern = re.compile(r"\b" + re.escape(meal.name.lower()) + r"\b")
            if any(pattern.search(b) for b in blobs_low):
                avoid.add(k)
    # Fixed meals are exempt from the no-repeat rule.
    for fixed_name in FIXED.values():
        avoid.discard(key(fixed_name))
    return avoid, src


# Spelling variants in Meals.numbers that should buy the same thing.
INGREDIENT_ALIASES = {
    "mozarella": "mozzarella",
    "potatos": "potato",
    "potatoes": "potato",
    "tomatos": "tomato",
    "soja": "soy",
    "goat cheese": "goat cheese",
    "béchamel (milk)": "milk",
    "bechamel (milk)": "milk",
}

# Ingredients whose obvious keyword lands them in the wrong aisle.
SECTION_OVERRIDES = {
    "fried tomato": "Pantry",
    "corn flour": "Pantry",
    "canned beans": "Pantry",
    "sushi rice": "Pantry",
}


def section_for(ingredient):
    low = ingredient.lower()
    if low in SECTION_OVERRIDES:
        return SECTION_OVERRIDES[low]
    for name, words in SECTIONS:
        for w in words:
            if re.search(r"\b" + re.escape(w) + r"(s|es)?\b", low):
                return name
    return "Other"


def split_ingredients(meal):
    parts = re.split(r"[,\n]", meal.ingredients)
    return [norm(p) for p in parts if norm(p)]


def canonical_ingredients(meals):
    """Map each ingredient spelling to a canonical one, merging plurals that the
    data also spells in the singular (Potatos/Potato, Sausages/Sausage)."""
    forms = set()
    for meal in meals:
        forms.update(p.lower() for p in split_ingredients(meal))

    canon = {}
    for form in forms:
        target = INGREDIENT_ALIASES.get(form, form)
        if target == form:
            for candidate in (form[:-1], form[:-2],
                              form[:-3] + "o" if form.endswith("oes") else None):
                if candidate and candidate in forms:
                    target = candidate
                    break
        canon[form] = INGREDIENT_ALIASES.get(target, target)
    return canon


def build_shopping_list(menu, all_meals):
    canon = canonical_ingredients(all_meals)
    items = {}
    for (day, slot), meal in menu.items():
        for raw in split_ingredients(meal):
            base = canon.get(raw.lower(), raw.lower())
            entry = items.setdefault(base, {"label": base, "exact": False, "meals": []})
            # Prefer the spelling that matches the canonical form.
            if raw.lower() == base and not entry["exact"]:
                entry["label"], entry["exact"] = raw, True
            if meal.name not in entry["meals"]:
                entry["meals"].append(meal.name)

    order = {name: i for i, (name, _) in enumerate(SECTIONS)}
    order["Other"] = len(SECTIONS)
    rows = []
    for base, entry in items.items():
        # Keep the sheet's own spelling when it matches; otherwise the merged
        # form is bare lowercase and needs capitalising.
        label = entry["label"].strip() if entry["exact"] else base.title()
        label = label[0].upper() + label[1:] if label else label
        rows.append((section_for(base), label, entry["meals"]))
    rows.sort(key=lambda r: (order.get(r[0], 99), r[1].lower()))
    return rows


def build_slot_plan(rng):
    """Assign a category to each (day, slot), respecting the fixed dinners."""
    plan = {}
    lunch_cats = []
    for cat, n in QUOTA["Lunch"].items():
        lunch_cats += [cat] * n
    dinner_cats = []
    for cat, n in QUOTA["Dinner"].items():
        dinner_cats += [cat] * n

    # The two fixed dinners are Proteins; spend them from the dinner quota.
    for (day, slot), name in FIXED.items():
        plan[(day, slot)] = "Proteins"
        dinner_cats.remove("Proteins")

    free_dinners = [d for d in DAYS if (d, "Dinner") not in FIXED]
    rng.shuffle(dinner_cats)
    for day, cat in zip(free_dinners, dinner_cats):
        plan[(day, "Dinner")] = cat

    rng.shuffle(lunch_cats)
    for day, cat in zip(DAYS, lunch_cats):
        plan[(day, "Lunch")] = cat
    return plan


def attempt(meals, avoid, rng, relax_previous=False, relax_category=False):
    by_key = {key(m.name): m for m in meals}
    plan = build_slot_plan(rng)
    menu = {}
    used = set()

    for (day, slot), name in FIXED.items():
        meal = by_key.get(key(name))
        if meal is None:
            raise SystemExit(f"Fixed meal '{name}' not found in Meals.numbers")
        menu[(day, slot)] = meal
        used.add(key(name))

    order = [(d, s) for d in DAYS for s in SLOTS if (d, s) not in FIXED]
    rng.shuffle(order)

    for day, slot in order:
        cat = plan[(day, slot)]
        other = menu.get((day, "Dinner" if slot == "Lunch" else "Lunch"))

        def pool(categories, honour_previous):
            out = []
            for m in meals:
                if m.category not in categories or not m.fits(slot):
                    continue
                k = key(m.name)
                if k in used:
                    continue
                if honour_previous and k in avoid:
                    continue
                if other is not None:
                    if m.category == other.category:
                        continue
                    if m.main_ingredient() and m.main_ingredient() == other.main_ingredient():
                        continue
                out.append(m)
            return out

        choices = pool({cat}, True)
        if not choices and relax_previous:
            choices = pool({cat}, False)
        if not choices and relax_category:
            choices = pool(set(CATEGORIES), True) or pool(set(CATEGORIES), False)
        if not choices:
            return None
        pick = rng.choice(choices)
        menu[(day, slot)] = pick
        used.add(key(pick.name))

    meat_days = {d for d in DAYS if any(menu[(d, s)].is_meat for s in SLOTS)}
    fish_days = {d for d in DAYS if any(menu[(d, s)].is_fish for s in SLOTS)}
    if len(meat_days) < 2 or len(fish_days) < 2:
        return None
    return menu, sorted(meat_days, key=DAYS.index), sorted(fish_days, key=DAYS.index)


def generate(meals, avoid, rng, tries=4000):
    for relax_previous, relax_category in [(False, False), (True, False), (True, True)]:
        for _ in range(tries):
            res = attempt(meals, avoid, rng, relax_previous, relax_category)
            if res:
                return res + (relax_previous, relax_category)
    raise SystemExit("Could not build a menu satisfying the constraints.")


def fill_table(table, grid, header_cols=1):
    # delete_row/delete_column take a COUNT (trimmed from the end), not an index.
    n_rows, n_cols = len(grid), max(len(r) for r in grid)
    if table.num_rows > n_rows:
        table.delete_row(table.num_rows - n_rows)
    elif table.num_rows < n_rows:
        table.add_row(n_rows - table.num_rows)
    if table.num_cols > n_cols:
        table.delete_column(table.num_cols - n_cols)
    elif table.num_cols < n_cols:
        table.add_column(n_cols - table.num_cols)

    for r, row in enumerate(grid):
        for c, value in enumerate(row):
            table.write(r, c, value)

    table.num_header_rows = 1
    table.num_header_cols = header_cols


def write_numbers(menu, shopping, out_path):
    doc = Document()
    sheet = doc.sheets[0]
    sheet.name = "Weekly Menu"
    sheet.tables[0].name = "Weekly Menu"

    menu_grid = [[""] + DAYS]
    for slot in SLOTS:
        menu_grid.append([slot] + [menu[(d, slot)].name for d in DAYS])
    fill_table(sheet.tables[0], menu_grid)

    shop_grid = [["Section", "Ingredient", "Used in"]]
    for section, label, meals in shopping:
        shop_grid.append([section, label, ", ".join(meals)])
    doc.add_sheet("Shopping List", "Shopping List",
                  num_rows=len(shop_grid), num_cols=3)
    fill_table(doc.sheets[-1].tables[0], shop_grid, header_cols=0)

    doc.save(str(out_path))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--folder", default=".", help="folder holding Meals.numbers")
    ap.add_argument("--meals", default=None, help="path to Meals.numbers")
    ap.add_argument("--out", default=None, help="output .numbers path")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    folder = Path(args.folder).expanduser().resolve()
    meals_path = Path(args.meals).expanduser() if args.meals else folder / "Meals.numbers"
    if not meals_path.exists():
        raise SystemExit(f"Meals file not found: {meals_path}")

    rng = random.Random(args.seed)
    meals = load_meals(meals_path)
    avoid, prev_src = load_previous(folder, meals)

    menu, meat_days, fish_days, relaxed_prev, relaxed_cat = generate(meals, avoid, rng)

    if args.out:
        out_path = Path(args.out).expanduser()
    else:
        today = dt.date.today()
        monday = today + dt.timedelta(days=(7 - today.weekday()) % 7 or 7)
        out_path = folder / f"Menu_{monday.isoformat()}.numbers"
        n = 2
        while out_path.exists():
            out_path = folder / f"Menu_{monday.isoformat()}_{n}.numbers"
            n += 1

    shopping = build_shopping_list(menu, meals)
    write_numbers(menu, shopping, out_path)

    by_cat = {}
    for m in meals:
        by_cat[m.category] = by_cat.get(m.category, 0) + 1
    used_cats = ", ".join(f"{c} {by_cat.get(c, 0)}" for c in CATEGORIES)
    ignored = {c: n for c, n in by_cat.items() if c not in CATEGORIES}
    print(f"Meals loaded from {meals_path}: {used_cats}")
    if ignored:
        print("Sheets ignored (not menu categories): "
              + ", ".join(f"{c} {n}" for c, n in sorted(ignored.items())))
    if prev_src:
        print(f"Previous menu: {prev_src.name} ({len(avoid)} meals excluded)")
    else:
        print("Previous menu: none found (no previous_menu* file in folder)")
    if relaxed_prev:
        print("NOTE: no-repeat rule relaxed for some slots (pool exhausted).")
    if relaxed_cat:
        print("NOTE: category quota relaxed for some slots (pool exhausted).")
    print()
    for day in DAYS:
        for slot in SLOTS:
            m = menu[(day, slot)]
            tags = "".join(t for t in ("meat" if m.is_meat else "", "fish" if m.is_fish else "") if t)
            print(f"{day:<10} {slot:<7} {m.name:<45} [{m.category}]{' (' + tags + ')' if tags else ''}")
    counts = {}
    for m in menu.values():
        counts[m.category] = counts.get(m.category, 0) + 1
    print()
    print("Category balance:", ", ".join(f"{c}={counts.get(c, 0)}" for c in CATEGORIES))
    print(f"Meat days ({len(meat_days)}): {', '.join(meat_days)}")
    print(f"Fish days ({len(fish_days)}): {', '.join(fish_days)}")

    print(f"\nShopping list ({len(shopping)} ingredients):")
    current = None
    for section, label, used in shopping:
        if section != current:
            current = section
            print(f"  {section}:")
        print(f"    - {label}  ({len(used)} meal{'s' if len(used) > 1 else ''})")

    print(f"\nWritten: {out_path}")


if __name__ == "__main__":
    main()
