import streamlit as st
from category_dict import categories
import asyncio
from scrapper import scrape
import os
import uuid
import fcntl
import multiprocessing
import time
import signal


def run_async_scrape(
    sellers_to_search,
    categories_to_search,
    file_name,
    log_file,
    max_concurrency,
    delay_after_request,
):
    """
    Create a new event loop and run the async scrape function.
    This function is executed in a separate process.
    """
    # Reset SIGTERM to default so termination is not blocked.
    signal.signal(signal.SIGTERM, signal.SIG_DFL)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(
            scrape(
                sellers_to_search,
                categories_to_search,
                file_name,
                log_file,
                max_concurrency,
                delay_after_request,
            )
        )
    finally:
        loop.close()


def get_current_log(log_path: str):
    if not os.path.exists(log_path):
        return None
    with open(log_path, "r+") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            lines = f.readlines()
            if not lines:
                return None
            log_text = "".join(lines)
            f.seek(0)
            f.truncate()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    return log_text


def generate_file(log=False):
    if log:
        os.makedirs("logs", exist_ok=True)
        return os.path.join("logs", f"{uuid.uuid4()}.log")
    else:
        os.makedirs("data", exist_ok=True)
        return os.path.join("data", f"{uuid.uuid4()}.csv")


def main():
    st.title("Seller and Category Filter")
    if "sellers" not in st.session_state:
        st.session_state.sellers = []
    if "scraping_active" not in st.session_state:
        st.session_state.scraping_active = False
    if "scrape_process" not in st.session_state:
        st.session_state.scrape_process = None
    if "log_content" not in st.session_state:
        st.session_state.log_content = ""
    if "log_file" not in st.session_state:
        st.session_state.log_file = ""
    if "export_file" not in st.session_state:
        st.session_state.export_file = ""
    if "scrape_finished" not in st.session_state:
        st.session_state.scrape_finished = False

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

    st.session_state.max_concurrency = st.sidebar.slider(
        "Max Concurrency",
        1,
        15,
        2,
        help="Number of concurrent requests to make to the website.Note: if multiple Users are using this app at same time. It's better to keep this value low to avoid getting blocked by the website.",
    )
    st.session_state.delay_after_request = st.sidebar.slider(
        "Delay after request",
        0,
        10,
        0,
        help="How many seconds to wait between requests. More delay means slower but safer scrapin.Wait in seconds after each concurrent requests to the watch.com .",
    )

    file_name = st.sidebar.text_input("File name", key="file_name").strip()
    if file_name and not (file_name.endswith(".csv") or file_name.endswith(".excel")):
        file_name += ".csv"

    button_label = "Stop" if st.session_state.scraping_active else "Start Scrape"
    if st.sidebar.button(button_label):
        if st.session_state.scraping_active:
            if st.session_state.scrape_process is not None:
                st.sidebar.info("Attempting to stop scraping process...")
                st.session_state.scrape_process.terminate()
                st.session_state.scrape_process.join(timeout=1)
                if st.session_state.scrape_process.is_alive():
                    st.sidebar.warning(
                        "Process did not terminate with SIGTERM; force killing..."
                    )
                    st.session_state.scrape_process.kill()
                    st.session_state.scrape_process.join()
                st.session_state.scrape_process = None
            st.session_state.scraping_active = False
            st.sidebar.info("Scraping stopped by user.")
            st.rerun()
        else:
            # ----- Start scraping -----
            errors = False
            if st.session_state.sellers == []:
                st.warning("Please select at least one seller")
                errors = True
            if not selected_categories:
                st.warning("Please select at least one category")
                errors = True
            elif not file_name:
                st.warning("Please enter a file name")
                error = True
            if not errors:
                st.session_state.scraping_active = True
                st.session_state.scrape_finished = False
                st.session_state.log_content = ""
                # Generate a new log file and export file.
                log_file = generate_file(log=True)
                st.session_state.log_file = log_file
                st.session_state.export_file = generate_file(log=False)

                categories_to_search = [categorie[cat] for cat in selected_categories]
                sellers_to_search = st.session_state.sellers

                p = multiprocessing.Process(
                    target=run_async_scrape,
                    args=(
                        sellers_to_search,
                        categories_to_search,
                        st.session_state.export_file,
                        log_file,
                        st.session_state.max_concurrency,
                        st.session_state.delay_after_request,
                    ),
                )
                p.start()
                st.session_state.scrape_process = p
                st.rerun()

    # -------------------------------
    # Container for Live Log Updates
    # -------------------------------
    with st.container():
        if st.session_state.scraping_active:
            try:
                from streamlit_autorefresh import st_autorefresh

                st_autorefresh(interval=1000, key="log_autorefresh")
            except ImportError:
                time.sleep(1)
                st.rerun()

            new_logs = get_current_log(st.session_state.log_file)
            if new_logs:
                st.session_state.log_content += new_logs

            st.text_area("Live Logs", st.session_state.log_content, height=300)

            # Check if the process has finished.
            if (
                st.session_state.scrape_process is not None
                and not st.session_state.scrape_process.is_alive()
            ):
                st.session_state.scraping_active = False
                st.session_state.scrape_process = None
                st.session_state.scrape_finished = True
                st.success("Scraping finished.")
                # Do not rerun immediately so that the export popup can be shown.
        else:
            st.text_area("Live Logs", st.session_state.log_content, height=300)
            st.info("Idle. Press 'Start Scrape' to start scraping.")

    if st.session_state.scrape_finished:
        if st.session_state.export_file and os.path.exists(
            st.session_state.export_file
        ):
            print(st.session_state)
            found_data = True
            with open(st.session_state.export_file, "r") as f:
                export_data = f.read()
                if len(f.readlines()) <= 1:
                    found_data = False
                    st.warning(f"No data found during recent Scrape.")
            if found_data:

                def handle_download():
                    if os.path.exists(st.session_state.export_file):
                        os.remove(st.session_state.export_file)

                st.download_button(
                    label="Download Recent Scraped Data [Auto-Delete after download]",
                    data=export_data,
                    file_name=file_name,
                    mime="text/csv",
                    on_click=handle_download,
                )
        else:
            st.info("Export file not available yet ,Start Scraping.")


if __name__ == "__main__":
    try:
        multiprocessing.set_start_method("fork")
    except RuntimeError:
        pass
    main()
