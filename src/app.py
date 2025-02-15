import streamlit as st
from category_dict import categories
import asyncio
from scrapper import scrape
import csv
from io import StringIO


def main():
    st.title("Seller and Category Filter")

    if "sellers" not in st.session_state:
        st.session_state.sellers = []
    if "export_file" not in st.session_state:
        st.session_state.export_file = ""
    if "scraping" not in st.session_state:
        st.session_state.scraping = False
    if "scraped_data" not in st.session_state:
        st.session_state.scraped_data = None

    st.sidebar.header("Filters")

    def add_seller():
        seller = st.session_state.new_seller.strip()
        if seller and seller not in st.session_state.sellers:
            st.session_state.sellers.append(seller)
        st.session_state.new_seller = ""

    with st.sidebar.form("seller_form"):
        st.text_input(
            "Seller name",
            key="new_seller",
            help="Enter the name of the seller and press enter to add multiple sellers.",
            disabled=st.session_state.scraping,
        )
        st.form_submit_button(
            "Add Seller", on_click=add_seller, disabled=st.session_state.scraping
        )

    if st.session_state.sellers:
        st.sidebar.write("Selected sellers:")
        cols = st.sidebar.columns(2)
        for idx, seller in enumerate(st.session_state.sellers):
            col = cols[idx % 2]
            if col.button(
                f"❌ {seller}", key=f"del_{idx}", disabled=st.session_state.scraping
            ):
                st.session_state.sellers.remove(seller)
                st.rerun()

    st.sidebar.subheader("Select Categories")
    categorie = {value.name: value for _, value in categories.items()}
    selected_categories = st.sidebar.multiselect(
        "List of chosen categories",
        options=list(categorie.keys()),
        disabled=st.session_state.scraping,
    )

    max_concurrency = st.sidebar.slider(
        "Max Concurrency",
        1,
        15,
        2,
        help="Number of concurrent requests to make to the website. Lower value reduces risk of blocking.",
        disabled=st.session_state.scraping,
    )
    delay_after_request = st.sidebar.slider(
        "Delay after request",
        0,
        10,
        0,
        help="Wait time between concurrent requests (in seconds).",
        disabled=st.session_state.scraping,
    )

    file_name = st.sidebar.text_input(
        "File name", key="file_name", disabled=st.session_state.scraping
    ).strip()
    if file_name and not (file_name.endswith(".csv") or file_name.endswith(".excel")):
        file_name += ".csv"

    if st.sidebar.button(
        "Start Scrape",
        disabled=st.session_state.scraping,
        help="Starts scraping. Cannot be canceled midway.",
    ):
        errors = False
        if not st.session_state.sellers:
            st.warning("Please select at least one seller")
            errors = True
        if not selected_categories:
            st.warning("Please select at least one category")
            errors = True
        elif not file_name:
            st.warning("Please enter a file name")
            errors = True

        if not errors:
            st.session_state.scraping = True
            st.session_state.scraped_data = None  # Reset previous data
            st.rerun()

    if st.session_state.scraping:
        with st.spinner("Scraping in progress... Please wait."):
            categories_to_search = [categorie[cat] for cat in selected_categories]
            sellers_to_search = st.session_state.sellers

            # Run the scraping synchronously
            scraped_data = asyncio.run(
                scrape(
                    sellers_to_search,
                    categories_to_search,
                    max_concurrency,
                    delay_after_request,
                )
            )

            st.session_state.scraping = False
            st.session_state.scraped_data = scraped_data  # Store results
            st.rerun()

    # Display results if available
    if st.session_state.scraped_data is not None:
        if not st.session_state.scraped_data:
            st.warning("No data found during scraping.")
        else:
            st.success("Scraping completed!")

            output = StringIO()
            csv_writer = csv.writer(output)

            headers = [
                "Price",
                "Shop Now Link",
                "Watchers",
                "Title",
                "Start Date",
                "End Date",
                "Running Time",
            ]
            csv_writer.writerow(headers)

            for row in st.session_state.scraped_data:
                csv_writer.writerow(row)

            csv_string = output.getvalue()
            output.close()

            st.download_button(
                label="Download Scraped Data",
                data=csv_string,
                file_name=file_name,
                mime="text/csv",
            )


if __name__ == "__main__":
    main()
