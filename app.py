import streamlit as st
from groq import Groq
from supabase import create_client
import uuid
import re  # کتابخانه برای چک کردن فرمت ایمیل

# --- BRANDING & CONFIG ---
BRAND_NAME = "MailWise AI"
APP_URL = "https://mailwiseai.streamlit.app/"

st.set_page_config(page_title=f"{BRAND_NAME} | Professional AI", page_icon="🚀", layout="centered")

# --- FUNCTION: VALIDATE EMAIL ---
def is_valid_email(email):
    # این الگو چک می‌کند که متن حتما به فرمت email@domain.com باشد
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

# --- CSS ---
st.markdown("""
    <style>
    .stTextArea textarea { font-size: 16px !important; border-radius: 12px; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def init_connections():
    try:
        url = st.secrets["SUPABASE_URL"].strip().rstrip('/')
        key = st.secrets["SUPABASE_KEY"].strip()
        g_key = st.secrets["GROQ_API_KEY"].strip()
        return create_client(url, key), Groq(api_key=g_key)
    except Exception as e:
        st.error(f"Config Error: {e}")
        return None, None

supabase, groq_client = init_connections()

if not supabase or not groq_client:
    st.stop()

# --- DATABASE FUNCTIONS ---
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
        
        if ref_by and ref_by != "None":
            inviter = supabase.table("users_credits").select("*").eq("referral_code", ref_by).execute()
            if inviter.data:
                new_count = inviter.data[0]['referred_count'] + 1
                is_prem = True if new_count >= 2 else False
                supabase.table("users_credits").update({"referred_count": new_count, "is_premium": is_prem}).eq("referral_code", ref_by).execute()
        
        return res.data[0]
    except Exception: return None

# --- APP FLOW ---
ref_id = st.query_params.get("ref")

if "user_email" not in st.session_state:
    st.title(f"🔐 {BRAND_NAME} Login")
    st.write("Please enter your business email to continue.")
    
    email_input = st.text_input("Email Address:", placeholder="example@company.com")
    
    if st.button("Log In / Start Free Trial", use_container_width=True):
        if email_input:
            # --- چک کردن معتبر بودن ایمیل ---
            if is_valid_email(email_input):
                with st.spinner("Authenticating..."):
                    user = get_user(email_input)
                    if user == "ERROR": st.warning("Database connection failed.")
                    elif user is None: user = register_user(email_input, ref_id)
                    if user and user != "ERROR":
                        st.session_state.user_email = email_input
                        st.rerun()
            else:
                # اگر ایمیل نامعتبر بود این پیام را نشان بده
                st.error("⚠️ Please enter a valid email address (e.g., name@domain.com)")
        else:
            st.warning("Email field cannot be empty.")

else:
    # (بقیه کد داشبورد که قبلا داشتیم...)
    user = get_user(st.session_state.user_email)
    with st.sidebar:
        st.title(f"🚀 {BRAND_NAME}")
        st.write(f"Logged in: **{user['email']}**")
        if user['is_premium']: st.success("⭐ Premium Access")
        else:
            st.write(f"Credits: **{user['credits_left']}/10**")
            st.progress(user['credits_left'] / 10)
        st.divider()
        st.code(f"{APP_URL}?ref={user['referral_code']}", language="text")
        if st.button("Log Out"):
            del st.session_state.user_email
            st.rerun()

    st.title("📨 AI Workspace")
    email_content = st.text_area("Paste email content:", height=250)
    if st.button("Analyze & Reply", type="primary", use_container_width=True):
        if user['credits_left'] > 0 or user['is_premium']:
            with st.spinner("AI is thinking..."):
                try:
                    prompt = f"Summarize and reply to: {email_content}"
                    completion = groq_client.chat.completions.create(messages=[{"role": "user", "content": prompt}], model="llama-3.3-70b-versatile")
                    st.info(completion.choices[0].message.content)
                    if not user['is_premium']:
                        supabase.table("users_credits").update({"credits_left": user['credits_left'] - 1}).eq("email", user['email']).execute()
                except Exception as e: st.error(f"Error: {e}")
        else: st.error("Out of credits!")
