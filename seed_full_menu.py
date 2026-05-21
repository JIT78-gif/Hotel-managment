"""Replace the demo cafe menu with a comprehensive multi-cuisine menu.

Inspired by a real hotel cafe menu (cafe name intentionally not copied).
Talks to the running backend via the admin API — no DB lock, changes show
up live in the frontend without restart.

Run:
    python seed_full_menu.py

Optional env vars:
    HOTEL_API_BASE   default http://127.0.0.1:8000
    HOTEL_ADMIN_EMAIL    default admin@democafe.com
    HOTEL_ADMIN_PASSWORD default admin1234
"""
import os
import sys
import httpx

BASE = os.environ.get("HOTEL_API_BASE", "http://127.0.0.1:8000")
EMAIL = os.environ.get("HOTEL_ADMIN_EMAIL", "admin@democafe.com")
PASSWORD = os.environ.get("HOTEL_ADMIN_PASSWORD", "admin1234")


def _img(photo_id: str) -> str:
    return f"https://images.unsplash.com/{photo_id}?w=800&auto=format&fit=crop&q=70"


# One curated Unsplash photo per category — items in a category share the image.
# Admin can later edit specific items via the /admin/menu page.
IMG = {
    "salads":              _img("photo-1546069901-ba9599a7e63c"),
    "soups":               _img("photo-1547592180-85f173990554"),
    "appetizers":          _img("photo-1606923829579-718061ce14b4"),
    "pasta":               _img("photo-1551183053-bf91a1d81141"),
    "pizza":               _img("photo-1574071318508-1cdbab80d002"),
    "gourmet_pizza":       _img("photo-1565299624946-b28f40a0ae38"),
    "asian_starters":      _img("photo-1559847844-5315695dadae"),
    "asian_soups":         _img("photo-1569718212165-3a8278d5f624"),
    "noodles":             _img("photo-1612929633738-8fe44f7ec841"),
    "asian_curries":       _img("photo-1455619452474-d2be8b1e70cd"),
    "rice":                _img("photo-1633436374961-09b92742047b"),
    "north_indian":        _img("photo-1631452180519-c014fe946bc7"),
    "south_indian":        _img("photo-1668236543090-82eba5ee5976"),
    "breads":              _img("photo-1576618148400-f54bed99fcfd"),
    "continental":         _img("photo-1525351484163-7529414344d8"),
    "bagels":              _img("photo-1592847905229-5db8dde7d796"),
    "sourdough":           _img("photo-1541519227354-08fa5d50c44d"),
    "espresso":            _img("photo-1610632380989-680fe40816c6"),
    "espresso_with":       _img("photo-1462917882517-e150004895fa"),
    "espresso_cocktails":  _img("photo-1545665277-5937489579f2"),
    "frappe":              _img("photo-1572442388796-11668a67e53d"),
    "manual_brew":         _img("photo-1495474472287-4d71bcdd2085"),
    "cold_brew":           _img("photo-1461023058943-07fcbe16d735"),
    "cold_brew_cocktails": _img("photo-1514362545857-3bc16c4c7d1b"),
    "hot_chocolate":       _img("photo-1542990253-0d0f5be5f0ed"),
    "milkshake":           _img("photo-1572490122747-3968b75cc699"),
    "teas":                _img("photo-1571934811356-5cc061b6821f"),
    "juices":              _img("photo-1622597467836-f3285f2131b8"),
    "coolers":             _img("photo-1556679343-c7306c1976bc"),
    "kebab":               _img("photo-1567188040759-fb8a883dc6d8"),
    "tandoor":             _img("photo-1567188040759-fb8a883dc6d8"),
    "big_plates":          _img("photo-1563379091339-03b21ab4a4f8"),
    "smoothie_bowls":      _img("photo-1490474504059-bf2db5ab2348"),
}

