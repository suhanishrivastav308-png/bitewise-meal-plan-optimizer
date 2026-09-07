import os
import re
import itertools
import numpy as np
import pandas as pd
from scipy.optimize import linprog


# ============================================================
# NUTRIBUDGET
# Smart nutrition. Smarter spending.
# ============================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

FOOD_FILE = os.path.join(DATA_DIR, "food_dataset.csv")
RECIPE_FILE = os.path.join(DATA_DIR, "recipes.csv")

os.makedirs(OUTPUT_DIR, exist_ok=True)

MEAL_TYPES = ["Breakfast", "Lunch", "Snack", "Dinner"]


# ============================================================
# REQUIRED COLUMNS
# ============================================================

FOOD_COLUMNS = [
    "Food", "Category", "Diet", "Meal_Type", "Cuisine",
    "Unit", "Price", "Calories", "Protein",
    "Carbs", "Fat", "Max_Quantity"
]

RECIPE_COLUMNS = [
    "Recipe_ID", "Recipe_Name", "Meal_Type",
    "Cuisine", "Diet", "Ingredients",
    "Preparation", "Prep_Time_Min"
]


# ============================================================
# NON-VEGETARIAN INGREDIENTS
# ============================================================

NON_VEG_WORDS = {
    "chicken", "mutton", "lamb", "beef", "pork",
    "fish", "prawn", "prawns", "shrimp", "crab",
    "seafood", "meat", "turkey", "bacon", "ham",
    "sausage", "egg", "eggs"
}


# ============================================================
# INGREDIENT ALIASES
# ============================================================

ALIASES = {
    "atta": "wheat flour",
    "wheat atta": "wheat flour",
    "whole wheat atta": "wheat flour",

    "aloo": "potato",
    "pyaz": "onion",
    "pyaaz": "onion",
    "tamatar": "tomato",
    "kheera": "cucumber",
    "palak": "spinach",
    "gobhi": "cauliflower",
    "phool gobhi": "cauliflower",
    "baingan": "brinjal",
    "bhindi": "okra",

    "methi": "fenugreek leaves",
    "methi leaves": "fenugreek leaves",

    "soya": "soybeans",
    "soya chunks": "soybeans",
    "soy chunks": "soybeans",
    "soybean": "soybeans",

    "moong dal": "lentils",
    "masoor dal": "lentils",
    "toor dal": "lentils",
    "dal": "lentils",

    "chana dal": "chickpeas",
    "kabuli chana": "chickpeas",
    "chole": "chickpeas",

    "rajma": "kidney beans",

    "besan": "gram flour",

    "dahi": "curd",
    "yogurt": "curd",

    "tel": "cooking oil",
    "oil": "cooking oil"
}


# ============================================================
# TEXT FUNCTIONS
# ============================================================

def normalize_text(value):

    if pd.isna(value):
        return ""

    text = str(value).lower().strip()
    text = text.replace("&", " and ")
    text = text.replace("-", " ")
    text = text.replace("_", " ")

    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def canonical_name(value):

    text = normalize_text(value)

    return ALIASES.get(text, text)


def contains_non_veg(value):

    words = set(
        normalize_text(value).split()
    )

    return any(
        word in words
        for word in NON_VEG_WORDS
    )


# ============================================================
# LOAD DATA
# ============================================================

def load_data():

    if not os.path.exists(FOOD_FILE):
        raise FileNotFoundError(
            f"food_dataset.csv not found at:\n{FOOD_FILE}"
        )

    if not os.path.exists(RECIPE_FILE):
        raise FileNotFoundError(
            f"recipes.csv not found at:\n{RECIPE_FILE}"
        )

    food = pd.read_csv(FOOD_FILE)
    recipes = pd.read_csv(RECIPE_FILE)

    food.columns = food.columns.str.strip()
    recipes.columns = recipes.columns.str.strip()

    missing_food = [
        x for x in FOOD_COLUMNS
        if x not in food.columns
    ]

    missing_recipe = [
        x for x in RECIPE_COLUMNS
        if x not in recipes.columns
    ]

    if missing_food:
        raise ValueError(
            f"Missing food columns: {missing_food}"
        )

    if missing_recipe:
        raise ValueError(
            f"Missing recipe columns: {missing_recipe}"
        )

    numeric_columns = [
        "Price",
        "Calories",
        "Protein",
        "Carbs",
        "Fat",
        "Max_Quantity"
    ]

    for column in numeric_columns:

        food[column] = pd.to_numeric(
            food[column],
            errors="coerce"
        ).fillna(0)

    recipes["Meal_Type"] = (
        recipes["Meal_Type"]
        .astype(str)
        .str.strip()
        .str.title()
    )

    return food, recipes


