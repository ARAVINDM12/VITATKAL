import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pytz
import time



CSV_FILE = "vitatkal_requests.csv"

# Initialize CSV
def init_csv():
    expected_columns = [
        "Name", "Age", "Gender", "Class", "Boarding Station",
        "Destination", "Phone", "Date of Journey", "Date", "Status"
    ]
    if not os.path.exists(CSV_FILE):
        pd.DataFrame(columns=expected_columns).to_csv(CSV_FILE, index=False)
    else:
        df = pd.read_csv(CSV_FILE)
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""
        df = df[expected_columns]
        df.to_csv(CSV_FILE, index=False)

def load_data():
    return pd.read_csv(CSV_FILE)

def save_booking(data):
    df = load_data()
    df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
    df.to_csv(CSV_FILE, index=False)

def mark_as_booked(index):
    df = load_data()
    df.at[index, "Status"] = "Booked ✅"
    df.to_csv(CSV_FILE, index=False)

def mark_as_pending(index):
    df = load_data()
    df.at[index, "Status"] = "Pending"
    df.to_csv(CSV_FILE, index=False)

def delete_booking(index):
    df = load_data()
    df = df.drop(index=index)
    df.to_csv(CSV_FILE, index=False)

def send_email_notification(data):
    try:
        sender = st.secrets["email"]["sender"]
        password = st.secrets["email"]["password"]
        receiver = st.secrets["email"]["receiver"]

        subject = f"🚨 New Vitatkal Booking Request from {data['Name']}"
        body = "\n".join([f"{k}: {v}" for k, v in data.items()])

        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = receiver
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
        print("✅ Email sent successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to send email: {e}")
        return False

# Page config
st.set_page_config("Vitatkal Booking System", layout="centered", page_icon="🚅")

# Init CSV
init_csv()

# Read query parameters
params = st.query_params
is_admin = params.get("admin", "false").lower() == "true"
restart = params.get("restart", "false").lower() == "true"

# Handle restart
if restart:
    st.session_state.submitted = False
    st.query_params.clear()
    st.rerun()

# ---------- ADMIN PANEL ----------
if is_admin:
    st.title("🛡️ VITATKAL ADMIN PANEL")
    admin_pass = st.text_input("ENTER ADMIN ACCESS CODE", type="password")

    if admin_pass == st.secrets["admin"]["pass"]:
        st.success("✅ ACCESS GRANTED")
        df = load_data()

        if df.empty:
            st.info("No bookings found.")
        else:
            df["Date of Journey"] = pd.to_datetime(df["Date of Journey"], errors="coerce")
            df = df.dropna(subset=["Date of Journey"])
            df = df.sort_values("Date of Journey", ascending=False)

            # ----- 📊 Summary Dashboard -----
            total = len(df)
            pending = len(df[df["Status"] == "Pending"])
            booked = len(df[df["Status"] == "Booked ✅"])
            upcoming_dates = sorted(df["Date of Journey"].dt.strftime("%Y-%m-%d").unique())

            st.markdown("## 📊 Summary Dashboard")
            col1, col2, col3 = st.columns(3)
            col1.metric("📋 Total Requests", total)
            col2.metric("⏳ Pending", pending)
            col3.metric("✅ Booked", booked)
            st.markdown("---")

            # ---------- Grouped View Below ----------
            grouped = df.groupby(df["Date of Journey"].dt.strftime("%Y-%m-%d"))
            for date in sorted(grouped.groups.keys()):
                group = grouped.get_group(date)
                st.markdown(f"### 📅 {date} — {len(group)} Request(s)")
                for _, row in group.iterrows():
                    status = row["Status"]
                    with st.expander(f"🎫 {row['Name']} — {status} | {row['Boarding Station']} → {row['Destination']}"):
                        cleaned_data = {k: v for k, v in row.items() if k not in ["Date", "Status"]}
                        if isinstance(cleaned_data.get("Date of Journey"), pd.Timestamp):
                            cleaned_data["Date of Journey"] = cleaned_data["Date of Journey"].strftime("%Y-%m-%d")
                        for k, v in cleaned_data.items():
                            st.markdown(f"- **{k}**: {v}")

                        col1, col2, col3 = st.columns(3)
                        if row["Status"] != "Booked ✅":
                            if col1.button("✅ Mark as Booked", key=f"book_{row.name}"):
                                mark_as_booked(row.name)
                                st.success(f"Marked {row['Name']} as booked.")
                                time.sleep(1)
                                st.rerun()
                        else:
                            if col1.button("🔄 Mark as Pending", key=f"pending_{row.name}"):
                                mark_as_pending(row.name)
                                st.info(f"Marked {row['Name']} as pending.")
                                time.sleep(1)
                                st.rerun()

                        if col3.button("🗑️ Delete Request", key=f"delete_{row.name}"):
                            delete_booking(row.name)
                            st.warning(f"Deleted booking for {row['Name']}")
                            time.sleep(1)
                            st.rerun()

    else:
        if admin_pass:
            st.error("⛔ ACCESS DENIED")