# (Category display name, image key, [(item name, description, price), …])
MENU = [
    ("Salads", "salads", [
        ("Caesar Salad", "Romaine, cottage cheese, cherry tomato, olives, crispy croutons, Caesar dressing", 320),
        ("Horiatiki Greek Salad", "Tomato, cucumber, kalamata olives, bell pepper, feta cheese, Greek dressing", 360),
        ("Moroccan Salad", "Shredded vegetables, blanched chickpeas, Cajun spices, pomegranate molasses", 340),
        ("Watermelon Feta", "Cubed watermelon, feta, mint, lemon dressing", 280),
        ("Vegan Buddha Bowl", "Brown rice, carrots, cucumber, beetroot, marinated chickpeas, lemon-tahini dressing", 380),
        ("Quinoa Avocado", "Quinoa, avocado, cottage cheese, corn, tomatoes, cucumber, lettuce, herb vinaigrette", 420),
        ("Burrata Fruit Salad", "Seasonal fruits, burrata cheese, balsamic reduction", 460),
        ("Sauté Vegetables", "Exotic vegetables sautéed in olive oil and fresh herbs", 280),
    ]),
    ("Soups", "soups", [
        ("Tomato Basil Soup", "Slow-roasted tomato, garden basil, herb bread crisp", 180),
        ("Broccoli Almond Soup", "Broccoli purée with toasted almond slivers", 200),
        ("Cream of Mushroom", "Sautéed mushrooms simmered in cream", 220),
    ]),
    ("Appetizers", "appetizers", [
        ("Bean Bell Pepper Wrap", "Sautéed kidney beans and bell pepper rolled in a tortilla with sliced cheese", 240),
        ("Mediterranean Wrap", "Falafel, pickled tomato and olives, beetroot hummus", 280),
        ("Burrito Wrap", "Tortilla wrap filled with cottage cheese, Mexican rice, chilli beans, sour cream", 320),
        ("Nachos", "House nachos with chilli beans, cheese sauce, jalapeños, black olives, guacamole, salsa", 280),
        ("Quesadilla", "Tortilla wrap filled with sautéed bell pepper, zucchini and broccoli, topped with mozzarella and cheddar", 320),
        ("Falafel Hummus", "Falafel and hummus pita bread with za'atar crackers", 260),
        ("Garlic Bread", "Oven-baked, hand-stretched garlic bread", 180),
        ("Sourdough Sandwich", "Sourdough sandwich with cottage cheese, spinach and grilled vegetables", 300),
        ("Classic Fries", "Crisp golden fries — salted or with peri-peri / Cajun / truffle oil", 180),
        ("Wedges", "Classic salted potato wedges with butter and parmesan", 200),
    ]),
    ("Pasta", "pasta", [
        ("Aglio E Olio Spaghetti", "Spaghetti tossed in garlic, olive oil, chilli flakes, basil, parmesan, parsley", 360),
        ("Pesto Spaghetti", "Spaghetti in pesto with garlic and fresh herbs, parmesan", 380),
        ("Arrabbiata", "Choice of pasta in a fiery rich tomato sauce with fresh herbs", 360),
        ("Alfredo", "Choice of pasta in cream, garlic and parmesan sauce", 380),
        ("Alla Rosé", "Choice of pasta in Italian tomato cream sauce with fresh herbs", 380),
        ("Pesto Cream", "Choice of pasta in basil pesto cream sauce, parmesan", 400),
        ("Mac and Cheese", "Macaroni tossed in cream and English cheddar sauce", 360),
        ("Burrata Al Pomodoro", "Spaghetti tossed in pomodoro sauce, topped with burrata", 480),
        ("Burrata Al Pesto", "Spaghetti tossed in pesto, topped with burrata", 480),
        ("Fettuccine Mushroom Ragu", "Fettuccine tossed in cremini, shiitake and portobello mushroom ragu, fresh herbs", 460),
        ("Linguine in Lemon Butter Sauce", "Linguine in lemon butter infused with garlic, fresh herbs and chilli flakes", 420),
    ]),
    ("Pizza", "pizza", [
        ("Margherita", "Thin crust, San Marzano tomato, mozzarella, basil", 320),
        ("Fiama", "Mozzarella, brown garlic, green chillies, sliced onion", 340),
        ("Bianca", "Cream cheese topped with mozzarella, basil, chilli flakes", 360),
        ("Burrata Cheese Pizza", "Burrata, olive oil and chilli oil", 460),
        ("Cancún", "Pizza sauce topped with mozzarella, peri cheese, sundried tomatoes, black olives, jalapeños", 380),
        ("Pizza Rosso", "Pizza sauce topped with mozzarella, feta, sundried tomatoes, black olives, jalapeños", 380),
        ("Four Cheese", "Mozzarella, blue cheese, parmesan, cheddar topped with fresh oregano", 440),
        ("Pizza Zucchini", "Pizza sauce topped with zucchini, mushroom, red paprika, oregano", 340),
        ("Sicilia", "Pizza sauce topped with mozzarella, spinach, mushroom, red paprika, oregano", 360),
        ("Truffle Mushroom", "Truffle oil, button mushroom, onion, drizzled with Tabasco", 520),
        ("Artichoke Farmhouse", "Pizza sauce topped with artichoke, sundried tomato, broccoli, finished with chimichurri", 420),
    ]),
    ("Gourmet Pizza", "gourmet_pizza", [
        ("Gourmet Margherita", "Classic blend of San Marzano tomato sauce, fior di latte, grana padano, fresh basil", 460),
        ("Bianca Mozzarella", "Smoked mozzarella with zucchini, mushroom, pickled red paprika, onion, hot honey, capers", 520),
        ("Quattro Formaggi", "Bold blend of smoked mozzarella, grana padano, gouda and emmental, topped with jalapeños, pickled onion, fresh garlic and black pepper", 580),
        ("Greek Pizza", "Fior di latte, roasted bell pepper, cherry tomato, sundried marinated olives, red onion, capers, lemon zest", 540),
    ]),
    ("Asian Starters", "asian_starters", [
        ("Crispy Chilli Potato", "Fried julienne potato tossed in hot garlic sauce", 240),
        ("Cottage Cheese Chilli", "Fried cottage cheese, bell pepper, onions, schezwan soy sauce", 260),
        ("Crispy Corn Tempura", "Tempura-coated fried corn with hot garlic sauce", 240),
        ("Steam Dimsums", "Cottage cheese and exotic vegetables in lotus flour, steamed, with soy sauce, tomato-sesame dip, chilli vinegar", 280),
        ("Fried Dimsums", "Cottage cheese and exotic vegetables fried in lotus flour, with soy sauce, tomato-sesame dip, chilli vinegar", 280),
        ("Black Pepper Soya Chaap", "Soya chaap tossed in black pepper sauce", 260),
        ("Ming Bao Roll", "Exotic vegetables, cheese and tofu stuffed in cornflake-crusted bread, hot garlic sauce", 280),
        ("Oyster Scallion Vegetable", "Exotic vegetables tossed in vegetarian oyster sauce with diced scallions", 260),
        ("Thai Bamboo Shoot & Water Chestnut", "Bamboo shoot and water chestnut tossed in sweet chilli sauce", 280),
        ("Honey Chilli Lotus Root", "Lotus root tossed in honey chilli sauce", 260),
        ("Mix Vegetable Tempura", "Crispy tempura of carrot, broccoli, baby corn, sweet potato and zucchini", 280),
        ("Mushroom Lentil Roll", "Lentil, mushroom, bell pepper, cheese wrapped in spring roll sheet", 260),
        ("Mushroom in Cilantro Sauce", "Button mushrooms tossed in house cilantro sauce", 260),
    ]),
    ("Asian Soups", "asian_soups", [
        ("Malaysian Laksa", "In-house laksa paste with brown garlic, fried onion, Asian vegetables and rice noodles", 240),
        ("Ramen Soup Bowl", "Ramen noodles, sliced vegetables topped with soy-sauce marinated tofu", 260),
        ("Veg Clear Soup", "Sliced vegetables simmered in vegetable broth, topped with spring onion", 180),
        ("Classic Manchow", "Chopped vegetables in vegetable broth and soy sauce, topped with crispy fried noodles", 200),
        ("Jade Corn Soup", "Sweet corn, broccoli, zucchini and spinach in seaweed broth", 220),
        ("Thukpa", "Udon noodles, steamed dimsums, butter mushroom in vegetable stock with fried onion and garlic", 240),
    ]),
    ("Noodles", "noodles", [
        ("Hakka Noodles", "Fresh noodles and shredded vegetables tossed in soy sauce", 260),
        ("Thai Udon Noodles", "Udon stir-fried with peanut sauce and red curry, topped with fresh basil, lemongrass, coriander", 320),
        ("Yamin Noodles", "Fresh noodles, shredded vegetables, butter and shiitake tossed in soy sauce", 300),
        ("Dan Dan Noodles", "Udon, vegetables, soya chaap kheema and basil tossed in soy chilli sauce", 320),
        ("Teppanyaki Noodles", "Soba, carrot, napa cabbage and bok choy tossed in butter, soy and ponzu", 320),
        ("Chilli Basil Noodles", "Fresh noodles tossed in basil and chilli paste", 300),
    ]),
    ("Asian Curries", "asian_curries", [
        ("Mapo Tofu", "Exotic vegetables and tofu tossed in chilli bean sauce", 320),
        ("Stir Fry Vegetables", "Exotic vegetables tossed in chilli butter sauce", 280),
        ("Asian Chilli Basil", "Exotic vegetables tossed in soy sauce with a hint of basil", 280),
        ("Thai Curry", "Choice of green or red curry with herbs and curry paste in coconut milk", 340),
        ("Hot Garlic Sauce", "Exotic vegetables tossed in chilli and hot garlic sauce", 280),
        ("Black Bean Sauce", "Exotic vegetables tossed in black bean and soy sauce", 280),
        ("Okra & Tofu in Chilli Soy", "Crispy okra and tender tofu in chilli soy sauce, sesame, garlic, ginger", 320),
        ("Mandarin Sauce", "Cottage cheese and green vegetables tossed in mandarin sauce", 300),
    ]),
    ("Rice", "rice", [
        ("Jasmine Rice", "Steamed jasmine rice tossed in butter", 180),
        ("Fried Rice", "Rice tossed in butter with exotic vegetables", 240),
        ("Burnt Garlic Fried Rice", "Rice tossed with butter, burnt garlic and exotic vegetables", 260),
        ("Cottage Cheese Tossed Rice", "Rice tossed in butter, cottage cheese and exotic vegetables", 280),
        ("Chilli Garlic Mushroom Rice", "Rice tossed with mushrooms and vegetables in chilli garlic sauce", 280),
        ("Brussels Sprout & Gochujang Rice", "Jasmine rice stir-fried with brussels sprouts, baby corn, zucchini and broccoli in spicy gochujang sauce", 320),
        ("Tibetan Rice", "Rice tossed in mushroom, spinach paste and green chillies with a hint of cumin", 260),
    ]),
    ("North Indian", "north_indian", [
        ("Aloo Poha", "Pune-style aloo poha with fresh sev, lime and sweet chutney", 120),
        ("Chole Bhature", "Spiced chickpea curry served with two fluffy bhature", 220),
        ("Palak Paneer Paratha", "Palak-paneer stuffed paratha served with curd, chutney and pickle", 220),
        ("Gobi Paratha", "Spiced cauliflower stuffed paratha served with curd, chutney and pickle", 200),
        ("Aloo Paratha", "Spiced potato stuffed paratha served with curd, chutney and pickle", 180),
    ]),
    ("South Indian", "south_indian", [
        ("Steamed Idli", "Steamed rice cakes with sambar and coconut chutney", 120),
        ("Gun Powder Idli", "Mini idlis tossed in spicy gun powder and ghee", 160),
        ("Masala Idli", "Idlis tempered with curry leaves, mustard and onions", 160),
        ("Plain Dosa", "Crispy dosa with sambar and chutney", 140),
        ("Cheese Dosa", "Dosa stuffed with melted cheese, sambar and chutney", 200),
        ("Palak Cheese Dosa", "Dosa stuffed with sautéed spinach and cheese", 220),
        ("Masala Dosa", "Dosa stuffed with potato masala, sambar and chutney", 180),
        ("Mysore Masala Dosa", "Dosa coated with red Mysore chutney and potato masala", 200),
        ("Masala Uttapam", "Thick rice pancake topped with mixed vegetables and spices", 180),
        ("Onion-Tomato Uttapam", "Thick rice pancake topped with onion and tomato", 160),
    ]),
    ("Breads", "breads", [
        ("Keema Pav", "Spiced soya keema served with buttered pav", 220),
        ("Usal Pav", "Maharashtrian sprouted-moth curry with pav, onion and lemon", 180),
        ("Paneer Scramble", "Spiced paneer bhurji served with buttered pav", 240),
    ]),
    ("Continental", "continental", [
        ("French Toast Nutella", "Brioche French toast with Nutella filling, maple syrup", 280),
        ("French Toast Blueberry", "Brioche French toast with blueberry compote, maple syrup", 300),
        ("Pancakes", "Fluffy buttermilk pancakes with Nutella and maple syrup", 280),
        ("Nutella Croissant", "Buttery croissant filled with Nutella", 220),
        ("Biscoff Croissant", "Buttery croissant filled with Biscoff spread", 220),
        ("Caramel Croissant", "Buttery croissant with caramel cream", 220),
        ("Cut Fruits", "Seasonal fresh-cut fruit platter", 240),
    ]),
    ("Bagels", "bagels", [
        ("Spinach Cream Cheese Mushroom Bagel", "Toasted bagel with sautéed spinach, cream cheese and mushrooms", 320),
        ("Guacamole Mushroom Purple Cabbage Bagel", "Toasted bagel with guacamole, mushroom and purple cabbage", 320),
        ("Cream Cheese Tomato Balsamic Bagel", "Toasted bagel with cream cheese, tomato, balsamic reduction", 300),
    ]),
    ("Sourdough Toasts", "sourdough", [
        ("Sliced Avocado Toast", "Sourdough toast topped with sliced avocado, chilli flakes, lemon", 280),
        ("Guacamole Toast", "Sourdough toast topped with house guacamole and microgreens", 280),
        ("Hummus Toast", "Sourdough toast topped with classic hummus and za'atar", 260),
        ("Pumpkin Hummus Toast", "Sourdough toast topped with pumpkin hummus and pomegranate seeds", 280),
        ("Red Pepper Pesto Toast", "Sourdough toast topped with red pepper pesto and burrata", 320),
        ("Red Pepper Ricotta Toast", "Sourdough toast topped with red pepper ricotta and basil", 320),
    ]),
    ("Espresso Based", "espresso", [
        ("Espresso", "Single shot espresso", 140),
        ("Americano", "Espresso topped with hot water", 160),
        ("Macchiato", "Espresso topped with a dollop of frothed milk", 160),
        ("Cortado", "Equal parts espresso and steamed milk", 180),
        ("Flat White", "Double ristretto with velvety microfoam milk", 200),
        ("Cappuccino", "Espresso, steamed milk and thick foam", 200),
        ("Café Latte", "Espresso with steamed milk and light foam", 220),
        ("Mocha Latte", "Espresso, chocolate, steamed milk and foam", 240),
        ("Orange Zest Mocha Latte", "Mocha latte infused with fresh orange zest", 260),
        ("Caramel Latte", "Caramel-infused latte with caramel drizzle", 240),
        ("Café Bombón", "Espresso layered with sweetened condensed milk", 220),
    ]),
    ("Espresso With", "espresso_with", [
        ("Espresso Tonic", "Double shot espresso over chilled tonic water", 220),
        ("Espresso Ginger Ale", "Double shot espresso over ginger ale", 220),
        ("Espresso Yuzu", "Double shot espresso over yuzu soda", 240),
        ("Espresso Orange Tonic", "Double shot espresso with orange tonic water", 240),
    ]),
    ("Espresso Cocktails", "espresso_cocktails", [
        ("Espresso Martini", "Espresso, cold brew, caramel syrup, chocolate syrup — shaken and chilled", 280),
    ]),
    ("Frappes", "frappe", [
        ("Classic Frappe", "Blended iced coffee with milk and sugar", 220),
        ("Irish Frappe", "Frappe with a hint of Irish cream", 260),
        ("Caramel Frappe", "Frappe with caramel syrup", 240),
        ("Hazelnut Frappe", "Frappe with hazelnut syrup", 240),
        ("Nutella Frappe", "Frappe blended with Nutella", 260),
        ("Mocha Frappe", "Frappe blended with chocolate", 240),
    ]),
    ("Manual Brew", "manual_brew", [
        ("V60 Pour Over", "Single-origin hand-pour through V60 — bright and clean", 240),
        ("Aeropress", "Single-origin coffee brewed through Aeropress", 240),
        ("French Press", "Full-bodied immersion-brewed coffee", 220),
        ("Clever Dripper", "Hybrid immersion and pour-over for a balanced cup", 240),
        ("Syphon", "Theatre brewing — full-immersion vacuum coffee", 280),
    ]),
    ("Cold Brew", "cold_brew", [
        ("Cold Brew", "12-hour cold brew served over ice", 220),
        ("Barrel Aged Cold Brew", "Cold brew aged in oak barrels for a rich, smooth profile", 280),
        ("Cold Brew Tonic", "Cold brew topped with tonic water", 240),
        ("Cold Brew Ginger Ale", "Cold brew topped with ginger ale", 240),
        ("Cold Brew Orange Tonic", "Cold brew with orange tonic water", 260),
    ]),
    ("Cold Brew Cocktails", "cold_brew_cocktails", [
        ("Vietnamese", "Cold brew with sweetened condensed milk over ice", 260),
        ("Coffee Daiquiri", "Cold brew, lime juice, vanilla cream", 280),
        ("Italian Jungle Bird", "Pineapple, lime, cold brew, demerara syrup, salt", 300),
        ("Hot Toddy", "Honey, lemon, hot water and a dash of cold brew", 260),
        ("Hot Rum Punch", "Cold brew warmed with spices and rum essence", 280),
        ("Irish Coffee", "Strong coffee with Irish cream and brown sugar", 280),
        ("Hot Butter Rum", "Hot buttered rum with cinnamon stick", 280),
        ("Passion Fruit Tonic", "Cold brew with passion fruit and tonic", 280),
    ]),
    ("Hot Chocolate", "hot_chocolate", [
        ("Classic Hot Chocolate", "Warm milk and dark chocolate", 240),
        ("Belgian Hot Chocolate", "Premium Belgian dark chocolate with cream", 280),
        ("Sea Salt Hot Chocolate", "Hot chocolate finished with a pinch of sea salt", 260),
        ("Cinnamon Hot Chocolate", "Hot chocolate infused with cinnamon", 260),
    ]),
    ("Milkshakes", "milkshake", [
        ("Chocolate Milkshake", "Thick blended milkshake with chocolate sauce", 240),
        ("Nutella Milkshake", "Thick blended milkshake with Nutella", 280),
        ("Biscoff Milkshake", "Thick blended milkshake with Biscoff spread", 280),
        ("Brownie Milkshake", "Thick blended milkshake with brownie chunks", 280),
        ("Rich Chocolate Milkshake", "Indulgent milkshake with extra dark chocolate", 280),
    ]),
    ("Teas", "teas", [
        ("Masala Tea", "House blend chai with ginger, cardamom and fresh milk", 80),
        ("Blue Pea Tea", "Floral, antioxidant-rich blue pea flower tea", 140),
        ("Hibiscus Tea", "Tart and refreshing hibiscus tea", 140),
        ("Chamomile Tea", "Soothing chamomile flower tea", 140),
        ("Autumnal Punch Tea", "Spiced fruit tea with cinnamon, clove and orange peel", 160),
    ]),
    ("Juices", "juices", [
        ("Watermelon Juice", "Fresh watermelon juice", 140),
        ("Pineapple Juice", "Fresh pineapple juice", 160),
        ("Orange Juice", "Fresh orange juice", 180),
    ]),
    ("Coolers", "coolers", [
        ("Fresh Lime Water / Soda", "Sweet or salted lime over ice", 110),
        ("Fruit Punch", "House blend of seasonal fruit juices", 200),
        ("Bee's Knees", "Fresh orange juice, honey marmalade, orange bitters", 240),
        ("Grasshopper", "White chocolate, fresh cream, mint syrup", 280),
        ("Stay Sober", "Apple juice, cranberry juice, ginger ale", 220),
        ("Paloma", "Grapefruit syrup, lime juice, extract water", 240),
        ("Aviation", "Butterfly pea flower, lime juice, orgeat syrup", 260),
        ("Lime Mint Spritzer", "Fresh lime, mint and soda", 180),
        ("Lemon Iced Tea", "Black tea over ice with fresh lemon", 180),
        ("Peach Iced Tea", "Black tea over ice with peach syrup", 200),
        ("Mint Mojito", "Mint, lime and soda over ice", 220),
        ("Orange Mojito", "Orange, mint, lime, soda over ice", 220),
        ("Iced Guava Passion Fruit", "Fresh guava juice, passion fruit syrup, lime", 240),
        ("Cranberry Spritzer", "Cranberry, lime, soda", 220),
        ("Piña Colada", "Pineapple and coconut cream over ice", 260),
        ("Elder Flower Collins", "Elder flower, lemon juice, cucumber, rose water", 260),
    ]),
    ("Indian Kebab", "kebab", [
        ("Hara Bhara Kebab", "Spinach, peas and herb kebab served with mint chutney and onion rings", 280),
        ("Continental Kebab", "Broccoli, cauliflower, French beans and paneer kebab", 320),
    ]),
    ("Tandoor", "tandoor", [
        ("Paneer Tikka", "Char-grilled marinated cottage cheese cubes", 360),
        ("Hariyali Tikka", "Paneer marinated in coriander and mint, char-grilled", 360),
        ("Achari Tikka", "Paneer marinated in pickling spices, char-grilled", 380),
        ("Aloo Matar Kulcha", "Stuffed kulcha with potato and peas masala, served with green chutney, red chutney and white butter", 240),
        ("Paneer Stuffed Kulcha", "Stuffed kulcha with paneer, served with green chutney, red chutney and white butter", 260),
    ]),
    ("Big Plates", "big_plates", [
        ("Dal Palak Khichdi", "One-pot dal-palak khichdi served with curd", 260),
        ("Sprouts Khichdi", "Khichdi with sprouted moong, served with curd", 280),
        ("Millet Khichdi", "Khichdi with whole millets, served with curd", 280),
        ("Quinoa Khichdi", "Khichdi made with quinoa, served with curd", 300),
        ("Dal Tadka with Jeera Rice", "Yellow dal tempered with cumin, served with jeera rice", 260),
        ("Rajma Chawal", "Kidney bean curry with steamed basmati rice", 260),
    ]),
    ("Smoothie Bowls", "smoothie_bowls", [
        ("Tropical Bowl", "Mango, pineapple and banana smoothie bowl topped with granola, coconut and seasonal fruit", 320),
        ("Belgian Chocolate Bowl", "Dark chocolate smoothie bowl topped with granola, cocoa nibs and banana", 360),
        ("Berry Bowl", "Mixed berry smoothie bowl topped with granola and chia seeds", 340),
    ]),
]


