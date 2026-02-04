# PCAN_Auto

This project is a production-grade Python application blueprint that replicates the core and add-in feature set of PCAN-Explorer 6.

See `app/README.md` for a detailed breakdown of the new architecture.

## Running the App

1.  Install dependencies:
    ```sh
    pip install -r requirements.txt
    ```

2.  Run the main UI (requires a PCAN device or will show an error):
    ```sh
    python -m app.ui.main
    ```

3.  Run a basic smoke test (no hardware required):
    ```sh
    python -m app.examples.smoke
    ```

