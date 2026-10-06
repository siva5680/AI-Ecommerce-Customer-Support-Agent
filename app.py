"""
AI E-Commerce Customer Support Agent
Complete implementation with Streamlit UI, SQLite database, and AI capabilities
Fixed for latest Streamlit version
"""

import streamlit as st
import sqlite3
import json
import re
import os
import bcrypt
import jwt
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import base64
from io import BytesIO
from PIL import Image

# ============================================
# CONFIGURATION & SETUP
# ============================================

# Initialize session state
if "user" not in st.session_state:
    st.session_state.user = None
if "token" not in st.session_state:
    st.session_state.token = None
if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "conversations" not in st.session_state:
    st.session_state.conversations = {}
if "selected_product" not in st.session_state:
    st.session_state.selected_product = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "page" not in st.session_state:
    st.session_state.page = "home"

# Constants
SECRET_KEY = "your-secret-key-change-in-production"
ALGORITHM = "HS256"
DB_PATH = "ecommerce.db"
IMAGES_DIR = "product_images"

# Create images directory if it doesn't exist
if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)

# ============================================
# DATABASE SETUP
# ============================================

def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            full_name TEXT NOT NULL,
            preferences TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Products table with image support
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            price REAL NOT NULL,
            category TEXT,
            brand TEXT,
            stock INTEGER DEFAULT 0,
            rating REAL DEFAULT 0,
            availability BOOLEAN DEFAULT 1,
            specifications TEXT,
            image_path TEXT,
            image_data TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Orders table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            shipping_address TEXT,
            tracking_number TEXT,
            shipping_updates TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    # Returns table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS returns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            refund_amount REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (product_id) REFERENCES products (id)
        )
    ''')
    
    # FAQs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS faqs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            category TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Cart table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (product_id) REFERENCES products (id),
            UNIQUE(user_id, product_id)
        )
    ''')
    
    # Reviews table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            rating INTEGER CHECK(rating >= 1 AND rating <= 5),
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Get database connection"""
    return sqlite3.connect(DB_PATH)

# ============================================
# IMAGE HANDLING
# ============================================

def encode_image_to_base64(image_file) -> str:
    """Convert image file to base64 string"""
    try:
        image = Image.open(image_file)
        buffered = BytesIO()
        
        # Convert to RGB if necessary
        if image.mode in ('RGBA', 'LA', 'P'):
            image = image.convert('RGB')
        
        # Resize image to reduce size
        max_size = (400, 400)
        image.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        image.save(buffered, format="JPEG", quality=70)
        return base64.b64encode(buffered.getvalue()).decode()
    except Exception as e:
        st.error(f"Error processing image: {e}")
        return None

def create_placeholder_image(color: str, text: str = "") -> str:
    """Create a placeholder image as base64"""
    try:
        img = Image.new('RGB', (300, 300), color=color)
        buffered = BytesIO()
        img.save(buffered, format="JPEG")
        return base64.b64encode(buffered.getvalue()).decode()
    except:
        # Fallback to a simple colored rectangle
        return base64.b64encode(b"R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7").decode()

# ============================================
# DATA LOADING & SEEDING
# ============================================

def seed_sample_data():
    """Seed database with sample products and FAQs"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if products exist
    cursor.execute("SELECT COUNT(*) FROM products")
    if cursor.fetchone()[0] == 0:
        # Sample products with image data
        sample_products = [
            {
                "name": "Sony WH-1000XM4 Wireless Headphones",
                "description": "Industry-leading noise canceling with Dual Noise Sensor technology. Premium sound quality with up to 30 hours battery life.",
                "price": 24990,
                "category": "Electronics",
                "brand": "Sony",
                "stock": 45,
                "rating": 4.8,
                "availability": 1,
                "specifications": json.dumps({"battery": "30 hours", "noise_cancellation": "Yes", "bluetooth": "5.0"}),
                "image_data": create_placeholder_image("#1a73e8")
            },
            {
                "name": "Boat Rockerz 450 Bluetooth Headphones",
                "description": "Wireless headphones with 15 hours battery life, Bluetooth 4.2, and comfortable over-ear design.",
                "price": 1499,
                "category": "Electronics",
                "brand": "Boat",
                "stock": 120,
                "rating": 4.2,
                "availability": 1,
                "specifications": json.dumps({"battery": "15 hours", "noise_cancellation": "No", "bluetooth": "4.2"}),
                "image_data": create_placeholder_image("#ff6b6b")
            },
            {
                "name": "Samsung Galaxy S24 Ultra",
                "description": "Latest flagship smartphone with 200MP camera, AI features, and S Pen support.",
                "price": 129999,
                "category": "Smartphones",
                "brand": "Samsung",
                "stock": 25,
                "rating": 4.9,
                "availability": 1,
                "specifications": json.dumps({"display": "6.8-inch Dynamic AMOLED", "camera": "200MP", "battery": "5000mAh"}),
                "image_data": create_placeholder_image("#1428a0")
            },
            {
                "name": "Apple iPhone 15 Pro Max",
                "description": "A17 Pro chip, Titanium design, 48MP main camera with 5x optical zoom.",
                "price": 159900,
                "category": "Smartphones",
                "brand": "Apple",
                "stock": 30,
                "rating": 4.8,
                "availability": 1,
                "specifications": json.dumps({"display": "6.7-inch Super Retina XDR", "camera": "48MP", "battery": "~29 hours"}),
                "image_data": create_placeholder_image("#555555")
            },
            {
                "name": "OnePlus 12",
                "description": "Snapdragon 8 Gen 3, 50MP main camera, 100W fast charging.",
                "price": 69999,
                "category": "Smartphones",
                "brand": "OnePlus",
                "stock": 40,
                "rating": 4.6,
                "availability": 1,
                "specifications": json.dumps({"display": "6.82-inch AMOLED", "camera": "50MP", "battery": "5400mAh"}),
                "image_data": create_placeholder_image("#b30000")
            },
            {
                "name": "Dell XPS 13 Laptop",
                "description": "13.4-inch InfinityEdge display, Intel Core i7, 16GB RAM, 512GB SSD.",
                "price": 119990,
                "category": "Laptops",
                "brand": "Dell",
                "stock": 15,
                "rating": 4.7,
                "availability": 1,
                "specifications": json.dumps({"display": "13.4-inch 4K UHD", "processor": "Intel Core i7", "ram": "16GB"}),
                "image_data": create_placeholder_image("#0078d4")
            },
            {
                "name": "MacBook Air M2",
                "description": "Apple M2 chip, 13.6-inch Liquid Retina display, Up to 18 hours battery life.",
                "price": 109900,
                "category": "Laptops",
                "brand": "Apple",
                "stock": 20,
                "rating": 4.9,
                "availability": 1,
                "specifications": json.dumps({"display": "13.6-inch Liquid Retina", "processor": "Apple M2", "ram": "8GB"}),
                "image_data": create_placeholder_image("#c0c0c0")
            },
            {
                "name": "Sony BRAVIA X90L 55-inch TV",
                "description": "4K HDR Smart TV with Cognitive Processor XR, Full Array LED display.",
                "price": 139990,
                "category": "Televisions",
                "brand": "Sony",
                "stock": 10,
                "rating": 4.7,
                "availability": 1,
                "specifications": json.dumps({"display": "55-inch 4K HDR", "processor": "Cognitive Processor XR", "smart": "Google TV"}),
                "image_data": create_placeholder_image("#000000")
            }
        ]
        
        for product in sample_products:
            cursor.execute('''
                INSERT INTO products (name, description, price, category, brand, stock, rating, availability, specifications, image_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (product["name"], product["description"], product["price"], product["category"], 
                  product["brand"], product["stock"], product["rating"], product["availability"], 
                  product["specifications"], product["image_data"]))
    
    # Check if FAQs exist
    cursor.execute("SELECT COUNT(*) FROM faqs")
    if cursor.fetchone()[0] == 0:
        sample_faqs = [
            {"question": "What payment methods do you accept?", 
             "answer": "We accept Credit Card, Debit Card, Net Banking, UPI, Cash on Delivery, and EMI options. All payments are secure and encrypted.", 
             "category": "Payments"},
            {"question": "How long does delivery take?", 
             "answer": "Standard delivery takes 3-5 business days. Express delivery is available for 1-2 business days with additional charges. Free delivery is offered on orders above ₹499.", 
             "category": "Delivery"},
            {"question": "What is your return policy?", 
             "answer": "We accept returns within 30 days of delivery. Items must be in original condition with tags. Refund is processed within 5-7 business days. Free returns for Prime members.", 
             "category": "Returns"},
            {"question": "Do you offer warranty on products?", 
             "answer": "Warranty varies by product category. Electronics come with 2 years manufacturer warranty, apparel has 1 year warranty, and home furnishings have 1 year warranty.", 
             "category": "Warranty"},
            {"question": "How can I track my order?", 
             "answer": "You can track your order using the tracking number sent via email. Visit our Order Tracking page and enter your order number.", 
             "category": "Orders"},
            {"question": "Can I cancel my order?", 
             "answer": "You can cancel your order within 1 hour of placing it. After that, please contact customer support for cancellation assistance.", 
             "category": "Orders"},
            {"question": "Do you offer gift wrapping?", 
             "answer": "Yes, we offer gift wrapping services for all products. You can select this option at checkout for a small additional fee.", 
             "category": "Services"},
            {"question": "How do I apply a discount coupon?", 
             "answer": "You can apply your coupon code at checkout in the 'Promo Code' section. The discount will be applied before payment confirmation.", 
             "category": "Payments"},
            {"question": "What is the estimated delivery time?", 
             "answer": "Estimated delivery time depends on your location. Typically 3-5 business days for metro cities and 5-7 business days for other areas.", 
             "category": "Delivery"}
        ]
        
        for faq in sample_faqs:
            cursor.execute('''
                INSERT INTO faqs (question, answer, category)
                VALUES (?, ?, ?)
            ''', (faq["question"], faq["answer"], faq["category"]))
    
    conn.commit()
    conn.close()

# ============================================
# AUTHENTICATION HELPERS
# ============================================

def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against hash"""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# ============================================
# BUSINESS LOGIC - TOOLS
# ============================================

class ECommerceTools:
    """Tools for e-commerce operations"""
    
    def __init__(self):
        self.db = get_db_connection()
        self.db.row_factory = sqlite3.Row
    
    def search_products(self, query: str, max_price: Optional[float] = None, category: Optional[str] = None) -> List[Dict]:
        """Search for products by name, description, or category"""
        cursor = self.db.cursor()
        
        # Parse query for price filter
        price_match = re.search(r'under\s*[₹$]?\s*([\d,]+)', query, re.IGNORECASE)
        if price_match and not max_price:
            max_price = float(price_match.group(1).replace(',', ''))
        
        # Build search query
        sql = '''
            SELECT * FROM products 
            WHERE (name LIKE ? OR description LIKE ? OR category LIKE ?)
        '''
        params = [f'%{query}%', f'%{query}%', f'%{query}%']
        
        if category:
            sql += ' AND category = ?'
            params.append(category)
        
        if max_price:
            sql += ' AND price <= ?'
            params.append(max_price)
        
        sql += ' ORDER BY rating DESC LIMIT 20'
        
        cursor.execute(sql, params)
        results = [dict(row) for row in cursor.fetchall()]
        
        # Parse specifications JSON
        for product in results:
            if product.get('specifications'):
                try:
                    product['specifications'] = json.loads(product['specifications'])
                except:
                    product['specifications'] = {}
        
        return results
    
    def get_all_categories(self) -> List[str]:
        """Get all product categories"""
        cursor = self.db.cursor()
        cursor.execute('SELECT DISTINCT category FROM products WHERE availability = 1')
        return [row[0] for row in cursor.fetchall() if row[0]]
    
    def get_product_by_id(self, product_id: int) -> Optional[Dict]:
        """Get product details by ID"""
        cursor = self.db.cursor()
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        if product:
            product_dict = dict(product)
            if product_dict.get('specifications'):
                try:
                    product_dict['specifications'] = json.loads(product_dict['specifications'])
                except:
                    product_dict['specifications'] = {}
            return product_dict
        return None
    
    def add_to_cart(self, user_id: int, product_id: int, quantity: int = 1) -> Dict:
        """Add product to cart"""
        cursor = self.db.cursor()
        
        # Check if product exists and has stock
        cursor.execute('SELECT stock FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        if not product:
            return {"error": "Product not found"}
        
        if product['stock'] < quantity:
            return {"error": f"Only {product['stock']} items available"}
        
        # Check if already in cart
        cursor.execute('SELECT * FROM cart WHERE user_id = ? AND product_id = ?', (user_id, product_id))
        existing = cursor.fetchone()
        
        if existing:
            new_quantity = existing['quantity'] + quantity
            if product['stock'] < new_quantity:
                return {"error": f"Only {product['stock']} items available"}
            
            cursor.execute('''
                UPDATE cart SET quantity = ?, created_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND product_id = ?
            ''', (new_quantity, user_id, product_id))
        else:
            cursor.execute('''
                INSERT INTO cart (user_id, product_id, quantity)
                VALUES (?, ?, ?)
            ''', (user_id, product_id, quantity))
        
        self.db.commit()
        return {"success": True, "message": "Added to cart"}
    
    def get_cart(self, user_id: int) -> List[Dict]:
        """Get user's cart items"""
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT c.*, p.name, p.price, p.image_data, p.stock 
            FROM cart c 
            JOIN products p ON c.product_id = p.id 
            WHERE c.user_id = ?
        ''', (user_id,))
        
        items = []
        for row in cursor.fetchall():
            item = dict(row)
            items.append(item)
        
        return items
    
    def remove_from_cart(self, user_id: int, product_id: int) -> Dict:
        """Remove item from cart"""
        cursor = self.db.cursor()
        cursor.execute('DELETE FROM cart WHERE user_id = ? AND product_id = ?', (user_id, product_id))
        self.db.commit()
        return {"success": True, "message": "Removed from cart"}
    
    def create_order(self, user_id: int, shipping_address: str) -> Dict:
        """Create order from cart items"""
        cursor = self.db.cursor()
        
        # Get cart items
        cart_items = self.get_cart(user_id)
        if not cart_items:
            return {"error": "Cart is empty"}
        
        # Calculate total
        total = sum(item['price'] * item['quantity'] for item in cart_items)
        
        # Generate order number
        order_number = f"ORD-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
        
        # Create orders for each item
        order_ids = []
        for item in cart_items:
            # Check stock
            if item['stock'] < item['quantity']:
                return {"error": f"Insufficient stock for {item['name']}"}
            
            cursor.execute('''
                INSERT INTO orders (order_number, user_id, product_id, quantity, total_amount, status, shipping_address)
                VALUES (?, ?, ?, ?, ?, 'pending', ?)
            ''', (order_number, user_id, item['product_id'], item['quantity'], item['price'] * item['quantity'], shipping_address))
            
            order_ids.append(cursor.lastrowid)
            
            # Update stock
            cursor.execute('UPDATE products SET stock = stock - ? WHERE id = ?', (item['quantity'], item['product_id']))
        
        # Clear cart
        cursor.execute('DELETE FROM cart WHERE user_id = ?', (user_id,))
        
        self.db.commit()
        
        return {
            "success": True, 
            "order_number": order_number,
            "total_amount": total,
            "items_count": len(cart_items)
        }
    
    def get_orders(self, user_id: int) -> List[Dict]:
        """Get user's orders"""
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT o.*, p.name as product_name, p.image_data
            FROM orders o 
            JOIN products p ON o.product_id = p.id 
            WHERE o.user_id = ?
            ORDER BY o.created_at DESC
        ''', (user_id,))
        
        orders = []
        for row in cursor.fetchall():
            order = dict(row)
            if order.get('shipping_updates'):
                try:
                    order['shipping_updates'] = json.loads(order['shipping_updates'])
                except:
                    order['shipping_updates'] = []
            orders.append(order)
        
        return orders
    
    def get_order_status(self, order_number: str) -> Dict:
        """Get status and shipping updates for an order"""
        cursor = self.db.cursor()
        
        cursor.execute('''
            SELECT o.*, p.name as product_name 
            FROM orders o 
            JOIN products p ON o.product_id = p.id 
            WHERE o.order_number = ?
        ''', (order_number,))
        
        order = cursor.fetchone()
        if not order:
            return {"error": "Order not found"}
        
        order_dict = dict(order)
        if order_dict.get('shipping_updates'):
            try:
                order_dict['shipping_updates'] = json.loads(order_dict['shipping_updates'])
            except:
                order_dict['shipping_updates'] = []
        
        return order_dict
    
    def create_return_request(self, order_number: str, product_id: int, reason: str, user_id: int) -> Dict:
        """Create a return request for an order"""
        cursor = self.db.cursor()
        
        # Check if order exists and belongs to user
        cursor.execute('''
            SELECT * FROM orders WHERE order_number = ? AND user_id = ?
        ''', (order_number, user_id))
        
        order = cursor.fetchone()
        if not order:
            return {"error": "Order not found or unauthorized"}
        
        # Check if return already exists
        cursor.execute('''
            SELECT * FROM returns WHERE order_number = ? AND product_id = ?
        ''', (order_number, product_id))
        
        if cursor.fetchone():
            return {"error": "Return request already exists for this product"}
        
        # Calculate refund amount (80% of total)
        refund_amount = order['total_amount'] * 0.8
        
        # Create return request
        cursor.execute('''
            INSERT INTO returns (order_number, user_id, product_id, reason, status, refund_amount)
            VALUES (?, ?, ?, ?, 'pending', ?)
        ''', (order_number, user_id, product_id, reason, refund_amount))
        
        self.db.commit()
        
        return {
            "return_id": cursor.lastrowid,
            "order_number": order_number,
            "status": "pending",
            "refund_amount": refund_amount,
            "created_at": datetime.utcnow().isoformat()
        }
    
    def get_return_policy(self) -> str:
        """Get the return and refund policy"""
        return """
        📋 Our Return Policy:
        
        1. ✅ Returns accepted within 30 days of delivery
        2. 📦 Items must be in original condition with tags
        3. 💰 Refund processed within 5-7 business days
        4. 🆓 Free returns for Prime members
        5. 🚚 Pickup service available for large items
        
        🔄 Refund Process:
        1. Create return request
        2. Wait for approval (24-48 hours)
        3. Ship item back (or schedule pickup)
        4. Refund initiated after inspection
        5. Refund credited to original payment method
        """
    
    def get_recommendations(self, product_id: int, user_id: Optional[int] = None) -> List[Dict]:
        """Get product recommendations based on product and user preferences"""
        cursor = self.db.cursor()
        recommendations = []
        
        # Get the product
        cursor.execute('SELECT * FROM products WHERE id = ?', (product_id,))
        product = cursor.fetchone()
        if not product:
            return []
        
        # Find similar products (same category or brand)
        cursor.execute('''
            SELECT * FROM products 
            WHERE (category = ? OR brand = ?) AND id != ?
            ORDER BY rating DESC LIMIT 8
        ''', (product['category'], product['brand'], product_id))
        
        similar = cursor.fetchall()
        for p in similar:
            rec = dict(p)
            rec['reason'] = f"Similar to {product['name']} in {product['category']}"
            recommendations.append(rec)
        
        # If user has preferences, add personalized recommendations
        if user_id:
            cursor.execute('SELECT preferences FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            if user and user['preferences']:
                try:
                    preferences = json.loads(user['preferences'])
                    preferred_categories = preferences.get('categories', [])
                    
                    if preferred_categories:
                        placeholders = ','.join(['?'] * len(preferred_categories))
                        cursor.execute(f'''
                            SELECT * FROM products 
                            WHERE category IN ({placeholders}) AND id != ?
                            ORDER BY rating DESC LIMIT 5
                        ''', (*preferred_categories, product_id))
                        
                        personalized = cursor.fetchall()
                        for p in personalized:
                            if not any(r['id'] == p['id'] for r in recommendations):
                                rec = dict(p)
                                rec['reason'] = "Based on your preferences"
                                recommendations.append(rec)
                except:
                    pass
        
        return recommendations[:10]
    
    def get_faq_answer(self, query: str) -> Dict:
        """Get FAQ answer based on query"""
        cursor = self.db.cursor()
        
        cursor.execute('SELECT * FROM faqs')
        faqs = cursor.fetchall()
        
        # Simple keyword matching
        query_lower = query.lower()
        best_match = None
        best_score = 0
        
        for faq in faqs:
            score = 0
            question_words = faq['question'].lower().split()
            for word in query_lower.split():
                if word in ' '.join(question_words):
                    score += 1
            
            if score > best_score:
                best_score = score
                best_match = faq
        
        if best_match and best_score > 0:
            return {
                "question": best_match['question'],
                "answer": best_match['answer'],
                "category": best_match['category']
            }
        
        return None
    
    def add_product(self, name: str, description: str, price: float, category: str, 
                   brand: str, stock: int, specifications: dict, image_file=None) -> Dict:
        """Add a new product to the database with image"""
        cursor = self.db.cursor()
        
        try:
            # Process image
            image_data = None
            if image_file:
                image_data = encode_image_to_base64(image_file)
            
            # If no image, create placeholder
            if not image_data:
                image_data = create_placeholder_image("#808080")
            
            # Insert product
            cursor.execute('''
                INSERT INTO products (name, description, price, category, brand, stock, availability, specifications, image_data)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?)
            ''', (name, description, price, category, brand, stock, json.dumps(specifications), image_data))
            
            self.db.commit()
            product_id = cursor.lastrowid
            
            return {
                "success": True,
                "product_id": product_id,
                "message": "Product added successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_all_products(self) -> List[Dict]:
        """Get all products"""
        cursor = self.db.cursor()
        cursor.execute('SELECT * FROM products ORDER BY created_at DESC')
        products = []
        for row in cursor.fetchall():
            product = dict(row)
            if product.get('specifications'):
                try:
                    product['specifications'] = json.loads(product['specifications'])
                except:
                    product['specifications'] = {}
            products.append(product)
        return products
    
    def get_products_by_category(self, category: str) -> List[Dict]:
        """Get products by category"""
        cursor = self.db.cursor()
        cursor.execute('SELECT * FROM products WHERE category = ? AND availability = 1 ORDER BY rating DESC', (category,))
        products = []
        for row in cursor.fetchall():
            product = dict(row)
            if product.get('specifications'):
                try:
                    product['specifications'] = json.loads(product['specifications'])
                except:
                    product['specifications'] = {}
            products.append(product)
        return products
    
    def add_review(self, product_id: int, user_id: int, rating: int, comment: str) -> Dict:
        """Add a product review"""
        cursor = self.db.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO reviews (product_id, user_id, rating, comment)
                VALUES (?, ?, ?, ?)
            ''', (product_id, user_id, rating, comment))
            
            # Update product rating
            cursor.execute('''
                UPDATE products 
                SET rating = (
                    SELECT AVG(rating) FROM reviews WHERE product_id = ?
                )
                WHERE id = ?
            ''', (product_id, product_id))
            
            self.db.commit()
            return {"success": True, "message": "Review added successfully"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_reviews(self, product_id: int) -> List[Dict]:
        """Get product reviews"""
        cursor = self.db.cursor()
        cursor.execute('''
            SELECT r.*, u.full_name as user_name 
            FROM reviews r 
            JOIN users u ON r.user_id = u.id 
            WHERE r.product_id = ?
            ORDER BY r.created_at DESC
        ''', (product_id,))
        
        reviews = []
        for row in cursor.fetchall():
            reviews.append(dict(row))
        return reviews

# ============================================
# UI COMPONENTS
# ============================================

def display_product_card(product: Dict, show_add_to_cart: bool = True):
    """Display a product in a card format with image"""
    with st.container():
        col1, col2 = st.columns([1, 2])
        
        with col1:
            # Display product image - FIXED: removed use_column_width
            if product.get('image_data'):
                try:
                    image_data = product['image_data']
                    st.image(f"data:image/jpeg;base64,{image_data}", width=150)
                except:
                    st.image("data:image/jpeg;base64," + create_placeholder_image("#808080"), width=150)
            else:
                st.image("data:image/jpeg;base64," + create_placeholder_image("#808080"), width=150)
        
        with col2:
            st.markdown(f"### {product['name']}")
            st.markdown(f"**Brand:** {product.get('brand', 'N/A')} | **Category:** {product.get('category', 'N/A')}")
            st.markdown(f"**Price:** ₹{product['price']:,}")
            st.markdown(f"**Rating:** ⭐ {product.get('rating', 0):.1f}")
            st.markdown(f"**Stock:** {product.get('stock', 0)} units")
            
            if show_add_to_cart and st.session_state.user:
                if st.button(f"🛒 Add to Cart", key=f"add_{product['id']}"):
                    tools = ECommerceTools()
                    result = tools.add_to_cart(st.session_state.user['id'], product['id'])
                    if result.get('success'):
                        st.success("✅ Added to cart!")
                    else:
                        st.error(f"❌ {result.get('error', 'Failed to add to cart')}")
        
        with st.expander("📋 View Details"):
            st.markdown(f"**Description:** {product.get('description', 'No description available')}")
            
            # Display specifications
            if product.get('specifications'):
                st.markdown("**Specifications:**")
                specs = product['specifications']
                if isinstance(specs, dict):
                    for key, value in specs.items():
                        st.markdown(f"- {key.title()}: {value}")
                else:
                    st.markdown(f"- {specs}")
            
            # Reviews section
            st.markdown("---")
            st.markdown("### 💬 Reviews")
            
            tools = ECommerceTools()
            reviews = tools.get_reviews(product['id'])
            
            if reviews:
                for review in reviews[:3]:
                    st.markdown(f"**{review.get('user_name', 'User')}** ⭐ {review['rating']}")
                    st.markdown(f"_{review.get('comment', 'No comment')}_")
                    st.markdown("---")
            else:
                st.info("No reviews yet. Be the first to review!")
            
            # Add review
            if st.session_state.user:
                with st.form(key=f"review_form_{product['id']}"):
                    rating = st.slider("Rating", 1, 5, 5, key=f"rating_{product['id']}")
                    comment = st.text_area("Your review", key=f"comment_{product['id']}")
                    if st.form_submit_button("Submit Review"):
                        tools = ECommerceTools()
                        result = tools.add_review(product['id'], st.session_state.user['id'], rating, comment)
                        if result.get('success'):
                            st.success("✅ Review submitted!")
                            st.rerun()
                        else:
                            st.error(f"❌ {result.get('error', 'Failed to submit review')}")

def display_product_grid(products: List[Dict], columns: int = 2):
    """Display products in a grid layout"""
    if not products:
        st.info("No products found")
        return
    
    rows = [products[i:i + columns] for i in range(0, len(products), columns)]
    
    for row in rows:
        cols = st.columns(columns)
        for idx, product in enumerate(row):
            if idx < len(cols):
                with cols[idx]:
                    with st.container(border=True):
                        display_product_card(product)

def display_cart():
    """Display user's cart"""
    if not st.session_state.user:
        st.warning("Please login to view your cart")
        return
    
    tools = ECommerceTools()
    cart_items = tools.get_cart(st.session_state.user['id'])
    
    if not cart_items:
        st.info("Your cart is empty")
        return
    
    st.subheader("🛒 Your Cart")
    
    total = 0
    for item in cart_items:
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
            
            with col1:
                # FIXED: removed use_column_width
                if item.get('image_data'):
                    try:
                        st.image(f"data:image/jpeg;base64,{item['image_data']}", width=80)
                    except:
                        pass
                st.markdown(f"**{item['name']}**")
            
            with col2:
                st.markdown(f"₹{item['price']:,}")
            
            with col3:
                st.markdown(f"Qty: {item['quantity']}")
            
            with col4:
                if st.button("❌ Remove", key=f"remove_{item['product_id']}"):
                    tools.remove_from_cart(st.session_state.user['id'], item['product_id'])
                    st.rerun()
            
            st.markdown(f"**Subtotal:** ₹{item['price'] * item['quantity']:,}")
            total += item['price'] * item['quantity']
    
    st.markdown("---")
    st.markdown(f"### Total: ₹{total:,}")
    
    # Checkout
    with st.form("checkout_form"):
        shipping_address = st.text_area("Shipping Address", placeholder="Enter your complete shipping address")
        if st.form_submit_button("Place Order"):
            if not shipping_address:
                st.error("Please enter shipping address")
            else:
                result = tools.create_order(st.session_state.user['id'], shipping_address)
                if result.get('success'):
                    st.success(f"✅ Order placed successfully! Order Number: {result['order_number']}")
                    st.balloons()
                    st.rerun()
                else:
                    st.error(f"❌ {result.get('error', 'Failed to place order')}")

# ============================================
# ADD PRODUCT PAGE
# ============================================

def add_product_page():
    """Page for adding new products"""
    st.subheader("➕ Add New Product")
    
    with st.form("add_product_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        
        with col1:
            name = st.text_input("Product Name *", placeholder="Enter product name")
            description = st.text_area("Description", placeholder="Enter product description")
            price = st.number_input("Price (₹) *", min_value=0.0, step=100.0)
            category = st.text_input("Category *", placeholder="Electronics, Smartphones, etc.")
        
        with col2:
            brand = st.text_input("Brand *", placeholder="Enter brand name")
            stock = st.number_input("Stock Quantity *", min_value=0, step=1)
            image_file = st.file_uploader("Product Image", type=['jpg', 'jpeg', 'png'])
            
            # Specifications as JSON
            spec_keys = st.text_input("Specification Keys (comma separated)", 
                                     placeholder="battery, camera, display")
            spec_values = st.text_input("Specification Values (comma separated)",
                                       placeholder="5000mAh, 200MP, 6.8-inch")
        
        if st.form_submit_button("Add Product"):
            if not all([name, price > 0, category, brand, stock >= 0]):
                st.error("❌ Please fill all required fields (*)")
            else:
                # Parse specifications
                specifications = {}
                if spec_keys and spec_values:
                    keys = [k.strip() for k in spec_keys.split(',') if k.strip()]
                    values = [v.strip() for v in spec_values.split(',') if v.strip()]
                    
                    if keys and values:
                        for i, key in enumerate(keys):
                            if i < len(values):
                                specifications[key] = values[i]
                
                tools = ECommerceTools()
                result = tools.add_product(
                    name=name,
                    description=description,
                    price=price,
                    category=category,
                    brand=brand,
                    stock=stock,
                    specifications=specifications,
                    image_file=image_file
                )
                
                if result.get('success'):
                    st.success("✅ Product added successfully!")
                    st.balloons()
                else:
                    st.error(f"❌ {result.get('error', 'Failed to add product')}")

# ============================================
# AI RESPONSE GENERATOR
# ============================================

def generate_ai_response(query: str, tools: ECommerceTools) -> str:
    """Generate AI response based on user query"""
    query_lower = query.lower()
    
    # Check for product search
    if any(word in query_lower for word in ["search", "find", "show", "products", "looking for", "want"]):
        products = tools.search_products(query)
        if products:
            response = "🔍 **Found these products:**\n\n"
            for i, product in enumerate(products[:5], 1):
                response += f"{i}. **{product['name']}** - ₹{product['price']:,}\n"
                response += f"   {product.get('description', '')[:100]}...\n"
                response += f"   ⭐ {product.get('rating', 0):.1f} | Stock: {product.get('stock', 0)}\n\n"
            
            if len(products) > 5:
                response += f"*And {len(products) - 5} more products...*\n"
            response += "\nWould you like more details about any product?"
        else:
            response = "❌ No products found matching your search. Try:\n"
            response += "- Different keywords\n"
            response += "- Checking spelling\n"
            response += "- Adjusting price range"
    
    # Check for order tracking
    elif any(word in query_lower for word in ["track", "order", "status", "delivery"]):
        order_match = re.search(r'ORD-[A-Z0-9]+', query.upper())
        if order_match:
            order_number = order_match.group()
            order = tools.get_order_status(order_number)
            if order and not order.get('error'):
                response = f"📦 **Order #{order_number}**\n"
                response += f"Status: {order['status'].upper()}\n"
                response += f"Product: {order.get('product_name', 'N/A')}\n"
                response += f"Total: ₹{order['total_amount']:,}\n"
                if order.get('tracking_number'):
                    response += f"Tracking: {order['tracking_number']}\n"
                if order.get('shipping_updates'):
                    response += "\nUpdates:\n"
                    for update in order['shipping_updates']:
                        response += f"- {update}\n"
            else:
                response = "❌ Order not found. Please check the order number and try again."
        else:
            response = "🔍 **To track an order:**\n"
            response += "1. Provide your order number (format: ORD-YYYYMMDD-XXXXXXXX)\n"
            response += "2. Example: ORD-20250101-ABC12345\n"
            response += "3. Your order status will be displayed with all updates"
    
    # Check for FAQ
    else:
        faq = tools.get_faq_answer(query)
        if faq:
            response = f"❓ **Q: {faq['question']}**\n\n"
            response += f"📝 **A: {faq['answer']}**\n"
            response += f"\n📂 Category: {faq.get('category', 'General')}"
        else:
            # General response
            response = "🤖 I'm your AI assistant! I can help you with:\n\n"
            response += "🛍️ **Product Search** - Ask about any product\n"
            response += "📦 **Order Tracking** - Provide order number\n"
            response += "🔄 **Returns & Refunds** - Return policy info\n"
            response += "📚 **FAQ** - Common questions answered\n\n"
            response += "How can I help you today?"
    
    return response

# ============================================
# MAIN APP
# ============================================

def main():
    st.set_page_config(
        page_title="AI E-Commerce Support", 
        page_icon="🛍️", 
        layout="wide"
    )
    
    # Initialize database
    init_database()
    seed_sample_data()
    
    # Custom CSS
    st.markdown("""
        <style>
        .stButton > button {
            width: 100%;
        }
        .product-card {
            padding: 10px;
            border-radius: 10px;
            border: 1px solid #ddd;
            margin: 5px 0;
        }
        .product-card:hover {
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            transition: box-shadow 0.3s ease;
        }
        .stImage {
            border-radius: 8px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Header - FIXED: removed use_column_width
    st.title("🛍️ AI E-Commerce Customer Support")
    st.markdown("---")
    
    # Sidebar
    with st.sidebar:
        # FIXED: removed use_column_width and added width parameter
        st.image("https://via.placeholder.com/200x100/1a73e8/FFFFFF?text=AI+E-Commerce", width=200)
        
        st.subheader("👤 User")
        if st.session_state.user:
            st.success(f"Welcome, {st.session_state.user['full_name']}!")
            if st.button("🚪 Logout"):
                st.session_state.user = None
                st.session_state.token = None
                st.session_state.messages = []
                st.session_state.chat_history = []
                st.rerun()
        else:
            st.warning("Please login to continue")
        
        st.markdown("---")
        
        # Navigation
        st.subheader("📱 Navigation")
        page = st.radio("Go to", [
            "🏠 Home",
            "💬 Chat", 
            "🛍️ Products",
            "🛒 Cart",
            "📦 Orders", 
            "🔄 Returns",
            "📚 FAQ"
        ])
        
        # Admin section for product management
        if st.session_state.user:
            st.markdown("---")
            st.subheader("⚙️ Admin")
            if st.button("➕ Add Product"):
                st.session_state.page = "add_product"
                st.rerun()
    
    # Login/Register
    if not st.session_state.user:
        tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
        
        with tab1:
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                
                if st.form_submit_button("Login"):
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
                    user = cursor.fetchone()
                    conn.close()
                    
                    if user and verify_password(password, user[3]):
                        st.session_state.user = {
                            "id": user[0], 
                            "username": user[1], 
                            "email": user[2], 
                            "full_name": user[4]
                        }
                        st.success("✅ Login successful!")
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials")
        
        with tab2:
            with st.form("register_form"):
                full_name = st.text_input("Full Name")
                username = st.text_input("Username")
                email = st.text_input("Email")
                password = st.text_input("Password", type="password")
                confirm = st.text_input("Confirm Password", type="password")
                
                if st.form_submit_button("Register"):
                    if not all([full_name, username, email, password]):
                        st.error("❌ Please fill all fields")
                    elif password != confirm:
                        st.error("❌ Passwords don't match")
                    else:
                        conn = get_db_connection()
                        cursor = conn.cursor()
                        try:
                            hashed = hash_password(password)
                            cursor.execute('''
                                INSERT INTO users (username, email, hashed_password, full_name) 
                                VALUES (?, ?, ?, ?)
                            ''', (username, email, hashed, full_name))
                            conn.commit()
                            st.success("✅ Registration successful! Please login.")
                        except sqlite3.IntegrityError:
                            st.error("❌ Username or email already exists")
                        finally:
                            conn.close()
        return
    
    # Check if we need to show add product page
    if hasattr(st.session_state, 'page') and st.session_state.page == "add_product":
        add_product_page()
        # Reset page after adding
        if st.button("← Back to Home"):
            st.session_state.page = "home"
            st.rerun()
        return
    
    # Page routing
    tools = ECommerceTools()
    
    if page == "🏠 Home":
        st.subheader("🏠 Welcome to AI E-Commerce")
        
        st.markdown("""
        ### 🌟 Features
        - 🤖 **AI Chat Assistant** - Get instant help with any query
        - 🛍️ **Product Search** - Find products with intelligent search
        - 🛒 **Smart Cart** - Add items and checkout easily
        - 📦 **Order Tracking** - Track your orders in real-time
        - 🔄 **Returns Management** - Easy return requests
        - 📚 **FAQ System** - Quick answers to common questions
        """)
        
        # Display featured products
        st.markdown("### 🔥 Featured Products")
        
        # Get products with highest rating
        all_products = tools.get_all_products()
        featured = sorted(all_products, key=lambda x: x.get('rating', 0), reverse=True)[:6]
        
        if featured:
            display_product_grid(featured, columns=3)
        else:
            st.info("No products available")
    
    elif page == "💬 Chat":
        st.subheader("💬 AI Assistant Chat")
        
        # Display chat messages
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
        
        # Chat input
        if prompt := st.chat_input("Ask me anything about products, orders, returns..."):
            # Add user message
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)
            
            # Generate response
            response = generate_ai_response(prompt, tools)
            
            # Add assistant response
            st.session_state.chat_history.append({"role": "assistant", "content": response})
            with st.chat_message("assistant"):
                st.markdown(response)
            
            st.rerun()
    
    elif page == "🛍️ Products":
        st.subheader("🛍️ Product Catalog")
        
        # Search and filter
        col1, col2, col3 = st.columns([3, 1, 1])
        
        with col1:
            search_query = st.text_input("🔍 Search products", placeholder="Search by name, category, or brand...")
        
        with col2:
            categories = ["All"] + tools.get_all_categories()
            selected_category = st.selectbox("Category", categories)
        
        with col3:
            price_filter = st.selectbox("Price Range", ["All", "Under ₹1000", "₹1000 - ₹5000", "₹5000 - ₹10000", "Above ₹10000"])
        
        # Apply filters
        if search_query:
            products = tools.search_products(search_query)
        elif selected_category != "All":
            products = tools.get_products_by_category(selected_category)
        else:
            products = tools.get_all_products()
        
        # Apply price filter
        if price_filter != "All":
            price_ranges = {
                "Under ₹1000": (0, 1000),
                "₹1000 - ₹5000": (1000, 5000),
                "₹5000 - ₹10000": (5000, 10000),
                "Above ₹10000": (10000, float('inf'))
            }
            
            if price_filter in price_ranges:
                min_price, max_price = price_ranges[price_filter]
                products = [p for p in products if min_price <= p['price'] <= max_price]
        
        st.markdown(f"### Found {len(products)} products")
        
        if products:
            # Display as grid
            display_product_grid(products, columns=3)
        else:
            st.info("No products found matching your criteria")
    
    elif page == "🛒 Cart":
        display_cart()
    
    elif page == "📦 Orders":
        st.subheader("📦 My Orders")
        
        orders = tools.get_orders(st.session_state.user['id'])
        
        if not orders:
            st.info("No orders found")
        else:
            for order in orders:
                with st.expander(f"Order #{order['order_number']} - {order['status'].upper()}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f"**Product:** {order.get('product_name', 'N/A')}")
                        # FIXED: removed use_column_width
                        if order.get('image_data'):
                            try:
                                st.image(f"data:image/jpeg;base64,{order['image_data']}", width=100)
                            except:
                                pass
                        st.markdown(f"**Quantity:** {order['quantity']}")
                        st.markdown(f"**Total:** ₹{order['total_amount']:,}")
                    
                    with col2:
                        st.markdown(f"**Status:** {order['status'].upper()}")
                        st.markdown(f"**Created:** {order['created_at'][:10]}")
                        if order.get('tracking_number'):
                            st.markdown(f"**Tracking:** {order['tracking_number']}")
                        if order.get('shipping_address'):
                            st.markdown(f"**Address:** {order['shipping_address']}")
                    
                    # Return request option
                    if order['status'].lower() == 'delivered':
                        if st.button("🔄 Request Return", key=f"return_{order['id']}"):
                            with st.form(f"return_form_{order['id']}"):
                                reason = st.text_area("Reason for return")
                                if st.form_submit_button("Submit Return Request"):
                                    result = tools.create_return_request(
                                        order['order_number'], 
                                        order['product_id'], 
                                        reason, 
                                        st.session_state.user['id']
                                    )
                                    if result.get('success'):
                                        st.success("✅ Return request submitted!")
                                    else:
                                        st.error(f"❌ {result.get('error', 'Failed to submit return')}")
    
    elif page == "🔄 Returns":
        st.subheader("🔄 Returns & Refunds")
        
        tab1, tab2 = st.tabs(["📋 Return Policy", "📝 My Returns"])
        
        with tab1:
            st.markdown(tools.get_return_policy())
        
        with tab2:
            # Show user's return requests
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT r.*, p.name as product_name 
                FROM returns r 
                JOIN products p ON r.product_id = p.id 
                WHERE r.user_id = ?
                ORDER BY r.created_at DESC
            ''', (st.session_state.user['id'],))
            
            returns = cursor.fetchall()
            conn.close()
            
            if not returns:
                st.info("No return requests found")
            else:
                for return_req in returns:
                    with st.container(border=True):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**Order:** {return_req['order_number']}")
                            st.markdown(f"**Product:** {return_req['product_name']}")
                        with col2:
                            status = return_req['status'].upper()
                            if status == 'PENDING':
                                st.warning(f"Status: {status}")
                            elif status == 'APPROVED':
                                st.info(f"Status: {status}")
                            elif status == 'COMPLETED':
                                st.success(f"Status: {status}")
                            else:
                                st.error(f"Status: {status}")
                            st.markdown(f"**Refund Amount:** ₹{return_req['refund_amount']:,}")
                            st.markdown(f"**Created:** {return_req['created_at'][:10]}")
    
    elif page == "📚 FAQ":
        st.subheader("📚 Frequently Asked Questions")
        
        # Search FAQ
        search_faq = st.text_input("🔍 Search FAQs", placeholder="What would you like to know?")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if search_faq:
            cursor.execute('''
                SELECT * FROM faqs 
                WHERE question LIKE ? OR answer LIKE ?
            ''', (f'%{search_faq}%', f'%{search_faq}%'))
        else:
            cursor.execute('SELECT * FROM faqs')
        
        faqs = cursor.fetchall()
        conn.close()
        
        if faqs:
            for faq in faqs:
                with st.expander(f"❓ {faq[1]}"):
                    st.markdown(f"**Category:** {faq[3]}")
                    st.markdown(f"**Answer:** {faq[2]}")
        else:
            st.info("No FAQs found")

# ============================================
# ENTRY POINT
# ============================================

if __name__ == "__main__":
    main()