import time


def _request_with_retry(method: str, url: str, *, retries: int = 6, **kwargs) -> httpx.Response:
    """Make a request, reconnecting through network blips (e.g. uvicorn reload)."""
    last_exc = None
    for attempt in range(retries):
        try:
            with httpx.Client(base_url=BASE, timeout=15.0) as c:
                return c.request(method, url, **kwargs)
        except (httpx.HTTPError, httpx.ReadError, httpx.ConnectError, httpx.RemoteProtocolError) as e:
            last_exc = e
            sleep = 0.5 + attempt * 0.5
            print(f"  ⟲ retry {attempt+1}/{retries} on {method} {url} (sleep {sleep:.1f}s) — {type(e).__name__}")
            time.sleep(sleep)
    raise RuntimeError(f"giving up after {retries} retries on {method} {url}: {last_exc}")


def main() -> int:
    print(f"Logging in as {EMAIL} on {BASE} …")
    try:
        r = _request_with_retry("POST", "/auth/login", json={"email": EMAIL, "password": PASSWORD})
        r.raise_for_status()
    except Exception as e:
        print(f"Login failed: {e}")
        return 1
    body = r.json()
    if body.get("role") != "admin":
        print(f"User {EMAIL} is not an admin (role={body.get('role')}). Aborting.")
        return 1
    token = body["token"]
    cafe_name = body["cafe_name"]
    print(f"Logged in. cafe={cafe_name}, role=admin")

    auth = {"Authorization": f"Bearer {token}"}

    # Wipe existing categories (cascades to items)
    cats = _request_with_retry("GET", "/admin/categories", headers=auth).json()
    if cats:
        print(f"Wiping {len(cats)} existing categories (cascades to items)…")
        for c in cats:
            _request_with_retry("DELETE", f"/admin/categories/{c['id']}", headers=auth)

    # Insert new menu
    total_items = 0
    for sort_order, (cat_name, image_key, items) in enumerate(MENU):
        r = _request_with_retry(
            "POST", "/admin/categories", headers=auth,
            json={"name": cat_name, "sort_order": sort_order},
        )
        if r.status_code != 201:
            print(f"  FAILED to create category {cat_name}: {r.status_code} {r.text}")
            continue
        cat_id = r.json()["id"]
        img_url = IMG[image_key]
        item_ok = 0
        for name, desc, price in items:
            ri = _request_with_retry(
                "POST", "/admin/menu-items", headers=auth,
                json={
                    "category_id": cat_id, "name": name, "description": desc,
                    "price": price, "image_url": img_url, "is_available": True,
                },
            )
            if ri.status_code == 201:
                item_ok += 1
                total_items += 1
            else:
                print(f"  ! {name}: {ri.status_code} {ri.text}")
        print(f"  {cat_name}: {item_ok}/{len(items)} items")

    print(f"\nDone. Inserted {len(MENU)} categories and {total_items} items.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
