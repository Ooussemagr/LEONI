import streamlit as st
from pymongo import MongoClient
import bcrypt
import pandas as pd
import os
import base64
from PIL import Image
import io
import re
from datetime import datetime, timedelta
from streamlit import toast
import csv

# Clear caches
st.cache_data.clear()
st.cache_resource.clear()

# Validation functions
def validate_email(email):
    """Validate email format"""
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not any(char.isupper() for char in password):
        return False, "Password must contain at least one uppercase letter"
    if not any(char.isdigit() for char in password):
        return False, "Password must contain at least one digit"
    return True, "Password is valid"

# MongoDB Connection
client = MongoClient('mongodb://localhost:27017')
db = client['LEONI']
users_collection = db['users']
logins_collection = db['logins']
images_collection = db['images']
csv_collection = db['csv_files']

# Custom CSS styling
def apply_custom_styles():
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] {
        background-color: #C0C3C9;
    }
    [data-testid="stSidebar"] {
        background-color: #B3B3B3;
        color: white;
    }
    .stButton>button {
        background-color: #1E90FF;
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 5px;
        width: 100%;
        font-size: 16px;
        margin: 5px 0;
    }
    .stButton>button:hover {
        background-color: #0077B6;
    }
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
        color: #0A1975;
    }
    input {
        background-color: #D3D3D3;
        color: #0A1975;
        border: 2px solid #A9A9A9;
        border-radius: 5px;
        padding: 8px;
    }
    textarea {
        background-color: #D3D3D3;
        color: black;
        border: 2px solid #A9A9A9;
        border-radius: 5px;
        padding: 8px;
    }
    input:focus, textarea:focus {
        outline: none;
        border: 2px solid #1E90FF;
    }
    .stButton>button {
        transition: background-color 0.3s ease, transform 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #0077B6;
        transform: scale(1.05);
    }
    </style>
    """, unsafe_allow_html=True)

apply_custom_styles()

# Security functions
def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def check_password(password, hashed_password):
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password)

def check_login_attempts(email):
    return logins_collection.count_documents({
        "email": email,
        "success": False,
    })

# Image handling functions
def decode_image(encoded_image):
    decoded_data = base64.b64decode(encoded_image)
    return Image.open(io.BytesIO(decoded_data))

def encode_image_to_base64(file_path):
    with open(file_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

# Fonction pour afficher et télécharger les clusters
def display_clusters(file_path, supplier_name):
    """Affiche et permet le téléchargement des données clusters"""
    try:
        if os.path.exists(file_path):
            # Essayer différents encodages
            try:
                df = pd.read_csv(file_path, sep=';', encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(file_path, sep=';', encoding='latin1')
            
            st.subheader(f"Données Clusters - {supplier_name}")
            st.dataframe(df)
            
            # Bouton de téléchargement
            with open(file_path, "rb") as f:
                csv_data = f.read()
            
            st.download_button(
                label=f"⬇️ Télécharger clusters {supplier_name}",
                data=csv_data,
                file_name=f"clusters_{supplier_name.lower().replace(' ', '_')}.csv",
                mime="text/csv"
            )
        else:
            st.error(f"Fichier clusters introuvable: {file_path}")
    except Exception as e:
        st.error(f"Erreur: {str(e)}")

# Session state management
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'user_email' not in st.session_state:
    st.session_state['user_email'] = None
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = "Accueil"

# Navigation
def navigate_to(page):
    st.session_state['current_page'] = page

# CSV validation function
def validate_csv_file(file_path):
    try:
        if not os.path.isfile(file_path):
            return False, "File does not exist"
        if os.path.getsize(file_path) == 0:
            return False, "File is empty"
        
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            lines = [next(f) for _ in range(3)]
            
        semicolon_counts = [line.count(';') for line in lines]
        if len(set(semicolon_counts)) > 1:
            return False, "Inconsistent number of delimiters"
            
        return True, "CSV appears valid"
    except Exception as e:
        return False, f"Validation error: {str(e)}"

# Main application
st.title("Welcome")

# Home page
if st.session_state['current_page'] == "Accueil":
    st.image("C:/Users/MSI/Desktop/pfee/images/images.png", width=150)

# Sidebar navigation
if st.session_state['logged_in']:
    st.sidebar.success(f"User: {st.session_state['user_email']}")
    if st.sidebar.button("Logout"):
        st.session_state['logged_in'] = False
        st.session_state['user_email'] = None
        st.session_state['current_page'] = "Login"
        st.toast("Logged out successfully!", icon="✅")
else:
    option = st.sidebar.selectbox("Choose an option", ["Register", "Login"])
    st.session_state['current_page'] = option

# Registration page
if st.session_state['current_page'] == "Register":
    st.subheader("Registration")
    username = st.text_input("Username", key="register_username")
    email = st.text_input("Email", key="register_email")
    password = st.text_input("Password", type="password", key="register_password")
    confirm_password = st.text_input("Confirm Password", type="password", key="register_confirm_password")

    if st.button("Register", key="register_button"):
        if not validate_email(email):
            st.toast("Please enter a valid email.", icon="❌")
        else:
            is_valid, message = validate_password(password)
            if not is_valid:
                st.toast(message, icon="❌")
            elif password != confirm_password:
                st.toast("Passwords don't match.", icon="❌")
            else:
                hashed_password = hash_password(password)
                user_data = {
                    "username": username,
                    "email": email,
                    "password": hashed_password.decode('utf-8')
                }
                try:
                    users_collection.insert_one(user_data)
                    st.toast("Registration successful! Please login.", icon="✅")
                    navigate_to("Login")
                except Exception as e:
                    st.toast(f"Error: {e}", icon="❌")

# Login page
if st.session_state['current_page'] == "Login" and not st.session_state['logged_in']:
    st.subheader("Login")
    email = st.text_input("Email", key="login_email")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login", key="login_button"):
        if not validate_email(email):
            st.toast("Please enter a valid email.", icon="❌")
        else:
            user = users_collection.find_one({"email": email})
            if user:
                if check_password(password, user["password"].encode('utf-8')):
                    st.session_state['logged_in'] = True
                    st.session_state['user_email'] = email
                    logins_collection.insert_one({
                        "email": email,
                        "success": True,
                        "login_time": datetime.now()
                    })
                    st.toast("Login successful!", icon="✅")
                    navigate_to("Options")
                else:
                    logins_collection.insert_one({
                        "email": email,
                        "success": False,
                        "login_time": datetime.now()
                    })
                    st.toast("Incorrect password.", icon="❌")
            else:
                logins_collection.insert_one({
                    "email": email,
                    "success": False,
                    "login_time": datetime.now()
                })
                st.toast("Email not found.", icon="❌")

# Image and CSV management function
def manage_images_and_csv(folder_path, file_path_csv):
    st.subheader("Image Management")
    
    if st.button("📤 Import Images"):
        if os.path.exists(folder_path):
            images_collection.delete_many({})
            imported_count = 0
            for filename in os.listdir(folder_path):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    full_path = os.path.join(folder_path, filename)
                    try:
                        encoded_image = encode_image_to_base64(full_path)
                        images_collection.insert_one({
                            "filename": filename,
                            "data": encoded_image
                        })
                        imported_count += 1
                    except Exception as e:
                        st.error(f"Failed to import {filename}: {str(e)}")
            st.success(f"Imported {imported_count} images successfully!")
        else:
            st.error("The specified folder path does not exist.")

    if st.button("📊 Show Images"):
        images = list(images_collection.find({}, {"_id": 0, "filename": 1, "data": 1}))
        if images:
            for image in images:
                try:
                    img = decode_image(image["data"])
                    st.image(img, caption=image['filename'], use_container_width=True)
                except Exception as e:
                    st.error(f"Failed to display {image['filename']}: {str(e)}")
        else:
            st.info("No images found in database.")

    if st.button("🚫 Clear Images"):
        try:
            result = images_collection.delete_many({})
            st.success(f"Deleted {result.deleted_count} images!")
        except Exception as e:
            st.error(f"Error clearing images: {str(e)}")

    st.subheader("CSV Management")
    
    if st.button("📤 Import CSV"):
        is_valid, msg = validate_csv_file(file_path_csv)
        if not is_valid:
            st.error(f"Invalid CSV file: {msg}")
            return
            
        try:
            csv_collection.delete_many({})
            
            # Try reading with standard parameters first
            try:
                df_csv = pd.read_csv(
                    file_path_csv,
                    sep=';',
                    encoding='utf-8-sig',
                    quoting=csv.QUOTE_ALL
                )
            except pd.errors.ParserError:
                # Fallback to python engine if default fails
                df_csv = pd.read_csv(
                    file_path_csv,
                    sep=';',
                    encoding='utf-8-sig',
                    engine='python',
                    quoting=csv.QUOTE_ALL
                )
            
            # Clean the dataframe
            df_csv = df_csv.dropna(how='all')
            csv_data = df_csv.to_dict(orient="records")
            
            if csv_data:
                csv_collection.insert_many(csv_data)
                st.success(f"Successfully imported {len(csv_data)} records!")
            else:
                st.warning("CSV file contained no valid data")
                
        except Exception as e:
            st.error(f"Failed to import CSV: {str(e)}")
            # Show sample data for debugging
            try:
                with open(file_path_csv, 'r', encoding='utf-8-sig') as f:
                    sample = "".join([next(f) for _ in range(3)])
                st.text("First 3 lines of CSV:")
                st.code(sample)
            except:
                st.text("Could not read file for debugging")

    if st.button("📊 Show CSV Data"):
        saved_csv_data = list(csv_collection.find({}, {"_id": 0}))
        if saved_csv_data:
            df_csv_db = pd.DataFrame(saved_csv_data)
            st.dataframe(df_csv_db)
        else:
            st.info("No CSV data found in database.")

    if st.button("🚫 Clear CSV Data"):
        try:
            result = csv_collection.delete_many({})
            st.success(f"Deleted {result.deleted_count} CSV records!")
        except Exception as e:
            st.error(f"Error clearing CSV data: {str(e)}")

    if st.button("🔙 Back to Options"):
        navigate_to("Options")

# Options page
if st.session_state['current_page'] == "Options" and st.session_state['logged_in']:
    st.header("📁 Available Options")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📁 MD ELEKTRONIK"):
            navigate_to("MD ELEKTRONIK")
    with col2:
        if st.button("📁 Rosenberger"):
            navigate_to("Rosenberger")
    with col3:
        if st.button("📊 View History"):
            navigate_to("History")
    
    st.markdown("---")
    st.markdown("""
        **Instructions:**
        - Select **MD ELEKTRONIK** or **Rosenberger** to manage images and CSV files
        - Click **View History** to see recent logins
    """)

# History page
if st.session_state['current_page'] == "History" and st.session_state['logged_in']:
    st.header("Login History (Last 10 Connections)")
    user_history = list(
        logins_collection.find({"success": True})
        .sort("login_time", -1)
        .limit(10)
    )
    
    if user_history:
        history_data = []
        for record in user_history:
            history_data.append({
                "Date/Time": record["login_time"].strftime("%Y-%m-%d %H:%M:%S"),
                "Email": record["email"],
                "Status": "Success"
            })
        
        df_history = pd.DataFrame(history_data)
        st.dataframe(df_history)
    else:
        st.info("No login history found.")
    
    if st.button("🔙 Back to Options"):
        navigate_to("Options")

# Rosenberger section
if st.session_state['current_page'] == "Rosenberger" and st.session_state['logged_in']:
    st.header("Rosenberger: Image and CSV Management")
    folder_path_a = "C:/Users/MSI/Desktop/pfee/PROJET1/IMAGE2"
    file_path_csv_a = "C:/Users/MSI/Desktop/pfee/PROJET1/RESULTATS/donnees_brutes.csv"
    
    # Onglets pour une meilleure organisation
    tab1, tab2, tab3 = st.tabs(["Gestion Images/CSV", "Recherche", "Clusters"])
    
    with tab1:
        manage_images_and_csv(folder_path_a, file_path_csv_a)
    
    with tab2:
        st.subheader("🔎 Recherche par nom d'image")
        search_query = st.text_input("Entrez le nom de l'image - Rosenberger", key="search_image_1")
        if st.button("🔍 Rechercher", key="search_button_1"):
            image_data = images_collection.find_one({"filename": search_query}, {"_id": 0, "data": 1})
            csv_data = list(csv_collection.find({"Nom du fichier": search_query}, {"_id": 0}))
            
            if image_data:
                try:
                    img = decode_image(image_data['data'])
                    st.image(img, caption=search_query, use_container_width=True)
                except Exception as e:
                    st.error(f"Erreur d'affichage: {str(e)}")
            else:
                st.error("Image non trouvée")
            
            if csv_data:
                df_csv = pd.DataFrame(csv_data)
                st.dataframe(df_csv)
            else:
                st.info("Aucune donnée CSV correspondante")
    
    with tab3:
        st.subheader("📊 Données Clusters")
        if st.button("Afficher les clusters Rosenberger"):
            clusters_path = "C:/Users/MSI/Desktop/pfee/PROJET1/RESULTATS/clusters_groupes.csv"
            display_clusters(clusters_path, "Rosenberger")

# MD ELEKTRONIK section
if st.session_state['current_page'] == "MD ELEKTRONIK" and st.session_state['logged_in']:
    st.header("MD ELEKTRONIK: Image and CSV Management")
    folder_path_b = "C:/Users/MSI/Desktop/pfee/PROJET/IMAGES2"
    file_path_csv_b = "C:/Users/MSI/Desktop/pfee/PROJET/RESULTATS/donnees_brutes.csv"
    
    # Onglets pour une meilleure organisation
    tab1, tab2, tab3 = st.tabs(["Gestion Images/CSV", "Recherche", "Clusters"])
    
    with tab1:
        manage_images_and_csv(folder_path_b, file_path_csv_b)
    
    with tab2:
        st.subheader("🔍 Recherche par nom d'image")
        search_query = st.text_input("Entrez le nom de l'image - MD ELEKTRONIK", key="search_image_2")
        if st.button("🔍 Rechercher", key="search_button_2"):
            image_data = images_collection.find_one({"filename": search_query}, {"_id": 0, "data": 1})
            csv_data = list(csv_collection.find({"Nom du fichier": search_query}, {"_id": 0}))
            
            if image_data:
                try:
                    img = decode_image(image_data['data'])
                    st.image(img, caption=search_query, use_container_width=True)
                except Exception as e:
                    st.error(f"Erreur d'affichage: {str(e)}")
            else:
                st.error("Image non trouvée")
            
            if csv_data:
                df_csv = pd.DataFrame(csv_data)
                st.dataframe(df_csv)
            else:
                st.info("Aucune donnée CSV correspondante")
    
    with tab3:
        st.subheader("📊 Données Clusters")
        if st.button("Afficher les clusters MD ELEKTRONIK"):
            clusters_path = "C:/Users/MSI/Desktop/pfee/PROJET/RESULTATS/clusters_groupes.csv"
            display_clusters(clusters_path, "MD ELEKTRONIK")

# Authentication check
if not st.session_state['logged_in']:
    st.warning("Please log in to access the platform")
    navigate_to("Login")