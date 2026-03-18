import streamlit as st
from groq import Groq
from supabase import create_client
import uuid

# --- CONFIGURATION ---
st.set_page_config(page_title="MailWise Pro", page_icon="🚀")

@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"].strip().rstrip('/')
        key = st.secrets["SUPABASE_KEY"].strip()
        return create_client(url, key)
    except Exception as e:
        st.error(f"Config Error: {e}")
        return None

supabase = init_supabase()
client = Groq(api_key=st.secrets["GROQ_API_KEY"].strip())

# --- DATABASE LOGIC ---
def get_user_data(email):
    try:
        # اینجا از لیست استفاده می‌کنیم تا خطای انتخاب خالی ندهد
        res = supabase.table("users_credits").select("*").eq("email", email).execute()
        return res.data[0] if len(res.data) > 0 else None
    except Exception as e:
        st.error(f"🔍 Database Read Error: {e}")
        return "ERROR"

def register_user(email, ref_by=None):
    try:
        ref_code = str(uuid.uuid4())[:8]
        new_user = {
            "email": email,
            "credits_left": 10,
            "referral_code": ref_code,
            "referred_by": str(ref_by) if ref_by and ref_by != "None" else None
        }
        res = supabase.table("users_credits").insert(new_user).execute()
        return res.data[0] if len(res.data) > 0 else None
    except Exception as e:
        st.error(f"❌ Database Write Error: {e}")
        return None

# --- UI LOGIC ---
if "user_email" not in st.session_state:
    st.title("🔐 MailWise Login")
    email_in = st.text_input("Enter your business email:")
    if st.button("Access AI Dashboard"):
        if email_in:
            with st.spinner("Checking your account..."):
                user = get_user_data(email_in)
                if user == "ERROR":
                    st.error("Please check Supabase connection.")
                elif user is None:
                    # ایجاد کاربر جدید اگر وجود نداشت
                    user = register_user(email_in, st.query_params.get("ref"))
                
                if user and user != "ERROR":
                    st.session_state.user_email = email_in
                    st.rerun()
else:
    # --- DASHBOARD ---
    user = get_user_data(st.session_state.user_email)
    st.success(f"Welcome back, {st.session_state.user_email}!")
    st.write(f"Your Credits: **{user['credits_left']}/10**")
    
    if st.button("Logout"):
        del st.session_state.user_email
        st.rerun()