# ============================================================
# DIET FILTER
# ============================================================

def apply_diet_filter(food, recipes, diet):

    if diet.lower() == "vegetarian":

        food = food[
            ~food["Food"].apply(
                contains_non_veg
            )
        ].copy()

        recipes = recipes[
            ~recipes["Ingredients"]
            .fillna("")
            .apply(contains_non_veg)
        ].copy()

    return (
        food.reset_index(drop=True),
        recipes.reset_index(drop=True)
    )


# ============================================================
# PARSE INGREDIENTS
# ============================================================

def parse_ingredients(value):

    if pd.isna(value):
        return []

    text = str(value)

    text = text.replace("|", ",")
    text = text.replace(";", ",")

    parts = text.split(",")

    result = []

    for part in parts:

        part = part.strip()

        if not part:
            continue

        # Remove quantities
        part = re.sub(
            r"^\s*\d+(?:\.\d+)?\s*"
            r"(?:kg|g|grams?|ml|l|litres?|liters?|"
            r"cups?|tbsp|tablespoons?|tsp|teaspoons?|"
            r"pieces?|pcs|pinch)?\s*",
            "",
            part,
            flags=re.IGNORECASE
        )

        # Remove preparation words
        part = re.sub(
            r"\b(chopped|diced|sliced|minced|boiled|"
            r"grated|crushed|finely|roughly|fresh|"
            r"dry|dried|optional)\b",
            "",
            part,
            flags=re.IGNORECASE
        )

        part = re.sub(
            r"\s+",
            " ",
            part
        ).strip()

        if part:
            result.append(part)

    return result


# ============================================================
# MATCH RECIPE INGREDIENT TO FOOD DATASET
# ============================================================

def match_food(ingredient, food):

    ingredient_name = canonical_name(
        ingredient
    )

    if not ingredient_name:
        return None

    food_names = food["Food"].astype(str)

    # Exact match
    for index, name in food_names.items():

        if ingredient_name == canonical_name(name):
            return index

    # Containment match
    for index, name in food_names.items():

        food_name = canonical_name(name)

        if (
            ingredient_name in food_name
            or food_name in ingredient_name
        ):
            return index

    # Word overlap
    ingredient_words = set(
        ingredient_name.split()
    )

    best_index = None
    best_score = 0

    for index, name in food_names.items():

        food_words = set(
            canonical_name(name).split()
        )

        overlap = len(
            ingredient_words
            & food_words
        )

        if overlap > best_score:

            best_score = overlap
            best_index = index

    return best_index


# ============================================================
# STANDARD PORTION
# ============================================================

def standard_portion(food_name, category="", meal_type=""):
    name = str(food_name).lower()
    category = str(category).lower()

    # Cooking oil / ghee / butter
    if any(x in name for x in ["oil", "ghee", "butter"]):
        return 0.02

    # Rice, flour, oats and other grains
    if any(x in name for x in [
        "rice",
        "wheat flour",
        "atta",
        "maida",
        "flour",
        "oats",
        "poha"
    ]):
        return 0.08

    # Pulses, beans and protein-rich foods
    if any(x in name for x in [
        "soy",
        "soya",
        "lentil",
        "dal",
        "chickpea",
        "chana",
        "rajma",
        "kidney bean",
        "lobia",
        "paneer",
        "egg",
        "peanut"
    ]):
        return 0.07

    # Milk and curd
    if any(x in name for x in [
        "milk",
        "curd",
        "dahi",
        "yogurt"
    ]):
        return 0.15

    # Vegetables
    if category == "vegetable" or any(x in name for x in [
        "tomato",
        "onion",
        "potato",
        "spinach",
        "corn",
        "carrot",
        "cabbage",
        "cauliflower",
        "brinjal",
        "bhindi",
        "okra",
        "peas"
    ]):
        return 0.12

    # Fruits
    if category == "fruit":
        return 0.12

    # Default ingredient quantity
    return 0.06


# ============================================================
# CALCULATE RECIPE
# ============================================================

