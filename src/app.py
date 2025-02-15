import streamlit as st
from category_dict import categories
import asyncio
from scrapper import scrape
import os
import uuid
import csv
from io import StringIO


def main():
    st.title("Seller and Category Filter")
    if "sellers" not in st.session_state:
        st.session_state.sellers = []
    if "export_file" not in st.session_state:
        st.session_state.export_file = ""

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
        )
        st.form_submit_button("Add Seller", on_click=add_seller)

    if st.session_state.sellers:
        st.sidebar.write("Selected sellers:")
        cols = st.sidebar.columns(2)
        for idx, seller in enumerate(st.session_state.sellers):
            col = cols[idx % 2]
            if col.button(f"❌ {seller}", key=f"del_{idx}"):
                st.session_state.sellers.remove(seller)
                st.rerun()

    st.sidebar.subheader("Select Categories")
    categorie = {value.name: value for _, value in categories.items()}
    selected_categories = st.sidebar.multiselect(
        "List of chosen categories", options=list(categorie.keys())
    )

    max_concurrency = st.sidebar.slider(
        "Max Concurrency",
        1,
        15,
        2,
        help="Number of concurrent requests to make to the website. Note: if multiple Users are using this app at same time. It's better to keep this value low to avoid getting blocked by the website.",
    )
    delay_after_request = st.sidebar.slider(
        "Delay after request",
        0,
        10,
        0,
        help="How many seconds to wait between requests. More delay means slower but safer scraping. Wait in seconds after each concurrent requests to the watch.com.",
    )

    file_name = st.sidebar.text_input("File name", key="file_name").strip()
    if file_name and not (file_name.endswith(".csv") or file_name.endswith(".excel")):
        file_name += ".csv"

    if st.sidebar.button("Start Scrape"):
        errors = False
        if st.session_state.sellers == []:
            st.warning("Please select at least one seller")
            errors = True
        if not selected_categories:
            st.warning("Please select at least one category")
            errors = True
        elif not file_name:
            st.warning("Please enter a file name")
            errors = True

        if not errors:
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

                st.success("Scraping completed!")

                if not scraped_data:
                    st.warning("No data found during scraping.")
                else:
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

                    for row in scraped_data:
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
