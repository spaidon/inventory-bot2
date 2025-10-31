"""
ISTHT Founty Inventory Management Bot - Debian Ready Version
Smart Telegram Bot for School/Institution Inventory Tracking
Complete with Database, Admin Panel, Color Management
Author: Inventory System Team
Date: November 2025
"""

import logging
import os
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)
import json
import csv
from datetime import datetime
from pathlib import Path
import sqlite3
from typing import Dict, List, Optional
import re

# ==================== CONFIGURATION ====================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot Settings
BOT_TOKEN = os.environ.get('BOT_TOKEN', 'YOUR_BOT_TOKEN_HERE')
ADMIN_PIN = "1234"  # CHANGE THIS TO YOUR SECURE PIN!
CONFIG_FILE = "config.json"
DB_FILE = "inventory.db"

# Conversation States
(MAIN_MENU, SELECT_ROLE, ADMIN_PIN_STATE, SELECT_ROOM, SELECT_MATERIAL,
 ENTER_TOTAL, ENTER_BROKEN, SELECT_CONDITION, CONFIRM_ENTRY,
 ADMIN_MENU, MANAGE_ROOMS, MANAGE_MATERIALS, SEARCH_QUERY,
 FEEDBACK_INPUT, ADD_ROOM, REMOVE_ROOM, ADD_MATERIAL, REMOVE_MATERIAL,
 VIEW_DASHBOARD, ROOM_DETAILS, MANAGE_COLORS, ADD_COLOR, EDIT_COLOR, SELECT_COLOR) = range(24)

# Emojis
EMOJIS = {
    "chair": "🪑", "table": "📋", "pc": "🖥️", "projector": "📽️",
    "board": "🎯", "window": "🪟", "door": "🚪", "user": "👤",
    "admin": "🔐", "check": "✅", "warning": "⚠️", "search": "🔍",
    "export": "📤", "feedback": "💬", "dashboard": "📊", "chart": "📈",
    "refresh": "🔄", "restart": "🔄", "color": "🎨"
}

# ==================== DATABASE MANAGER ====================

