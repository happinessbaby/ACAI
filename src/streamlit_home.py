from st_pages import show_pages_from_config, add_page_title, show_pages, Page

# Either this or add_indentation() MUST be called on each page in your
# app to add indendation in the sidebar

# Optional -- adds the title and icon to the current page
add_page_title()

# Specify what pages should be shown in the sidebar, and what their titles and icons
# should be
show_pages(
    [
        Page("streamlit_chatbot.py", "Home", "🏠"),
        Page("streamlit_interviewbot.py", "Mock Interview", ":books:"),
    ]
)