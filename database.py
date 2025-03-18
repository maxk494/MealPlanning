import sqlite3
import pandas as pd
from typing import List, Tuple


class MealDatabase:
    def __init__(self, db_path: str = "meals.db"):
        self.db_path = db_path
        self.setup_database()

    def setup_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recipes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    meal_type TEXT NOT NULL,
                    name TEXT NOT NULL UNIQUE,
                    preparation TEXT NOT NULL
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS ingredients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipe_id INTEGER,
                    name TEXT NOT NULL,
                    amount REAL NOT NULL,
                    unit TEXT NOT NULL,
                    category TEXT NOT NULL,
                    FOREIGN KEY (recipe_id) REFERENCES recipes(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS selected_recipes (
                    recipe_id INTEGER PRIMARY KEY,
                    FOREIGN KEY (recipe_id) REFERENCES recipes(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS additional_ingredients (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL
                )
            """)

    def add_recipe(self, meal_type: str, name: str, preparation: str,
                   ingredients: List[Tuple[str, float, str, str]]):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO recipes (meal_type, name, preparation) VALUES (?, ?, ?)",
                (meal_type, name, preparation)
            )
            recipe_id = cursor.lastrowid

            for ingredient in ingredients:
                cursor.execute(
                    """INSERT INTO ingredients 
                    (recipe_id, name, amount, unit, category) 
                    VALUES (?, ?, ?, ?, ?)""",
                    (recipe_id, *ingredient)
                )

    def get_all_recipes(self):
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query("SELECT * FROM recipes", conn)

    def get_recipe_details(self, recipe_id: int):

        with sqlite3.connect(self.db_path) as conn:
            recipe = pd.read_sql_query(
                "SELECT * FROM recipes WHERE id = ?",
                conn,
                params=(recipe_id,)
            )
            ingredients = pd.read_sql_query(
                "SELECT * FROM ingredients WHERE recipe_id = ?",
                conn,
                params=(recipe_id,)
            )
            return recipe, ingredients

    def get_selected_recipes(self):
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(
                """SELECT r.* FROM recipes r 
                JOIN selected_recipes sr ON r.id = sr.recipe_id""",
                conn
            )

    def update_selected_recipes(self, recipe_ids: List[int]):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM selected_recipes")
            if len(recipe_ids) > 0:
                conn.executemany(
                    "INSERT INTO selected_recipes (recipe_id) VALUES (?)",
                    [(id,) for id in recipe_ids]
                )

    def get_shopping_list(self):
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(
                """SELECT i.name, i.category, SUM(i.amount) as total_amount, i.unit
                FROM ingredients i
                JOIN selected_recipes sr ON i.recipe_id = sr.recipe_id
                GROUP BY i.name, i.unit, i.category

                UNION ALL

                SELECT a.name, 'Sonstiges' as category, COUNT(*) as total_amount, 'Stk' as unit
                FROM additional_ingredients a
                GROUP BY a.name
                ORDER BY category, name""",
                conn
            )

    def get_recipe_by_name(self, name: str):
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql_query(
                "SELECT * FROM recipes WHERE name = ?",
                conn,
                params=(name,)
            )

    def edit_recipe(self, recipe_id: int, meal_type: str, name: str, preparation: str, ingredients: list):
        with sqlite3.connect(self.db_path) as conn:
            # Update recipe details
            conn.execute("UPDATE recipes SET meal_type = ?, name = ?, preparation = ? WHERE id = ?", (meal_type, name, preparation, recipe_id))
            # Update ingredients (this is a simplified example; you may need to handle this differently)
            conn.execute("DELETE FROM ingredients WHERE recipe_id = ?", (recipe_id,))
            for ing_name, amount, unit, category in ingredients:
                conn.execute("INSERT INTO ingredients (recipe_id, name, amount, unit, category) VALUES (?, ?, ?, ?, ?)", (recipe_id, ing_name, amount, unit, category))

        return True

    def delete_recipe(self, recipe_id: int):
        with sqlite3.connect(self.db_path) as conn:
            # Delete the recipe
            conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
            # Also delete associated ingredients
            conn.execute("DELETE FROM ingredients WHERE recipe_id = ?", (recipe_id,))

        return True

    def add_additional_ingredient(self, name):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                INSERT INTO additional_ingredients (name)
                VALUES (?)
            ''', (name,))

    def clear_additional_ingredients(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('DELETE FROM additional_ingredients')

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