class DatabaseManager:
    """Handles all database operations"""
    
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.init_database()
    
    def init_database(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            role TEXT DEFAULT 'user',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Rooms table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS rooms (
            room_id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_name TEXT UNIQUE NOT NULL,
            room_type TEXT,
            location TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Materials table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            material_id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_name TEXT UNIQUE NOT NULL,
            emoji TEXT,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Chair colors table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS chair_colors (
            color_id INTEGER PRIMARY KEY AUTOINCREMENT,
            color_name TEXT UNIQUE NOT NULL,
            color_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Inventory entries table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory_entries (
            entry_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            room_id INTEGER,
            material_id INTEGER,
            color_id INTEGER,
            total_count INTEGER NOT NULL,
            broken_count INTEGER NOT NULL,
            good_count INTEGER,
            condition TEXT,
            location_details TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id),
            FOREIGN KEY (room_id) REFERENCES rooms(room_id),
            FOREIGN KEY (material_id) REFERENCES materials(material_id),
            FOREIGN KEY (color_id) REFERENCES chair_colors(color_id)
        )
        """)
        
        # Feedback table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            feedback_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            feedback_text TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
        """)
        
        conn.commit()
        conn.close()
        logger.info("✅ Database initialized successfully")
    
    def add_user(self, user_id: int, username: str, first_name: str, last_name: str):
        """Add or update user"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
        """, (user_id, username, first_name, last_name))
        conn.commit()
        conn.close()
    
    def add_inventory_entry(self, user_id: int, room_name: str, material_name: str,
                           total: int, broken: int, condition: str, color_id: int = None):
        """Add inventory entry"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute("SELECT room_id FROM rooms WHERE room_name = ?", (room_name,))
        room = cursor.fetchone()
        if not room:
            cursor.execute("INSERT INTO rooms (room_name) VALUES (?)", (room_name,))
            room_id = cursor.lastrowid
        else:
            room_id = room[0]
        
        cursor.execute("SELECT material_id FROM materials WHERE material_name = ?", (material_name,))
        material = cursor.fetchone()
        if not material:
            conn.close()
            return False
        material_id = material[0]
        
        good_count = total - broken
        cursor.execute("""
        INSERT INTO inventory_entries
        (user_id, room_id, material_id, color_id, total_count, broken_count, good_count, condition)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, room_id, material_id, color_id, total, broken, good_count, condition))
        
        conn.commit()
        conn.close()
        return True
    
    def get_rooms(self) -> List[str]:
        """Get all rooms"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT room_name FROM rooms ORDER BY room_name")
        rooms = [row[0] for row in cursor.fetchall()]
        conn.close()
        return rooms
    
    def get_materials(self) -> List[Dict]:
        """Get all materials"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT material_name, emoji FROM materials ORDER BY material_name")
        materials = [{"name": row[0], "emoji": row[1]} for row in cursor.fetchall()]
        conn.close()
        return materials
    
    def get_chair_colors(self) -> List[Dict]:
        """Get all chair colors"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("SELECT color_id, color_name, color_code FROM chair_colors ORDER BY color_name")
        colors = [{"id": row[0], "name": row[1], "code": row[2]} for row in cursor.fetchall()]
        conn.close()
        return colors
    
    def add_chair_color(self, color_name: str, color_code: str = "") -> bool:
        """Add new chair color"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO chair_colors (color_name, color_code) VALUES (?, ?)",
                         (color_name, color_code))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    def update_chair_color(self, color_id: int, color_name: str, color_code: str) -> bool:
        """Update chair color"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("UPDATE chair_colors SET color_name = ?, color_code = ? WHERE color_id = ?",
                      (color_name, color_code, color_id))
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        return updated
    
    def delete_chair_color(self, color_id: int) -> bool:
        """Delete chair color"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chair_colors WHERE color_id = ?", (color_id,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted
    
    def get_dashboard_stats(self) -> Dict:
        """Get dashboard statistics"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        stats = {}
        
        cursor.execute("SELECT COUNT(*) FROM inventory_entries")
        stats['total_entries'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT SUM(total_count) FROM inventory_entries")
        stats['total_items'] = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(broken_count) FROM inventory_entries")
        stats['total_broken'] = cursor.fetchone()[0] or 0
        
        cursor.execute("SELECT SUM(good_count) FROM inventory_entries")
        stats['total_good'] = cursor.fetchone()[0] or 0
        
        if stats['total_items'] > 0:
            stats['broken_percentage'] = round((stats['total_broken'] / stats['total_items']) * 100, 2)
            stats['good_percentage'] = round((stats['total_good'] / stats['total_items']) * 100, 2)
        else:
            stats['broken_percentage'] = 0
            stats['good_percentage'] = 0
        
        cursor.execute("SELECT COUNT(*) FROM rooms")
        stats['total_rooms'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM materials")
        stats['total_materials'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT user_id) FROM inventory_entries")
        stats['active_users'] = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM inventory_entries WHERE timestamp > datetime('now', '-1 day')")
        stats['entries_24h'] = cursor.fetchone()[0]
        
        conn.close()
        return stats
    
    def export_to_csv(self, filename: str):
        """Export data to CSV"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""
        SELECT u.username, r.room_name, m.material_name,
        ie.total_count, ie.broken_count, ie.good_count, ie.condition, ie.timestamp
        FROM inventory_entries ie
        JOIN users u ON ie.user_id = u.user_id
        JOIN rooms r ON ie.room_id = r.room_id
        JOIN materials m ON ie.material_id = m.material_id
        ORDER BY ie.timestamp DESC
        """)
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['User', 'Room', 'Material', 'Total', 'Broken', 'Good', 'Condition', 'Timestamp'])
            writer.writerows(cursor.fetchall())
        
        conn.close()
        return filename
    
    def add_room(self, room_name: str) -> bool:
        """Add new room"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO rooms (room_name) VALUES (?)", (room_name,))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    def remove_room(self, room_name: str) -> bool:
        """Remove room"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM rooms WHERE room_name = ?", (room_name,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted
    
    def add_material(self, material_name: str, emoji: str = "📦") -> bool:
        """Add new material"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO materials (material_name, emoji) VALUES (?, ?)",
                         (material_name, emoji))
            conn.commit()
            conn.close()
            return True
        except sqlite3.IntegrityError:
            conn.close()
            return False
    
    def remove_material(self, material_name: str) -> bool:
        """Remove material"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM materials WHERE material_name = ?", (material_name,))
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted
    
    def add_feedback(self, user_id: int, feedback_text: str):
        """Add user feedback"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO feedback (user_id, feedback_text) VALUES (?, ?)",
                      (user_id, feedback_text))
        conn.commit()
        conn.close()

