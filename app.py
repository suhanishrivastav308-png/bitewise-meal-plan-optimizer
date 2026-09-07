import streamlit as st
import os
import pandas as pd
import plotly.graph_objects as go
import matplotlib.pyplot as plt

from meal_optimizer import run_optimizer


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="BiteWise",
    page_icon="🌿",
    layout="wide"
)
st.markdown("""
<style>

    /* Main background */
    .stApp {
        background-color: #F7F3E8;
    }

    /* Main text */
    html, body, [class*="css"] {
        color: #26352F;
    }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background-color: #E8F0E5;
    }

    /* Buttons */
    .stButton > button {
        background-color: #2F5D50;
        color: white;
        border-radius: 10px;
        border: none;
        padding: 0.6rem 1rem;
        font-weight: 600;
    }

    .stButton > button:hover {
        background-color: #1F4037;
        color: white;
    }

    /* Metric cards */
    div[data-testid="metric-container"] {
        background-color: #FFFDF7;
        border: 1px solid #D8E4D5;
        border-radius: 14px;
        padding: 15px;
    }

    /* Tables */
    .stDataFrame {
        border-radius: 12px;
    }

    /* Headings */
    h1, h2, h3 {
        color: #1F4037;
    }
/* ============================================================
   BITEWISE SUMMARY CARDS
   ============================================================ */

.summary-card {
    background: #FFFDF7;
    border: 1px solid #D8E4D5;
    border-left: 5px solid #2F5D50;
    border-radius: 16px;
    padding: 22px;
    min-height: 125px;
    box-shadow: 0 4px 12px rgba(31, 64, 55, 0.06);
    margin-bottom: 12px;
}

.card-label {
    color: #52635B;
    font-size: 12px;
    font-weight: 700;
    letter-spacing: 0.8px;
    margin-bottom: 8px;
}

.card-value {
    color: #1F4037;
    font-size: 30px;
    font-weight: 750;
    margin-bottom: 6px;
}

.card-description {
    color: #718078;
    font-size: 13px;
}

.nutrition-card {
    background: #E8F0E5;
    border: 1px solid #D1E0CE;
    border-radius: 16px;
    padding: 20px;
    display: flex;
    align-items: center;
    gap: 18px;
    min-height: 90px;
}

.nutrition-icon {
    font-size: 32px;
}

.nutrition-value {
    color: #1F4037;
    font-size: 26px;
    font-weight: 750;
}
/* ============================================================
   MEAL CARDS
   ============================================================ */

.meal-card {
    background: #FFFDF7;
    border: 1px solid #D8E4D5;
    border-radius: 14px;
    padding: 16px 20px;
    margin-bottom: 12px;
    box-shadow: 0 3px 10px rgba(31, 64, 55, 0.05);
}

.meal-type {
    color: #52635B;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 5px;
}

.meal-name {
    color: #1F4037;
    font-size: 18px;
    font-weight: 650;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# TITLE
# ============================================================

logo_path = os.path.join("assets", "bitewise_logo.png")

if os.path.exists(logo_path):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.image(logo_path, width=350)
# ============================================================
# BITEWISE HEADER
# ============================================================

# ============================================================
# BITEWISE HEADER
# ============================================================

st.markdown(
    "<h1 style='text-align:center;'>BiteWise</h1>",
    unsafe_allow_html=True
)

st.markdown(
    "<h3 style='text-align:center;'>Eat Smart. Spend Wise.</h3>",
    unsafe_allow_html=True
)

st.caption(
    "Smart meal planning that balances your budget, "
    "nutrition and dietary preference."
)     

# --------------------------------------------------

st.write(
    """
    **Meal Plan Optimizer on a Budget**

    Enter your maximum weekly budget and dietary preference.
    Bite Wise creates a **7-day meal plan** using
    constrained optimization and connects every selected
    recipe to its ingredients and grocery list.
    """
)


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🌿 Build Your Plan")

st.sidebar.caption(
    "Enter your preferences and we'll create "
    "a personalized 7-day meal plan."
)


# ------------------------------------------------------------
# BUDGET
# ------------------------------------------------------------

weekly_budget = st.sidebar.number_input(
    "💰 Maximum Weekly Budget (₹)",
    min_value=500.0,
    value=None,
    step=100.0,
    placeholder="Enter your budget"
)


# ------------------------------------------------------------
# DIET
# ------------------------------------------------------------

diet = st.sidebar.selectbox(
    "🥗 Dietary Preference",
    [
        "Vegetarian",
        "Non-Vegetarian"
    ]
)


# ------------------------------------------------------------
# CALORIES
# ------------------------------------------------------------

daily_calories = st.sidebar.number_input(
    "🔥 Daily Calorie Requirement",
    min_value=1000.0,
    max_value=4000.0,
    value=None,
    step=100.0,
    placeholder="Enter calories"
)


# ------------------------------------------------------------
# PROTEIN
# ------------------------------------------------------------

daily_protein = st.sidebar.number_input(
    "💪 Minimum Daily Protein (g)",
    min_value=20.0,
    max_value=200.0,
    value=None,
    step=5.0,
    placeholder="Enter protein"
)


# ------------------------------------------------------------
# CHECK INPUTS
# ------------------------------------------------------------

if (
    weekly_budget is None
    or daily_calories is None
    or daily_protein is None
):

    st.sidebar.info(
        "Please enter your budget, calories and protein "
        "requirements."
    )

    st.stop()


# ============================================================
# OPTIMIZE BUTTON
# ============================================================

if st.sidebar.button(
    "🌿 Create My Meal Plan",
    type="primary",
    use_container_width=True
):

    with st.spinner(
        "Creating your personalized 7-day meal plan..."
    ):

        try:

            results = run_optimizer(
                weekly_budget,
                diet,
                daily_calories,
                daily_protein
            )

            st.session_state["results"] = results

            st.success(
                "Your 7-day meal plan has been optimized successfully!"
            )

        except Exception as e:

            st.error(
                f"Optimization failed: {str(e)}"
            )

            st.stop()


# ============================================================
# SHOW RESULTS
# ============================================================

if "results" not in st.session_state:

    st.info(
        "👈 Enter your requirements in the sidebar "
        "and click **Optimize Meal Plan**."
    )

    st.markdown(
        """
        ### How Bite Wise works

        **1. Input**
        - Maximum weekly budget
        - Dietary preference
        - Daily calorie requirement
        - Minimum daily protein

        **2. Optimization**
        - Recipe cost
        - Calories
        - Protein
        - Budget constraint
        - Recipe diversity
        - Nutrition-per-rupee

        **3. Output**
        - 7-day meal plan
        - Grocery list
        - Daily nutrition
        - Calories per rupee
        - Protein per rupee
        - Recipe-to-ingredient mapping
        """
    )

    st.stop()


results = st.session_state["results"]

summary = results["summary"]
weekly_plan = results["weekly_plan"]
weekly_plan_long = results["weekly_plan_long"]
daily_nutrition = results["daily_nutrition"]
grocery_list = results["grocery_list"]
food_basket = results["optimized_food_basket"]
mapping = results["recipe_food_mapping"]







# ============================================================
# ============================================================
# PROFESSIONAL SUMMARY
# ============================================================

st.markdown("## 🌿 Your Weekly Plan")

s = summary.iloc[0]

# Calculate values
budget = float(s["Weekly Budget"])
cost = float(s["Actual Weekly Cost"])
remaining = float(s["Budget Remaining"])
used = float(s["Budget Used %"])
calories = float(s["Average Daily Calories"])
protein = float(s["Average Daily Protein"])

# ------------------------------------------------------------
# FINANCIAL SUMMARY
# ------------------------------------------------------------

st.markdown("### 💰 Budget Overview")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        f"""
        <div class="summary-card">
            <div class="card-label">WEEKLY BUDGET</div>
            <div class="card-value">₹{budget:,.0f}</div>
            <div class="card-description">Your maximum spending limit</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        f"""
        <div class="summary-card">
            <div class="card-label">PLANNED COST</div>
            <div class="card-value">₹{cost:,.0f}</div>
            <div class="card-description">Estimated weekly grocery cost</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col3:
    st.markdown(
        f"""
        <div class="summary-card">
            <div class="card-label">MONEY LEFT</div>
            <div class="card-value">₹{remaining:,.0f}</div>
            <div class="card-description">{used:.1f}% of budget used</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ------------------------------------------------------------
# BUDGET PROGRESS
# ------------------------------------------------------------

st.markdown("### 📊 Budget Utilization")

st.progress(
    min(used / 100, 1.0)
)

st.caption(
    f"₹{cost:,.0f} used out of ₹{budget:,.0f} maximum budget"
)


# ------------------------------------------------------------
# NUTRITION SUMMARY
# ------------------------------------------------------------

st.markdown("### 🥗 Daily Nutrition")

col4, col5 = st.columns(2)

with col4:
    st.markdown(
        f"""
        <div class="nutrition-card">
            <div class="nutrition-icon">🔥</div>
            <div>
                <div class="card-label">AVERAGE DAILY CALORIES</div>
                <div class="nutrition-value">{calories:,.0f} kcal</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

with col5:
    st.markdown(
        f"""
        <div class="nutrition-card">
            <div class="nutrition-icon">💪</div>
            <div>
                <div class="card-label">AVERAGE DAILY PROTEIN</div>
                <div class="nutrition-value">{protein:.1f} g</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# LP INFORMATION
# ============================================================

st.header("🧮 Optimization Method")

st.write(
    """
    The optimizer uses **linear programming as a nutrition-cost
    reference** and then selects a practical 7-day recipe plan
    under the weekly budget.

    The optimization considers:

    - Minimum daily calories
    - Minimum daily protein
    - Maximum weekly spending
    - Recipe cost
    - Nutrition value
    - Recipe diversity
    - Repetition control
    - Dietary preference
    """
)

lp_cost = s["LP Minimum Daily Cost Reference"]

if pd.notna(lp_cost):

    st.info(
        f"LP minimum daily cost reference: "
        f"₹{lp_cost:.2f}"
    )

st.write(
    f"**LP Status:** {s['LP Status']}"
)


# ============================================================
# ============================================================
# YOUR 7-DAY MEAL PLAN
# ============================================================

st.header("📅 Your 7-Day Meal Plan")

st.caption(
    "Explore your personalized meals day by day."
)

days = weekly_plan_long["Day"].drop_duplicates().tolist()

day_tabs = st.tabs(days)

for tab, day in zip(day_tabs, days):

    with tab:

        day_data = weekly_plan_long[
            weekly_plan_long["Day"] == day
        ]

        meal_order = [
            "Breakfast",
            "Lunch",
            "Snack",
            "Dinner"
        ]

        for meal in meal_order:

            meal_data = day_data[
                day_data["Meal_Type"] == meal
            ]

            if not meal_data.empty:

                recipe_name = meal_data.iloc[0]["Recipe_Name"]

                if meal == "Breakfast":
                    icon = "🍳"
                elif meal == "Lunch":
                    icon = "🥗"
                elif meal == "Snack":
                    icon = "🍎"
                else:
                    icon = "🍽️"

                st.markdown(
                    f"""
                    <div class="meal-card">
                        <div class="meal-type">
                            {icon} {meal}
                        </div>
                        <div class="meal-name">
                            {recipe_name}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )


# ============================================================
# DAILY NUTRITION
# ============================================================

# ============================================================
# DAILY NUTRITION
# ============================================================

st.header("🥗 Daily Nutrition")

st.caption(
    "Your actual nutrition compared with your daily requirement."
)

col1, col2 = st.columns(2)

with col1:

    actual_calories = float(s["Average Daily Calories"])
    required_calories = float(daily_calories)

    st.metric(
        "🔥 Calories",
        f"{actual_calories:,.0f} kcal",
        f"Required: {required_calories:,.0f} kcal"
    )

    if actual_calories >= required_calories:
        st.success("✓ Daily calorie requirement met")
    else:
        st.warning("Below your daily calorie requirement")


with col2:

    actual_protein = float(s["Average Daily Protein"])
    required_protein = float(daily_protein)

    st.metric(
        "💪 Protein",
        f"{actual_protein:.1f} g",
        f"Minimum: {required_protein:.1f} g"
    )

    if actual_protein >= required_protein:
        st.success("✓ Daily protein requirement met")
    else:
        st.warning("Below your minimum protein requirement")

# ============================================================
# NUTRITION PER RUPEE
# ============================================================

st.header("💰 Nutrition Efficiency")

st.caption(
    "See how efficiently your meal plan converts every rupee "
    "into calories and protein."
)

# Prepare chart data
efficiency_data = daily_nutrition[
    ["Day", "Calories_per_Rupee", "Protein_per_Rupee"]
].copy()

days = efficiency_data["Day"].tolist()

calorie_values = efficiency_data[
    "Calories_per_Rupee"
].tolist()

protein_values = efficiency_data[
    "Protein_per_Rupee"
].tolist()


# ------------------------------------------------------------
# Interactive chart
# ------------------------------------------------------------

fig = go.Figure()

# Calories per Rupee
fig.add_trace(
    go.Bar(
        x=days,
        y=calorie_values,
        name="Calories per ₹",
        marker_color="#2F5D50",
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Calories per ₹: %{y:.1f}"
            "<extra></extra>"
        )
    )
)

# Protein per Rupee
fig.add_trace(
    go.Bar(
        x=days,
        y=protein_values,
        name="Protein per ₹",
        marker_color="#8BAF8B",
        visible=False,
        hovertemplate=(
            "<b>%{x}</b><br>"
            "Protein per ₹: %{y:.2f} g"
            "<extra></extra>"
        )
    )
)


# ------------------------------------------------------------
# Dropdown to switch between metrics
# ------------------------------------------------------------

fig.update_layout(
    updatemenus=[
        dict(
            type="buttons",
            direction="right",
            buttons=[
                dict(
                    label="🔥 Calories per ₹",
                    method="update",
                    args=[
                        {"visible": [True, False]},
                        {
                            "yaxis": {
                                "title": "Calories per Rupee"
                            }
                        }
                    ]
                ),
                dict(
                    label="💪 Protein per ₹",
                    method="update",
                    args=[
                        {"visible": [False, True]},
                        {
                            "yaxis": {
                                "title": "Protein per Rupee (g)"
                            }
                        }
                    ]
                )
            ],
            showactive=True,
            x=0,
            xanchor="left",
            y=1.18,
            yanchor="top"
        )
    ],

    title={
        "text": "Daily Nutrition Efficiency",
        "x": 0.02
    },

    xaxis={
        "title": "Day",
        "showgrid": False
    },

    yaxis={
        "title": "Calories per Rupee",
        "showgrid": True,
        "gridcolor": "#E4E8E2"
    },

    plot_bgcolor="#FFFDF7",
    paper_bgcolor="#FFFDF7",

    font={
        "color": "#26352F"
    },

    height=430,

    margin=dict(
        l=60,
        r=30,
        t=100,
        b=60
    ),

    hovermode="x unified"
)

st.plotly_chart(
    fig,
    use_container_width=True,
    config={
        "displayModeBar": False
    }
)
# ============================================================
# GROCERY LIST
# ============================================================

st.header("🛒 Grocery List")

st.caption(
    "Your shopping list is generated directly from the ingredients "
    "used in your 7-day meal plan."
)

# Create a clean shopping list
shopping_list = grocery_list[
    ["Food_Item", "Purchase_Quantity_kg", "Estimated_Cost"]
].copy()

# Rename columns for a cleaner display
shopping_list.columns = [
    "🛒 Item",
    "📦 Quantity",
    "💰 Estimated Cost"
]

# Display grocery list
st.dataframe(
    shopping_list,
    use_container_width=True,
    hide_index=True,
    column_config={
        "🛒 Item": st.column_config.TextColumn(
            "🛒 Item"
        ),
        "📦 Quantity": st.column_config.NumberColumn(
            "📦 Quantity (kg)",
            format="%.2f kg"
        ),
        "💰 Estimated Cost": st.column_config.NumberColumn(
            "💰 Estimated Cost",
            format="₹%.2f"
        )
    }
)

# Total grocery cost
total_grocery_cost = shopping_list[
    "💰 Estimated Cost"
].sum()

st.markdown(
    f"""
    <div class="summary-card">
        <div class="card-label">TOTAL ESTIMATED GROCERY COST</div>
        <div class="card-value">₹{total_grocery_cost:,.2f}</div>
        <div class="card-description">
            Estimated cost of ingredients required for your weekly meal plan
        </div>
    </div>
    """,
    unsafe_allow_html=True
)



# ============================================================
# GROCERY NUTRITION VALUE
# ============================================================

st.subheader(
    "Grocery Nutrition Value"
)

if not grocery_list.empty:

    grocery_chart = grocery_list[
        [
            "Food_Item",
            "Estimated_Cost",
            "Calories",
            "Protein"
        ]
    ].copy()

    grocery_chart = grocery_chart.set_index(
        "Food_Item"
    )

    st.bar_chart(
        grocery_chart
    )


# ============================================================
# ============================================================
# OPTIMIZED FOOD BASKET
# ============================================================

st.header("🧺 Optimized Food Basket")

st.caption(
    "The food basket contains the ingredients selected by BiteWise "
    "to build your optimized 7-day meal plan."
)

# Select useful information from the optimized basket
basket_display = food_basket[
    [
        "Food_Item",
        "Purchase_Quantity_kg",
        "Estimated_Cost",
        "Calories",
        "Protein"
    ]
].copy()

# Rename columns for a cleaner display
basket_display.columns = [
    "🥕 Food Item",
    "📦 Quantity (kg)",
    "💰 Cost",
    "🔥 Calories",
    "💪 Protein (g)"
]

# Calculate basket summary
total_items = len(basket_display)
total_cost = basket_display["💰 Cost"].sum()
total_calories = basket_display["🔥 Calories"].sum()
total_protein = basket_display["💪 Protein (g)"].sum()

# ============================================================
# BASKET SUMMARY CARDS
# ============================================================

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(
        f"""
        <div class="summary-card">
            <div class="card-label">FOOD ITEMS</div>
            <div class="card-value">{total_items}</div>
            <div class="card-description">Ingredients selected</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c2:
    st.markdown(
        f"""
        <div class="summary-card">
            <div class="card-label">BASKET COST</div>
            <div class="card-value">₹{total_cost:,.0f}</div>
            <div class="card-description">Estimated total cost</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c3:
    st.markdown(
        f"""
        <div class="summary-card">
            <div class="card-label">CALORIES</div>
            <div class="card-value">{total_calories:,.0f}</div>
            <div class="card-description">From selected ingredients</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c4:
    st.markdown(
        f"""
        <div class="summary-card">
            <div class="card-label">PROTEIN</div>
            <div class="card-value">{total_protein:,.1f} g</div>
            <div class="card-description">From selected ingredients</div>
        </div>
        """,
        unsafe_allow_html=True
    )

# ============================================================
# SHOPPING BASKET TABLE
# ============================================================

st.markdown("### 🛍️ Your Shopping Basket")

st.dataframe(
    basket_display,
    use_container_width=True,
    hide_index=True,
    height=400,
    column_config={
        "🥕 Food Item": st.column_config.TextColumn(
            "🥕 Food Item"
        ),
        "📦 Quantity (kg)": st.column_config.NumberColumn(
            "📦 Quantity (kg)",
            format="%.2f"
        ),
        "💰 Cost": st.column_config.NumberColumn(
            "💰 Cost",
            format="₹%.2f"
        ),
        "🔥 Calories": st.column_config.NumberColumn(
            "🔥 Calories",
            format="%.0f"
        ),
        "💪 Protein (g)": st.column_config.NumberColumn(
            "💪 Protein (g)",
            format="%.1f"
        )
    }
)

# Summary cards
total_items = len(basket_display)
total_cost = basket_display["💰 Cost"].sum()
total_calories = basket_display["🔥 Calories"].sum()
total_protein = basket_display["💪 Protein (g)"].sum()

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.markdown(
        f"""
        <div class="summary-card">
            <div class="card-label">FOOD ITEMS</div>
            <div class="card-value">{total_items}</div>
            <div class="card-description">Ingredients selected</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c2:
    st.markdown(
        f"""
        <div class="summary-card">
            <div class="card-label">BASKET COST</div>
            <div class="card-value">₹{total_cost:,.0f}</div>
            <div class="card-description">Estimated total cost</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c3:
    st.markdown(
        f"""
        <div class="summary-card">
            <div class="card-label">CALORIES</div>
            <div class="card-value">{total_calories:,.0f}</div>
            <div class="card-description">From selected ingredients</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with c4:
    st.markdown(
        f"""
        <div class="summary-card">
            <div class="card-label">PROTEIN</div>
            <div class="card-value">{total_protein:,.1f} g</div>
            <div class="card-description">From selected ingredients</div>
        </div>
        """,
        unsafe_allow_html=True
    )




# ============================================================



# ============================================================
# RECIPE DETAILS
# ============================================================

st.header("📖 Recipe Details")

recipe_names = weekly_plan_long[
    "Recipe_Name"
].drop_duplicates().tolist()

selected_recipe = st.selectbox(
    "Select a recipe",
    recipe_names
)

recipe_row = weekly_plan_long[
    weekly_plan_long["Recipe_Name"]
    == selected_recipe
].iloc[0]

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Meal Type",
        recipe_row["Meal_Type"]
    )

with col2:
    st.metric(
        "Cuisine",
        recipe_row["Cuisine"]
    )

with col3:
    st.metric(
        "Calories",
        f"{recipe_row['Calories']:.0f}"
    )

with col4:
    st.metric(
        "Protein",
        f"{recipe_row['Protein']:.1f} g"
    )

st.write(
    f"**Estimated Cost:** "
    f"₹{recipe_row['Cost']:.2f}"
)

st.write(
    f"**Preparation Time:** "
    f"{recipe_row['Prep_Time_Min']} minutes"
)


# ============================================================
# BUDGET VISUAL
# ============================================================

st.header("💵 Budget Utilization")

budget_df = pd.DataFrame({
    "Category": [
        "Used",
        "Remaining"
    ],
    "Amount": [
        s["Actual Weekly Cost"],
        s["Budget Remaining"]
    ]
})

budget_df = budget_df.set_index(
    "Category"
)

st.bar_chart(
    budget_df
)


# ============================================================
# DOWNLOAD FILES
# ============================================================

st.header("⬇️ Download Results")

col1, col2, col3 = st.columns(3)

with col1:

    st.download_button(
        "Download 7-Day Meal Plan",
        data=weekly_plan.to_csv(
            index=False
        ),
        file_name="weekly_meal_plan.csv",
        mime="text/csv"
    )

with col2:

    st.download_button(
        "Download Grocery List",
        data=grocery_list.to_csv(
            index=False
        ),
        file_name="grocery_list.csv",
        mime="text/csv"
    )

with col3:

    st.download_button(
        "Download Daily Nutrition",
        data=daily_nutrition.to_csv(
            index=False
        ),
        file_name="daily_nutrition.csv",
        mime="text/csv"
    )


st.download_button(
    "Download Complete Recipe-Ingredient Mapping",
    data=mapping.to_csv(
        index=False
    ),
    file_name="recipe_food_mapping.csv",
    mime="text/csv"
)


st.download_button(
    "Download Final Summary",
    data=summary.to_csv(
        index=False
    ),
    file_name="final_summary.csv",
    mime="text/csv"
)


# ============================================================
# FOOTER
# ============================================================

st.markdown("---")

st.caption(
    "Bite Wise | Smart nutrition. Smarter spending."
)