# ---------- USER FORM ----------
else:
    st.title("🚅 VITATKAL Booking System")

    if st.session_state.get("submitted", False):
        st.success("✅ Your booking request has been submitted successfully!")
        st.balloons()
        st.markdown("""
        ### 🎟️ Next Steps
        - Our team will verify your details and contact you via Whatsapp.
        - You’ll be notified via call or Whatsapp once it is booked.
        - For urgent help, contact: **+91 93834 96183** | **+91 97787 01912**

        [🔁 Make another request](?restart=true)
        """, unsafe_allow_html=True)
        st.stop()

    with st.form("booking_form"):
        st.subheader("📝 Passenger Details")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Full Name*")
            age = st.number_input("Age*", min_value=1, max_value=100, value=25)
            gender = st.selectbox("Gender*", ["Male", "Female", "Other"])
        with col2:
            phone = st.text_input("Mobile Number*")
            train_class = st.selectbox("Class*", ["Sleeper", "3A","3E", "2A", "1A", "CC", "2S"])

        st.subheader("🚉 Journey Details")
        col3, col4 = st.columns(2)
        with col3:
            boarding = st.text_input("Boarding Station*")
        with col4:
            destination = st.text_input("Destination Station*")

        india_tz = pytz.timezone("Asia/Kolkata")
        now_ist = datetime.now(india_tz)
        tomorrow = now_ist + timedelta(days=1)

        doj = st.date_input("Date of Journey*", value=tomorrow.date(), min_value=now_ist.date())

        submitted = st.form_submit_button("SUBMIT BOOKING REQUEST")

        if submitted:
            if not phone.isdigit() or len(phone) != 10:
                st.error("❌ Invalid phone number")
                st.stop()

            if name and phone and boarding and destination:
                data = {
                    "Name": name,
                    "Age": age,
                    "Gender": gender,
                    "Class": train_class,
                    "Boarding Station": boarding,
                    "Destination": destination,
                    "Phone": phone,
                    "Date of Journey": doj.strftime("%Y-%m-%d"),
                    "Date": now_ist.strftime("%Y-%m-%d"),
                    "Status": "Pending"
                }
                save_booking(data)
                if send_email_notification(data):
                    st.session_state.submitted = True
                    st.rerun()
                else:
                    st.warning("⚠️ Booking saved but failed to send email notification.")
            else:
                st.error("❌ Please fill all required fields")

    st.markdown("""
    <div style='text-align: center; margin-top: 40px; font-size: 0.8rem; color: #666;'>
        ©️ 2025 Vitatkal Booking System | Premium Railway Services<br>
        For support: vitatkal@gmail.com | Phone: +91 93834 96183 | +91 97787 01912
    </div>
    """, unsafe_allow_html=True)