def calculate_recipe(recipe, food):

    ingredients = parse_ingredients(
        recipe["Ingredients"]
    )

    total_cost = 0
    total_calories = 0
    total_protein = 0

    matched = 0

    mapping = []

    for ingredient in ingredients:

        index = match_food(
            ingredient,
            food
        )

        if index is None:
            continue

        item = food.loc[index]

        portion = standard_portion(
            item["Food"],
            item["Category"]
        )

        cost = (
            float(item["Price"])
            * portion
        )

        calories = (
            float(item["Calories"])
            * portion
        )

        protein = (
            float(item["Protein"])
            * portion
        )

        total_cost += cost
        total_calories += calories
        total_protein += protein

        matched += 1

        mapping.append({
            "Recipe_ID": recipe["Recipe_ID"],
            "Recipe_Name": recipe["Recipe_Name"],
            "Meal_Type": recipe["Meal_Type"],
            "Recipe_Ingredient": ingredient,
            "Food_Item": item["Food"],
            "Quantity_kg": portion,
            "Ingredient_Cost": cost,
            "Ingredient_Calories": calories,
            "Ingredient_Protein": protein
        })

    match_ratio = (
        matched / len(ingredients)
        if ingredients
        else 0
    )

    return {
        "Recipe_ID": recipe["Recipe_ID"],
        "Recipe_Name": recipe["Recipe_Name"],
        "Meal_Type": recipe["Meal_Type"],
        "Cuisine": recipe["Cuisine"],
        "Diet": recipe["Diet"],
        "Preparation": recipe["Preparation"],
        "Prep_Time_Min": recipe["Prep_Time_Min"],
        "Recipe_Cost": total_cost,
        "Calories": total_calories,
        "Protein": total_protein,
        "Match_Ratio": match_ratio,
        "Mapping": mapping
    }


# ============================================================
# PREPARE ALL RECIPES
# ============================================================

def prepare_recipes(recipes, food):

    prepared = []
    mapping = []

    for _, recipe in recipes.iterrows():

        result = calculate_recipe(
            recipe,
            food
        )

        if (
            result["Match_Ratio"] >= 0.50
            and result["Recipe_Cost"] > 0
            and result["Calories"] > 0
        ):

            prepared.append(result)
            mapping.extend(
                result["Mapping"]
            )

    if not prepared:
        raise ValueError(
            "No usable recipes were found."
        )

    return (
        pd.DataFrame(prepared),
        pd.DataFrame(mapping)
    )


# ============================================================
# RECIPE FAMILY
# ============================================================

def recipe_family(row):

    text = (
        str(row["Recipe_Name"])
        + " "
        + str(row["Cuisine"])
    ).lower()

    if any(
        x in text
        for x in ["soya", "soy"]
    ):
        return "Soy"

    if any(
        x in text
        for x in [
            "dal",
            "lentil",
            "chickpea",
            "chana",
            "rajma",
            "bean",
            "lobia"
        ]
    ):
        return "Pulse"

    if any(
        x in text
        for x in [
            "paneer",
            "curd",
            "yogurt",
            "milk"
        ]
    ):
        return "Dairy"

    if any(
        x in text
        for x in [
            "egg",
            "chicken",
            "fish",
            "mutton"
        ]
    ):
        return "Animal Protein"

    if any(
        x in text
        for x in [
            "rice",
            "roti",
            "paratha",
            "poha",
            "upma",
            "oats",
            "bread",
            "khichdi"
        ]
    ):
        return "Grain"

    if any(
        x in text
        for x in [
            "vegetable",
            "aloo",
            "potato",
            "palak",
            "spinach",
            "gobi",
            "cauliflower",
            "bhindi"
        ]
    ):
        return "Vegetable"

    return "Other"


# ============================================================
# LINEAR PROGRAMMING
# ============================================================

def linear_programming_reference(
    recipes,
    daily_calories,
    daily_protein
):

    costs = recipes[
        "Recipe_Cost"
    ].values.astype(float)

    calories = recipes[
        "Calories"
    ].values.astype(float)

    protein = recipes[
        "Protein"
    ].values.astype(float)

    # Minimize cost
    objective = costs

    # Convert >= into <=
    constraints = np.vstack([
        -calories,
        -protein
    ])

    requirements = np.array([
        -daily_calories,
        -daily_protein
    ])

    bounds = [
        (0, 1)
        for _ in recipes.index
    ]

    result = linprog(
        objective,
        A_ub=constraints,
        b_ub=requirements,
        bounds=bounds,
        method="highs"
    )

    if result.success:

        return {
            "minimum_daily_cost":
                float(result.fun),
            "status":
                "Optimal LP reference found"
        }

    return {
        "minimum_daily_cost": None,
        "status":
            "LP reference could not find a solution"
    }


# ============================================================
# WEEKLY DIVERSITY SCORE
# ============================================================

