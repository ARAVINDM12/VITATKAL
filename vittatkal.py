import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import pytz
import time
import json 

CSV_FILE = "vitatkal_requests.csv"
AGENTS_FILE = "agents.json"
BOOKED_LOG_FILE = "booked_log.csv"

def load_agents():
    if os.path.exists(AGENTS_FILE):
        return pd.read_json(AGENTS_FILE, typ='series').to_dict()
    else:
        return {
            "Aravind": 30,
            "Nazmil": 30,
            "Christy": 30
        }

def save_agents(agent_dict):
    pd.Series(agent_dict).to_json(AGENTS_FILE)

agents = load_agents()

# Initialize CSV
def init_csv():
    expected_columns = [
        "Name", "Age", "Gender", "Class", "Boarding Station",
        "Destination", "Phone", "Date of Journey", "Date", "Status", "GroupID"
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

def save_booking(data_list):
    df = load_data()
    df = pd.concat([df, pd.DataFrame(data_list)], ignore_index=True)
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
    group_id = df.at[index, "GroupID"]
    df = df[df["GroupID"] != group_id]
    df.to_csv(CSV_FILE, index=False)

def send_email_notification(data_list):
    try:
        sender = st.secrets["email"]["sender"]
        password = st.secrets["email"]["password"]
        receiver = st.secrets["email"]["receiver"]

        subject = f"🚨 New Vitatkal Booking Request from {data_list[0]['Name']}"
        body_lines = ["Booking Group Details:\n"]

        # Common info
        common_keys = ["Class", "Boarding Station", "Destination", "Phone", "Date of Journey"]
        for key in common_keys:
            body_lines.append(f"{key}: {data_list[0][key]}")

        body_lines.append("\nPassenger Details:")
        for i, data in enumerate(data_list):
            body_lines.append(f"Passenger {i + 1}:")
            body_lines.append(f"  Name: {data['Name']}")
            body_lines.append(f"  Age: {data['Age']}")
            body_lines.append(f"  Gender: {data['Gender']}")
            body_lines.append("")

        body = "\n".join(body_lines)

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

        tab1, tab2, tab3 ,tab4 = st.tabs(["📋 Booking Requests","📊 Summary Dashboard", "👤 Agent Dashboard", "💳 Finances"])

        with tab1:
            if df.empty:
                st.info("No bookings found.")
            else:
                df["Date of Journey"] = pd.to_datetime(df["Date of Journey"], errors="coerce")
                df = df.dropna(subset=["Date of Journey"])
                df = df.sort_values("Date of Journey", ascending=False)

                total = df["GroupID"].nunique()
                pending = df[df["Status"] == "Pending"]["GroupID"].nunique()
                booked = df[df["Status"] == "Booked ✅"]["GroupID"].nunique()

                st.markdown("## 📋 Booking Requests")
                col1, col2, col3 = st.columns(3)
                col1.metric("📋 Total Requests", total)
                col2.metric("⏳ Pending", pending)
                col3.metric("✅ Booked", booked)
                st.markdown("---")

                # 🌟 Group by Date of Journey
                grouped_by_date = df.groupby(df["Date of Journey"].dt.strftime("%Y-%m-%d"))

                for journey_date in sorted(grouped_by_date.groups.keys(), reverse=True):
                    group_df = grouped_by_date.get_group(journey_date)
                    grouped = group_df.groupby("GroupID")
                    if grouped.ngroups == 0:
                        continue  # ⛔️ Skip this date section if there are no groups

                    st.markdown(f"### 📅 {journey_date} — {grouped.ngroups} Request(s)")


                    for group_id, group in grouped:
                        main_row = group.iloc[0]
                        with st.expander(f"🎫 {main_row['Name']} — {main_row['Status']} | {main_row['Boarding Station']} → {main_row['Destination']}"):
                            for passenger_num, (_, row) in enumerate(group.iterrows(), start=1):
                                st.markdown(f"### Passenger {passenger_num}")
                                for k in ["Name", "Age", "Gender"]:
                                    st.markdown(f"- **{k}**: {row[k]}")
                            st.markdown("---")
                            for key in ["Class", "Boarding Station", "Destination", "Phone", "Date of Journey"]:
                                st.markdown(f"**{key}**: {main_row[key]}")

                            col1, col2, col3 = st.columns(3)
                            if main_row["Status"] != "Booked ✅":
                                if f"show_agent_select_{group_id}" not in st.session_state:
                                    st.session_state[f"show_agent_select_{group_id}"] = False

                                cols = st.columns([2, 2, 1])
                                col1, col2, col3 = cols

                                if not st.session_state[f"show_agent_select_{group_id}"]:
                                    if col1.button("✅ Mark as Booked", key=f"book_btn_{group_id}"):
                                        st.session_state[f"show_agent_select_{group_id}"] = True
                                        st.rerun()
                                else:
                                    selected_agent = col1.selectbox(
                                        "👤 Choose Agent", ["Aravind", "Nazmil", "Christy"],
                                        key=f"agent_select_{group_id}"
                                    )

                                    passenger_count = len(group)
                                    profit_input = col2.number_input(
                                        "💰 Profit ₹",
                                        value=passenger_count * 100,
                                        step=10,
                                        key=f"profit_input_{group_id}"
                                    )

                                    split_col1, split_col2, split_col3 = st.columns(3)
                                    split_aravind = split_col1.slider("Aravind (%)", 0, 100, 50, key=f"split_aravind_{group_id}")
                                    split_nazmil = split_col2.slider("Nazmil (%)", 0, 100, 25, key=f"split_nazmil_{group_id}")
                                    split_christy = split_col3.slider("Christy (%)", 0, 100, 25, key=f"split_christy_{group_id}")

                                    total_split = split_aravind + split_nazmil + split_christy
                                    if total_split != 100:
                                        st.warning("⚠️ Profit split must total 100%.")
                                    else:
                                        if col3.button("✅ Confirm", key=f"confirm_booked_{group_id}"):
                                            # Mark as booked
                                            df.loc[df["GroupID"] == group_id, "Status"] = "Booked ✅"
                                            df.to_csv(CSV_FILE, index=False)

                                            log_entry = {
                                                "Customer Name": main_row["Name"],
                                                "Date of Journey": pd.to_datetime(main_row["Date of Journey"]).strftime("%Y-%m-%d"),
                                                "Agent": selected_agent,
                                                "Profit": float(profit_input),
                                                "Split_Aravind": split_aravind / 100,
                                                "Split_Nazmil": split_nazmil / 100,
                                                "Split_Christy": split_christy / 100
                                            }

                                            if os.path.exists(BOOKED_LOG_FILE):
                                                log_df = pd.read_csv(BOOKED_LOG_FILE)
                                            else:
                                                log_df = pd.DataFrame(columns=["Customer Name", "Date of Journey", "Agent", "Profit"])

                                            log_df = pd.concat([log_df, pd.DataFrame([log_entry])], ignore_index=True)
                                            log_df.to_csv(BOOKED_LOG_FILE, index=False)

                                            st.success(f"✅ Booked and assigned to {selected_agent}")
                                            st.session_state[f"show_agent_select_{group_id}"] = False
                                            st.rerun()

                            else:
                                if col1.button("🔄 Mark as Pending", key=f"pending_{group_id}"):
                                    df.loc[df["GroupID"] == group_id, "Status"] = "Pending"
                                    df.to_csv(CSV_FILE, index=False)

                                    if os.path.exists(BOOKED_LOG_FILE):
                                        log_df = pd.read_csv(BOOKED_LOG_FILE)
                                        updated_log = log_df[log_df["Customer Name"] != main_row["Name"]]
                                        updated_log.to_csv(BOOKED_LOG_FILE, index=False)

                                    st.info(f"Marked group {group_id} as pending and removed log entry.")
                                    time.sleep(1)
                                    st.rerun()

                            if col3.button("🗑️ Delete Request", key=f"delete_{group_id}"):
                                delete_booking(main_row.name)

                                if os.path.exists(BOOKED_LOG_FILE):
                                    log_df = pd.read_csv(BOOKED_LOG_FILE)
                                    updated_log = log_df[~(
                                        (log_df["Customer Name"] == main_row["Name"]) &
                                        (log_df["Date of Journey"] == pd.to_datetime(main_row["Date of Journey"]).strftime("%Y-%m-%d"))
                                    )]
                                    updated_log.to_csv(BOOKED_LOG_FILE, index=False)

                                st.warning(f"Deleted booking and log for group {group_id}")
                                time.sleep(1)
                                st.rerun()



        with tab2:
            st.subheader("📊 Summary Dashboard")

            # Load log
            if os.path.exists(BOOKED_LOG_FILE) and os.path.getsize(BOOKED_LOG_FILE) > 0:
                log_df = pd.read_csv(BOOKED_LOG_FILE)
                log_df["Date of Journey"] = pd.to_datetime(log_df["Date of Journey"], errors="coerce")
                log_df["Profit"] = log_df["Profit"].astype(float)

                # --- Filters ---
                st.markdown("### 🔍 Filter Bookings")

                col_filter1, col_filter2 = st.columns(2)
                with col_filter1:
                    selected_agent = st.selectbox("Filter by Agent", ["All"] + sorted(log_df["Agent"].unique().tolist()))
                with col_filter2:
                    unique_months = log_df["Date of Journey"].dt.to_period("M").dropna().unique()
                    month_options = ["All"] + [str(m) for m in sorted(unique_months, reverse=True)]
                    selected_month = st.selectbox("Filter by Month", month_options)

                # --- Apply Filters ---
                filtered_df = log_df.copy()
                if selected_agent != "All":
                    filtered_df = filtered_df[filtered_df["Agent"] == selected_agent]
                if selected_month != "All":
                    filtered_df = filtered_df[filtered_df["Date of Journey"].dt.to_period("M") == pd.Period(selected_month)]

                # --- Display Table ---
                if not filtered_df.empty:
                    st.dataframe(filtered_df[["Customer Name", "Date of Journey", "Agent", "Profit"]], use_container_width=True)
                    st.markdown(f"**💰 Total Earnings (Filtered):** ₹{filtered_df['Profit'].sum():.2f}")
                else:
                    st.warning("No data found for selected filters.")

            else:
                filtered_df = pd.DataFrame(columns=["Customer Name", "Date of Journey", "Agent", "Profit"])
                st.info("No booking logs available.")

            

            st.markdown("---")

            # Session state triggers
            if "show_add_form" not in st.session_state:
                st.session_state.show_add_form = False
            if "show_edit_form" not in st.session_state:
                st.session_state.show_edit_form = False
            if "show_delete_form" not in st.session_state:
                st.session_state.show_delete_form = False

            # Button controls
            col1, col2, col3 = st.columns(3)
            if col1.button("➕ Add Entry"):
                st.session_state.show_add_form = not st.session_state.show_add_form
                st.session_state.show_edit_form = False
                st.session_state.show_delete_form = False
            if col2.button("✏️ Edit Entry"):
                st.session_state.show_edit_form = not st.session_state.show_edit_form
                st.session_state.show_add_form = False
                st.session_state.show_delete_form = False
            if col3.button("🗑️ Delete Entry"):
                st.session_state.show_delete_form = not st.session_state.show_delete_form
                st.session_state.show_add_form = False
                st.session_state.show_edit_form = False

            # --- Add Entry ---
            if st.session_state.show_add_form:
                st.markdown("### ➕ Add New Entry")
                with st.form("add_entry"):
                    name = st.text_input("Customer Name")
                    date = st.date_input("Date of Journey")
                    agent = st.selectbox("Agent", ["Aravind", "Nazmil", "Christy"])
                    profit = st.number_input("Profit (₹)", min_value=0.0, step=10.0)

                    split_col1, split_col2, split_col3 = st.columns(3)
                    split_aravind = split_col1.slider("Aravind (%)", 0, 100, 50)
                    split_nazmil = split_col2.slider("Nazmil (%)", 0, 100, 25)
                    split_christy = split_col3.slider("Christy (%)", 0, 100, 25)

                    total_split = split_aravind + split_nazmil + split_christy
                    if st.form_submit_button("💾 Save Entry"):
                        if total_split != 100:
                            st.warning("⚠️ Profit split must total 100%.")
                        else:
                            new_row = {
                                "Customer Name": name,
                                "Date of Journey": date.strftime("%Y-%m-%d"),
                                "Agent": agent,
                                "Profit": profit,
                                "Split_Aravind": split_aravind / 100,
                                "Split_Nazmil": split_nazmil / 100,
                                "Split_Christy": split_christy / 100
                            }
                            log_df = pd.concat([log_df, pd.DataFrame([new_row])], ignore_index=True)
                            log_df.to_csv(BOOKED_LOG_FILE, index=False)
                            st.success("✅ Entry added.")
                            st.rerun()


            # --- Edit Entry ---
            if st.session_state.show_edit_form:
                st.markdown("### ✏️ Edit Existing Entry")
                if log_df.empty:
                    st.warning("No entries to edit.")
                else:
                    selected_index = st.selectbox(
                        "Select Row to Edit",
                        options=log_df.index,
                        format_func=lambda i: f"{log_df.at[i, 'Customer Name']} | {log_df.at[i, 'Date of Journey'].date()} | {log_df.at[i, 'Agent']}"
                    )
                    row = log_df.loc[selected_index]

                    with st.form("edit_entry"):
                        name = st.text_input("Customer Name", value=row["Customer Name"])
                        date = st.date_input("Date of Journey", value=pd.to_datetime(row["Date of Journey"]))
                        agent = st.selectbox("Agent", ["Aravind", "Nazmil", "Christy"], index=["Aravind", "Nazmil", "Christy"].index(row["Agent"]))
                        profit = st.number_input("Profit (₹)", min_value=0.0, step=10.0, value=row["Profit"])

                        split_col1, split_col2, split_col3 = st.columns(3)
                        split_aravind = split_col1.slider("Aravind (%)", 0, 100, int(row.get("Split_Aravind", 0.0) * 100))
                        split_nazmil = split_col2.slider("Nazmil (%)", 0, 100, int(row.get("Split_Nazmil", 0.0) * 100))
                        split_christy = split_col3.slider("Christy (%)", 0, 100, int(row.get("Split_Christy", 0.0) * 100))

                        total_split = split_aravind + split_nazmil + split_christy
                        if st.form_submit_button("💾 Update Entry"):
                            if total_split != 100:
                                st.warning("⚠️ Profit split must total 100%.")
                            else:
                                log_df.at[selected_index, "Customer Name"] = name
                                log_df.at[selected_index, "Date of Journey"] = date
                                log_df.at[selected_index, "Agent"] = agent
                                log_df.at[selected_index, "Profit"] = profit
                                log_df.at[selected_index, "Split_Aravind"] = split_aravind / 100
                                log_df.at[selected_index, "Split_Nazmil"] = split_nazmil / 100
                                log_df.at[selected_index, "Split_Christy"] = split_christy / 100
                                log_df.to_csv(BOOKED_LOG_FILE, index=False)
                                st.success("✅ Entry updated.")
                                st.rerun()


            # --- Delete Entry ---
            if st.session_state.show_delete_form:
                st.markdown("### 🗑️ Delete Entry")
                if log_df.empty:
                    st.warning("No entries to delete.")
                else:
                    selected_index = st.selectbox(
                        "Select Row to Delete",
                        options=log_df.index,
                        format_func=lambda i: f"{log_df.at[i, 'Customer Name']} | {log_df.at[i, 'Date of Journey'].date()} | {log_df.at[i, 'Agent']}"
                    )
                    if st.button("⚠️ Confirm Delete"):
                        log_df = log_df.drop(selected_index).reset_index(drop=True)
                        log_df.to_csv(BOOKED_LOG_FILE, index=False)
                        st.warning("❌ Entry deleted.")
                        st.rerun()



        

        with tab3:
            st.subheader("👥 Agent Dashboard")
            # ---------- Style: CSS Hover Effects + Card Design ----------
            st.markdown("""
                <style>
                    .agent-card {
                        border-radius: 15px;
                        padding: 20px 10px 15px 10px;
                        text-align: center;
                        min-height: 240px;
                        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
                        transition: transform 0.2s ease, box-shadow 0.3s ease;
                    }
                    .agent-card:hover {
                        transform: scale(1.02);
                        box-shadow: 0 6px 16px rgba(0,0,0,0.3);
                    }
                </style>
            """, unsafe_allow_html=True)

            # ---------- Agent Configs ----------
            default_agents = {
                "Aravind": {"icon": "🧔", "color": "#FFADAD"},
                "Nazmil": {"icon": "👨‍💼", "color": "#FFD6A5"},
                "Christy": {"icon": "👨‍🎓", "color": "#B5EAD7"}
            }

            # ---------- Load Booking Log ----------
            if os.path.exists(BOOKED_LOG_FILE) and os.path.getsize(BOOKED_LOG_FILE) > 0:
                log_df = pd.read_csv(BOOKED_LOG_FILE)
                log_df["Date of Journey"] = pd.to_datetime(log_df["Date of Journey"], errors="coerce")
                this_month = log_df["Date of Journey"].dt.to_period("M") == pd.Period(datetime.now(), freq="M")


            else:
                log_df = pd.DataFrame(columns=["Customer Name", "Date of Journey", "Agent", "Profit"])
                this_month = pd.Series([False] * len(log_df))

            # ---------- Agent Card Renderer ----------
            def render_agent_card(agent, col, icon, color):
                agent_bookings = log_df[log_df["Agent"] == agent]
                monthly_bookings = log_df[this_month & (log_df["Agent"] == agent)]

                # Ticket counts based on direct bookings only
                total_tickets = len(agent_bookings)
                this_month_count = len(monthly_bookings)

                # Profit split
                if agent in ["Aravind", "Nazmil", "Christy"]:
                    split_column = f"Split_{agent}"
                    if split_column in log_df.columns:
                        total_profit = (log_df["Profit"] * log_df[split_column].fillna(0)).sum()
                    else:
                        total_profit = 0
                else:
                    total_profit = 0


                col.markdown(f"""
                <div class="agent-card" style="background-color: {color};">
                    <div style="font-size: 40px; margin-bottom: 10px;">{icon}</div>
                    <div style="font-size: 20px; font-weight: bold; color: #000;">{agent}</div>
                    <hr style="border: 0.5px solid #666; width: 60%; margin: 10px auto;">
                    <div style="font-size: 15px; color: #000; text-align: left; padding-left: 15px;">
                        🎟️ <b>Total Tickets:</b> {total_tickets}<br>
                        📅 <b>This Month:</b> {this_month_count}<br>
                        💰 <b>Earnings:</b> ₹{total_profit:.2f}
                    </div>
                </div>
                """, unsafe_allow_html=True)


            # ---------- Layout: 3 Cards in Row ----------
            col1, col2, col3 = st.columns(3)
            render_agent_card("Aravind", col1, default_agents["Aravind"]["icon"], default_agents["Aravind"]["color"])
            render_agent_card("Nazmil", col2, default_agents["Nazmil"]["icon"], default_agents["Nazmil"]["color"])
            render_agent_card("Christy", col3, default_agents["Christy"]["icon"], default_agents["Christy"]["color"])


        with tab4:
            st.subheader("💳 Settle Agent Dues")

            # ---------- Load Logs ----------
            booked_df = pd.read_csv(BOOKED_LOG_FILE) if os.path.exists(BOOKED_LOG_FILE) else pd.DataFrame(columns=["Customer Name", "Date of Journey", "Agent", "Profit"])
            settlement_file = "settlement_log.csv"
            settled_df = pd.read_csv(settlement_file) if os.path.exists(settlement_file) else pd.DataFrame(columns=["Agent", "Amount", "Date", "Notes"])

            # ---------- Compute Agent-wise Profit Share ----------
            profit_shares = {"Aravind": 0.5, "Nazmil": 0.25, "Christy": 0.25}
            agent_profits = {agent: 0 for agent in profit_shares}

            for _, row in booked_df.iterrows():
                try:
                    profit = float(row["Profit"])
                    for agent in profit_shares:
                        split_col = f"Split_{agent}"
                        share = row[split_col] if split_col in row else profit_shares[agent]
                        agent_profits[agent] += profit * share
                except:
                    continue


            # ---------- Compute Settled Amounts ----------
            settled_totals = settled_df.groupby("Agent")["Amount"].sum().to_dict()

            # ---------- Display Agent Summary Table ----------
            st.markdown("### 📊 Agent-wise Summary")
            summary_data = []

            for agent in profit_shares:
                total = round(agent_profits.get(agent, 0), 2)
                settled = round(settled_totals.get(agent, 0), 2)
                due = round(total - settled, 2)
                summary_data.append({
                    "Agent": agent,
                    "Total Profit Earned (₹)": total,
                    "Amount Settled (₹)": settled,
                    "Amount Due (₹)": due
                })

            st.dataframe(pd.DataFrame(summary_data), use_container_width=True)

            st.markdown("---")

            # ---------- Settlement Form ----------
            st.markdown("### 💸 Settle Dues")

            with st.form("settle_form"):
                col1, col2 = st.columns(2)
                agent_selected = col1.selectbox("Select Agent", list(profit_shares.keys()))
                amount = col2.number_input("Amount to Settle (₹)", min_value=0.0, step=10.0)

                col3, col4 = st.columns(2)
                date = col3.date_input("Settlement Date", value=datetime.now().date())
                notes = col4.text_input("Notes (optional)", placeholder="e.g., UPI, Cash, etc.")

                submit = st.form_submit_button("💾 Record Settlement")

                if submit:
                    if amount == 0:
                        st.warning("⚠️ Enter a valid amount.")
                    else:
                        new_entry = pd.DataFrame([{
                            "Agent": agent_selected,
                            "Amount": amount,
                            "Date": date.strftime("%Y-%m-%d"),
                            "Notes": notes
                        }])

                        if os.path.exists(settlement_file):
                            settlement_log = pd.read_csv(settlement_file)
                            settlement_log = pd.concat([settlement_log, new_entry], ignore_index=True)
                        else:
                            settlement_log = new_entry

                        settlement_log.to_csv(settlement_file, index=False)
                        st.success(f"✅ ₹{amount} settled to {agent_selected}")
                        st.rerun()

            st.markdown("---")

            # ---------- View Settlement History ----------
            with st.expander("📜 View Settlement History"):
                if not settled_df.empty:
                    st.dataframe(settled_df.sort_values("Date", ascending=False), use_container_width=True)
                else:
                    st.info("No settlements have been recorded yet.")

            st.markdown("---")
            st.markdown("### ✏️ Edit or 🗑️ Delete Settlement Entries")

            if not settled_df.empty:
                settled_df = settled_df.reset_index(drop=True)
                settled_df["Index"] = settled_df.index
                selected_idx = st.selectbox("Select Entry to Modify", settled_df["Index"])

                entry = settled_df.loc[selected_idx]

                with st.form("edit_delete_form"):
                    col1, col2 = st.columns(2)
                    edit_agent = col1.selectbox("Agent", list(profit_shares.keys()), index=list(profit_shares.keys()).index(entry["Agent"]))
                    edit_amount = col2.number_input("Amount (₹)", min_value=0.0, value=float(entry["Amount"]), step=10.0)

                    col3, col4 = st.columns(2)
                    edit_date = col3.date_input("Date", value=pd.to_datetime(entry["Date"]).date())
                    edit_notes = col4.text_input("Notes", value=entry["Notes"])

                    col_a, col_b = st.columns([1, 1])
                    update_btn = col_a.form_submit_button("💾 Update Entry")
                    delete_btn = col_b.form_submit_button("🗑️ Delete Entry")

                    if update_btn:
                        settled_df.at[selected_idx, "Agent"] = edit_agent
                        settled_df.at[selected_idx, "Amount"] = edit_amount
                        settled_df.at[selected_idx, "Date"] = edit_date.strftime("%Y-%m-%d")
                        settled_df.at[selected_idx, "Notes"] = edit_notes
                        settled_df.drop(columns=["Index"], inplace=True)
                        settled_df.to_csv(settlement_file, index=False)
                        st.success("✅ Entry updated successfully.")
                        st.rerun()

                    if delete_btn:
                        settled_df.drop(index=selected_idx, inplace=True)
                        settled_df.drop(columns=["Index"], inplace=True)
                        settled_df.to_csv(settlement_file, index=False)
                        st.warning("🗑️ Entry deleted.")
                        st.rerun()
            else:
                st.info("No settlement records available to edit or delete.")




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

    if "num_passengers" not in st.session_state:
        st.session_state.num_passengers = 1

    with st.form("booking_form"):
        st.subheader("📝 Passenger Details")
        col_main1, col_main2 = st.columns(2)

        with col_main1:
            name = st.text_input("Full Name*")
            age = st.number_input("Age*", min_value=1, max_value=100, value=25)
            gender = st.selectbox("Gender*", ["Male", "Female", "Other"])
        with col_main2:
            phone = st.text_input("Mobile Number*")
            train_class = st.selectbox("Class*", ["Sleeper", "3A", "2A", "1A", "CC", "2S"])

        passenger_data = [{"Name": name, "Age": age, "Gender": gender}]

        for i in range(1, st.session_state.num_passengers):
            st.markdown(f"#### Additional Passenger {i + 1}")
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input(f"Name*", key=f"name_{i}")
                age = st.number_input(f"Age*", min_value=1, max_value=100, value=25, key=f"age_{i}")
            with col2:
                gender = st.selectbox(f"Gender*", ["Male", "Female", "Other"], key=f"gender_{i}")
            passenger_data.append({"Name": name, "Age": age, "Gender": gender})

        st.markdown("""<div style='text-align: right;'>""", unsafe_allow_html=True)
        col_add, col_remove = st.columns([1, 1])
        with col_add:
            add_passenger = st.form_submit_button("➕ Add Extra Passenger")
        with col_remove:
            if st.session_state.num_passengers > 1:
                remove_passenger = st.form_submit_button("➖ Remove Last Passenger")
            else:
                remove_passenger = False

        if add_passenger:
            st.session_state.num_passengers += 1
            st.rerun()
        elif remove_passenger:
            st.session_state.num_passengers -= 1
            st.rerun()

        st.markdown("""</div>""", unsafe_allow_html=True)

        if add_passenger:
            st.session_state.num_passengers += 1
            st.rerun()

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

            if boarding and destination and all(p["Name"] and p["Age"] for p in passenger_data):
                group_id = f"G{int(time.time())}"
                full_data = []
                for p in passenger_data:
                    entry = {
                        **p,
                        "Class": train_class,
                        "Boarding Station": boarding,
                        "Destination": destination,
                        "Phone": phone,
                        "Date of Journey": doj.strftime("%Y-%m-%d"),
                        "Date": now_ist.strftime("%Y-%m-%d"),
                        "Status": "Pending",
                        "GroupID": group_id
                    }
                    full_data.append(entry)

                save_booking(full_data)
                if send_email_notification(full_data):
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
