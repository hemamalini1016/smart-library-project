import json
from pathlib import Path
from datetime import date, timedelta

import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Smart Library Management System",
    page_icon="📚",
    layout="wide"
)

DATA_FILE = Path(__file__).with_name("library_data.json")
LOAN_DAYS = 14
FINE_PER_DAY = 2


def load_data():
    if DATA_FILE.exists():
        try:
            return json.loads(DATA_FILE.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            st.error("The saved data file could not be read.")
            st.stop()
    return {"books": [], "members": [], "loans": []}


def save_data():
    DATA_FILE.write_text(
        json.dumps(data, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )


data = load_data()


def book_by_id(book_id):
    return next(
        (b for b in data["books"] if b["id"] == book_id), None
    )


def member_by_id(member_id):
    return next(
        (m for m in data["members"] if m["id"] == member_id), None
    )


def active_loans():
    return [loan for loan in data["loans"] if not loan["return_date"]]


def fine_for(loan):
    end = (
        date.fromisoformat(loan["return_date"])
        if loan["return_date"]
        else date.today()
    )
    due = date.fromisoformat(loan["due_date"])
    return max(0, (end - due).days) * FINE_PER_DAY


st.sidebar.title("📚 Smart Library")
st.sidebar.caption("Books • Members • Analytics")

page = st.sidebar.radio(
    "Choose a section",
    [
        "Dashboard",
        "Manage Books",
        "Manage Members",
        "Issue Book",
        "Return Book",
        "Overdue & History"
    ]
)

st.sidebar.divider()
st.sidebar.write("*Library rules*")
st.sidebar.write("Borrowing period: 14 days")
st.sidebar.write("Late fine: ₹2 per day")


if page == "Dashboard":
    st.title("📚 Smart Library Dashboard")
    st.write("A smarter way to manage library resources.")

    total = sum(b["total"] for b in data["books"])
    available = sum(b["available"] for b in data["books"])
    borrowed = active_loans()
    overdue = [
        loan for loan in borrowed
        if date.fromisoformat(loan["due_date"]) < date.today()
    ]

    a, b, c, d = st.columns(4)
    a.metric("Total Copies", total)
    b.metric("Available Copies", available)
    c.metric("Books Borrowed", len(borrowed))
    d.metric("Overdue Loans", len(overdue))

    st.divider()
    left, right = st.columns(2)

    with left:
        st.subheader("📊 Popular Books")
        popular = sorted(
            data["books"],
            key=lambda item: item["times_borrowed"],
            reverse=True
        )
        popular = [b for b in popular if b["times_borrowed"] > 0][:10]              
        if popular:
                st.write("Most borrowed books:")
                for book in popular:
                    st.write(
                        f"📚 {book['title']} — "
                        f"Borrowed {book['times_borrowed']} time(s)"
                    )
        else:
                st.info("Issue a book to see popular books here.")
        

    with right:
        st.subheader("📌 Library Summary")
        st.write(f"Registered members: *{len(data['members'])}*")
        st.write(f"Different book titles: *{len(data['books'])}*")
        st.write(f"Borrowing records: *{len(data['loans'])}*")

        if overdue:
            st.warning(f"{len(overdue)} book loan(s) are overdue.")
        else:
            st.success("No books are currently overdue.")


elif page == "Manage Books":
    st.title("📖 Manage Books")

    with st.form("book_form", clear_on_submit=True):
        title = st.text_input("Book title")
        author = st.text_input("Author")
        category = st.text_input("Subject or category")
        quantity = st.number_input(
            "Number of copies", min_value=1, max_value=1000, value=1
        )
        submitted = st.form_submit_button("Add Book")

    if submitted:
        if not title.strip() or not author.strip():
            st.error("Enter both the book title and author.")
        else:
            book_id = f"B{len(data['books']) + 1:03d}"
            data["books"].append({
                "id": book_id,
                "title": title.strip(),
                "author": author.strip(),
                "category": category.strip() or "General",
                "total": int(quantity),
                "available": int(quantity),
                "times_borrowed": 0
            })
            save_data()
            st.success(f"Book added! ID: {book_id}")

    st.divider()
    search = st.text_input("🔍 Search by title, author, category, or ID")
    matches = [
        book for book in data["books"]
        if search.lower() in (
            book["id"] + " " + book["title"] + " "
            + book["author"] + " " + book["category"]
        ).lower()
    ]

    if matches:
        st.dataframe(
            [
                {
                    "ID": b["id"],
                    "Title": b["title"],
                    "Author": b["author"],
                    "Category": b["category"],
                    "Total": b["total"],
                    "Available": b["available"],
                    "Times Borrowed": b["times_borrowed"]
                }
                for b in matches
            ],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No matching books found.")


elif page == "Manage Members":
    st.title("👥 Manage Members")

    with st.form("member_form", clear_on_submit=True):
        name = st.text_input("Member name")
        contact = st.text_input("Contact information (optional)")
        submitted = st.form_submit_button("Register Member")

    if submitted:
        if not name.strip():
            st.error("Enter the member's name.")
        else:
            member_id = f"M{len(data['members']) + 1:03d}"
            data["members"].append({
                "id": member_id,
                "name": name.strip(),
                "contact": contact.strip()
            })
            save_data()
            st.success(f"Member registered! ID: {member_id}")

    if data["members"]:
        st.dataframe(
            [
                {"Member ID": m["id"], "Name": m["name"],
                 "Contact": m["contact"]}
                for m in data["members"]
            ],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No members registered yet.")


elif page == "Issue Book":
    st.title("📤 Issue a Book")

    available_books = [
        b for b in data["books"] if b["available"] > 0
    ]

    if not available_books:
        st.warning("No books available. Add a book first.")
    elif not data["members"]:
        st.warning("Register a member before issuing a book.")
    else:
        with st.form("issue_form"):
            book_id = st.selectbox(
                "Select book",
                [b["id"] for b in available_books],
                format_func=lambda bid: f"{book_by_id(bid)['title']} ({bid})"
            )
            member_id = st.selectbox(
                "Select member",
                [m["id"] for m in data["members"]],
                format_func=lambda mid: (
                    f"{member_by_id(mid)['name']} ({mid})"
                )
            )
            submitted = st.form_submit_button("Issue Book")

        if submitted:
            today = date.today()
            due = today + timedelta(days=LOAN_DAYS)
            data["loans"].append({
                "id": f"L{len(data['loans']) + 1:03d}",
                "book_id": book_id,
                "member_id": member_id,
                "issue_date": today.isoformat(),
                "due_date": due.isoformat(),
                "return_date": None,
                "fine": 0
            })
            book_by_id(book_id)["available"] -= 1
            book_by_id(book_id)["times_borrowed"] += 1
            save_data()
            st.success(f"Book issued! Return by {due.isoformat()}.")


elif page == "Return Book":
    st.title("📥 Return a Book")
    loans = active_loans()

    if not loans:
        st.info("There are no active loans.")
    else:
        for loan in loans:
            book = book_by_id(loan["book_id"])
            member = member_by_id(loan["member_id"])

            with st.container(border=True):
                st.write(f"*{book['title']}* — {member['name']}")
                st.write(
                    f"Loan ID: {loan['id']} | Due: {loan['due_date']}"
                )
                st.write(f"Current fine: ₹{fine_for(loan)}")

                if st.button("Confirm Return", key=loan["id"]):
                    loan["return_date"] = date.today().isoformat()
                    loan["fine"] = fine_for(loan)
                    book["available"] += 1
                    save_data()
                    st.success(f"Returned successfully. Fine: ₹{loan['fine']}")
                    st.rerun()


elif page == "Overdue & History":
    st.title("⏰ Overdue Books & Borrowing History")

    overdue = [
        loan for loan in active_loans()
        if date.fromisoformat(loan["due_date"]) < date.today()
    ]

    st.subheader(f"Overdue loans: {len(overdue)}")
    overdue_rows = []

    for loan in overdue:
        overdue_rows.append({
            "Book": book_by_id(loan["book_id"])["title"],
            "Member": member_by_id(loan["member_id"])["name"],
            "Due Date": loan["due_date"],
            "Days Late": (
                date.today() - date.fromisoformat(loan["due_date"])
            ).days,
            "Current Fine (₹)": fine_for(loan)
        })

    if overdue_rows:
        st.dataframe(overdue_rows, use_container_width=True, hide_index=True)
    else:
        st.success("No overdue books.")

    st.divider()
    st.subheader("All Borrowing Records")
    history = []

    for loan in data["loans"]:
        history.append({
            "Loan ID": loan["id"],
            "Book": book_by_id(loan["book_id"])["title"],
            "Member": member_by_id(loan["member_id"])["name"],
            "Issue Date": loan["issue_date"],
            "Due Date": loan["due_date"],
            "Return Date": loan["return_date"] or "Not returned",
            "Fine (₹)": (
                loan["fine"] if loan["return_date"] else fine_for(loan)
            )
        })

    if history:
        st.dataframe(history, use_container_width=True, hide_index=True)
    else:
        st.info("No borrowing records yet.")