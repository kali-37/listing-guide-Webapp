import streamlit as st
from category_dict import categories
import asyncio
from scrapper import scrape
import threading
from concurrent.futures import ThreadPoolExecutor


def run_async_scrape(sellers_to_search, categories_to_search, st_instance):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            scrape(sellers_to_search, categories_to_search, st_instance)
        )
    finally:
        loop.close()


def main():
    st.title("Seller and Category Filter")

    # Initialize session state for sellers if it doesn't exist
    if "sellers" not in st.session_state:
        st.session_state.sellers = []

    if "scrapping_status" not in st.session_state:
        st.session_state.scrapping_status = None

    # Create a sidebar for filters
    st.sidebar.header("Filters", divider=True)

    # Seller input section with tag-like functionality
    st.sidebar.subheader(
        "Add Sellers", help="Type a seller name and press Enter to add it as a tag"
    )

    # Create a callback for the form submit
    def add_seller():
        if st.session_state.new_seller.strip():
            if st.session_state.new_seller.strip() not in st.session_state.sellers:
                st.session_state.sellers.append(st.session_state.new_seller.strip())
            st.session_state.new_seller = ""

    # Use a form for better input handling
    with st.sidebar.form(key="seller_form", border=True):
        st.text_input("Seller names", key="new_seller")
        print(st.session_state)
        st.form_submit_button("Add Seller", on_click=add_seller)

    # Display current sellers as tags
    if st.session_state.sellers:
        st.sidebar.write("Selected sellers:")
        cols = st.sidebar.columns(2)
        for idx, seller in enumerate(st.session_state.sellers):
            col_idx = idx % 2
            with cols[col_idx]:
                if st.button(f"❌ {seller}", key=f"del_{idx}"):
                    st.session_state.sellers.remove(seller)
                    st.rerun()

    # Multiple category selection
    st.sidebar.subheader("Select Categories")

    categorie = {}
    for _, value in categories.items():
        categorie[value.name] = value

    selected_categories = st.sidebar.multiselect(
        "list of Choosen categories", options=categorie.keys(), default=None
    )
    st.sidebar.text_input("File name", key="file_name")
    # Search button
    if st.sidebar.button("Scrape and Save"):
        # Display results
        st.header("Search Results")

        if not st.session_state.sellers and not selected_categories:
            st.warning("Please select at least one seller or category")
        elif not st.session_state.file_name:
            st.warning("Please enter a file name")

        # elif selected_categories and st.session_state.sellers and st.session_state.file_name:
        else:
            categories_to_search = [
                categorie[category] for category in selected_categories
            ]
            sellers_to_search = st.session_state.sellers
            # Create a progress indicator
            progress_bar = st.empty()
            progress_bar.info("Starting scraping operation...")

            with ThreadPoolExecutor() as executor:
                future = executor.submit(
                    run_async_scrape,
                    sellers_to_search,
                    categories_to_search,
                    st.session_state.file_name,
                )
                st.session_state.scraping_status = "Running"
                try:
                    future.result()
                    progress_bar.success("Scraping operation completed")
                except Exception as e:
                    progress_bar.error(f"An error occurred: {e}")
                    st.session_state.scraping_status = "Error"
                finally:
                    st.session_state.scraping_status = None

        if st.session_state.scrapping_status == "Running":
            st.write("Scraping is running")


if __name__ == "__main__":
    main()