# ==================== CONFIG MANAGER ====================

class ConfigManager:
    """Manages bot configuration"""
    
    def __init__(self, config_file: str):
        self.config_file = config_file
        self.load_config()
    
    def load_config(self):
        """Load or create default config"""
        if Path(self.config_file).exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        else:
            self.config = self.get_default_config()
            self.save_config()
    
    def get_default_config(self):
        """Get default configuration"""
        return {
            "default_rooms": [
                "Classe MH202", "Salle de Formation 1", "Salle de Formation 2",
                "Atelier Pratique 1", "Atelier Pratique 2",
                "Bureau Administratif", "Espace Commun",
                "LAB Informatique", "Bibliothèque"
            ],
            "default_materials": [
                {"name": "Chaises", "emoji": "🪑"},
                {"name": "Tables", "emoji": "📋"},
                {"name": "Fenêtres", "emoji": "🪟"},
                {"name": "Portes", "emoji": "🚪"},
                {"name": "Datashows", "emoji": "📽️"},
                {"name": "Ordinateurs", "emoji": "🖥️"},
                {"name": "Tableaux", "emoji": "🎯"}
            ],
            "default_chair_colors": [
                {"name": "Rouge", "code": "#FF0000"},
                {"name": "Bleu", "code": "#0000FF"},
                {"name": "Vert", "code": "#00FF00"},
                {"name": "Jaune", "code": "#FFFF00"},
                {"name": "Noir", "code": "#000000"},
                {"name": "Blanc", "code": "#FFFFFF"}
            ],
            "conditions": ["Neuf", "Bon état", "État moyen", "Cassé", "Manquant", "Déplacé"],
            "admin_pin": ADMIN_PIN
        }
    
    def save_config(self):
        """Save configuration"""
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

# ==================== INITIALIZE MANAGERS ====================

db = DatabaseManager(DB_FILE)
config_manager = ConfigManager(CONFIG_FILE)

def seed_database():
    """Seed database with default data"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    for room in config_manager.config["default_rooms"]:
        cursor.execute("INSERT OR IGNORE INTO rooms (room_name) VALUES (?)", (room,))
    
    for material in config_manager.config["default_materials"]:
        cursor.execute("INSERT OR IGNORE INTO materials (material_name, emoji) VALUES (?, ?)",
                      (material["name"], material["emoji"]))
    
    for color in config_manager.config.get("default_chair_colors", []):
        cursor.execute("INSERT OR IGNORE INTO chair_colors (color_name, color_code) VALUES (?, ?)",
                      (color["name"], color["code"]))
    
    conn.commit()
    conn.close()
    logger.info("✅ Database seeded with default data")

seed_database()

# ==================== COMMAND HANDLERS ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    context.user_data.clear()
    user = update.effective_user
    db.add_user(user.id, user.username, user.first_name, user.last_name)
    
    welcome_text = f"""
🏫 **Système d'Inventaire ISTHT Founty**
Bienvenue {user.first_name}!

**Choisissez votre rôle:**
"""
    
    keyboard = [
        [InlineKeyboardButton(f"{EMOJIS['user']} Utilisateur", callback_data="role_user")],
        [InlineKeyboardButton(f"{EMOJIS['admin']} Administrateur", callback_data="role_admin")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
        await update.callback_query.edit_message_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')
    
    return SELECT_ROLE

async def select_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle role selection"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "role_user":
        context.user_data['role'] = 'user'
        return await show_room_selection(update, context)
    elif query.data == "role_admin":
        await query.edit_message_text(
            f"{EMOJIS['admin']} **Accès Administrateur**\n\nVeuillez entrer le code PIN:",
            parse_mode='Markdown'
        )
        return ADMIN_PIN_STATE

async def verify_admin_pin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify admin PIN"""
    pin = update.message.text.strip()
    
    if pin == config_manager.config["admin_pin"]:
        context.user_data['role'] = 'admin'
        await update.message.reply_text(f"{EMOJIS['check']} Accès accordé!", parse_mode='Markdown')
        return await show_admin_menu(update, context)
    else:
        await update.message.reply_text(
            f"{EMOJIS['warning']} Code PIN incorrect. Utilisez /start pour réessayer"
        )
        return ConversationHandler.END

