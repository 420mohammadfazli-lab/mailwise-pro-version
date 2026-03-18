import streamlit as st
from groq import Groq
from supabase import create_client
import uuid

# --- CONFIGURATION ---
st.set_page_config(page_title="MailWise Pro", page_icon="🚀")

@st.cache_resource
def init_connection():
    try:
        url = st.secrets["SUPABASE_URL"].strip().rstrip('/')
        key = st.secrets["SUPABASE_KEY"].strip() # حتما service_role باشد
        g_key = st.secrets["GROQ_API_KEY"].strip()
        return create_client(url, key), Groq(api_key=g_key)
    except Exception as e:
        st.error(f"Config Error: {e}")
        return None, None

supabase, client = init_connection()

if not supabase or not client:
    st.stop()

# --- DATABASE LOGIC ---
def get_user_data(email):
    try:
        res = supabase.table("users_credits").select("*").eq("email", email).execute()
        return res.data[0] if len(res.data) > 0 else None
    except Exception as e:
        st.error(f"Database Read Error: {e}")
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
        st.error(f"Registration Error: {e}")
        return None

# --- APP INTERFACE ---
ref_url = st.query_params.get("ref")

if "user_email" not in st.session_state:
    st.title("🔐 MailWise Login")
    st.write("Professional AI for your Business Emails.")
    email_in = st.text_input("Enter your business email:")
    if st.button("Access Dashboard"):
        if email_in:
            user = get_user_data(email_in)
            if user == "ERROR":
                st.info("Check Supabase database settings.")
            elif user is None:
                user = register_user(email_in, ref_url)
            
            if user and user != "ERROR":
                st.session_state.user_email = email_in
                st.rerun()
else:
    # --- DASHBOARD ---
    user = get_user_data(st.session_state.user_email)
    
    with st.sidebar:
        st.title("🚀 MailWise Pro")
        st.write(f"Logged in: {user['email']}")
        st.write(f"Credits: **{user['credits_left']}/10**")
        st.divider()
        ref_link = f"https://mailwise-pro-version-9npiazjngvc3m7tmxarigt.streamlit.app/?ref={user['referral_code']}"
        st.write("Invite friends:")
        st.code(ref_link)
        if st.button("Logout"):
            del st.session_state.user_email
            st.rerun()

    st.title("📨 AI Assistant")
    content = st.text_area("Paste Business Email:")
    if st.button("Analyze & Reply"):
        if user['credits_left'] > 0:
            with st.spinner("AI is thinking..."):
                try:
                    chat = client.chat.completions.create(
                        messages=[{"role": "user", "content": f"Summarize and draft a reply for: {content}"}],
                        model="llama-3.3-70b-versatile"
                    )
                    st.markdown(chat.choices[0].message.content)
                    # کسر اعتبار
                    supabase.table("users_credits").update({"credits_left": user['credits_left'] - 1}).eq("email", user['email']).execute()
                except Exception as e:
                    st.error(f"AI Error: {e}")
        else:
            st.error("Out of credits! Invite friends to get more.")
