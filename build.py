# build.py

import os
from PyInstaller import __main__ as pyi_main

os.environ['TCL_LIBRARY'] = r"C:\Users\hi\anaconda3\Library\lib\tcl8.6"
os.environ['TK_LIBRARY'] = r"C:\Users\hi\anaconda3\Library\lib\tk8.6"

pyi_main.run([
    'main.py',
    '--onefile',
    '--name=ItalianLearning',
    '--noconsole',
    '--add-binary=C:\\Users\\hi\\anaconda3\\Library\\bin\\tcl86t.dll;.',
    '--add-binary=C:\\Users\\hi\\anaconda3\\Library\\bin\\tk86t.dll;.',
])