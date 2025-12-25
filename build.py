import os
import shutil
import subprocess


def run_script(script_name):
    """Runs a Python script and checks for errors."""
    try:
        print(f"--- Running {script_name} ---")
        subprocess.run(
            ["python", script_name], check=True, text=True, capture_output=True
        )
        print(f"--- Finished {script_name} ---")
    except subprocess.CalledProcessError as e:
        print(f"!!! Error running {script_name} !!!")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        raise


def copy_files():
    """Copies static files and directories to the output directory."""
    output_dir = "site"
    static_dir = "static"

    print("--- Copying files ---")

    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Copy static HTML files from root to site/
    static_html_files = [
        "landing_page.html",
        "about.html",
        "contact.html",
        "privacy.html",
        "terms.html",
        "admin.html",
        "blog.html",
    ]
    for file_name in static_html_files:
        if os.path.exists(file_name):
            if file_name == "landing_page.html":
                shutil.copy(file_name, os.path.join(output_dir, "index.html"))
                print(f"Copied {file_name} to {os.path.join(output_dir, 'index.html')}")
            else:
                shutil.copy(file_name, os.path.join(output_dir, file_name))
                print(f"Copied {file_name} to {os.path.join(output_dir, file_name)}")

    # Copy static assets directory
    if os.path.exists(static_dir):
        shutil.copytree(
            static_dir, os.path.join(output_dir, static_dir), dirs_exist_ok=True
        )
        print(f"Copied '{static_dir}' directory to '{output_dir}/{static_dir}'")

    print("--- Finished copying files ---")


def main():
    """Main build function."""
    try:
        # Run generation scripts
        run_script("generate_blog.py")
        run_script("generate_gmc_feed.py")
        run_script("generate_rss.py")

        # Copy static files
        copy_files()

        print("\n✅✅✅ Build successful! ✅✅✅")

    except Exception as e:
        print(f"\n❌❌❌ Build failed: {e} ❌❌❌")
        exit(1)


if __name__ == "__main__":
    main()