def calculate_plan_score(
    combination,
    daily_calories,
    daily_protein,
    previous_recipe_counts,
    previous_families,
    remaining_budget
):

    total_calories = sum(
        x["Calories"]
        for x in combination
    )

    total_protein = sum(
        x["Protein"]
        for x in combination
    )

    total_cost = sum(
        x["Recipe_Cost"]
        for x in combination
    )

    families = [
        recipe_family(x)
        for x in combination
    ]

    family_count = len(
        set(families)
    )

    # --------------------------------------------------------
    # Nutrition
    # --------------------------------------------------------

    calorie_error = abs(
        total_calories
        - daily_calories
    ) / daily_calories

    if total_protein >= daily_protein:

        protein_error = 0

    else:

        protein_error = (
            daily_protein
            - total_protein
        ) / daily_protein

    # Avoid extremely high calorie plans
    if total_calories > daily_calories * 1.15:

        calorie_error += (
            total_calories
            - daily_calories * 1.15
        ) / daily_calories

    # --------------------------------------------------------
    # Recipe repetition
    # --------------------------------------------------------

    repetition_penalty = 0

    for recipe in combination:

        rid = str(
            recipe["Recipe_ID"]
        )

        repetition_penalty += (
            previous_recipe_counts.get(
                rid,
                0
            ) * 1.2
        )

    # --------------------------------------------------------
    # Family repetition
    # --------------------------------------------------------

    family_penalty = 0

    for family in families:

        family_penalty += (
            previous_families.get(
                family,
                0
            ) * 0.35
        )

    # --------------------------------------------------------
    # Soy penalty
    # --------------------------------------------------------

    soy_meals = sum(
        1
        for family in families
        if family == "Soy"
    )

    soy_penalty = soy_meals * 1.5

    # --------------------------------------------------------
    # Diversity reward
    # --------------------------------------------------------

    diversity_reward = (
        family_count * 1.0
    )

    # --------------------------------------------------------
    # Nutrition per rupee
    # --------------------------------------------------------

    calories_per_rupee = (
        total_calories
        / max(total_cost, 0.01)
    )

    protein_per_rupee = (
        total_protein
        / max(total_cost, 0.01)
    )

    value = (
        calories_per_rupee / 40
        + protein_per_rupee / 2
    )

    # --------------------------------------------------------
    # Cost pressure
    # --------------------------------------------------------

    cost_pressure = (
        total_cost
        / max(remaining_budget, 1)
    )

    # --------------------------------------------------------
    # Final score
    # LOWER = BETTER
    # --------------------------------------------------------

    score = (
        calorie_error * 8
        + protein_error * 10
        + repetition_penalty
        + family_penalty
        + soy_penalty
        + cost_pressure
        - diversity_reward
        - value
    )

    return score


