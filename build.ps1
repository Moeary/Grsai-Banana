# Install Nuitka if not installed
# pip install nuitka zstandard

# Build Command
nuitka `
    --standalone `
    --onefile `
    --enable-plugin=pyqt5 `
    --windows-icon-from-ico=logo.ico `
    --include-data-file=logo.ico=logo.ico `
    --nofollow-import-to=tkinter `
    --nofollow-import-to=unittest `
    --nofollow-import-to=pydoc `
    --nofollow-import-to=distutils `
    --nofollow-import-to=setuptools `
    --nofollow-import-to=lib2to3 `
    --output-dir=dist `
    --remove-output `
    --no-pyi-file `
    main.py
