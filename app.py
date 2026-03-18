import streamlit as st
from groq import Groq
from supabase import create_client
import uuid
import re

# --- BRANDING & BUSINESS INFO ---
BRAND_NAME = "MailWise AI"
APP_URL = "https://mailwiseai.streamlit.app/"
USDT_WALLET = "0x0c8Cd4Ef0214d8bA0688eD5986176022b7DDB4B5" 
# آدرس اینستاگرام خودت را اینجا بگذار (مثلاً https://instagram.com/your_id)
MY_INSTAGRAM = "https://www.instagram.com/mailwise.ai/" 

st.set_page_config(page_title=f"{BRAND_NAME} | Pro Edition", page_icon="💰", layout="centered")

# --- INITIALIZATION ---
@st.cache_resource
def init_conn():
    try:
        url = st.secrets["SUPABASE_URL"].strip().rstrip('/')
        key = st.secrets["SUPABASE_KEY"].strip()
        g_key = st.secrets["GROQ_API_KEY"].strip()
        return create_client(url, key), Groq(api_key=g_key)
    except Exception as e:
        st.error(f"Config Error: {e}")
        return None, None

supabase, groq_client = init_conn()

# --- HELPER FUNCTIONS ---
def is_valid_email(email):
    return re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email) is not None

def get_user(email):
    try:
        res = supabase.table("users_credits").select("*").eq("email", email).execute()
        return res.data[0] if len(res.data) > 0 else None
    except Exception: return "ERROR"

def register_user(email, ref_by=None):
    try:
        ref_code = str(uuid.uuid4())[:8]
        new_user = {"email": email, "credits_left": 10, "referral_code": ref_code, "referred_by": str(ref_by) if ref_by else None}
        res = supabase.table("users_credits").insert(new_user).execute()
        return res.data[0]
    except Exception: return None

def activate_license(email, input_key):
    try:
        res = supabase.table("license_keys").select("*").eq("key_code", input_key).eq("is_used", False).execute()
        if res.data:
            supabase.table("license_keys").update({"is_used": True, "used_by_email": email}).eq("key_code", input_key).execute()
            supabase.table("users_credits").update({"is_premium": True}).eq("email", email).execute()
            return True
        return False
    except Exception: return False

# --- UI FLOW ---
if "user_email" not in st.session_state:
    st.title(f"🔐 Welcome to {BRAND_NAME}")
    email_in = st.text_input("Enter your business email:")
    if st.button("Start Free Trial"):
        if email_in and is_valid_email(email_in):
            user = get_user(email_in)
            if not user: user = register_user(email_in, st.query_params.get("ref"))
            st.session_state.user_email = email_in
            st.rerun()
        else: st.error("Please enter a valid email.")
else:
    user = get_user(st.session_state.user_email)
    
    with st.sidebar:
        st.title(f"🚀 {BRAND_NAME}")
        st.write(f"Account: **{user['email']}**")
        if user['is_premium']:
            st.success("⭐ PREMIUM: Unlimited Access")
        else:
            st.write(f"Credits: **{user['credits_left']}/10**")
            if st.button("💎 Upgrade to Premium"):
                st.session_state.show_upgrade = True
        st.divider()
        if st.button("Logout"):
            del st.session_state.user_email
            st.rerun()

    if st.session_state.get("show_upgrade"):
        st.title("🏆 Upgrade to Pro Plan")
        st.success("**Unlimited AI Access for 30 Days | Only $10 USDT**")
        
        st.subheader("Step 1: Send $10 USDT")
        st.error("⚠️ IMPORTANT: Send only on **POLYGON (PoS) Network**")
        st.code(USDT_WALLET, language="text")
        
        st.write("Step 2: Send the payment screenshot to our Instagram:")
        st.link_button("DM Screenshot on Instagram", MY_INSTAGRAM)
        
        st.divider()
        st.subheader("Step 3: Enter your License Key")
        key_input = st.text_input("Paste the key you received here:")
        if st.button("Activate Now"):
            if activate_license(user['email'], key_input):
                st.success("🎉 Account Activated! You are now a Pro Member.")
                st.session_state.show_upgrade = False
                st.rerun()
            else: st.error("Invalid or already used key.")
            
        if st.button("← Back to Workspace"):
            st.session_state.show_upgrade = False
            st.rerun()
    else:
        st.title("📨 AI Workspace")
        content = st.text_area("Paste email content:", height=250)
        if st.button("Analyze & Draft Reply", type="primary"):
            if user['is_premium'] or user['credits_left'] > 0:
                with st.spinner("Analyzing..."):
                    try:
                        prompt = f"Summarize and draft a professional reply for: {content}"
                        res = groq_client.chat.completions.create(messages=[{"role":"user","content":prompt}], model="llama-3.3-70b-versatile")
                        st.info(res.choices[0].message.content)
                        if not user['is_premium']:
                            supabase.table("users_credits").update({"credits_left": user['credits_left'] - 1}).eq("email", user['email']).execute()
                    except Exception as e: st.error(f"Error: {e}")
            else: st.error("Out of credits! Please upgrade to Pro.")

st.divider()
st.caption(f"© 2025 {BRAND_NAME} | Support available via Instagram")