async def show_room_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show room selection"""
    rooms = db.get_rooms()
    
    if not rooms:
        text = "❌ Aucune salle disponible."
        if update.callback_query:
            await update.callback_query.edit_message_text(text)
        return ConversationHandler.END
    
    keyboard = []
    for room in rooms:
        keyboard.append([InlineKeyboardButton(f"🏫 {room}", callback_data=f"room_{room}")])
    keyboard.append([InlineKeyboardButton("« Retour", callback_data="back_to_start")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "**Sélectionnez une salle:**"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    return SELECT_ROOM

async def select_room(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle room selection"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "back_to_start":
        return await start(update, context)
    
    room_name = query.data.replace("room_", "")
    context.user_data['selected_room'] = room_name
    
    materials = db.get_materials()
    keyboard = []
    for material in materials:
        emoji = material['emoji']
        name = material['name']
        keyboard.append([InlineKeyboardButton(f"{emoji} {name}", callback_data=f"material_{name}")])
    keyboard.append([InlineKeyboardButton("« Retour", callback_data="back_to_rooms")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"**Salle:** {room_name}\n\n**Choisissez un matériel:**",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    
    return SELECT_MATERIAL

async def select_material(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle material selection"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "back_to_rooms":
        return await show_room_selection(update, context)
    
    material_name = query.data.replace("material_", "")
    context.user_data['selected_material'] = material_name
    
    # Check if material is chairs
    if material_name == "Chaises":
        colors = db.get_chair_colors()
        if colors:
            keyboard = []
            for color in colors:
                keyboard.append([InlineKeyboardButton(
                    f"🎨 {color['name']}",
                    callback_data=f"chaircolor_{color['id']}"
                )])
            keyboard.append([InlineKeyboardButton("Aucune couleur", callback_data="chaircolor_none")])
            keyboard.append([InlineKeyboardButton("« Retour", callback_data="back_to_materials")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"**Salle:** {context.user_data['selected_room']}\n"
                f"**Matériel:** Chaises\n\n**Choisissez la couleur:**",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return SELECT_COLOR
    
    await query.edit_message_text(
        f"**Salle:** {context.user_data['selected_room']}\n"
        f"**Matériel:** {material_name}\n\n"
        f"Entrez le **nombre total**:",
        parse_mode='Markdown'
    )
    
    return ENTER_TOTAL

async def select_chair_color(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle chair color selection"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "back_to_materials":
        room_name = context.user_data['selected_room']
        materials = db.get_materials()
        keyboard = []
        for material in materials:
            keyboard.append([InlineKeyboardButton(
                f"{material['emoji']} {material['name']}",
                callback_data=f"material_{material['name']}"
            )])
        keyboard.append([InlineKeyboardButton("« Retour", callback_data="back_to_rooms")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"**Salle:** {room_name}\n\n**Choisissez un matériel:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        return SELECT_MATERIAL
    
    if query.data == "chaircolor_none":
        context.user_data['color_id'] = None
        context.user_data['color_name'] = "Non spécifiée"
    else:
        color_id = int(query.data.replace("chaircolor_", ""))
        context.user_data['color_id'] = color_id
        colors = db.get_chair_colors()
        color_name = next((c['name'] for c in colors if c['id'] == color_id), "Inconnue")
        context.user_data['color_name'] = color_name
    
    await query.edit_message_text(
        f"**Salle:** {context.user_data['selected_room']}\n"
        f"**Matériel:** Chaises\n"
        f"**Couleur:** {context.user_data['color_name']}\n\n"
        f"Entrez le **nombre total**:",
        parse_mode='Markdown'
    )
    
    return ENTER_TOTAL

async def enter_total(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle total count input"""
    try:
        total = int(update.message.text.strip())
        if total < 0:
            raise ValueError("Negative number")
        
        context.user_data['total'] = total
        
        await update.message.reply_text(
            f"Total: {total}\n\nEntrez le **nombre cassé/endommagé**:",
            parse_mode='Markdown'
        )
        
        return ENTER_BROKEN
    except ValueError:
        await update.message.reply_text(
            f"{EMOJIS['warning']} Nombre invalide. Entrez un nombre positif."
        )
        return ENTER_TOTAL