def choose_daily_plan(
    recipe_groups,
    daily_calories,
    daily_protein,
    remaining_budget,
    previous_recipe_counts,
    previous_families
):
    """
    Fast meal-plan selection using beam search.

    Creates 4 different meals while trying to satisfy
    the user's calorie and protein requirements.
    """

    meal_calorie_target = daily_calories / 4

    candidate_lists = []

    MAX_CANDIDATES = 25
    BEAM_WIDTH = 40

    # --------------------------------------------------
    # 1. Create candidate pool for each meal
    # --------------------------------------------------

    for meal_type in MEAL_TYPES:

        group = recipe_groups[meal_type].copy()

        if group.empty:
            raise ValueError(
                f"No recipes available for {meal_type}."
            )

        # Nutrition value
        group["Value"] = (
            group["Calories"]
            + group["Protein"] * 10
        ) / group["Recipe_Cost"].clip(
            lower=0.01
        )

        # Difference from ideal calories for this meal
        group["CalorieGap"] = (
            group["Calories"]
            - meal_calorie_target
        ).abs()

        # --------------------------------------------------
        # Get candidates from several categories
        # --------------------------------------------------

        best_value = group.nlargest(
            12,
            "Value"
        )

        highest_protein = group.nlargest(
            12,
            "Protein"
        )

        calorie_match = group.nsmallest(
            12,
            "CalorieGap"
        )

        # Prefer reasonably priced recipes
        lowest_cost = group.nsmallest(
            12,
            "Recipe_Cost"
        )

        candidates = pd.concat([
            best_value,
            highest_protein,
            calorie_match,
            lowest_cost
        ]).drop_duplicates(
            subset=["Recipe_ID"]
        )

        # --------------------------------------------------
        # Keep soy from dominating
        # --------------------------------------------------

        non_soy = candidates[
            candidates["Family"] != "Soy"
        ]

        soy = candidates[
            candidates["Family"] == "Soy"
        ]

        candidates = pd.concat([
            non_soy,
            soy.head(5)
        ]).drop_duplicates(
            subset=["Recipe_ID"]
        )

        candidates = candidates.head(
            MAX_CANDIDATES
        )

        candidate_lists.append(
            candidates.to_dict("records")
        )

    # --------------------------------------------------
    # 2. Beam search
    # --------------------------------------------------

    beam = [{
        "recipes": [],
        "cost": 0.0,
        "calories": 0.0,
        "protein": 0.0,
        "families": [],
        "score": 0.0
    }]

    for meal_index, candidates in enumerate(
        candidate_lists
    ):

        new_states = []

        for state in beam:

            used_ids = {
                str(recipe["Recipe_ID"])
                for recipe in state["recipes"]
            }

            for recipe in candidates:

                recipe_id = str(
                    recipe["Recipe_ID"]
                )

                # No duplicate recipe in one day
                if recipe_id in used_ids:
                    continue

                recipe_cost = float(
                    recipe["Recipe_Cost"]
                )

                new_cost = (
                    state["cost"]
                    + recipe_cost
                )

                # --------------------------------------------------
                # IMPORTANT:
                # Don't reject too early based only on cost.
                # We only need the final plan to fit the budget.
                # --------------------------------------------------

                if new_cost > remaining_budget:
                    continue

                new_calories = (
                    state["calories"]
                    + float(recipe["Calories"])
                )

                new_protein = (
                    state["protein"]
                    + float(recipe["Protein"])
                )

                new_families = (
                    state["families"]
                    + [recipe["Family"]]
                )

                # --------------------------------------------------
                # Partial plan score
                # --------------------------------------------------

                target_calories = (
                    meal_calorie_target
                    * (meal_index + 1)
                )

                calorie_gap = abs(
                    new_calories
                    - target_calories
                )

                protein_deficit = max(
                    0,
                    daily_protein - new_protein
                )

                unique_families = len(
                    set(new_families)
                )

                family_repetition = (
                    len(new_families)
                    - unique_families
                )

                soy_count = sum(
                    1
                    for family in new_families
                    if family == "Soy"
                )

                previous_repetition = sum(
                    previous_recipe_counts.get(
                        str(r["Recipe_ID"]),
                        0
                    )
                    for r in state["recipes"]
                )

                score = (
                    calorie_gap * 0.5
                    + protein_deficit * 4
                    + family_repetition * 10
                    + soy_count * 5
                    + previous_repetition * 8
                    - unique_families * 8
                    + new_cost * 0.02
                )

                new_states.append({
                    "recipes": (
                        state["recipes"]
                        + [recipe]
                    ),
                    "cost": new_cost,
                    "calories": new_calories,
                    "protein": new_protein,
                    "families": new_families,
                    "score": score
                })

        if not new_states:
            raise ValueError(
                "Unable to create a meal plan within "
                "the selected weekly budget. "
                "Try increasing the budget slightly "
                "or lowering the nutrition requirements."
            )

        # Keep best partial plans
        new_states.sort(
            key=lambda x: x["score"]
        )

        beam = new_states[
            :BEAM_WIDTH
        ]

    # --------------------------------------------------
    # 3. Find feasible complete plans
    # --------------------------------------------------

    feasible_plans = []

    for state in beam:

        calories = state["calories"]
        protein = state["protein"]
        cost = state["cost"]

        # --------------------------------------------------
        # More flexible calorie requirement
        # --------------------------------------------------

        if calories < daily_calories * 0.75:
            continue

        if calories > daily_calories * 1.30:
            continue

        # Protein must still meet the user's minimum
        if protein < daily_protein:
            continue

        # Budget must never be exceeded
        if cost > remaining_budget:
            continue

        feasible_plans.append(state)

    # --------------------------------------------------
    # 4. If strict plans don't exist, choose the
    #    closest nutrition plan within budget.
    # --------------------------------------------------

    if not feasible_plans:

        closest_plan = None
        closest_score = float("inf")

        for state in beam:

            calories = state["calories"]
            protein = state["protein"]
            cost = state["cost"]

            if cost > remaining_budget:
                continue

            calorie_gap = abs(
                calories - daily_calories
            )

            protein_gap = max(
                0,
                daily_protein - protein
            )

            score = (
                calorie_gap
                + protein_gap * 10
            )

            if score < closest_score:
                closest_score = score
                closest_plan = state

        if closest_plan is not None:

            # Only accept the fallback if protein
            # is reasonably close to the target.
            if (
                closest_plan["protein"]
                >= daily_protein * 0.90
            ):

                feasible_plans = [
                    closest_plan
                ]

    # --------------------------------------------------
    # 5. Final check
    # --------------------------------------------------

    if not feasible_plans:
        raise ValueError(
            "Unable to create a feasible meal plan "
            "with the selected budget and nutrition "
            "requirements."
        )

    # --------------------------------------------------
    # 6. Final scoring
    # --------------------------------------------------

    best_plan = None
    best_score = float("inf")

    for state in feasible_plans:

        combination = state["recipes"]

        base_score = calculate_plan_score(
            combination,
            daily_calories,
            daily_protein,
            previous_recipe_counts,
            previous_families,
            remaining_budget
        )

        # --------------------------------------------------
        # Budget utilization
        # --------------------------------------------------

        utilization = (
            state["cost"]
            / max(remaining_budget, 1)
        )

        if utilization < 0.40:

            budget_penalty = (
                0.40 - utilization
            ) * 30

        elif utilization <= 0.85:

            budget_penalty = 0

        else:

            budget_penalty = (
                utilization - 0.85
            ) * 20

        # --------------------------------------------------
        # Diversity
        # --------------------------------------------------

        family_count = len(
            set(state["families"])
        )

        diversity_bonus = (
            family_count * 10
        )

        final_score = (
            base_score
            + budget_penalty
            - diversity_bonus
        )

        if final_score < best_score:

            best_score = final_score
            best_plan = combination

    if best_plan is None:
        raise ValueError(
            "Unable to select a suitable meal plan."
        )

    return list(best_plan)
