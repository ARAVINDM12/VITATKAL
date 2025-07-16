# VITATKAL

🚅 Vitatkal Booking System
Vitatkal is a lightweight, user-friendly railway Tatkal booking request management system built with Streamlit.
It enables users to submit booking requests, and provides a secure admin panel for managing, tracking, and organizing all submissions.

🔧 Features
📝 Booking Form for users to submit passenger and journey details.

📧 Email Notification sent automatically on each new request.

🛡️ Admin Panel (accessible via ?admin=true) with:

📊 Summary Dashboard showing total, pending, and booked requests.

📅 Grouped view by Date of Journey for better organization.

✅ Mark requests as Booked or revert to Pending.

🗑️ Delete individual booking requests if needed.

💾 Uses a CSV file (vitatkal_requests.csv) as a lightweight database.

🔐 Admin access secured via Streamlit Secrets.

🕒 Automatically sets tomorrow’s date as the default journey date.

📁 Tech Stack
Python 3

Streamlit

Pandas

SMTP (for Gmail integration)
