import streamlit as st
import sqlite3
import os
from dotenv import load_dotenv
from database import MealDatabase, MEAL_TYPES, UNITS, CATEGORIES
from format import format_amount

# Initialize database
db = MealDatabase()

# Set page config
st.set_page_config(
    page_title="Meal Planner",
    page_icon="🥗",
    layout="wide"
)


def main():
    st.title("Meal Planner 🥗")

    # Sidebar navigation
    page = st.sidebar.radio(
        "Navigation",
        ["Gerichte", "Einkauf", "Neue Rezepte", "Rezept bearbeiten"]
    )

    if page == "Gerichte":
        show_recipes_page()
    elif page == "Einkauf":
        show_shopping_page()
    elif page == "Neue Rezepte":
        show_new_recipe_page()
    else:
        show_edit_recipe_page()


def show_recipes_page():
    st.header("Gerichte")

    # Get all recipes and currently selected ones
    all_recipes = db.get_all_recipes()
    selected_recipes = db.get_selected_recipes()
    # Update selected_ids from the database
    selected_ids = selected_recipes['id'].tolist()

    # Clear selection button
    if st.button("Auswahl zurücksetzen"):
        # Clear selected recipes in the database
        db.update_selected_recipes([])
        selected_ids.clear()  # Clear the selected_ids list to reflect the reset
        db.clear_additional_ingredients()  # Clear the additional ingredients table
        st.rerun()  # Rerun the app

    # Filter by meal type
    meal_type = st.selectbox("Nach Mahlzeit filtern", ["Alle"] + MEAL_TYPES)
    if meal_type != "Alle":
        all_recipes = all_recipes[all_recipes['meal_type'] == meal_type]

    # CSS
    st.markdown(
        """
        <style>
        .st-emotion-cache-rb05al {
            min-width: 0px;}
        .st-emotion-cache-bfpqqo {
            min-width: 0px;}
        .st-emotion-cache-1hyd1ho p {
            word-break: normal;
            white-space: normal;}
        </style>
        """,
        unsafe_allow_html=True
    )
    st.markdown('<div class="horizontal-container">', unsafe_allow_html=True)
    # Display recipes grouped by meal type
    selected_recipe_ids = []
    for meal in MEAL_TYPES:
        st.subheader(meal)  # Display meal type header
        meal_recipes = all_recipes[all_recipes['meal_type'] == meal].sort_values(
            'name')

        for _, recipe in meal_recipes.iterrows():
            col1, col2 = st.columns([0.1, 0.9])
            with col1:
                # Initialize session_state for the checkbox if it doesn't exist
                is_selected = st.checkbox(
                    "x", key=f"recipe_{recipe['id']}", value=recipe['id'] in selected_ids, label_visibility="hidden")

                if is_selected:
                    selected_recipe_ids.append(recipe['id'])

            with col2:
                if st.button(recipe['name'], key=f"details_{recipe['id']}"):
                    show_recipe_details(recipe['id'])

    st.markdown('</div>', unsafe_allow_html=True)

    # Update selected recipes in database
    if len(selected_recipe_ids) > 0:
        db.update_selected_recipes(selected_recipe_ids)


def show_recipe_details(recipe_id):
    recipe, ingredients = db.get_recipe_details(recipe_id)

    if recipe is None or recipe.empty:
        st.error("Rezept nicht gefunden!")
        return

    st.write(f"**Mahlzeit:** {recipe['meal_type'].iloc[0]}")

    st.write("**Zutaten:**")
    ingredients_df = ingredients[['name', 'amount', 'unit']].copy()
    ingredients_df['formatted_amount'] = ingredients_df['amount'].apply(
        format_amount)
    ingredients_df = ingredients_df.rename(columns={
        'name': 'Zutat',
        'formatted_amount': 'M',
        'unit': 'E'
    })
    st.dataframe(ingredients_df[['Zutat', 'M', 'E']], hide_index=True)

    st.write("**Zubereitung:**")
    preparation_steps = recipe['preparation'].iloc[0].split('\n')
    preparation_steps = [x for x in preparation_steps if x != '']
    for i, step in enumerate(preparation_steps, start=1):
        # Display each step as a numbered item
        st.write(f"{i}. {step.strip()}")


def show_shopping_page():
    st.header("Einkaufsliste")

    shopping_list = db.get_shopping_list()
    if shopping_list.empty:
        st.warning(
            "Keine Rezepte ausgewählt. Bitte wähle zuerst Rezepte auf der 'Gerichte' Seite aus.")
        return

    # Format the total_amount column using the format_amount function
    shopping_list['formatted_amount'] = shopping_list['total_amount'].apply(format_amount)

    # Group by category
    for category in CATEGORIES:
        category_items = shopping_list[shopping_list['category'] == category]
        if not category_items.empty:
            st.subheader(category)
            for _, item in category_items.iterrows():
                st.checkbox(
                    f"{item['name']}: {item['formatted_amount']} {item['unit']}",
                    key=f"shop_{item['name']}"
                )
    
    # Zuästzliche Einkäufe
    new_ingredient_name = st.text_input('+ Weitere Einkäufe hinzufügen')
    if new_ingredient_name:
        db.add_additional_ingredient(new_ingredient_name)
        st.success(f'{new_ingredient_name} hinzugefügt!')
        st.rerun()

# Load environment variables
load_dotenv()
APP_PASSWORD = os.getenv("APP_PASSWORD")

