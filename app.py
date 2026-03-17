import streamlit as st
from groq import Groq
from supabase import create_client, Client
import uuid

# --- CONFIGURATION & SECRETS ---
# Ensure these secrets are added in Streamlit Cloud Settings -> Secrets
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    st.error(f"⚠️ Secrets Configuration Error: {e}")
    st.stop()

# --- PAGE SETTINGS ---
st.set_page_config(page_title="MailWise AI Pro", page_icon="🚀", layout="wide")

# --- DATABASE FUNCTIONS ---
def get_user_data(email):
    response = supabase.table("users_credits").select("*").eq("email", email).execute()
    return response.data[0] if response.data else None

def create_user(email, ref_by=None):
    ref_code = str(uuid.uuid4())[:8]
    new_user = {
        "email": email,
        "credits_left": 10,
        "referral_code": ref_code,
        "referred_by": ref_by
    }
    supabase.table("users_credits").insert(new_user).execute()
    
    if ref_by:
        inviter_res = supabase.table("users_credits").select("*").eq("referral_code", ref_by).execute()
        if inviter_res.data:
            new_count = inviter_res.data[0]['referred_count'] + 1
            is_prem = True if new_count >= 2 else False
            supabase.table("users_credits").update({"referred_count": new_count, "is_premium": is_prem}).eq("referral_code", ref_by).execute()
    
    return get_user_data(email)

# --- APP LOGIC ---
# Handle Referral link (?ref=xyz)
query_params = st.query_params
ref_from_url = query_params.get("ref")

if "user_email" not in st.session_state:
    st.title("🔐 Welcome to MailWise AI")
    st.subheader("Professional SaaS for Email Intelligence")
    st.write("Please enter your email to get **10 Free AI Credits**.")
    
    email_input = st.text_input("Business Email Address:")
    if st.button("Start Free Trial"):
        if email_input:
            user = get_user_data(email_input)
            if not user:
                user = create_user(email_input, ref_from_url)
                st.success("Account created! 10 free credits added.")
            st.session_state.user_email = email_input
            st.rerun()
        else:
            st.warning("Please enter a valid email.")
else:
    # --- DASHBOARD AFTER LOGIN ---
    user = get_user_data(st.session_state.user_email)
    
    with st.sidebar:
        st.title("🚀 MailWise Pro")
        st.write(f"User: **{user['email']}**")
        
        if user['is_premium']:
            st.success("⭐ PREMIUM: Unlimited Access")
        else:
            st.write(f"Credits: **{user['credits_left']}/10**")
            st.progress(user['credits_left'] / 10)
        
        st.divider()
        st.subheader("🎁 Free Unlimited Access")
        st.write("Invite 2 friends to get **Premium** for 4 days.")
        ref_link = f"https://mailwise-ai.streamlit.app/?ref={user['referral_code']}"
        st.code(ref_link, language="text")
        st.write(f"Friends invited: {user['referred_count']}/2")
        
        if st.button("Logout"):
            del st.session_state.user_email
            st.rerun()

    # --- MAIN AI INTERFACE ---
    st.title("📨 AI Email Assistant")
    email_content = st.text_area("Paste Incoming Email Here:", height=250)
    
    if st.button("🚀 Analyze with AI"):
        if user['credits_left'] > 0 or user['is_premium']:
            if email_content:
                with st.spinner("Processing..."):
                    try:
                        prompt = f"Summarize and draft a reply for: {email_content}"
                        chat_completion = client.chat.completions.create(
                            messages=[{"role": "user", "content": prompt}],
                            model="llama-3.3-70b-versatile",
                        )
                        st.markdown("### ⚡ AI Output:")
                        st.write(chat_completion.choices[0].message.content)
                        
                        # Deduct Credit if not premium
                        if not user['is_premium']:
                            supabase.table("users_credits").update({"credits_left": user['credits_left'] - 1}).eq("email", user['email']).execute()
                    except Exception as e:
                        st.error(f"AI Error: {e}")
            else:
                st.warning("Please paste an email content.")
        else:
            st.error("❌ No credits left! Invite 2 friends to get more.")