# ============================================================
# GROCERY LIST
# ============================================================

def create_grocery_list(
    selected_recipes,
    mapping_df
):

    selected_ids = {
        str(x["Recipe_ID"])
        for x in selected_recipes
    }

    mapping = mapping_df[
        mapping_df["Recipe_ID"]
        .astype(str)
        .isin(selected_ids)
    ].copy()

    if mapping.empty:
        return pd.DataFrame()

    grocery = (
        mapping
        .groupby(
            "Food_Item",
            as_index=False
        )
        .agg({
            "Quantity_kg": "sum",
            "Ingredient_Cost": "sum",
            "Ingredient_Calories": "sum",
            "Ingredient_Protein": "sum"
        })
    )

    # --------------------------------------------------------
    # REALISTIC GROCERY PURCHASE QUANTITY
    # --------------------------------------------------------

    def purchase_quantity(quantity):

        if quantity <= 0:
            return 0.0

        if quantity <= 0.25:
            return 0.25

        elif quantity <= 0.50:
            return 0.50

        elif quantity <= 1.00:
            return 1.00

        elif quantity <= 1.50:
            return 1.50

        elif quantity <= 2.00:
            return 2.00

        else:
            return round(quantity * 2) / 2

    grocery["Purchase_Quantity_kg"] = (
        grocery["Quantity_kg"]
        .apply(purchase_quantity)
    )

    # --------------------------------------------------------
    # PRICE PER KG
    # --------------------------------------------------------

    grocery["Price_per_kg"] = (
        grocery["Ingredient_Cost"]
        / grocery["Quantity_kg"].replace(0, np.nan)
    ).fillna(0)

    # --------------------------------------------------------
    # ESTIMATED GROCERY PURCHASE COST
    # --------------------------------------------------------

    grocery["Estimated_Cost"] = (
        grocery["Purchase_Quantity_kg"]
        * grocery["Price_per_kg"]
    )

    # --------------------------------------------------------
    # RENAME NUTRITION COLUMNS
    # --------------------------------------------------------

    grocery = grocery.rename(
        columns={
            "Ingredient_Calories": "Calories",
            "Ingredient_Protein": "Protein"
        }
    )

    # --------------------------------------------------------
    # NUTRITION PER RUPEE
    # --------------------------------------------------------

    grocery["Calories_per_Rupee"] = (
        grocery["Calories"]
        / grocery["Estimated_Cost"].clip(lower=0.01)
    )

    grocery["Protein_per_Rupee"] = (
        grocery["Protein"]
        / grocery["Estimated_Cost"].clip(lower=0.01)
    )

    # --------------------------------------------------------
    # SORT
    # --------------------------------------------------------

    grocery = grocery.sort_values(
        "Estimated_Cost",
        ascending=False
    )

    return grocery.reset_index(
        drop=True
    )



# ============================================================
# MAIN OPTIMIZER
# ============================================================