def show_new_recipe_page():
    st.header("Neues Rezept erstellen")

    # Password input
    password = st.text_input("Password", type="password")

    if password != APP_PASSWORD:
        st.error("Incorrect password. Access denied.")
    else:
        # Proceed with the rest of the page functionality
        st.success("Access granted.")

        with st.form("new_recipe"):
            name = st.text_input("Rezeptname")
            meal_type = st.selectbox("Mahlzeit", MEAL_TYPES)
            preparation = st.text_area("Zubereitung")

            st.subheader("Zutaten")
            ingredients = []

            # Container for dynamic ingredient fields
            ingredient_container = st.container()

            # Add ingredient button
            if 'ingredient_count' not in st.session_state:
                st.session_state.ingredient_count = 1

            if st.form_submit_button("+ Zutat hinzufügen"):
                st.session_state.ingredient_count += 1

            # Display ingredient fields
            with ingredient_container:
                for i in range(st.session_state.ingredient_count):
                    col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
                    with col1:
                        ing_name = st.text_input(
                            f"Zutat {i+1}", key=f"ing_name_{i}")
                    with col2:
                        amount = st.number_input(f"Menge {i+1}",
                                                min_value=0.0,
                                                key=f"amount_{i}")
                    with col3:
                        unit = st.selectbox(f"Einheit {i+1}",
                                            UNITS,
                                            key=f"unit_{i}")
                    with col4:
                        category = st.selectbox(f"Kategorie {i+1}",
                                                CATEGORIES,
                                                key=f"category_{i}")

                    if ing_name and amount > 0:
                        ingredients.append((ing_name, amount, unit, category))

            # Save button
            if st.form_submit_button("Speichern"):
                if not name or not meal_type or not preparation or not ingredients:
                    st.error("Bitte fülle alle Pflichtfelder aus!")
                else:
                    try:
                        db.add_recipe(meal_type, name, preparation, ingredients)
                        st.success("Rezept erfolgreich gespeichert!")
                        st.session_state.ingredient_count = 1  # Reset ingredient count
                    except sqlite3.IntegrityError:
                        st.error("Ein Rezept mit diesem Namen existiert bereits!")

# Load environment variables
load_dotenv()
APP_PASSWORD = os.getenv("APP_PASSWORD")

def show_edit_recipe_page():
    st.header("Rezept bearbeiten")

    # Password input
    password = st.text_input("Password", type="password")

    if password != APP_PASSWORD:
        st.error("Incorrect password. Access denied.")
    else:
        # Proceed with the rest of the page functionality
        st.success("Access granted.")        

        def update_ingredient_count():
            if 'edit_ingredient_count' in st.session_state:
                del st.session_state.edit_ingredient_count

        all_recipes = db.get_all_recipes()
        recipe_names = all_recipes.sort_values('name')['name'].tolist()
        recipe_name = st.selectbox("Rezeptname", recipe_names, on_change=update_ingredient_count)
        recipe_id = int(all_recipes[all_recipes['name'] == recipe_name].iloc[0]['id'])

        # After fetching the new recipe and its ingredients
        recipe, ingredients = db.get_recipe_details(recipe_id)

        # Initialize ingredient count if not already set
        if 'edit_ingredient_count' not in st.session_state:
            st.session_state.edit_ingredient_count = len(ingredients)

        # Edit recipe form
        with st.form("edit_recipe"):
            meal_type = st.selectbox("Mahlzeit", MEAL_TYPES, index=MEAL_TYPES.index(recipe['meal_type'].iloc[0]))
            preparation = st.text_area("Zubereitung", value=recipe['preparation'].iloc[0])

            st.subheader("Zutaten")
            edited_ingredients = []

            # Display existing ingredients with editable fields
            for idx in range(st.session_state.edit_ingredient_count):
                if idx < len(ingredients):
                    ing_name = ingredients.iloc[idx]['name']
                    amount = ingredients.iloc[idx]['amount']
                    unit = ingredients.iloc[idx]['unit']
                    category = ingredients.iloc[idx]['category']
                else:
                    ing_name, amount, unit, category = "", 0, "g", CATEGORIES[0]

                col1, col2, col3, col4 = st.columns([2, 1, 1, 2])
                with col1:
                    ing_name = st.text_input(f"Zutat {idx + 1}", value=ing_name, key=f"ing_name_{idx}")
                with col2:
                    amount = st.number_input(f"Menge {idx + 1}", value=float(amount), min_value=0.0, key=f"amount_{idx}")
                with col3:
                    unit = st.selectbox(f"Einheit {idx + 1}", UNITS, index=UNITS.index(unit), key=f"unit_{idx}")
                with col4:
                    category = st.selectbox(f"Kategorie {idx + 1}", CATEGORIES, index=CATEGORIES.index(category), key=f"category_{idx}")

                if ing_name and amount > 0:
                    edited_ingredients.append((ing_name, amount, unit, category))

            if st.form_submit_button("+ Zutat hinzufügen"):
                st.session_state.edit_ingredient_count += 1
                st.rerun()

            # Save button
            if st.form_submit_button("Speichern"):
                if not meal_type or not preparation or not edited_ingredients:
                    st.error("Bitte fülle alle Pflichtfelder aus!")
                else:
                    try:
                        db.edit_recipe(recipe_id, meal_type, name, preparation, edited_ingredients)
                        st.success("Rezept erfolgreich gespeichert!")
                        st.session_state.ingredient_count = len(edited_ingredients)  # Reset ingredient count
                    except sqlite3.IntegrityError:
                        st.error("Ein Rezept mit diesem Namen existiert bereits!")

        # Delete button
        if st.button("Rezept löschen"):
            db.delete_recipe(recipe_id)
            st.success("Rezept erfolgreich gelöscht!")


if __name__ == "__main__":
    main()
