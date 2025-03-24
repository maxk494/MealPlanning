import streamlit as st
import psycopg2
from sqlalchemy import create_engine, text
import pandas as pd
from typing import List, Tuple

class MealDatabase:
    def __init__(self):
        self.db_path = st.secrets["DATABASE_URL"]
        self.engine = self.create_engine(self.db_path)
        self.setup_database()

    def create_engine(self, db_path):
        # Pooling-Einstellungen Datenbank
        return create_engine(
            db_path,
            pool_size=10,       # Maximale Anzahl der Verbindungen im Pool
            max_overflow=5,     # Anzahl der Verbindungen, die über den Pool hinaus erstellt werden können
            pool_timeout=30,    # Maximale Wartezeit, um eine Verbindung zu erhalten
            pool_pre_ping=True   # Automatischer Ping, um sicherzustellen, dass die Verbindung gültig ist
        )
        
    def setup_database(self):
        with self.engine.connect() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS recipes (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    meal_type VARCHAR(25),
                    preparation TEXT
                );"""))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS ingredients (
                    id SERIAL PRIMARY KEY,
                    recipe_id INTEGER REFERENCES recipes(id) ON DELETE CASCADE,
                    name VARCHAR(100) NOT NULL,
                    amount DECIMAL(10,2) NOT NULL,
                    unit VARCHAR(10) NOT NULL,
                    category VARCHAR(50) NOT NULL
                );"""))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS selected_recipes (
                    recipe_id INTEGER PRIMARY KEY REFERENCES recipes(id) ON DELETE CASCADE
                );"""))

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS additional_ingredients (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    amount DECIMAL(10,2) DEFAULT 1,
                    unit VARCHAR(10) DEFAULT 'Stk'
                );"""))
            conn.commit()

    # ------- #
    # RECIPES #
    # ------- #
    def get_all_recipes(self):
        return pd.read_sql("SELECT * FROM recipes", self.engine)

    def get_selected_recipes(self):
        return pd.read_sql("SELECT * FROM selected_recipes", self.engine)

    def update_selected_recipes(self, recipe_ids: List[int]):
        with self.engine.connect() as conn:
            # Delete all existing selected recipes
            conn.execute(text("DELETE FROM selected_recipes"))

            # Insert new selected recipes if any
            if recipe_ids:
                conn.execute(
                    text("INSERT INTO selected_recipes (recipe_id) VALUES (:recipe_id)"),
                    [{"recipe_id": id} for id in recipe_ids])
            conn.commit()

    def get_recipe_details(self, recipe_id: int):
        recipe = pd.read_sql("SELECT * FROM recipes WHERE id = %s", self.engine, params=(recipe_id,))
        recipe = recipe.to_dict(orient="records")[0] # Use as dict

        ingredients = pd.read_sql("SELECT * FROM ingredients WHERE recipe_id = %s", self.engine, params=(recipe_id,))

        return recipe, ingredients

    # ----------- #
    # INGREDIENTS #
    # ----------- #
    def clear_additional_ingredients(self):
        with self.engine.connect() as conn:
            conn.execute(text("DELETE FROM additional_ingredients"))
            conn.commit()

    # ------------ #
    # SHOPPINGLIST #
    # ------------ #
    def get_shopping_list(self):
        ingredients = pd.read_sql('''
                SELECT i.name, i.category, 
                       SUM(i.amount) as total_amount, 
                       i.unit
                FROM ingredients i
                JOIN selected_recipes sr ON i.recipe_id = sr.recipe_id
                GROUP BY i.name, i.unit, i.category
                
                UNION
                
                SELECT a.name, 'Sonstiges' as category, 
                       COUNT(*) as total_amount, 
                       'Stk' as unit
                FROM additional_ingredients a
                GROUP BY a.name''', self.engine)

        ingredients = ingredients.sort_values(["category", "name"])
        return ingredients

    def add_additional_ingredient(self, name: str, amount: float=1, unit: str='Stk'):
        with self.engine.connect() as conn:
            conn.execute(
                text("INSERT INTO additional_ingredients (name, amount, unit) VALUES (:name, :amount, :unit)"),
                {"name": name.capitalize(), "amount": amount, "unit": unit}
            )
            conn.commit()

    # ---------- #
    # NEW RECIPE #
    # ---------- #

    def add_recipe(self, meal_type: str, name: str, preparation: str, ingredients: List[Tuple[str, float, str, str]]):
        with self.engine.connect() as conn:
            conn.execute(
                text("INSERT INTO recipes (meal_type, name, preparation) VALUES (:meal_type, :name, :preparation)"),
                {'meal_type': meal_type, 'name': name, 'preparation': preparation}
            )
            conn.commit()
            recipe_id = pd.read_sql("SELECT id FROM recipes WHERE name = %s", self.engine, params=(name,)).iloc[0, 0]

            for ingredient in ingredients:
                conn.execute(text(
                    """INSERT INTO ingredients 
                    (recipe_id, name, amount, unit, category) 
                    VALUES (:recipe_id, :name, :amount, :unit, :category)"""),
                    {"recipe_id": int(recipe_id),
                    "name": ingredient[0],
                    "amount": ingredient[1],
                    "unit": ingredient[2],
                    "category": ingredient[3]}
                )    
            conn.commit()

    # ----------- #
    # EDIT RECIPE #
    # ----------- #
    def edit_recipe(self, recipe_id: int, meal_type: str, name: str, preparation: str, ingredients: list):
        with self.engine.connect() as conn:
            # Update recipe details
            conn.execute(text('''UPDATE recipes 
                                 SET meal_type = :meal_type, 
                                     name = :name, 
                                     preparation = :preparation 
                                 WHERE id = :recipe_id'''),
                        {"recipe_id": recipe_id, 
                        "meal_type": meal_type, 
                        "name": name, 
                        "preparation": preparation})
            conn.commit()

            # Update ingredients
            conn.execute(text("DELETE FROM ingredients WHERE recipe_id = :recipe_id"), {"recipe_id": recipe_id})
            conn.commit()

            for ing_name, amount, unit, category in ingredients:
                conn.execute(text("""
                    INSERT INTO ingredients (recipe_id, name, amount, unit, category) VALUES (:recipe_id, :name, :amount, :unit, :category)"""),
                {"recipe_id": recipe_id, 
                "name": ing_name, 
                "amount": amount, 
                "unit": unit, 
                "category": category})
            conn.commit()

        return True

    def delete_recipe(self, recipe_id: int):
        with self.engine.connect() as conn:
            # Delete the recipe
            conn.execute(text("DELETE FROM recipes WHERE id = :recipe_id"), {"recipe_id": recipe_id})
            # Also delete associated ingredients
            conn.execute(text("DELETE FROM ingredients WHERE recipe_id = :recipe_id"), {"recipe_id": recipe_id})
            conn.commit()
        return True


# Predefined lists
MEAL_TYPES = ["Frühstück", "Mittagessen", "Abendessen", "Snack", "Backen"]
UNITS = ["g", "ml", "EL", "TL", "Stk"]
CATEGORIES = [
    "Obst & Gemüse",
    "Fleisch & Fisch",
    "Aufschnitt & Aufstrich",
    "Milchprodukte & Eier",
    "Brot & Backwaren",
    "Müsli & Cerealien",
    "Konserven & Öle",
    "Nudeln & Reis",
    "Tiefkühl",
    "Sonstiges"
]