def run_optimizer(
    weekly_budget,
    diet,
    daily_calories,
    daily_protein
):

    weekly_budget = float(
        weekly_budget
    )

    daily_calories = float(
        daily_calories
    )

    daily_protein = float(
        daily_protein
    )

    if weekly_budget <= 0:
        raise ValueError(
            "Weekly budget must be greater than zero."
        )

    food, recipes = load_data()

    # --------------------------------------------------------
    # Diet
    # --------------------------------------------------------

    food, recipes = apply_diet_filter(
        food,
        recipes,
        diet
    )

    # --------------------------------------------------------
    # Recipe calculations
    # --------------------------------------------------------

    prepared_recipes, mapping_df = (
        prepare_recipes(
            recipes,
            food
        )
    )

    prepared_recipes["Family"] = (
        prepared_recipes.apply(
            recipe_family,
            axis=1
        )
    )

    # --------------------------------------------------------
    # Check meal types
    # --------------------------------------------------------

    recipe_groups = {}

    for meal_type in MEAL_TYPES:

        group = prepared_recipes[
            prepared_recipes["Meal_Type"]
            == meal_type
        ].copy()

        if group.empty:

            raise ValueError(
                f"No recipes available for {meal_type}."
            )

        recipe_groups[
            meal_type
        ] = group

    # --------------------------------------------------------
    # LP reference
    # --------------------------------------------------------

    lp_result = linear_programming_reference(
        prepared_recipes,
        daily_calories,
        daily_protein
    )

    # --------------------------------------------------------
    # Build 7 days
    # --------------------------------------------------------

    remaining_budget = weekly_budget

    previous_recipe_counts = {}
    previous_families = {}

    all_meals = []
    daily_rows = []

    for day in range(1, 8):
        days_left = 8 - day
        daily_budget_limit = remaining_budget / days_left

        daily_plan = choose_daily_plan(
            recipe_groups,
            daily_calories,
            daily_protein,
            daily_budget_limit,
            previous_recipe_counts,
            previous_families
        )

        day_cost = sum(
            float(x["Recipe_Cost"])
            for x in daily_plan
        )

        day_calories = sum(
            float(x["Calories"])
            for x in daily_plan
        )

        day_protein = sum(
            float(x["Protein"])
            for x in daily_plan
        )

        remaining_budget -= day_cost

        for recipe in daily_plan:
            rid = str(recipe["Recipe_ID"])

            previous_recipe_counts[rid] = (
                previous_recipe_counts.get(rid, 0) + 1
            )

            family = recipe_family(recipe)

            previous_families[family] = (
                previous_families.get(family, 0) + 1
            )

            all_meals.append({
                "Day": f"Day {day}",
                "Meal_Type": recipe["Meal_Type"],
                "Recipe_ID": recipe["Recipe_ID"],
                "Recipe_Name": recipe["Recipe_Name"],
                "Cuisine": recipe["Cuisine"],
                "Family": family,
                "Cost": recipe["Recipe_Cost"],
                "Calories": recipe["Calories"],
                "Protein": recipe["Protein"],
                "Prep_Time_Min": recipe["Prep_Time_Min"]
            })

        daily_rows.append({
            "Day": f"Day {day}",
            "Calories": day_calories,
            "Protein": day_protein,
            "Cost": day_cost,
            "Calories_per_Rupee": day_calories / max(day_cost, 0.01),
            "Protein_per_Rupee": day_protein / max(day_cost, 0.01),
            "Remaining_Budget": remaining_budget
        })

    # --------------------------------------------------------
    

    # --------------------------------------------------------
    # DataFrames
    # --------------------------------------------------------

    weekly_plan_long = pd.DataFrame(
        all_meals
    )

    daily_nutrition = pd.DataFrame(
        daily_rows
    )

    # --------------------------------------------------------
    # Grocery list comes from EXACT meal plan
    # --------------------------------------------------------

    grocery_list = create_grocery_list(
        weekly_plan_long.to_dict("records"),
        mapping_df
    )

    if grocery_list.empty:

        raise ValueError(
            "Could not generate grocery list."
        )

    # --------------------------------------------------------
    # Total values
    # --------------------------------------------------------

    total_cost = float(
    weekly_plan_long["Cost"].sum()
 )


    total_calories = float(
        daily_nutrition["Calories"].sum()
    )

    total_protein = float(
        daily_nutrition["Protein"].sum()
    )

    # --------------------------------------------------------
    # Budget validation
    # --------------------------------------------------------

    if total_cost > weekly_budget + 0.01:

        raise ValueError(
            "Final meal plan exceeds the weekly budget."
        )

    # --------------------------------------------------------
    # Wide meal plan
    # --------------------------------------------------------

    weekly_plan = weekly_plan_long.pivot(
        index="Day",
        columns="Meal_Type",
        values="Recipe_Name"
    ).reset_index()

    for meal_type in MEAL_TYPES:

        if meal_type not in weekly_plan.columns:
            weekly_plan[meal_type] = ""

    weekly_plan = weekly_plan[
        ["Day"] + MEAL_TYPES
    ]

    # --------------------------------------------------------
    # Selected recipe mapping
    # --------------------------------------------------------

    selected_ids = set(
        weekly_plan_long[
            "Recipe_ID"
        ].astype(str)
    )

    selected_mapping = mapping_df[
        mapping_df["Recipe_ID"]
        .astype(str)
        .isin(selected_ids)
    ].copy()

    # --------------------------------------------------------
    # Nutrition per rupee
    # --------------------------------------------------------

    calories_per_rupee = (
        total_calories
        / max(total_cost, 0.01)
    )

    protein_per_rupee = (
        total_protein
        / max(total_cost, 0.01)
    )

    # --------------------------------------------------------
    # SUMMARY
    # --------------------------------------------------------

    summary = pd.DataFrame([{

        "Weekly Budget":
            weekly_budget,

        "Actual Weekly Cost":
            total_cost,

        "Budget Remaining":
            weekly_budget - total_cost,

        "Budget Used %":
            total_cost
            / weekly_budget
            * 100,

        "Total Meals":
            len(weekly_plan_long),

        "Average Daily Cost":
            total_cost / 7,

        "Average Daily Calories":
            total_calories / 7,

        "Average Daily Protein":
            total_protein / 7,

        "Weekly Calories":
            total_calories,

        "Weekly Protein":
            total_protein,

        "Calories per Rupee":
            calories_per_rupee,

        "Protein per Rupee":
            protein_per_rupee,

        "LP Minimum Daily Cost Reference":
            lp_result[
                "minimum_daily_cost"
            ],

        "LP Status":
            lp_result["status"],

        "Diet":
            diet
    }])

    # --------------------------------------------------------
    # Save outputs
    # --------------------------------------------------------

    weekly_plan.to_csv(
        os.path.join(
            OUTPUT_DIR,
            "weekly_meal_plan.csv"
        ),
        index=False
    )

    weekly_plan_long.to_csv(
        os.path.join(
            OUTPUT_DIR,
            "weekly_meal_plan_long.csv"
        ),
        index=False
    )

    daily_nutrition.to_csv(
        os.path.join(
            OUTPUT_DIR,
            "daily_nutrition.csv"
        ),
        index=False
    )

    grocery_list.to_csv(
        os.path.join(
            OUTPUT_DIR,
            "grocery_list.csv"
        ),
        index=False
    )

    # Food basket = exact grocery list
    grocery_list.to_csv(
        os.path.join(
            OUTPUT_DIR,
            "optimized_food_basket.csv"
        ),
        index=False
    )

    selected_mapping.to_csv(
        os.path.join(
            OUTPUT_DIR,
            "recipe_food_mapping.csv"
        ),
        index=False
    )

    summary.to_csv(
        os.path.join(
            OUTPUT_DIR,
            "final_summary.csv"
        ),
        index=False
    )

    return {
        "summary": summary,
        "weekly_plan": weekly_plan,
        "weekly_plan_long":
            weekly_plan_long,
        "daily_nutrition":
            daily_nutrition,
        "grocery_list":
            grocery_list,
        "optimized_food_basket":
            grocery_list,
        "recipe_food_mapping":
            selected_mapping,
        "recipes":
            prepared_recipes,
        "lp_reference":
            lp_result
    }


