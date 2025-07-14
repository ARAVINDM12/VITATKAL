import streamlit as st
import pandas as pd
import os
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# CSV file to store data
CSV_FILE = "tatkal_requests.csv"

# Initialize CSV if not present or incomplete
def init_csv():
    expected_columns = [
        "Name", "Age", "Gender", "Class", "Boarding Station",
        "Destination", "Phone", "Date of Journey", "Date", "Status"
    ]
    if not os.path.exists(CSV_FILE):
        df = pd.DataFrame(columns=expected_columns)
        df.to_csv(CSV_FILE, index=False)
    else:
        df = pd.read_csv(CSV_FILE)
        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""
        df = df[expected_columns]
        df.to_csv(CSV_FILE, index=False)

# Load data
def load_data():
    return pd.read_csv(CSV_FILE)

# Save a new booking
def save_booking(data):
    df = load_data()
    df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
    df.to_csv(CSV_FILE, index=False)

# Mark a booking as done
def mark_as_booked(index):
    df = load_data()
    df.at[index, "Status"] = "Booked ✅"
    df.to_csv(CSV_FILE, index=False)

# Send email notification
def send_email_notification(data):
    try:
        sender = st.secrets["email"]["sender"]
        password = st.secrets["email"]["password"]
        receiver = st.secrets["email"]["receiver"]

        subject = f"🚨 New Tatkal Booking Request from {data['Name']}"
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
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

# ----------- STREAMLIT UI -------------
st.set_page_config(page_title="Tatkal Booking", layout="centered")

init_csv()

# Admin check
query_params = st.query_params
is_admin = query_params.get("admin", "").lower() == "true"

# ---------- ADMIN PANEL ----------
if is_admin:
    st.title("🔐 Admin Dashboard")
    admin_pass = st.text_input("Enter Admin Password", type="password")

    if admin_pass == "EKx85dRzMrd4JdU":
        st.success("Access granted ✅")
        st.subheader("📂 Booking Requests")

        df = load_data()

        if df.empty:
            st.info("No bookings yet.")
        else:
            df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
            df = df.dropna(subset=["Date"])
            df = df.sort_values("Date", ascending=False)

            grouped = df.groupby(df["Date"].dt.strftime("%Y-%m-%d"))
            sorted_dates = sorted(grouped.groups.keys(), reverse=True)

            for date in sorted_dates:
                group = grouped.get_group(date)
                st.markdown(f"### 📅 {date} — {len(group)} booking(s)")

                for i, row in group.iterrows():
                    with st.expander(f"{row['Name']} — {row['Status']}"):
                        cols = st.columns(2)
                        for key, val in row.items():
                            if key not in ["Status", "Date"]:
                                cols[0].markdown(f"**{key}:**")
                                cols[1].markdown(f"{val}")
                        if row["Status"] != "Booked ✅":
                            if st.button(f"Mark as Booked", key=f"book_{i}"):
                                mark_as_booked(i)
                                st.success(f"{row['Name']}'s ticket marked as Booked ✅")
                                st.rerun()
    else:
        st.warning("Incorrect password or unauthorized access.")

# ---------- USER FORM ----------
else:
    st.title("🚆 Tatkal Booking Request Form")

    all_data = load_data()
    total_booked = all_data[all_data["Status"] == "Booked ✅"].shape[0]
    st.markdown(f"### 💺 {100 + total_booked} Tatkal Tickets Booked So Far!")

    with st.form("booking_form"):
        st.subheader("📋 Enter Passenger Details")
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Name")
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])
            boarding = st.text_input("Boarding Station")
            doj = st.date_input("Date of Journey")

        with col2:
            age = st.number_input("Age", min_value=1, max_value=100)
            train_class = st.selectbox("Class", ["Sleeper", "3A", "2A", "1A", "CC", "2S"])
            destination = st.text_input("Destination")
            phone = st.text_input("Phone (WhatsApp)")

        submitted = st.form_submit_button("Submit Request")

        if submitted:
            if name and phone:
                data = {
                    "Name": name,
                    "Age": age,
                    "Gender": gender,
                    "Class": train_class,
                    "Boarding Station": boarding,
                    "Destination": destination,
                    "Phone": phone,
                    "Date of Journey": doj.strftime("%Y-%m-%d"),
                    "Date": datetime.now().strftime("%Y-%m-%d"),
                    "Status": "Pending"
                }
                save_booking(data)
                send_email_notification(data)  # 🔔 Email
                st.success("✅ Request submitted successfully! Our team will contact you shortly.")
                st.toast("📩 Confirmation saved successfully!", icon="✅")
                st.rerun()
            else:
                st.error("❌ Please fill in at least Name and Phone.")