async def enter_broken(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle broken count input"""
    try:
        broken = int(update.message.text.strip())
        total = context.user_data['total']
        
        if broken < 0 or broken > total:
            raise ValueError("Invalid broken count")
        
        context.user_data['broken'] = broken
        
        conditions = config_manager.config["conditions"]
        keyboard = []
        for condition in conditions:
            keyboard.append([InlineKeyboardButton(condition, callback_data=f"condition_{condition}")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"Cassés: {broken}\n\n**Sélectionnez l'état:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return SELECT_CONDITION
    except ValueError:
        await update.message.reply_text(
            f"{EMOJIS['warning']} Nombre invalide."
        )
        return ENTER_BROKEN

async def select_condition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle condition selection"""
    query = update.callback_query
    await query.answer()
    
    condition = query.data.replace("condition_", "")
    context.user_data['condition'] = condition
    
    room = context.user_data['selected_room']
    material = context.user_data['selected_material']
    total = context.user_data['total']
    broken = context.user_data['broken']
    good = total - broken
    
    color_info = ""
    if material == "Chaises" and 'color_name' in context.user_data:
        color_info = f"🎨 **Couleur:** {context.user_data['color_name']}\n"
    
    broken_pct = round((broken / total * 100), 1) if total > 0 else 0
    
    summary = f"""
**📝 Confirmation**

🏫 **Salle:** {room}

📦 **Matériel:** {material}

{color_info}

━━━━━━━━━━━━━━━━━━━━

🔢 **Total:** {total}

✅ **Bon état:** {good} ({100-broken_pct}%)

❌ **Cassés:** {broken} ({broken_pct}%)

🏷️ **État:** {condition}

**Confirmer cette entrée?**
"""
    
    keyboard = [
        [InlineKeyboardButton(f"{EMOJIS['check']} Confirmer", callback_data="confirm_yes")],
        [InlineKeyboardButton(f"{EMOJIS['refresh']} Rester", callback_data="confirm_stay")],
        [InlineKeyboardButton("❌ Annuler", callback_data="confirm_no")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(summary, reply_markup=reply_markup, parse_mode='Markdown')
    
    return CONFIRM_ENTRY

async def confirm_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle entry confirmation"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "confirm_yes":
        user_id = update.effective_user.id
        room = context.user_data['selected_room']
        material = context.user_data['selected_material']
        total = context.user_data['total']
        broken = context.user_data['broken']
        condition = context.user_data['condition']
        color_id = context.user_data.get('color_id', None)
        
        success = db.add_inventory_entry(user_id, room, material, total, broken, condition, color_id)
        
        if success:
            await query.edit_message_text(
                f"{EMOJIS['check']} **Enregistré avec succès!**\n\n"
                f"Utilisez /start pour continuer.",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                f"{EMOJIS['warning']} Erreur. Utilisez /start pour réessayer."
            )
        
        context.user_data.clear()
        return ConversationHandler.END
    
    elif query.data == "confirm_stay":
        user_id = update.effective_user.id
        room = context.user_data['selected_room']
        material = context.user_data['selected_material']
        total = context.user_data['total']
        broken = context.user_data['broken']
        condition = context.user_data['condition']
        color_id = context.user_data.get('color_id', None)
        
        success = db.add_inventory_entry(user_id, room, material, total, broken, condition, color_id)
        
        if success:
            selected_room = context.user_data['selected_room']
            context.user_data.clear()
            context.user_data['selected_room'] = selected_room
            
            materials = db.get_materials()
            keyboard = []
            for mat in materials:
                keyboard.append([InlineKeyboardButton(f"{mat['emoji']} {mat['name']}", callback_data=f"material_{mat['name']}")])
            keyboard.append([InlineKeyboardButton("« Changer de salle", callback_data="back_to_rooms")])
            keyboard.append([InlineKeyboardButton("🏠 Menu", callback_data="back_to_start")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"{EMOJIS['check']} **Enregistré!**\n\n"
                f"**Salle:** {selected_room}\n**Ajouter un autre matériel:**",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return SELECT_MATERIAL
        else:
            await query.edit_message_text(f"{EMOJIS['warning']} Erreur.")
            context.user_data.clear()
            return ConversationHandler.END
    
    else:  # confirm_no
        await query.edit_message_text("❌ Annulé. Utilisez /start pour recommencer.")
        context.user_data.clear()
        return ConversationHandler.END

async def show_admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show admin menu"""
    keyboard = [
        [InlineKeyboardButton(f"{EMOJIS['dashboard']} Tableau de Bord", callback_data="admin_dashboard")],
        [InlineKeyboardButton(f"{EMOJIS['color']} Gérer Couleurs", callback_data="admin_manage_colors")],
        [InlineKeyboardButton("➕ Ajouter Salle", callback_data="admin_add_room")],
        [InlineKeyboardButton("➖ Supprimer Salle", callback_data="admin_remove_room")],
        [InlineKeyboardButton("➕ Ajouter Matériel", callback_data="admin_add_material")],
        [InlineKeyboardButton("➖ Supprimer Matériel", callback_data="admin_remove_material")],
        [InlineKeyboardButton(f"{EMOJIS['export']} Exporter CSV", callback_data="admin_export")],
        [InlineKeyboardButton("« Retour", callback_data="back_to_start")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"{EMOJIS['admin']} **Menu Administrateur**\n\nChoisissez une action:"
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    return ADMIN_MENU

async def show_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show dashboard"""
    query = update.callback_query
    await query.answer("Génération du tableau de bord...")
    
    stats = db.get_dashboard_stats()
    
    dashboard = f"""
{EMOJIS['dashboard']} **TABLEAU DE BORD**

📊 **Statistiques Globales**

━━━━━━━━━━━━━━━━━━━━

📦 Total articles: **{stats['total_items']}**

✅ Bon état: **{stats['total_good']}** ({stats['good_percentage']}%)

❌ Cassés: **{stats['total_broken']}** ({stats['broken_percentage']}%)

🏫 Salles: **{stats['total_rooms']}**

📋 Matériels: **{stats['total_materials']}**

👥 Utilisateurs: **{stats['active_users']}**

📝 Entrées: **{stats['total_entries']}**

🕐 24h: **{stats['entries_24h']}** entrées
"""
    
    keyboard = [
        [InlineKeyboardButton(f"{EMOJIS['refresh']} Actualiser", callback_data="admin_dashboard")],
        [InlineKeyboardButton("« Retour", callback_data="back_to_admin")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(dashboard, reply_markup=reply_markup, parse_mode='Markdown')
    
    return ADMIN_MENU

async def manage_colors_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show color management menu"""
    query = update.callback_query
    await query.answer()
    
    colors = db.get_chair_colors()
    
    text = f"{EMOJIS['color']} **Gestion des Couleurs de Chaises**\n\n"
    text += f"**Couleurs:** {len(colors)}\n\n"
    
    for color in colors:
        text += f"🎨 {color['name']} ({color['code']})\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ Ajouter", callback_data="color_add")],
        [InlineKeyboardButton("❌ Supprimer", callback_data="color_delete")],
        [InlineKeyboardButton("« Retour", callback_data="back_to_admin")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    return MANAGE_COLORS

async def handle_color_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle color management actions"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "color_add":
        await query.edit_message_text(
            "**Ajouter une couleur**\n\nEntrez: Nom #Code\nEx: Orange #FFA500",
            parse_mode='Markdown'
        )
        return ADD_COLOR
    
    elif query.data == "color_delete":
        colors = db.get_chair_colors()
        if not colors:
            await query.edit_message_text("Aucune couleur.")
            return await manage_colors_menu(update, context)
        
        keyboard = []
        for color in colors:
            keyboard.append([InlineKeyboardButton(
                f"❌ {color['name']}",
                callback_data=f"delcolor_{color['id']}"
            )])
        keyboard.append([InlineKeyboardButton("« Retour", callback_data="back_to_colors")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "**Supprimer une couleur:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return MANAGE_COLORS
    
    elif query.data == "back_to_colors":
        return await manage_colors_menu(update, context)
    
    elif query.data.startswith("delcolor_"):
        color_id = int(query.data.replace("delcolor_", ""))
        if db.delete_chair_color(color_id):
            await query.edit_message_text(f"{EMOJIS['check']} Couleur supprimée!")
        else:
            await query.edit_message_text(f"{EMOJIS['warning']} Erreur.")
        
        return await manage_colors_menu(update, context)
    
    elif query.data == "back_to_admin":
        return await show_admin_menu(update, context)
    
    return MANAGE_COLORS

async def add_color_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle adding a new color"""
    text = update.message.text.strip()
    
    parts = text.split('#')
    color_name = parts[0].strip()
    color_code = f"#{parts[1].strip()}" if len(parts) > 1 else ""
    
    if db.add_chair_color(color_name, color_code):
        await update.message.reply_text(
            f"{EMOJIS['check']} Couleur '{color_name}' ajoutée!",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"{EMOJIS['warning']} Cette couleur existe déjà!"
        )
    
    return await show_admin_menu(update, context)

async def handle_admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin menu actions"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "admin_dashboard":
        return await show_dashboard(update, context)
    
    elif query.data == "admin_manage_colors":
        return await manage_colors_menu(update, context)
    
    elif query.data == "admin_export":
        filename = f"inventory_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        db.export_to_csv(filename)
        
        with open(filename, 'rb') as f:
            await query.message.reply_document(
                document=f,
                filename=filename,
                caption=f"{EMOJIS['export']} Export ISTHT Founty"
            )
        
        Path(filename).unlink()
        return await show_admin_menu(update, context)
    
    elif query.data == "admin_add_room":
        await query.edit_message_text(
            "**Ajouter une salle**\n\nEntrez le nom:",
            parse_mode='Markdown'
        )
        return ADD_ROOM
    
    elif query.data == "admin_remove_room":
        rooms = db.get_rooms()
        keyboard = []
        for room in rooms:
            keyboard.append([InlineKeyboardButton(f"❌ {room}", callback_data=f"delroom_{room}")])
        keyboard.append([InlineKeyboardButton("« Retour", callback_data="back_to_admin")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "**Supprimer une salle:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return REMOVE_ROOM
    
    elif query.data == "admin_add_material":
        await query.edit_message_text(
            "**Ajouter un matériel**\n\nEntrez: emoji nom\nEx: 🪑 Chaises",
            parse_mode='Markdown'
        )
        return ADD_MATERIAL
    
    elif query.data == "admin_remove_material":
        materials = db.get_materials()
        keyboard = []
        for material in materials:
            keyboard.append([InlineKeyboardButton(
                f"❌ {material['emoji']} {material['name']}",
                callback_data=f"delmat_{material['name']}"
            )])
        keyboard.append([InlineKeyboardButton("« Retour", callback_data="back_to_admin")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "**Supprimer un matériel:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return REMOVE_MATERIAL
    
    elif query.data == "back_to_admin":
        return await show_admin_menu(update, context)
    
    elif query.data == "back_to_start":
        context.user_data.clear()
        return await start(update, context)
    
    # Handle delete callbacks
    elif query.data.startswith("delroom_"):
        room_name = query.data.replace("delroom_", "")
        if db.remove_room(room_name):
            await query.edit_message_text(f"{EMOJIS['check']} Salle supprimée!")
        else:
            await query.edit_message_text(f"{EMOJIS['warning']} Erreur.")
        return await show_admin_menu(update, context)
    
    elif query.data.startswith("delmat_"):
        material_name = query.data.replace("delmat_", "")
        if db.remove_material(material_name):
            await query.edit_message_text(f"{EMOJIS['check']} Matériel supprimé!")
        else:
            await query.edit_message_text(f"{EMOJIS['warning']} Erreur.")
        return await show_admin_menu(update, context)
    
    return ADMIN_MENU

async def add_room_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle adding a new room"""
    room_name = update.message.text.strip()
    
    if db.add_room(room_name):
        await update.message.reply_text(
            f"{EMOJIS['check']} Salle '{room_name}' ajoutée!",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            f"{EMOJIS['warning']} Cette salle existe déjà!"
        )
    
    return await show_admin_menu(update, context)

async def add_material_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle adding a new material"""
    text = update.message.text.strip()
    
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"
        u"\U0001F300-\U0001F5FF"
        u"\U0001F680-\U0001F6FF"
        u"\U0001F1E0-\U0001F1FF"
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    
    emoji_match = emoji_pattern.search(text)
    
    if emoji_match:
        emoji = emoji_match.group()
        material_name = text.replace(emoji, "").strip()
    else:
        emoji = "📦"
        material_name = text
    
    if db.add_material(material_name, emoji):
        await update.message.reply_text(
            f"{EMOJIS['check']} Matériel '{emoji} {material_name}' ajouté!"
        )
    else:
        await update.message.reply_text(
            f"{EMOJIS['warning']} Ce matériel existe déjà!"
        )
    
    return await show_admin_menu(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel conversation"""
    await update.message.reply_text("❌ Annulé. /start pour recommencer.")
    context.user_data.clear()
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = """
🆘 **Aide - Bot Inventaire ISTHT**

**Commandes:**
/start - Démarrer
/help - Cette aide
/stats - Statistiques
/cancel - Annuler

**Workflow Utilisateur:**
1. /start
2. Choisissez "Utilisateur"
3. Sélectionnez salle → matériel
4. Entrez quantités
5. Confirmez

**Pour Admins:**
• PIN requis
• Gérez salles/matériels
• Dashboard & export
• Gérez couleurs de chaises

Besoin d'aide? Contactez l'administrateur.
"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick stats"""
    stats = db.get_dashboard_stats()
    
    response = f"""
📊 **Statistiques Rapides**

📦 Total: **{stats['total_items']}** articles
✅ Bon: **{stats['total_good']}** ({stats['good_percentage']}%)
❌ Cassé: **{stats['total_broken']}** ({stats['broken_percentage']}%)
🏫 {stats['total_rooms']} salles
👥 {stats['active_users']} users
🕐 {stats['entries_24h']} entrées (24h)
"""
    
    await update.message.reply_text(response, parse_mode='Markdown')

# ==================== MAIN FUNCTION ====================

def main():
    """Main function"""
    if BOT_TOKEN == '8483609319:AAGsjpT8Nwb51BKiXMQBRJmdkni3Chdiv14':
        logger.error("❌ BOT_TOKEN not set! Set environment variable BOT_TOKEN")
        return
    
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Conversation handler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_ROLE: [CallbackQueryHandler(select_role)],
            ADMIN_PIN_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, verify_admin_pin)],
            SELECT_ROOM: [CallbackQueryHandler(select_room)],
            SELECT_MATERIAL: [CallbackQueryHandler(select_material)],
            SELECT_COLOR: [CallbackQueryHandler(select_chair_color)],
            ENTER_TOTAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_total)],
            ENTER_BROKEN: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_broken)],
            SELECT_CONDITION: [CallbackQueryHandler(select_condition)],
            CONFIRM_ENTRY: [CallbackQueryHandler(confirm_entry)],
            ADMIN_MENU: [CallbackQueryHandler(handle_admin_action)],
            ADD_ROOM: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_room_handler)],
            REMOVE_ROOM: [CallbackQueryHandler(handle_admin_action)],
            ADD_MATERIAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_material_handler)],
            REMOVE_MATERIAL: [CallbackQueryHandler(handle_admin_action)],
            MANAGE_COLORS: [CallbackQueryHandler(handle_color_action)],
            ADD_COLOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_color_handler)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('stats', stats_command))
    
    logger.info("🚀 Bot ISTHT Founty démarré avec succès!")
    logger.info("Bot running... Press Ctrl+C to stop")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