# ============================================================
# COMMAND LINE TEST
# ============================================================

if __name__ == "__main__":

    print("=" * 60)
    print("NUTRIBUDGET")
    print("Smart nutrition. Smarter spending.")
    print("=" * 60)

    try:

        budget = float(
            input(
                "Enter maximum weekly budget (₹): "
            )
        )

        diet = input(
            "Enter diet (Vegetarian/Non-Vegetarian): "
        )

        calories = float(
            input(
                "Enter required daily calories: "
            )
        )

        protein = float(
            input(
                "Enter minimum daily protein (g): "
            )
        )

        print(
            "\nCreating optimized 7-day meal plan..."
        )

        print(
            "Connecting recipes with ingredients..."
        )

        print(
            "Applying budget + nutrition + diversity constraints..."
        )

        results = run_optimizer(
            budget,
            diet,
            calories,
            protein
        )

        print("\n")
        print("=" * 60)
        print("7-DAY MEAL PLAN")
        print("=" * 60)

        print(
            results["weekly_plan"]
            .to_string(index=False)
        )

        print("\n")
        print("=" * 60)
        print("DAILY NUTRITION")
        print("=" * 60)

        print(
            results["daily_nutrition"]
            .to_string(index=False)
        )

        print("\n")
        print("=" * 60)
        print("GROCERY LIST")
        print("=" * 60)

        print(
            results["grocery_list"]
            .to_string(index=False)
        )

        print("\n")
        print("=" * 60)
        print("FINAL SUMMARY")
        print("=" * 60)

        print(
            results["summary"]
            .to_string(index=False)
        )

        print("\nOutput files saved to:")
        print(OUTPUT_DIR)

    except Exception as error:

        print("\nERROR:")
        print(error)